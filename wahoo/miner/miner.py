import logging
import os
import time
from typing import Optional

import bittensor as bt
from dotenv import load_dotenv

from wahoo.protocol.protocol import WAHOOPredict

load_dotenv()

logger = logging.getLogger(__name__)


def generate_prediction(event_id: str) -> tuple[float, float, float]:
    import random

    prob_yes = random.uniform(0.3, 0.7)
    prob_no = 1.0 - prob_yes
    confidence = random.uniform(0.5, 0.9)

    logger.debug(
        f"Generated prediction for {event_id}: yes={prob_yes:.2f}, no={prob_no:.2f}, conf={confidence:.2f}"
    )

    return prob_yes, prob_no, confidence


class Miner:
    def __init__(
        self,
        wallet_name: str = "default",
        hotkey_name: str = "default",
        netuid: int = 1,
        network: str = "local",
        chain_endpoint: Optional[str] = None,
    ):
        self.wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        # Use chain_endpoint for local net, otherwise use network
        # Pass endpoint URL as network parameter
        if chain_endpoint:
            self.subtensor = bt.subtensor(network=chain_endpoint)
        elif network == "local":
            # Default local endpoint
            self.subtensor = bt.subtensor(network="ws://127.0.0.1:9945")
        else:
            self.subtensor = bt.subtensor(network=network)
        # Metagraph uses the same network/endpoint
        if chain_endpoint:
            self.metagraph = bt.metagraph(netuid=netuid, network=chain_endpoint)
        elif network == "local":
            self.metagraph = bt.metagraph(netuid=netuid, network="ws://127.0.0.1:9945")
        else:
            self.metagraph = bt.metagraph(netuid=netuid, network=network)
        self.netuid = netuid
        self.network = network

        self.axon = bt.axon(
            wallet=self.wallet,
            port=8091,
        )

        logger.info(f"Initialized miner: {wallet_name}/{hotkey_name}")
        logger.info(f"Network: {network}, Subnet: {netuid}")

    def process_query(self, synapse: WAHOOPredict) -> WAHOOPredict:
        event_id = synapse.event_id

        if not event_id:
            logger.warning("Received query with empty event_id")
            synapse.prob_yes = 0.5
            synapse.prob_no = 0.5
            synapse.confidence = 0.0
            synapse.protocol_version = "1.0"
            return synapse

        prob_yes, prob_no, confidence = generate_prediction(event_id)

        synapse.prob_yes = prob_yes
        synapse.prob_no = prob_no
        synapse.confidence = confidence
        synapse.protocol_version = "1.0"

        logger.info(
            f"Responded to query for {event_id}: "
            f"yes={prob_yes:.2f}, no={prob_no:.2f}, conf={confidence:.2f}"
        )

        return synapse

    def run(self):
        logger.info("=" * 70)
        logger.info("WaHoo Predict Miner")
        logger.info("=" * 70)

        self.axon.attach(
            forward_fn=self.process_query,
            blacklist_fn=None,
            priority_fn=None,
        )

        logger.info("Starting axon server...")
        self.axon.start()
        
        # Serve axon on blockchain so validators can find it
        logger.info("Serving axon on blockchain...")
        try:
            self.subtensor.serve_axon(
                netuid=self.netuid,
                axon=self.axon,
            )
            logger.info("✓ Axon served on blockchain")
        except Exception as e:
            logger.error(f"Failed to serve axon on blockchain: {e}")
            logger.warning("Miner will continue but validators may not be able to find it")

        logger.info("Miner running. Waiting for queries...")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                self.metagraph.sync(subtensor=self.subtensor)
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.axon.stop()
            logger.info("Miner stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    wallet_name = os.getenv("WALLET_NAME", "default")
    hotkey_name = os.getenv("HOTKEY_NAME", "default")
    netuid = int(os.getenv("NETUID", "1"))
    network = os.getenv("NETWORK", "finney")
    chain_endpoint = os.getenv("CHAIN_ENDPOINT", None)

    miner = Miner(
        wallet_name=wallet_name,
        hotkey_name=hotkey_name,
        netuid=netuid,
        network=network,
        chain_endpoint=chain_endpoint,
    )

    miner.run()


if __name__ == "__main__":
    main()
