import json
import threading
from datetime import datetime
from typing import List

import websocket  # websocket-client

from storage.db import insert_tick, init_db

# Match the HTML collector: one WS per symbol on fstream. [file:1][web:22]
BINANCE_FUTURES_WS_TEMPLATE = "wss://fstream.binance.com/ws/{sym}@trade"


def _normalize_trade(j: dict) -> dict:
    """
    Mirror the JS normalize(j):

    const ts = new Date(j.T || j.E).toISOString();
    return {symbol:j.s, ts, price:Number(j.p), size:Number(j.q)};
    """
    # T (trade time) or E (event time)
    t_ms = j.get("T") or j.get("E")
    if t_ms is None:
        ts = datetime.utcnow()
    else:
        ts = datetime.utcfromtimestamp(t_ms / 1000.0)

    symbol = j.get("s")
    price = float(j.get("p", 0.0))
    size = float(j.get("q", 0.0))  # HTML calls this "size"

    return {
        "symbol": symbol,
        "ts": ts,
        "price": price,
        "size": size,
    }


class BinanceFuturesTickIngestor:
    """
    Python equivalent of your HTML Binance Futures collector:
    - one WebSocket per symbol
    - only trade events (e === 'trade')
    - normalized to {symbol, ts, price, size}
    - stored into DB as qty=size
    """

    def __init__(self, symbols: List[str]):
        self.symbols = [s.lower() for s in symbols]
        self._threads: List[threading.Thread] = []
        self._running = False

    def _run_for_symbol(self, sym: str):
        url = BINANCE_FUTURES_WS_TEMPLATE.format(sym=sym)
        print(f"[WS] Connecting futures stream: {url}")

        def on_message(ws, message):
            try:
                j = json.loads(message)
            except Exception:
                return

            # Futures trade stream emits a trade object directly
            # or in some cases a dict with event type j['e'] === 'trade'
            if isinstance(j, dict) and j.get("e") == "trade":
                norm = _normalize_trade(j)
            else:
                # If format differs, try to access as nested "data"
                data = j.get("data") if isinstance(j, dict) else None
                if not isinstance(data, dict) or data.get("e") != "trade":
                    return
                norm = _normalize_trade(data)

            # Store normalized tick: DB column "qty" is the HTML "size"
            insert_tick(
                symbol=norm["symbol"],
                ts=norm["ts"],
                price=norm["price"],
                qty=norm["size"],
            )

        def on_open(ws):
            print(f"[WS] Opened for {sym}")

        def on_close(ws, code, msg):
            print(f"[WS] Closed for {sym} code={code} msg={msg}")

        def on_error(ws, err):
            print(f"[WS] Error for {sym}: {err}")

        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever()

    def start(self):
        if self._running:
            return
        self._running = True
        self._threads = []
        for sym in self.symbols:
            t = threading.Thread(target=self._run_for_symbol, args=(sym,), daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self):
        # WebSocketApp.run_forever() will exit when ws.close() is called,
        # but for simplicity we rely on process exit / restart for now.
        self._running = False
        print("[WS] Stop requested (threads daemon=True; will exit with process).")


_ingestor_instance = None


def get_or_create_ingestor(symbols: List[str]) -> BinanceFuturesTickIngestor:
    """
    Singleton-style entry used by app.py.
    """
    global _ingestor_instance
    if _ingestor_instance is None:
        init_db()
        _ingestor_instance = BinanceFuturesTickIngestor(symbols)
        _ingestor_instance.start()
    return _ingestor_instance
