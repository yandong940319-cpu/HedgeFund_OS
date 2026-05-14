#!/usr/bin/env python3
"""Feishu push notification module"""

import os, json, logging, requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
logger = logging.getLogger(__name__)


def send_feishu(text: str, title: str = "AI Hedge Fund OS") -> bool:
    """Send text message to Feishu"""
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        logger.warning("FEISHU_WEBHOOK not configured")
        return False
    try:
        resp = requests.post(webhook, json={
            "msg_type": "text",
            "content": {"text": f"{title}\n\n{text}"}
        }, timeout=10)
        ok = resp.status_code == 200 and resp.json().get("StatusCode") == 0
        if ok:
            logger.info("Feishu push success")
        else:
            logger.warning(f"Feishu push failed: {resp.text[:200]}")
        return ok
    except Exception as e:
        logger.error(f"Feishu push error: {e}")
        return False


def send_feishu_card(title: str, content_lines: list) -> bool:
    """Send interactive card message to Feishu"""
    webhook = os.getenv("FEISHU_WEBHOOK")
    if not webhook:
        return False

    elements = [{"tag": "markdown", "content": line} for line in content_lines]

    try:
        resp = requests.post(webhook, json={
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "blue"
                },
                "elements": elements
            }
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Feishu card push error: {e}")
        return False
