import logging
import os
import time
from typing import Dict, List, Optional, Any

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
from wahoo.protocol.protocol import WAHOOPredict

load_dotenv()

logger = logging.getLogger(__name__)


def load_validator_config() -> Dict[str, Any]:
    return {
        "netuid": int(os.getenv("NETUID", "0")),
        "network": os.getenv("NETWORK", "finney"),
        "wallet_name": os.getenv("WALLET_NAME", "default"),
        "hotkey_name": os.getenv("HOTKEY_NAME", "default"),
        "loop_interval": float(os.getenv("LOOP_INTERVAL", "100.0")),
        "use_validator_db": os.getenv("USE_VALIDATOR_DB", "false").lower() == "true",
        "wahoo_api_url": os.getenv("WAHOO_API_URL", "https://api.wahoopredict.com"),
        "wahoo_validation_endpoint": os.getenv(
            "WAHOO_VALIDATION_ENDPOINT",
            "https://api.wahoopredict.com/api/v2/event/bittensor/statistics",
        ),
    }


def initialize_bittensor(
    wallet_name: str,
    hotkey_name: str,
    netuid: int,
    network: str = "finney",
) -> tuple[bt.Wallet, bt.Subtensor, bt.Dendrite, bt.Metagraph]:
    logger.info("Initializing Bittensor components...")
    try:
        wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        logger.info(f"Loaded wallet: {wallet_name}/{hotkey_name}")
    except Exception as e:
        logger.error(f"Failed to load wallet: {e}")
        raise

    try:
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
        metagraph = bt.metagraph(netuid=netuid, network=network)
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


def query_miners(
    dendrite: bt.Dendrite,
    metagraph: bt.Metagraph,
    active_uids: List[int],
    event_id: str,
    timeout: float = 12.0,
) -> List[WAHOOPredict]:
    if not active_uids:
        logger.warning("No active UIDs to query")
        return []

    logger.debug(
        f"Querying {len(active_uids)} miners for event_id={event_id} "
        f"with timeout={timeout}s"
    )

    axons = [metagraph.axons[uid] for uid in active_uids]

    synapses = [WAHOOPredict(event_id=event_id) for _ in active_uids]

    try:
        responses = dendrite.query(
            axons=axons,
            synapses=synapses,
            timeout=timeout,
        )
        logger.info(f"Received {len(responses)} responses from miners")
        return responses
    except Exception as e:
        logger.error(f"Error querying miners: {e}")
        return [None] * len(active_uids)


