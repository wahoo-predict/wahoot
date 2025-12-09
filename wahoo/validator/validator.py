import logging
import os
import time
from typing import Dict, List, Optional, Any

import bittensor as bt
from dotenv import load_dotenv

from .api import get_active_event_id, get_wahoo_validation_data, should_skip_weight_computation
from .blockchain import set_weights_with_retry
from .scoring.rewards import reward
from .utils.miners import build_uid_to_hotkey, get_active_uids
from wahoo.protocol.protocol import WAHOOPredict

load_dotenv()

logger = logging.getLogger(__name__)


WAHOO_API_URL = "https://api.wahoopredict.com"
WAHOO_VALIDATION_ENDPOINT = (
    "https://api.wahoopredict.com/api/v2/event/bittensor/statistics"
)

BLOCK_TIME_SECONDS = 12.0


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


def query_miners(
    dendrite: bt.Dendrite,
    metagraph: bt.Metagraph,
    active_uids: List[int],
    event_id: str,
    timeout: float = 12.0,
) -> List[WAHOOPredict]:
    """
    Query miners via dendrite. 
    Note: In this subnet, miners may not run code, so this is a placeholder.
    Returns empty responses if miners don't have valid axons.
    """
    if not active_uids:
        logger.debug("No active UIDs to query")
        return []

    logger.debug(
        f"Querying {len(active_uids)} miners for event_id={event_id} "
        f"with timeout={timeout}s"
    )

    # Filter to only UIDs with valid axons (if any)
    valid_axons = []
    valid_uids = []
    for uid in active_uids:
        try:
            if uid < len(metagraph.axons):
                axon = metagraph.axons[uid]
                # Check if axon has valid IP/port (optional check)
                if hasattr(axon, "ip") and hasattr(axon, "port"):
                    ip = str(axon.ip) if axon.ip else "0.0.0.0"
                    port = int(axon.port) if axon.port else 0
                    if ip != "0.0.0.0" and port > 0:
                        valid_axons.append(axon)
                        valid_uids.append(uid)
        except (IndexError, AttributeError, TypeError) as e:
            logger.debug(f"UID {uid} has no valid axon: {e}")
            continue

    if not valid_axons:
        logger.debug("No miners with valid axons to query (this is expected if miners don't run code)")
        return [None] * len(active_uids)

    synapses = [WAHOOPredict(event_id=event_id) for _ in valid_axons]

    try:
        responses = dendrite.query(
            axons=valid_axons,
            synapses=synapses,
            timeout=timeout,
        )
        logger.debug(f"Received {len(responses)} responses from {len(valid_axons)} miners with axons")
        # Pad with None for UIDs without axons
        full_responses = [None] * len(active_uids)
        for i, uid in enumerate(valid_uids):
            if uid in active_uids:
                idx = active_uids.index(uid)
                full_responses[idx] = responses[i] if i < len(responses) else None
        return full_responses
    except Exception as e:
        logger.debug(f"Error querying miners (expected if miners don't run code): {e}")
        return [None] * len(active_uids)


def compute_weights(
    validation_data: List[Any],
    active_uids: List[int],
    uid_to_hotkey: Dict[int, str],
    previous_scores: Optional[Dict[str, float]] = None,
) -> tuple[Dict[str, float], Dict[str, float]]:
    from .dataframe import records_to_dataframe
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

    # Automatic database cleanup (runs every iteration for active maintenance)
    # Keeps 3 days of performance snapshots (EMA only needs latest, but buffer for debugging)
    # Keeps 7 days of scoring runs (for historical analysis)
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
        logger.info("[1/9] Syncing metagraph...")
        metagraph = sync_metagraph(metagraph, subtensor)
        logger.info(f"✓ Metagraph synced: {len(metagraph.uids)} total UIDs")

        logger.info("[2/9] Getting active UIDs...")
        active_uids = get_active_uids(metagraph)
        if not active_uids:
            logger.warning("No active UIDs found, skipping iteration")
            return
        logger.info(f"✓ Found {len(active_uids)} active UIDs")

        logger.info("[3/9] Extracting hotkeys...")
        uid_to_hotkey = build_uid_to_hotkey(metagraph, active_uids=active_uids)
        hotkeys = [uid_to_hotkey[uid] for uid in active_uids if uid in uid_to_hotkey]
        logger.info(f"✓ Extracted {len(hotkeys)} hotkeys")

        logger.info("[4/9] Fetching WAHOO validation data...")
        try:
            validation_data = get_wahoo_validation_data(
                hotkeys=hotkeys,
                api_base_url=config.get("wahoo_validation_endpoint"),
                validator_db=validator_db,
            )
            logger.info(f"✓ Fetched validation data for {len(validation_data)} miners")

            # Check if we should skip weight computation due to no usable data
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
            # Check if we should skip after exception
            if should_skip_weight_computation(validation_data, log_reason=True):
                logger.warning(
                    "No usable validation data after exception. "
                    "Skipping weight computation and set_weights() call "
                    "for this iteration."
                )
                return

        logger.info("[5/9] Getting active event ID...")
        try:
            event_id = get_active_event_id(api_base_url=config.get("wahoo_api_url"))
            logger.info(f"✓ Active event ID: {event_id}")
        except Exception as e:
            logger.warning(f"Failed to get event ID, using default: {e}")
            event_id = "wahoo_test_event"

        logger.info("[6/9] Querying miners...")
        miner_responses = query_miners(
            dendrite=dendrite,
            metagraph=metagraph,
            active_uids=active_uids,
            event_id=event_id,
            timeout=12.0,
        )
        logger.info(f"✓ Queried {len(miner_responses)} miners (placeholder)")

        logger.info("[7/9] Computing weights...")

        if wahoo_weights is not None:
            logger.info("Using fallback weights from DB, skipping new computation")
            updated_ema_scores = {}  # No new scores to save
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

        logger.info("[8/9] Calculating rewards...")
        try:
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

        logger.info("[9/9] Setting weights on blockchain...")
        try:
            transaction_hash, success = set_weights_with_retry(
                subtensor=subtensor,
                wallet=wallet,
                netuid=netuid,
                uids=active_uids,
                weights=rewards,
            )
            if success and transaction_hash:
                # Enhanced logging for successful weight setting
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
                # Cooldown period - not an error, just waiting
                # Logging is handled in blockchain.py at DEBUG level
                pass
            else:
                logger.warning("Failed to set weights (will retry next iteration)")
        except Exception as e:
            logger.error(f"Failed to set weights: {e}")

        iteration_time = time.time() - iteration_start
        logger.info(f"✓ Iteration complete in {iteration_time:.2f}s")

    except Exception as e:
        logger.error(f"Error in main loop iteration: {e}", exc_info=True)


# Main entry point moved to wahoo.entrypoints.validator
# This module contains validator logic and orchestration functions
