#!/usr/bin/env python3
"""
Data access layer — Layer 1
Sources: Akshare (A-shares) / Binance (Crypto) / News / Macro
All numbers from real APIs, LLM never generates numerical data
"""

import os, json, time, logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
logger = logging.getLogger(__name__)
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


class DataFetcher:
    """Multi-market data fetcher — all data from real APIs"""

    def get_cn_kline(self, symbol: str, period: str = "daily",
                     days: int = 365) -> pd.DataFrame:
        import akshare as ak
        try:
            end = datetime.now().strftime('%Y%m%d')
            start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            df = ak.stock_zh_a_hist(symbol=symbol, period=period,
                                    start_date=start, end_date=end, adjust="qfq")
            df.columns = ['date', 'open', 'close', 'high', 'low',
                          'volume', 'amount', 'amplitude', 'pct_change',
                          'change_amount', 'turnover']
            df['date'] = pd.to_datetime(df['date'])
            return df.sort_values('date').reset_index(drop=True)
        except Exception as e:
            logger.error(f"A-share fetch failed {symbol}: {e}")
            return pd.DataFrame()

    def get_cn_news(self, limit: int = 20) -> list:
        import akshare as ak
        try:
            df = ak.stock_news_em()
            return [{"title": str(r.get('标题','')), "content": str(r.get('内容',''))[:300],
                     "time": str(r.get('发布时间','')), "source": str(r.get('来源',''))}
                    for _, r in df.head(limit).iterrows()]
        except Exception as e:
            logger.error(f"News fetch failed: {e}")
            return []

    def get_crypto_kline(self, symbol: str = "BTCUSDT",
                         interval: str = "1d", limit: int = 365) -> list:
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
                timeout=15
            )
            resp.raise_for_status()
            return [{"time": k[0], "open": float(k[1]), "high": float(k[2]),
                     "low": float(k[3]), "close": float(k[4]), "volume": float(k[5])}
                    for k in resp.json()]
        except Exception as e:
            logger.error(f"Crypto fetch failed {symbol}: {e}")
            return []

    def get_crypto_kline_df(self, symbol="BTCUSDT", interval="1d", limit=365) -> pd.DataFrame:
        klines = self.get_crypto_kline(symbol, interval, limit)
        if not klines:
            return pd.DataFrame()
        df = pd.DataFrame(klines)
        df['date'] = pd.to_datetime(df['time'], unit='ms')
        return df

    def get_macro_data(self) -> dict:
        import akshare as ak
        macro = {}
        try:
            dxy = ak.macro_fx_dollar_index()
            macro['dxy'] = float(dxy['收盘'].iloc[-1])
        except:
            macro['dxy'] = None
        try:
            df = ak.stock_zh_a_spot_em()
            up = len(df[df['涨幅幅'] > 0])
            down = len(df[df['涨幅幅'] < 0])
            macro['cn_up_ratio'] = round(up / (up + down + 1), 3)
        except:
            macro['cn_up_ratio'] = None
        return macro
