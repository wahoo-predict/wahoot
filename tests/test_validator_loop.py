"""
Comprehensive tests for the validator main loop.

These tests verify:
- Loop iterations and timing
- Error handling and recovery
- Integration with all components
- Edge cases (no miners, API failures, etc.)
"""

import time
from unittest.mock import Mock, patch
import pytest
import torch

import bittensor as bt

from wahoo.validator.validator import (
    main_loop_iteration,
)
from wahoo.validator.mock_data import generate_mock_validation_data
from wahoo.protocol.protocol import WAHOOPredict


class TestValidatorLoop:
    """Test the main validator loop iteration."""

    @pytest.fixture
    def mock_wallet(self):
        """Create a mock wallet."""
        wallet = Mock(spec=bt.Wallet)
        wallet.name = "test_wallet"
        wallet.hotkey = Mock()
        return wallet

    @pytest.fixture
    def mock_subtensor(self):
        """Create a mock subtensor."""
        subtensor = Mock(spec=bt.Subtensor)
        subtensor.network = "local"
        return subtensor

    @pytest.fixture
    def mock_dendrite(self):
        """Create a mock dendrite."""
        dendrite = Mock(spec=bt.Dendrite)
        return dendrite

    @pytest.fixture
    def mock_metagraph(self):
        """Create a mock metagraph with active miners."""
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
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",  # Inactive
            "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        ]
        return metagraph

    @pytest.fixture
    def config(self):
        """Create test configuration."""
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

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_event_id")
    @patch("wahoo.validator.validator.reward")
    @patch("wahoo.validator.validator.set_weights_with_retry")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_main_loop_iteration_success(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_set_weights,
        mock_reward,
        mock_get_event_id,
        mock_get_validation_data,
        mock_wallet,
        mock_subtensor,
        mock_dendrite,
        mock_metagraph,
        config,
    ):
        """Test successful main loop iteration."""
        # Setup mocks
        active_uids = [0, 1, 3, 4]
        mock_get_active_uids.return_value = active_uids

        uid_to_hotkey = {
            0: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            1: "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            3: "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
            4: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        }
        mock_build_uid_to_hotkey.return_value = uid_to_hotkey

        # Mock validation data
        hotkeys = list(uid_to_hotkey.values())
        mock_validation_data = generate_mock_validation_data(hotkeys)
        mock_get_validation_data.return_value = mock_validation_data

        # Mock event ID
        mock_get_event_id.return_value = "test_event_123"

        # Mock dendrite query responses
        mock_responses = [
            WAHOOPredict(event_id="test_event_123", prob_yes=0.7, prob_no=0.3, confidence=0.8),
            WAHOOPredict(event_id="test_event_123", prob_yes=0.6, prob_no=0.4, confidence=0.7),
            None,  # Timeout/failure
            WAHOOPredict(event_id="test_event_123", prob_yes=0.5, prob_no=0.5, confidence=0.6),
        ]
        mock_dendrite.query.return_value = mock_responses

        # Mock reward calculation
        mock_rewards = torch.tensor([0.3, 0.3, 0.0, 0.4])
        mock_reward.return_value = mock_rewards

        # Mock set_weights
        mock_set_weights.return_value = ("tx_hash_123", True)

        # Run iteration
        start_time = time.time()
        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )
        elapsed = time.time() - start_time

        # Verify calls
        mock_get_active_uids.assert_called_once_with(mock_metagraph)
        mock_build_uid_to_hotkey.assert_called_once_with(mock_metagraph, active_uids=active_uids)
        mock_get_validation_data.assert_called_once()
        mock_get_event_id.assert_called_once()
        mock_dendrite.query.assert_called_once()
        mock_reward.assert_called_once()
        mock_set_weights.assert_called_once()

        # Verify timing (should complete quickly in test, but check it doesn't hang)
        assert elapsed < 5.0, "Loop iteration took too long"

    @patch("wahoo.validator.validator.get_active_uids")
    def test_main_loop_no_active_uids(
        self,
        mock_get_active_uids,
        mock_wallet,
        mock_subtensor,
        mock_dendrite,
        mock_metagraph,
        config,
    ):
        """Test loop iteration when no active UIDs are found."""
        mock_get_active_uids.return_value = []

        # Should return early without errors
        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )

        mock_get_active_uids.assert_called_once()

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_main_loop_api_failure(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_validation_data,
        mock_wallet,
        mock_subtensor,
        mock_dendrite,
        mock_metagraph,
        config,
    ):
        """Test loop iteration when API fails."""
        active_uids = [0, 1]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1", 1: "hotkey2"}

        # API failure
        mock_get_validation_data.side_effect = Exception("API Error")

        # Should handle gracefully and continue
        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )

        # Should have attempted to fetch data
        mock_get_validation_data.assert_called_once()

    @patch("wahoo.validator.validator.reward")
    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_main_loop_zero_rewards(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_validation_data,
        mock_reward,
        mock_wallet,
        mock_subtensor,
        mock_dendrite,
        mock_metagraph,
        config,
    ):
        """Test loop iteration when all rewards are zero."""
        active_uids = [0, 1]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1", 1: "hotkey2"}
        mock_get_validation_data.return_value = []

        # Zero rewards
        mock_reward.return_value = torch.tensor([0.0, 0.0])

        # Should skip set_weights
        with patch("wahoo.validator.validator.set_weights_with_retry") as mock_set_weights:
            main_loop_iteration(
                wallet=mock_wallet,
                subtensor=mock_subtensor,
                dendrite=mock_dendrite,
                metagraph=mock_metagraph,
                netuid=1,
                config=config,
                validator_db=None,
            )

            # Should not call set_weights when rewards are zero
            mock_set_weights.assert_not_called()


