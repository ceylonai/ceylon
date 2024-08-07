import pickle
import random
from typing import List

from pydantic.dataclasses import dataclass

from ceylon import Agent, on_message
from ceylon import CoreAdmin

admin_port = 8000
admin_peer = "Auctioneer"
workspace_id = "single_item_auction"


@dataclass(repr=True)
class Item:
    name: str
    starting_price: float


@dataclass(repr=True)
class Bid:
    bidder: str
    amount: float


@dataclass(repr=True)
class AuctionStart:
    item: Item


@dataclass(repr=True)
class AuctionResult:
    winner: str
    winning_bid: float


@dataclass(repr=True)
class AuctionEnd:
    pass


class Bidder(Agent):
    name: str
    budget: float

    def __init__(self, name: str, budget: float):
        self.name = name
        self.budget = budget
        super().__init__(name=name, workspace_id=workspace_id, admin_peer=admin_peer, admin_port=admin_port,
                         role="bidder")

    @on_message(type=AuctionStart)
    async def on_auction_start(self, data: AuctionStart):
        if self.budget > data.item.starting_price:
            random_i = random.randint(100, 1000)
            bid_amount = min(self.budget, data.item.starting_price * random_i / 100)  # Simple bidding strategy
            await self.broadcast_data(Bid(bidder=self.name, amount=bid_amount))

    @on_message(type=Bid)
    async def on_auction_result(self, data: AuctionResult):
        self.budget -= data.winning_bid
        print(f"{self.name} won the auction for ${data.winning_bid:.2f}")


class Auctioneer(CoreAdmin):
    item: Item
    bids: List[Bid] = []
    expected_bidders: int
    connected_bidders: int = 0

    def __init__(self, item: Item, expected_bidders: int):
        self.item = item
        self.expected_bidders = expected_bidders
        super().__init__(name=workspace_id, port=admin_port)

    async def on_agent_connected(self, topic: str, agent_id: str):
        self.connected_bidders += 1
        print(f"Bidder {agent_id} connected. {self.connected_bidders}/{self.expected_bidders} bidders connected.")
        if self.connected_bidders == self.expected_bidders:
            print("All bidders connected. Starting the auction.")
            await self.start_auction()

    async def start_auction(self):
        print(f"Starting auction for {self.item.name} with starting price ${self.item.starting_price}")
        await self.broadcast_data(AuctionStart(item=self.item))

    @on_message(type=Bid)
    async def on_bid(self, bid: Bid):
        self.bids.append(bid)
        print(f"Received bid from {bid.bidder} for ${bid.amount:.2f}")
        await self.end_auction()

    async def end_auction(self):
        if not self.bids:
            print(f"No bids received for {self.item.name}")
        else:
            winning_bid = max(self.bids, key=lambda x: x.amount)
            result = AuctionResult(winner=winning_bid.bidder, winning_bid=winning_bid.amount)
            await self.broadcast_data(result)
            print(f"Auction ended. Winner: {result.winner}, Winning Bid: ${result.winning_bid:.2f}")
            await self.stop()

        await self.broadcast_data(AuctionEnd())


if __name__ == '__main__':
    item = Item("Rare Painting", 1000)

    bidders = [
        Bidder("Alice", 1500),
        Bidder("Bob", 1200),
        Bidder("Charlie", 2000),
    ]

    auctioneer = Auctioneer(item, expected_bidders=len(bidders))
    auctioneer.run_admin(inputs=b"", workers=bidders)
