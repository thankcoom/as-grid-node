# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/liutsungying/as網格/bitget_as/gui/app.py'],
    pathex=['/Users/liutsungying/as網格/bitget_as', '/Users/liutsungying/as網格/bitget_as/gui', '/Users/liutsungying/as網格/bitget_as/client', '/Users/liutsungying/as網格/bitget_as/core'],
    binaries=[],
    datas=[('/Users/liutsungying/as網格/bitget_as/config', 'config'), ('/Users/liutsungying/as網格/bitget_as/asBack/backtest_system', 'asBack/backtest_system'), ('/Users/liutsungying/as網格/bitget_as/asBack/data', 'asBack/data'), ('/Users/liutsungying/.pyenv/versions/3.10.12/lib/python3.10/site-packages/certifi/cacert.pem', 'certifi')],
    hiddenimports=['customtkinter', 'tkinter', 'PIL', 'PIL._tkinter_finder', 'ccxt', 'ccxt.async_support', 'ccxt.bitget', 'websockets', 'pandas', 'numpy', 'cryptography', 'cryptography.hazmat.primitives.ciphers.aead', 'aiohttp', 'certifi', 'ssl', 'logging.handlers', 'as_terminal_max_bitget', 'gui.pages', 'gui.pages.trading', 'gui.pages.symbols', 'gui.pages.backtest', 'gui.pages.coin_selection', 'gui.pages.settings', 'gui.components', 'gui.components.cards', 'gui.components.charts', 'gui.components.indicators', 'gui.components.inputs', 'gui.components.navigation', 'gui.dialogs', 'gui.dialogs.base', 'gui.dialogs.backtest_dialogs', 'gui.dialogs.rotation_dialogs', 'gui.dialogs.setup_dialogs', 'gui.dialogs.symbol_dialogs', 'gui.styles', 'gui.styles.colors', 'gui.trading_engine', 'core', 'core.config', 'core.constants', 'core.logging_setup', 'core.error_handler', 'core.path_resolver', 'client', 'client.license_manager', 'client.secure_storage', 'coin_selection', 'coin_selection.ranker', 'coin_selection.models', 'coin_selection.rotator', 'coin_selection.tracker', 'coin_selection.scorer', 'coin_selection.symbol_scanner', 'coin_selection.ws_provider', 'asBack', 'asBack.backtest_system', 'asBack.backtest_system.backtester', 'asBack.backtest_system.config', 'asBack.backtest_system.data_loader', 'asBack.backtest_system.optimizer', 'asBack.backtest_system.smart_optimizer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AS_Grid_Trading_Bitget',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/liutsungying/as網格/bitget_as/assets/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AS_Grid_Trading_Bitget',
)
app = BUNDLE(
    coll,
    name='AS_Grid_Trading_Bitget.app',
    icon='/Users/liutsungying/as網格/bitget_as/assets/icon.icns',
    bundle_identifier='com.louislab.asgrid.bitget',
)
