#!/usr/bin/env python3
"""5분봉 DL 분석 스크립트 - CNN, LSTM"""

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crypto_backtest.data_loader import BacktestConfig, load_5min_data
from crypto_backtest.features import create_candle_sequences, create_candle_images
from crypto_backtest.long_strategy import LongStrategyConfig, run_long_backtest
from crypto_backtest.models_deep import (
    CNNConfig,
    train_cnn_model,
    train_lstm_model,
    HAS_TORCH,
)

DATA_PATH = Path("/mnt/data/projects/dantaRang-ai/data/hive_partition")
OUTPUT_DIR = Path(__file__).parent.parent / "docs"


def run_dl_analysis():
    """5분봉 DL 분석 실행"""
    
    if not HAS_TORCH:
        print("PyTorch not available. Skipping DL analysis.")
        return
    
    print("=" * 60)
    print("5분봉 Deep Learning Analysis")
    print("=" * 60)
    
    # Best 5m parameters (risk-adjusted)
    best_params = {
        "ma": 48,
        "consolidation_bars": 6,
        "consolidation_range_pct": 3.0,
        "drop_threshold_pct": 2.0,
        "take_profit_pct": 2.0,
        "stop_loss_pct": 1.5,
    }
    
    print(f"\nParameters: MA{best_params['ma']}/TP{best_params['take_profit_pct']}%/SL{best_params['stop_loss_pct']}%")
    
    # Load 5m data
    print("\n[1/5] Loading 5-minute data...")
    data_config = BacktestConfig(
        data_path=DATA_PATH,
        symbol="BTCUSDT",
        timeframe="5m",
        ma_periods=[24, 48, 100],
    )
    data = load_5min_data(data_config)
    print(f"  Loaded {len(data):,} candles")
    
    # Run backtest
    print("\n[2/5] Running backtest...")
    strategy_config = LongStrategyConfig(
        data_path=DATA_PATH,
        symbol="BTCUSDT",
        timeframe="5m",
        breakout_ma=best_params["ma"],
        consolidation_bars=best_params["consolidation_bars"],
        consolidation_range_pct=best_params["consolidation_range_pct"],
        drop_threshold_pct=best_params["drop_threshold_pct"],
        take_profit_pct=best_params["take_profit_pct"],
        stop_loss_pct=best_params["stop_loss_pct"],
        half_close_enabled=False,
    )
    
    trades_df = run_long_backtest(strategy_config, data)
    print(f"  Total trades: {len(trades_df)}")
    
    if len(trades_df) < 50:
        print("Not enough trades for DL. Exiting.")
        return
    
    sl_count = trades_df.filter(pl.col("is_sl") == True).height
    tp_count = trades_df.filter(pl.col("is_sl") == False).height
    print(f"  SL: {sl_count} ({sl_count/len(trades_df)*100:.1f}%), TP: {tp_count} ({tp_count/len(trades_df)*100:.1f}%)")
    
    # Create candle sequences for LSTM
    print("\n[3/5] Creating candle sequences for LSTM...")
    X_seq, y_seq = create_candle_sequences(data, trades_df, sequence_length=50)
    print(f"  Sequence shape: {X_seq.shape}")
    print(f"  Samples: {len(y_seq)}")
    
    # Create candle images for CNN
    print("\n[4/5] Creating candle images for CNN...")
    X_img, y_img = create_candle_images(data, trades_df, sequence_length=50, image_size=(64, 64))
    print(f"  Image shape: {X_img.shape}")
    print(f"  Samples: {len(y_img)}")
    
    # Train/test split (80/20)
    split_seq = int(len(X_seq) * 0.8)
    split_img = int(len(X_img) * 0.8)
    
    X_seq_train, X_seq_test = X_seq[:split_seq], X_seq[split_seq:]
    y_seq_train, y_seq_test = y_seq[:split_seq], y_seq[split_seq:]
    
    X_img_train, X_img_test = X_img[:split_img], X_img[split_img:]
    y_img_train, y_img_test = y_img[:split_img], y_img[split_img:]
    
    print(f"\n  LSTM Train/Test: {len(y_seq_train)}/{len(y_seq_test)}")
    print(f"  CNN Train/Test: {len(y_img_train)}/{len(y_img_test)}")
    
    # Train models
    print("\n[5/5] Training Deep Learning models...")
    dl_results = []
    
    # BiLSTM
    print("\n  Training BiLSTM...")
    lstm_result = train_lstm_model(
        X_seq_train, y_seq_train,
        X_seq_test, y_seq_test,
        hidden_size=64,
        num_layers=2,
        epochs=100,
        batch_size=32,
        learning_rate=0.001,
    )
    if lstm_result:
        dl_results.append({**lstm_result, "type": "Deep Learning"})
        print(f"    Accuracy: {lstm_result['accuracy']:.4f}, AUC: {lstm_result['auc_roc']:.4f}")
    
    # CandleCNN
    print("\n  Training CandleCNN...")
    cnn_config = CNNConfig(
        input_channels=3,
        image_size=(64, 64),
        num_classes=2,
        learning_rate=0.001,
        batch_size=32,
        epochs=100,
        dropout=0.3,
    )
    cnn_result = train_cnn_model(
        X_img_train, y_img_train,
        X_img_test, y_img_test,
        config=cnn_config,
        model_class="simple",
    )
    if cnn_result:
        dl_results.append({**cnn_result, "type": "Deep Learning"})
        print(f"    Accuracy: {cnn_result['accuracy']:.4f}, AUC: {cnn_result['auc_roc']:.4f}")
    
    # MultiScaleCNN
    print("\n  Training MultiScaleCNN...")
    ms_result = train_cnn_model(
        X_img_train, y_img_train,
        X_img_test, y_img_test,
        config=cnn_config,
        model_class="multiscale",
    )
    if ms_result:
        dl_results.append({**ms_result, "type": "Deep Learning"})
        print(f"    Accuracy: {ms_result['accuracy']:.4f}, AUC: {ms_result['auc_roc']:.4f}")
    
    # Results summary
    print("\n" + "=" * 60)
    print("DEEP LEARNING RESULTS (5-minute)")
    print("=" * 60)
    
    for r in dl_results:
        print(f"\n{r['model_name']}:")
        print(f"  Accuracy:  {r['accuracy']:.4f}")
        print(f"  Precision: {r['precision']:.4f}")
        print(f"  Recall:    {r['recall']:.4f}")
        print(f"  F1 Score:  {r['f1']:.4f}")
        print(f"  AUC-ROC:   {r['auc_roc']:.4f}")
    
    # Save results
    dl_df = pl.DataFrame(dl_results)
    dl_csv_path = OUTPUT_DIR / "5min_dl_results.csv"
    dl_df.write_csv(dl_csv_path)
    print(f"\nResults saved to: {dl_csv_path}")
    
    # Combine with ML results
    ml_csv_path = OUTPUT_DIR / "5min_ml_results.csv"
    if ml_csv_path.exists():
        ml_df = pl.read_csv(ml_csv_path)
        ml_df = ml_df.with_columns(pl.lit("Tree").alias("type"))
        
        combined_df = pl.concat([ml_df, dl_df])
        combined_path = OUTPUT_DIR / "5min_all_ml_results.csv"
        combined_df.write_csv(combined_path)
        print(f"Combined results saved to: {combined_path}")
    
    return dl_results


if __name__ == "__main__":
    run_dl_analysis()
