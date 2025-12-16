#!/usr/bin/env python3
"""
AS Grid Trading (Bitget) - PyInstaller 打包腳本
======================================

簡單的 MVP 打包方案：
- 打包成單一 .app 文件
- 用戶雙擊即可運行
- 包含所有依賴

使用方式:
    python build_pyinstaller.py          # 打包成 .app bundle
    python build_pyinstaller.py --clean  # 清理並重新打包
    python build_pyinstaller.py --dmg    # 打包並創建 DMG
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

# 應用程式設定 - Bitget 版本
APP_NAME = "AS_Grid_Trading_Bitget"
ENTRY_POINT = PROJECT_ROOT / "gui" / "app.py"

# Icon 設定
ICON_ICNS = PROJECT_ROOT / "assets" / "icon.icns"
ICON_ICO = PROJECT_ROOT / "assets" / "icon.ico"


def get_icon_path():
    """根據平台獲取正確的圖示路徑"""
    if sys.platform == "win32":
        if ICON_ICO.exists():
            return ICON_ICO
    elif sys.platform == "darwin":
        if ICON_ICNS.exists():
            return ICON_ICNS
    return None


def clean():
    """Clean old build files"""
    print("Cleaning old files...")

    dirs_to_clean = [
        DIST_DIR,
        BUILD_DIR,
        PROJECT_ROOT / f"{APP_NAME}.spec",
    ]

    for path in dirs_to_clean:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  Deleted dir: {path}")
            else:
                path.unlink()
                print(f"  Deleted file: {path}")


def get_hidden_imports():
    """獲取需要額外包含的模組"""
    return [
        # GUI 相關
        "customtkinter",
        "tkinter",
        "PIL",
        "PIL._tkinter_finder",

        # 交易相關
        "ccxt",
        "ccxt.async_support",
        "ccxt.bitget",  # Bitget 專用
        "websockets",

        # 數據處理
        "pandas",
        "numpy",

        # 加密相關
        "cryptography",
        "cryptography.hazmat.primitives.ciphers.aead",

        # 網路相關
        "aiohttp",
        "certifi",
        "ssl",

        # 日誌
        "logging.handlers",

        # ★ 主交易引擎（非常重要！）
        "as_terminal_max_bitget",

        # GUI 頁面
        "gui.pages",
        "gui.pages.trading",
        "gui.pages.symbols",
        "gui.pages.backtest",
        "gui.pages.coin_selection",
        "gui.pages.settings",

        # GUI 元件（補充完整）
        "gui.components",
        "gui.components.cards",
        "gui.components.charts",
        "gui.components.indicators",
        "gui.components.inputs",
        "gui.components.navigation",

        # GUI 對話框（補充完整）
        "gui.dialogs",
        "gui.dialogs.base",
        "gui.dialogs.backtest_dialogs",
        "gui.dialogs.rotation_dialogs",
        "gui.dialogs.setup_dialogs",
        "gui.dialogs.symbol_dialogs",

        # GUI 樣式（補充完整）
        "gui.styles",
        "gui.styles.colors",

        # 交易引擎
        "gui.trading_engine",

        # 核心模組
        "core",
        "core.config",
        "core.constants",
        "core.logging_setup",
        "core.error_handler",
        "core.path_resolver",

        # 客戶端模組
        "client",
        "client.license_manager",
        "client.secure_storage",

        # 選幣模組
        "coin_selection",
        "coin_selection.ranker",
        "coin_selection.models",
        "coin_selection.rotator",
        "coin_selection.tracker",
        "coin_selection.scorer",
        "coin_selection.symbol_scanner",
        "coin_selection.ws_provider",

        # 回測系統
        "asBack",
        "asBack.backtest_system",
        "asBack.backtest_system.backtester",
        "asBack.backtest_system.config",
        "asBack.backtest_system.data_loader",
        "asBack.backtest_system.optimizer",
        "asBack.backtest_system.smart_optimizer",
    ]


def get_data_files():
    """獲取需要包含的數據文件"""
    data = []

    # 配置文件
    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        data.append((str(config_dir), "config"))

    # asBack 回測系統
    asback_dir = PROJECT_ROOT / "asBack"
    if asback_dir.exists():
        # 只包含必要的回測文件
        backtest_system = asback_dir / "backtest_system"
        if backtest_system.exists():
            data.append((str(backtest_system), "asBack/backtest_system"))

        # 數據目錄（如果有）
        data_dir = asback_dir / "data"
        if data_dir.exists():
            data.append((str(data_dir), "asBack/data"))

    # SSL 證書
    import certifi
    data.append((certifi.where(), "certifi"))

    return data


def build_app():
    """Build using PyInstaller"""
    print(f"\nStarting build for {APP_NAME}...")
    print(f"Entry point: {ENTRY_POINT}")

    # Ensure entry point exists
    if not ENTRY_POINT.exists():
        print(f"Error: Entry point not found {ENTRY_POINT}")
        sys.exit(1)

    # Build PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",  # macOS .app bundle / Windows no console
        "--noconfirm",
        "--clean",

        # macOS specific - Bitget version
        "--osx-bundle-identifier", "com.louislab.asgrid.bitget",
    ]

    # 添加 icon（如果存在）
    icon_path = get_icon_path()
    if icon_path:
        cmd.extend(["--icon", str(icon_path)])

    # 添加隱藏導入
    for module in get_hidden_imports():
        cmd.extend(["--hidden-import", module])

    # 添加數據文件
    for src, dest in get_data_files():
        cmd.extend(["--add-data", f"{src}:{dest}"])

    # 添加路徑
    cmd.extend(["--paths", str(PROJECT_ROOT)])
    cmd.extend(["--paths", str(PROJECT_ROOT / "gui")])
    cmd.extend(["--paths", str(PROJECT_ROOT / "client")])
    cmd.extend(["--paths", str(PROJECT_ROOT / "core")])

    # 工作目錄和輸出目錄
    cmd.extend(["--workpath", str(BUILD_DIR)])
    cmd.extend(["--distpath", str(DIST_DIR)])
    cmd.extend(["--specpath", str(PROJECT_ROOT)])

    # 入口點
    cmd.append(str(ENTRY_POINT))

    print("\nExecuting command:")
    print(" ".join(cmd[:10]) + " ...")

    # Execute build
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode != 0:
        print("\nBuild Failed!")
        sys.exit(1)

    print("\nBuild Success!")

    # Copy asBack to Frameworks (macOS)
    app_path = DIST_DIR / f"{APP_NAME}.app"
    if app_path.exists():
        copy_asback_to_app(app_path)

    return app_path


def copy_asback_to_app(app_path: Path):
    """複製 asBack 到 .app bundle 的 Frameworks 目錄"""
    print("\n複製 asBack 到 .app bundle...")

    frameworks_dir = app_path / "Contents" / "Frameworks"
    frameworks_dir.mkdir(parents=True, exist_ok=True)

    asback_src = PROJECT_ROOT / "asBack"
    asback_dest = frameworks_dir / "asBack"

    if asback_src.exists():
        if asback_dest.exists():
            # 處理符號連結的情況
            if asback_dest.is_symlink():
                asback_dest.unlink()
            else:
                shutil.rmtree(asback_dest)

        # 只複製必要的文件
        shutil.copytree(
            asback_src,
            asback_dest,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                ".DS_Store",
                "_archive",
            )
        )
        print(f"  已複製: {asback_dest}")


def create_dmg(app_path: Path):
    """創建專業 DMG 安裝檔（使用 create-dmg）"""
    print("\n創建 DMG...")

    dmg_path = DIST_DIR / f"{APP_NAME}.dmg"
    icon_path = get_icon_path()

    # 刪除舊的 DMG
    if dmg_path.exists():
        dmg_path.unlink()

    # 使用 create-dmg 製作專業 DMG
    cmd = [
        "create-dmg",
        "--volname", APP_NAME,
        "--volicon", str(icon_path) if icon_path else "",
        "--window-pos", "200", "120",
        "--window-size", "600", "400",
        "--icon-size", "100",
        "--icon", f"{APP_NAME}.app", "150", "190",
        "--hide-extension", f"{APP_NAME}.app",
        "--app-drop-link", "450", "190",
        "--no-internet-enable",
        str(dmg_path),
        str(app_path)
    ]

    # 移除空的 volicon 參數
    if not icon_path:
        cmd = [c for c in cmd if c != "--volicon" and c != ""]

    print("  使用 create-dmg 製作專業安裝檔...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0 and dmg_path.exists():
        print(f"DMG 創建成功: {dmg_path}")
        print(f"檔案大小: {dmg_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print(f"create-dmg 失敗，使用備用方案...")
        if result.stderr:
            print(f"  錯誤: {result.stderr[:200]}")
        # 備用：使用基本 hdiutil
        _create_dmg_fallback(app_path, dmg_path)


def _create_dmg_fallback(app_path: Path, dmg_path: Path):
    """備用 DMG 創建方案"""
    temp_dmg_dir = DIST_DIR / "dmg_contents"

    if temp_dmg_dir.exists():
        shutil.rmtree(temp_dmg_dir)

    temp_dmg_dir.mkdir(parents=True)
    shutil.copytree(app_path, temp_dmg_dir / app_path.name, symlinks=True)

    # 創建 Applications 符號連結
    (temp_dmg_dir / "Applications").symlink_to("/Applications")

    # 創建安裝說明檔案
    readme_content = """============================================
  AS Grid Trading (Bitget) 安裝說明
