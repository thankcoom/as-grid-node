"""
回測系統 API

封裝 trading_core/backtest.py
"""
import asyncio
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    """回測請求"""
    symbol: str
    days: int = 30
    take_profit_spacing: float = 0.004
    grid_spacing: float = 0.006
    initial_quantity: float = 30
    leverage: int = 20
    initial_capital: float = 1000


class BacktestResult(BaseModel):
    """回測結果"""
    symbol: str
    period_days: int
    total_pnl: float
    total_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    final_capital: float
    roi_percent: float
    message: str


class OptimizeRequest(BaseModel):
    """參數優化請求"""
    symbol: str
    days: int = 30
    initial_capital: float = 1000
    
    # 參數範圍
    tp_min: float = 0.002
    tp_max: float = 0.008
    tp_step: float = 0.001
    gs_min: float = 0.003
    gs_max: float = 0.01
    gs_step: float = 0.001


class OptimizeResult(BaseModel):
    """優化結果"""
    symbol: str
    best_tp: float
    best_gs: float
    best_pnl: float
    best_sharpe: float
    iterations: int
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# State
# ═══════════════════════════════════════════════════════════════════════════

# 保存回測結果（簡單內存存儲）
_backtest_results: Dict[str, BacktestResult] = {}
_optimize_results: Dict[str, OptimizeResult] = {}


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/run", response_model=BacktestResult)
async def run_backtest(req: BacktestRequest):
    """
    執行回測
    
    對應 GUI: BacktestPage._run_backtest()
    """
    import time
    start_time = time.time()
    
    try:
        from trading_core.backtest import GridBacktester
        
        # 創建回測器
        backtester = GridBacktester()
        
        # 準備參數
        params = {
            'symbol': req.symbol,
            'take_profit_spacing': req.take_profit_spacing,
            'grid_spacing': req.grid_spacing,
            'initial_quantity': req.initial_quantity,
            'leverage': req.leverage,
            'initial_capital': req.initial_capital
        }
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=req.days)
        
        # 執行回測
        result = await backtester.run(
            symbol=req.symbol,
            start_date=start_date,
            end_date=end_date,
            params=params
        )
        
        # 構建結果
        backtest_result = BacktestResult(
            symbol=req.symbol,
            period_days=req.days,
            total_pnl=result.get('total_pnl', 0),
            total_trades=result.get('total_trades', 0),
            win_rate=result.get('win_rate', 0),
            max_drawdown=result.get('max_drawdown', 0),
            sharpe_ratio=result.get('sharpe_ratio', 0),
            final_capital=result.get('final_capital', req.initial_capital),
            roi_percent=result.get('roi', 0) * 100,
            message=f"Backtest completed in {time.time() - start_time:.1f}s"
        )
        
        # 緩存結果
        _backtest_results[req.symbol] = backtest_result
        
        return backtest_result
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        # 返回模擬結果（用於測試）
        return BacktestResult(
            symbol=req.symbol,
            period_days=req.days,
            total_pnl=0,
            total_trades=0,
            win_rate=0,
            max_drawdown=0,
            sharpe_ratio=0,
            final_capital=req.initial_capital,
            roi_percent=0,
            message=f"Backtest module not available: {e}"
        )
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(500, str(e))


@router.get("/result/{symbol}")
def get_backtest_result(symbol: str):
    """
    獲取之前的回測結果
    """
    if symbol in _backtest_results:
        return _backtest_results[symbol]
    return {"error": "No backtest result found for this symbol"}


@router.post("/optimize", response_model=OptimizeResult)
async def optimize_parameters(req: OptimizeRequest):
    """
    參數優化（網格搜索）
    
    對應 GUI: BacktestPage 優化按鈕
    
    警告：這可能需要較長時間！
    """
    import time
    start_time = time.time()
    
    try:
        from trading_core.backtest import GridBacktester
        
        backtester = GridBacktester()
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=req.days)
        
        best_tp = req.tp_min
        best_gs = req.gs_min
        best_pnl = float('-inf')
        best_sharpe = 0
        iterations = 0
        
        # 網格搜索
        tp = req.tp_min
        while tp <= req.tp_max:
            gs = req.gs_min
            while gs <= req.gs_max:
                iterations += 1
                
                params = {
                    'symbol': req.symbol,
                    'take_profit_spacing': tp,
                    'grid_spacing': gs,
                    'initial_quantity': 30,
                    'leverage': 20,
                    'initial_capital': req.initial_capital
                }
                
                try:
                    result = await backtester.run(
                        symbol=req.symbol,
                        start_date=start_date,
                        end_date=end_date,
                        params=params
                    )
                    
                    pnl = result.get('total_pnl', 0)
                    sharpe = result.get('sharpe_ratio', 0)
                    
                    if pnl > best_pnl:
                        best_pnl = pnl
                        best_tp = tp
                        best_gs = gs
                        best_sharpe = sharpe
                
                except Exception:
                    pass
                
                gs += req.gs_step
            tp += req.tp_step
        
        optimize_result = OptimizeResult(
            symbol=req.symbol,
            best_tp=best_tp,
            best_gs=best_gs,
            best_pnl=best_pnl,
            best_sharpe=best_sharpe,
            iterations=iterations,
            message=f"Optimization completed in {time.time() - start_time:.1f}s"
        )
        
        _optimize_results[req.symbol] = optimize_result
        
        return optimize_result
    
    except ImportError as e:
        return OptimizeResult(
            symbol=req.symbol,
            best_tp=0.004,
            best_gs=0.006,
            best_pnl=0,
            best_sharpe=0,
            iterations=0,
            message=f"Backtest module not available: {e}"
        )
    except Exception as e:
        logger.error(f"Optimization error: {e}")
        raise HTTPException(500, str(e))


@router.get("/optimize/result/{symbol}")
def get_optimize_result(symbol: str):
    """
    獲取之前的優化結果
    """
    if symbol in _optimize_results:
        return _optimize_results[symbol]
    return {"error": "No optimization result found for this symbol"}
