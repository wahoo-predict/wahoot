"""
WAHOOPREDICT - Protocol definitions for the Bittensor subnet.

Defines the communication protocol between validators and miners.
"""

import bittensor as bt


class WAHOOPredict(bt.Synapse):
    """
    Protocol for WAHOOPREDICT subnet.

    Validators query miners for predictions on binary events.
    Miners respond with probability predictions (prob_yes ∈ [0,1]).
    """

    # Event to predict
    event_id: str = ""

    # Miner's probability prediction (0.0 to 1.0)
    prob_yes: float = 0.0

    # Manifest hash for verification
    manifest_hash: str = ""

    # HMAC signature
    sig: str = ""
