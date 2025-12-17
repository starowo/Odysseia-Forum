"""JWT utility functions for authentication"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


def base64url_encode(data: bytes) -> str:
    """Base64 URL-safe encode"""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    """Base64 URL-safe decode"""
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


async def sign_jwt(payload: Dict[str, Any], secret: str, expires_in_sec: int) -> str:
    """
    Sign a JWT token with HS256 algorithm

    Args:
        payload: The payload to encode
        secret: The secret key for signing
        expires_in_sec: Token expiration time in seconds

    Returns:
        The signed JWT token
    """
    header = {"alg": "HS256", "typ": "JWT"}
    exp = int(time.time()) + expires_in_sec
    full_payload = {**payload, "exp": exp}

    # Encode header and payload
    header_b64 = base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(full_payload).encode("utf-8"))

    # Create signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{message}.{signature_b64}"


async def verify_jwt(token: str, secret: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token

    Args:
        token: The JWT token to verify
        secret: The secret key for verification

    Returns:
        The decoded payload if valid, None otherwise
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts

        # Verify signature
        message = f"{header_b64}.{payload_b64}"
        expected_signature = hmac.new(
            secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).digest()

        actual_signature = base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        # Decode payload
        payload_json = base64url_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)

        # Check expiration
        if payload.get("exp", 0) < time.time():
            return None

        return payload

    except Exception:
        return None
