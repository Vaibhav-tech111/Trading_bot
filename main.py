from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import os
from typing import Dict, Optional
import logging

from session_manager import SessionManager
from fake_wallet import load_wallet
from summary_report import load_summary
from binance_client import valid_symbols, valid_timeframes # Import validation lists

app = FastAPI()

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

    session_manager = SessionManager(symbol, timeframe, duration, active_websocket)
    await session_manager.start_trading()
    return {"message": f"Started trading session for {symbol} on {timeframe} for {duration} seconds."}

@app.post("/stop_session")
async def stop_session():
    global session_manager
    if not session_manager or not session_manager.is_active:
        raise HTTPException(status_code=400, detail="No active session to stop.")
    
    await session_manager.stop_trading()
    session_manager = None
    return {"message": "Stopped trading session."}

@app.get("/get_wallet")
async def get_wallet():
    return load_wallet()

@app.get("/get_summary")
async def get_summary():
    return load_summary()

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    global active_websocket
    await websocket.accept()
    
    # If there's an active session, update its websocket reference
    if session_manager and session_manager.is_active:
        session_manager.websocket = websocket
        
    active_websocket = websocket
    try:
        while True:
            # Keep the connection alive, listen for messages if needed
            data = await websocket.receive_text()
            # Handle potential client messages here if necessary
            # For now, we mainly push data from the session manager
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
        if active_websocket == websocket:
            active_websocket = None
        # Optionally notify session manager about disconnection
        if session_manager:
             session_manager.websocket = None

# Run the main FastAPI app
# Command for Render: uvicorn main:app --host 0.0.0.0 --port $PORT
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
