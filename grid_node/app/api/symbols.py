"""
交易對管理 API

封裝 GlobalConfig 交易對配置
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════

class SymbolConfig(BaseModel):
    """交易對配置"""
    symbol: str
    enabled: bool = True
    take_profit_spacing: float = 0.004
    grid_spacing: float = 0.006
    initial_quantity: float = 30
    leverage: int = 20


class SymbolResponse(BaseModel):
    """交易對響應"""
    symbol: str
    ccxt_symbol: str
    enabled: bool
    take_profit_spacing: float
    grid_spacing: float
    initial_quantity: float
    leverage: int


class SymbolsListResponse(BaseModel):
    """交易對列表響應"""
    symbols: List[SymbolResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# Helper
# ═══════════════════════════════════════════════════════════════════════════

def load_config():
    """載入配置"""
    try:
        from trading_core.models import GlobalConfig
        return GlobalConfig.load()
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise HTTPException(500, "Failed to load configuration")


def save_config(config):
    """保存配置"""
    try:
        config.save()
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(500, "Failed to save configuration")


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/", response_model=SymbolsListResponse)
def list_symbols():
    """
    獲取所有交易對配置
    
    對應 GUI: SymbolsPage 顯示列表
    """
    config = load_config()
    
    symbols = []
    for sym_name, sym_config in config.symbols.items():
        symbols.append(SymbolResponse(
            symbol=sym_config.symbol,
            ccxt_symbol=sym_config.ccxt_symbol,
            enabled=sym_config.enabled,
            take_profit_spacing=sym_config.take_profit_spacing,
            grid_spacing=sym_config.grid_spacing,
            initial_quantity=sym_config.initial_quantity,
            leverage=getattr(sym_config, 'leverage', 20)
        ))
    
    return SymbolsListResponse(symbols=symbols, total=len(symbols))


@router.post("/", response_model=SymbolResponse)
def add_symbol(sym: SymbolConfig):
    """
    新增交易對
    
    對應 GUI: SymbolsPage 新增按鈕
    """
    config = load_config()
    
    # 檢查是否已存在
    if sym.symbol in config.symbols:
        raise HTTPException(400, f"Symbol {sym.symbol} already exists")
    
    # 創建 ccxt 格式
    from trading_core.models import SymbolConfig as ModelSymbolConfig
    
    coin = sym.symbol.replace("USDT", "").replace("USDC", "")
    if "USDC" in sym.symbol:
        ccxt_symbol = f"{coin}/USDC:USDC"
    else:
        ccxt_symbol = f"{coin}/USDT:USDT"
    
    # 新增到配置
    config.symbols[sym.symbol] = ModelSymbolConfig(
        symbol=sym.symbol,
        ccxt_symbol=ccxt_symbol,
        enabled=sym.enabled,
        take_profit_spacing=sym.take_profit_spacing,
        grid_spacing=sym.grid_spacing,
        initial_quantity=sym.initial_quantity
    )
    
    save_config(config)
    
    logger.info(f"Added symbol: {sym.symbol}")
    
    return SymbolResponse(
        symbol=sym.symbol,
        ccxt_symbol=ccxt_symbol,
        enabled=sym.enabled,
        take_profit_spacing=sym.take_profit_spacing,
        grid_spacing=sym.grid_spacing,
        initial_quantity=sym.initial_quantity,
        leverage=sym.leverage
    )


@router.put("/{symbol}")
def update_symbol(symbol: str, update: SymbolConfig):
    """
    更新交易對配置
    
    對應 GUI: SymbolsPage 編輯
    """
    config = load_config()
    
    if symbol not in config.symbols:
        raise HTTPException(404, f"Symbol {symbol} not found")
    
    sym_config = config.symbols[symbol]
    sym_config.enabled = update.enabled
    sym_config.take_profit_spacing = update.take_profit_spacing
    sym_config.grid_spacing = update.grid_spacing
    sym_config.initial_quantity = update.initial_quantity
    
    save_config(config)
    
    logger.info(f"Updated symbol: {symbol}")
    
    return {"status": "updated", "symbol": symbol}


@router.delete("/{symbol}")
def delete_symbol(symbol: str):
    """
    刪除交易對
    
    對應 GUI: SymbolsPage 刪除
    """
    config = load_config()
    
    if symbol not in config.symbols:
        raise HTTPException(404, f"Symbol {symbol} not found")
    
    del config.symbols[symbol]
    save_config(config)
    
    logger.info(f"Deleted symbol: {symbol}")
    
    return {"status": "deleted", "symbol": symbol}


@router.post("/{symbol}/toggle")
def toggle_symbol(symbol: str):
    """
    切換交易對啟用狀態
    """
    config = load_config()
    
    if symbol not in config.symbols:
        raise HTTPException(404, f"Symbol {symbol} not found")
    
    sym_config = config.symbols[symbol]
    sym_config.enabled = not sym_config.enabled
    save_config(config)
    
    status = "enabled" if sym_config.enabled else "disabled"
    logger.info(f"Toggled symbol {symbol}: {status}")
    
    return {"status": status, "symbol": symbol, "enabled": sym_config.enabled}


@router.post("/toggle-all")
def toggle_all_symbols(enabled: bool):
    """
    批量啟用/停用所有交易對
    """
    config = load_config()
    
    count = 0
    for sym_config in config.symbols.values():
        sym_config.enabled = enabled
        count += 1
    
    save_config(config)
    
    status = "enabled" if enabled else "disabled"
    logger.info(f"Toggled all {count} symbols: {status}")
    
    return {"status": status, "count": count}
