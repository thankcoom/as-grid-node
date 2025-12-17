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
        from trading_core.backtest import BacktestManager
        from trading_core.models import SymbolConfig
        
        # 創建回測器
        backtester = BacktestManager()
        
        # 轉換 symbol 格式
        symbol_raw = req.symbol  # e.g., "XRPUSDC"
        coin = symbol_raw.replace("USDT", "").replace("USDC", "")
        if "USDC" in symbol_raw:
            ccxt_symbol = f"{coin}/USDC:USDC"
        else:
            ccxt_symbol = f"{coin}/USDT:USDT"
        
        # 創建 SymbolConfig
        config = SymbolConfig(
            symbol=symbol_raw,
            ccxt_symbol=ccxt_symbol,
            take_profit_spacing=req.take_profit_spacing,
            grid_spacing=req.grid_spacing,
            initial_quantity=req.initial_quantity,
            leverage=req.leverage
        )
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=req.days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # 嘗試載入數據
        df = backtester.load_data(symbol_raw, start_str, end_str)
        
        if df is None or len(df) < 100:
            # 嘗試下載數據
            logger.info(f"No local data for {symbol_raw}, attempting download...")
            backtester.download_data(symbol_raw, ccxt_symbol, start_str, end_str)
            df = backtester.load_data(symbol_raw, start_str, end_str)
        
        if df is None or len(df) < 100:
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
                message=f"數據不足，無法進行回測 (需要至少 100 條 K 線)"
            )
        
        # 執行回測
        result = backtester.run_backtest(config, df)
        
        # 計算 Sharpe Ratio (簡化版)
        roi = result.get('return_pct', 0)
        sharpe = roi / result.get('max_drawdown', 0.01) if result.get('max_drawdown', 0) > 0 else roi * 10
        
        # 構建結果
        backtest_result = BacktestResult(
            symbol=req.symbol,
            period_days=req.days,
            total_pnl=result.get('realized_pnl', 0) + result.get('unrealized_pnl', 0),
            total_trades=result.get('trades_count', 0),
            win_rate=result.get('win_rate', 0),
            max_drawdown=result.get('max_drawdown', 0),
            sharpe_ratio=sharpe,
            final_capital=result.get('final_equity', req.initial_capital),
            roi_percent=result.get('return_pct', 0) * 100,
            message=f"回測完成，耗時 {time.time() - start_time:.1f}s"
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
        from trading_core.backtest import BacktestManager
        from trading_core.models import SymbolConfig
        
        backtester = BacktestManager()
        
        # 轉換 symbol 格式
        symbol_raw = req.symbol
        coin = symbol_raw.replace("USDT", "").replace("USDC", "")
        if "USDC" in symbol_raw:
            ccxt_symbol = f"{coin}/USDC:USDC"
        else:
            ccxt_symbol = f"{coin}/USDT:USDT"
        
        # 創建 base config
        config = SymbolConfig(
            symbol=symbol_raw,
            ccxt_symbol=ccxt_symbol,
            take_profit_spacing=0.004,
            grid_spacing=0.006,
            initial_quantity=30,
            leverage=20
        )
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=req.days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # 載入數據
        df = backtester.load_data(symbol_raw, start_str, end_str)
        
        if df is None or len(df) < 100:
            # 嘗試下載
            backtester.download_data(symbol_raw, ccxt_symbol, start_str, end_str)
            df = backtester.load_data(symbol_raw, start_str, end_str)
        
        if df is None or len(df) < 100:
            return OptimizeResult(
                symbol=req.symbol,
                best_tp=0.004,
                best_gs=0.006,
                best_pnl=0,
                best_sharpe=0,
                iterations=0,
                message="數據不足，無法進行優化"
            )
        
        # 使用 BacktestManager 的優化方法
        results = backtester.optimize_params(config, df)
        
        if results:
            best = results[0]
            best_tp = best.get('take_profit_spacing', 0.004)
            best_gs = best.get('grid_spacing', 0.006)
            best_pnl = best.get('realized_pnl', 0) + best.get('unrealized_pnl', 0)
            roi = best.get('return_pct', 0)
            best_sharpe = roi / best.get('max_drawdown', 0.01) if best.get('max_drawdown', 0) > 0 else roi * 10
        else:
            best_tp = 0.004
            best_gs = 0.006
            best_pnl = 0
            best_sharpe = 0
        
        optimize_result = OptimizeResult(
            symbol=req.symbol,
            best_tp=best_tp,
            best_gs=best_gs,
            best_pnl=best_pnl,
            best_sharpe=best_sharpe,
            iterations=len(results) if results else 0,
            message=f"優化完成，耗時 {time.time() - start_time:.1f}s"
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


# 保存 Top 5 結果
_top_results: Dict[str, List[Dict]] = {}


@router.post("/smart_optimize")
async def smart_optimize(req: OptimizeRequest):
    """
    智能優化（使用 Optuna TPE）
    
    對應 GUI: BacktestPage 智能優化按鈕
    使用 Tree-structured Parzen Estimator 進行貝葉斯優化
    """
    import time
    start_time = time.time()
    
    try:
        # 嘗試導入 Optuna
        import optuna
        from trading_core.backtest import BacktestManager
        
        backtester = BacktestManager()
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=req.days)
        
        all_results = []
        
        def objective(trial):
            tp = trial.suggest_float('tp', req.tp_min, req.tp_max)
            gs = trial.suggest_float('gs', req.gs_min, req.gs_max)
            
            params = {
                'symbol': req.symbol,
                'take_profit_spacing': tp,
                'grid_spacing': gs,
                'initial_quantity': 30,
                'leverage': 20,
                'initial_capital': req.initial_capital
            }
            
            try:
                # 使用 asyncio 運行回測
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(backtester.run(
                    symbol=req.symbol,
                    start_date=start_date,
                    end_date=end_date,
                    params=params
                ))
                
                pnl = result.get('total_pnl', 0)
                sharpe = result.get('sharpe_ratio', 0)
                
                # 保存結果
                all_results.append({
                    'tp': tp,
                    'gs': gs,
                    'pnl': pnl,
                    'sharpe': sharpe,
                    'roi': result.get('roi', 0) * 100,
                    'trades': result.get('total_trades', 0)
                })
                
                # 使用 Sharpe 作為優化目標
                return sharpe
            except Exception:
                return float('-inf')
        
        # 創建 Optuna 研究
        study = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler()
        )
        
        # 運行優化（50 次試驗）
        study.optimize(objective, n_trials=50, show_progress_bar=False)
        
        # 排序並獲取 Top 5
        all_results.sort(key=lambda x: x['sharpe'], reverse=True)
        top_5 = all_results[:5]
        
        # 保存 Top 5 結果
        _top_results[req.symbol] = top_5
        
        # 最佳結果
        best = study.best_params
        
        return {
            "symbol": req.symbol,
            "best_tp": best['tp'],
            "best_gs": best['gs'],
            "best_sharpe": study.best_value,
            "top_5": top_5,
            "trials": len(study.trials),
            "elapsed_time": time.time() - start_time,
            "message": f"Smart optimization completed with {len(study.trials)} trials"
        }
    
    except ImportError as e:
        logger.warning(f"Optuna not available, falling back to grid search: {e}")
        # 回退到網格搜索
        return await optimize_parameters(req)
    
    except Exception as e:
        logger.error(f"Smart optimization error: {e}")
        raise HTTPException(500, str(e))


