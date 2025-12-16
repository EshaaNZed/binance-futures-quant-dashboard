import threading
from datetime import datetime
from typing import List

import numpy as np
import pandas as pd
from sqlalchemy import (
    Column, String, Float, DateTime, create_engine, Integer
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = create_engine("sqlite:///data.db", echo=False, future=True)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
_db_lock = threading.Lock()


class Tick(Base):
    __tablename__ = "ticks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, index=True)
    ts = Column(DateTime, index=True)
    price = Column(Float)
    qty = Column(Float)


class Bar(Base):
    __tablename__ = "bars"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, index=True)
    timeframe = Column(String, index=True)  # '1s','1m','5m'
    ts = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)


def init_db():
    Base.metadata.create_all(_engine)


def insert_tick(symbol: str, ts: datetime, price: float, qty: float):
    with _db_lock:
        session = SessionLocal()
        try:
            t = Tick(symbol=symbol, ts=ts, price=price, qty=qty)
            session.add(t)
            session.commit()
        finally:
            session.close()


def get_ticks(symbols: List[str], minutes_back: int = 60) -> pd.DataFrame:
    """Return recent ticks for given symbols."""
    from datetime import timedelta

    with _db_lock:
        session = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=minutes_back)
            q = (
                session.query(Tick)
                .filter(Tick.symbol.in_(symbols))
                .filter(Tick.ts >= cutoff)
            )
            rows = q.all()
        finally:
            session.close()

    if not rows:
        return pd.DataFrame(columns=["symbol", "ts", "price", "qty"])

    data = {
        "symbol": [r.symbol for r in rows],
        "ts": [r.ts for r in rows],
        "price": [r.price for r in rows],
        "qty": [r.qty for r in rows],
    }
    return pd.DataFrame(data)


def resample_ticks_to_bars(
    symbols: List[str],
    timeframe: str = "1m",
    minutes_back: int = 60,
) -> pd.DataFrame:
    """
    Resample ticks into OHLCV bars for the requested timeframe.
    timeframe: '1s','1m','5m'
    """
    freq_map = {"1s": "1S", "1m": "1T", "5m": "5T"}
    freq = freq_map.get(timeframe, "1T")

    df = get_ticks(symbols, minutes_back=minutes_back)
    if df.empty:
        return pd.DataFrame(columns=["symbol", "ts", "open", "high", "low", "close", "volume"])

    df = df.set_index("ts")
    bars_list = []

    for sym in symbols:
        sub = df[df["symbol"] == sym]
        if sub.empty:
            continue
        ohlc = (
            sub["price"]
            .resample(freq)
            .agg(["first", "max", "min", "last"])
            .rename(columns={"first": "open", "max": "high", "min": "low", "last": "close"})
        )
        vol = sub["qty"].resample(freq).sum()
        merged = ohlc.join(vol).rename(columns={"qty": "volume"})
        merged["symbol"] = sym
        merged = merged.dropna(subset=["open", "high", "low", "close"])
        merged = merged.reset_index().rename(columns={"ts": "ts"})
        bars_list.append(merged)

    if not bars_list:
        return pd.DataFrame(columns=["symbol", "ts", "open", "high", "low", "close", "volume"])

    bars = pd.concat(bars_list, ignore_index=True)

    # Optional: persist bars
    with _db_lock:
        session = SessionLocal()
        try:
            for _, row in bars.iterrows():
                b = Bar(
                    symbol=row["symbol"],
                    timeframe=timeframe,
                    ts=row["ts"].to_pydatetime(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"]),
                )
                session.add(b)
            session.commit()
        finally:
            session.close()

    return bars