def compute_weights(
    validation_data: List[Any],
    active_uids: List[int],
    uid_to_hotkey: Dict[int, str],
    previous_scores: Optional[Dict[str, float]] = None,
) -> tuple[Dict[str, float], Dict[str, float]]:
    """
    Compute weights using EMAVolumeScorer operator.
    
    Args:
        validation_data: List of ValidationRecord objects
        active_uids: List of active UIDs
        uid_to_hotkey: Mapping from UID to hotkey
        previous_scores: Previous EMA scores for continuity (hotkey -> score)
    
    Returns:
        Tuple of (weights_dict, updated_scores_dict) where:
        - weights_dict: hotkey -> normalized weight (for rewards calculation)
        - updated_scores_dict: hotkey -> new EMA score (for DB persistence)
    """
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

    # Run cache cleanup periodically (every 10 iterations, ~16 minutes at 100s interval)
    if validator_db is not None and hasattr(validator_db, "cleanup_old_cache"):
        if iteration_count > 0 and iteration_count % 10 == 0:
            try:
                deleted_count = validator_db.cleanup_old_cache(max_age_days=7)
                if deleted_count > 0:
                    logger.info(
                        f"Cache cleanup: Deleted {deleted_count} old cache entries "
                        f"(older than 7 days)"
                    )
            except Exception as cleanup_error:
                logger.warning(f"Cache cleanup failed: {cleanup_error}")

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
                        logger.info(f"Loaded {len(previous_ema_scores)} valid EMA scores from database")
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
                    validator_db.add_scoring_run(updated_ema_scores, reason="ema_update")
                    logger.debug(f"Saved {len(updated_ema_scores)} EMA scores to database")
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
            if success:
                logger.info(
                    f"✓ Weights set successfully. Transaction: {transaction_hash}"
                )
            else:
                logger.warning("Failed to set weights (will retry next iteration)")
        except Exception as e:
            logger.error(f"Failed to set weights: {e}")

        iteration_time = time.time() - iteration_start
        logger.info(f"✓ Iteration complete in {iteration_time:.2f}s")

    except Exception as e:
        logger.error(f"Error in main loop iteration: {e}", exc_info=True)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="WaHoo Predict Bittensor Validator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--netuid",
        type=int,
        default=int(os.getenv("NETUID", "1")),
        help="Subnet UID",
    )
    parser.add_argument(
        "--network",
        type=str,
        default=os.getenv("NETWORK", "finney"),
        choices=["test", "finney"],
        help="Bittensor network",
    )

    parser.add_argument(
        "--wallet.name",
        type=str,
        default=os.getenv("WALLET_NAME", "default"),
        dest="wallet_name",
        help="Wallet name (coldkey)",
    )
    parser.add_argument(
        "--wallet.hotkey",
        type=str,
        default=os.getenv("HOTKEY_NAME", "default"),
        dest="hotkey_name",
        help="Hotkey name",
    )

    parser.add_argument(
        "--loop-interval",
        type=float,
        default=float(os.getenv("LOOP_INTERVAL", "100.0")),
        dest="loop_interval",
        help="Main loop interval in seconds",
    )
    parser.add_argument(
        "--use-validator-db",
        action="store_true",
        default=os.getenv("USE_VALIDATOR_DB", "false").lower() == "true",
        dest="use_validator_db",
        help="Enable ValidatorDB caching",
    )
    parser.add_argument(
        "--validator-db-path",
        type=str,
        default=os.getenv("VALIDATOR_DB_PATH", "validator.db"),
        dest="validator_db_path",
        help="Path to validator database",
    )

    parser.add_argument(
        "--wahoo-api-url",
        type=str,
        default=os.getenv("WAHOO_API_URL", "https://api.wahoopredict.com"),
        dest="wahoo_api_url",
        help="WAHOO API base URL",
    )
    parser.add_argument(
        "--wahoo-validation-endpoint",
        type=str,
        default=os.getenv(
            "WAHOO_VALIDATION_ENDPOINT",
            "https://api.wahoopredict.com/api/v2/event/bittensor/statistics",
        ),
        dest="wahoo_validation_endpoint",
        help="WAHOO validation endpoint URL",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        dest="log_level",
        help="Logging level",
    )

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper())
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 70)
    logger.info("WaHoo Predict Validator")
    logger.info("=" * 70)

    from .database.validator_db import check_database_exists, get_db_path

    db_path = get_db_path()
    if not check_database_exists(db_path):
        logger.info("First run detected - initializing database...")
        try:
            from .init import initialize

            initialize(skip_deps=True, skip_db=False, db_path=str(db_path))
            logger.info("✓ Database initialized successfully")
        except Exception as e:
            logger.warning(f"Auto-initialization failed: {e}")
            logger.info("You can manually run: wahoo-validator-init")
            logger.info("Continuing anyway...")

    config = {
        "netuid": args.netuid,
        "network": args.network,
        "wallet_name": args.wallet_name,
        "hotkey_name": args.hotkey_name,
        "loop_interval": args.loop_interval,
        "use_validator_db": args.use_validator_db,
        "wahoo_api_url": args.wahoo_api_url,
        "wahoo_validation_endpoint": args.wahoo_validation_endpoint,
    }

    logger.info("Configuration:")
    logger.info(f"  Network: {config['network']}")
    logger.info(f"  Subnet UID: {config['netuid']}")
    logger.info(f"  Wallet: {config['wallet_name']}/{config['hotkey_name']}")
    logger.info(f"  Loop interval: {config['loop_interval']}s")
    logger.info(f"  ValidatorDB: {config['use_validator_db']}")

    try:
        wallet, subtensor, dendrite, metagraph = initialize_bittensor(
            wallet_name=config["wallet_name"],
            hotkey_name=config["hotkey_name"],
            netuid=config["netuid"],
            network=config["network"],
        )
    except Exception as e:
        logger.error(f"Failed to initialize Bittensor: {e}")
        return

    validator_db = None
    if config["use_validator_db"]:
        try:
            from .database.core import ValidatorDB
            validator_db = ValidatorDB(db_path=get_db_path())
            logger.info(f"ValidatorDB initialized at {get_db_path()}")
        except Exception as e:
            logger.error(f"Failed to initialize ValidatorDB: {e}")
            logger.warning("Continuing without database support")

    logger.info("Entering main loop...")
    logger.info(f"Loop interval: {config['loop_interval']}s")
    logger.info("Press Ctrl+C to stop")

    iteration_count = 0
    try:
        while True:
            main_loop_iteration(
                wallet=wallet,
                subtensor=subtensor,
                dendrite=dendrite,
                metagraph=metagraph,
                netuid=config["netuid"],
                config=config,
                validator_db=validator_db,
                iteration_count=iteration_count,
            )
            iteration_count += 1

            sleep_time = config["loop_interval"]
            logger.info(f"Sleeping for {sleep_time}s before next iteration...")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
    finally:
        logger.info("Validator stopped")


if __name__ == "__main__":
    main()
