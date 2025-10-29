import json
import os
import threading
from fake_wallet import load_wallet
import logging

# File path for summary data
SUMMARY_FILE = 'data/summary.json'

# Lock for thread-safe file operations
summary_lock = threading.Lock()

logger = logging.getLogger(__name__)

def load_summary() -> dict:
    """Loads the latest summary data from the JSON file."""
    with summary_lock:
        if os.path.exists(SUMMARY_FILE):
            try:
                with open(SUMMARY_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading summary: {e}")
        # Return empty summary if file doesn't exist or is corrupt
        return {}

def save_summary(summary_data: dict):
    """Saves the summary data to the JSON file."""
    with summary_lock:
        try:
            with open(SUMMARY_FILE, 'w') as f:
                json.dump(summary_data, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving summary: {e}")

async def generate_summary(symbol: str, timeframe: str, duration: int):
    """Calculates and saves the trading session summary."""
    wallet = load_wallet()
    
    trade_history = wallet.get('trade_history', [])
    initial_balance = 1000.0
    final_balance = wallet['balance']
    
    total_trades = len(trade_history)
    total_profit = final_balance - initial_balance
    
    wins = 0
    losses = 0
    for trade in trade_history:
        if trade.get('profit_loss', 0) > 0:
            wins += 1
        elif trade.get('profit_loss', 0) < 0:
            losses += 1

    roi = (total_profit / initial_balance) * 100 if initial_balance != 0 else 0

    summary = {
        "symbol": symbol,
        "timeframe": timeframe,
        "duration": f"{duration}s",
        "trades": total_trades,
        "wins": wins,
        "losses": losses,
        "total_profit": round(total_profit, 2),
        "roi": round(roi, 2),
        "final_balance": round(final_balance, 2),
        "timestamp": _get_timestamp()
    }

    save_summary(summary)
    logger.info(f"Summary generated: {summary}")
    return summary

def _get_timestamp() -> str:
    """Helper to get current timestamp string."""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
