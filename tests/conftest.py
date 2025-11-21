import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock
import torch
import bittensor as bt


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def mock_metagraph():
    metagraph = Mock(spec=bt.Metagraph)
    metagraph.uids = torch.tensor([0, 1, 2, 3, 4])
    metagraph.axons = [
        Mock(ip="127.0.0.1", port=8091),
        Mock(ip="127.0.0.1", port=8092),
        Mock(ip="0.0.0.0", port=0),  # Inactive
        Mock(ip="127.0.0.1", port=8093),
        Mock(ip="127.0.0.1", port=8094),
    ]
    metagraph.hotkeys = [
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
    ]
    return metagraph


@pytest.fixture
def mock_wallet():

    wallet = Mock(spec=bt.Wallet)
    wallet.name = "test_wallet"
    wallet.hotkey = Mock()
    return wallet


@pytest.fixture
def mock_subtensor():

    subtensor = Mock(spec=bt.Subtensor)
    subtensor.network = "local"
    return subtensor


@pytest.fixture
def mock_dendrite():

    return Mock(spec=bt.Dendrite)


@pytest.fixture
def test_config():

    return {
        "netuid": 1,
        "network": "local",
        "wallet_name": "test",
        "hotkey_name": "test",
        "loop_interval": 10.0,
        "use_validator_db": False,
        "wahoo_api_url": "https://api.wahoopredict.com",
        "wahoo_validation_endpoint": "https://api.wahoopredict.com/api/v2/event/bittensor/statistics",
    }
