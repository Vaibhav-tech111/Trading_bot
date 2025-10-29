import json
import os
import threading
from typing import Dict, List, Optional
import logging

# File path for wallet data
WALLET_FILE = 'data/wallet.json'

# Lock for thread-safe file operations
wallet_lock = threading.Lock()

logger = logging.getLogger(__name__)

def load_wallet() -> Dict:
    """Loads the wallet data from the JSON file."""
    with wallet_lock:
        if os.path.exists(WALLET_FILE):
            try:
                with open(WALLET_FILE, 'r') as f:
                    data = json.load(f)
                    # Ensure structure exists
                    data.setdefault('balance', 1000.0)
                    data.setdefault('open_positions', [])
                    data.setdefault('trade_history', [])
                    return data
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading wallet: {e}. Initializing with default.")
        # Initialize default wallet if file doesn't exist or is corrupt
        default_wallet = {
            'balance': 1000.0,
            'open_positions': [],
            'trade_history': []
        }
        save_wallet(default_wallet)
        return default_wallet

def save_wallet(wallet_data: Dict):
    """Saves the wallet data to the JSON file."""
    with wallet_lock:
        try:
            with open(WALLET_FILE, 'w') as f:
                json.dump(wallet_data, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving wallet: {e}")

def buy(symbol: str, price: float, quantity: float):
    """Executes a fake buy order."""
    wallet = load_wallet()
    cost = price * quantity
    if wallet['balance'] >= cost:
        wallet['balance'] -= cost
        wallet['open_positions'].append({
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': price,
            'timestamp': _get_timestamp()
        })
        wallet['trade_history'].append({
            'action': 'BUY',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'cost': cost,
            'timestamp': _get_timestamp()
        })
        save_wallet(wallet)
        logger.info(f"Fake BUY executed: {quantity} {symbol} at ${price:.4f}, Cost: ${cost:.2f}")
        return True
    else:
        logger.warning(f"Insufficient balance for BUY: ${cost:.2f} needed, ${wallet['balance']:.2f} available.")
        return False

def sell(symbol: str, price: float):
    """Executes a fake sell order for all open positions of the symbol."""
    wallet = load_wallet()
    positions_to_sell = [p for p in wallet['open_positions'] if p['symbol'] == symbol]
    if not positions_to_sell:
        logger.warning(f"No open positions for {symbol} to sell.")
        return False

    total_profit_loss = 0.0
    for pos in positions_to_sell:
        quantity = pos['quantity']
        entry_price = pos['entry_price']
        revenue = price * quantity
        profit_loss = revenue - (entry_price * quantity)
        total_profit_loss += profit_loss

        wallet['balance'] += revenue
        wallet['trade_history'].append({
            'action': 'SELL',
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'revenue': revenue,
            'profit_loss': profit_loss,
            'timestamp': _get_timestamp()
        })

    # Remove sold positions
    wallet['open_positions'] = [p for p in wallet['open_positions'] if p['symbol'] != symbol]
    save_wallet(wallet)
    logger.info(f"Fake SELL executed for {symbol}: Revenue: ${revenue:.2f}, Profit/Loss: ${profit_loss:.2f} for position, Total P/L: ${total_profit_loss:.2f}")
    return True

def get_balance() -> float:
    """Returns the current fake balance."""
    wallet = load_wallet()
    return wallet['balance']

def _get_timestamp() -> str:
    """Helper to get current timestamp string."""
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
