import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

import bittensor as bt
from dotenv import load_dotenv

from .api import (
    get_active_event_id,
    get_wahoo_validation_data,
    should_skip_weight_computation,
)
from .blockchain import set_weights_with_retry
from .scoring.rewards import reward
from .utils.miners import build_uid_to_hotkey, get_active_uids

load_dotenv()

logger = logging.getLogger(__name__)


WAHOO_API_URL = "https://api.wahoopredict.com"
WAHOO_VALIDATION_ENDPOINT = (
    "https://api.wahoopredict.com/api/v2/event/bittensor/statistics"
)

BLOCK_TIME_SECONDS = 12.0


def calculate_epoch_timestamps(
    subtensor: bt.Subtensor,
    metagraph: bt.Metagraph,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Calculate start_date and end_date timestamps for the current Bittensor epoch.
        
    Returns:
        Tuple of (start_date, end_date) as ISO8601 strings, or (None, None) if unable to calculate
    """
    try:
        # Get current block number
        current_block = None
        if hasattr(subtensor, "block"):
            current_block = subtensor.block
        elif hasattr(subtensor, "get_current_block"):
            current_block = subtensor.get_current_block()
        
        if current_block is None:
            logger.warning("Could not get current block number, skipping epoch timestamp calculation")
            return None, None
        
        # Get blocks per epoch
        blocks_per_epoch = None
        if hasattr(metagraph, "blocks_per_epoch") and metagraph.blocks_per_epoch is not None:
            blocks_per_epoch = int(metagraph.blocks_per_epoch)
        elif hasattr(metagraph, "tempo") and metagraph.tempo is not None:
            blocks_per_epoch = int(metagraph.tempo)
        
        if blocks_per_epoch is None or blocks_per_epoch <= 0:
            logger.warning("Could not get blocks_per_epoch from metagraph, skipping epoch timestamp calculation")
            return None, None
        
        # Calculate current epoch number
        current_epoch = current_block // blocks_per_epoch
        
        # Calculate epoch start and end blocks
        epoch_start_block = current_epoch * blocks_per_epoch
        epoch_end_block = (current_epoch + 1) * blocks_per_epoch - 1
        
        # Get current time as reference
        current_time = datetime.now(timezone.utc)
        
        # Calculate timestamps based on block differences
        # Estimate: blocks ago * block_time = seconds ago
        blocks_from_start = current_block - epoch_start_block
        blocks_to_end = epoch_end_block - current_block
        
        epoch_start_time = current_time - timedelta(seconds=blocks_from_start * BLOCK_TIME_SECONDS)
        epoch_end_time = current_time + timedelta(seconds=blocks_to_end * BLOCK_TIME_SECONDS)
        
        # Format as ISO8601 strings (API expects this format)
        start_date = epoch_start_time.isoformat().replace("+00:00", "Z")
        end_date = epoch_end_time.isoformat().replace("+00:00", "Z")
        
        logger.debug(
            f"Epoch {current_epoch}: blocks {epoch_start_block}-{epoch_end_block}, "
            f"timestamps {start_date} to {end_date}"
        )
        
        return start_date, end_date
        
    except Exception as e:
        logger.warning(f"Failed to calculate epoch timestamps: {e}")
        return None, None


def load_validator_config() -> Dict[str, Any]:
    wallet_name = os.getenv("WALLET_NAME")
    hotkey_name = os.getenv("HOTKEY_NAME")

    if not wallet_name or not hotkey_name:
        raise ValueError(
            "WALLET_NAME and HOTKEY_NAME must be set via environment variables or CLI arguments. "
            "Example: export WALLET_NAME=my_wallet HOTKEY_NAME=my_hotkey"
        )

    return {
        "netuid": int(os.getenv("NETUID", "0")),
        "network": os.getenv("NETWORK", "finney"),
        "wallet_name": wallet_name,
        "hotkey_name": hotkey_name,
        "use_validator_db": os.getenv("USE_VALIDATOR_DB", "false").lower() == "true",
        "wahoo_api_url": WAHOO_API_URL,
        "wahoo_validation_endpoint": WAHOO_VALIDATION_ENDPOINT,
    }


def initialize_bittensor(
    wallet_name: str,
    hotkey_name: str,
    netuid: int,
    network: str = "finney",
    chain_endpoint: Optional[str] = None,
) -> tuple[bt.Wallet, bt.Subtensor, bt.Dendrite, bt.Metagraph]:
    logger.info("Initializing Bittensor components...")
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        logger.info(f"Loaded wallet: {wallet_name}/{hotkey_name}")
    except Exception as e:
        logger.error(f"Failed to load wallet: {e}")
        raise

    try:
        if chain_endpoint:
            subtensor = bt.subtensor(network=chain_endpoint)
            logger.info(f"Connected to subtensor at {chain_endpoint}")
        else:
            subtensor = bt.subtensor(network=network)
            logger.info(f"Connected to subtensor on {network}")
    except Exception as e:
        logger.error(f"Failed to connect to subtensor: {e}")
        raise

    try:
        dendrite = bt.dendrite(wallet=wallet)
        logger.info("Dendrite initialized")
    except Exception as e:
        logger.error(f"Failed to initialize dendrite: {e}")
        raise

    try:
        if chain_endpoint:
            metagraph = bt.metagraph(netuid=netuid, network=chain_endpoint)
        else:
            metagraph = bt.metagraph(netuid=netuid, network=network)
        # Sync metagraph to get latest network state
        metagraph.sync(subtensor=subtensor)
        logger.info(f"Metagraph synced: {len(metagraph.uids)} UIDs on subnet {netuid}")
    except Exception as e:
        logger.error(f"Failed to load metagraph: {e}")
        raise

    return wallet, subtensor, dendrite, metagraph


def sync_metagraph(metagraph: bt.Metagraph, subtensor: bt.Subtensor) -> bt.Metagraph:
    logger.debug("Syncing metagraph...")
    metagraph.sync(subtensor=subtensor)
    logger.debug(f"Metagraph synced: {len(metagraph.uids)} total UIDs")
    return metagraph


def calculate_loop_interval(metagraph: bt.Metagraph) -> float:
    try:
        if hasattr(metagraph, "tempo") and metagraph.tempo is not None:
            tempo = int(metagraph.tempo)
            interval = tempo * BLOCK_TIME_SECONDS * 1.1
            logger.info(
                f"Calculated loop interval from tempo: {tempo} blocks = {interval:.1f}s"
            )
            return max(interval, 60.0)
        elif (
            hasattr(metagraph, "blocks_per_epoch")
            and metagraph.blocks_per_epoch is not None
        ):
            blocks_per_epoch = int(metagraph.blocks_per_epoch)
            interval = blocks_per_epoch * BLOCK_TIME_SECONDS * 1.1
            logger.info(
                f"Calculated loop interval from blocks_per_epoch: "
                f"{blocks_per_epoch} blocks = {interval:.1f}s"
            )
            return max(interval, 60.0)
    except (AttributeError, TypeError, ValueError) as e:
        logger.debug(f"Could not get tempo from metagraph: {e}")

    logger.info(
        "Using default loop interval: 100.0s (tempo not available from metagraph)"
    )
    return 100.0


def compute_weights(
    validation_data: List[Any],
    active_uids: List[int],
    uid_to_hotkey: Dict[int, str],
    previous_scores: Optional[Dict[str, float]] = None,
) -> tuple[Dict[str, float], Dict[str, float]]:
    from .scoring.dataframe import records_to_dataframe
    from .scoring.operators import EMAVolumeScorer

    logger.debug("Computing weights using EMAVolumeScorer...")
    df = records_to_dataframe(validation_data)

    if df.empty:
        logger.warning("No validation data to compute weights from")
        return {}, {}

    scorer = EMAVolumeScorer()
    result = scorer.run(df, previous_scores=previous_scores)
    weights: Dict[str, float] = {}

    hotkeys = df["hotkey"].to_numpy()
    for i, hotkey in enumerate(hotkeys):
        weight = float(result.weights[i])
        if weight > 0:
            weights[hotkey] = weight

    updated_scores: Dict[str, float] = result.meta.get("smoothed_scores", {})

    logger.info(
        f"EMA Scoring: {result.meta['total_miners']} miners, "
        f"{result.meta['new_miners']} new, "
        f"{result.meta['active_miners']} active (weight > 0), "
        f"max_weight={result.meta['max_weight']:.6f}"
    )
    logger.debug(f"Scoring metadata: {result.meta}")

    return weights, updated_scores


def main_loop_iteration(
    wallet: bt.Wallet,
    subtensor: bt.Subtensor,
    dendrite: bt.Dendrite,
    metagraph: bt.Metagraph,
    netuid: int,
    config: Dict[str, Any],
    validator_db: Optional[Any] = None,
    iteration_count: int = 0,
) -> None:
    iteration_start = time.time()
    logger.info("=" * 70)
    logger.info("Starting main loop iteration")
    logger.info("=" * 70)

    if validator_db is not None and hasattr(validator_db, "cleanup_old_cache"):
        try:
            cleanup_result = validator_db.cleanup_old_cache()
            if (
                cleanup_result.get("snapshots_deleted", 0) > 0
                or cleanup_result.get("scoring_runs_deleted", 0) > 0
            ):
                logger.info(
                    f"Database cleanup: Deleted {cleanup_result.get('snapshots_deleted', 0)} "
                    f"old snapshots and {cleanup_result.get('scoring_runs_deleted', 0)} "
                    f"old scoring runs"
                )
        except Exception as cleanup_error:
            logger.warning(f"Database cleanup failed: {cleanup_error}")

    try:
        logger.info("[1/8] Syncing metagraph...")
        metagraph = sync_metagraph(metagraph, subtensor)
        logger.info(f"✓ Metagraph synced: {len(metagraph.uids)} total UIDs")

        logger.info("[2/8] Getting active UIDs...")
        active_uids = get_active_uids(metagraph)
        if not active_uids:
            logger.warning("No active UIDs found, skipping iteration")
            return
        logger.info(f"✓ Found {len(active_uids)} active UIDs")

        logger.info("[3/8] Extracting hotkeys...")
        uid_to_hotkey = build_uid_to_hotkey(metagraph, active_uids=active_uids)
        hotkeys = [uid_to_hotkey[uid] for uid in active_uids if uid in uid_to_hotkey]
        logger.info(f"✓ Extracted {len(hotkeys)} hotkeys")

        logger.info("[4/8] Fetching WAHOO validation data...")
        try:
            # Calculate epoch timestamps for the current Bittensor epoch
            start_date, end_date = calculate_epoch_timestamps(subtensor, metagraph)
            
            if not start_date or not end_date:
                logger.warning(
                    "Could not calculate epoch timestamps. Skipping weight setting for this epoch "
                    "to avoid using full history. Will retry next iteration."
                )
                return
            
            logger.info(
                f"Using epoch date range: {start_date} to {end_date}"
            )
            
            validation_data = get_wahoo_validation_data(
                hotkeys=hotkeys,
                start_date=start_date,
                end_date=end_date,
                api_base_url=config.get("wahoo_validation_endpoint"),
                validator_db=validator_db,
            )
            logger.info(f"✓ Fetched validation data for {len(validation_data)} miners")

            # Remove unregistered miners from database after API call
            if validator_db is not None:
                try:
                    removed_count = validator_db.remove_unregistered_miners(
                        registered_hotkeys=hotkeys
                    )
                    if removed_count > 0:
                        logger.info(
                            f"✓ Removed {removed_count} unregistered miners from database"
                        )
                except Exception as e:
                    logger.warning(f"Failed to remove unregistered miners: {e}")

            if should_skip_weight_computation(validation_data, log_reason=True):
                logger.warning(
                    "No usable validation data available after API + cache fallback. "
                    "Attempting to use last known good scores from database..."
                )

                from .scoring.fallback import get_fallback_weights_from_db

                wahoo_weights = get_fallback_weights_from_db(validator_db)
                if wahoo_weights is not None:
                    validation_data = []
                else:
                    logger.warning("No fallback weights available, skipping iteration")
                    return
            else:
                wahoo_weights = None

        except Exception as e:
            logger.error(f"Failed to fetch validation data: {e}")
            validation_data = []
            if should_skip_weight_computation(validation_data, log_reason=True):
                logger.warning(
                    "No usable validation data after exception. "
                    "Skipping weight computation and set_weights() call "
                    "for this iteration."
                )
                return

        logger.info("[5/8] Getting active event ID...")
        try:
            event_id = get_active_event_id(api_base_url=config.get("wahoo_api_url"))
            logger.info(f"✓ Active event ID: {event_id}")
        except Exception as e:
            logger.warning(f"Failed to get event ID, using default: {e}")
            event_id = "wahoo_test_event"

        logger.info("[6/8] Computing weights...")

        if wahoo_weights is not None:
            logger.info("Using fallback weights from DB, skipping new computation")
            updated_ema_scores = {}
        else:
            previous_ema_scores = {}
            if validator_db is not None:
                try:
                    from .scoring.validation import validate_ema_scores

                    raw_scores = validator_db.get_latest_scores()
                    if raw_scores:
                        previous_ema_scores = validate_ema_scores(raw_scores)
                        logger.info(
                            f"Loaded {len(previous_ema_scores)} valid EMA scores from database"
                        )
                except Exception as e:
                    logger.warning(f"Failed to load EMA scores from DB: {e}")
                    previous_ema_scores = {}

            if not previous_ema_scores:
                previous_ema_scores = config.get("ema_scores", {})

            wahoo_weights, updated_ema_scores = compute_weights(
                validation_data=validation_data,
                active_uids=active_uids,
                uid_to_hotkey=uid_to_hotkey,
                previous_scores=previous_ema_scores,
            )

            if validator_db is not None and updated_ema_scores:
                try:
                    validator_db.add_scoring_run(
                        updated_ema_scores, reason="ema_update"
                    )
                    logger.debug(
                        f"Saved {len(updated_ema_scores)} EMA scores to database"
                    )
                except Exception as e:
                    logger.warning(f"Failed to save EMA scores to DB: {e}")

        logger.info(f"✓ Computed weights for {len(wahoo_weights)} miners")

        logger.info("[7/8] Calculating rewards...")
        try:
            # Miner responses are not used in this subnet (miners don't run code)
            miner_responses = [None] * len(active_uids)
            rewards = reward(
                responses=miner_responses,
                uids=active_uids,
                metagraph=metagraph,
                wahoo_weights=wahoo_weights,
                wahoo_validation_data=validation_data,
                uid_to_hotkey=uid_to_hotkey,
            )
            logger.info(f"✓ Calculated rewards tensor: shape={rewards.shape}")

            rewards_sum = rewards.sum().item()
            if rewards_sum > 0.0:
                logger.info(f"✓ Rewards sum: {rewards_sum:.6f} (ready to set weights)")
            else:
                logger.warning("All rewards are zero, skipping set_weights() call")
                return
        except Exception as e:
            logger.error(f"Failed to calculate rewards: {e}")
            return

        logger.info("[8/8] Setting weights on blockchain...")
        try:
            transaction_hash, success = set_weights_with_retry(
                subtensor=subtensor,
                wallet=wallet,
                netuid=netuid,
                uids=active_uids,
                weights=rewards,
            )
            if success and transaction_hash:
                logger.info("=" * 70)
                logger.info("✓✓✓ WEIGHTS SET SUCCESSFULLY ON BLOCKCHAIN ✓✓✓")
                logger.info("=" * 70)
                logger.info(f"Transaction Hash: {transaction_hash}")
                logger.info(f"Number of Miners: {len(active_uids)}")
                logger.info("Weight Distribution:")
                for uid, weight in zip(active_uids, rewards):
                    logger.info(f"  UID {uid}: {weight:.6f} ({weight*100:.2f}%)")
                logger.info(f"Total Weight Sum: {rewards.sum().item():.6f}")
                logger.info("=" * 70)
            elif success and not transaction_hash:
                pass
            else:
                logger.warning("Failed to set weights (will retry next iteration)")
        except Exception as e:
            logger.error(f"Failed to set weights: {e}")

        iteration_time = time.time() - iteration_start
        logger.info(f"✓ Iteration complete in {iteration_time:.2f}s")

    except Exception as e:
        logger.error(f"Error in main loop iteration: {e}", exc_info=True)
