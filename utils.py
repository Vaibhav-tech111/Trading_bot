import numpy as np
import threading
import json
import os
from datetime import datetime

# Lock for thread-safe file operations (can be shared if needed)
file_lock = threading.Lock()

def calculate_rsi(prices: list, period: int = 14) -> float:
    """Calculates the Relative Strength Index (RSI) using numpy."""
    if len(prices) < period + 1:
        return 50.0 # Default RSI if insufficient data

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)

def calculate_sma(prices: list, period: int = 20) -> float:
    """Calculates the Simple Moving Average (SMA) using numpy."""
    if len(prices) < period:
        return float(np.mean(prices)) # Return average of available data if less than period
    return float(np.mean(prices[-period:]))

def safe_json_write(filepath: str, data: dict):
    """Safely writes data to a JSON file using a lock."""
    with file_lock:
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error writing to {filepath}: {e}")

def safe_json_read(filepath: str, default: dict = None):
    """Safely reads data from a JSON file using a lock."""
    if default is None:
        default = {}
    with file_lock:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error reading from {filepath}: {e}")
        return default

def format_timestamp(timestamp: float) -> str:
    """Formats a timestamp float (seconds since epoch) into an ISO string."""
    return datetime.utcfromtimestamp(timestamp).isoformat() + "Z"
