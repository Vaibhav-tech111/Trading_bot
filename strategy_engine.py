import numpy as np
from utils import calculate_rsi, calculate_sma
import logging

logger = logging.getLogger(__name__)

def generate_signal(price: float, rsi_value: float, sma_value: float) -> str:
    """
    Generates a trading signal based on RSI and SMA values.
    Buy signal: RSI < 30 and price > SMA.
    Sell signal: RSI > 70 or price < SMA.
    Otherwise, hold.
    """
    try:
        if rsi_value < 30 and price > sma_value:
            return "BUY"
        elif rsi_value > 70 or price < sma_value:
            return "SELL"
        else:
            return "HOLD"
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return "HOLD" # Default to HOLD on error

def evaluate_strategy(closes: list, sma_period: int = 20, rsi_period: int = 14) -> tuple:
    """
    Calculates RSI and SMA for the latest data point and generates a signal.
    Returns (signal, rsi_value, sma_value).
    """
    try:
        if len(closes) < max(sma_period, rsi_period):
            logger.warning("Insufficient data for strategy calculation.")
            return "HOLD", None, None

        sma = calculate_sma(closes, sma_period)
        rsi = calculate_rsi(closes, rsi_period)
        current_price = closes[-1]

        signal = generate_signal(current_price, rsi, sma)
        return signal, rsi, sma
    except Exception as e:
        logger.error(f"Error evaluating strategy: {e}")
        return "HOLD", None, None
