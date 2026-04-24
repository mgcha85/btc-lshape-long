"""
L-Shape Detection Enhancement Modules

4 parallel approaches for improving pattern detection:
1. enhanced_rules: ATR-based dynamic thresholds + volume + flatness
2. vlm_labeler: Gemini Vision for labeling training data
3. gaf_cnn: Gramian Angular Field + CNN classifier
4. yolo_detector: YOLOv8 for real-time pattern detection
"""

from .enhanced_rules.detector import EnhancedLShapeDetector
from .vlm_labeler.labeler import GeminiLabeler
from .gaf_cnn.classifier import GAFClassifier
from .yolo_detector.detector import YOLOPatternDetector
from .integration.pipeline import DetectionPipeline

__all__ = [
    "EnhancedLShapeDetector",
    "GeminiLabeler", 
    "GAFClassifier",
    "YOLOPatternDetector",
    "DetectionPipeline",
]
