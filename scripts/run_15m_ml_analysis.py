#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_backtest.data_loader import BacktestConfig, load_15min_data
from crypto_backtest.features import prepare_ml_features
from crypto_backtest.long_strategy import LongStrategyConfig, LongBacktestEngine
from crypto_backtest.models_tree import (
    train_all_models,
    get_top_features,
    walk_forward_validation,
)

DATA_PATH = Path("/mnt/data/finance/cryptocurrency")
OUTPUT_DIR = Path(__file__).parent.parent / "docs"


def run_ml_analysis():
    print("=" * 60)
    print("15분봉 ML Analysis")
    print("=" * 60)
    
    best_params = {
        "ma": 50, 
        "consolidation_bars": 8, 
        "consolidation_range_pct": 2.0, 
        "drop_threshold_pct": 2.0, 
        "take_profit_pct": 5.0, 
        "stop_loss_pct": 2.0
    }
    
    print(f"\nUsing parameters (balanced risk-adjusted):")
    for k, v in best_params.items():
        print(f"  {k}: {v}")
    
    print("\n[1/4] Loading 15-minute data...")
    data_config = BacktestConfig(
        data_path=DATA_PATH,
        symbol="BTCUSDT",
        timeframe="15m",
        ma_periods=[25, 50, 100, 200, 400],
    )
    data = load_15min_data(data_config)
    print(f"  Loaded {len(data):,} candles")
    print(f"  Date range: {data['datetime'].min()} to {data['datetime'].max()}")
    
    print("\n[2/4] Running backtest with selected parameters...")
    strategy_config = LongStrategyConfig(
        data_path=DATA_PATH,
        symbol="BTCUSDT",
        timeframe="15m",
        breakout_ma=best_params["ma"],
        consolidation_bars=best_params["consolidation_bars"],
        consolidation_range_pct=best_params["consolidation_range_pct"],
        drop_threshold_pct=best_params["drop_threshold_pct"],
        take_profit_pct=best_params["take_profit_pct"],
        stop_loss_pct=best_params["stop_loss_pct"],
        half_close_enabled=False,
    )
    
    engine = LongBacktestEngine(strategy_config)
    engine.run(data)
    trades_df = engine.get_trades_df()
    print(f"  Total trades: {len(trades_df)}")
    
    if len(trades_df) == 0:
        print("No trades generated. Exiting.")
        return
    
    sl_count = trades_df.filter(pl.col("is_sl") == True).height
    tp_count = trades_df.filter(pl.col("is_sl") == False).height
    print(f"  SL trades: {sl_count} ({sl_count/len(trades_df)*100:.1f}%)")
    print(f"  TP trades: {tp_count} ({tp_count/len(trades_df)*100:.1f}%)")
    
    print("\n[3/4] Preparing ML features...")
    X, y, feature_names = prepare_ml_features(data, trades_df, lookback=20)
    print(f"  Feature matrix shape: {X.shape}")
    print(f"  Feature count: {len(feature_names)}")
    print(f"  Samples: {len(y)}")
    print(f"  Class distribution: SL={np.sum(y==1)} ({np.mean(y)*100:.1f}%), TP={np.sum(y==0)} ({(1-np.mean(y))*100:.1f}%)")
    
    if len(y) < 50:
        print("Not enough samples for ML. Exiting.")
        return
    
    print("\n[4/4] Training ML models...")
    results = train_all_models(X, y, feature_names, test_ratio=0.2)
    
    print("\n" + "=" * 60)
    print("ML RESULTS (15-minute timeframe)")
    print("=" * 60)
    
    ml_results = []
    for r in results:
        print(f"\n{r.model_name}:")
        print(f"  Accuracy:  {r.accuracy:.4f}")
        print(f"  Precision: {r.precision:.4f}")
        print(f"  Recall:    {r.recall:.4f}")
        print(f"  F1 Score:  {r.f1:.4f}")
        print(f"  AUC-ROC:   {r.auc_roc:.4f}")
        print(f"  Train/Test: {r.train_samples}/{r.test_samples}")
        
        ml_results.append({
            "model": r.model_name,
            "accuracy": r.accuracy,
            "precision": r.precision,
            "recall": r.recall,
            "f1": r.f1,
            "auc_roc": r.auc_roc,
            "train_samples": r.train_samples,
            "test_samples": r.test_samples,
        })
    
    print("\n" + "-" * 40)
    print("TOP 20 FEATURES:")
    print("-" * 40)
    top_features = get_top_features(results, top_n=20)
    for i, (name, score) in enumerate(top_features, 1):
        print(f"  {i:2d}. {name}: {score:.6f}")
    
    print("\n" + "-" * 40)
    print("WALK-FORWARD VALIDATION:")
    print("-" * 40)
    
    train_size = min(500, len(X) // 3)
    test_size = min(100, len(X) // 10)
    
    wf_results = walk_forward_validation(
        X, y,
        train_size=train_size,
        test_size=test_size,
        feature_names=feature_names,
    )
    
    if wf_results:
        print(f"  Folds: {len(wf_results)}")
        
        wf_aucs = {}
        for fold in wf_results:
            for model in fold["models"]:
                name = model["model_name"]
                if name not in wf_aucs:
                    wf_aucs[name] = []
                wf_aucs[name].append(model["auc_roc"])
        
        print("\n  Walk-Forward AUC-ROC (mean ± std):")
        for name, aucs in wf_aucs.items():
            print(f"    {name}: {np.mean(aucs):.4f} ± {np.std(aucs):.4f}")
    
    print("\n" + "=" * 60)
    print("SAVING RESULTS...")
    print("=" * 60)
    
    ml_df = pl.DataFrame(ml_results)
    ml_csv_path = OUTPUT_DIR / "15min_ml_results.csv"
    ml_df.write_csv(ml_csv_path)
    print(f"  ML results: {ml_csv_path}")
    
    feature_importance = {name: score for name, score in top_features}
    fi_path = OUTPUT_DIR / "15min_feature_importance.json"
    with open(fi_path, "w") as f:
        json.dump(feature_importance, f, indent=2)
    print(f"  Feature importance: {fi_path}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  15m samples: {len(y):,}")
    print(f"  15m best AUC: {max(r.auc_roc for r in results):.4f}")


if __name__ == "__main__":
    run_ml_analysis()
