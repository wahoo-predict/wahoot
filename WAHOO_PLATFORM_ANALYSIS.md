# WAHOO Predict Platform & Bittensor Subnet Integration Analysis

## Executive Summary

**WaHoo Predict** is a Bittensor subnet that creates a decentralized bridge between the **WAHOO Predict prediction market platform** and the Bittensor network. The subnet rewards miners (traders) based on their real trading performance on [WAHOOPREDICT.com](https://wahoopredict.com), creating a unique incentive mechanism where Bittensor rewards are tied to actual market participation and performance.

---

## Part 1: WAHOO Predict Platform Overview

### What is WAHOO Predict?

According to the [official documentation](https://wahoopredict.gitbook.io/wahoopredict-docs/getting-started/what-is-wahoopredict), **WAHOO Predict** is:

> A next-generation prediction platform that captures real-time sentiment across global events and sports. Unlike traditional polls or static news reports, WahooPredict reflects what people believe right now, providing a dynamic and data-driven view of collective opinion.

### Key Platform Features

1. **Real-Time Prediction Markets**
   - Users make predictions on unfolding events (political, economic, sports)
   - Probabilities adjust dynamically based on user sentiment and trading activity
   - Events range from political decisions to live sports matches

2. **Binary Prediction Markets**
   - Events have binary outcomes (Yes/No)
   - Users trade on probabilities (0.0 to 1.0)
   - Markets settle based on real-world outcomes

3. **Categories**
   - **Events**: Political, economic, news-based predictions
   - **Sports**: Football, basketball, tennis, and other major competitions
   - **Economics**: Market movements, economic indicators

4. **Platform Access**
   - Web interface: [wahoopredict.com/en/events](https://wahoopredict.com/en/events)
   - API for developers: [API Documentation](https://wahoopredict.gitbook.io/wahoopredict-docs/api/api-for-developers)
   - User accounts with balances and trading history

### Platform Architecture

The platform operates as a traditional prediction market:
- Users deposit funds
- Place orders on event outcomes
- Trade positions (buy/sell)
- Collect winnings when events settle
- Track performance metrics (volume, profit, win rate)

---

## Part 2: Bittensor Subnet Integration

### How WaHoo Subnet Connects to WAHOO Predict

The WaHoo Bittensor subnet creates a **decentralized reward layer** on top of the WAHOO Predict platform:

```
┌─────────────────────────────────────────────────────────┐
│              WAHOO Predict Platform                      │
│  (Centralized prediction market - wahoopredict.com)      │
│                                                           │
│  • Users trade on binary events                          │
│  • Track volume, profit, win rate                        │
│  • API provides performance data                          │
└───────────────────┬─────────────────────────────────────┘
                    │
                    │ API Integration
                    │ GET /api/v2/users/validation
                    │
┌───────────────────▼─────────────────────────────────────┐
│          WaHoo Bittensor Subnet                        │
│                                                          │
│  Validators:                                            │
│  • Query WAHOO API for miner performance                │
│  • Score miners based on trading metrics                │
│  • Set weights on Bittensor blockchain                  │
│                                                          │
│  Miners:                                                │
│  • Register hotkey on Bittensor subnet                  │
│  • Link hotkey to WAHOO account                         │
│  • Trade on WAHOO Predict                              │
│  • Earn TAO rewards based on performance                │
└──────────────────────────────────────────────────────────┘
```

### Unique Value Proposition

Unlike most Bittensor subnets where miners run code and validators evaluate outputs, **WaHoo subnet**:

1. **No Code Required for Miners**: Miners don't need to run any code - they just trade on WAHOO Predict
2. **Real Performance Metrics**: Rewards are based on actual trading performance (volume, profit, accuracy)
3. **External Platform Integration**: Leverages existing prediction market infrastructure
4. **Decentralized Rewards**: Bittensor validators distribute TAO rewards based on centralized platform performance

---

## Part 3: Miner Registration & Participation Flow

### Step-by-Step Miner Onboarding

#### 1. Register on Bittensor Subnet
```bash
btcli wallet register --netuid <netuid>
```
- Miner registers their hotkey on the WaHoo subnet
- Receives a unique UID
- Becomes part of the metagraph

#### 2. Sign Message with Hotkey
- Miner signs a message using their Bittensor hotkey
- This proves ownership of the hotkey
- Message format: `"hello"` (or custom message from API)

#### 3. Link Hotkey to WAHOO Account
- Miner visits: `wahoopredict.com/miners`
- Submits registration form with:
  - `ss58_hotkey`: Their Bittensor hotkey address
  - `signature_message`: The message they signed
  - `signature`: The cryptographic signature

#### 4. WAHOO Platform Verification
- WAHOO API verifies the hotkey signature
- Creates a miner record linking hotkey to WAHOO account
- Miner can now trade on WAHOO Predict

#### 5. Start Trading
- Miner trades on WAHOO Predict platform
- Performance is automatically tracked:
  - `total_volume_usd`: Total trading volume
  - `realized_profit_usd`: Closed position profits
  - `unrealized_profit_usd`: Open position profits
  - `win_rate`: Percentage of winning trades

#### 6. Earn Bittensor Rewards
- Validators periodically query WAHOO API for miner performance
- Performance metrics are converted to Bittensor weights
- TAO emissions are distributed based on weights
- Better performance = higher weight = more TAO rewards

### Miner API Endpoints

Based on the codebase, WAHOO provides these endpoints for miners:

- `POST /miners/signup` - Miner registration
- `POST /miners/verify` - Hotkey verification
- `GET /miners/verification-message` - Get message to sign

---

## Part 4: Validator Integration with WAHOO API

### Validator API Integration

Validators integrate with WAHOO Predict through the following API endpoint:

#### Primary Endpoint: `GET /api/v2/users/validation`

**Purpose**: Retrieve performance data for registered miners

**Request**:
```http
GET https://api.wahoopredict.com/api/v2/users/validation?hotkeys=<hotkey1>,<hotkey2>,...&start_date=<ISO8601>&end_date=<ISO8601>
```

**Query Parameters**:
- `hotkeys` (required): Comma-separated list of SS58 hotkey addresses
  - Max 246-248 hotkeys per request (batched for larger lists)
- `start_date` (optional): ISO 8601 datetime string (e.g., `2024-01-01T00:00:00Z`)
- `end_date` (optional): ISO 8601 datetime string

**Date Filtering Logic**:
- Both `start_date` and `end_date`: Returns data for that time range
- Only `start_date`: Returns data from start date to now
- Only `end_date`: Returns data from beginning to end date
- Neither: Returns all historical data for registered miners

**Response Format**:
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

### Validator Implementation Details

From `neurons/validator.py`, validators:

1. **Batch Hotkey Requests**
   - Split large hotkey lists into batches of 246
   - Make multiple API calls if needed
   - Aggregate results

2. **Handle API Failures**
   - Graceful error handling
   - Fallback to cached data (if validator DB enabled)
   - Continue operation even if API is temporarily down

3. **Cache Validation Data**
   - Optional SQLite database (`ValidatorDB`)
   - Cache validation data and weights locally
   - Auto-cleanup cache older than 7 days
   - Enables operation during API outages

---

## Part 5: Scoring Mechanism

### Performance Metrics Used

The scoring system (`neurons/scoring.py`) evaluates miners based on:

1. **Total Volume (USD)**
   - `total_volume_usd`: Total amount traded on WAHOO Predict
   - Indicates market participation and activity
   - Higher volume = more engagement

2. **Realized Profit (USD)**
   - `realized_profit_usd`: Profits from closed positions
   - Measures actual trading success
   - Positive profit = profitable trading

3. **Unrealized Profit (USD)**
   - `unrealized_profit_usd`: Potential profits from open positions
   - Current position value
   - May change as events progress

4. **Win Rate**
   - Percentage of winning trades
   - Measures prediction accuracy
   - Higher win rate = better predictions

### Scoring Algorithm

The `compute_final_weights()` function implements a **dual-ranking system**:

#### Step 1: Rank by Spending
- Extract `total_volume_usd` for each miner
- Rank miners by volume (highest to lowest)
- Assign percentile ranks (1.0 for best, decreasing to 0.0 for worst)

#### Step 2: Rank by Volume
- Currently uses same metric (`total_volume_usd`)
- Can be extended to use different metrics
- Assign percentile ranks

#### Step 3: Combine Rankings
- Weighted average of spending rank and volume rank
- Default weights: 50% spending, 50% volume
- Configurable via `spending_weight` and `volume_weight` parameters

#### Step 4: Normalize to Sum to 1.0
- All weights must sum to 1.0 (Bittensor requirement)
- Ensures proper distribution of emissions
- Handles edge cases (all zeros, empty data)

### Scoring Priority (Fallback Chain)

From `template/reward.py`, the reward function uses a priority system:

1. **Primary**: WAHOO performance weights (computed from API data)
   - Based on actual trading metrics
   - Most accurate and fair

2. **Fallback**: Optional scoring API weights
   - Alternative scoring service (if configured)
   - Can use Brier scores or other metrics

3. **Last Resort**: Response validity
   - Basic check: `0.0 <= prob_yes <= 1.0`
   - Ensures responding miners get some weight
   - Prevents total exclusion

### Example Scoring Flow

```
Miner A: volume=$10,000, profit=$500
Miner B: volume=$5,000, profit=$300
Miner C: volume=$1,000, profit=$50

Step 1: Rank by volume
  A: rank=1.0 (best)
  B: rank=0.67
  C: rank=0.33

Step 2: Rank by volume (same for now)
  A: rank=1.0
  B: rank=0.67
  C: rank=0.33

Step 3: Combine (50/50 weights)
  A: (1.0 * 0.5) + (1.0 * 0.5) = 1.0
  B: (0.67 * 0.5) + (0.67 * 0.5) = 0.67
  C: (0.33 * 0.5) + (0.33 * 0.5) = 0.33

Step 4: Normalize (sum=2.0, divide by 2.0)
  A: 1.0 / 2.0 = 0.50 (50% of emissions)
  B: 0.67 / 2.0 = 0.335 (33.5% of emissions)
  C: 0.33 / 2.0 = 0.165 (16.5% of emissions)
```

---

## Part 6: Validator Loop & Operations

### Main Validator Loop

The validator runs a continuous loop every ~100 seconds:

```python
while True:
    # 1. Sync metagraph
    metagraph = subtensor.metagraph(netuid)
    
    # 2. Get active miners
    active_uids = get_active_uids(metagraph)
    hotkeys = [metagraph.hotkeys[uid] for uid in active_uids]
    
    # 3. Get WAHOO validation data
    validation_data = get_wahoo_validation_data(
        hotkeys=hotkeys,
        start_date=None,  # All history
        end_date=None
    )
    
    # 4. Compute weights from WAHOO data
    wahoo_weights = compute_final_weights(
        validation_data=validation_data,
        spending_weight=0.5,
        volume_weight=0.5
    )
    
    # 5. Query miners (optional - for response validation)
    event_id = get_active_event_id(API_BASE_URL)
    responses = dendrite.query(axons, synapses, timeout=12.0)
    
    # 6. Compute rewards (combines WAHOO weights with responses)
    rewards = reward(
        responses=responses,
        uids=active_uids,
        metagraph=metagraph,
        wahoo_weights=wahoo_weights,
        wahoo_validation_data=validation_data
    )
    
    # 7. Set weights on-chain
    if rewards.sum() > 0:
        subtensor.set_weights(
            wallet=wallet,
            netuid=netuid,
            uids=active_uids,
            weights=rewards
        )
    
    # 8. Wait before next iteration
    time.sleep(100)
```

### Key Operations

1. **Metagraph Sync** (~100s)
   - Updates local state with blockchain state
   - Tracks registered miners and their hotkeys

2. **WAHOO API Call** (~100s)
   - Fetches performance data for all active miners
   - Batches requests if needed (max 246 hotkeys per request)
   - Caches data locally (if validator DB enabled)

3. **Miner Queries** (~100s)
   - Optional: Queries miners for predictions on active events
   - Used for response validation (fallback scoring)
   - Timeout: 12 seconds

4. **Weight Setting** (~100s)
   - Posts normalized weights to Bittensor blockchain
   - Influences TAO emission distribution
   - Only if rewards sum > 0

5. **Cache Cleanup** (~100s, if enabled)
   - Removes cached data older than 7 days
   - Prevents database bloat

---

## Part 7: WAHOO Predict API Overview

### Available API Endpoints

Based on the [API documentation](https://wahoopredict.gitbook.io/wahoopredict-docs/api/api-for-developers), WAHOO Predict provides:

#### Event Management
- `POST /api/v2/event/events-list` - Get list of events
- `GET /api/v2/event/{eventId}` - Get detailed event information
- `GET /api/v2/event/{eventId}/orderbook` - Get order book for event

#### Trading Operations
- `POST /api/v2/event/test-order` - Test order placement
- `POST /api/v2/event/place-order` - Place an order
- `DELETE /api/v2/event/cancel-order` - Cancel an order
- `POST /api/v2/event/collect-position` - Collect settled position

#### User Data
- `POST /api/v2/event/orders` - Get user's orders
- `POST /api/v2/event/positions` - Get user's positions
- `GET /api/v2/user/profile` - Get user profile

#### Subnet-Specific Endpoints
- `GET /api/v2/users/validation` - **Used by validators** to get miner performance data
- `POST /miners/signup` - Miner registration
- `POST /miners/verify` - Hotkey verification
- `GET /miners/verification-message` - Get message to sign

### Event Structure

Events on WAHOO Predict have:
- **ID**: Unique event identifier
- **Title**: Event description
- **Status**: `LIVE`, `PENDING`, `SETTLED`
- **Type**: `COLLECTION` (binary event)
- **Outcomes**: Yes/No options
- **Outcome Options**: Trading options with probabilities
- **Volume**: Total trading volume
- **Estimated End**: Expected settlement date

### Order Types

- **LIMIT**: Order at specific price
- **MARKET**: Order at current market price
- **Sides**: `BUY` or `SELL`
- **Status**: `OPEN`, `FILLED`, `CANCELLED`

---

## Part 8: Architecture & Data Flow

### Complete System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WAHOO Predict Platform                    │
│                  (Centralized Infrastructure)                │
│                                                               │
│  • Web Interface (wahoopredict.com)                          │
│  • Trading Engine                                             │
│  • User Accounts & Balances                                  │
│  • Event Management                                           │
│  • Performance Tracking                                       │
│  • API Server (api.wahoopredict.com)                         │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            │ REST API
                            │
┌───────────────────────────▼───────────────────────────────────┐
│              WaHoo Bittensor Subnet                          │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Validator Nodes                         │    │
│  │                                                       │    │
│  │  1. Sync Metagraph (blockchain state)                │    │
│  │  2. Query WAHOO API (GET /users/validation)         │    │
│  │  3. Compute Weights (scoring.py)                     │    │
│  │  4. Query Miners (optional validation)               │    │
│  │  5. Set Weights On-Chain (subtensor.set_weights)     │    │
│  │                                                       │    │
│  │  Optional: ValidatorDB (SQLite cache)                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Miner Nodes                              │    │
│  │                                                       │    │
│  │  1. Register on Bittensor subnet                      │    │
│  │  2. Link hotkey to WAHOO account                     │    │
│  │  3. Trade on WAHOO Predict                           │    │
│  │  4. Receive TAO rewards (based on performance)       │    │
│  │                                                       │    │
│  │  No code required - just trade!                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Bittensor Blockchain                          │    │
│  │                                                       │    │
│  │  • Metagraph (miner/validator registry)              │    │
│  │  • Weight Storage (validator submissions)            │    │
│  │  • Yuma Consensus (weight aggregation)                │    │
│  │  • TAO Emissions (reward distribution)                │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

### Data Flow: Miner Performance → Bittensor Rewards

```
1. Miner trades on WAHOO Predict
   ↓
2. WAHOO tracks performance metrics
   (volume, profit, win rate)
   ↓
3. Validator queries WAHOO API
   GET /api/v2/users/validation?hotkeys=...
   ↓
4. WAHOO returns performance data
   {
     "hotkey": "...",
     "performance": {
       "total_volume_usd": 10000,
       "realized_profit_usd": 500,
       ...
     }
   }
   ↓
5. Validator computes weights
   compute_final_weights(validation_data)
   → ranks by volume/profit
   → combines rankings
   → normalizes to sum=1.0
   ↓
6. Validator sets weights on-chain
   subtensor.set_weights(uids, weights)
   ↓
7. Yuma Consensus aggregates weights
   (from all validators)
   ↓
8. TAO emissions distributed
   (proportional to aggregated weights)
   ↓
9. Miner receives TAO rewards
   (based on trading performance)
```

---

## Part 9: Key Differentiators

### What Makes WaHoo Subnet Unique?

1. **No Code for Miners**
   - Most subnets require miners to run code and generate outputs
   - WaHoo miners just trade on an existing platform
   - Low barrier to entry

2. **Real-World Performance Metrics**
   - Rewards based on actual trading performance
   - Not based on code execution or AI model outputs
   - Direct connection between market participation and rewards

3. **External Platform Integration**
   - Leverages existing prediction market infrastructure
   - No need to build trading engine from scratch
   - Focus on reward distribution, not market mechanics

4. **Transparent Scoring**
   - Performance metrics are public (via API)
   - Scoring algorithm is open source
   - Fair and verifiable

5. **Decentralized Rewards, Centralized Trading**
   - Trading happens on centralized platform (WAHOO)
   - Rewards distributed via decentralized network (Bittensor)
   - Best of both worlds

---

## Part 10: Technical Implementation Details

### Key Files & Their Roles

#### `neurons/validator.py`
- Main validator loop
- Integrates with WAHOO API
- Manages metagraph sync
- Sets weights on-chain

#### `neurons/scoring.py`
- Scoring algorithm implementation
- Ranks miners by performance metrics
- Combines rankings into final weights
- Normalizes weights to sum to 1.0

#### `template/protocol.py`
- Defines `WAHOOPredict` synapse
- Communication protocol between validators and miners
- Request/response structure

#### `template/reward.py`
- Reward computation logic
- Combines WAHOO weights with miner responses
- Implements fallback scoring mechanisms
- Normalizes rewards tensor

#### `neurons/validator_db.py`
- Optional SQLite database
- Caches validation data and weights
- Enables operation during API outages
- Auto-cleanup of old data

### Environment Variables

```bash
# WAHOO API Configuration
WAHOO_API_URL=https://api.wahoopredict.com  # Default

# Optional Scoring API (fallback)
API_BASE_URL=http://localhost:8000

# Optional Validator Database
USE_VALIDATOR_DB=true
VALIDATOR_DB_PATH=~/.wahoo/validator.db
```

### Dependencies

- `bittensor>=7.0.0` - Bittensor SDK
- `httpx>=0.25.0` - HTTP client for API calls
- `torch>=2.0.0` - PyTorch (required by Bittensor)
- `python-dotenv>=1.0.0` - Environment variable management

---

## Part 11: Use Cases & Applications

### For Miners (Traders)

1. **Passive Income from Trading**
   - Trade on WAHOO Predict as usual
   - Earn additional TAO rewards based on performance
   - No additional code or infrastructure needed

2. **Performance-Based Rewards**
   - Better traders earn more TAO
   - Incentivizes quality predictions
   - Rewards market participation

3. **Low Barrier to Entry**
   - Just register hotkey and link to WAHOO account
   - No technical knowledge required
   - Start earning immediately

### For Validators

1. **Simple Integration**
   - Just query WAHOO API and set weights
   - No complex evaluation logic needed
   - Performance data is already computed

2. **Reliable Data Source**
   - WAHOO API provides verified performance metrics
   - Less prone to manipulation
   - Transparent and auditable

3. **Optional Caching**
   - Validator DB enables operation during outages
   - Improves reliability
   - Historical data for analysis

### For the Ecosystem

1. **Bridges Traditional Markets to Crypto**
   - Connects prediction markets to blockchain rewards
   - Brings traditional traders into crypto ecosystem
   - Expands Bittensor use cases

2. **Real-World Utility**
   - Rewards based on actual market participation
   - Not just computational tasks
   - Tangible value creation

---

## Part 12: Challenges & Considerations

### Potential Challenges

1. **API Dependency**
   - Validators depend on WAHOO API availability
   - Mitigation: Validator DB caching
   - Fallback scoring mechanisms

2. **Centralization Risk**
   - Trading happens on centralized platform
   - Performance data from single source
   - Mitigation: Multiple validators verify data

3. **Gaming Prevention**
   - Miners might try to game the system
   - Wash trading, manipulation
   - Mitigation: Volume + profit metrics, win rate tracking

4. **Scaling**
   - API rate limits (max 246 hotkeys per request)
   - Batching required for large miner counts
   - Mitigation: Efficient batching, caching

### Best Practices

1. **Validator Reliability**
   - Maintain high uptime
   - Cache data locally
   - Handle API failures gracefully

2. **Fair Scoring**
   - Use multiple metrics (volume, profit, win rate)
   - Normalize weights properly
   - Document scoring algorithm

3. **Security**
   - Protect wallet keys
   - Verify API responses
   - Monitor for suspicious activity

---

## Summary

The **WaHoo Bittensor subnet** creates a unique bridge between the centralized **WAHOO Predict prediction market platform** and the decentralized **Bittensor network**. By rewarding miners based on their real trading performance, the subnet incentivizes quality predictions and market participation while maintaining the simplicity of traditional trading platforms.

### Key Takeaways

1. **WAHOO Predict** is a real-time prediction market platform for events and sports
2. **WaHoo Subnet** rewards miners based on their WAHOO trading performance
3. **Miners** just trade on WAHOO - no code required
4. **Validators** query WAHOO API and set weights on-chain
5. **Scoring** is based on volume, profit, and win rate
6. **Integration** is simple and transparent

### Resources

- **WAHOO Predict Platform**: [wahoopredict.com](https://wahoopredict.com/en/events)
- **WAHOO Documentation**: [wahoopredict.gitbook.io](https://wahoopredict.gitbook.io/wahoopredict-docs/getting-started/what-is-wahoopredict)
- **WAHOO API Docs**: [API for Developers](https://wahoopredict.gitbook.io/wahoopredict-docs/api/api-for-developers)
- **Bittensor Research**: See `BITTENSOR_RESEARCH.md` in this repository

---

*This analysis is based on the WaHoo codebase, WAHOO Predict documentation, and platform exploration. For the most up-to-date information, refer to the official documentation and codebase.*

