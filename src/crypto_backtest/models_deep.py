from dataclasses import dataclass

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@dataclass
class CNNConfig:
    input_channels: int = 3
    image_size: tuple[int, int] = (64, 64)
    num_classes: int = 2
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 50
    dropout: float = 0.3


if HAS_TORCH:
    class CandleCNN(nn.Module):
        def __init__(self, config: CNNConfig):
            super().__init__()
            self.config = config
            
            self.conv1 = nn.Conv2d(config.input_channels, 32, kernel_size=3, padding=1)
            self.bn1 = nn.BatchNorm2d(32)
            self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
            self.bn2 = nn.BatchNorm2d(64)
            self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
            self.bn3 = nn.BatchNorm2d(128)
            self.conv4 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
            self.bn4 = nn.BatchNorm2d(256)
            
            self.pool = nn.MaxPool2d(2, 2)
            self.dropout = nn.Dropout(config.dropout)
            
            h, w = config.image_size
            final_h = h // 16
            final_w = w // 16
            
            self.fc1 = nn.Linear(256 * final_h * final_w, 256)
            self.fc2 = nn.Linear(256, 64)
            self.fc3 = nn.Linear(64, config.num_classes)
        
        def forward(self, x):
            x = self.pool(F.relu(self.bn1(self.conv1(x))))
            x = self.pool(F.relu(self.bn2(self.conv2(x))))
            x = self.pool(F.relu(self.bn3(self.conv3(x))))
            x = self.pool(F.relu(self.bn4(self.conv4(x))))
            
            x = x.view(x.size(0), -1)
            
            x = F.relu(self.fc1(x))
            x = self.dropout(x)
            x = F.relu(self.fc2(x))
            x = self.dropout(x)
            x = self.fc3(x)
            
            return x


    class MultiScaleCNN(nn.Module):
        def __init__(self, config: CNNConfig):
            super().__init__()
            self.config = config
            
            self.branch3 = self._make_branch(config.input_channels, 3)
            self.branch5 = self._make_branch(config.input_channels, 5)
            self.branch7 = self._make_branch(config.input_channels, 7)
            
            self.fusion = nn.Conv2d(128 * 3, 256, kernel_size=1)
            self.bn_fusion = nn.BatchNorm2d(256)
            
            self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
            
            self.fc1 = nn.Linear(256, 128)
            self.fc2 = nn.Linear(128, config.num_classes)
            self.dropout = nn.Dropout(config.dropout)
        
        def _make_branch(self, in_channels: int, kernel_size: int) -> nn.Sequential:
            padding = kernel_size // 2
            return nn.Sequential(
                nn.Conv2d(in_channels, 32, kernel_size, padding=padding),
                nn.BatchNorm2d(32),
                nn.GELU(),
                nn.Conv2d(32, 64, kernel_size, padding=padding),
                nn.BatchNorm2d(64),
                nn.GELU(),
                nn.MaxPool2d(2, 2),
                nn.Conv2d(64, 128, kernel_size, padding=padding),
                nn.BatchNorm2d(128),
                nn.GELU(),
                nn.MaxPool2d(2, 2),
            )
        
        def forward(self, x):
            b3 = self.branch3(x)
            b5 = self.branch5(x)
            b7 = self.branch7(x)
            
            fused = torch.cat([b3, b5, b7], dim=1)
            fused = F.gelu(self.bn_fusion(self.fusion(fused)))
            
            pooled = self.global_pool(fused)
            pooled = pooled.view(pooled.size(0), -1)
            
            x = F.relu(self.fc1(pooled))
            x = self.dropout(x)
            x = self.fc2(x)
            
            return x


    class LSTMClassifier(nn.Module):
        def __init__(self, input_size: int = 5, hidden_size: int = 32, num_layers: int = 2, num_classes: int = 2, dropout: float = 0.2):
            super().__init__()
            
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
                bidirectional=True,
            )
            
            self.fc1 = nn.Linear(hidden_size * 2, 64)
            self.fc2 = nn.Linear(64, num_classes)
            self.dropout = nn.Dropout(dropout)
        
        def forward(self, x):
            lstm_out, _ = self.lstm(x)
            last_hidden = lstm_out[:, -1, :]
            
            x = F.relu(self.fc1(last_hidden))
            x = self.dropout(x)
            x = self.fc2(x)
            
            return x


