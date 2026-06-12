"""Web Push helpers — VAPID-signed push to user-supplied subscription endpoints."""
import os
import json
import logging
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)


def vapid_public_hex() -> str:
    return os.environ.get("VAPID_PUBLIC_HEX", "")


def send_push(subscription: dict, payload: dict) -> bool:
    private_pem = os.environ.get("VAPID_PRIVATE_PEM", "").replace("\\n", "\n")
    if not private_pem:
        return False
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=private_pem,
            vapid_claims={"sub": os.environ.get("VAPID_CONTACT", "mailto:safety@expiremate.com")},
            ttl=86400,
        )
        return True
    except WebPushException as e:
        logger.warning(f"[push] failed: {e}")
        return False
    except Exception as e:
        logger.error(f"[push] error: {e}")
        return False
