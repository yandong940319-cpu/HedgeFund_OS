#!/usr/bin/env python3
"""Feishu push notification module — supports signature"""

import os, json, logging, time, hmac, hashlib, base64
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "config", ".env"))
logger = logging.getLogger(__name__)


def _sign(secret: str, timestamp: int) -> str:
    h = hmac.new(
        f"{timestamp}\n{secret}".encode("utf-8"),
        digestmod=hashlib.sha256
    )
    return base64.b64encode(h.digest()).decode("utf-8")


def _build_payload(msg_type: str, content: dict,
                   secret: str = "", timestamp: int = 0) -> dict:
    if not timestamp:
        timestamp = int(time.time())
    payload = {"msg_type": msg_type, "content": content}
    if secret:
        payload["timestamp"] = str(timestamp)
        payload["sign"] = _sign(secret, timestamp)
    return payload


def send_feishu(text: str, title: str = "AI Hedge Fund OS") -> bool:
    webhook = os.getenv("FEISHU_WEBHOOK")
    secret = os.getenv("FEISHU_SIGN_SECRET", "")
    if not webhook:
        logger.warning("FEISHU_WEBHOOK not configured")
        return False
    try:
        ts = int(time.time())
        payload = _build_payload("text", {"text": f"{title}\n\n{text}"}, secret, ts)
        resp = requests.post(webhook, json=payload, timeout=10)
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
    webhook = os.getenv("FEISHU_WEBHOOK")
    secret = os.getenv("FEISHU_SIGN_SECRET", "")
    if not webhook:
        return False

    elements = [{"tag": "markdown", "content": line} for line in content_lines]
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue"
        },
        "elements": elements,
    }

    try:
        ts = int(time.time())
        payload = _build_payload("interactive", card, secret, ts)
        resp = requests.post(webhook, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"Feishu card push error: {e}")
        return False
