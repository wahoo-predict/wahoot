#!/usr/bin/env python3
"""
Comprehensive test status checker for localnet testing
Checks all critical test criteria from the test plan
"""

import os
import sys
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

# Colors
GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"  # No Color


def check_processes():
    """Test 1: Check if validator and miners are running"""
    print(
        f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}"
    )
    print(f"{BLUE}TEST 1: Validator-Miner Communication{NC}")
    print(
        f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n"
    )

    results = {}

    # Check validator
    try:
        validator_count = int(
            subprocess.check_output(
                ["pgrep", "-f", "python.*validator"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
            .count("\n")
            + 1
        )
        results["validator_running"] = validator_count > 0
        print(
            f"{GREEN if results['validator_running'] else RED}{'✓' if results['validator_running'] else '✗'}{NC} Validator running: {validator_count} process(es)"
        )
    except Exception:
        results["validator_running"] = False
        print(f"{RED}✗{NC} Validator not running")

    # Check miners
    try:
        miner_count = int(
            subprocess.check_output(
                ["pgrep", "-f", "python.*miner"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
            .count("\n")
            + 1
        )
        results["miners_running"] = miner_count >= 3
        print(
            f"{GREEN if results['miners_running'] else RED}{'✓' if results['miners_running'] else '✗'}{NC} Miners running: {miner_count} (expected 3+)"
        )
    except Exception:
        results["miners_running"] = False
        print(f"{RED}✗{NC} Miners not running")

    return results


def check_logs():
    """Test 2: Check validator logs for connectivity and weight computation"""
    print(
        f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}"
    )
    print(f"{BLUE}TEST 2: Main Loop Execution & Weight Computation{NC}")
    print(
        f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n"
    )

    results = {}
    log_file = Path("validator.log")

    if not log_file.exists():
        print(f"{YELLOW}⚠{NC} Log file not found: {log_file}")
        return results

    # Read last 200 lines
    with open(log_file, "r") as f:
        lines = f.readlines()[-200:]
        log_content = "".join(lines)

    # Check for queried miners
    if "Queried" in log_content and "miners" in log_content:
        # Try to extract count
        import re

        matches = re.findall(r"Queried (\d+) miners", log_content)
        if matches:
            queried_count = int(matches[-1])
            results["miners_queried"] = queried_count >= 3
            print(
                f"{GREEN if results['miners_queried'] else YELLOW}{'✓' if results['miners_queried'] else '⚠'}{NC} Validator queried {queried_count} miners"
            )
        else:
            results["miners_queried"] = True
            print(f"{GREEN}✓{NC} Validator queried miners (count not found)")
    else:
        results["miners_queried"] = False
        print(f"{YELLOW}⚠{NC} No 'Queried miners' log found")

    # Check for EMA scoring
    if "EMA Scoring" in log_content:
        results["ema_scoring"] = True
        print(f"{GREEN}✓{NC} EMA scoring found in logs")
    else:
        results["ema_scoring"] = False
        print(f"{YELLOW}⚠{NC} EMA scoring not found in logs")

    # Check for rewards sum
    if "Rewards sum: 1.000000" in log_content:
        results["weights_normalized"] = True
        print(f"{GREEN}✓{NC} Weights sum to 1.0")
    else:
        results["weights_normalized"] = False
        print(f"{YELLOW}⚠{NC} Weights do not sum to 1.0 (or not found)")

    # Check iteration count
    iteration_count = log_content.count("Starting main loop iteration")
    results["iterations"] = iteration_count
    print(
        f"{GREEN if iteration_count > 0 else YELLOW}{'✓' if iteration_count > 0 else '⚠'}{NC} Found {iteration_count} loop iterations"
    )

    return results


def check_database():
    """Test 3: Check database operations"""
    print(
        f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}"
    )
    print(f"{BLUE}TEST 3: Database Operations{NC}")
    print(
        f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n"
    )

    results = {}
    db_path = os.getenv("WAHOO_DB_PATH", "validator.db")

    if not Path(db_path).exists():
        results["db_exists"] = False
        print(f"{RED}✗{NC} Database not found: {db_path}")
        return results

    results["db_exists"] = True
    print(f"{GREEN}✓{NC} Database exists: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check scoring_runs table
        cursor.execute("SELECT COUNT(*) FROM scoring_runs")
        score_count = cursor.fetchone()[0]
        results["scoring_runs"] = score_count
        print(
            f"{GREEN if score_count > 0 else YELLOW}{'✓' if score_count > 0 else '⚠'}{NC} Scoring runs: {score_count}"
        )

        # Check unique miners
        cursor.execute("SELECT COUNT(DISTINCT hotkey) FROM scoring_runs")
        unique_miners = cursor.fetchone()[0]
        results["unique_miners"] = unique_miners
        print(
            f"{GREEN if unique_miners >= 3 else YELLOW}{'✓' if unique_miners >= 3 else '⚠'}{NC} Unique miners in DB: {unique_miners} (expected 3+)"
        )

        # Check latest scores
        cursor.execute(
            """
            SELECT hotkey, score, ts
            FROM scoring_runs
            ORDER BY ts DESC
            LIMIT 10
        """
        )
        latest = cursor.fetchall()
        if latest:
            print(f"\n{GREEN}✓{NC} Latest scores:")
            for hotkey, score, ts in latest[:5]:
                print(f"   {hotkey[:16]}...: {score:.6f} ({ts})")

        conn.close()

    except Exception as e:
        results["db_error"] = str(e)
        print(f"{RED}✗{NC} Database error: {e}")

    return results


def check_weight_setting():
    """Test 7: Check if weights were set on blockchain"""
    print(
        f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}"
    )
    print(f"{BLUE}TEST 7: Weight Setting on Blockchain{NC}")
    print(
        f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n"
    )

    results = {}
    log_file = Path("validator.log")

    if not log_file.exists():
        print(f"{YELLOW}⚠{NC} Log file not found")
        return results

    with open(log_file, "r") as f:
        lines = f.readlines()[-300:]
        log_content = "".join(lines)

    # Check for success message
    if "✓✓✓ WEIGHTS SET SUCCESSFULLY" in log_content:
        results["weights_set"] = True
        print(f"{GREEN}✓✓✓{NC} Weights set successfully on blockchain!")

        # Extract transaction hash
        import re

        tx_match = re.search(r"Transaction Hash: ([^\s]+)", log_content)
        if tx_match:
            tx_hash = tx_match.group(1)
            print(f"{GREEN}✓{NC} Transaction hash: {tx_hash}")
            results["tx_hash"] = tx_hash

        # Extract weight distribution
        if "Weight Distribution:" in log_content:
            print(f"\n{GREEN}✓{NC} Weight distribution found in logs")
            # Extract UID and weight lines
            for line in lines:
                if "UID" in line and ":" in line and "%" in line:
                    print(f"   {line.strip()}")
    else:
        results["weights_set"] = False
        print(f"{RED}✗{NC} Weights NOT set successfully yet")

        # Check for tempo errors
        if "too soon to commit weights" in log_content:
            print(f"{YELLOW}⚠{NC} Tempo restriction active - waiting for tempo window")
            print(
                "   This is normal on localnet - weights will be set when tempo allows"
            )

        # Count failures
        fail_count = log_content.count("Failed to set weights")
        if fail_count > 0:
            print(f"{YELLOW}⚠{NC} Found {fail_count} 'Failed to set weights' messages")

    return results


def main():
    print("=" * 70)
    print("LOCALNET TEST STATUS CHECKER")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_results = {}

    # Run all checks
    all_results.update(check_processes())
    all_results.update(check_logs())
    all_results.update(check_database())
    all_results.update(check_weight_setting())

    # Summary
    print(
        f"\n{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}"
    )
    print(f"{BLUE}SUMMARY{NC}")
    print(
        f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}\n"
    )

    critical_tests = [
        ("validator_running", "Validator Running"),
        ("miners_running", "Miners Running"),
        ("miners_queried", "Miners Queried"),
        ("weights_normalized", "Weights Normalized"),
        ("db_exists", "Database Exists"),
        ("weights_set", "Weights Set on Blockchain"),
    ]

    passed = 0
    failed = 0
    pending = 0

    for key, name in critical_tests:
        if key in all_results:
            value = all_results[key]
            if value is True:
                print(f"{GREEN}✓{NC} {name}")
                passed += 1
            elif value is False:
                print(f"{RED}✗{NC} {name}")
                failed += 1
            else:
                print(f"{YELLOW}⚠{NC} {name}: {value}")
                pending += 1

    print(
        f"\n{GREEN if failed == 0 else YELLOW}Passed: {passed} | Failed: {failed} | Pending: {pending}{NC}"
    )

    if failed == 0 and passed >= 4:
        print(f"\n{GREEN}✓ Critical tests are passing!{NC}")
        return 0
    elif failed > 0:
        print(f"\n{RED}✗ Some critical tests are failing{NC}")
        return 1
    else:
        print(f"\n{YELLOW}⚠ Tests are pending or incomplete{NC}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
