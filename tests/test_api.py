#!/usr/bin/env python3

import httpx
import json

API_BASE_URL = "https://api.wahoopredict.com"
TEST_HOTKEY = "5G6HBuhKoYUjGvbcoa6X6Tm3q2jNFek1Ry78S8gKyY5HgiDj"


def test_single_hotkey():
    print("=" * 60)
    print("Test 1: Single Hotkey")
    print("=" * 60)

    url = f"{API_BASE_URL}/api/v2/event/bittensor/statistics"
    params = {"hotkeys": TEST_HOTKEY}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"URL: {response.url}")
            print("\nResponse:")
            data = response.json()
            print(json.dumps(data, indent=2))
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_multiple_hotkeys():

    print("\n" + "=" * 60)
    print("Test 2: Multiple Hotkeys (including fake)")
    print("=" * 60)

    url = f"{API_BASE_URL}/api/v2/event/bittensor/statistics"
    params = {"hotkeys": f"{TEST_HOTKEY},fakeadresstotest"}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"URL: {response.url}")
            print("\nResponse:")
            data = response.json()
            print(json.dumps(data, indent=2))
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_with_dates():

    print("\n" + "=" * 60)
    print("Test 3: With Date Range")
    print("=" * 60)

    url = f"{API_BASE_URL}/api/v2/event/bittensor/statistics"

    start_date = "2025-10-10T12:11:08.566Z"
    end_date = "2025-11-30T12:11:08.566Z"

    params = {
        "hotkeys": f"{TEST_HOTKEY},fakeadresstotest",
        "start_date": start_date,
        "end_date": end_date,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            print(f"Status Code: {response.status_code}")
            print(f"URL: {response.url}")
            print("\nResponse:")
            data = response.json()
            print(json.dumps(data, indent=2))
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_response_structure():

    print("\n" + "=" * 60)
    print("Test 4: Response Structure Analysis")
    print("=" * 60)

    url = f"{API_BASE_URL}/api/v2/event/bittensor/statistics"
    params = {"hotkeys": TEST_HOTKEY}

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            data = response.json()

            print(f"Response Type: {type(data)}")

            if isinstance(data, dict):
                print("Response is wrapped in dict:")
                print(f"  Keys: {list(data.keys())}")
                if "status" in data:
                    print(f"  Status: {data.get('status')}")
                if "data" in data:
                    print(f"  Data type: {type(data.get('data'))}")
                    if (
                        isinstance(data.get("data"), list)
                        and len(data.get("data", [])) > 0
                    ):
                        print(f"  First item keys: {list(data['data'][0].keys())}")
            elif isinstance(data, list):
                print("Response is direct array:")
                if len(data) > 0:
                    print(f"  First item keys: {list(data[0].keys())}")
                    if "performance" in data[0]:
                        print(
                            f"  Performance keys: {list(data[0]['performance'].keys())}"
                        )

            return True
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    print("WAHOO API Endpoint Tests")
    print("=" * 60)

    results = []
    results.append(("Single Hotkey", test_single_hotkey()))
    results.append(("Multiple Hotkeys", test_multiple_hotkeys()))
    results.append(("With Date Range", test_with_dates()))
    results.append(("Structure Analysis", test_response_structure()))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
