#!/usr/bin/env python3
"""
Comprehensive Local Net Integration Tests for WaHooNet

Tests all critical paths for release readiness:
1. Validator-Miner connection
2. Main loop (9 steps)
3. Database operations
4. Scoring & weights
5. Error handling
6. End-to-end

Run with: pytest tests/test_local_net_integration.py -v
Or: python -m pytest tests/test_local_net_integration.py -v
"""

import os
import sys
import time
import pytest
import torch
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # noqa: E402

import bittensor as bt  # noqa: E402
from wahoo.validator.validator import main_loop_iteration  # noqa: E402
from wahoo.validator.models import ValidationRecord, PerformanceMetrics  # noqa: E402
from wahoo.protocol.protocol import WAHOOPredict  # noqa: E402


# Test configuration
TEST_NETUID = 1
TEST_NETWORK = "local"
MOCK_API_PORT = 8000
MOCK_API_URL = f"http://127.0.0.1:{MOCK_API_PORT}"


class TestLocalNetIntegration:
    """Comprehensive integration tests for local net"""

    @pytest.fixture(scope="class")
    def mock_api_server(self):
        """Start mock API server in background"""
        from tests.mock_wahoo_api import run_mock_server
        import threading

        server_thread = threading.Thread(
            target=run_mock_server, args=(MOCK_API_PORT,), daemon=True
        )
        server_thread.start()
        time.sleep(1)  # Give server time to start
        yield
        # Server will stop when thread dies

    @pytest.fixture
    def mock_wallet(self):
        """Create mock wallet"""
        wallet = Mock(spec=bt.Wallet)
        wallet.name = "test-validator"
        wallet.hotkey = Mock()
        wallet.hotkey.ss58_address = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        return wallet

    @pytest.fixture
    def mock_subtensor(self):
        """Create mock subtensor"""
        subtensor = Mock(spec=bt.Subtensor)
        subtensor.network = TEST_NETWORK
        return subtensor

    @pytest.fixture
    def mock_dendrite(self):
        """Create mock dendrite"""
        dendrite = Mock(spec=bt.Dendrite)
        return dendrite

    @pytest.fixture
    def mock_metagraph(self):
        """Create mock metagraph with 5 UIDs"""
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
    def test_config(self):
        """Test configuration"""
        return {
            "netuid": TEST_NETUID,
            "network": TEST_NETWORK,
            "wallet_name": "test-validator",
            "hotkey_name": "default",
            "loop_interval": 10.0,
            "use_validator_db": True,
            "wahoo_api_url": MOCK_API_URL,
            "wahoo_validation_endpoint": f"{MOCK_API_URL}/api/v2/event/bittensor/statistics",
        }

    # ========== Test 1: Validator-Miner Connection ==========

    def test_1_validator_detects_miner_in_metagraph(
        self, mock_metagraph, mock_subtensor
    ):
        """Test 1.1: Validator detects miner in metagraph"""
        from wahoo.validator.utils.miners import get_active_uids

        active_uids = get_active_uids(mock_metagraph)
        assert len(active_uids) > 0, "Should detect active miners"
        assert 2 not in active_uids, "UID 2 should be inactive (port 0)"
        assert 0 in active_uids, "UID 0 should be active"

    def test_1_validator_queries_miner_via_dendrite(
        self, mock_dendrite, mock_metagraph
    ):
        """Test 1.2: Validator queries miner via dendrite"""
        from wahoo.validator.validator import query_miners

        active_uids = [0, 1, 3, 4]
        event_id = "test_event_123"

        # Mock successful responses
        mock_responses = [
            WAHOOPredict(event_id=event_id, prob_yes=0.7, prob_no=0.3, confidence=0.8),
            WAHOOPredict(event_id=event_id, prob_yes=0.6, prob_no=0.4, confidence=0.7),
            WAHOOPredict(event_id=event_id, prob_yes=0.5, prob_no=0.5, confidence=0.6),
            WAHOOPredict(event_id=event_id, prob_yes=0.8, prob_no=0.2, confidence=0.9),
        ]
        mock_dendrite.query.return_value = mock_responses

        responses = query_miners(
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            active_uids=active_uids,
            event_id=event_id,
            timeout=12.0,
        )

        assert len(responses) == len(active_uids), "Should get response for each UID"
        assert mock_dendrite.query.called, "Dendrite query should be called"

    def test_1_miner_responds_with_valid_synapse(self, mock_dendrite, mock_metagraph):
        """Test 1.3: Miner responds with valid WAHOOPredict synapse"""
        from wahoo.validator.validator import query_miners

        active_uids = [0, 1]
        event_id = "test_event_123"

        mock_responses = [
            WAHOOPredict(event_id=event_id, prob_yes=0.7, prob_no=0.3, confidence=0.8),
            WAHOOPredict(event_id=event_id, prob_yes=0.6, prob_no=0.4, confidence=0.7),
        ]
        mock_dendrite.query.return_value = mock_responses

        responses = query_miners(
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            active_uids=active_uids,
            event_id=event_id,
            timeout=12.0,
        )

        for resp in responses:
            if resp is not None:
                assert isinstance(resp, WAHOOPredict), "Response should be WAHOOPredict"
                assert resp.event_id == event_id, "Event ID should match"
                assert 0 <= resp.prob_yes <= 1, "prob_yes should be valid"

    def test_1_communication_within_timeout(self, mock_dendrite, mock_metagraph):
        """Test 1.4: Communication works within 12s timeout"""
        from wahoo.validator.validator import query_miners

        active_uids = [0, 1]
        event_id = "test_event_123"
        timeout = 12.0

        mock_responses = [
            WAHOOPredict(event_id=event_id, prob_yes=0.7, prob_no=0.3, confidence=0.8),
            WAHOOPredict(event_id=event_id, prob_yes=0.6, prob_no=0.4, confidence=0.7),
        ]
        mock_dendrite.query.return_value = mock_responses

        start_time = time.time()
        responses = query_miners(
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            active_uids=active_uids,
            event_id=event_id,
            timeout=timeout,
        )
        elapsed = time.time() - start_time

        assert elapsed < timeout, f"Query should complete within {timeout}s"
        assert len(responses) > 0, "Should get at least one response"

    # ========== Test 2: Main Loop (9 Steps) ==========

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_event_id")
    @patch("wahoo.validator.validator.reward")
    @patch("wahoo.validator.validator.set_weights_with_retry")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_2_main_loop_all_9_steps(
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
        test_config,
    ):
        """Test 2: All 9 steps execute successfully"""
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

        # Generate mock validation data
        hotkeys = list(uid_to_hotkey.values())
        validation_records = []
        for hk in hotkeys:
            perf = PerformanceMetrics(
                total_volume_usd=10000.0,
                realized_profit_usd=500.0,
                trade_count=100,
                win_rate=0.65,
            )
            record = ValidationRecord(hotkey=hk, performance=perf)
            validation_records.append(record)
        mock_get_validation_data.return_value = validation_records

        mock_get_event_id.return_value = "test_event_123"

        mock_responses = [
            WAHOOPredict(
                event_id="test_event_123", prob_yes=0.7, prob_no=0.3, confidence=0.8
            ),
            WAHOOPredict(
                event_id="test_event_123", prob_yes=0.6, prob_no=0.4, confidence=0.7
            ),
            None,  # Timeout
            WAHOOPredict(
                event_id="test_event_123", prob_yes=0.5, prob_no=0.5, confidence=0.6
            ),
        ]
        mock_dendrite.query.return_value = mock_responses

        mock_rewards = torch.tensor([0.3, 0.3, 0.0, 0.4])
        mock_reward.return_value = mock_rewards

        mock_set_weights.return_value = ("tx_hash_123", True)

        # Run iteration
        main_loop_iteration(
            wallet=mock_wallet,
            subtensor=mock_subtensor,
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            netuid=TEST_NETUID,
            config=test_config,
            validator_db=None,
        )

        # Verify all steps were called
        assert mock_get_active_uids.called, "Step 2: get_active_uids should be called"
        assert (
            mock_build_uid_to_hotkey.called
        ), "Step 3: build_uid_to_hotkey should be called"
        assert (
            mock_get_validation_data.called
        ), "Step 4: get_wahoo_validation_data should be called"
        assert mock_get_event_id.called, "Step 5: get_active_event_id should be called"
        assert mock_dendrite.query.called, "Step 6: query_miners should be called"
        assert mock_reward.called, "Step 7: reward computation should be called"
        assert mock_set_weights.called, "Step 9: set_weights should be called"

    # ========== Test 3: Database Operations ==========

    def test_3_database_auto_creates(self, tmp_path):
        """Test 3.1: Database auto-creates"""
        from wahoo.validator.database.core import ValidatorDB  # noqa: F401
        from wahoo.validator.database.validator_db import get_or_create_database

        db_path = tmp_path / "test_validator.db"
        assert not db_path.exists(), "DB should not exist initially"

        # Create database
        conn = get_or_create_database(db_path=db_path)
        conn.close()
        assert db_path.exists(), "DB should be created automatically"

    def test_3_ema_scores_persist(self, tmp_path):
        """Test 3.2: EMA scores persist across iterations"""
        from wahoo.validator.database.core import ValidatorDB

        db_path = tmp_path / "test_validator.db"
        db = ValidatorDB(db_path=str(db_path))

        # Save scores using add_scoring_run
        scores = {
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty": 0.5,
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY": 0.3,
        }
        db.add_scoring_run(scores, reason="test")

        # Load scores
        loaded = db.get_latest_scores()
        assert len(loaded) > 0, "Should load saved scores"
        assert (
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty" in loaded
        ), "Should contain saved hotkey"

    # ========== Test 4: Scoring & Weights ==========

    def test_4_ema_volume_scorer_computes_weights(self):
        """Test 4.1: EMAVolumeScorer computes weights"""
        from wahoo.validator.scoring.operators import EMAVolumeScorer
        from wahoo.validator.dataframe import records_to_dataframe

        scorer = EMAVolumeScorer(alpha=0.3)

        # Mock validation records
        records = [
            ValidationRecord(
                hotkey="hk1",
                performance=PerformanceMetrics(
                    total_volume_usd=10000.0, realized_profit_usd=500.0
                ),
            ),
            ValidationRecord(
                hotkey="hk2",
                performance=PerformanceMetrics(
                    total_volume_usd=5000.0, realized_profit_usd=200.0
                ),
            ),
        ]

        # Convert to dataframe and run scorer
        df = records_to_dataframe(records)
        result = scorer.run(df)

        assert len(result.weights) > 0, "Should compute weights"
        assert all(w >= 0 for w in result.weights), "Weights should be non-negative"

    def test_4_weights_normalized(self):
        """Test 4.4: Weights normalized (sum to 1.0)"""
        from wahoo.validator.scoring.rewards import reward
        from unittest.mock import Mock

        # Mock responses
        mock_responses = [
            WAHOOPredict(event_id="test", prob_yes=0.7, prob_no=0.3, confidence=0.8),
            WAHOOPredict(event_id="test", prob_yes=0.6, prob_no=0.4, confidence=0.7),
        ]

        uids = [0, 1]
        mock_metagraph = Mock()
        mock_metagraph.hotkeys = ["hk1", "hk2"]

        # Mock wahoo_weights (from EMA scoring) - these should sum close to 1.0 after normalization
        wahoo_weights = {"hk1": 0.6, "hk2": 0.4}

        weights = reward(
            responses=mock_responses,
            uids=uids,
            metagraph=mock_metagraph,
            wahoo_weights=wahoo_weights,
        )
        weight_sum = weights.sum().item()

        assert (
            abs(weight_sum - 1.0) < 0.01
        ), f"Weights should sum to 1.0, got {weight_sum}"

    # ========== Test 5: Error Handling ==========

    def test_5_handles_miner_disconnection(self, mock_dendrite, mock_metagraph):
        """Test 5.1: Handles miner disconnection"""
        from wahoo.validator.validator import query_miners

        active_uids = [0, 1, 2]
        event_id = "test_event_123"

        # Simulate disconnection (None responses)
        mock_responses = [
            None,  # Disconnected
            WAHOOPredict(event_id=event_id, prob_yes=0.7, prob_no=0.3, confidence=0.8),
            None,  # Disconnected
        ]
        mock_dendrite.query.return_value = mock_responses

        responses = query_miners(
            dendrite=mock_dendrite,
            metagraph=mock_metagraph,
            active_uids=active_uids,
            event_id=event_id,
            timeout=12.0,
        )

        # Should handle None responses gracefully
        assert len(responses) == len(active_uids), "Should return response for each UID"
        assert responses[0] is None or isinstance(responses[0], WAHOOPredict)

    def test_5_handles_empty_data(
        self, mock_wallet, mock_subtensor, mock_dendrite, mock_metagraph, test_config
    ):
        """Test 5.3: Handles empty data"""
        from unittest.mock import patch

        with patch("wahoo.validator.validator.get_active_uids") as mock_get_uids:
            mock_get_uids.return_value = []  # No active UIDs

            # Should not crash
            main_loop_iteration(
                wallet=mock_wallet,
                subtensor=mock_subtensor,
                dendrite=mock_dendrite,
                metagraph=mock_metagraph,
                netuid=TEST_NETUID,
                config=test_config,
                validator_db=None,
            )

    # ========== Test 6: End-to-End ==========

    @patch("wahoo.validator.validator.get_wahoo_validation_data")
    @patch("wahoo.validator.validator.get_active_event_id")
    @patch("wahoo.validator.validator.reward")
    @patch("wahoo.validator.validator.set_weights_with_retry")
    @patch("wahoo.validator.validator.get_active_uids")
    @patch("wahoo.validator.validator.build_uid_to_hotkey")
    def test_6_end_to_end_multiple_iterations(
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
        test_config,
    ):
        """Test 6: Full loop completes successfully, runs 10+ iterations"""
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

        hotkeys = list(uid_to_hotkey.values())
        validation_records = []
        for hk in hotkeys:
            perf = PerformanceMetrics(
                total_volume_usd=10000.0,
                realized_profit_usd=500.0,
                trade_count=100,
                win_rate=0.65,
            )
            record = ValidationRecord(hotkey=hk, performance=perf)
            validation_records.append(record)
        mock_get_validation_data.return_value = validation_records

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
            WAHOOPredict(
                event_id="test_event_123", prob_yes=0.8, prob_no=0.2, confidence=0.9
            ),
        ]
        mock_dendrite.query.return_value = mock_responses

        mock_rewards = torch.tensor([0.3, 0.3, 0.2, 0.2])
        mock_reward.return_value = mock_rewards

        mock_set_weights.return_value = ("tx_hash_123", True)

        # Run 10 iterations
        iterations = 10
        for i in range(iterations):
            main_loop_iteration(
                wallet=mock_wallet,
                subtensor=mock_subtensor,
                dendrite=mock_dendrite,
                metagraph=mock_metagraph,
                netuid=TEST_NETUID,
                config=test_config,
                validator_db=None,
                iteration_count=i,
            )

        # Verify weights were set multiple times
        assert (
            mock_set_weights.call_count == iterations
        ), f"Should set weights {iterations} times"
        assert (
            mock_reward.call_count == iterations
        ), f"Should compute rewards {iterations} times"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
