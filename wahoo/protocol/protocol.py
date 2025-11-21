"""
Protocol definition for WaHoo Predict Bittensor subnet.

This module defines the synapse protocol used for communication between
validators and miners in the WaHoo Predict subnet.
"""

from typing import Optional
import bittensor as bt


class WAHOOPredict(bt.Synapse):
    """
    Synapse for WaHoo Predict protocol.

    Miners respond with their prediction probabilities for a given event.

    Fields:
        event_id: The event ID to make a prediction for
        prob_yes: Probability that the event will occur (0.0 to 1.0)
        prob_no: Probability that the event will not occur (0.0 to 1.0)
        confidence: Confidence level in the prediction (0.0 to 1.0)
        protocol_version: Version of the protocol being used
    """

    event_id: str = ""
    prob_yes: Optional[float] = None
    prob_no: Optional[float] = None
    confidence: Optional[float] = None
    protocol_version: Optional[str] = None

    def deserialize(self) -> "WAHOOPredict":
        """Deserialize the synapse."""
        return self
