"""
選幣系統 API

封裝 coin_selection 模組，提供 REST API
"""
import asyncio
import logging
import os
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import ccxt.async_support as ccxt

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════

class ScanRequest(BaseModel):
    """掃描請求"""
    force_refresh: bool = False
    limit: int = 20


class SymbolRanking(BaseModel):
    """幣種評分結果"""
    symbol: str
    rank: int
    total_score: float
    amplitude: float
    trend: float
    volume_24h: float
    price: float
    grid_suitability: float
    action: str  # HOLD, WATCH, AVOID


class ScanResponse(BaseModel):
    """掃描結果"""
    rankings: List[SymbolRanking]
    elapsed_seconds: float
    message: str


class RotationCheckRequest(BaseModel):
    """輪動檢查請求"""
    current_symbol: str


class RotationSignal(BaseModel):
    """輪動信號"""
    should_rotate: bool
    current_symbol: str
    suggested_symbol: Optional[str]
    reason: str
    score_improvement: float


# ═══════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════

async def get_exchange():
    """獲取交易所連接"""
    api_key = os.getenv("EXCHANGE_API_KEY")
    api_secret = os.getenv("EXCHANGE_SECRET")
    passphrase = os.getenv("EXCHANGE_PASSPHRASE")
    
    if not api_key or not api_secret:
        raise HTTPException(503, "Exchange not configured")
    
    exchange = ccxt.bitget({
        'apiKey': api_key,
        'secret': api_secret,
        'password': passphrase,
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    })
    
    return exchange


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/scan", response_model=ScanResponse)
async def scan_all_symbols(req: ScanRequest):
    """
    掃描全部合約交易對，返回評分排名
    
    對應 GUI: CoinSelectionPage._scan_all_symbols()
    """
    import time
    start_time = time.time()
    
    exchange = await get_exchange()
    
    try:
        # 導入選幣模組
        from coin_selection import CoinScorer, CoinRanker
        from coin_selection.symbol_scanner import SymbolScanner
        
        # 掃描交易對
        scanner = SymbolScanner()
        
        # 獲取 USDC 和 USDT 合約
        usdc_results = await scanner.scan_usdc_symbols(exchange)
        usdt_results = await scanner.scan_usdt_symbols(exchange)
        
        # 合併結果
        all_candidates = usdc_results + usdt_results
        
        # 按振幅排序，取前 N 個
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        candidates = all_candidates[:req.limit]
        
        if not candidates:
            return ScanResponse(
                rankings=[],
                elapsed_seconds=time.time() - start_time,
                message="No suitable symbols found"
            )
        
        # 評分
        scorer = CoinScorer()
        ranker = CoinRanker(scorer)
        
        symbols = [sym.ccxt_symbol for sym, _ in candidates]
        rankings = await ranker.get_rankings(
            symbols, 
            exchange, 
            force_refresh=req.force_refresh
        )
        
        # 轉換為響應格式
        result_rankings = []
        for i, rank in enumerate(rankings):
            amp_stats = getattr(rank, '_amplitude_stats', None)
            result_rankings.append(SymbolRanking(
                symbol=rank.symbol,
                rank=i + 1,
                total_score=rank.score.final_score,
                amplitude=amp_stats.avg_amplitude if amp_stats else 0,
                trend=amp_stats.total_change if amp_stats else 0,
                volume_24h=amp_stats.volume_24h if amp_stats else rank.score.volume_24h,
                price=amp_stats.last_price if amp_stats else 0,
                grid_suitability=amp_stats.grid_suitability if amp_stats else 0,
                action=rank.action.value if hasattr(rank.action, 'value') else str(rank.action)
            ))
        
        elapsed = time.time() - start_time
        
        return ScanResponse(
            rankings=result_rankings,
            elapsed_seconds=elapsed,
            message=f"Found {len(result_rankings)} candidates"
        )
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(500, f"Coin selection module not available: {e}")
    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(500, str(e))
    finally:
        await exchange.close()


@router.get("/rankings")
async def get_cached_rankings():
    """
    獲取快取的評分排名（不重新掃描）
    """
    try:
        from coin_selection import get_cached_rankings
        rankings = get_cached_rankings()
        
        if not rankings:
            return {"rankings": [], "message": "No cached rankings. Run scan first."}
        
        return {"rankings": rankings}
    
    except ImportError:
        return {"rankings": [], "message": "Coin selection module not available"}


@router.post("/rotation/check", response_model=RotationSignal)
async def check_rotation(req: RotationCheckRequest):
    """
    檢查是否需要輪動到更好的幣種
    
    對應 GUI: CoinSelectionPage._check_rotation()
    """
    exchange = await get_exchange()
    
    try:
        from coin_selection import CoinScorer, CoinRanker, CoinRotator
        
        scorer = CoinScorer()
        ranker = CoinRanker(scorer)
        rotator = CoinRotator(ranker)
        
        # 獲取候選幣種列表
        default_symbols = [
            "XRP/USDC:USDC", "DOGE/USDC:USDC", "ETH/USDC:USDC", "BTC/USDC:USDC",
            "SOL/USDC:USDC", "ADA/USDC:USDC", "LINK/USDC:USDC"
        ]
        
        signal = await rotator.check_rotation(
            req.current_symbol,
            exchange,
            default_symbols,
            force_check=True
        )
        
        if signal:
            return RotationSignal(
                should_rotate=True,
                current_symbol=signal.current_symbol,
                suggested_symbol=signal.new_symbol,
                reason=signal.reason,
                score_improvement=signal.score_improvement
            )
        else:
            return RotationSignal(
                should_rotate=False,
                current_symbol=req.current_symbol,
                suggested_symbol=None,
                reason="Current symbol is optimal",
                score_improvement=0
            )
    
    except ImportError as e:
        raise HTTPException(500, f"Rotation module not available: {e}")
    except Exception as e:
        logger.error(f"Rotation check error: {e}")
        raise HTTPException(500, str(e))
    finally:
        await exchange.close()


@router.post("/rotation/execute")
async def execute_rotation(
    new_symbol: str,
    close_positions: bool = True
):
    """
    執行輪動（更換交易幣種）
    
    警告：這會停止當前交易並平倉！
    """
    # TODO: 實現輪動執行邏輯
    # 1. 停止當前交易
    # 2. 平倉（如果 close_positions=True）
    # 3. 更新配置
    # 4. 重新啟動交易
    
    return {
        "status": "not_implemented",
        "message": "Rotation execution requires manual confirmation"
    }
