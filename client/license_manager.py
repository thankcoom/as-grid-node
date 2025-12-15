"""
AS Grid Trading - 授權管理模組 (Bitget 版本)

負責：
1. 獲取 Bitget UID
2. 與驗證伺服器通訊
3. 維持心跳
4. 處理授權失敗

Bitget API 文檔參考：
- https://www.bitget.com/api-doc/spot/account/Get-Account-Info
- API 端點: GET /api/v2/spot/account/info
- 回應格式: {"code":"00000","data":{"userId":"xxx",...}}
"""

import asyncio
import hashlib
import platform
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime

import aiohttp
import ssl
import certifi

logger = logging.getLogger(__name__)

# 創建 SSL context 用於 HTTPS 連線
def _create_ssl_context():
    """創建 SSL context，使用 certifi 的證書"""
    try:
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


class LicenseManager:
    """
    授權管理器

    使用範例：
    ```python
    license_mgr = LicenseManager(exchange, server_url)

    # 驗證授權
    result = await license_mgr.verify()
    if not result["success"]:
        print(f"授權失敗: {result['reason']}")
        return

    # 開始交易...

    # 程式結束時
    await license_mgr.logout()
    ```
    """

    # 心跳間隔（秒）
    HEARTBEAT_INTERVAL = 300  # 5 分鐘

    def __init__(
        self,
        exchange,
        server_url: str,
        version: str = "1.0.0"
    ):
        """
        初始化授權管理器

        Args:
            exchange: ccxt 交易所實例
            server_url: 驗證伺服器 URL
            version: 軟體版本
        """
        self.exchange = exchange
        self.server_url = server_url.rstrip('/')
        self.version = version

        self.uid: Optional[str] = None
        self.session_token: Optional[str] = None
        self.user_info: Optional[Dict] = None
        self.machine_id = self._generate_machine_id()

        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stats: Dict[str, Any] = {}

    def _generate_machine_id(self) -> str:
        """生成硬體指紋"""
        info = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
        return hashlib.sha256(info.encode()).hexdigest()[:32]

    def _get_platform(self) -> str:
        """取得平台名稱"""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        return system

    async def get_bitget_uid(self) -> str:
        """
        獲取 Bitget UID

        API 文檔: https://www.bitget.com/api-doc/spot/account/Get-Account-Info
        端點: GET /api/v2/spot/account/info
        回應: {"code":"00000","data":{"userId":"xxx",...}}

        Returns:
            用戶的 Bitget UID
        """
        errors = []

        try:
            # 方法 1: 使用 V2 Spot Account API (推薦)
            # GET /api/v2/spot/account/info
            try:
                account_info = await self.exchange.privateSpotGetV2SpotAccountInfo()
                logger.debug(f"V2 Spot Account Info 回應: {account_info}")
                if account_info and account_info.get('code') == '00000':
                    data = account_info.get('data', {})
                    uid = str(data.get('userId', '') or data.get('uid', ''))
                    if uid and uid.isdigit():
                        self.uid = uid
                        logger.info(f"從 V2 Spot API 獲取 UID: {self.uid}")
            except Exception as e:
                errors.append(f"V2 Spot: {str(e)[:50]}")

            # 方法 2: 使用 V2 Mix (合約) Account API
            # GET /api/v2/mix/account/accounts
            if not self.uid:
                try:
                    # 需要 productType 參數
                    mix_info = await self.exchange.privateMixGetV2MixAccountAccounts({
                        'productType': 'USDT-FUTURES'
                    })
                    logger.debug(f"V2 Mix Account Info 回應: {mix_info}")
                    if mix_info and mix_info.get('code') == '00000':
                        data = mix_info.get('data', [])
                        if isinstance(data, list) and len(data) > 0:
                            uid = str(data[0].get('userId', '') or data[0].get('uid', ''))
                            if uid and uid.isdigit():
                                self.uid = uid
                                logger.info(f"從 V2 Mix API 獲取 UID: {self.uid}")
                except Exception as e:
                    errors.append(f"V2 Mix: {str(e)[:50]}")

            # 方法 3: 嘗試 V1 Spot Account API (舊版備用)
            if not self.uid:
                try:
                    account_info_v1 = await self.exchange.privateSpotGetSpotV1AccountGetInfo()
                    logger.debug(f"V1 Spot Account Info 回應: {account_info_v1}")
                    if account_info_v1 and 'data' in account_info_v1:
                        data = account_info_v1.get('data', {})
                        uid = str(data.get('userId', '') or data.get('uid', ''))
                        if uid and uid.isdigit():
                            self.uid = uid
                            logger.info(f"從 V1 Spot API 獲取 UID: {self.uid}")
                except Exception as e:
                    errors.append(f"V1 Spot: {str(e)[:50]}")

            # 方法 4: 通過 fetch_balance 嘗試獲取
            if not self.uid:
                try:
                    balance = await self.exchange.fetch_balance()
                    info = balance.get('info', {})
                    logger.debug(f"fetch_balance info: {info}")
                    if isinstance(info, dict):
                        uid = str(info.get('userId', '') or info.get('uid', ''))
                        if uid and uid.isdigit():
                            self.uid = uid
                            logger.info(f"從 fetch_balance 獲取 UID: {self.uid}")
                except Exception as e:
                    errors.append(f"Balance: {str(e)[:50]}")

            # 方法 5: 通過 privateUserGetUserV1FeeQuery 獲取
            if not self.uid:
                try:
                    fee_info = await self.exchange.privateUserGetUserV1FeeQuery()
                    logger.debug(f"Fee Query 回應: {fee_info}")
                    if fee_info and 'data' in fee_info:
                        data = fee_info.get('data', {})
                        uid = str(data.get('userId', '') or data.get('uid', ''))
                        if uid and uid.isdigit():
                            self.uid = uid
                            logger.info(f"從 Fee Query API 獲取 UID: {self.uid}")
                except Exception as e:
                    errors.append(f"Fee: {str(e)[:50]}")

            # 方法 6: 通過 V1 Mix Account 獲取
            if not self.uid:
                try:
                    mix_v1 = await self.exchange.privateMixGetMixV1AccountAccounts({
                        'productType': 'umcbl'
                    })
                    logger.debug(f"V1 Mix Account 回應: {mix_v1}")
                    if mix_v1 and 'data' in mix_v1:
                        data = mix_v1.get('data', [])
                        if isinstance(data, list) and len(data) > 0:
                            uid = str(data[0].get('userId', '') or data[0].get('uid', ''))
                            if uid and uid.isdigit():
                                self.uid = uid
                                logger.info(f"從 V1 Mix API 獲取 UID: {self.uid}")
                except Exception as e:
                    errors.append(f"V1Mix: {str(e)[:50]}")

            # 方法 7: 通過訂單歷史獲取
            if not self.uid:
                try:
                    orders = await self.exchange.fetch_orders(limit=1)
                    if orders and len(orders) > 0:
                        info = orders[0].get('info', {})
                        uid = str(info.get('userId', '') or info.get('uid', ''))
                        if uid and uid.isdigit():
                            self.uid = uid
                            logger.info(f"從訂單獲取 UID: {self.uid}")
                except Exception as e:
                    errors.append(f"Orders: {str(e)[:50]}")

            if not self.uid:
                if errors:
                    error_detail = "; ".join(errors)[:150]
                    raise ValueError(f"無法獲取 Bitget UID ({error_detail})")
                else:
                    raise ValueError("無法獲取 Bitget UID，請確認 API 權限")

            return self.uid

        except ValueError:
            raise
        except Exception as e:
            # 清理錯誤訊息（移除 HTML 內容）
            error_msg = str(e)
            if '<html' in error_msg.lower() or '<!doctype' in error_msg.lower():
                if '404' in error_msg:
                    error_msg = "API 無法訪問合約帳戶（請確認 API 有合約權限）"
                elif '401' in error_msg or '403' in error_msg:
                    error_msg = "API Key 無效或權限不足"
                elif 'passphrase' in error_msg.lower() or 'password' in error_msg.lower():
                    error_msg = "Passphrase 錯誤，請檢查 API 設定"
                else:
                    error_msg = "API 請求失敗"
            logger.error(f"獲取 Bitget UID 失敗: {error_msg}")
            raise ValueError(error_msg)

    async def verify(self) -> Dict[str, Any]:
        """
        向伺服器驗證授權

        Returns:
            {
                "success": True/False,
                "user": {...},  # 成功時
                "reason": "..."  # 失敗時
            }
        """
        try:
            # 獲取 UID (Bitget 版本)
            if not self.uid:
                await self.get_bitget_uid()

            # 發送驗證請求（使用 SSL context）
            connector = aiohttp.TCPConnector(ssl=_create_ssl_context())
            async with aiohttp.ClientSession(connector=connector) as session:
                payload = {
                    "uid": self.uid,
                    "machine_id": self.machine_id,
                    "version": self.version,
                    "platform": self._get_platform()
                }

                async with session.post(
                    f"{self.server_url}/api/verify",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    # 檢查 Content-Type，確保是 JSON
                    content_type = resp.headers.get('Content-Type', '')
                    if 'application/json' not in content_type:
                        logger.warning(f"伺服器回應非 JSON 格式: {content_type}")
                        return {
                            "success": False,
                            "reason": "驗證伺服器回應格式錯誤"
                        }

                    try:
                        result = await resp.json()
                    except Exception as json_err:
                        logger.warning(f"JSON 解析失敗: {json_err}")
                        return {
                            "success": False,
                            "reason": "驗證伺服器回應無法解析"
                        }

                    if resp.status == 200 and result.get("status") == "ok":
                        self.session_token = result.get("session_token")
                        self.user_info = result.get("user")

                        # 啟動心跳任務
                        self._start_heartbeat()

                        logger.info(f"授權驗證成功: {self.user_info.get('nickname', 'Unknown')}")

                        return {
                            "success": True,
                            "user": self.user_info
                        }
                    else:
                        reason = result.get("reason", "驗證失敗")
                        logger.warning(f"授權驗證失敗: {reason}")

                        return {
                            "success": False,
                            "reason": reason
                        }

        except aiohttp.ClientError as e:
            logger.error(f"網路連接失敗: {e}")
            return {
                "success": False,
                "reason": f"無法連接驗證伺服器: {e}"
            }
        except Exception as e:
            logger.error(f"驗證過程發生錯誤: {e}")
            return {
                "success": False,
                "reason": f"驗證錯誤: {e}"
            }

    def _start_heartbeat(self):
        """啟動心跳任務"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """心跳循環"""
        while True:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"心跳發送失敗: {e}")

    async def send_heartbeat(self, stats: Optional[Dict] = None):
        """
        發送心跳

        Args:
            stats: 交易統計資料（可選）
        """
        if not self.session_token:
            return

        try:
            connector = aiohttp.TCPConnector(ssl=_create_ssl_context())
            async with aiohttp.ClientSession(connector=connector) as session:
                payload = {
                    "session_token": self.session_token,
                    "stats": stats or self._stats
                }

                async with session.post(
                    f"{self.server_url}/api/heartbeat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"心跳回應異常: {resp.status}")

        except Exception as e:
            logger.warning(f"心跳發送失敗: {e}")

    def update_stats(
        self,
        symbols: list = None,
        total_trades: int = None,
        total_pnl: float = None,
        positions: dict = None
    ):
        """
        更新統計資料（下次心跳時發送）

        Args:
            symbols: 交易中的幣種
            total_trades: 總交易筆數
            total_pnl: 總盈虧
            positions: 目前持倉
        """
        if symbols is not None:
            self._stats["symbols"] = symbols
        if total_trades is not None:
            self._stats["total_trades"] = total_trades
        if total_pnl is not None:
            self._stats["total_pnl"] = total_pnl
        if positions is not None:
            self._stats["positions"] = positions
        self._stats["updated_at"] = datetime.utcnow().isoformat()

    async def logout(self):
        """登出"""
        # 停止心跳
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        # 發送登出請求
        if self.session_token:
            try:
                connector = aiohttp.TCPConnector(ssl=_create_ssl_context())
                async with aiohttp.ClientSession(connector=connector) as session:
                    await session.post(
                        f"{self.server_url}/api/logout",
                        json={"session_token": self.session_token},
                        timeout=aiohttp.ClientTimeout(total=10)
                    )
            except Exception as e:
                logger.warning(f"登出請求失敗: {e}")

        self.session_token = None
        logger.info("已登出")

    @property
    def is_verified(self) -> bool:
        """是否已驗證"""
        return self.session_token is not None


# ========== 整合啟動流程 ==========

async def secure_startup(
    config: dict,
    server_url: str,
    version: str = "1.0.0"
):
    """
    安全啟動流程

    整合了：
    1. API 憑證加密解鎖
    2. 授權驗證

    Args:
        config: 包含 exchange 實例的配置
        server_url: 驗證伺服器 URL
        version: 軟體版本

    Returns:
        (exchange, license_manager) 或 (None, None) 如果失敗
    """
    from rich.console import Console
    from rich.prompt import Prompt
    from rich.panel import Panel
    from client.secure_storage import CredentialManager, check_password_strength

    console = Console()

    console.print(Panel.fit(
        "[bold blue]AS 網格交易系統[/bold blue]\n"
        "[dim]您的 API 資料使用 AES-256-GCM 加密[/dim]",
        border_style="blue"
    ))

    manager = CredentialManager()

    # ========== API 憑證處理 ==========

    if not manager.is_configured():
        # 首次設定 (Bitget 版本)
        console.print("\n[yellow]首次使用，請設定 Bitget API 憑證[/yellow]\n")

        api_key = Prompt.ask("請輸入 Bitget API Key")
        api_secret = Prompt.ask("請輸入 Bitget API Secret", password=True)
        passphrase = Prompt.ask("請輸入 Bitget Passphrase", password=True)

        console.print("\n[cyan]請設定加密密碼[/cyan]")
        console.print("[dim]此密碼用於加密您的 API，請牢記！忘記密碼將無法恢復[/dim]\n")

        while True:
            password = Prompt.ask("設定密碼", password=True)
            level, level_name, suggestions = check_password_strength(password)

            if level < 2:
                console.print(f"[red]密碼強度：{level_name}[/red]")
                if suggestions:
                    console.print(f"[yellow]建議：{', '.join(suggestions)}[/yellow]\n")
                continue

            console.print(f"[green]密碼強度：{level_name}[/green]")

            confirm = Prompt.ask("確認密碼", password=True)
            if password != confirm:
                console.print("[red]密碼不一致，請重新輸入[/red]\n")
                continue

            break

        # 加密儲存 (包含 passphrase)
        try:
            manager.setup(api_key, api_secret, password, passphrase)
            console.print("\n[green]✓ API 憑證已安全加密儲存[/green]")
        except Exception as e:
            console.print(f"[red]設定失敗：{e}[/red]")
            return None, None

    else:
        # 解鎖
        console.print("\n[cyan]請輸入密碼解鎖[/cyan]\n")

        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            password = Prompt.ask("密碼", password=True)

            try:
                api_key, api_secret, passphrase = manager.unlock(password)
                console.print("[green]✓ 解鎖成功[/green]\n")
                break
            except ValueError:
                attempts += 1
                remaining = max_attempts - attempts
                if remaining > 0:
                    console.print(f"[red]密碼錯誤，還剩 {remaining} 次機會[/red]")
                else:
                    console.print("[red]密碼錯誤次數過多，程式結束[/red]")
                    return None, None

    # 清除密碼變數
    password = None

    # ========== 初始化交易所 (Bitget) ==========

    import ccxt.async_support as ccxt

    try:
        exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': api_secret,
            'password': passphrase,  # Bitget 需要 passphrase
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',  # Bitget 永續合約
            }
        })

        # 測試連接
        await exchange.load_markets()
        console.print("[green]✓ Bitget 交易所連接成功[/green]")

    except Exception as e:
        console.print(f"[red]Bitget 交易所連接失敗：{e}[/red]")
        return None, None

    # ========== 授權驗證 ==========

    console.print("\n[yellow]正在驗證授權...[/yellow]")

    license_mgr = LicenseManager(exchange, server_url, version)

    result = await license_mgr.verify()

    if not result["success"]:
        console.print(f"[bold red]授權驗證失敗: {result['reason']}[/bold red]")
        console.print("[yellow]請聯繫管理員獲取授權[/yellow]")
        await exchange.close()
        return None, None

    user = result.get("user", {})
    console.print(f"[bold green]✓ 授權驗證成功！歡迎 {user.get('nickname', 'Unknown')}[/bold green]\n")

    # 清除 API 變數（交易所已經有副本）
    api_key = None
    api_secret = None

    return exchange, license_mgr


# ========== 測試 ==========

if __name__ == "__main__":
    print("授權管理模組")
    print("請在主程式中整合使用")
