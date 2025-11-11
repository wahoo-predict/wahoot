# WaHoo Predict

<div align="center">

*We reduce life to a button. Odds, not oaths. Grift responsibly.*

</div>

<div align="center">

**A Bittensor subnet for decentralized binary prediction markets**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**WaHoo Predict** is a Bittensor subnet that enables decentralized binary prediction markets. The platform sources events from [WAHOOPREDICT.com](https://wahoopredict.com/en/events), covering Sports, Economics, and other categories. 

> **⚠️ This is a validator-only repository.** Validators clone this repo to run the subnet. Miners do not need to clone this repository—they simply register on the Bittensor subnet/metagraph and use WAHOO Predict directly. Miners may reference this repo to understand validator behavior and scoring mechanisms.

This repository contains the **validator-only** implementation based on the [opentensor subnet template](https://github.com/opentensor/bittensor-subnet-template).

> **Note:** This platform provides data and signals only—no bookmaking functionality.

### How It Works

The system operates through a validator workflow:

1. **Miner Registration**: Miners register on Bittensor subnet/metagraph with their hotkey, then go to WAHOO site and create a regular login/account to start using WAHOO Predict
2. **Validators** publish event registries by mirroring WAHOO, freeze submissions at lock time, compute Brier scores after resolution, maintain 7-day EMAs, and convert scores to weights using `w ∝ exp(−EMA7[Brier])`
3. **WAHOO Rankings**: Validators periodically call WAHOO API with list of hotkeys to get miner rankings based on metrics like volume, profit, etc. (filterable by time period, e.g., past 7 days)
4. **Scoring** evaluates the last pre-lock submission using Brier scores, smoothed with a 7-day EMA, with normalized weights committed every tempo
5. **Revenue** from WAHOO affiliate programs (up to 50% rev-share/CPA) is distributed: 60% to miners, 20% to validators, and 20% to treasury

---

## ✨ Features

- 🔮 **Binary Prediction Markets**: YES/NO probability predictions for real-world events
- 📊 **Brier Score Evaluation**: Objective scoring mechanism for prediction accuracy
- 📈 **EMA Smoothing**: 7-day exponential moving average for stable weight calculation
- 🔐 **HMAC Signing**: Secure submission authentication and anti-replay protection
- 💰 **Affiliate Revenue Sharing**: Integrated revenue distribution system
- 🧪 **Comprehensive Testing**: Full test suite with pytest

---

## 🚀 Quick Start

> **For Validators:** This section is for setting up and running validators. If you're a miner, you don't need to clone this repository—just register on the Bittensor subnet and use WAHOO Predict.

### Prerequisites

- Python 3.10 or higher
- Bittensor wallet configured for validator

### Installation

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

### Running the Validator

The validator is simple: it calls APIs, scores miner responses, and sets weights on-chain.

```bash
# Set API base URL (optional, defaults to http://localhost:8000)
export API_BASE_URL=http://your-api-url.com

# Set WAHOO API URL (optional, defaults to https://api.wahoopredict.com)
export WAHOO_API_URL=https://api.wahoopredict.com

# Run validator
python neurons/validator.py \
    --netuid <netuid> \
    --wallet.name <wallet_name> \
    --wallet.hotkey <hotkey_name> \
    --logging.debug
```

**What the validator does:**
1. Syncs metagraph periodically (keeps it in sync for weight setting)
2. Gets miner rankings from WAHOO API (past 7 days)
3. Gets weights from scoring API
4. Queries miners for predictions
5. Scores responses based on API data and WAHOO rankings
6. Sets weights on-chain

**No database needed** - everything comes from APIs!

---

## 🏗️ Architecture

### Project Structure

This project follows the [opentensor subnet template](https://github.com/opentensor/bittensor-subnet-template) structure:

```
WaHoo/
├── template/          # Subnet template files
│   ├── protocol.py   # Protocol definition (WAHOOPredict synapse)
│   ├── forward.py    # Validator forward pass
│   └── reward.py     # Reward mechanism
├── neurons/          # Neuron implementations
│   └── validator.py  # Validator implementation
├── wahoopredict/     # FastAPI service and database models
└── cli/              # CLI tools for seeding, scoring, etc.
```

### Scoring System (v1)

The core scoring mechanism follows these steps:

1. **Task**: Predict `prob_yes` for each outcome in WAHOO events
2. **Scoring**: Calculate Brier score on last pre-lock submission:
   ```
   Brier = (p − y)²
   ```
   where `p` is the predicted probability and `y` is the actual outcome (0 or 1)
3. **Smoothing**: Apply per-miner EMA(7d) of Brier scores:
   ```
   alpha = 2/(7+1) = 0.25
   ```
4. **Weights**: Convert to weights and normalize:
   ```
   w_i = exp(−EMA7_i) → normalize → commit
   ```

### Optional V2 Scoring

An enhanced scoring system that blends performance with usage metrics:

```
score_i = exp(−EMA7_Brier_i) × (1 + λ₁·sqrt(usage_i) + λ₂·EMA7(referrals_i))
```

**Parameters:**
- `usage_i`: Unique clicks to WAHOO from miner pages/widgets
- `referrals_i`: Qualified first deposits from miner funnels
- `λ₁, λ₂`: Small coefficients (0.1–0.2) to keep performance as the primary factor

### Database Schema (Reference Only)

> **Note:** Validators don't need a database. This schema is for reference only to understand how the scoring API works.

| Table | Description |
|-------|-------------|
| `miners` | Miner registry and metadata |
| `events` | Binary events with lock times |
| `submissions` | Miner predictions (prob_yes, manifest_hash, sig) |
| `resolutions` | Event outcomes and sources |
| `brier_archive` | Historical Brier scores |
| `miner_stats` | EMA(7d) Brier scores per miner |
| `weights` | Normalized weights for validators |
| `affiliate_clicks` | Track clicks to WAHOO via affiliate links |
| `affiliate_postbacks` | S2S postbacks from WAHOO |
| `miner_usage` | Aggregated usage stats (clicks, referrals) |
| `revenue_pool` | Weekly affiliate revenue pool |
| `miner_revenue_share` | Individual miner allocations |

### Security Features

- **HMAC Signing**: All submissions signed with HMAC-SHA256
- **Anti-Replay**: Unique constraint on `(event_id, manifest_hash)`
- **Late Rejection**: Submissions at/after `lock_time` are rejected (HTTP 400)
- **Duplicate Detection**: Flags duplicate manifests across keys

---

## 📚 API Documentation

### WAHOO API Integration

Validators call WAHOO API to get miner rankings. See [WAHOO API Requirements](docs/WAHOO_API_REQUIREMENTS.md) for detailed specifications.

**Endpoint:** `POST /api/v1/miners/rankings`

**Request:**
```json
{
  "hotkeys": ["5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"],
  "start_date": "2024-01-01T00:00:00Z",  // Optional
  "end_date": "2024-01-08T00:00:00Z",    // Optional
  "metrics": ["volume", "profit"]        // Optional
}
```

**Response:**
```json
{
  "rankings": [
    {
      "ss58_address": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
      "rank": 1,
      "volume": 1000.0,
      "profit": 500.0,
      "metrics": {...}
    }
  ]
}
```

### Core Endpoints

#### Health Check
```bash
curl http://localhost:8000/healthz
```

#### List Events
```bash
curl http://localhost:8000/events
```

#### Submit Prediction (Miner)
```bash
curl -X POST http://localhost:8000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "wahoo_2024_election",
    "miner_id": "miner_yesman",
    "prob_yes": 0.65,
    "manifest_hash": "abc123...",
    "sig": "hmac_signature_here"
  }'
```

#### Get Aggregated Odds
```bash
curl "http://localhost:8000/agg_odds?event_id=wahoo_2024_election"
```

#### Get Current Weights
```bash
curl http://localhost:8000/weights
```

### Validator Endpoints

#### Sync Event Registry
```bash
curl -X POST http://localhost:8000/events/sync
```

Publishes event registry by mirroring WAHOO API and stamping with `lock_time` and resolution rules.

### Affiliate Endpoints

#### Generate Deeplink
```bash
curl "http://localhost:8000/affiliate/deeplink?market_id=123&affid=wahoo&subid=miner_1"
```

#### Track Click
```bash
curl -X POST "http://localhost:8000/affiliate/click?miner_id=miner_1&market_id=123&affid=wahoo&subid=miner_1"
```

#### Receive Postback (S2S)
```bash
curl -X POST "http://localhost:8000/affiliate/postback?postback_type=settled_prediction&affid=wahoo&subid=miner_1&market_id=123" \
  -H "Content-Type: application/json" \
  -d '{"outcome": true, "source": "https://wahoopredict.com/markets/123"}'
```

#### Create Revenue Pool
```bash
curl -X POST "http://localhost:8000/affiliate/revenue-pool?week_start=2024-01-01T00:00:00Z&week_end=2024-01-07T23:59:59Z&total_revenue=1000.00"
```

#### Distribute Revenue Pool
```bash
curl -X POST "http://localhost:8000/affiliate/revenue-pool/1/distribute?use_v2_scoring=false"
```

---

## 💰 Affiliate Economics

### WAHOO Affiliate Program

- **Revenue Share**: Up to 50% revenue share and/or CPA on FTDs (First Time Deposits)
- **Postbacks**: Supports `signup`, `first_deposit`, `first_prediction`, `settled_prediction` with `affid`/`subid` tracking
- **User Referrals**: 40% lifetime referral program

### Revenue Distribution

The **Affiliate Revenue Pool (ARP)** is distributed as follows:

| Recipient | Percentage | Allocation Method |
|-----------|------------|-------------------|
| **Miners** | 60% | By normalized `exp(−EMA Brier)` |
| **Validators** | 20% | By validator stake × convergence |
| **Treasury** | 20% | Operations and development |

> This revenue stream stacks on top of TAO emissions from Bittensor subnet rewards.

### Traffic & Tracking

**Deeplinks Format:**
```
https://wahoopredict.com/markets/{MARKET_ID}?utm_source=aff&utm_campaign={AFFID}&utm_content={SUBID}
```

**S2S Postbacks:** Receive `signup`/`first_deposit`/`first_prediction`/`settled_prediction` events to attribute value to channels/miners and feed the (optional) volume term.

---

## 🛠️ Development

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=wahoopredict tests/
```


### Makefile Commands

```bash
make test        # Run tests
make clean       # Clean temporary files
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | Base URL for scoring API (weights endpoint) | `http://localhost:8000` |
| `WAHOO_API_URL` | Base URL for WAHOO API (rankings endpoint) | `https://api.wahoopredict.com` |

---

## 👥 For Miners

**Miners do NOT need to clone this repository.** To participate:

1. **Register on Bittensor subnet/metagraph** with your hotkey
2. **Go to WAHOO site** and create a regular login/account
3. **Start using WAHOO Predict** - that's it!

You may reference this repository to understand:
- How validators score your predictions (see `template/reward.py` and `wahoopredict/services/scoring.py`)
- How validators query miners (see `neurons/validator.py`)
- The protocol definition (see `template/protocol.py`)

But you don't need to run any code from this repository.

---

## 👥 Validator Responsibilities

### How Validators Work

The validator runs a simple loop:

1. **Sync Metagraph**: Call `subtensor.metagraph(netuid)` to keep metagraph in sync for weight setting
2. **Get WAHOO Rankings**: Call WAHOO API with list of hotkeys to get miner rankings (past 7 days) based on metrics like volume, profit, etc.
3. **Get Weights from API**: Call scoring API to get normalized weights (computed from EMA(7d) Brier scores)
4. **Query Miners**: Query miners for predictions on active events
5. **Score Responses**: Score miner responses based on:
   - API weights (priority 1)
   - WAHOO rankings (priority 2)
   - Response validity (priority 3)
6. **Set Weights On-Chain**: Normalize scores and set weights on-chain using `subtensor.set_weights()`

**No database needed** - all data comes from APIs. The validator is stateless and simple.

### Understanding Miner Behavior

From a validator's perspective:

1. **Miners register on Bittensor subnet/metagraph** with their hotkey
2. **Miners go to WAHOO site** and create a regular login/account
3. **Miners start using WAHOO Predict** - no additional hotkey verification needed during signup
4. **Analytics**: Analytics stay with internal account ID, not the user. Only current hotkey has analytics. Miners can change hotkey in settings (old key loses analytics, new key gets analytics)


---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**WaHoo Predict** — *We reduce life to a button. Odds, not oaths.*

Made with ❤️ for the Bittensor ecosystem

</div>
