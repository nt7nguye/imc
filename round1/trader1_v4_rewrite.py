from copy import deepcopy
from dataclasses import dataclass
import pdb
from re import I
from datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    ProsperityEncoder,
    Symbol,
    Trade,
    TradingState,
)
from typing import List, Any, Optional, Tuple
import string
import jsonpickle
import json
import numpy as np
import math


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(
        self,
        state: TradingState,
        orders: dict[Symbol, list[Order]],
        conversions: int,
        trader_data: str,
    ) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(
                        state, self.truncate(state.traderData, max_item_length)
                    ),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(
        self, order_depths: dict[Symbol, OrderDepth]
    ) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()


@dataclass
class Microstructure:
    best_ask: Optional[int] = None
    best_bid: Optional[int] = None

    filtered_best_ask: Optional[int] = None
    filtered_best_bid: Optional[int] = None

    fair_value: Optional[float] = (
        None  # Fair value can be None if there's no order book or order book is empty
    )
    spread: Optional[float] = None
    filtered_spread: Optional[float] = None


class Product:
    RAINFOREST_RESIN = "RAINFOREST_RESIN"
    KELP = "KELP"
    SQUID_INK = "SQUID_INK"


class Trader:
    def __init__(self, params=None):
        if params is None:
            params = {
                Product.RAINFOREST_RESIN: {
                    "forced_fair_value": 10000,
                    "take_width": 0.5,  # its good to take 10000
                    "min_volume": 10,
                },
                Product.KELP: {
                    "take_width": 1,
                    "min_volume": 20,
                },
                Product.SQUID_INK: {
                    "take_width": 1,
                    "min_volume": 20,
                },
            }
        self.params = params

        # self.LIMIT = {
        #     Product.RAINFOREST_RESIN: 50,
        #     Product.KELP: 50,
        #     Product.SQUID_INK: 50,
        # }
        self.logs = {
            Product.RAINFOREST_RESIN: [],
            Product.KELP: [],
            Product.SQUID_INK: [],
        }

    def log(self, product: Product, message: str):
        self.logs[product].append(message)

    def _min(self, value: Optional[int], default: int) -> int:
        return min(value, default) if value is not None else default

    def _max(self, value: Optional[int], default: int) -> int:
        return max(value, default) if value is not None else default

    def _get_microstructure(
        self,
        order_depth: OrderDepth,
        forced_min_volume: int = 0,
        forced_fair_value: Optional[float] = None,
    ) -> Microstructure:
        # Filter volume less than min_volume to avoid noise
        structure = Microstructure()

        for price, volume in order_depth.buy_orders.items():
            structure.best_bid = self._max(structure.best_bid, price)
            if abs(volume) >= forced_min_volume:
                structure.filtered_best_bid = self._max(
                    structure.filtered_best_bid, price
                )
        for price, volume in order_depth.sell_orders.items():
            structure.best_ask = self._min(structure.best_ask, price)
            if abs(volume) >= forced_min_volume:
                structure.filtered_best_ask = self._min(
                    structure.filtered_best_ask, price
                )

        if forced_fair_value:
            structure.fair_value = forced_fair_value
        else:
            ask = structure.filtered_best_ask or structure.best_ask
            bid = structure.filtered_best_bid or structure.best_bid
            if ask is not None and bid is not None:
                structure.fair_value = (ask + bid) / 2
            else:
                structure.fair_value = None

        structure.spread = (
            structure.best_ask - structure.best_bid
            if structure.best_ask is not None and structure.best_bid is not None
            else None
        )
        structure.filtered_spread = (
            (structure.filtered_best_ask - structure.filtered_best_bid)
            if structure.filtered_best_ask is not None
            and structure.filtered_best_bid is not None
            else structure.spread
        )
        return structure

    def take_best_orders(
        self,
        product: Product,
        order_depth: OrderDepth,
        microstructure: Microstructure,
        take_width: float,
    ) -> List[Order]:
        orders = []
        if not microstructure.fair_value or not microstructure.spread:
            return orders

        # optimistically fill all the orders
        for bid, volume in list(order_depth.buy_orders.items()):
            if (
                bid
                >= microstructure.fair_value
                + take_width * microstructure.filtered_spread
            ):
                orders.append(Order(product, bid, -volume))
                del order_depth.buy_orders[bid]

        for ask, volume in list(order_depth.sell_orders.items()):
            if (
                ask
                <= microstructure.fair_value
                - take_width * microstructure.filtered_spread
            ):
                orders.append(Order(product, ask, -volume))
                del order_depth.sell_orders[ask]
        return orders
    



    def balance_limits(
        self,
        product: Product,
        position: int,
        orders: List[Order],
        min_bid: int,
        max_ask: int,
        position_limit: int = 50,
    ) -> List[Order]:
        final_position = position + sum(order.quantity for order in orders)
        balance_orders = []

        if final_position > position_limit:
            # Have to sell at some arbitrary level to get back down to 50
            balance_orders.append(
                Order(
                    product,
                    min_bid,
                    -final_position,
                )
            )
        elif final_position < -position_limit:
            # Have to buy at some arbitrary level to get back down to -50
            balance_orders.append(
                Order(
                    product,
                    max_ask,
                    final_position,
                )
            )
        return balance_orders

    def get_resin_orders(self, state: TradingState) -> List[Order]:
        # Settings
        product = Product.RAINFOREST_RESIN
        params = self.params[product]

        # Base calcs
        order_depth = deepcopy(state.order_depths.get(product, OrderDepth()))
        position = state.position.get(product, 0)
        microstructure = self._get_microstructure(
            order_depth,
            forced_min_volume=params.get("min_volume"),
            forced_fair_value=params.get("forced_fair_value"),
        )

        # Have to keep a reference of min_bid, max_ask because they might get cleared
        min_bid = min(order_depth.buy_orders.keys())
        max_ask = max(order_depth.sell_orders.keys())

        # Take orders
        take_orders = self.take_best_orders(product, order_depth, microstructure, 0)

        return [
            *take_orders,
            *self.balance_limits(product, position, take_orders, min_bid, max_ask),
        ]

    def get_kelp_orders(self, state: TradingState) -> List[Order]:
        # Settings
        product = Product.KELP
        params = self.params[product]

        # Base calcs
        order_depth = deepcopy(state.order_depths.get(product, OrderDepth()))
        position = state.position.get(product, 0)
        microstructure = self._get_microstructure(
            order_depth,
            forced_min_volume=params.get("min_volume"),
        )
        # Have to keep a reference of min_bid, max_ask because they might get cleared
        min_bid = min(order_depth.buy_orders.keys())
        max_ask = max(order_depth.sell_orders.keys())

        # Take orders
        take_orders = self.take_best_orders(product, order_depth, microstructure, 0)

        return [
            *take_orders,
            *self.balance_limits(product, position, take_orders, min_bid, max_ask),
        ]

    def get_squid_ink_orders(self, state: TradingState) -> List[Order]:
        # Settings
        product = Product.SQUID_INK
        params = self.params[product]

        # Base calcs
        order_depth = deepcopy(state.order_depths.get(product, OrderDepth()))
        position = state.position.get(product, 0)
        microstructure = self._get_microstructure(
            order_depth,
            forced_min_volume=params.get("min_volume"),
        )

        # Have to keep a reference of min_bid, max_ask because they might get cleared
        min_bid = min(order_depth.buy_orders.keys())
        max_ask = max(order_depth.sell_orders.keys())

        # Take orders
        take_orders = self.take_best_orders(product, order_depth, microstructure, 0)

        return [
            *take_orders,
            *self.balance_limits(product, position, take_orders, min_bid, max_ask),
        ]

    def run(self, state: TradingState):
        persistentData = {}
        if state.traderData != None and state.traderData != "":
            persistentData = jsonpickle.decode(state.traderData)

        result = {
            Product.RAINFOREST_RESIN: self.get_resin_orders(state),
            Product.KELP: self.get_kelp_orders(state),
            # Product.SQUID_INK: self.get_squid_ink_orders(state),
        }

        conversions = 1
        persistentData["logs"] = self.logs
        traderData = jsonpickle.encode(persistentData)

        logger.flush(state, result, conversions, traderData)

        return result, conversions, traderData
