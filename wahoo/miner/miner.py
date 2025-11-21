import logging
import os
import time

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
    ):
        self.wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
        self.subtensor = bt.subtensor(network=network)
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

    miner = Miner(
        wallet_name=wallet_name,
        hotkey_name=hotkey_name,
        netuid=netuid,
        network=network,
    )

    miner.run()


if __name__ == "__main__":
    main()
