"""
GUI 頁面模組

包含所有主要頁面元件
"""

from .trading import TradingPage
from .symbols import SymbolsPage
from .backtest import BacktestPage
from .coin_selection import CoinSelectionPage
from .settings import SettingsPage

__all__ = [
    'TradingPage',
    'SymbolsPage',
    'BacktestPage',
    'CoinSelectionPage',
    'SettingsPage',
]
