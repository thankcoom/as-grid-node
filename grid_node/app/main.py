from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.services.bot_manager import bot_manager

app = FastAPI(title="AS Grid Node")

# CORS - Allow frontend to connect from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def verify_secret(x_node_secret: str = Header(...)):
    if x_node_secret != settings.NODE_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Node Secret")

class StartRequest(BaseModel):
    symbol: str
    quantity: float

@app.post("/api/v1/grid/start", dependencies=[Depends(verify_secret)])
def start_grid(req: StartRequest):
    try:
        return bot_manager.start(req.symbol, req.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/grid/stop", dependencies=[Depends(verify_secret)])
async def stop_grid():
    return await bot_manager.stop()

@app.get("/api/v1/grid/status", dependencies=[Depends(verify_secret)])
def get_status():
    return bot_manager.get_status()

# Placeholder for Backtest and Coin Selection
@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
