#!/usr/bin/env python3
"""Data persistence layer — saves all agent outputs to PostgreSQL"""

import os, json, logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
logger = logging.getLogger(__name__)


def get_conn():
    import psycopg2
    return psycopg2.connect(
        dbname='hedgefund', user='admin', password='Passw0rd',
        host='localhost', port=5432
    )


class AgentRunRepository:
    def save_run(self, agent_name, symbol=None, timeframe=None, status='running',
                 duration_ms=None, error_msg=None):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO agent_runs (agent_name, symbol, timeframe, status, duration_ms, error_msg) "
            "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
            (agent_name, symbol, timeframe, status, duration_ms, error_msg)
        )
        run_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return run_id

    def update_run(self, run_id, status, duration_ms=None, error_msg=None):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "UPDATE agent_runs SET status=%s, duration_ms=%s, error_msg=%s WHERE id=%s",
            (status, duration_ms, error_msg, run_id)
        )
        conn.commit()
        cur.close()
        conn.close()


class SignalRepository:
    def save_signal(self, run_id, symbol, timeframe, indicators: dict):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO technical_signals (run_id, symbol, timeframe, "
            "current_price, ma5, ma20, ma60, rsi14, atr14, volume_ratio, "
            "macd, macd_signal, golden_cross, pct_from_ma20) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (run_id, symbol, timeframe,
             indicators.get('current_price'), indicators.get('ma5'),
             indicators.get('ma20'), indicators.get('ma60'),
             indicators.get('rsi14'), indicators.get('atr14'),
             indicators.get('volume_ratio'), indicators.get('macd'),
             indicators.get('macd_signal'), indicators.get('golden_cross'),
             indicators.get('pct_from_ma20'))
        )
        conn.commit()
        cur.close()
        conn.close()


class AnalysisRepository:
    def save_analysis(self, run_id, agent_name, symbol, signal_type,
                      raw_input, raw_output, parsed_result, validation_passed):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ai_analyses (run_id, agent_name, symbol, signal_type, "
            "raw_input, raw_output, parsed_result, validation_layers_passed) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (run_id, agent_name, symbol, signal_type,
             raw_input[:10000] if raw_input else None,
             raw_output[:10000] if raw_output else None,
             json.dumps(parsed_result) if parsed_result else None,
             validation_passed)
        )
        conn.commit()
        cur.close()
        conn.close()


class ReportRepository:
    def save_report(self, report_date, market, summary, signals_summary,
                    news_summary, sentiment, push_status, push_channel):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO daily_reports (report_date, market, summary, "
            "signals_summary, news_summary, sentiment, push_status, push_channel) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
            "ON CONFLICT (report_date) DO UPDATE SET "
            "summary=EXCLUDED.summary, push_status=EXCLUDED.push_status",
            (report_date, market, summary,
             json.dumps(signals_summary) if signals_summary else None,
             json.dumps(news_summary) if news_summary else None,
             sentiment, push_status, push_channel)
        )
        conn.commit()
        cur.close()
        conn.close()
