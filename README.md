# WaHoo Predict

<div align="center">

*We reduce life to a button. Odds, not oaths. Grift responsibly.*

**A Bittensor subnet for decentralized binary prediction markets**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## 🎯 Overview

**WaHoo Predict** is a Bittensor subnet that enables decentralized binary prediction markets. Validators score miners based on their trading performance on [WAHOOPREDICT.com](https://wahoopredict.com), using real-time metrics like volume, profit, and prediction accuracy.

> **⚠️ This is a validator-only repository.** Validators clone this repo to run the subnet. Miners simply register on the Bittensor subnet and use WAHOO Predict directly.

---

## 👥 For Miners

**Want to participate as a miner?** It's simple:

1. **Register on the Bittensor subnet** with your hotkey
2. **Sign up at [wahoopredict.com/miners](https://wahoopredict.com/miners)** with your hotkey and signature
3. **Start trading on WAHOO Predict** - your performance automatically determines your rewards

**That's it!** No code to run, no repository to clone. Just trade and earn.

### How It Works

- Validators periodically query the WAHOO API with all registered hotkeys
- Your trading performance (volume, profit, win rate) determines your weight
- Weights are set on-chain every ~100 seconds
- Better performance = higher weight = more rewards

**Questions?** Check out the [WAHOO Predict documentation](https://wahoopredict.com/docs) or join our community.

---

## 🚀 For Validators

### Quick Start

#### Prerequisites

- Python 3.10+
- Bittensor wallet configured for validator
- Access to scoring API (optional, for Brier score-based weights)

#### Installation

```bash
# Clone the repository
git clone https://github.com/Bet-TyWhite/WaHoo.git
cd WaHoo

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Running the Validator

```bash
# Set environment variables (optional)
export API_BASE_URL=http://your-api-url.com          # Scoring API (optional)
export WAHOO_API_URL=https://api.wahoopredict.com    # WAHOO API (default)
export USE_VALIDATOR_DB=true                         # Enable SQLite backup (optional)
export VALIDATOR_DB_PATH=/path/to/validator.db       # Custom DB path (optional)

# Run validator
python neurons/validator.py \
    --netuid <netuid> \
    --wallet.name <wallet_name> \
    --wallet.hotkey <hotkey_name> \
    --logging.debug
```

### What the Validator Does

The validator runs a continuous loop (every ~100 seconds):

1. **Sync Metagraph** - Keeps metagraph in sync for weight setting
2. **Get WAHOO Validation Data** - Calls `GET /api/v2/users/validation` with list of hotkeys
3. **Query Miners** - Queries miners for predictions on active events
4. **Compute Rewards** - Scores based on:
   - WAHOO performance metrics (volume, profit) - **Primary**
   - Scoring API weights (Brier scores) - **Fallback**
   - Response validity - **Last resort**
5. **Set Weights On-Chain** - Normalizes and commits weights to blockchain

### Validator Database Backup (Optional)

Validators can enable a lightweight SQLite backup database:

```bash
export USE_VALIDATOR_DB=true
```

This will:
- Cache validation data and weights locally
- Automatically fall back if APIs go down
- Store data in `~/.wahoo/validator.db` (or custom path)
- Auto-cleanup cache older than 7 days

**Benefits:**
- Continue operating if AWS/API is down
- Faster lookups for frequently accessed data
- Historical data for analysis

---

## 📚 API Integration

### WAHOO API

Validators call the WAHOO API to get miner performance data:

**Endpoint:** `GET /api/v2/users/validation`

**Query Parameters:**
- `hotkeys` (required): Comma-separated list of SS58 hotkey addresses (max 246 per request)
- `start_date` (optional): ISO 8601 datetime string (e.g., `2024-01-01T00:00:00Z`)
- `end_date` (optional): ISO 8601 datetime string

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "hotkey": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
      "signature": "0x...",
      "message": "hello",
      "performance": {
        "total_volume_usd": 10500.75,
        "realized_profit_usd": 875.20,
        "unrealized_profit_usd": 45.10,
        "win_rate": 0.62,
        ...
      }
    }
  ]
}
```

**Date Filtering:**
- Both `start_date` and `end_date`: Returns data for that time range
- Only `start_date`: Returns data from start date to now
- Only `end_date`: Returns data from beginning to end date
- Neither: Returns all historical data for registered miners

### Scoring API (Optional)

If you're running a scoring API service, validators can fetch Brier score-based weights:

**Endpoint:** `GET /weights`

**Response:**
```json
{
  "weights": [
    {"miner_id": "5Grwva...", "weight": 0.05},
    ...
  ],
  "updated_at": "2024-01-01T00:00:00Z",
  "sum": 1.0
}
```

---

## 🏗️ Architecture

### Project Structure

```
WaHoo/
├── template/              # Subnet template files
│   ├── protocol.py       # Protocol definition (WAHOOPredict synapse)
│   └── reward.py         # Reward mechanism
└── neurons/              # Neuron implementations
    ├── validator.py      # Validator implementation
    ├── scoring.py        # Scoring system (computes weights from WAHOO data)
    └── validator_db.py   # SQLite backup database (optional)
```

### Scoring System

Validators use `neurons/scoring.py` to compute weights from WAHOO API data:

1. **Get WAHOO Validation Data** - Calls WAHOO API with list of hotkeys
2. **Compute Weights** - Uses `compute_final_weights()` to score miners based on:
   - `total_volume_usd` - Trading volume (normalized by 1000)
   - `realized_profit_usd` - Closed position profits
   - `unrealized_profit_usd` - Open position profits
   - Formula: `raw_score = 1.0 + (volume/1000) + (profit/100)`
3. **Normalize** - Weights are normalized to sum to 1.0
4. **Set On-Chain** - Weights are committed to blockchain

**Scoring Priority:**
- **Primary**: WAHOO performance metrics (computed locally)
- **Fallback**: Optional scoring API weights (if configured)
- **Last Resort**: Response validity (ensures all responding miners get some weight)

### Miner Sign-Up Flow

1. Miner registers on Bittensor subnet with hotkey
2. Miner signs a message with their hotkey (proves ownership)
3. Miner visits `wahoopredict.com/miners` and submits:
   - `ss58_hotkey`
   - `signature_message` (the message they signed)
   - `signature` (the signature)
4. Service verifies hotkey signature → creates miner record
5. Miner can now trade on WAHOO Predict

**API Endpoints:**
- `POST /miners/signup` - Miner registration
- `POST /miners/verify` - Hotkey verification (for serverless/AWS)
- `GET /miners/verification-message` - Get message to sign

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | Scoring API base URL | `http://localhost:8000` |
| `WAHOO_API_URL` | WAHOO API base URL | `https://api.wahoopredict.com` |
| `USE_VALIDATOR_DB` | Enable SQLite backup | `false` |
| `VALIDATOR_DB_PATH` | Custom database path | `~/.wahoo/validator.db` |

### Validator Loop Timing

- **Metagraph Sync**: Every loop iteration (~100 seconds)
- **WAHOO API Call**: Every loop iteration
- **Miner Queries**: Every loop iteration
- **Weight Setting**: Every loop iteration (if rewards > 0)
- **Cache Cleanup**: Every loop iteration (if validator DB enabled)

---

## 🔧 Development

This repository is minimal and focused on validators. For development of the scoring API or other services, see the separate development repository.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**WaHoo Predict** — *We reduce life to a button. Odds, not oaths.*

Made with ❤️ for the Bittensor ecosystem

</div>
