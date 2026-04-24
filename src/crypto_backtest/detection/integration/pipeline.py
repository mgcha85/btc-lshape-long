"""
Integration Pipeline - Combines all detection methods into unified interface.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl

from ..enhanced_rules.detector import EnhancedLShapeDetector, EnhancedDetectorConfig
from ..gaf_cnn.classifier import GAFClassifier, GAFConfig


@dataclass
class PipelineConfig:
    use_enhanced_rules: bool = True
    use_gaf_cnn: bool = False
    use_yolo: bool = False
    use_vlm: bool = False
    
    ensemble_method: Literal["any", "all", "majority", "weighted"] = "weighted"
    weights: dict | None = None
    min_confidence: float = 0.5
    
    enhanced_config: EnhancedDetectorConfig | None = None
    gaf_config: GAFConfig | None = None
    
    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                "enhanced_rules": 0.3,
                "gaf_cnn": 0.3,
                "yolo": 0.2,
                "vlm": 0.2,
            }


@dataclass
class PipelineResult:
    detected: bool
    confidence: float
    
    enhanced_rules_detected: bool | None = None
    enhanced_rules_confidence: float | None = None
    
    gaf_cnn_detected: bool | None = None
    gaf_cnn_confidence: float | None = None
    
    yolo_detected: bool | None = None
    yolo_confidence: float | None = None
    
    vlm_detected: bool | None = None
    vlm_confidence: float | None = None
    
    details: dict | None = None


class DetectionPipeline:
    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        
        self.enhanced_detector = None
        self.gaf_classifier = None
        self.yolo_detector = None
        self.vlm_labeler = None
        
        if self.config.use_enhanced_rules:
            self.enhanced_detector = EnhancedLShapeDetector(
                self.config.enhanced_config or EnhancedDetectorConfig()
            )
        
        if self.config.use_gaf_cnn:
            self.gaf_classifier = GAFClassifier(
                self.config.gaf_config or GAFConfig()
            )
    
    def load_gaf_model(self, path: Path) -> None:
        if self.gaf_classifier is None:
            self.gaf_classifier = GAFClassifier(self.config.gaf_config or GAFConfig())
        self.gaf_classifier.load(path)
    
    def load_yolo_model(self, path: Path) -> None:
        from ..yolo_detector.detector import YOLOPatternDetector, YOLOConfig
        self.yolo_detector = YOLOPatternDetector(YOLOConfig())
        self.yolo_detector.load(path)
    
    def detect(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_column: str = "ma_50",
    ) -> PipelineResult:
        results = {}
        
        if self.enhanced_detector:
            enhanced_result = self.enhanced_detector.detect(df, idx, ma_column)
            results["enhanced_rules"] = (
                enhanced_result.detected,
                enhanced_result.confidence,
            )
        
        if self.gaf_classifier and self.gaf_classifier.model:
            try:
                is_lshape, conf = self.gaf_classifier.predict(df, idx)
                results["gaf_cnn"] = (is_lshape, conf)
            except ValueError:
                results["gaf_cnn"] = (False, 0.0)
        
        if self.yolo_detector and self.yolo_detector.model:
            try:
                is_pattern, conf, _ = self.yolo_detector.is_lshape_pattern(df, idx)
                results["yolo"] = (is_pattern, conf)
            except Exception:
                results["yolo"] = (False, 0.0)
        
        final_detected, final_confidence = self._ensemble(results)
        
        return PipelineResult(
            detected=final_detected,
            confidence=final_confidence,
            enhanced_rules_detected=results.get("enhanced_rules", (None, None))[0],
            enhanced_rules_confidence=results.get("enhanced_rules", (None, None))[1],
            gaf_cnn_detected=results.get("gaf_cnn", (None, None))[0],
            gaf_cnn_confidence=results.get("gaf_cnn", (None, None))[1],
            yolo_detected=results.get("yolo", (None, None))[0],
            yolo_confidence=results.get("yolo", (None, None))[1],
            vlm_detected=results.get("vlm", (None, None))[0],
            vlm_confidence=results.get("vlm", (None, None))[1],
            details={"raw_results": results},
        )
    
    def _ensemble(
        self,
        results: dict[str, tuple[bool, float]],
    ) -> tuple[bool, float]:
        if not results:
            return False, 0.0
        
        method = self.config.ensemble_method
        weights = self.config.weights
        
        if method == "any":
            detected = any(r[0] for r in results.values())
            confidence = max(r[1] for r in results.values()) if detected else 0.0
            
        elif method == "all":
            detected = all(r[0] for r in results.values())
            confidence = min(r[1] for r in results.values()) if detected else 0.0
            
        elif method == "majority":
            votes = sum(1 for r in results.values() if r[0])
            detected = votes > len(results) / 2
            confidence = sum(r[1] for r in results.values() if r[0]) / max(votes, 1)
            
        elif method == "weighted":
            weighted_sum = 0.0
            total_weight = 0.0
            
            for name, (det, conf) in results.items():
                w = weights.get(name, 0.0)
                if det:
                    weighted_sum += w * conf
                total_weight += w
            
            confidence = weighted_sum / total_weight if total_weight > 0 else 0.0
            detected = confidence >= self.config.min_confidence
        else:
            detected = False
            confidence = 0.0
        
        return detected, confidence
    
    def detect_batch(
        self,
        df: pl.DataFrame,
        indices: list[int],
        ma_column: str = "ma_50",
    ) -> list[tuple[int, PipelineResult]]:
        return [(idx, self.detect(df, idx, ma_column)) for idx in indices]
    
    def compare_methods(
        self,
        df: pl.DataFrame,
        indices: list[int],
        ma_column: str = "ma_50",
    ) -> pl.DataFrame:
        rows = []
        
        for idx in indices:
            result = self.detect(df, idx, ma_column)
            rows.append({
                "idx": idx,
                "final_detected": result.detected,
                "final_confidence": result.confidence,
                "enhanced_detected": result.enhanced_rules_detected,
                "enhanced_confidence": result.enhanced_rules_confidence,
                "gaf_detected": result.gaf_cnn_detected,
                "gaf_confidence": result.gaf_cnn_confidence,
                "yolo_detected": result.yolo_detected,
                "yolo_confidence": result.yolo_confidence,
            })
        
        return pl.DataFrame(rows)
