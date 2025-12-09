<div align="center">

# Wahooτ

</div>

<div align="center">

*We reduce life to a button. Prediction Markets are THE future.*

**Earn TAO rewards by trading on prediction markets. No code required.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## 🎯 What Makes This Special?

Picture this: You're already trading on prediction markets, making calls on whether your favorite team will win or if that political candidate will pull through. Now imagine getting **paid in TAO** just for doing what you're already doing. That's **Wahooτ** – we took the prediction markets you love and added a Bittensor rewards layer on top.

**No coding. No servers. No "wait, what's a Docker container?" moments.** Just trade, perform well, and watch the rewards come in.

### What is Wahooτ? (The Fun Part)

Wahooτ is where the action happens. While your friends are scrolling through stale news articles, you're trading on what people *actually* think is going to happen – in real-time. Politics, sports, economics, you name it. It's like having a front-row seat to the world's collective gut feeling, and you can bet on it.

**Here's what makes it awesome:**
- **Live markets** on literally everything – from "Will it rain tomorrow?" to "Will Bitcoin hit $100k?"
- **Dead simple Yes/No bets** – no complex derivatives, no confusing options
- **Odds that move in real-time** – watch the market react to news as it breaks
- **Trade from anywhere** – just open your browser and go
- **Want to automate?** Full API access for the power users

### How It All Works Together (The Simple Version)

Okay, here's the deal: You don't need to understand blockchain, APIs, or any of that stuff. But if you're the curious type (we like you), here's what happens behind the curtain:

1. **You register** – Link your Bittensor wallet to Wahooτ (seriously, 2 minutes max)
2. **You trade** – Do your thing on Wahooτ like you always do
3. **We track** – Our validators peek at your performance through the Wahooτ API (don't worry, it's all public data)
4. **You get scored** – Based on how much you trade, how much you profit, and how often you're right
5. **You earn TAO** – Rewards hit your wallet based on your actual trading chops

**The formula is simple:** Better trades = More rewards. More trades = More rewards. It's all about your real performance, not some abstract code test.

### Why This Is Actually Different

Let's be real – most Bittensor subnets read like a computer science textbook. You need to know Python, understand neural networks, and probably have a server running 24/7. **We said "nah" to all of that.**

Here's what makes us different:

- ✅ **Literally zero coding** – If you can click "Yes" or "No" on a prediction, you're qualified
- ✅ **Real money, real performance** – We reward actual trading skills, not your ability to write a script
- ✅ **Built on something that works** – Wahooτ is already live and thriving. We just added the rewards layer
- ✅ **Nothing to hide** – Your performance is public, so you can see exactly why you're earning what you're earning

---

## 👥 Start Mining Today (It's Actually Fun!)

### Look, We Made Mining Actually Accessible

Here's the thing: Most Bittensor subnets make you feel like you need a PhD in computer science just to get started. We looked at that and thought, "That's dumb." So we fixed it.

**No code. No servers. No "why is my terminal showing errors?" moments.** Just trade on Wahooτ like you normally would, and watch the TAO rewards show up in your wallet. It's that simple.

If you can make a prediction and click a button, you can mine. Period.

### Get Started in 3 Steps (Seriously, That's It)

#### Step 1: Get Your Bittensor Wallet

You'll need a Bittensor wallet with a hotkey. Never heard of that? Totally fine. The [official Bittensor docs](https://docs.learnbittensor.org/miners) have your back. It's basically like setting up any crypto wallet – follow the steps, and you're golden.

#### Step 2: Register on Our Subnet

Copy this. Paste it. Run it. Done:

```bash
btcli wallet register --netuid 30
```

#### Step 3: Link Everything Together

