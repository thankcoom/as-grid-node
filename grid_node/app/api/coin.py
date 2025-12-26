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
        usdc_results = await scanner.scan_with_amplitude(
            exchange, quote_currency='USDC', top_n=req.limit, use_cache=not req.force_refresh
        )
        usdt_results = await scanner.scan_with_amplitude(
            exchange, quote_currency='USDT', top_n=req.limit, use_cache=not req.force_refresh
        )
        
        # 合併結果
        all_candidates = usdc_results + usdt_results
        
        # scan_with_amplitude 已經按 grid_suitability 排序，取前 N 個
        # 結構: [(SymbolInfo, AmplitudeStats), ...]
        all_candidates.sort(key=lambda x: x[1].grid_suitability if x[1] else 0, reverse=True)
        candidates = all_candidates[:req.limit]
        
        if not candidates:
            return ScanResponse(
                rankings=[],
                elapsed_seconds=time.time() - start_time,
                message="No suitable symbols found"
            )
        
        # 直接從 AmplitudeStats 建立排名結果
        result_rankings = []
        for i, (sym_info, amp_stats) in enumerate(candidates):
            if amp_stats:
                result_rankings.append(SymbolRanking(
                    symbol=sym_info.ccxt_symbol,
                    rank=i + 1,
                    total_score=amp_stats.grid_suitability,
                    amplitude=amp_stats.avg_amplitude,
                    trend=amp_stats.total_change,
                    volume_24h=amp_stats.volume_24h,
                    price=amp_stats.last_price,
                    grid_suitability=amp_stats.grid_suitability,
                    action="WATCH" if amp_stats.grid_suitability >= 60 else "AVOID"
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
