"""
Miner utility functions for UID-to-hotkey mapping and active miner filtering.

This module provides utilities for:
- Filtering active miners from metagraph
- Building UID-to-hotkey mappings
- Validating hotkey formats
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def get_active_uids(metagraph: Any) -> List[int]:
    """
    Get list of active UIDs from metagraph.

    Filters miners based on valid axon configuration:
    - axon.ip != "0.0.0.0" (not default/invalid IP)
    - axon.port > 0 (valid port number)

    Args:
        metagraph: Bittensor metagraph object

    Returns:
        List[int]: List of active UID integers
    """
    active_uids: List[int] = []

    try:
        if not hasattr(metagraph, "axons"):
            logger.warning("Metagraph does not have 'axons' attribute")
            return active_uids

        for uid in range(len(metagraph.axons)):
            try:
                axon = metagraph.axons[uid]

                # Check if axon has valid IP and port
                if hasattr(axon, "ip") and hasattr(axon, "port"):
                    ip = str(axon.ip)
                    port = int(axon.port) if axon.port else 0

                    # Filter: IP must not be default, port must be > 0
                    if ip != "0.0.0.0" and port > 0:
                        active_uids.append(uid)
                else:
                    logger.debug(f"UID {uid} axon missing ip or port attributes")

            except (IndexError, AttributeError, ValueError, TypeError) as e:
                logger.debug(f"Error checking UID {uid} axon: {e}")
                continue

        logger.info(f"Found {len(active_uids)} active UIDs out of {len(metagraph.axons)} total")
        return active_uids

    except Exception as e:
        logger.error(f"Error getting active UIDs from metagraph: {e}")
        return []


def is_valid_hotkey(hotkey: Optional[str]) -> bool:
    """
    Validate hotkey format.

    Checks if hotkey is:
    - Not None or empty
    - A non-empty string
    - Has reasonable length (ss58 addresses are typically 48 characters)

    Args:
        hotkey: Hotkey string to validate

    Returns:
        bool: True if hotkey appears valid, False otherwise
    """
    if hotkey is None:
        return False

    if not isinstance(hotkey, str):
        return False

    if len(hotkey.strip()) == 0:
        return False

    # SS58 addresses are typically 48 characters, but allow some flexibility
    # Minimum reasonable length (e.g., 20 chars), max reasonable (e.g., 100 chars)
    if len(hotkey) < 20 or len(hotkey) > 100:
        logger.debug(f"Hotkey length suspicious: {len(hotkey)} chars")
        # Don't reject based on length alone, but log it

    return True


def build_uid_to_hotkey(
    metagraph: Any, active_uids: Optional[List[int]] = None
) -> Dict[int, str]:
    """
    Build UID-to-hotkey mapping for active miners.

    Creates a dictionary mapping UID (int) to hotkey (str) for all active UIDs.
    Only includes UIDs that:
    1. Are in the active_uids list (if provided), or all UIDs if not provided
    2. Have a valid hotkey in metagraph.hotkeys[uid]
    3. Pass hotkey validation checks

    Args:
        metagraph: Bittensor metagraph object
        active_uids: Optional list of UIDs to include. If None, uses all UIDs
                    from metagraph. Typically should use get_active_uids() result.

    Returns:
        Dict[int, str]: Mapping of UID to hotkey string
                       Only includes UIDs with valid hotkeys
    """
    uid_to_hotkey: Dict[int, str] = {}

    try:
        if not hasattr(metagraph, "hotkeys"):
            logger.warning("Metagraph does not have 'hotkeys' attribute")
            return uid_to_hotkey

        # If active_uids not provided, use all UIDs in metagraph
        if active_uids is None:
            active_uids = list(range(len(metagraph.hotkeys)))

        for uid in active_uids:
            try:
                # Check bounds
                if uid < 0 or uid >= len(metagraph.hotkeys):
                    logger.debug(f"UID {uid} out of bounds for metagraph.hotkeys")
                    continue

                # Get hotkey from metagraph
                hotkey = metagraph.hotkeys[uid]

                # Validate hotkey
                if not is_valid_hotkey(hotkey):
                    logger.warning(
                        f"UID {uid} has invalid/malformed hotkey: {hotkey}. "
                        "Will be excluded from mapping."
                    )
                    continue

                # Add to mapping
                uid_to_hotkey[uid] = str(hotkey).strip()

            except (IndexError, AttributeError, TypeError) as e:
                logger.warning(f"Error processing UID {uid} for hotkey mapping: {e}")
                continue

        logger.info(
            f"Built UID-to-hotkey mapping: {len(uid_to_hotkey)} valid mappings "
            f"out of {len(active_uids)} active UIDs"
        )
        return uid_to_hotkey

    except Exception as e:
        logger.error(f"Error building UID-to-hotkey mapping: {e}")
        return {}


__all__ = [
    "get_active_uids",
    "is_valid_hotkey",
    "build_uid_to_hotkey",
]
