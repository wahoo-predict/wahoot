from typing import Optional
import bittensor as bt


class WAHOOPredict(bt.Synapse):
    event_id: str = ""
    prob_yes: Optional[float] = None
    prob_no: Optional[float] = None
    confidence: Optional[float] = None
    protocol_version: Optional[str] = None

    def deserialize(self) -> "WAHOOPredict":
        return self
