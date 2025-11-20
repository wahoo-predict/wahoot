"""
End-to-end integration tests for the validator.

These tests simulate the full validator pipeline with mock data
to ensure all components work together correctly.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import torch

import bittensor as bt

from wahoo.validator.validator import (
    main_loop_iteration,
    initialize_bittensor,
    load_validator_config,
)
from wahoo.validator.mock_data import (
    generate_mock_validation_data,
    create_mock_miner_responses,
)
from wahoo.validator.models import ValidationRecord
from wahoo.protocol.protocol import WAHOOPredict


class TestValidatorIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def mock_components(self):
        """Create mock Bittensor components."""
        wallet = Mock(spec=bt.Wallet)
        subtensor = Mock(spec=bt.Subtensor)
        dendrite = Mock(spec=bt.Dendrite)
        metagraph = Mock(spec=bt.Metagraph)
        
        # Setup metagraph
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
        """Test configuration."""
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
        """Test successful full pipeline execution."""
        wallet, subtensor, dendrite, metagraph = mock_components
        
        # Setup mocks
        active_uids = [0, 1, 2]
        mock_get_active_uids.return_value = active_uids
        
        hotkeys = [
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
            "5GNJqTPyNqANBkUVMN1LPPrxXnFouWXoe2wNSmmEoLctxiZY",
        ]
        uid_to_hotkey = dict(zip(active_uids, hotkeys))
        mock_build_uid_to_hotkey.return_value = uid_to_hotkey
        
        # Mock validation data
        mock_validation_data = generate_mock_validation_data(hotkeys)
        mock_get_validation_data.return_value = mock_validation_data
        
        # Mock event ID
        mock_get_event_id.return_value = "test_event_123"
        
        # Mock dendrite responses
        mock_responses = [
            WAHOOPredict(event_id="test_event_123", prob_yes=0.7, prob_no=0.3, confidence=0.8),
            WAHOOPredict(event_id="test_event_123", prob_yes=0.6, prob_no=0.4, confidence=0.7),
            WAHOOPredict(event_id="test_event_123", prob_yes=0.5, prob_no=0.5, confidence=0.6),
        ]
        dendrite.query.return_value = mock_responses
        
        # Mock rewards
        mock_rewards = torch.tensor([0.4, 0.3, 0.3])
        mock_reward.return_value = mock_rewards
        
        # Mock set_weights
        mock_set_weights.return_value = ("tx_hash_123", True)
        
        # Run iteration
        main_loop_iteration(
            wallet=wallet,
            subtensor=subtensor,
            dendrite=dendrite,
            metagraph=metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )
        
        # Verify all steps executed
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
        """Test pipeline when validation data is empty."""
        wallet, subtensor, dendrite, metagraph = mock_components
        
        active_uids = [0, 1]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1", 1: "hotkey2"}
        mock_get_validation_data.return_value = []  # Empty data
        
        # Should handle gracefully
        main_loop_iteration(
            wallet=wallet,
            subtensor=subtensor,
            dendrite=dendrite,
            metagraph=metagraph,
            netuid=1,
            config=config,
            validator_db=None,
        )
        
        # Should have attempted to fetch data
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
        """Test pipeline when only some miners have validation data."""
        wallet, subtensor, dendrite, metagraph = mock_components
        
        active_uids = [0, 1, 2]
        hotkeys = ["hotkey1", "hotkey2", "hotkey3"]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = dict(zip(active_uids, hotkeys))
        
        # Only first two miners have data
        mock_validation_data = generate_mock_validation_data(hotkeys[:2])
        mock_get_validation_data.return_value = mock_validation_data
        
        # Should handle partial data
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
    """Test edge cases and error scenarios."""

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
        """Test when no active miners are found."""
        mock_get_active_uids.return_value = []
        
        # Should return early without errors
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
        """Test handling of API timeout."""
        
        active_uids = [0, 1]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1", 1: "hotkey2"}
        
        # Simulate timeout
        from wahoo.validator.api.client import ValidationAPIError
        mock_get_validation_data.side_effect = ValidationAPIError("Request timed out")
        
        # Should handle gracefully
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
        """Test handling of set_weights failure."""
        
        active_uids = [0]
        mock_get_active_uids.return_value = active_uids
        mock_build_uid_to_hotkey.return_value = {0: "hotkey1"}
        mock_get_validation_data.return_value = []
        mock_reward.return_value = torch.tensor([1.0])
        
        # set_weights fails
        mock_set_weights.return_value = (None, False)
        
        # Should handle gracefully
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

