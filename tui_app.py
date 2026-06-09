import os
import argparse
import asyncio
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, DataTable, Button, Input, Select, RichLog, Label
from textual.containers import Vertical, Horizontal

from hyperliquid_client import HyperliquidClient
from hyperliquid.utils.constants import TESTNET_API_URL, MAINNET_API_URL

class DashboardTab(Vertical):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("Refresh Balances", id="refresh_balances", variant="primary"),
            Button("Refresh Positions", id="refresh_positions", variant="primary"),
            classes="buttons-bar"
        )
        yield Label("Spot Balances", classes="section-title")
        yield DataTable(id="spot_table")
        yield Label("Perp Positions", classes="section-title")
        yield DataTable(id="perp_table")

class OpenOrdersTab(Vertical):
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("Refresh Orders", id="refresh_orders", variant="primary"),
            Button("Cancel All", id="cancel_all_orders", variant="error"),
            classes="buttons-bar"
        )
        yield Label("💡 Click/Enter on a row below to cancel that specific order", classes="section-title")
        yield DataTable(id="orders_table", cursor_type="row")

class TradeTab(Vertical):
    def compose(self) -> ComposeResult:
        yield Input(placeholder="Coin (e.g. ETH, PURR/USDC)", id="trade_coin")
        yield Horizontal(
            Select(
                options=[("Limit", "limit"), ("Market", "market"), ("Stop Loss", "sl"), ("Take Profit", "tp")],
                prompt="Order Type",
                value="limit",
                id="trade_order_type"
            ),
            Select(
                options=[("Buy/Long", True), ("Sell/Short", False)],
                prompt="Side",
                id="trade_side"
            )
        )
        yield Input(placeholder="Size (e.g. 0.01)", id="trade_size", type="number")
        yield Input(placeholder="Price / Trigger Price (Leave blank for Market)", id="trade_limit_px", type="number")
        yield Input(placeholder="Attach Take Profit (Optional, Limit orders only)", id="trade_tp", type="number")
        yield Input(placeholder="Attach Stop Loss (Optional, Limit orders only)", id="trade_sl", type="number")
        yield Button("Execute Order", id="execute_order", variant="success")