class TestValidatorTiming:
    """Test timing constraints of the validator loop."""

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_loop_iteration_timing_budget(
        self,
        mock_build_uid_to_hotkey,
        mock_get_active_uids,
        mock_get_validation_data,
    ):
        """Test that loop iteration completes within timing budget (~100s worst case)."""
        # Setup minimal mocks
        mock_get_active_uids.return_value = []
        mock_build_uid_to_hotkey.return_value = {}
        mock_get_validation_data.return_value = []

        # Create minimal components
        mock_wallet = Mock()
        mock_subtensor = Mock()
        mock_dendrite = Mock()
        mock_metagraph = Mock()
        config = {"loop_interval": 100.0}

        # Time the iteration
        start = time.time()
        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )
        elapsed = time.time() - start

        # Should complete quickly when no active UIDs
        assert elapsed < 1.0, f"Loop iteration took {elapsed}s, expected < 1.0s"


class TestValidatorErrorHandling:
    """Test error handling in the validator loop."""

    def test_loop_handles_exceptions_gracefully(self):
        """Test that exceptions in loop iteration are caught and logged."""
        mock_wallet = Mock()
        mock_subtensor = Mock()
        mock_dendrite = Mock()
        mock_metagraph = Mock()
        config = {}

        # Make metagraph.sync raise an exception
        mock_metagraph.sync.side_effect = Exception("Sync failed")

        # Should not raise, but handle gracefully
        with patch("wahoo.validator.validator.logger") as mock_logger:
            main_loop_iteration(
                wallet=mock_wallet,
                subtensor=mock_subtensor,
                dendrite=mock_dendrite,
                metagraph=mock_metagraph,
                netuid=1,
                config=config,
                validator_db=None,
            )

            # Should have logged the error
            mock_logger.error.assert_called()


class TestValidatorIntegration:
    """Integration tests for the full validator pipeline."""

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_event_id")
    @patch("wahoo.validator.validator.reward")
    @patch("wahoo.validator.validator.set_weights_with_retry")
    def test_full_pipeline_with_mock_data(
        self,
        mock_set_weights,
        mock_reward,
        mock_get_event_id,
        mock_get_validation_data,
    ):
        """Test the full pipeline with mock data."""
        # Setup
        active_uids = [0, 1, 2]
        hotkeys = [
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
        ]

        # Mock validation data
        mock_validation_data = generate_mock_validation_data(hotkeys)
        mock_get_validation_data.return_value = mock_validation_data

        # Mock event ID
        mock_get_event_id.return_value = "test_event"

        # Mock rewards
        mock_rewards = torch.tensor([0.4, 0.3, 0.3])
        mock_reward.return_value = mock_rewards

        # Mock set_weights
        mock_set_weights.return_value = ("tx_hash", True)

        # Create mocks
        mock_wallet = Mock()
        mock_subtensor = Mock()
        mock_dendrite = Mock()
        mock_metagraph = Mock()
        mock_metagraph.uids = torch.tensor(active_uids)  # Must be torch tensor for len()
        mock_metagraph.axons = [Mock() for _ in active_uids]

        mock_responses = [
            WAHOOPredict(event_id="test_event", prob_yes=0.7, prob_no=0.3, confidence=0.8)
            for _ in active_uids
        ]
        mock_dendrite.query.return_value = mock_responses

        config = {
            "wahoo_validation_endpoint": "https://api.wahoopredict.com/api/v2/event/bittensor/statistics",
            "wahoo_api_url": "https://api.wahoopredict.com",
        }

        with patch("wahoo.validator.validator.get_active_uids", return_value=active_uids):
            with patch("wahoo.validator.validator.build_uid_to_hotkey", return_value=dict(zip(active_uids, hotkeys))):
                main_loop_iteration(
                    wallet=mock_wallet,
                    subtensor=mock_subtensor,
                    dendrite=mock_dendrite,
                    metagraph=mock_metagraph,
                    netuid=1,
                    config=config,
                    validator_db=None,
                )

        # Verify all components were called
        mock_get_validation_data.assert_called_once()
        mock_get_event_id.assert_called_once()
        mock_dendrite.query.assert_called_once()
        mock_reward.assert_called_once()
        mock_set_weights.assert_called_once()
