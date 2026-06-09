import os
import logging
import eth_account
from eth_account.signers.local import LocalAccount
from dotenv import load_dotenv

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.types import OrderType

logger = logging.getLogger(__name__)

class HyperliquidClient:
    def __init__(self, private_key: str = None, base_url: str = constants.MAINNET_API_URL, vault_address: str = None):
        """
        Initialize the Hyperliquid client.
        
        If private_key is None, it attempts to load from HYPERLIQUID_PRIVATE_KEY environment variable.
        If HYPERLIQUID_ACCOUNT_ADDRESS is set in the environment, it uses that for account state querying
        if it differs from the wallet address (e.g. agent wallets).
        """
        load_dotenv()
        
        self.base_url = base_url
        
        # Resolve private key
        pk = private_key or os.getenv("HYPERLIQUID_PRIVATE_KEY")
        if not pk:
            raise ValueError("Private key must be provided either directly or via HYPERLIQUID_PRIVATE_KEY env var.")
        
        self.account: LocalAccount = eth_account.Account.from_key(pk)
        
        # Resolve address
        self.address = os.getenv("HYPERLIQUID_ACCOUNT_ADDRESS", self.account.address)
        if not self.address:
            self.address = self.account.address
            
        self.vault_address = vault_address
        
        # Initialize Info and Exchange objects (skip_ws=True for REST-only operations)
        self.info = Info(self.base_url, skip_ws=True)
        self.exchange = Exchange(
            self.account, 
            self.base_url, 
            account_address=self.address,
            vault_address=self.vault_address
        )

    # ---------------------------------------------------------
    # Account & Info
    # ---------------------------------------------------------

    def get_perp_positions(self) -> list:
        """Get open perp positions for the account."""
        user_state = self.info.user_state(self.address)
        positions = []
        for position in user_state.get("assetPositions", []):
            positions.append(position["position"])
        return positions

    def get_spot_balances(self) -> list:
        """Get available spot balances."""
        spot_user_state = self.info.spot_user_state(self.address)
        return spot_user_state.get("balances", [])

    def get_open_orders(self) -> list:
        """Get all open orders for the account."""
        return self.info.open_orders(self.address)
        
    def get_order_status(self, oid: int) -> dict:
        """Get the status of an order by its OID."""
        return self.info.query_order_by_oid(self.address, oid)

    # ---------------------------------------------------------
    # Trading Operations
    # ---------------------------------------------------------

    def place_limit_order(
        self, 
        coin: str, 
        is_buy: bool, 
        sz: float, 
        limit_px: float, 
        reduce_only: bool = False,
        tif: str = "Gtc"
    ) -> dict:
        """
        Place a limit order.
        
        :param coin: The coin name (e.g. "ETH", "PURR/USDC", "@8")
        :param is_buy: True for buy/long, False for sell/short
        :param sz: Order size
        :param limit_px: Limit price
        :param reduce_only: Whether the order is reduce only
        :param tif: Time in force, typically "Gtc", "Ioc", or "Alo"
        """
        order_type: OrderType = {"limit": {"tif": tif}}
        return self.exchange.order(
            coin, 
            is_buy, 
            sz, 
            limit_px, 
            order_type=order_type, 
            reduce_only=reduce_only
        )

    def place_market_order(
        self, 
        coin: str, 
        is_buy: bool, 
        sz: float, 
        slippage: float = 0.05
    ) -> dict:
        """
        Place a market order (implemented as an aggressive limit IOC order).
        """
        return self.exchange.market_open(
            coin,
            is_buy,
            sz,
            slippage=slippage
        )

    def cancel_order(self, coin: str, oid: int) -> dict:
        """
        Cancel a specific order.
        """
        return self.exchange.cancel(coin, oid)

    def cancel_all_orders(self) -> dict:
        """
        Cancel all open orders by retrieving them first.
        """
        open_orders = self.get_open_orders()
        if not open_orders:
            return {"status": "ok", "response": {"data": {"statuses": []}}}
            
        cancel_requests = []
        for order in open_orders:
            cancel_requests.append({
                "coin": order["coin"],
                "oid": order["oid"]
            })
            
        return self.exchange.bulk_cancel(cancel_requests)
