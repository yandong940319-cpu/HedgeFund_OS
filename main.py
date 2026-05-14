#!/usr/bin/env python3
"""
AI Hedge Fund OS — Phase 1 Main Scheduler
Daily: fetch data -> analyze -> push report
"""

import os, sys, logging, json, time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "config", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(f"logs/hedge-fund-{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

from agents.data_fetcher import DataFetcher
from agents.technical_agent import TechnicalAgent, TechIndicators
from agents.repository import AgentRunRepository, SignalRepository, AnalysisRepository
from agents.feishu_pusher import send_feishu


def run_daily_analysis():
    """Full pipeline: Phase 1-4 integrated"""
    start_time = time.time()
    logger.info("=== AI Hedge Fund OS — Full Pipeline ===")

    fetcher = DataFetcher()
    tech_agent = TechnicalAgent()
    run_repo = AgentRunRepository()
    sig_repo = SignalRepository()
    ana_repo = AnalysisRepository()

    from signals.regime_detection import detect_regime
    from agents.voting_committee import VotingCommittee, CommitteeVote
    from agents.review_agent import ReviewAgent
    from knowledge.rag_knowledge import RAGKnowledge

    committee = VotingCommittee()
    rag = RAGKnowledge()

    signals = []
    news_items = []
    macro = {}
    all_votes = []
    regimes = {}

    # 1. Crypto analysis with regime detection + committee voting
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        run_id = run_repo.save_run("technical_agent", symbol, "1d", "running")

        try:
            df = fetcher.get_crypto_kline_df(symbol, "1d", 365)
            if df.empty:
                run_repo.update_run(run_id, "failed", error_msg="no data")
                continue

            # Regime Detection
            regime = detect_regime(df)
            regimes[symbol] = regime
            logger.info(f"{symbol} regime: {regime['regime']} ({regime['description']})")

            # Technical indicators (Python only)
            ind = TechIndicators.compute(df)
            sig_repo.save_signal(run_id, symbol, "1d", ind)

            # AI reasoning
            signal = tech_agent.analyze(symbol, df, "1d")
            if signal:
                signals.append({
                    "symbol": symbol, "trend": signal.trend,
                    "strength": signal.strength, "price": ind["current_price"],
                    "support": signal.support, "resistance": signal.resistance,
                    "reason": signal.key_reason, "rsi": ind["rsi14"],
                    "vol_ratio": ind["volume_ratio"],
                })
                ana_repo.save_analysis(
                    run_id, "technical_agent", symbol, "technical",
                    None, None, signal.model_dump(), 3
                )

                # Add to committee voting
                all_votes.append(CommitteeVote(
                    agent_name="technical_agent",
                    trend=signal.trend,
                    strength=signal.strength,
                    confidence=min(1.0, signal.strength / 10),
                    weight=committee.weights.get("technical_agent", 1.0),
                ))

                run_repo.update_run(run_id, "success",
                                    duration_ms=int((time.time() - start_time) * 1000))
            else:
                run_repo.update_run(run_id, "failed", error_msg="no signal")
        except Exception as e:
            run_repo.update_run(run_id, "failed", error_msg=str(e))
            logger.error(f"Analysis error {symbol}: {e}")

    # 2. Store results to RAG knowledge base
    if regimes:
        lines.append("[Market Regime]")
        for sym, r in regimes.items():
            lines.append(f"  {sym}: {r['regime']} - {r['description']}")
            lines.append(f"  Volatility: {r['volatility_pct']}%  |  "
                         f"Volume: {r['volume_ratio']}x")
        lines.append("")

    for sig in signals:
        rag.store_analysis(
            f"{sig['symbol']}_{datetime.now().strftime('%Y%m%d')}",
            json.dumps(sig, ensure_ascii=False),
            {"type": "technical_signal", "symbol": sig["symbol"],
             "date": datetime.now().strftime('%Y-%m-%d')}
        )

    # 3. Committee decision
    if all_votes:
        decision = committee.vote(all_votes)
        logger.info(f"Committee decision: {decision.final_trend} "
                    f"(consensus {decision.consensus_score})")

        # Phase 4: Risk check + simulated execution
        from risk.risk_engine import RiskEngine
        from execution.engine import ExecutionEngine

        risk_engine = RiskEngine(capital=10000)
        exec_engine = ExecutionEngine()

        for sig in signals:
            df_local = fetcher.get_crypto_kline_df(sig["symbol"], "1d", 100)
            if df_local.empty:
                continue

            risk_result = risk_engine.evaluate(
                sig["symbol"], sig["price"], sig, df_local,
                win_rate=0.6, profit_factor=2.0,
                volatility_pct=2.0
            )

            if risk_result.approved:
                pos = risk_result.position_sizing
                if pos["shares"] > 0:
                    order = exec_engine.execute_market(
                        sig["symbol"], "BUY",
                        sig["price"], pos["shares"]
                    )
                    risk_engine.record_trade(
                        sig["symbol"], pos["shares"], order.filled_price
                    )
                    logger.info(f"TRADE: {order.side} {order.filled_quantity} "
                                f"{sig['symbol']} @ {order.filled_price}")
            else:
                logger.info(f"RISK REJECT: {risk_result.reject_reason}")

        # Log positions
        positions = exec_engine.get_all_positions()
        if positions:
            logger.info(f"Open positions: {len(positions)}")
            for p in positions:
                logger.info(f"  {p['symbol']}: {p['shares']} @ {p['avg_price']}")

    # 4. Fetch news & macro
    try:  news_items = fetcher.get_cn_news(5)
    except Exception as e:  logger.error(f"News error: {e}")
    try:  macro = fetcher.get_macro_data()
    except Exception as e:  logger.error(f"Macro error: {e}")

    # 5. Generate and push report
    elapsed = int(time.time() - start_time)
    report = _build_report(signals, news_items, macro, regimes)
    send_feishu(report, "AI Hedge Fund OS Daily Report (Phase 2)")

    # 6. Store daily report to RAG
    rag.store_daily_report(datetime.now().strftime('%Y-%m-%d'), report, "crypto")

    logger.info(f"=== Phase 2 analysis complete ({elapsed}s) ===")


def _build_report(signals: list, news: list, macro: dict,
                   regimes: dict = None) -> str:
    """Build a text report from analysis results"""
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"Date: {date}", "=" * 40, ""]

    if regimes:
        lines.append("[Market Regime]")
        for sym, r in regimes.items():
            lines.append(f"  {sym}: {r['regime']} - {r['description']}")
            lines.append(f"  Volatility: {r['volatility_pct']}%  |  "
                         f"Volume: {r['volume_ratio']}x")
        lines.append("")

    for sig in signals:
        trend_icon = {"bullish": "BULL", "bearish": "BEAR", "neutral": "NEUTRAL"}
        icon = trend_icon.get(sig["trend"], "-")
        lines.append(f"[{sig['symbol']}] {icon} (strength {sig['strength']}/10)")
        lines.append(f"  Price: {sig['price']:.2f}  |  RSI: {sig['rsi']}")
        lines.append(f"  Support: {sig['support']:.2f}  |  Resistance: {sig['resistance']:.2f}")
        lines.append(f"  Volume: {sig['vol_ratio']}x avg")
        lines.append(f"  Reason: {sig['reason']}")
        lines.append("")

    if news:
        lines.append("[News Highlights]")
        for n in news[:3]:
            lines.append(f"  - {n.get('title','')[:60]}")
        lines.append("")

    if macro:
        lines.append("[Macro]")
        if macro.get('dxy'):
            lines.append(f"  DXY: {macro['dxy']}")
        if macro.get('cn_up_ratio'):
            lines.append(f"  A-share up ratio: {macro['cn_up_ratio']}")

    lines.append("")
    lines.append("=" * 40)
    lines.append("Powered by AI Hedge Fund OS | Phase 1")
    return "\n".join(lines)


if __name__ == "__main__":
    import schedule

    schedule.every().day.at("09:00").do(run_daily_analysis)
    schedule.every().day.at("21:00").do(run_daily_analysis)

    logger.info("Scheduler started. Waiting for scheduled tasks...")
    logger.info("  - 09:00 daily analysis")
    logger.info("  - 21:00 daily analysis")

    # Run once immediately for testing
    run_daily_analysis()

    while True:
        schedule.run_pending()
        time.sleep(60)
