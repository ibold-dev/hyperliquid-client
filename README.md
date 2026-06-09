# Hyperliquid Client

A lightweight, customized Python wrapper around the official `hyperliquid-python-sdk` for streamlined authentication, querying accounts, and trading on Hyperliquid (both spot and perps).

## Setup

1. **Install the package locally**
   Using pip, install this wrapper which will automatically link the local SDK dependency:
   ```bash
   pip install -e .
   ```

2. **Configure Environment Variables**
   Copy `.env.example` to `.env` and fill in your private key:
   ```bash
   cp .env.example .env
   ```
   *Note: Ensure your private key is kept safe and never committed. If your trading wallet address differs from the key's native address (e.g., you are using an API agent), you can optionally specify `HYPERLIQUID_ACCOUNT_ADDRESS` in the `.env` file.*

## Quick Start

```python
from hyperliquid_client import HyperliquidClient

# The client automatically loads HYPERLIQUID_PRIVATE_KEY from your .env
client = HyperliquidClient()

# Get Spot Balances
balances = client.get_spot_balances()
print("Spot Balances:", balances)

# Get Open Perp Positions
positions = client.get_perp_positions()
print("Perp Positions:", positions)

# Place a Limit Order
response = client.place_limit_order(
    coin="ETH",
    is_buy=True,
    sz=0.01,
    limit_px=3000
)
print("Limit Order Response:", response)

# Place a Limit Order with attached Take Profit and Stop Loss
grouped_response = client.place_order_with_tpsl(
    coin="ETH",
    is_buy=True,
    sz=0.01,
    limit_px=3000,
    tp_px=3500,
    sl_px=2800
)
print("TP/SL Order Response:", grouped_response)
```

## Features Supported
- **Account Data**: Fetch spot balances, perp positions, open orders, and order status.
- **Trading**: Place limit orders, market orders, cancel orders, cancel all open orders, and advanced TP/SL order groups.
