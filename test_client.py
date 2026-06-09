import os
import eth_account
from hyperliquid_client.client import HyperliquidClient
from hyperliquid.utils.constants import TESTNET_API_URL

def run_test():
    # We will generate a random private key for testnet testing
    # DO NOT do this for mainnet!
    print("Generating a temporary testnet wallet...")
    acct = eth_account.Account.create()
    
    print(f"Address: {acct.address}")
    
    client = HyperliquidClient(
        private_key=acct.key.hex(),
        base_url=TESTNET_API_URL
    )
    
    print("\n--- Getting Balances ---")
    spot_bals = client.get_spot_balances()
    print(f"Spot balances: {spot_bals}")
    
    perp_pos = client.get_perp_positions()
    print(f"Perp positions: {perp_pos}")
    
    print("\n--- Testing Open Orders Retrieval ---")
    open_orders = client.get_open_orders()
    print(f"Open Orders: {open_orders}")
    
    print("\nAll read-only methods passed. Since this wallet has no funds, we cannot test order placement effectively without an error, but the client is initialized successfully!")

if __name__ == "__main__":
    run_test()
