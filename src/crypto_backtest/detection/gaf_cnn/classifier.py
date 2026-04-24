"""
GAF (Gramian Angular Field) + CNN Classifier for L-Shape Detection

Converts time series to images using pyts, then classifies with CNN.
Based on arXiv:1901.05237 achieving 90.7% accuracy on candlestick patterns.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import polars as pl

try:
    from pyts.image import GramianAngularField
    HAS_PYTS = True
except ImportError:
    HAS_PYTS = False

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@dataclass
class GAFConfig:
    window_size: int = 64
    image_size: int = 64
    gaf_method: Literal["summation", "difference"] = "summation"
    channels: list[str] | None = None  # ["close", "volume"] etc
    
    cnn_filters: list[int] | None = None
    dropout: float = 0.3
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 50
    
    device: str = "cuda" if HAS_TORCH and torch.cuda.is_available() else "cpu"
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = ["close"]
        if self.cnn_filters is None:
            self.cnn_filters = [32, 64, 128]


class GAFTransformer:
    def __init__(self, config: GAFConfig):
        if not HAS_PYTS:
            raise ImportError("pyts required: pip install pyts")
        
        self.config = config
        self.gaf = GramianAngularField(
            image_size=config.image_size,
            method=config.gaf_method,
        )
    
    def transform_window(self, window: np.ndarray) -> np.ndarray:
        normalized = (window - window.min()) / (window.max() - window.min() + 1e-8)
        gaf_image = self.gaf.fit_transform(normalized.reshape(1, -1))
        return gaf_image[0]
    
    def transform_ohlcv(
        self,
        df: pl.DataFrame,
        idx: int,
    ) -> np.ndarray:
        window_size = self.config.window_size
        if idx < window_size:
            raise ValueError(f"idx {idx} < window_size {window_size}")
        
        window = df.slice(idx - window_size, window_size)
        
        channels = []
        for col in self.config.channels:
            if col not in window.columns:
                raise ValueError(f"Column {col} not found")
            
            values = window[col].to_numpy().astype(np.float32)
            gaf_image = self.transform_window(values)
            channels.append(gaf_image)
        
        return np.stack(channels, axis=0)
    
    def transform_batch(
        self,
        df: pl.DataFrame,
        indices: list[int],
    ) -> np.ndarray:
        images = []
        for idx in indices:
            try:
                img = self.transform_ohlcv(df, idx)
                images.append(img)
            except ValueError:
                continue
        
        return np.stack(images, axis=0) if images else np.array([])


class LShapeCNN(nn.Module):
    def __init__(self, config: GAFConfig):
        super().__init__()
        
        n_channels = len(config.channels)
        filters = config.cnn_filters
        
        layers = []
        in_ch = n_channels
        
        for out_ch in filters:
            layers.extend([
                nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
                nn.BatchNorm2d(out_ch),
                nn.ReLU(),
                nn.MaxPool2d(2),
            ])
            in_ch = out_ch
        
        self.conv = nn.Sequential(*layers)
        
        final_size = config.image_size // (2 ** len(filters))
        fc_input = filters[-1] * final_size * final_size
        
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(fc_input, 128),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(128, 2),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        x = self.fc(x)
        return x


class GAFDataset(Dataset):
    def __init__(self, images: np.ndarray, labels: np.ndarray):
        self.images = torch.FloatTensor(images)
        self.labels = torch.LongTensor(labels)
    
    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, idx):
        return self.images[idx], self.labels[idx]


class GAFClassifier:
    def __init__(self, config: GAFConfig | None = None):
        if not HAS_TORCH:
            raise ImportError("PyTorch required: pip install torch")
        
        self.config = config or GAFConfig()
        self.transformer = GAFTransformer(self.config)
        self.model = None
    
    def prepare_data(
        self,
        df: pl.DataFrame,
        positive_indices: list[int],
        negative_indices: list[int],
    ) -> tuple[np.ndarray, np.ndarray]:
        pos_images = self.transformer.transform_batch(df, positive_indices)
        neg_images = self.transformer.transform_batch(df, negative_indices)
        
        pos_labels = np.ones(len(pos_images), dtype=np.int64)
        neg_labels = np.zeros(len(neg_images), dtype=np.int64)
        
        images = np.concatenate([pos_images, neg_images], axis=0)
        labels = np.concatenate([pos_labels, neg_labels], axis=0)
        
        shuffle_idx = np.random.permutation(len(labels))
        return images[shuffle_idx], labels[shuffle_idx]
    
    def train(
        self,
        df: pl.DataFrame,
        positive_indices: list[int],
        negative_indices: list[int],
        val_split: float = 0.2,
    ) -> dict:
        images, labels = self.prepare_data(df, positive_indices, negative_indices)
        
        n_val = int(len(labels) * val_split)
        train_images, val_images = images[n_val:], images[:n_val]
        train_labels, val_labels = labels[n_val:], labels[:n_val]
        
        train_dataset = GAFDataset(train_images, train_labels)
        val_dataset = GAFDataset(val_images, val_labels)
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
        )
        
        self.model = LShapeCNN(self.config).to(self.config.device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        
        history = {"train_loss": [], "val_loss": [], "val_acc": []}
        best_acc = 0.0
        
        for epoch in range(self.config.epochs):
            self.model.train()
            train_loss = 0.0
            
            for images_batch, labels_batch in train_loader:
                images_batch = images_batch.to(self.config.device)
                labels_batch = labels_batch.to(self.config.device)
                
                optimizer.zero_grad()
                outputs = self.model(images_batch)
                loss = criterion(outputs, labels_batch)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
            
            self.model.eval()
            val_loss = 0.0
            correct = 0
            total = 0
            
            with torch.no_grad():
                for images_batch, labels_batch in val_loader:
                    images_batch = images_batch.to(self.config.device)
                    labels_batch = labels_batch.to(self.config.device)
                    
                    outputs = self.model(images_batch)
                    loss = criterion(outputs, labels_batch)
                    val_loss += loss.item()
                    
                    _, predicted = torch.max(outputs, 1)
                    total += labels_batch.size(0)
                    correct += (predicted == labels_batch).sum().item()
            
            val_acc = correct / total if total > 0 else 0.0
            
            history["train_loss"].append(train_loss / len(train_loader))
            history["val_loss"].append(val_loss / len(val_loader))
            history["val_acc"].append(val_acc)
            
            if val_acc > best_acc:
                best_acc = val_acc
            
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{self.config.epochs}: "
                      f"train_loss={train_loss/len(train_loader):.4f}, "
                      f"val_acc={val_acc:.4f}")
        
        history["best_acc"] = best_acc
        return history
    
    def predict(self, df: pl.DataFrame, idx: int) -> tuple[bool, float]:
        if self.model is None:
            raise ValueError("Model not trained")
        
        self.model.eval()
        
        image = self.transformer.transform_ohlcv(df, idx)
        image_tensor = torch.FloatTensor(image).unsqueeze(0).to(self.config.device)
        
        with torch.no_grad():
            outputs = self.model(image_tensor)
            probs = torch.softmax(outputs, dim=1)
            is_lshape = probs[0, 1] > probs[0, 0]
            confidence = probs[0, 1].item()
        
        return bool(is_lshape), confidence
    
    def predict_batch(
        self,
        df: pl.DataFrame,
        indices: list[int],
    ) -> list[tuple[int, bool, float]]:
        results = []
        for idx in indices:
            try:
                is_lshape, confidence = self.predict(df, idx)
                results.append((idx, is_lshape, confidence))
            except ValueError:
                continue
        return results
    
    def save(self, path: Path) -> None:
        if self.model is None:
            raise ValueError("Model not trained")
        
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state": self.model.state_dict(),
            "config": self.config,
        }, path)
    
    def load(self, path: Path) -> None:
        checkpoint = torch.load(path, map_location=self.config.device)
        self.config = checkpoint["config"]
        self.transformer = GAFTransformer(self.config)
        self.model = LShapeCNN(self.config).to(self.config.device)
        self.model.load_state_dict(checkpoint["model_state"])
