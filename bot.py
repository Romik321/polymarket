import asyncio
import requests
import time
from collections import defaultdict
from telegram import Bot

# =========================
# CONFIG
# =========================
TOKEN = "8654063600:AAE0ly-nTplNPdXfJ3YXlGGB1h9UKFaaDws"
CHAT_ID = -1003918506453

bot = Bot(token=TOKEN)

wallet_history = {}

# =========================
# 🔥 BTC 15M MARKETS (LIVE)
# =========================
def get_btc_markets():
    url = "https://gamma-api.polymarket.com/markets"

    res = requests.get(url, timeout=10)
    data = res.json()

    markets = []

    for m in data:
        q = m.get("question", "").lower()

        if "btc" in q and ("15" in q or "15m" in q):
            markets.append(m["conditionId"])

    return markets


# =========================
# 🔥 GET RECENT TRADES (15–30 MIN)
# =========================
def get_trades(condition_id):
    url = f"https://data-api.polymarket.com/trades?conditionId={condition_id}"

    try:
        res = requests.get(url, timeout=10)
        data = res.json()

        now = time.time()
        recent = []

        for t in data:
            ts = t.get("timestamp", 0)

            # 🔥 last 30 minutes only
            if now - ts <= 1800:
                recent.append(t)

        return recent

    except:
        return []


# =========================
# 🔥 BUILD LIVE WALLET STATS
# =========================
def build_wallets():
    markets = get_btc_markets()

    wallet_stats = defaultdict(lambda: {
        "volume": 0,
        "trades": 0
    })

    for market in markets:
        trades = get_trades(market)

        for t in trades:
            addr = t.get("user")
            size = t.get("size", 0)

            if not addr:
                continue

            wallet_stats[addr]["trades"] += 1
            wallet_stats[addr]["volume"] += size

    result = []

    for addr, s in wallet_stats.items():

        # 🔥 active trader filter
        if s["trades"] < 3:
            continue

        avg_size = s["volume"] / s["trades"]

        # 🔥 remove low-quality traders
        if avg_size < 1:
            continue

        # 🔥 trend tracking
        trend = "➖"
        if addr in wallet_history:
            prev = wallet_history[addr]

            if s["volume"] > prev:
                trend = "📈 Increasing"
            elif s["volume"] < prev:
                trend = "📉 Decreasing"

        wallet_history[addr] = s["volume"]

        result.append({
            "address": addr,
            "trades": s["trades"],
            "volume": s["volume"],
            "avg": avg_size,
            "trend": trend
        })

    return result


# =========================
# 🔥 TOP 10
# =========================
def get_top_wallets():
    wallets = build_wallets()

    wallets.sort(key=lambda x: (x["volume"], x["trades"]), reverse=True)

    return wallets[:10]


# =========================
# 🔥 SEND MESSAGE
# =========================
async def send_data():
    wallets = get_top_wallets()

    message = "🔥 BTC 15M LIVE ACTIVE TRADERS\n\n"

    if not wallets:
        message += "No active traders right now..."
    else:
        for i, w in enumerate(wallets, start=1):

            link = f"https://polymarket.com/profile/{w['address']}"

            message += (
                f"{i}. <a href='{link}'>{w['address'][:6]}...{w['address'][-4:]}</a>\n"
                f"Trades (30m): {w['trades']}\n"
                f"Volume: ${round(w['volume'],2)}\n"
                f"Avg Size: ${round(w['avg'],2)}\n"
                f"{w['trend']}\n\n"
            )

    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")


# =========================
# LOOP
# =========================
async def main():
    while True:
        print("Scanning LIVE BTC 15m traders...")

        try:
            await send_data()
        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(120)


asyncio.run(main())
