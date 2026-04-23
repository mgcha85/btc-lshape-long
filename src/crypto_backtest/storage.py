import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import polars as pl


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    open_time TIMESTAMP NOT NULL,
    open_price REAL NOT NULL,
    close_time TIMESTAMP,
    close_price REAL,
    profit REAL,
    profit_pct REAL,
    type TEXT NOT NULL,
    result TEXT,
    is_sl INTEGER,
    half_closed INTEGER,
    half_close_time TIMESTAMP,
    half_close_price REAL,
    half_close_profit_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    resistance_ma INTEGER NOT NULL,
    half_close_pct REAL NOT NULL,
    take_profit_pct REAL NOT NULL,
    stop_loss_pct REAL NOT NULL,
    start_date TEXT,
    end_date TEXT,
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate REAL,
    total_profit_pct REAL,
    avg_profit_pct REAL,
    max_drawdown_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    accuracy REAL,
    precision_score REAL,
    recall REAL,
    f1_score REAL,
    auc_roc REAL,
    train_samples INTEGER,
    test_samples INTEGER,
    feature_importance TEXT,
    hyperparams TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trades_run_id ON trades(run_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_is_sl ON trades(is_sl);
CREATE INDEX IF NOT EXISTS idx_ml_results_run_id ON ml_results(run_id);
"""


@contextmanager
def get_connection(db_path: Path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_database(db_path: Path) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(DB_SCHEMA)


def generate_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_trades(db_path: Path, run_id: str, trades_df: pl.DataFrame) -> None:
    if trades_df.is_empty():
        return
    
    with get_connection(db_path) as conn:
        for row in trades_df.to_dicts():
            conn.execute(
                """
                INSERT INTO trades (
                    run_id, symbol, open_time, open_price, close_time, close_price,
                    profit, profit_pct, type, result, is_sl, half_closed,
                    half_close_time, half_close_price, half_close_profit_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row["symbol"],
                    row["open_time"],
                    row["open_price"],
                    row["close_time"],
                    row["close_price"],
                    row["profit"],
                    row["profit_pct"],
                    row["type"],
                    row["result"],
                    1 if row.get("is_sl") else 0,
                    1 if row.get("half_closed") else 0,
                    row.get("half_close_time"),
                    row.get("half_close_price"),
                    row.get("half_close_profit_pct"),
                ),
            )


def save_backtest_run(
    db_path: Path,
    run_id: str,
    config: dict,
    stats: dict,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO backtest_runs (
                run_id, symbol, timeframe, resistance_ma, half_close_pct,
                take_profit_pct, stop_loss_pct, start_date, end_date,
                total_trades, winning_trades, losing_trades, win_rate,
                total_profit_pct, avg_profit_pct, max_drawdown_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                config.get("symbol"),
                config.get("timeframe"),
                config.get("resistance_ma"),
                config.get("half_close_pct"),
                config.get("take_profit_pct"),
                config.get("stop_loss_pct"),
                config.get("start_date"),
                config.get("end_date"),
                stats.get("total_trades", 0),
                stats.get("winning_trades", 0),
                stats.get("losing_trades", 0),
                stats.get("win_rate", 0.0),
                stats.get("total_profit_pct", 0.0),
                stats.get("avg_profit_pct", 0.0),
                stats.get("max_drawdown_pct", 0.0),
            ),
        )


def save_ml_result(
    db_path: Path,
    run_id: str,
    model_name: str,
    metrics: dict,
    hyperparams: str | None = None,
    feature_importance: str | None = None,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ml_results (
                run_id, model_name, accuracy, precision_score, recall,
                f1_score, auc_roc, train_samples, test_samples,
                feature_importance, hyperparams
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                model_name,
                metrics.get("accuracy"),
                metrics.get("precision"),
                metrics.get("recall"),
                metrics.get("f1"),
                metrics.get("auc_roc"),
                metrics.get("train_samples"),
                metrics.get("test_samples"),
                feature_importance,
                hyperparams,
            ),
        )


def load_trades(db_path: Path, run_id: str | None = None) -> pl.DataFrame:
    with get_connection(db_path) as conn:
        if run_id:
            cursor = conn.execute(
                "SELECT * FROM trades WHERE run_id = ?",
                (run_id,),
            )
        else:
            cursor = conn.execute("SELECT * FROM trades")
        
        rows = cursor.fetchall()
        if not rows:
            return pl.DataFrame()
        
        return pl.DataFrame([dict(row) for row in rows])


def load_ml_results(db_path: Path, run_id: str | None = None) -> pl.DataFrame:
    with get_connection(db_path) as conn:
        if run_id:
            cursor = conn.execute(
                "SELECT * FROM ml_results WHERE run_id = ?",
                (run_id,),
            )
        else:
            cursor = conn.execute("SELECT * FROM ml_results")
        
        rows = cursor.fetchall()
        if not rows:
            return pl.DataFrame()
        
        return pl.DataFrame([dict(row) for row in rows])


def calculate_stats(trades_df: pl.DataFrame) -> dict:
    if trades_df.is_empty():
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_profit_pct": 0.0,
            "avg_profit_pct": 0.0,
            "max_drawdown_pct": 0.0,
        }
    
    total = len(trades_df)
    winning = trades_df.filter(pl.col("profit_pct") > 0).height
    losing = trades_df.filter(pl.col("profit_pct") <= 0).height
    
    profit_pcts = trades_df["profit_pct"].to_list()
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    
    for pct in profit_pcts:
        cumulative += pct
        peak = max(peak, cumulative)
        dd = peak - cumulative
        max_dd = max(max_dd, dd)
    
    return {
        "total_trades": total,
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate": winning / total * 100 if total > 0 else 0.0,
        "total_profit_pct": sum(profit_pcts),
        "avg_profit_pct": sum(profit_pcts) / total if total > 0 else 0.0,
        "max_drawdown_pct": max_dd,
    }
