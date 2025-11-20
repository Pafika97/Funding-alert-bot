import os
import asyncio
import logging
from typing import List, Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import ccxt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MIN_FUNDING_RATE = float(os.getenv("MIN_FUNDING_RATE", "0.005"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
EXCHANGES_LIST = [ex.strip() for ex in os.getenv("EXCHANGES","binance,okx,bybit,bitget,kucoin,gate,huobi,kraken,mexc,bitmex").split(",")]

def create_exchanges():
    exchanges={}
    for ex_id in EXCHANGES_LIST:
        try:
            if not hasattr(ccxt, ex_id):
                continue
            exchanges[ex_id]=getattr(ccxt, ex_id)({"enableRateLimit":True})
        except:
            continue
    return exchanges

async def fetch_funding_for_exchange(ex_id, ex):
    alerts=[]
    if not ex.has.get("fetchFundingRates"):
        return alerts
    try:
        data=await asyncio.to_thread(ex.fetchFundingRates)
    except:
        return alerts
    iterable=data.values() if isinstance(data, dict) else data
    for item in iterable:
        rate=item.get("fundingRate")
        symbol=item.get("symbol")
        if rate and rate>MIN_FUNDING_RATE:
            alerts.append({"exchange":ex_id,"symbol":symbol,"funding_rate":rate})
    return alerts

async def watcher(bot):
    exs=create_exchanges()
    while True:
        all_alerts=[]
        for ex_id,ex in exs.items():
            all_alerts.extend(await fetch_funding_for_exchange(ex_id,ex))
        if all_alerts:
            msg="⚠️ High funding rate:
"
            for a in all_alerts:
                msg+=f"- {a['exchange']} {a['symbol']} = {a['funding_rate']*100:.4f}%
"
            await bot.send_message(CHAT_ID,msg)
        await asyncio.sleep(CHECK_INTERVAL)

async def cmd_start(msg:Message):
    await msg.answer("Funding monitoring activated.")

async def main():
    bot=Bot(BOT_TOKEN)
    dp=Dispatcher()
    dp.message.register(cmd_start,Command("start"))
    asyncio.create_task(watcher(bot))
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
