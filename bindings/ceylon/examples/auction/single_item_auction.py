import asyncio
import pickle
import random
from typing import List

from pydantic.dataclasses import dataclass

from ceylon.core.admin import Admin
from ceylon.core.worker import Worker

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


class Bidder(Worker):
    name: str
    budget: float

    def __init__(self, name: str, budget: float):
        self.name = name
        self.budget = budget
        super().__init__(name=name, workspace_id=workspace_id, admin_peer=admin_peer, admin_port=admin_port)

    async def on_message(self, agent_id: str, data: bytes, time: int):
        message = pickle.loads(data)
        if type(message) == AuctionStart:
            if self.budget > message.item.starting_price:
                random_i = random.randint(100, 1000)
                bid_amount = min(self.budget, message.item.starting_price * random_i / 100)  # Simple bidding strategy
                await self.broadcast(pickle.dumps(Bid(bidder=self.name, amount=bid_amount)))
        elif type(message) == AuctionResult:
            if message.winner == self.name:
                self.budget -= message.winning_bid
                print(f"{self.name} won the auction for ${message.winning_bid:.2f}")
            else:
                print(f"{self.name} lost the auction")


class Auctioneer(Admin):
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
        await self.broadcast(pickle.dumps(AuctionStart(item=self.item)))

    async def on_message(self, agent_id: str, data: bytes, time: int):
        message = pickle.loads(data)
        if type(message) == Bid:
            self.bids.append(message)
            print(f"Received bid from {message.bidder} for ${message.amount:.2f}")
        await self.end_auction()

    async def end_auction(self):
        if not self.bids:
            print(f"No bids received for {self.item.name}")
        else:
            winning_bid = max(self.bids, key=lambda x: x.amount)
            result = AuctionResult(winner=winning_bid.bidder, winning_bid=winning_bid.amount)
            await self.broadcast(pickle.dumps(result))
            print(f"Auction ended. Winner: {result.winner}, Winning Bid: ${result.winning_bid:.2f}")

        await self.broadcast(pickle.dumps(AuctionEnd()))


async def main():
    item = Item("Rare Painting", 1000)

    bidders = [
        Bidder("Alice", 1500),
        Bidder("Bob", 1200),
        Bidder("Charlie", 2000),
    ]

    auctioneer = Auctioneer(item, expected_bidders=len(bidders))
    await auctioneer.run_admin(inputs=b"", workers=bidders)


if __name__ == '__main__':
    asyncio.run(main())
