import asyncio
import os
import logging
from trading_core.bot import MaxGridBot
from trading_core.models import GlobalConfig, SymbolConfig

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.bot = None
        self.task = None

    def start(self, symbol: str, quantity: float):
        if self.bot and self.bot.state.running:
            raise ValueError("Bot is already running")

        api_key = os.getenv("EXCHANGE_API_KEY")
        api_secret = os.getenv("EXCHANGE_SECRET")
        passphrase = os.getenv("EXCHANGE_PASSPHRASE")

        if not api_key or not api_secret:
            raise ValueError("API Keys not found in environment variables")

        config = GlobalConfig()
        config.api_key = api_key
        config.api_secret = api_secret
        config.passphrase = passphrase
        config.symbols.clear()
        
        coin = symbol.replace("USDT", "")
        ccxt_symbol = f"{coin}/USDT:USDT"
        
        config.symbols[symbol] = SymbolConfig(
            symbol=symbol,
            ccxt_symbol=ccxt_symbol,
            enabled=True,
            initial_quantity=quantity
        )

        self.bot = MaxGridBot(config)
        
        async def run():
            try:
                await self.bot.run()
            except Exception as e:
                logger.error(f"Bot crashed: {e}")
            finally:
                self.bot = None

        self.task = asyncio.create_task(run())
        return {"status": "started"}

    async def stop(self):
        if self.bot:
            await self.bot.stop()
        if self.task:
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.bot = None
        return {"status": "stopped"}

    def get_status(self):
        if not self.bot:
            return {"status": "stopped"}
        
        return {
            "status": "running",
            "pnl": self.bot.state.total_profit,
            "positions": [
                {"symbol": s.symbol, "long": s.long_position, "short": s.short_position}
                for s in self.bot.state.symbols.values()
            ]
        }

bot_manager = BotManager()
