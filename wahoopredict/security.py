"""
🟩 WAHOOPREDICT × WAHOOPREDICT — Odds, not oaths. Grift responsibly.

HMAC signing helper for miners (v1).
"""

import hmac
import hashlib
from typing import Optional

from wahoopredict.config import settings


def verify_hmac_v1(manifest_hash: str, sig: str, secret: Optional[str] = None) -> bool:
    """
    Verify HMAC-SHA256 signature (v1).
    
    Args:
        manifest_hash: The manifest hash to verify
        sig: The signature to verify against
        secret: Secret key (defaults to API_SECRET)
        
    Returns:
        True if signature is valid, False otherwise
    """
    secret = secret or settings.api_secret
    
    # Compute expected signature
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        manifest_hash.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(expected_sig, sig)


def sign_hmac_v1(manifest_hash: str, secret: Optional[str] = None) -> str:
    """
    Generate HMAC-SHA256 signature (v1).
    
    Args:
        manifest_hash: The manifest hash to sign
        secret: Secret key (defaults to API_SECRET)
        
    Returns:
        Hex-encoded HMAC signature
    """
    secret = secret or settings.api_secret
    
    return hmac.new(
        secret.encode("utf-8"),
        manifest_hash.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