class HyperliquidTUI(App):
    CSS = """
    .buttons-bar {
        height: auto;
        margin: 1;
    }
    .buttons-bar Button {
        margin-right: 1;
    }
    .section-title {
        text-style: bold;
        padding: 1;
        background: $primary-background;
    }
    DataTable {
        height: 1fr;
    }
    Input {
        margin: 1 0;
    }
    Select {
        margin: 1 0;
    }
    RichLog {
        height: 10;
        border-top: solid $primary;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_all", "Refresh All"),
    ]

    def __init__(self, network: str):
        super().__init__()
        self.network = network
        base_url = MAINNET_API_URL if network == "mainnet" else TESTNET_API_URL
        self.client = HyperliquidClient(base_url=base_url)

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Dashboard", id="tab-dashboard"):
                yield DashboardTab()
            with TabPane("Open Orders", id="tab-orders"):
                yield OpenOrdersTab()
            with TabPane("Trade", id="tab-trade"):
                yield TradeTab()
        
        yield RichLog(id="log_panel", highlight=True, markup=True)
        yield Footer()
        
    def on_mount(self) -> None:
        self.title = f"Hyperliquid Client - {self.network.upper()} ({self.client.address})"
        
        # Setup tables
        spot_table = self.query_one("#spot_table", DataTable)
        spot_table.add_columns("Coin", "Total", "Available")
        
        perp_table = self.query_one("#perp_table", DataTable)
        perp_table.add_columns("Coin", "Size", "Entry Price", "Liq Price", "Margin Used", "Unrealized PNL")
        
        orders_table = self.query_one("#orders_table", DataTable)
        orders_table.add_columns("OID", "Coin", "Side", "Size", "Limit Px", "Reduce Only")
        
        self.log_msg(f"Connected to {self.network.upper()} at {self.client.base_url}")
        self.refresh_all()

    def log_msg(self, message: str) -> None:
        log_panel = self.query_one("#log_panel", RichLog)
        log_panel.write(message)
        
    def refresh_all(self):
        self.refresh_balances()
        self.refresh_positions()
        self.refresh_orders()

    def action_refresh_all(self):
        self.refresh_all()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh_balances":
            self.refresh_balances()
        elif event.button.id == "refresh_positions":
            self.refresh_positions()
        elif event.button.id == "refresh_orders":
            self.refresh_orders()
        elif event.button.id == "cancel_all_orders":
            self.cancel_all_orders()
        elif event.button.id == "execute_order":
            self.execute_order()
            
    def refresh_balances(self):
        self.log_msg("Fetching Spot Balances...")
        self.run_worker(self._fetch_balances(), exclusive=True)
        
    async def _fetch_balances(self):
        try:
            balances = await asyncio.to_thread(self.client.get_spot_balances)
            table = self.query_one("#spot_table", DataTable)
            table.clear()
            for b in balances:
                table.add_row(b.get("coin"), b.get("total"), b.get("holdable"))
            self.log_msg("[green]Balances updated.[/green]")
        except Exception as e:
            self.log_msg(f"[red]Error fetching balances: {e}[/red]")

    def refresh_positions(self):
        self.log_msg("Fetching Perp Positions...")
        self.run_worker(self._fetch_positions(), exclusive=True)
        
    async def _fetch_positions(self):
        try:
            positions = await asyncio.to_thread(self.client.get_perp_positions)
            table = self.query_one("#perp_table", DataTable)
            table.clear()
            for p in positions:
                table.add_row(
                    p.get("coin"), 
                    p.get("szi"), 
                    p.get("entryPx"), 
                    p.get("liquidationPx", "N/A"),
                    p.get("marginUsed"),
                    p.get("unrealizedPnl")
                )
            self.log_msg("[green]Positions updated.[/green]")
        except Exception as e:
            self.log_msg(f"[red]Error fetching positions: {e}[/red]")

    def refresh_orders(self):
        self.log_msg("Fetching Open Orders...")
        self.run_worker(self._fetch_orders(), exclusive=True)
        
    async def _fetch_orders(self):
        try:
            orders = await asyncio.to_thread(self.client.get_open_orders)
            table = self.query_one("#orders_table", DataTable)
            table.clear()
            for o in orders:
                table.add_row(
                    str(o.get("oid")),
                    o.get("coin"),
                    o.get("side"),
                    o.get("sz"),
                    o.get("limitPx"),
                    str(o.get("reduceOnly", False))
                )
            self.log_msg("[green]Orders updated.[/green]")
        except Exception as e:
            self.log_msg(f"[red]Error fetching orders: {e}[/red]")

    def cancel_all_orders(self):
        self.log_msg("Canceling all open orders...")
        self.run_worker(self._cancel_all(), exclusive=True)
        
    async def _cancel_all(self):
        try:
            res = await asyncio.to_thread(self.client.cancel_all_orders)
            self.log_msg(f"[yellow]Cancel All Response:[/yellow] {res}")
            self.refresh_orders()
        except Exception as e:
            self.log_msg(f"[red]Error canceling orders: {e}[/red]")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "orders_table":
            row_data = event.data_table.get_row(event.row_key)
            oid = int(row_data[0])
            coin = row_data[1]
            self.log_msg(f"Canceling order {oid} for {coin}...")
            self.run_worker(self._cancel_single_order(coin, oid), exclusive=True)

    async def _cancel_single_order(self, coin: str, oid: int):
        try:
            res = await asyncio.to_thread(self.client.cancel_order, coin, oid)
            self.log_msg(f"[yellow]Cancel Response:[/yellow] {res}")
            self.refresh_orders()
        except Exception as e:
            self.log_msg(f"[red]Error canceling order: {e}[/red]")

    def execute_order(self):
        coin = self.query_one("#trade_coin", Input).value
        is_buy_val = self.query_one("#trade_side", Select).value
        order_type_val = self.query_one("#trade_order_type", Select).value
        size_str = self.query_one("#trade_size", Input).value
        limit_px_str = self.query_one("#trade_limit_px", Input).value
        tp_str = self.query_one("#trade_tp", Input).value
        sl_str = self.query_one("#trade_sl", Input).value
        
        if not coin or is_buy_val == Select.BLANK or not size_str:
            self.log_msg("[red]Please fill in all required fields (Coin, Side, Size)[/red]")
            return
            
        try:
            is_buy = bool(is_buy_val)
            sz = float(size_str)
            limit_px = float(limit_px_str) if limit_px_str else None
            tp_px = float(tp_str) if tp_str else None
            sl_px = float(sl_str) if sl_str else None
            
            self.log_msg(f"Executing {order_type_val} order for {coin}...")
            self.run_worker(self._execute_order(coin, is_buy, order_type_val, sz, limit_px, tp_px, sl_px), exclusive=True)
        except Exception as e:
            self.log_msg(f"[red]Invalid input: {e}[/red]")
            
    async def _execute_order(self, coin, is_buy, order_type, sz, limit_px, tp_px, sl_px):
        try:
            if order_type == "market":
                res = await asyncio.to_thread(self.client.place_market_order, coin, is_buy, sz)
            elif order_type in ["sl", "tp"]:
                if limit_px is None:
                    self.log_msg("[red]Trigger Price is required for Stop Loss / Take Profit orders[/red]")
                    return
                is_tp = (order_type == "tp")
                res = await asyncio.to_thread(self.client.place_stop_order, coin, is_buy, sz, limit_px, True, is_tp)
            else: # limit
                if limit_px is None:
                    self.log_msg("[red]Limit Price is required for Limit orders[/red]")
                    return
                if tp_px or sl_px:
                    res = await asyncio.to_thread(self.client.place_order_with_tpsl, coin, is_buy, sz, limit_px, tp_px, sl_px)
                else:
                    res = await asyncio.to_thread(self.client.place_limit_order, coin, is_buy, sz, limit_px)
            
            self.log_msg(f"[green]Order Executed:[/green] {res}")
            self.refresh_orders()
        except Exception as e:
            self.log_msg(f"[red]Error executing order: {e}[/red]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperliquid Client TUI")
    parser.add_argument("--network", choices=["mainnet", "testnet"], default="mainnet", help="Network to connect to (default: mainnet)")
    args = parser.parse_args()
    
    app = HyperliquidTUI(network=args.network)
    app.run()
