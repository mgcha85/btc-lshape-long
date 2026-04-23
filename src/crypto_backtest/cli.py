import json
from pathlib import Path

import click
import numpy as np

from .backtest_engine import BacktestEngine, run_backtest
from .data_loader import BacktestConfig, load_hourly_data
from .features import (
    add_all_indicators,
    create_candle_images,
    create_candle_sequences,
    prepare_ml_features,
)
from .models_deep import CNNConfig, train_cnn_model, train_lstm_model
from .models_tree import (
    ModelResult,
    get_top_features,
    train_all_models,
    walk_forward_validation,
)
from .report import generate_full_report
from .storage import (
    calculate_stats,
    generate_run_id,
    init_database,
    save_backtest_run,
    save_ml_result,
    save_trades,
)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--data-path", type=click.Path(exists=True), required=True)
@click.option("--symbol", default="BTCUSDT")
@click.option("--resistance-ma", default=25, type=int)
@click.option("--half-close-pct", default=1.0, type=float)
@click.option("--take-profit-pct", default=2.0, type=float)
@click.option("--stop-loss-pct", default=2.0, type=float)
@click.option("--start-date", default=None)
@click.option("--end-date", default=None)
@click.option("--db-path", default="data/backtest.db", type=click.Path())
@click.option("--output-dir", default="docs", type=click.Path())
@click.option("--run-ml/--no-ml", default=True)
@click.option("--lookback", default=20, type=int)
@click.option("--sequence-length", default=50, type=int)
def run(
    data_path: str,
    symbol: str,
    resistance_ma: int,
    half_close_pct: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    start_date: str | None,
    end_date: str | None,
    db_path: str,
    output_dir: str,
    run_ml: bool,
    lookback: int,
    sequence_length: int,
):
    click.echo(f"Loading data from {data_path}...")
    
    config = BacktestConfig(
        data_path=Path(data_path),
        symbol=symbol,
        resistance_ma=resistance_ma,
        half_close_pct=half_close_pct,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        start_date=start_date,
        end_date=end_date,
    )
    
    data = load_hourly_data(config)
    click.echo(f"Loaded {len(data)} hourly candles")
    
    click.echo("Running backtest...")
    engine = BacktestEngine(config)
    engine.run(data)
    trades_df = engine.get_trades_df()
    
    click.echo(f"Generated {len(trades_df)} trades")
    
    db_path_obj = Path(db_path)
    db_path_obj.parent.mkdir(parents=True, exist_ok=True)
    init_database(db_path_obj)
    
    run_id = generate_run_id()
    save_trades(db_path_obj, run_id, trades_df)
    
    stats = calculate_stats(trades_df)
    config_dict = {
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "resistance_ma": config.resistance_ma,
        "half_close_pct": config.half_close_pct,
        "take_profit_pct": config.take_profit_pct,
        "stop_loss_pct": config.stop_loss_pct,
        "start_date": config.start_date,
        "end_date": config.end_date,
    }
    save_backtest_run(db_path_obj, run_id, config_dict, stats)
    
    click.echo(f"Saved to database with run_id: {run_id}")
    click.echo(f"Win rate: {stats['win_rate']:.2f}%")
    click.echo(f"Total profit: {stats['total_profit_pct']:.2f}%")
    
    ml_results = []
    feature_importance = None
    
    if run_ml and len(trades_df) > 100:
        click.echo("\nPreparing ML features...")
        
        data_with_indicators = add_all_indicators(data)
        
        X, y, feature_names = prepare_ml_features(data_with_indicators, trades_df, lookback)
        click.echo(f"Prepared {len(X)} samples with {len(feature_names)} features")
        
        sl_count = np.sum(y == 1)
        tp_count = np.sum(y == 0)
        click.echo(f"Class distribution - SL: {sl_count}, TP: {tp_count}")
        
        if len(X) > 200:
            click.echo("\nTraining tree-based models...")
            tree_results = train_all_models(X, y, feature_names)
            
            for r in tree_results:
                ml_results.append(r.to_dict())
                save_ml_result(
                    db_path_obj,
                    run_id,
                    r.model_name,
                    r.to_dict(),
                    json.dumps(r.hyperparams) if r.hyperparams else None,
                    json.dumps(r.feature_importance) if r.feature_importance else None,
                )
                click.echo(f"  {r.model_name}: Acc={r.accuracy:.4f}, F1={r.f1:.4f}, AUC={r.auc_roc:.4f}")
            
            feature_importance = get_top_features(tree_results, top_n=20)
            
            click.echo("\nPreparing sequence data for deep learning...")
            X_seq, y_seq = create_candle_sequences(data, trades_df, sequence_length)
            
            if len(X_seq) > 100:
                click.echo("Training LSTM model...")
                split_idx = int(len(X_seq) * 0.8)
                lstm_result = train_lstm_model(
                    X_seq[:split_idx], y_seq[:split_idx],
                    X_seq[split_idx:], y_seq[split_idx:],
                )
                if lstm_result:
                    ml_results.append(lstm_result)
                    save_ml_result(db_path_obj, run_id, "BiLSTM", lstm_result)
                    click.echo(f"  BiLSTM: Acc={lstm_result['accuracy']:.4f}, F1={lstm_result['f1']:.4f}")
            
            click.echo("\nPreparing candle images for CNN...")
            X_img, y_img = create_candle_images(data, trades_df, sequence_length)
            
            if len(X_img) > 100:
                click.echo("Training CNN models...")
                split_idx = int(len(X_img) * 0.8)
                
                cnn_config = CNNConfig(epochs=30)
                
                simple_cnn = train_cnn_model(
                    X_img[:split_idx], y_img[:split_idx],
                    X_img[split_idx:], y_img[split_idx:],
                    cnn_config, "simple",
                )
                if simple_cnn:
                    ml_results.append(simple_cnn)
                    save_ml_result(db_path_obj, run_id, "CandleCNN", simple_cnn)
                    click.echo(f"  CandleCNN: Acc={simple_cnn['accuracy']:.4f}, F1={simple_cnn['f1']:.4f}")
                
                multiscale_cnn = train_cnn_model(
                    X_img[:split_idx], y_img[:split_idx],
                    X_img[split_idx:], y_img[split_idx:],
                    cnn_config, "multiscale",
                )
                if multiscale_cnn:
                    ml_results.append(multiscale_cnn)
                    save_ml_result(db_path_obj, run_id, "MultiScaleCNN", multiscale_cnn)
                    click.echo(f"  MultiScaleCNN: Acc={multiscale_cnn['accuracy']:.4f}, F1={multiscale_cnn['f1']:.4f}")
    
    click.echo("\nGenerating report...")
    output_path = Path(output_dir) / f"backtest_report_{run_id}.md"
    
    report = generate_full_report(
        trades_df,
        config_dict,
        ml_results,
        feature_importance,
        output_path,
    )
    
    click.echo(f"Report saved to {output_path}")
    click.echo("\nDone!")


@cli.command()
@click.option("--db-path", default="data/backtest.db", type=click.Path(exists=True))
@click.option("--run-id", default=None)
def show_trades(db_path: str, run_id: str | None):
    from .storage import load_trades
    
    trades = load_trades(Path(db_path), run_id)
    
    if trades.is_empty():
        click.echo("No trades found")
        return
    
    click.echo(trades)


@cli.command()
@click.option("--db-path", default="data/backtest.db", type=click.Path(exists=True))
@click.option("--run-id", default=None)
def show_ml_results(db_path: str, run_id: str | None):
    from .storage import load_ml_results
    
    results = load_ml_results(Path(db_path), run_id)
    
    if results.is_empty():
        click.echo("No ML results found")
        return
    
    click.echo(results)


def main():
    cli()


if __name__ == "__main__":
    main()
