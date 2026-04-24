#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import polars as pl

load_dotenv()

DATA_ROOT = Path("/mnt/data/finance/cryptocurrency")
OUTPUT_DIR = Path("outputs/detection")


def load_data(symbol: str, timeframe: str = "1h") -> pl.DataFrame:
    from crypto_backtest.data_loader import BacktestConfig, load_hourly_data
    
    config = BacktestConfig(
        data_path=DATA_ROOT / symbol,
        ma_periods=[25, 50, 100, 200],
    )
    return load_hourly_data(config)


def get_rule_based_signals(df: pl.DataFrame, symbol: str) -> list[int]:
    from crypto_backtest.long_strategy import (
        LongStrategyConfig,
        LongBacktestEngine,
    )
    
    config = LongStrategyConfig(
        data_path=DATA_ROOT / symbol,
        symbol=symbol,
        breakout_ma=50,
        consolidation_bars=5,
        consolidation_range_pct=3.0,
        drop_threshold_pct=3.0,
        take_profit_pct=10.0,
        stop_loss_pct=3.0,
        half_close_enabled=True,
        half_close_pct=5.0,
    )
    
    engine = LongBacktestEngine(config)
    engine.run(df)
    trades = engine.get_trades_df()
    
    signal_indices = []
    for trade in trades.iter_rows(named=True):
        open_time = trade["open_time"]
        idx = df.filter(pl.col("open_time") == open_time).row_nr()
        if idx:
            signal_indices.append(idx[0])
    
    return signal_indices


def run_enhanced_rules(df: pl.DataFrame, output_dir: Path):
    from crypto_backtest.detection.enhanced_rules import EnhancedLShapeDetector
    
    print("\n=== Phase 1: Enhanced Rule-Based Detection ===")
    
    detector = EnhancedLShapeDetector()
    results = detector.detect_batch(df, ma_column="ma_50")
    
    print(f"Detected {len(results)} patterns with enhanced rules")
    
    rows = []
    for idx, result in results:
        rows.append({
            "idx": idx,
            "confidence": result.confidence,
            "drop_pct": result.drop_pct,
            "consol_range_pct": result.consolidation_range_pct,
            "flatness": result.flatness_score,
            "volume_declining": result.volume_declining,
        })
    
    if rows:
        result_df = pl.DataFrame(rows)
        output_dir.mkdir(parents=True, exist_ok=True)
        result_df.write_parquet(output_dir / "enhanced_rules_signals.parquet")
        print(f"Saved to {output_dir / 'enhanced_rules_signals.parquet'}")
    
    return results


def run_vlm_labeling(
    df: pl.DataFrame,
    signal_indices: list[int],
    api_key: str,
    output_dir: Path,
):
    from crypto_backtest.detection.vlm_labeler import GeminiLabeler
    from crypto_backtest.detection.vlm_labeler.labeler import GeminiLabelerConfig
    
    print("\n=== Phase 2: VLM Labeling with Gemini ===")
    
    config = GeminiLabelerConfig(
        api_key=api_key,
        model="gemini-2.0-flash",
        rate_limit_delay=1.5,
    )
    
    labeler = GeminiLabeler(config)
    
    result_df = labeler.generate_training_dataset(
        df=df,
        signal_indices=signal_indices[:50],
        negative_sample_ratio=1.0,
        ma_columns=["ma_50", "ma_100"],
        output_dir=output_dir,
    )
    
    print(f"\nVLM Labeling Results:")
    print(f"  Total samples: {len(result_df)}")
    print(f"  Rule signals: {result_df.filter(pl.col('is_rule_signal')).height}")
    print(f"  VLM confirmed: {result_df.filter(pl.col('is_lshape_vlm')).height}")
    
    agreement = result_df.filter(
        pl.col("is_rule_signal") == pl.col("is_lshape_vlm")
    ).height / len(result_df) * 100
    print(f"  Agreement rate: {agreement:.1f}%")
    
    return result_df


def run_gaf_cnn_training(
    df: pl.DataFrame,
    positive_indices: list[int],
    negative_indices: list[int],
    output_dir: Path,
):
    from crypto_backtest.detection.gaf_cnn import GAFClassifier
    from crypto_backtest.detection.gaf_cnn.classifier import GAFConfig
    
    print("\n=== Phase 3: GAF + CNN Training ===")
    
    config = GAFConfig(
        window_size=64,
        image_size=64,
        channels=["close", "volume"],
        epochs=30,
        batch_size=16,
    )
    
    classifier = GAFClassifier(config)
    
    history = classifier.train(
        df=df,
        positive_indices=positive_indices,
        negative_indices=negative_indices,
        val_split=0.2,
    )
    
    print(f"\nGAF+CNN Training Results:")
    print(f"  Best validation accuracy: {history['best_acc']:.4f}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    classifier.save(output_dir / "gaf_cnn_model.pt")
    print(f"  Saved model to {output_dir / 'gaf_cnn_model.pt'}")
    
    return classifier


def run_pipeline_comparison(
    df: pl.DataFrame,
    signal_indices: list[int],
    gaf_model_path: Path | None = None,
):
    from crypto_backtest.detection.integration import DetectionPipeline
    from crypto_backtest.detection.integration.pipeline import PipelineConfig
    
    print("\n=== Integration: Pipeline Comparison ===")
    
    config = PipelineConfig(
        use_enhanced_rules=True,
        use_gaf_cnn=gaf_model_path is not None,
        ensemble_method="weighted",
    )
    
    pipeline = DetectionPipeline(config)
    
    if gaf_model_path and gaf_model_path.exists():
        pipeline.load_gaf_model(gaf_model_path)
    
    comparison_df = pipeline.compare_methods(
        df=df,
        indices=signal_indices[:100],
        ma_column="ma_50",
    )
    
    print(f"\nPipeline Comparison:")
    print(comparison_df.describe())
    
    return comparison_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--phase", default="all", 
                       choices=["all", "enhanced", "vlm_label", "gaf_cnn", "compare"])
    parser.add_argument("--gemini-key", default=os.getenv("GEMINI_API_KEY"))
    args = parser.parse_args()
    
    output_dir = OUTPUT_DIR / args.symbol
    
    print(f"Loading {args.symbol} data...")
    df = load_data(args.symbol)
    print(f"Loaded {len(df)} bars")
    
    print(f"Getting rule-based signals...")
    signal_indices = get_rule_based_signals(df, args.symbol)
    print(f"Found {len(signal_indices)} signals")
    
    if args.phase in ["all", "enhanced"]:
        run_enhanced_rules(df, output_dir)
    
    if args.phase in ["all", "vlm_label"]:
        if not args.gemini_key:
            print("ERROR: --gemini-key or GEMINI_API_KEY required for VLM labeling")
        else:
            run_vlm_labeling(df, signal_indices, args.gemini_key, output_dir)
    
    if args.phase in ["all", "gaf_cnn"]:
        import random
        all_indices = set(range(100, len(df)))
        negative_indices = list(all_indices - set(signal_indices))
        negative_sample = random.sample(negative_indices, min(len(signal_indices), len(negative_indices)))
        
        run_gaf_cnn_training(df, signal_indices, negative_sample, output_dir)
    
    if args.phase in ["all", "compare"]:
        gaf_model = output_dir / "gaf_cnn_model.pt"
        run_pipeline_comparison(df, signal_indices, gaf_model if gaf_model.exists() else None)
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
