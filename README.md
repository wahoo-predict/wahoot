<div align="center">

# WaHoo Predict

</div>

<div align="center">

*We reduce life to a button. Prediction Markets are THE future.*

**Earn TAO rewards by trading on prediction markets. No code required.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

</div>

---

## 🎯 What Makes This Special?

Picture this: You're already trading on prediction markets, making calls on whether your favorite team will win or if that political candidate will pull through. Now imagine getting **paid in TAO** just for doing what you're already doing. That's **WaHoo Predict** – we took the prediction markets you love and added a Bittensor rewards layer on top.

**No coding. No servers. No "wait, what's a Docker container?" moments.** Just trade, perform well, and watch the rewards come in.

### What is WAHOO Predict? (The Fun Part)

WAHOO Predict is where the action happens. While your friends are scrolling through stale news articles, you're trading on what people *actually* think is going to happen – in real-time. Politics, sports, economics, you name it. It's like having a front-row seat to the world's collective gut feeling, and you can bet on it.

**Here's what makes it awesome:**
- **Live markets** on literally everything – from "Will it rain tomorrow?" to "Will Bitcoin hit $100k?"
- **Dead simple Yes/No bets** – no complex derivatives, no confusing options
- **Odds that move in real-time** – watch the market react to news as it breaks
- **Trade from anywhere** – just open your browser and go
- **Want to automate?** Full API access for the power users

### How It All Works Together (The Simple Version)

Okay, here's the deal: You don't need to understand blockchain, APIs, or any of that stuff. But if you're the curious type (we like you), here's what happens behind the curtain:

1. **You register** – Link your Bittensor wallet to WAHOO (seriously, 2 minutes max)
2. **You trade** – Do your thing on WAHOO Predict like you always do
3. **We track** – Our validators peek at your performance through the WAHOO API (don't worry, it's all public data)
4. **You get scored** – Based on how much you trade, how much you profit, and how often you're right
5. **You earn TAO** – Rewards hit your wallet based on your actual trading chops

**The formula is simple:** Better trades = More rewards. More trades = More rewards. It's all about your real performance, not some abstract code test.

### Why This Is Actually Different

Let's be real – most Bittensor subnets read like a computer science textbook. You need to know Python, understand neural networks, and probably have a server running 24/7. **We said "nah" to all of that.**

Here's what makes us different:

- ✅ **Literally zero coding** – If you can click "Yes" or "No" on a prediction, you're qualified
- ✅ **Real money, real performance** – We reward actual trading skills, not your ability to write a script
- ✅ **Built on something that works** – WAHOO Predict is already live and thriving. We just added the rewards layer
- ✅ **Nothing to hide** – Your performance is public, so you can see exactly why you're earning what you're earning

---

## 👥 Start Mining Today (It's Actually Fun!)

### Look, We Made Mining Actually Accessible

Here's the thing: Most Bittensor subnets make you feel like you need a PhD in computer science just to get started. We looked at that and thought, "That's dumb." So we fixed it.

**No code. No servers. No "why is my terminal showing errors?" moments.** Just trade on WAHOO Predict like you normally would, and watch the TAO rewards show up in your wallet. It's that simple.

If you can make a prediction and click a button, you can mine. Period.

### Get Started in 3 Steps (Seriously, That's It)

#### Step 1: Get Your Bittensor Wallet

You'll need a Bittensor wallet with a hotkey. Never heard of that? Totally fine. The [official Bittensor docs](https://docs.learnbittensor.org/miners) have your back. It's basically like setting up any crypto wallet – follow the steps, and you're golden.

#### Step 2: Register on Our Subnet

Copy this. Paste it. Run it. Done:

```bash
btcli wallet register --netuid <netuid>
```

That's literally it. You're now a miner. Told you it was easy.

#### Step 3: Link Everything Together

