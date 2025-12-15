"""
GUI 對話框模組

包含所有可重用的對話框元件
"""

from .base import ConfirmDialog
from .symbol_dialogs import AddSymbolDialog, EditSymbolDialog, AddFromCoinSelectDialog
from .backtest_dialogs import BacktestDialog, OptimizeDialog
from .setup_dialogs import SetupDialog, UnlockDialog, ChangeAPIDialog, MigrationDialog
from .rotation_dialogs import (
    RotationExecuteConfirmDialog,
    RotationConfirmDialog,
    RotationHistoryDialog
)

__all__ = [
    # 基礎
    'ConfirmDialog',
    # 交易對管理
    'AddSymbolDialog',
    'EditSymbolDialog',
    'AddFromCoinSelectDialog',
    # 回測優化
    'BacktestDialog',
    'OptimizeDialog',
    # 設定
    'SetupDialog',
    'UnlockDialog',
    'ChangeAPIDialog',
    'MigrationDialog',
    # 輪動
    'RotationExecuteConfirmDialog',
    'RotationConfirmDialog',
    'RotationHistoryDialog',
]
