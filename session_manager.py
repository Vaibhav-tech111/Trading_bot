import asyncio
import logging
from typing import Optional
from binance_client import stream_live_klines, get_historical_klines
from strategy_engine import evaluate_strategy
from fake_wallet import buy, sell, get_balance
from summary_report import generate_summary
import time
import json # Import json for sending WebSocket messages

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self, symbol: str, timeframe: str, duration: int, websocket: Optional['WebSocket']):
        self.symbol = symbol
        self.timeframe = timeframe
        self.duration = duration
        self.websocket = websocket
        self.is_active = False
        self._stop_event = asyncio.Event()
        self.closes = [] # Maintain a list of closing prices

    async def start_trading(self):
        if self.is_active:
            logger.warning("Session is already active.")
            return

        logger.info(f"Starting trading session for {self.symbol} on {self.timeframe} for {self.duration}s")
        self.is_active = True
        self._stop_event.clear()

        # Fetch initial historical data
        historical_data = await get_historical_klines(self.symbol, self.timeframe, limit=500)
        if historical_data:
            self.closes = [c[1] for c in historical_data] # Extract closing prices
            logger.info(f"Fetched {len(self.closes)} historical candles for initial strategy calculation.")

        # Start the trading loop and the WebSocket stream concurrently
        await asyncio.gather(
            self._trading_loop(),
            self._stream_data()
        )

    async def stop_trading(self):
        logger.info("Stopping trading session...")
        self.is_active = False
        self._stop_event.set()

    async def _trading_loop(self):
        """Main loop that evaluates strategy and executes trades based on signals."""
        start_time = time.time()
        try:
            while self.is_active and time.time() - start_time < self.duration:
                if len(self.closes) < 2: # Need at least 2 points to potentially trade
                    await asyncio.sleep(1)
                    continue

                signal, rsi_val, sma_val = evaluate_strategy(self.closes)
                current_price = self.closes[-1]

                # Execute trade based on signal
                if signal == "BUY":
                    balance = get_balance()
                    quantity = (balance * 0.1) / current_price # Example: buy 10% of balance
                    if quantity > 0:
                        success = buy(self.symbol, current_price, quantity)
                        if success:
                            logger.info(f"BUY signal executed for {quantity} {self.symbol} at {current_price}")
                elif signal == "SELL":
                    # Sell all open positions for the symbol
                    success = sell(self.symbol, current_price)
                    if success:
                         logger.info(f"SELL signal executed for {self.symbol} at {current_price}")

                # Wait before the next evaluation (e.g., for 1m timeframe, evaluate every minute)
                # This simplistic sleep might not perfectly align with candle closes.
                await asyncio.sleep(5) # Evaluate every 5 seconds as an example check frequency

        except asyncio.CancelledError:
            logger.info("Trading loop was cancelled.")
        finally:
            # Close any remaining positions when stopping
            if self.is_active: # If stopped manually, still close positions
                current_price = self.closes[-1] if self.closes else get_balance() / 100 # Fallback price
                sell(self.symbol, current_price) # Attempt to sell all open positions
            # Generate summary after stopping
            await generate_summary(self.symbol, self.timeframe, self.duration)
            self.is_active = False
            logger.info("Trading session loop finished.")

    async def _stream_data(self):
        """Streams live data from Binance and updates the closes list."""
        async def on_kline_update(data):
            if data['k']['x']:  # Check if kline is closed
                close_price = data['k']['c']
                self.closes.append(close_price)
                # Maintain list size based on strategy needs, e.g., keep last 500
                if len(self.closes) > 500:
                    self.closes.pop(0)
                logger.debug(f"New candle closed for {self.symbol}: {close_price}")

                # Calculate RSI and SMA for the latest data to send with the update
                # Note: This is calculated for every closed candle, which might be frequent.
                # Consider optimizing if needed, or sending less frequently.
                signal, rsi_val, sma_val = evaluate_strategy(self.closes)

                # Prepare the data to send via WebSocket
                ws_data = {
                    "symbol": self.symbol,
                    "price": close_price,
                    "rsi": rsi_val,
                    "sma": sma_val,
                    "signal": signal,
                    "balance": get_balance()
                }

                # Send data to the connected WebSocket client (frontend)
                if self.websocket:
                    try:
                        await self.websocket.send_text(json.dumps(ws_data))
                        logger.debug(f"Sent WebSocket update: {ws_data}")
                    except Exception as e:
                        logger.warning(f"Could not send WebSocket update: {e}")
                        # If websocket fails, update the internal reference
                        self.websocket = None

        try:
            await stream_live_klines(self.symbol, self.timeframe, on_kline_update)
        except Exception as e:
            logger.error(f"Error in streaming data loop: {e}")
        finally:
            # Ensure the main loop stops if streaming fails
            self._stop_event.set()
