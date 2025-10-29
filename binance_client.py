import asyncio
import aiohttp
import json
from typing import Callable, List
import logging

# Define valid symbols and timeframes as lists for validation
valid_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"] # Add more as needed
valid_timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Base URLs
BASE_URL = 'https://api.binance.com'
STREAM_URL = 'wss://stream.binance.com:9443/ws'

logger = logging.getLogger(__name__)

async def get_historical_klines(symbol: str, interval: str, limit: int = 500) -> List[List]:
    """Fetches historical klines/candles from Binance REST API."""
    url = f"{BASE_URL}/api/v3/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': min(limit, 1000)  # Binance max limit per request is 1000
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.text()
                klines = json.loads(data)
                # Return only the necessary fields: [timestamp, open, high, low, close, volume]
                return [[float(k[0]), float(k[4])] for k in klines] # Using close price
        except Exception as e:
            logger.error(f"Error fetching historical klines: {e}")
            return []

async def stream_live_klines(symbol: str, interval: str, callback: Callable[[dict], None]):
    """Streams live kline data from Binance WebSocket."""
    stream_name = f"{symbol.lower()}@kline_{interval}"
    url = f"{STREAM_URL}/{stream_name}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(url) as ws:
                logger.info(f"Connected to Binance WebSocket stream: {stream_name}")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            kline_data = data['k']
                            # Extract relevant data: event_type, close_time, symbol, interval, is_closed, open, high, low, close, volume
                            candle_info = {
                                'e': data['e'],  # Event type
                                'E': data['E'],  # Event time
                                's': data['s'],  # Symbol
                                'k': {
                                    't': kline_data['t'],  # Kline start time
                                    'T': kline_data['T'],  # Kline close time
                                    's': kline_data['s'],  # Symbol
                                    'i': kline_data['i'],  # Interval
                                    'f': kline_data['f'],  # First trade ID
                                    'L': kline_data['L'],  # Last trade ID
                                    'o': float(kline_data['o']),  # Open price
                                    'c': float(kline_data['c']),  # Close price
                                    'h': float(kline_data['h']),  # High price
                                    'l': float(kline_data['l']),  # Low price
                                    'v': float(kline_data['v']),  # Base asset volume
                                    'n': kline_data['n'],  # Number of trades
                                    'x': kline_data['x'],  # Is this kline closed?
                                    'q': float(kline_data['q']), # Quote asset volume
                                }
                            }
                            await callback(candle_info)
                        except json.JSONDecodeError:
                            logger.error("Failed to decode WebSocket message as JSON")
                        except KeyError as e:
                            logger.error(f"Key error processing WebSocket data: {e}")
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        logger.warning(f"WebSocket connection closed or error occurred for {stream_name}")
                        break
        except Exception as e:
            logger.error(f"Error connecting to Binance WebSocket: {e}")