@router.get("/top_results/{symbol}")
def get_top_results(symbol: str):
    """
    獲取 Top 5 優化結果
    
    對應 GUI: BacktestPage Top 5 結果選擇
    """
    if symbol in _top_results:
        return {"symbol": symbol, "results": _top_results[symbol]}
    return {"symbol": symbol, "results": [], "error": "No optimization results found"}


@router.post("/apply_params/{symbol}")
async def apply_optimized_params(symbol: str, rank: int = 0):
    """
    應用優化後的參數到交易對配置
    
    Args:
        symbol: 交易對符號
        rank: Top 5 中的排名 (0-4)
    """
    if symbol not in _top_results or not _top_results[symbol]:
        raise HTTPException(404, "No optimization results found")
    
    if rank < 0 or rank >= len(_top_results[symbol]):
        raise HTTPException(400, f"Invalid rank: {rank}")
    
    selected = _top_results[symbol][rank]
    
    try:
        from trading_core.models import GlobalConfig
        config = GlobalConfig.load()
        
        if symbol not in config.symbols:
            raise HTTPException(404, f"Symbol {symbol} not found in config")
        
        # 更新參數
        config.symbols[symbol].take_profit_spacing = selected['tp']
        config.symbols[symbol].grid_spacing = selected['gs']
        config.save()
        
        return {
            "status": "success",
            "symbol": symbol,
            "applied": {
                "take_profit_spacing": selected['tp'],
                "grid_spacing": selected['gs'],
                "expected_sharpe": selected['sharpe']
            }
        }
    
    except Exception as e:
        logger.error(f"Failed to apply params: {e}")
        raise HTTPException(500, str(e))
