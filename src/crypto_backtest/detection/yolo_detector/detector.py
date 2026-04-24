"""
YOLOv8 Pattern Detector for Real-Time L-Shape Detection

Uses ultralytics YOLOv8 for object detection on candlestick chart images.
Requires labeled bounding boxes for training.
"""

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import polars as pl

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

try:
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    from PIL import Image
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


@dataclass
class YOLOConfig:
    model_size: Literal["n", "s", "m", "l", "x"] = "s"
    image_width: int = 640
    image_height: int = 480
    window_size: int = 100
    
    conf_threshold: float = 0.5
    iou_threshold: float = 0.45
    
    epochs: int = 100
    batch_size: int = 16
    device: str = "0"


@dataclass
class DetectionBox:
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    
    @property
    def center(self) -> tuple[float, float]:
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2
    
    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


class ChartImageGenerator:
    def __init__(self, config: YOLOConfig):
        if not HAS_MPL:
            raise ImportError("mplfinance required: pip install mplfinance matplotlib pillow")
        self.config = config
    
    def generate(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_columns: list[str] | None = None,
    ) -> Image.Image:
        window_size = self.config.window_size
        start_idx = max(0, idx - window_size)
        window = df.slice(start_idx, idx - start_idx + 1)
        
        pdf = window.to_pandas()
        pdf.index = pdf["open_time"]
        pdf = pdf[["open", "high", "low", "close", "volume"]]
        pdf.columns = ["Open", "High", "Low", "Close", "Volume"]
        
        addplots = []
        if ma_columns:
            colors = ["blue", "orange", "green", "red"]
            for i, col in enumerate(ma_columns):
                if col in window.columns:
                    ma_data = window[col].to_pandas()
                    ma_data.index = pdf.index
                    addplots.append(mpf.make_addplot(
                        ma_data,
                        color=colors[i % len(colors)],
                        width=1.0,
                    ))
        
        buf = io.BytesIO()
        fig, _ = mpf.plot(
            pdf,
            type="candle",
            style="charles",
            addplot=addplots if addplots else None,
            volume=True,
            figsize=(self.config.image_width / 100, self.config.image_height / 100),
            returnfig=True,
        )
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        
        return Image.open(buf).convert("RGB")


class DatasetGenerator:
    CLASS_NAMES = ["lshape_drop", "lshape_consolidation", "lshape_breakout"]
    
    def __init__(self, config: YOLOConfig):
        self.config = config
        self.image_gen = ChartImageGenerator(config)
    
    def create_yolo_dataset(
        self,
        df: pl.DataFrame,
        labeled_data: list[dict],
        output_dir: Path,
        train_split: float = 0.8,
    ) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for split in ["train", "val"]:
            (output_dir / "images" / split).mkdir(parents=True, exist_ok=True)
            (output_dir / "labels" / split).mkdir(parents=True, exist_ok=True)
        
        n_train = int(len(labeled_data) * train_split)
        
        for i, sample in enumerate(labeled_data):
            split = "train" if i < n_train else "val"
            idx = sample["idx"]
            
            image = self.image_gen.generate(df, idx)
            image_path = output_dir / "images" / split / f"{idx}.png"
            image.save(image_path)
            
            label_path = output_dir / "labels" / split / f"{idx}.txt"
            self._write_yolo_label(label_path, sample.get("boxes", []), image.size)
        
        self._write_data_yaml(output_dir)
    
    def _write_yolo_label(
        self,
        path: Path,
        boxes: list[dict],
        image_size: tuple[int, int],
    ) -> None:
        w, h = image_size
        lines = []
        
        for box in boxes:
            class_id = self.CLASS_NAMES.index(box["class"])
            x_center = (box["x1"] + box["x2"]) / 2 / w
            y_center = (box["y1"] + box["y2"]) / 2 / h
            width = (box["x2"] - box["x1"]) / w
            height = (box["y2"] - box["y1"]) / h
            lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
        
        with open(path, "w") as f:
            f.write("\n".join(lines))
    
    def _write_data_yaml(self, output_dir: Path) -> None:
        yaml_content = f"""path: {output_dir.absolute()}
train: images/train
val: images/val

names:
  0: lshape_drop
  1: lshape_consolidation
  2: lshape_breakout
"""
        with open(output_dir / "data.yaml", "w") as f:
            f.write(yaml_content)


class YOLOPatternDetector:
    def __init__(self, config: YOLOConfig | None = None):
        if not HAS_YOLO:
            raise ImportError("ultralytics required: pip install ultralytics")
        
        self.config = config or YOLOConfig()
        self.image_gen = ChartImageGenerator(self.config)
        self.model = None
    
    def train(
        self,
        data_yaml: Path,
        output_dir: Path | None = None,
    ) -> dict:
        model_name = f"yolov8{self.config.model_size}.pt"
        self.model = YOLO(model_name)
        
        results = self.model.train(
            data=str(data_yaml),
            epochs=self.config.epochs,
            batch=self.config.batch_size,
            imgsz=self.config.image_width,
            device=self.config.device,
            project=str(output_dir) if output_dir else "runs/detect",
            name="lshape",
        )
        
        return {"results": results}
    
    def load(self, weights_path: Path) -> None:
        self.model = YOLO(str(weights_path))
    
    def detect(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_columns: list[str] | None = None,
    ) -> list[DetectionBox]:
        if self.model is None:
            raise ValueError("Model not loaded")
        
        image = self.image_gen.generate(df, idx, ma_columns)
        
        results = self.model.predict(
            source=image,
            conf=self.config.conf_threshold,
            iou=self.config.iou_threshold,
            verbose=False,
        )[0]
        
        boxes = []
        for box in results.boxes:
            class_id = int(box.cls[0])
            boxes.append(DetectionBox(
                class_id=class_id,
                class_name=DatasetGenerator.CLASS_NAMES[class_id],
                confidence=float(box.conf[0]),
                x1=float(box.xyxy[0][0]),
                y1=float(box.xyxy[0][1]),
                x2=float(box.xyxy[0][2]),
                y2=float(box.xyxy[0][3]),
            ))
        
        return boxes
    
    def is_lshape_pattern(
        self,
        df: pl.DataFrame,
        idx: int,
        ma_columns: list[str] | None = None,
        require_all_components: bool = True,
    ) -> tuple[bool, float, list[DetectionBox]]:
        boxes = self.detect(df, idx, ma_columns)
        
        if not boxes:
            return False, 0.0, []
        
        found_classes = {box.class_name for box in boxes}
        required = {"lshape_drop", "lshape_consolidation", "lshape_breakout"}
        
        if require_all_components:
            is_pattern = required.issubset(found_classes)
        else:
            is_pattern = len(found_classes.intersection(required)) >= 2
        
        avg_confidence = sum(box.confidence for box in boxes) / len(boxes)
        
        return is_pattern, avg_confidence, boxes
