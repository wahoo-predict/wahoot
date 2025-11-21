import logging
import os
import time
from typing import Dict, List, Optional, Any

import bittensor as bt
from dotenv import load_dotenv

from .api import get_active_event_id, get_wahoo_validation_data
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
) -> Dict[str, float]:
    logger.debug("Computing weights from validation data...")

    weights: Dict[str, float] = {}
    validation_by_hotkey: Dict[str, Any] = {}
    for record in validation_data:
        if hasattr(record, "hotkey"):
            validation_by_hotkey[record.hotkey] = record

    for uid in active_uids:
        hotkey = uid_to_hotkey.get(uid)
        if not hotkey:
            continue

        record = validation_by_hotkey.get(hotkey)
        if record and hasattr(record, "performance"):
            perf = record.performance
            if (
                perf.realized_profit_usd
                and perf.realized_profit_usd > 0
                and perf.total_volume_usd
            ):
                weight = perf.realized_profit_usd * perf.total_volume_usd
                weights[hotkey] = weight

    logger.debug(f"Computed weights for {len(weights)} miners")
    return weights


def main_loop_iteration(
    wallet: bt.Wallet,
    subtensor: bt.Subtensor,
    dendrite: bt.Dendrite,
    metagraph: bt.Metagraph,
    netuid: int,
    config: Dict[str, Any],
    validator_db: Optional[Any] = None,
) -> None:
    iteration_start = time.time()
    logger.info("=" * 70)
    logger.info("Starting main loop iteration")
    logger.info("=" * 70)

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
        except Exception as e:
            logger.error(f"Failed to fetch validation data: {e}")
            validation_data = []

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
        wahoo_weights = compute_weights(
            validation_data=validation_data,
            active_uids=active_uids,
            uid_to_hotkey=uid_to_hotkey,
        )
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

    logger.info("Entering main loop...")
    logger.info(f"Loop interval: {config['loop_interval']}s")
    logger.info("Press Ctrl+C to stop")

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
            )

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