Pop over to [wahoopredict.com/miners](https://wahoopredict.com/miners) and fill out the form. Takes 30 seconds. We do all the crypto verification magic behind the scenes – you just click "Submit" and move on with your life.

### Now the Fun Part: Trade and Earn

Alright, here's where it gets good. Once you're set up, **just trade like you always do**:

- Browse events at [wahoopredict.com/en/events](https://wahoopredict.com/en/events) – see what's hot
- Make your calls – Yes or No, that's it
- Watch your positions – manage your trades, see how you're doing

Meanwhile, in the background, we're tracking:
- **Your trading volume** → More activity = more rewards
- **Your profits** → Making money? Get rewarded for it
- **Your accuracy** → Right more often? That's worth something

**The math is simple:** Good trades = Good rewards. Bad trades = Less rewards. It's all tied to your actual performance, not some made-up metric. No code to debug, no servers to restart, no headaches – just trade well and get paid.

---

## 🛡️ Running a Validator? You're Our Hero

Validators are the unsung heroes here. You're the ones making sure the best traders actually get rewarded for their skills. You pull real trading data from WAHOO Predict, evaluate everyone's performance, and make sure TAO rewards go to the right people. It's important work, and we appreciate you.

### Getting Started (The Quick Version)

Same drill as miners, but you're a validator:

```bash
btcli wallet register --netuid <netuid>
```

Make sure you've got the standard Bittensor validator requirements covered (stake weight, validator permit, all that jazz) and you're ready to roll.

### What Your Validator Does (The Automated Part)

Your validator runs a loop that basically does all the heavy lifting:

1. **Stays in sync** – Keeps up with what's happening on the blockchain
2. **Grabs the data** – Pulls real trading stats from the WAHOO API for all the miners
3. **Does the math** – Ranks everyone by how well they're actually trading (volume, profit, win rate) and figures out the weights
4. **Distributes the rewards** – Posts those weights to the blockchain so TAO emissions go to the right people

The best part? It's all automated. Set it up, let it run, check on it occasionally. It's not going to demand your attention 24/7.

### How We Score Everyone (Keeping It Fair)

We keep the scoring simple and transparent. Every miner gets evaluated on three things:

- **Total Volume (USD)** – Are they actually trading, or just sitting there?
- **Realized Profit (USD)** – Are they making money or losing it?
- **Win Rate** – Are their predictions actually good, or are they just guessing?

| Variable | Description | Default |
|----------|-------------|---------|
| `API_BASE_URL` | Scoring API base URL | `http://localhost:8000` |
| `WAHOO_API_URL` | WAHOO API base URL | `https://api.wahoopredict.com` |
| `WAHOO_VALIDATION_ENDPOINT` | Full validation endpoint used by validators (overrides default statistics URL) | `https://api.wahoopredict.com/api/v2/event/bittensor/statistics` |
| `USE_VALIDATOR_DB` | Enable SQLite backup | `false` |
| `VALIDATOR_DB_PATH` | Custom database path | `~/.wahoo/validator.db` |

### Validator Setup & Installation

Ready to run a validator? Here's everything you need to get started.

#### Prerequisites

- **Python 3.10+** (3.11 or 3.12 recommended)
- **Unix/Linux system** (macOS or Linux)
- **SQLite 3** (usually pre-installed)
- **Virtual environment** (recommended: `venv`, `virtualenv`, or `uv`)

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
uv pip install -e ".[dev]"  # Install with dev dependencies
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
pip install -e ".[dev]"  # Install with dev dependencies
```

#### Environment Configuration

1. **Create a `.env` file** in the project root (optional):

```bash
# Database path (optional, defaults to validator.db in project root)
VALIDATOR_DB_PATH=/path/to/your/validator.db

# Add other environment variables as needed
```

2. **Set up your Bittensor wallet** (if not already done):

```bash
btcli wallet new_coldkey
btcli wallet new_hotkey --wallet.name <your_wallet>
```

#### Initialization

Before running the validator, you need to initialize the environment and database:

```bash
# Run the initialization script
wahoo-validator-init

# Or run it directly with Python
python -m wahoo.validator.init
```

The initialization script will:
- ✅ Check and install missing dependencies (automatically uses `uv` if available, falls back to `pip`)
- ✅ Verify SQLite is available
- ✅ Create and initialize the database if it doesn't exist
- ✅ Run Alembic migrations to ensure database schema is up to date
- ✅ Load configuration from `.env` file

**Initialization Options:**

```bash
# Skip dependency checking (if you've already installed everything)
wahoo-validator-init --skip-deps

# Skip database initialization (if database already exists)
wahoo-validator-init --skip-db

# Specify custom database path
wahoo-validator-init --db-path /custom/path/to/database.db
```

#### Starting the Validator

Once initialization is complete, you can start the validator:

```bash
# Activate your virtual environment (if not already active)
source venv/bin/activate  # or: source .venv/bin/activate for uv

# Run the validator
python -m wahoo.validator.validator
# Or use your preferred method to run the validator script
```

**Note:** Make sure you've registered your validator on the subnet first:

```bash
btcli wallet register --netuid <netuid>
```

#### Troubleshooting

**Issue: Dependencies fail to install**

- Make sure you're in a virtual environment
- Try running with elevated privileges: `sudo wahoo-validator-init`
- Or manually install: `pip install -r requirements.txt` or `uv pip install -e .`

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
- **Want to understand WAHOO better?** The [WAHOO docs](https://wahoopredict.gitbook.io/wahoopredict-docs/getting-started/what-is-wahoopredict) will fill you in
- **New to Bittensor?** The [official Bittensor docs](https://docs.bittensor.com) are your friend

Still have questions? That's cool. We're here to help make this as simple as possible.

---

## 📄 License

MIT License - see LICENSE file for details. TL;DR: Use it, build on it, make it better.

---

<div align="center">


</div>