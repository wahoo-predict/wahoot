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

**WaHoo Predict** is a Bittensor subnet that enables decentralized binary prediction markets. The platform sources events from [WAHOOPREDICT.com](https://wahoopredict.com/en/events), covering Sports, Economics, and other categories. Miners submit calibrated probability predictions (`prob_yes ∈ [0,1]`) for events before lock time, while validators score submissions using Brier scores, apply exponential moving averages (EMA), and push normalized weights on-chain.

> **Note:** This platform provides data and signals only—no bookmaking functionality.

### How It Works

The system operates through a coordinated workflow between miners and validators:

1. **Miners** pull live markets from WAHOO's API, generate `prob_yes` predictions before lock time, and post signed submissions
2. **Validators** publish event registries by mirroring WAHOO, freeze submissions at lock time, compute Brier scores after resolution, maintain 7-day EMAs, and convert scores to weights using `w ∝ exp(−EMA7[Brier])`
3. **Scoring** evaluates the last pre-lock submission using Brier scores, smoothed with a 7-day EMA, with normalized weights committed every tempo
4. **Revenue** from WAHOO affiliate programs (up to 50% rev-share/CPA) is distributed: 60% to miners, 20% to validators, and 20% to treasury

---

## ✨ Features

- 🔮 **Binary Prediction Markets**: YES/NO probability predictions for real-world events
- 📊 **Brier Score Evaluation**: Objective scoring mechanism for prediction accuracy
- 📈 **EMA Smoothing**: 7-day exponential moving average for stable weight calculation
- 🔐 **HMAC Signing**: Secure submission authentication and anti-replay protection
- 💰 **Affiliate Revenue Sharing**: Integrated revenue distribution system
- 🐳 **Docker Support**: Easy deployment with Docker Compose
- 🧪 **Comprehensive Testing**: Full test suite with pytest

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 12+
- Docker and Docker Compose (optional, for containerized deployment)

### Docker Compose (Recommended)

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/Bet-TyWhite/WaHoo.git
cd WaHoo

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor

# Start services
make up          # Start PostgreSQL and FastAPI
make migrate     # Run database migrations
make seed        # Seed demo data
```

The API will be available at `http://localhost:8000`

### Local Development

For local development without Docker:

```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
createdb wahoopredict

# Run migrations
alembic upgrade head

# Seed demo data
python -m cli.seed

# Start development server
uvicorn wahoopredict.main:app --reload
```

---

## 🏗️ Architecture

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

### Database Schema

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

### CLI Commands

```bash
# Seed demo data
python -m cli.seed

# Resolve an event
python -m cli.resolve --event wahoo_2024_election --outcome true --source "https://wahoopredict.com/results/2024-election"

# Score miners (compute Brier, update EMA, recalculate weights)
python -m cli.score

# Export weights for on-chain weight setting
python -m cli.export_weights
```

### Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=wahoopredict tests/
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Makefile Commands

```bash
make up          # Start Docker services
make down        # Stop Docker services
make migrate     # Run Alembic migrations
make seed        # Seed demo data
make test        # Run tests
make clean       # Clean temporary files
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `API_SECRET` | Secret for HMAC verification | Required |
| `WAHOO_BASE_URL` | WAHOOPREDICT API base URL | `https://api.wahoopredict.com` |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## 👥 Roles & Responsibilities

### How Miners Work

1. **Pull Events**: Fetch live markets from WAHOO API (`/events` or `/event/events-list`)
2. **Generate Predictions**: Produce `prob_yes ∈ [0,1]` for each outcome before lock time
   - Your approach can be ML, news scraping, statistical models, or any method—only accuracy matters
3. **Post Submissions**: Submit one signed submission per event before lock time
   - Only the final pre-lock submission counts toward scoring
   - Include manifest hash for de-duplication
4. **Objective**: Minimize Brier score after event resolution

### How Validators Work

1. **Publish Registry**: Mirror WAHOO (`/event/events-list`) and stamp with `lock_time` and resolution rules/links
2. **Freeze Book**: At lock time, reject all new submissions
3. **Compute Scores**: Once WAHOO settles (via `settled_prediction` postback), compute Brier scores per miner
4. **Maintain EMA**: Calculate and update 7-day EMA of each miner's Brier scores
5. **Set Weights**: Convert to weights using `w ∝ exp(−EMA7[Brier])`, normalize, and commit every tempo
6. **Anti-Grift**: Reject late submissions, flag duplicate manifests, penalize low coverage

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

**WaHoo Predict** — *We reduce life to a button. Odds, not oaths.*

Made with ❤️ for the Bittensor ecosystem

</div>
