"""
Gemini Vision Labeler for L-Shape Pattern Training Data Generation
"""

import base64
import io
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl
import google.generativeai as genai

try:
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


@dataclass
class LabelResult:
    is_lshape: bool
    confidence: float
    drop_quality: Literal["clear", "moderate", "weak", "none"]
    consolidation_quality: Literal["flat", "choppy", "trending", "none"]
    breakout_quality: Literal["strong", "moderate", "weak", "false"]
    reasoning: str
    raw_response: str


@dataclass
class GeminiLabelerConfig:
    api_key: str
    model: str = "gemini-2.5-flash"
    chart_width: int = 800
    chart_height: int = 400
    lookback_bars: int = 100
    rate_limit_delay: float = 1.0


LABELING_PROMPT = """Analyze this cryptocurrency candlestick chart for an L-shape pattern.

L-shape pattern definition:
1. DROP: Sharp price decline (at least 3-5% from recent high)
2. CONSOLIDATION: Horizontal price action forming a flat bottom (low volatility)
3. BREAKOUT: Price breaks above moving average with bullish candle

Evaluate each component and provide:

1. is_lshape: true/false - Is this a valid L-shape pattern?
2. confidence: 0.0-1.0 - How confident are you?
3. drop_quality: "clear" | "moderate" | "weak" | "none"
4. consolidation_quality: "flat" | "choppy" | "trending" | "none"
5. breakout_quality: "strong" | "moderate" | "weak" | "false"
6. reasoning: Brief explanation (1-2 sentences)

Respond in JSON format only:
{
    "is_lshape": boolean,
    "confidence": number,
    "drop_quality": string,
    "consolidation_quality": string,
    "breakout_quality": string,
    "reasoning": string
}"""


class GeminiLabeler:
    def __init__(self, config: GeminiLabelerConfig):
        self.config = config
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model)
        
        if not HAS_MPL:
            raise ImportError("mplfinance required: pip install mplfinance matplotlib")
    
    def generate_chart_image(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_columns: list[str] | None = None,
    ) -> bytes:
        lookback = self.config.lookback_bars
        start_idx = max(0, idx - lookback)
        window = df.slice(start_idx, idx - start_idx + 1)
        
        pdf = window.to_pandas()
        pdf.index = pdf["open_time"]
        pdf = pdf[["open", "high", "low", "close", "volume"]]
        pdf.columns = ["Open", "High", "Low", "Close", "Volume"]
        
        addplots = []
        if ma_columns:
            colors = ["blue", "orange", "green", "red", "purple"]
            for i, ma_col in enumerate(ma_columns):
                if ma_col in window.columns:
                    ma_data = window[ma_col].to_pandas()
                    ma_data.index = pdf.index
                    addplots.append(mpf.make_addplot(
                        ma_data, 
                        color=colors[i % len(colors)],
                        width=1.0,
                    ))
        
        buf = io.BytesIO()
        fig, axes = mpf.plot(
            pdf,
            type="candle",
            style="charles",
            addplot=addplots if addplots else None,
            volume=True,
            figsize=(self.config.chart_width / 100, self.config.chart_height / 100),
            returnfig=True,
        )
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        
        return buf.read()
    
    def label_pattern(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_columns: list[str] | None = None,
    ) -> LabelResult:
        image_bytes = self.generate_chart_image(df, idx, ma_columns)
        
        image_part = {
            "mime_type": "image/png",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }
        
        response = self.model.generate_content([
            LABELING_PROMPT,
            image_part,
        ])
        
        raw_response = response.text
        
        try:
            json_str = raw_response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            return LabelResult(
                is_lshape=bool(data.get("is_lshape", False)),
                confidence=float(data.get("confidence", 0.0)),
                drop_quality=data.get("drop_quality", "none"),
                consolidation_quality=data.get("consolidation_quality", "none"),
                breakout_quality=data.get("breakout_quality", "false"),
                reasoning=data.get("reasoning", ""),
                raw_response=raw_response,
            )
        except (json.JSONDecodeError, KeyError) as e:
            return LabelResult(
                is_lshape=False,
                confidence=0.0,
                drop_quality="none",
                consolidation_quality="none",
                breakout_quality="false",
                reasoning=f"Parse error: {e}",
                raw_response=raw_response,
            )
    
    def label_batch(
        self,
        df: pl.DataFrame,
        indices: list[int],
        ma_columns: list[str] | None = None,
        save_path: Path | None = None,
    ) -> list[tuple[int, LabelResult]]:
        results = []
        
        for i, idx in enumerate(indices):
            print(f"Labeling {i+1}/{len(indices)} (idx={idx})...")
            
            try:
                result = self.label_pattern(df, idx, ma_columns)
                results.append((idx, result))
            except Exception as e:
                print(f"  Error: {e}")
                results.append((idx, LabelResult(
                    is_lshape=False,
                    confidence=0.0,
                    drop_quality="none",
                    consolidation_quality="none",
                    breakout_quality="false",
                    reasoning=f"API error: {e}",
                    raw_response="",
                )))
            
            time.sleep(self.config.rate_limit_delay)
        
        if save_path:
            self._save_results(results, save_path)
        
        return results
    
    def _save_results(
        self,
        results: list[tuple[int, LabelResult]],
        path: Path,
    ) -> None:
        data = [
            {
                "idx": idx,
                "is_lshape": r.is_lshape,
                "confidence": r.confidence,
                "drop_quality": r.drop_quality,
                "consolidation_quality": r.consolidation_quality,
                "breakout_quality": r.breakout_quality,
                "reasoning": r.reasoning,
            }
            for idx, r in results
        ]
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(data)} labels to {path}")
    
    def generate_training_dataset(
        self,
        df: pl.DataFrame,
        signal_indices: list[int],
        negative_sample_ratio: float = 1.0,
        ma_columns: list[str] | None = None,
        output_dir: Path | None = None,
    ) -> pl.DataFrame:
        import random
        
        all_indices = set(range(100, len(df)))
        signal_set = set(signal_indices)
        negative_pool = list(all_indices - signal_set)
        
        n_negatives = int(len(signal_indices) * negative_sample_ratio)
        negative_indices = random.sample(negative_pool, min(n_negatives, len(negative_pool)))
        
        all_samples = signal_indices + negative_indices
        random.shuffle(all_samples)
        
        print(f"Labeling {len(signal_indices)} signals + {len(negative_indices)} negatives...")
        
        results = self.label_batch(df, all_samples, ma_columns)
        
        rows = []
        for idx, result in results:
            is_signal = idx in signal_set
            rows.append({
                "idx": idx,
                "is_rule_signal": is_signal,
                "is_lshape_vlm": result.is_lshape,
                "confidence": result.confidence,
                "drop_quality": result.drop_quality,
                "consolidation_quality": result.consolidation_quality,
                "breakout_quality": result.breakout_quality,
                "reasoning": result.reasoning,
            })
        
        result_df = pl.DataFrame(rows)
        
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            result_df.write_parquet(output_dir / "vlm_labels.parquet")
            result_df.write_csv(output_dir / "vlm_labels.csv")
        
        return result_df