============================================

【安裝步驟】
1. 將 AS_Grid_Trading_Bitget.app 拖拽到右側 Applications 資料夾
2. 前往 Applications，找到 AS_Grid_Trading_Bitget
3. 右鍵點擊 → 選擇「打開」

【重要】首次開啟時的安全提示

macOS 會對從網路下載的應用程式進行安全檢查。
如果出現「已損壞，無法打開」的錯誤，請：

方法一：終端機命令（推薦）
1. 開啟「終端機」(Terminal)
2. 執行：
   xattr -cr /Applications/AS_Grid_Trading_Bitget.app
3. 再次開啟 App

方法二：系統偏好設定
1. 嘗試開啟 App（會顯示錯誤）
2. 前往「系統偏好設定」→「安全性與隱私」
3. 點擊「仍要打開」

============================================
"""
    readme_path = temp_dmg_dir / "安裝說明.txt"
    readme_path.write_text(readme_content, encoding="utf-8")

    cmd = [
        "hdiutil", "create",
        "-volname", APP_NAME,
        "-srcfolder", str(temp_dmg_dir),
        "-ov", "-format", "UDZO",
        str(dmg_path)
    ]

    result = subprocess.run(cmd)
    shutil.rmtree(temp_dmg_dir)

    if result.returncode == 0:
        print(f"DMG 創建成功（備用方案）: {dmg_path}")
        print(f"檔案大小: {dmg_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("DMG 創建失敗")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AS Grid Trading (Bitget) 打包腳本")
    parser.add_argument("--clean", action="store_true", help="清理並重新打包")
    parser.add_argument("--dmg", action="store_true", help="創建 DMG 安裝檔")
    args = parser.parse_args()

    print("=" * 60)
    print("AS Grid Trading (Bitget) - PyInstaller 打包")
    print("=" * 60)

    # 切換到項目目錄
    os.chdir(PROJECT_ROOT)

    # 清理（如果需要）
    if args.clean:
        clean()

    # 打包
    app_path = build_app()

    # 創建 DMG（如果需要）
    if args.dmg and sys.platform == "darwin":
        create_dmg(app_path)

    print("\n" + "=" * 60)
    print("打包完成!")
    print("=" * 60)

    if sys.platform == "darwin":
        print(f"\n.app 位置: {DIST_DIR / f'{APP_NAME}.app'}")
        print(f"\n運行方式:")
        print(f"  1. 雙擊 .app 文件")
        print(f"  2. 或拖拽到 Applications 目錄")
    else:
        print(f"\n執行檔位置: {DIST_DIR / APP_NAME}")


if __name__ == "__main__":
    main()
