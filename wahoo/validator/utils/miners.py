import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def get_active_uids(metagraph: Any) -> List[int]:
    """
    Get all registered miner UIDs from the metagraph.
    Filters out validators (UIDs with stake > 0) since validators should not
    receive weights - only miners should.
    
    In this subnet, miners are not required to run code or set axon info,
    so we return all registered UIDs with zero stake rather than filtering by axon IP/port.
    """
    active_uids: List[int] = []

    try:
        # Get all registered UIDs first
        all_uids: List[int] = []
        if hasattr(metagraph, "uids") and metagraph.uids is not None:
            all_uids = list(metagraph.uids)
        elif hasattr(metagraph, "hotkeys") and metagraph.hotkeys is not None:
            all_uids = list(range(len(metagraph.hotkeys)))
        else:
            logger.warning("Metagraph does not have 'uids' or 'hotkeys' attribute")
            return active_uids

        # Filter out validators (UIDs with stake > 0)
        # Only include miners (UIDs with stake = 0)
        if hasattr(metagraph, "S") and metagraph.S is not None:
            stakes = metagraph.S
            for uid in all_uids:
                try:
                    stake = stakes[uid].item() if hasattr(stakes[uid], 'item') else float(stakes[uid])
                    # Only include UIDs with zero stake (miners)
                    if stake == 0:
                        active_uids.append(uid)
                except (IndexError, AttributeError, TypeError):
                    # If we can't get stake, include the UID (fallback to old behavior)
                    active_uids.append(uid)
            
            validator_count = len(all_uids) - len(active_uids)
            logger.info(
                f"Found {len(all_uids)} total registered UIDs: "
                f"{len(active_uids)} miners (stake=0), {validator_count} validators (stake>0)"
            )
        else:
            # Fallback: if we can't check stake, return all UIDs
            logger.warning("Metagraph does not have 'S' (stake) attribute, returning all UIDs")
            active_uids = all_uids
            logger.info(f"Found {len(active_uids)} registered UIDs from metagraph.uids")

        return active_uids

    except Exception as e:
        logger.error(f"Error getting active UIDs from metagraph: {e}")
        return []


def is_valid_hotkey(hotkey: Optional[str]) -> bool:
    if hotkey is None:
        return False

    if not isinstance(hotkey, str):
        return False

    if len(hotkey.strip()) == 0:
        return False

    if len(hotkey) < 20 or len(hotkey) > 100:
        logger.debug(f"Hotkey length suspicious: {len(hotkey)} chars")

    return True


def build_uid_to_hotkey(
    metagraph: Any, active_uids: Optional[List[int]] = None
) -> Dict[int, str]:
    uid_to_hotkey: Dict[int, str] = {}

    try:
        if not hasattr(metagraph, "hotkeys"):
            logger.warning("Metagraph does not have 'hotkeys' attribute")
            return uid_to_hotkey

        if active_uids is None:
            active_uids = list(range(len(metagraph.hotkeys)))

        for uid in active_uids:
            try:
                if uid < 0 or uid >= len(metagraph.hotkeys):
                    logger.debug(f"UID {uid} out of bounds for metagraph.hotkeys")
                    continue

                hotkey = metagraph.hotkeys[uid]

                if not is_valid_hotkey(hotkey):
                    logger.warning(
                        f"UID {uid} has invalid/malformed hotkey: {hotkey}. "
                        "Will be excluded from mapping."
                    )
                    continue

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
