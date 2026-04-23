import json
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl


def generate_backtest_summary(trades_df: pl.DataFrame, config: dict) -> dict:
    if trades_df.is_empty():
        return {"error": "No trades generated"}
    
    total = len(trades_df)
    sl_trades = trades_df.filter(pl.col("is_sl") == True)
    tp_trades = trades_df.filter(pl.col("is_sl") == False)
    
    sl_count = len(sl_trades)
    tp_count = len(tp_trades)
    
    profit_pcts = trades_df["profit_pct"].to_list()
    total_profit = sum(profit_pcts)
    avg_profit = total_profit / total if total > 0 else 0
    
    winning = [p for p in profit_pcts if p > 0]
    losing = [p for p in profit_pcts if p <= 0]
    
    avg_win = sum(winning) / len(winning) if winning else 0
    avg_loss = sum(losing) / len(losing) if losing else 0
    
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for pct in profit_pcts:
        cumulative += pct
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)
    
    return {
        "config": config,
        "total_trades": total,
        "sl_trades": sl_count,
        "tp_trades": tp_count,
        "sl_rate": sl_count / total * 100 if total > 0 else 0,
        "win_rate": len(winning) / total * 100 if total > 0 else 0,
        "total_profit_pct": total_profit,
        "avg_profit_pct": avg_profit,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "max_drawdown_pct": max_dd,
        "profit_factor": abs(sum(winning) / sum(losing)) if losing and sum(losing) != 0 else float("inf"),
    }


def generate_ml_comparison(results: list[dict]) -> dict:
    if not results:
        return {"error": "No ML results"}
    
    comparison = {
        "models": [],
        "best_accuracy": None,
        "best_f1": None,
        "best_auc": None,
    }
    
    best_acc = 0
    best_f1 = 0
    best_auc = 0
    
    for r in results:
        model_summary = {
            "name": r.get("model_name", "Unknown"),
            "accuracy": r.get("accuracy", 0),
            "precision": r.get("precision", 0),
            "recall": r.get("recall", 0),
            "f1": r.get("f1", 0),
            "auc_roc": r.get("auc_roc", 0),
        }
        comparison["models"].append(model_summary)
        
        if r.get("accuracy", 0) > best_acc:
            best_acc = r.get("accuracy", 0)
            comparison["best_accuracy"] = r.get("model_name")
        
        if r.get("f1", 0) > best_f1:
            best_f1 = r.get("f1", 0)
            comparison["best_f1"] = r.get("model_name")
        
        if r.get("auc_roc", 0) > best_auc:
            best_auc = r.get("auc_roc", 0)
            comparison["best_auc"] = r.get("model_name")
    
    return comparison


def format_markdown_report(
    backtest_summary: dict,
    ml_comparison: dict,
    feature_importance: list[tuple[str, float]] | None = None,
) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# Crypto Backtest & ML Analysis Report

Generated: {timestamp}

## 1. Backtest Configuration

| Parameter | Value |
|-----------|-------|
"""
    
    config = backtest_summary.get("config", {})
    for key, value in config.items():
        report += f"| {key} | {value} |\n"
    
    report += f"""
## 2. Backtest Results Summary

### Trade Statistics

| Metric | Value |
|--------|-------|
| Total Trades | {backtest_summary.get('total_trades', 0)} |
| Stop Loss Trades | {backtest_summary.get('sl_trades', 0)} |
| Take Profit Trades | {backtest_summary.get('tp_trades', 0)} |
| SL Rate | {backtest_summary.get('sl_rate', 0):.2f}% |
| Win Rate | {backtest_summary.get('win_rate', 0):.2f}% |

### Profitability

| Metric | Value |
|--------|-------|
| Total Profit | {backtest_summary.get('total_profit_pct', 0):.2f}% |
| Avg Profit per Trade | {backtest_summary.get('avg_profit_pct', 0):.4f}% |
| Avg Win | {backtest_summary.get('avg_win_pct', 0):.4f}% |
| Avg Loss | {backtest_summary.get('avg_loss_pct', 0):.4f}% |
| Max Drawdown | {backtest_summary.get('max_drawdown_pct', 0):.2f}% |
| Profit Factor | {backtest_summary.get('profit_factor', 0):.2f} |

## 3. ML Model Comparison

### Model Performance

| Model | Accuracy | Precision | Recall | F1 | AUC-ROC |
|-------|----------|-----------|--------|----|---------|\n"""
    
    for model in ml_comparison.get("models", []):
        report += f"| {model['name']} | {model['accuracy']:.4f} | {model['precision']:.4f} | {model['recall']:.4f} | {model['f1']:.4f} | {model['auc_roc']:.4f} |\n"
    
    report += f"""
### Best Models

- **Best Accuracy**: {ml_comparison.get('best_accuracy', 'N/A')}
- **Best F1 Score**: {ml_comparison.get('best_f1', 'N/A')}
- **Best AUC-ROC**: {ml_comparison.get('best_auc', 'N/A')}
"""
    
    if feature_importance:
        report += """
## 4. Top Feature Importance

| Rank | Feature | Importance |
|------|---------|------------|\n"""
        for i, (name, score) in enumerate(feature_importance[:20], 1):
            report += f"| {i} | {name} | {score:.6f} |\n"
    
    report += """
## 5. Analysis & Conclusions

### Strategy Viability

"""
    
    win_rate = backtest_summary.get('win_rate', 0)
    profit_factor = backtest_summary.get('profit_factor', 0)
    total_profit = backtest_summary.get('total_profit_pct', 0)
    
    if total_profit > 0 and profit_factor > 1.5:
        report += "**POSITIVE**: The strategy shows potential profitability.\n\n"
    elif total_profit > 0:
        report += "**MARGINAL**: The strategy is marginally profitable but needs optimization.\n\n"
    else:
        report += "**NEGATIVE**: The strategy is not profitable in current form.\n\n"
    
    report += "### ML Prediction Capability\n\n"
    
    best_acc_model = max(ml_comparison.get("models", [{}]), key=lambda x: x.get("accuracy", 0), default={})
    best_acc = best_acc_model.get("accuracy", 0)
    
    if best_acc > 0.6:
        report += f"**PROMISING**: Best model achieves {best_acc:.2%} accuracy, suggesting predictable patterns exist.\n\n"
    elif best_acc > 0.55:
        report += f"**MODERATE**: Best model achieves {best_acc:.2%} accuracy, slightly better than random.\n\n"
    else:
        report += f"**WEAK**: Best model achieves {best_acc:.2%} accuracy, near random baseline.\n\n"
    
    report += """### Recommendations

1. **If Profitable**: 
   - Use ML to filter low-confidence trades
   - Focus on features with high importance
   - Consider ensemble of top models

2. **If Not Profitable**:
   - Adjust entry/exit parameters
   - Test different MA periods for resistance
   - Consider adding trend filters

3. **For ML Improvement**:
   - Add more technical indicators
   - Try different lookback windows
   - Consider regime-based models (bull/bear market separation)
"""
    
    return report


def save_report(report: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def generate_full_report(
    trades_df: pl.DataFrame,
    config: dict,
    ml_results: list[dict],
    feature_importance: list[tuple[str, float]] | None,
    output_path: Path,
) -> str:
    backtest_summary = generate_backtest_summary(trades_df, config)
    ml_comparison = generate_ml_comparison(ml_results)
    
    report = format_markdown_report(backtest_summary, ml_comparison, feature_importance)
    save_report(report, output_path)
    
    return report