Pop over to [Wahooτ](https://wahoopredict.com/en/auth/login?tab=register) and create an account. After creating an account, be sure to [verify your email address](https://account.wahoopredict.com/en/settings) as well as [adding your registered Hotkey](https://account.wahoopredict.com/en/settings?tab=bittensor-wallet) to your account. Input yout hotkey as the wallet address and obtain a verification messsage and sign the message with your wallet hotkey using the following btcli command:

```bash
btcli wallet sign --use-hotkey \
--wallet.name REGISTERED_WALLET \
--wallet.hotkey REGISTERED_HOTKEY \
--message "PASTE ENTIRE VERFICATION MESSAGE"
```

After receiving a Signature from `btcli`, input the signature within the appropriate field. Note that the verification message will expire after 5 minutes. OInce your hotkey is linked to your account and said hotkey is registered as a miner, you can start trading to earn Tao!

### Now the Fun Part: Trade and Earn

Alright, here's where it gets good. Once you're set up, **just trade like you always do**:

- Browse events at [Wahooτ](https://wahoopredict.com/en/events) – see what's hot
- Make your calls – Yes or No, that's it
- Watch your positions – manage your trades, see how you're doing

Meanwhile, in the background, we're tracking:
- **Your trading volume** → More activity = more rewards
- **Your profits** → Making money? Get rewarded for it
- **Your accuracy** → Right more often? That's worth something

**The math is simple:** Good trades = Good rewards. Bad trades = Less rewards. It's all tied to your actual performance, not some made-up metric. No code to debug, no servers to restart, no headaches – just trade well and get paid.

#### Step 4 (Optional): Create API keys

Don't want to trade manually? Not a problem. The Wahooτ API provides live data on open markets as well as the ability to place trades. We'll leave this up to you to configure your own strategy or train a model based on the available data. Simply [generate an API key](https://account.wahoopredict.com/en/settings?tab=api-key-management) and keep your secret safe (this is used as your Authorization token in requests). 

For more information about the available endpoints, please refer to Wahooτ's [official API documentation](https://wahoopredict.gitbook.io/wahoopredict-docs/api/api-for-developers).

---

## 🛡️ Running a Validator? You're Our Hero

Validators are the unsung heroes here. You're the ones making sure the best traders actually get rewarded for their skills. You pull real trading data from Wahooτ, evaluate everyone's performance, and make sure TAO rewards go to the right people. It's important work, and we appreciate you.

### Getting Started (The Quick Version)

Same drill as miners, but you're a validator:

```bash
btcli wallet register --netuid 30
```

Make sure you've got the standard Bittensor validator requirements covered (stake weight, validator permit, all that jazz) and you're ready to roll.

### Validator Flow

The validator runs a continuous loop that:

1. **Syncs metagraph** – Gets current network state (active UIDs, hotkeys, axons)
2. **Fetches Wahooτ data** – Pulls trading stats from Wahooτ API for all registered traders
3. **Queries traders** – Requests predictions from active traders on the subnet
4. **Calculates rewards** – Scores traders using EMA-based scoring (volume, profit, win rate)
5. **Sets weights** – Posts weights to blockchain to distribute TAO rewards

The loop interval is automatically calculated from the metagraph tempo, ensuring perfect synchronization with the network.

### How We Score Everyone (Keeping It Fair)

We keep the scoring simple and transparent. Every miner gets evaluated on three things:

- **Total Volume (USD)** – Are they actually trading, or just sitting there?
- **Realized Profit (USD)** – Are they making money or losing it?
- **Win Rate** – Are their predictions actually good, or are they just guessing?

| Variable | Description | Default |
|----------|-------------|---------|
| `WALLET_NAME` | Bittensor wallet name (coldkey) | **Required** |
| `HOTKEY_NAME` | Bittensor hotkey name | **Required** |
| `NETUID` | Subnet UID | **Required** |
| `NETWORK` | Bittensor network (`finney` or `test`) | `finney` |
| `USE_VALIDATOR_DB` | Enable database caching and EMA score persistence | `false` |
| `VALIDATOR_DB_PATH` | Database file path (each validator gets their own) | `validator.db` |
| `CHAIN_ENDPOINT` | Custom chain endpoint URL | None (advanced use only) |
| `LOG_LEVEL` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

**Important Notes:**
- **API endpoints are hardcoded** in the validator code (not configurable)
  - Wahooτ API: `https://api.wahoopredict.com`
  - Validation endpoint: `https://api.wahoopredict.com/api/v2/event/bittensor/statistics`
- **Loop interval is automatically calculated** from metagraph tempo (synced with network)
  - Calculated as: `tempo * block_time * 1.1` (with 10% buffer)
  - Recalculates each iteration in case tempo changes
  - Falls back to 100 seconds if tempo unavailable
- **Database auto-initializes** at validator start (schema created automatically)
  - Each validator gets their own database file
  - Set `VALIDATOR_DB_PATH` to use a custom location
  - Database uses SQLite (synchronous, local file)

### Installation & Setup

**Simple 3-step setup:**
1. Clone repo and install with UV
2. Set your wallet keys
3. Start validator

That's it!

#### Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **Unix/Linux system** (macOS or Linux)
- **SQLite 3** (usually pre-installed)
- **Virtual environment** (recommended: `uv` , `venv`, or `virtualenv`)

#### Installation Options

**Option 1: Using `uv` (Recommended - Fastest)**

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repository-url>
cd wahoonet

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On macOS/Linux
uv pip install -e .  # Install production dependencies
```

**Option 2: Using `pip` (Traditional)**

```bash
# Clone the repository
git clone <repository-url>
cd wahoonet

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install the package
pip install -e .  # Install production dependencies
```

#### Step 2: Set Up Your Wallet Keys

**You need a Bittensor wallet with coldkey and hotkey:**

1. **Create wallet (if needed):**
   ```bash
   btcli wallet new_coldkey --wallet.name <your_wallet_name>
   btcli wallet new_hotkey --wallet.name <your_wallet_name> --wallet.hotkey <your_hotkey_name>
   ```

2. **Register on the subnet:**
   ```bash
   btcli wallet register --netuid <your_subnet_uid> --wallet.name <your_wallet_name> --wallet.hotkey <your_hotkey_name>
   ```

3. **Set environment variables:**
   ```bash
   export WALLET_NAME=<your_wallet_name>
   export HOTKEY_NAME=<your_hotkey_name>
   export NETUID=<your_subnet_uid>
   export NETWORK=finney  # or "test" for testnet
   ```

**Keys are stored in `~/.bittensor/wallets/`** - the validator loads them automatically.

#### Environment Configuration

**Required Environment Variables:**

```bash
# Set these in your shell or .env file
export WALLET_NAME=your_wallet_name
export HOTKEY_NAME=your_hotkey_name
export NETUID=your_subnet_uid  # The subnet you're validating on

# Network selection (default: finney/mainnet)
export NETWORK=finney  # For mainnet (production)
# OR
export NETWORK=test    # For testnet (testing)
```

**Optional Environment Variables:**

```bash
# Database configuration
export USE_VALIDATOR_DB=true  # Enable database caching and EMA score persistence (recommended)
export VALIDATOR_DB_PATH=/path/to/validator.db  # Custom database path (each validator gets their own)

# Logging
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, or ERROR

# Note: Loop interval is automatically calculated from metagraph tempo
# Note: API endpoints are hardcoded in the validator code
```

**Create a `.env` file** (optional, for convenience):

```bash
# .env file
WALLET_NAME=your_wallet_name
HOTKEY_NAME=your_hotkey_name
NETUID=your_subnet_uid
NETWORK=finney
USE_VALIDATOR_DB=true
VALIDATOR_DB_PATH=validator.db  # Optional: custom path (each validator gets their own)
LOG_LEVEL=INFO

# Note: Loop interval is auto-calculated from metagraph tempo
# Note: API endpoints are hardcoded (not configurable)
```

#### Step 3: Initialize (Optional)

The validator will auto-initialize on first run, but you can manually initialize:

```bash
python -m wahoo.validator.init
```

This sets up the database schema. The validator will auto-initialize if needed.

#### Step 4: Start the Validator

**That's it! Just run:**

```bash
# Make sure virtual environment is activated
source .venv/bin/activate  # or: source venv/bin/activate

# Start the validator as a background processs
nohup python -m wahoo.entrypoints.validator > wahoo-validator.log 2>&1 &
```

**Or with explicit arguments:**
```bash
nohup python -m wahoo.entrypoints.validator \
  --wallet.name your_wallet_name \
  --wallet.hotkey your_hotkey_name \
  --netuid your_subnet_uid \
  --network finney \
  > wahoo-validator.log 2>&1 &
```

If you want to use pm2 instead of nohup, then please use the following format:

```bash
pm2 start python2 --name wahoo-validator -- -m wahoo.entrypoints.validator
```

The validator will:
- ✅ Auto-initialize database on first run (if needed)
- ✅ Sync with metagraph automatically
- ✅ Calculate loop interval from metagraph tempo
- ✅ Start the main validation loop

**What happens when you start:**

1. ✅ **Auto-initializes database** - Creates schema if database doesn't exist (each validator gets their own database file)
2. ✅ **Loads your wallet** from `~/.bittensor/wallets/` using the provided wallet/hotkey names
3. ✅ **Connects to Bittensor network** (mainnet `finney` or `test` testnet)
4. ✅ **Syncs metagraph** to get current network state (UIDs, hotkeys, axons)
5. ✅ **Calculates loop interval** from metagraph tempo (automatically synced with network)
6. ✅ **Initializes ValidatorDB** (if `USE_VALIDATOR_DB=true`) for caching and EMA score persistence
7. ✅ **Enters main loop** - continuously:
   - Syncs metagraph each iteration
   - Fetches trading data from Wahooτ API for all registered traders
   - Caches validation data in database (if enabled)
   - Queries traders for predictions
   - Calculates rewards using EMA-based scoring
   - Persists EMA scores to database (if enabled)
   - Sets weights on blockchain

**Network Selection:**

- **Mainnet (Production)**: Use `--network finney` or `export NETWORK=finney`
  - Connects to: `wss://entrypoint-finney.opentensor.ai:443`
  - Real TAO rewards
  - See [Bittensor Networks](https://docs.learnbittensor.org/concepts/bittensor-networks) for details

- **Testnet (Testing)**: Use `--network test` or `export NETWORK=test`
  - Connects to: `wss://test.finney.opentensor.ai:443`
  - Test TAO (no real value)
  - Safe for testing

**Important Prerequisites:**
- ✅ Bittensor wallet created (`btcli wallet new_coldkey` and `btcli wallet new_hotkey`)
- ✅ Validator registered on the subnet (`btcli wallet register --netuid 30`)
- ✅ `WALLET_NAME` and `HOTKEY_NAME` set (via environment variables or CLI arguments)
- ✅ `NETUID` set to your subnet UID

#### Troubleshooting

**Issue: Dependencies fail to install**

- Make sure you're in a virtual environment
- Try running with elevated privileges: `sudo wahoo-validator-init`
- Or manually install: `pip install -r requirements.txt` or `uv pip install -e .`

#### Configuration

The validator requires the following environment variables or CLI arguments:

**Required:**
- `WALLET_NAME` - Your Bittensor wallet name (coldkey)
- `HOTKEY_NAME` - Your Bittensor hotkey name
- `NETUID` - The subnet UID you're validating on

**Optional:**
- `NETWORK` - Bittensor network (`finney` for mainnet, `test` for testnet). Default: `finney`
- `USE_VALIDATOR_DB` - Enable database caching and EMA score persistence (`true`/`false`). Default: `false`
- `VALIDATOR_DB_PATH` - Path to validator database (each validator gets their own). Default: `validator.db`
- `LOG_LEVEL` - Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default: `INFO`
- `CHAIN_ENDPOINT` - Custom chain endpoint URL (advanced use only)

**Note:** Loop interval is automatically calculated from metagraph tempo (not configurable). API endpoints are hardcoded in the validator code (not configurable).

**Issue: Database errors**

- Check that SQLite is installed: `sqlite3 --version`
- Verify database path permissions
- Try deleting the database file and re-running initialization

**Issue: Import errors**

- Ensure the package is installed in editable mode: `pip install -e .` or `uv pip install -e .`
- Verify your virtual environment is activated
- Check that all dependencies are installed: `pip list` or `uv pip list`

**Issue: Alembic migration errors**

- Ensure you're running from the project root directory
- Check that `wahoo/validator/database/alembic.ini` exists
- Try manually running: `cd wahoo/validator/database && alembic upgrade head`

#### Metagraph Syncing

The validator automatically syncs with the Bittensor metagraph to stay current with network state:

- **Initial sync**: Happens when validator starts (in `initialize_bittensor()`)
- **Per-iteration sync**: Happens at the start of each main loop iteration
- **What gets synced**: UIDs, hotkeys, axons, stake, tempo, and other network state

This ensures the validator always has the latest network information before:
- Querying traders
- Calculating rewards
- Setting weights on blockchain

The metagraph sync uses the Bittensor SDK's built-in syncing mechanism, which connects to the appropriate network endpoint based on your `NETWORK` setting (`finney` for mainnet, `test` for testnet).

#### Database

The validator uses SQLite for local data persistence:

- **Auto-initialization**: Database and schema are created automatically on first run
- **Per-validator**: Each validator gets their own database file (set `VALIDATOR_DB_PATH` for custom location)
- **Synchronous**: Uses `sqlite3` (standard library, blocking operations - no async)
- **Features**:
  - Caches validation data from Wahooτ API (reduces API calls)
  - Stores EMA scores for persistence across restarts
  - Automatic cleanup of old cache entries (7 days default)
  - WAL mode enabled for better write concurrency

**Database Location:**
- Default: `validator.db` in project root
- Custom: Set `VALIDATOR_DB_PATH` environment variable
- Example: `export VALIDATOR_DB_PATH=/home/validator/my_validator.db`

#### Development Setup

For development work, install with dev dependencies:

```bash
# With uv
uv pip install -e ".[dev]"

# With pip
pip install -e ".[dev]"
```

---

## 📚 Need More Info? We've Got You Covered

Got questions? Want to dive deeper? Here's where to go:

- **Ready to trade?** Head to [wahoopredict.com](https://wahoopredict.com/en/events) and see what's happening
- **Want to understand Wahooτ better?** The [Wahooτ docs](https://wahoopredict.gitbook.io/wahoopredict-docs/getting-started/what-is-wahoopredict) will fill you in
- **Bittensor Networks**: Learn about mainnet, testnet, and network endpoints at [Bittensor Networks Documentation](https://docs.learnbittensor.org/concepts/bittensor-networks)
- **Bittensor CLI**: Full reference at [BTCLI Documentation](https://docs.learnbittensor.org/btcli/btcli)
- **New to Bittensor?** The [official Bittensor docs](https://docs.bittensor.com) are your friend

Still have questions? That's cool. We're here to help make this as simple as possible. Assistance will be provided via our subnet channel on the [official Bittensor Discord](https://discord.gg/bittensor)

---

## 📄 License

MIT License - see LICENSE file for details.

---