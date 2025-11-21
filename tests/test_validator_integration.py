from unittest.mock import Mock, patch
import pytest
import torch

import bittensor as bt

from wahoo.validator.validator import (
    main_loop_iteration,
)
from wahoo.validator.models import ValidationRecord, PerformanceMetrics
from wahoo.protocol.protocol import WAHOOPredict


def generate_mock_validation_data(hotkeys):

    import random

    records = []
    for hotkey in hotkeys:
        performance = PerformanceMetrics(
            total_volume_usd=random.uniform(100.0, 20000.0),
            realized_profit_usd=random.uniform(-2000.0, 2000.0),
            unrealized_profit_usd=random.uniform(-100.0, 800.0),
            trade_count=random.randint(10, 800),
            open_positions_count=random.randint(0, 50),
            win_rate=random.uniform(0.3, 0.8) if random.random() > 0.3 else None,
        )
        record = ValidationRecord(
            hotkey=hotkey,
            signature=f"sig_{random.randint(1000, 9999)}",
            message=f"msg_{random.randint(1000, 9999)}",
            performance=performance,
        )
        records.append(record)
    return records


class TestValidatorIntegration:

    @pytest.fixture
    def mock_components(self):

        wallet = Mock(spec=bt.Wallet)
        subtensor = Mock(spec=bt.Subtensor)
        dendrite = Mock(spec=bt.Dendrite)
        metagraph = Mock(spec=bt.Metagraph)

        metagraph.uids = torch.tensor([0, 1, 2])
        metagraph.axons = [
            Mock(ip="127.0.0.1", port=8091),
            Mock(ip="127.0.0.1", port=8092),
            Mock(ip="127.0.0.1", port=8093),
        ]
        metagraph.hotkeys = [
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
        ]

        return wallet, subtensor, dendrite, metagraph

    @pytest.fixture
    def config(self):
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

    @patch("wahoo.validator.validator.set_weights_with_retry")
    @patch("wahoo.validator.validator.reward")
    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_event_id")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_full_pipeline_success(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_event_id,
        mock_get_validation_data,
        mock_reward,
        mock_set_weights,
        mock_components,
        config,
    ):

        wallet, subtensor, dendrite, metagraph = mock_components

        active_uids = [0, 1, 2]
        mock_get_active_uids.return_value = active_uids

        hotkeys = [
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
        ]
        uid_to_hotkey = dict(zip(active_uids, hotkeys))
        mock_build_uid_to_hotkey.return_value = uid_to_hotkey

        mock_validation_data = generate_mock_validation_data(hotkeys)
        mock_get_validation_data.return_value = mock_validation_data

        mock_get_event_id.return_value = "test_event_123"

        mock_responses = [
            WAHOOPredict(
                event_id="test_event_123", prob_yes=0.7, prob_no=0.3, confidence=0.8
            ),
            WAHOOPredict(
                event_id="test_event_123", prob_yes=0.6, prob_no=0.4, confidence=0.7
            ),
            WAHOOPredict(
                event_id="test_event_123", prob_yes=0.5, prob_no=0.5, confidence=0.6
            ),
        ]
        dendrite.query.return_value = mock_responses

        mock_rewards = torch.tensor([0.4, 0.3, 0.3])
        mock_reward.return_value = mock_rewards

        mock_set_weights.return_value = ("tx_hash_123", True)

        main_loop_iteration(
            wallet=wallet,
            subtensor=subtensor,
            dendrite=dendrite,
            metagraph=metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )

        mock_get_active_uids.assert_called_once()
        mock_build_uid_to_hotkey.assert_called_once()
        mock_get_validation_data.assert_called_once()
        mock_get_event_id.assert_called_once()
        dendrite.query.assert_called_once()
        mock_reward.assert_called_once()
        mock_set_weights.assert_called_once()

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_pipeline_with_empty_validation_data(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_validation_data,
        mock_components,
        config,
    ):

        wallet, subtensor, dendrite, metagraph = mock_components

        active_uids = [0, 1]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1", 1: "hotkey2"}
        mock_get_validation_data.return_value = []

        main_loop_iteration(
            wallet=wallet,
            subtensor=subtensor,
            dendrite=dendrite,
            metagraph=metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )

        mock_get_validation_data.assert_called_once()

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_pipeline_with_partial_validation_data(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_validation_data,
        mock_components,
        config,
    ):

        wallet, subtensor, dendrite, metagraph = mock_components

        active_uids = [0, 1, 2]
        hotkeys = ["hotkey1", "hotkey2", "hotkey3"]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = dict(zip(active_uids, hotkeys))

        mock_validation_data = generate_mock_validation_data(hotkeys[:2])
        mock_get_validation_data.return_value = mock_validation_data

        main_loop_iteration(
            wallet=wallet,
            subtensor=subtensor,
            dendrite=dendrite,
            metagraph=metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )

        mock_get_validation_data.assert_called_once()


class TestValidatorEdgeCases:

    @patch("wahoo.validator.validator.get_active_uids")
    def test_no_active_miners(
        self,
        mock_get_active_uids,
        mock_wallet,
        mock_subtensor,
        mock_dendrite,
        mock_metagraph,
        test_config,
    ):
        mock_get_active_uids.return_value = []

        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=1,
            config=test_config,
            validator_db=None,
        )

        mock_get_active_uids.assert_called_once()

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_api_timeout(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_validation_data,
        mock_wallet,
        mock_subtensor,
        mock_dendrite,
        mock_metagraph,
        test_config,
    ):

        active_uids = [0, 1]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1", 1: "hotkey2"}

        from wahoo.validator.api.client import ValidationAPIError

        mock_get_validation_data.side_effect = ValidationAPIError("Request timed out")

        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=1,
            config=test_config,
            validator_db=None,
        )

    @patch("wahoo.validator.validator.set_weights_with_retry")
    @patch("wahoo.validator.validator.reward")
    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_set_weights_failure(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_validation_data,
        mock_reward,
        mock_set_weights,
        mock_wallet,
        mock_subtensor,
        mock_dendrite,
        mock_metagraph,
        test_config,
    ):

        active_uids = [0]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1"}
        mock_get_validation_data.return_value = []
        mock_reward.return_value = torch.tensor([1.0])

        mock_set_weights.return_value = (None, False)

        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=1,
            config=test_config,
            validator_db=None,
        )

        mock_set_weights.assert_called_once()