def train_cnn_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    config: CNNConfig | None = None,
    model_class: str = "simple",
) -> dict | None:
    if not HAS_TORCH:
        return None
    
    if config is None:
        config = CNNConfig()
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.LongTensor(y_test)
    
    train_dataset = TensorDataset(X_train_t, y_train_t)
    test_dataset = TensorDataset(X_test_t, y_test_t)
    
    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=config.batch_size)
    
    if model_class == "multiscale":
        model = MultiScaleCNN(config).to(device)
        model_name = "MultiScaleCNN"
    else:
        model = CandleCNN(config).to(device)
        model_name = "CandleCNN"
    
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    weight = torch.FloatTensor([1.0, neg_count / pos_count if pos_count > 0 else 1.0]).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config.epochs)
    
    best_acc = 0.0
    best_model_state = None
    patience = 10
    patience_counter = 0
    
    for epoch in range(config.epochs):
        model.train()
        train_loss = 0.0
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        scheduler.step()
        
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
        
        acc = correct / total
        
        if acc > best_acc:
            best_acc = acc
            best_model_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
        
        if patience_counter >= patience:
            break
    
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    model.eval()
    all_preds = []
    all_probs = []
    
    with torch.no_grad():
        for batch_x, _ in test_loader:
            batch_x = batch_x.to(device)
            outputs = model(batch_x)
            probs = F.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs.data, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_probs.extend(probs[:, 1].cpu().numpy())
    
    y_pred = np.array(all_preds)
    y_proba = np.array(all_probs)
    
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
    
    metrics = {
        "model_name": model_name,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "train_samples": len(y_train),
        "test_samples": len(y_test),
    }
    
    if len(np.unique(y_test)) > 1:
        try:
            metrics["auc_roc"] = roc_auc_score(y_test, y_proba)
        except ValueError:
            metrics["auc_roc"] = 0.0
    else:
        metrics["auc_roc"] = 0.0
    
    return metrics


def train_lstm_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    hidden_size: int = 32,
    num_layers: int = 2,
    epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 0.001,
) -> dict | None:
    if not HAS_TORCH:
        return None
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    input_size = X_train.shape[2]
    
    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.LongTensor(y_train)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.LongTensor(y_test)
    
    train_dataset = TensorDataset(X_train_t, y_train_t)
    test_dataset = TensorDataset(X_test_t, y_test_t)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)
    
    model = LSTMClassifier(
        input_size=input_size,
        hidden_size=hidden_size,
        num_layers=num_layers,
    ).to(device)
    
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    weight = torch.FloatTensor([1.0, neg_count / pos_count if pos_count > 0 else 1.0]).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    best_acc = 0.0
    best_model_state = None
    patience = 10
    patience_counter = 0
    
    for epoch in range(epochs):
        model.train()
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
        
        scheduler.step()
        
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
        
        acc = correct / total
        
        if acc > best_acc:
            best_acc = acc
            best_model_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
        
        if patience_counter >= patience:
            break
    
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    model.eval()
    all_preds = []
    all_probs = []
    
    with torch.no_grad():
        for batch_x, _ in test_loader:
            batch_x = batch_x.to(device)
            outputs = model(batch_x)
            probs = F.softmax(outputs, dim=1)
            _, predicted = torch.max(outputs.data, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_probs.extend(probs[:, 1].cpu().numpy())
    
    y_pred = np.array(all_preds)
    y_proba = np.array(all_probs)
    
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
    
    metrics = {
        "model_name": "BiLSTM",
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "train_samples": len(y_train),
        "test_samples": len(y_test),
    }
    
    if len(np.unique(y_test)) > 1:
        try:
            metrics["auc_roc"] = roc_auc_score(y_test, y_proba)
        except ValueError:
            metrics["auc_roc"] = 0.0
    else:
        metrics["auc_roc"] = 0.0
    
    return metrics
