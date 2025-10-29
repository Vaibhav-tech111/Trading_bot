from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware # ✅ Import CORS middleware
import asyncio
import json
import os
from typing import Dict, Optional
import logging

from session_manager import SessionManager
from fake_wallet import load_wallet
from summary_report import load_summary
from binance_client import valid_symbols, valid_timeframes  # Import validation lists

app = FastAPI()

# ✅ Allow frontend to connect (CORS fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For open testing; restrict later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

# Global variables for session management
session_manager: Optional[SessionManager] = None
active_websocket: Optional[WebSocket] = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.post("/start_session")
async def start_session(symbol: str, timeframe: str, duration: int):
    """
    Start a trading session for a given symbol, timeframe, and duration.
    """
    global session_manager

    if session_manager and session_manager.is_active:
        raise HTTPException(status_code=400, detail="A session is already active. Please stop it first.")

    symbol = symbol.upper()
    timeframe = timeframe.lower()

    if symbol not in valid_symbols:
        raise HTTPException(status_code=400, detail=f"Invalid symbol: {symbol}. Valid symbols: {valid_symbols}")
    if timeframe not in valid_timeframes:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: {timeframe}. Valid timeframes: {valid_timeframes}")
    if duration <= 0:
        raise HTTPException(status_code=400, detail="Duration must be a positive integer.")

    # Pass the active_websocket (which might be None if no client is connected yet)
    # The session_manager will update its websocket reference if needed later
    session_manager = SessionManager(symbol, timeframe, duration, active_websocket)
    await session_manager.start_trading()
    logger.info(f"Started trading session for {symbol} ({timeframe}) for {duration}s")
    return {"message": f"Started trading session for {symbol} on {timeframe} for {duration} seconds."}


@app.post("/stop_session")
async def stop_session():
    """
    Stop the active trading session.
    """
    global session_manager

    if not session_manager or not session_manager.is_active:
        raise HTTPException(status_code=400, detail="No active session to stop.")
    
    await session_manager.stop_trading()
    session_manager = None
    logger.info("Trading session stopped manually.")
    return {"message": "Stopped trading session."}


@app.get("/get_wallet")
async def get_wallet():
    """Return current fake wallet info."""
    return load_wallet()


@app.get("/get_summary")
async def get_summary():
    """Return current trading summary."""
    return load_summary()


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection for live price and event updates.
    """
    global active_websocket, session_manager

    await websocket.accept()
    logger.info("WebSocket connected.")

    # Update active websocket reference
    active_websocket = websocket
    # If a session is already active, update its internal websocket reference
    if session_manager and session_manager.is_active:
        session_manager.websocket = websocket
        logger.info("Updated session manager's WebSocket reference.")

    try:
        while True:
            # Keep alive, listen for client messages (if any)
            # We primarily push data, so receiving might not be necessary unless you send commands back
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.warning("WebSocket disconnected.")
        if active_websocket == websocket:
            active_websocket = None
        # 🧩 Gracefully stop any active session on disconnect
        # This might be optional depending on your logic - maybe just remove the websocket reference
        # and let the session run until duration expires.
        # For now, let's just remove the reference.
        if session_manager:
            session_manager.websocket = None
            logger.info("Removed WebSocket reference from session manager on disconnect.")
        # Optionally, stop the session if desired on disconnect:
        # if session_manager and session_manager.is_active:
        #     await session_manager.stop_trading()
        #     session_manager = None
        #     logger.info("Session stopped due to WebSocket disconnect.")


# ✅ Run the app (Render command: uvicorn main:app --host 0.0.0.0 --port $PORT)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
