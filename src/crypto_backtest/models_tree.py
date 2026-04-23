import json
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


@dataclass
class ModelResult:
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc_roc: float
    train_samples: int
    test_samples: int
    feature_importance: dict[str, float] | None = None
    hyperparams: dict | None = None
    
    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "auc_roc": self.auc_roc,
            "train_samples": self.train_samples,
            "test_samples": self.test_samples,
        }


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray | None = None) -> dict:
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    
    if y_proba is not None and len(np.unique(y_true)) > 1:
        try:
            metrics["auc_roc"] = roc_auc_score(y_true, y_proba)
        except ValueError:
            metrics["auc_roc"] = 0.0
    else:
        metrics["auc_roc"] = 0.0
    
    return metrics


def train_logistic_regression(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str] | None = None,
) -> ModelResult:
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )
    model.fit(X_train_scaled, y_train)
    
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    metrics = evaluate_predictions(y_test, y_pred, y_proba)
    
    importance = None
    if feature_names:
        coef = np.abs(model.coef_[0])
        importance = {name: float(c) for name, c in zip(feature_names, coef)}
    
    return ModelResult(
        model_name="LogisticRegression",
        accuracy=metrics["accuracy"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        f1=metrics["f1"],
        auc_roc=metrics["auc_roc"],
        train_samples=len(y_train),
        test_samples=len(y_test),
        feature_importance=importance,
        hyperparams={"max_iter": 1000, "class_weight": "balanced"},
    )


def train_random_forest(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str] | None = None,
) -> ModelResult:
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_split=20,
        min_samples_leaf=10,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = evaluate_predictions(y_test, y_pred, y_proba)
    
    importance = None
    if feature_names:
        importance = {name: float(imp) for name, imp in zip(feature_names, model.feature_importances_)}
    
    return ModelResult(
        model_name="RandomForest",
        accuracy=metrics["accuracy"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        f1=metrics["f1"],
        auc_roc=metrics["auc_roc"],
        train_samples=len(y_train),
        test_samples=len(y_test),
        feature_importance=importance,
        hyperparams={
            "n_estimators": 200,
            "max_depth": 6,
            "min_samples_split": 20,
            "min_samples_leaf": 10,
        },
    )


def train_xgboost(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str] | None = None,
) -> ModelResult | None:
    if not HAS_XGBOOST:
        return None
    
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
    
    model = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.03,
        min_child_weight=10,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.3,
        reg_lambda=1.5,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        early_stopping_rounds=80,
        random_state=42,
        n_jobs=-1,
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = evaluate_predictions(y_test, y_pred, y_proba)
    
    importance = None
    if feature_names:
        importance = {name: float(imp) for name, imp in zip(feature_names, model.feature_importances_)}
    
    return ModelResult(
        model_name="XGBoost",
        accuracy=metrics["accuracy"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        f1=metrics["f1"],
        auc_roc=metrics["auc_roc"],
        train_samples=len(y_train),
        test_samples=len(y_test),
        feature_importance=importance,
        hyperparams={
            "n_estimators": 500,
            "max_depth": 4,
            "learning_rate": 0.03,
            "scale_pos_weight": scale_pos_weight,
        },
    )


def train_lightgbm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str] | None = None,
) -> ModelResult | None:
    if not HAS_LIGHTGBM:
        return None
    
    model = lgb.LGBMClassifier(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.03,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.3,
        reg_lambda=1.5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
    )
    
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    
    metrics = evaluate_predictions(y_test, y_pred, y_proba)
    
    importance = None
    if feature_names:
        importance = {name: float(imp) for name, imp in zip(feature_names, model.feature_importances_)}
    
    return ModelResult(
        model_name="LightGBM",
        accuracy=metrics["accuracy"],
        precision=metrics["precision"],
        recall=metrics["recall"],
        f1=metrics["f1"],
        auc_roc=metrics["auc_roc"],
        train_samples=len(y_train),
        test_samples=len(y_test),
        feature_importance=importance,
        hyperparams={
            "n_estimators": 500,
            "max_depth": 4,
            "learning_rate": 0.03,
        },
    )


def walk_forward_validation(
    X: np.ndarray,
    y: np.ndarray,
    train_size: int = 1500,
    test_size: int = 200,
    feature_names: list[str] | None = None,
) -> list[dict]:
    results = []
    n = len(X)
    
    i = 0
    fold = 0
    while i + train_size + test_size <= n:
        train_end = i + train_size
        test_end = train_end + test_size
        
        X_train, y_train = X[i:train_end], y[i:train_end]
        X_test, y_test = X[train_end:test_end], y[train_end:test_end]
        
        if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
            i += test_size
            fold += 1
            continue
        
        fold_results = {
            "fold": fold,
            "train_start": i,
            "train_end": train_end,
            "test_start": train_end,
            "test_end": test_end,
            "models": [],
        }
        
        lr_result = train_logistic_regression(X_train, y_train, X_test, y_test, feature_names)
        fold_results["models"].append(lr_result.to_dict())
        
        rf_result = train_random_forest(X_train, y_train, X_test, y_test, feature_names)
        fold_results["models"].append(rf_result.to_dict())
        
        if HAS_XGBOOST:
            xgb_result = train_xgboost(X_train, y_train, X_test, y_test, feature_names)
            if xgb_result:
                fold_results["models"].append(xgb_result.to_dict())
        
        if HAS_LIGHTGBM:
            lgb_result = train_lightgbm(X_train, y_train, X_test, y_test, feature_names)
            if lgb_result:
                fold_results["models"].append(lgb_result.to_dict())
        
        results.append(fold_results)
        
        i += test_size
        fold += 1
    
    return results


def train_all_models(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str] | None = None,
    test_ratio: float = 0.2,
) -> list[ModelResult]:
    split_idx = int(len(X) * (1 - test_ratio))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    if len(np.unique(y_train)) < 2 or len(np.unique(y_test)) < 2:
        return []
    
    results = []
    
    results.append(train_logistic_regression(X_train, y_train, X_test, y_test, feature_names))
    results.append(train_random_forest(X_train, y_train, X_test, y_test, feature_names))
    
    if HAS_XGBOOST:
        xgb_result = train_xgboost(X_train, y_train, X_test, y_test, feature_names)
        if xgb_result:
            results.append(xgb_result)
    
    if HAS_LIGHTGBM:
        lgb_result = train_lightgbm(X_train, y_train, X_test, y_test, feature_names)
        if lgb_result:
            results.append(lgb_result)
    
    return results


def get_top_features(results: list[ModelResult], top_n: int = 20) -> list[tuple[str, float]]:
    feature_scores = {}
    
    for result in results:
        if result.feature_importance:
            for name, score in result.feature_importance.items():
                if name not in feature_scores:
                    feature_scores[name] = []
                feature_scores[name].append(score)
    
    avg_scores = {name: np.mean(scores) for name, scores in feature_scores.items()}
    sorted_features = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_features[:top_n]
