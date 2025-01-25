import asyncio
import pickle
import random
from dataclasses import dataclass
from typing import List

from loguru import logger
from ceylon import AgentDetail, enable_log, BaseAgent, PeerMode, DEFAULT_WORKSPACE_ID, on, on_run, on_connect

enable_log("INFO")

@dataclass
class Item:
    name: str
    starting_price: float

@dataclass
class Bid:
    bidder: str
    amount: float

@dataclass
class AuctionStart:
    item: Item

@dataclass
class AuctionResult:
    winner: str
    winning_bid: float

@dataclass
class AuctionEnd:
    pass

class Auctioneer(BaseAgent):
    def __init__(self, item: Item, expected_bidders: int, name="auctioneer", port=8888):
        super().__init__(
            name=name,
            mode=PeerMode.ADMIN,
            role="auctioneer",
            port=port
        )
        self.item = item
        self.expected_bidders = expected_bidders
        self.bids: List[Bid] = []
        self.auction_ended = False

    @on_connect("*")
    async def handle_connection(self, topic: str, agent: AgentDetail):
        logger.info(
            f"Bidder {agent.name} connected with {self.details().name}. {len(await self.get_connected_agents())}/{self.expected_bidders} bidders connected."
        )
        if len(await self.get_connected_agents()) == self.expected_bidders:
            logger.info("All bidders connected. Starting the auction.")
            await self.start_auction()
        else:
            logger.info("Waiting for more bidders to connect...")

    async def start_auction(self):
        logger.info(f"Starting auction for {self.item.name} with starting price ${self.item.starting_price}")
        start_msg = AuctionStart(item=self.item)
        await self.broadcast_message(start_msg)

    @on(Bid)
    async def handle_bid(self, bid: Bid, time: int, agent: AgentDetail):
        if self.auction_ended:
            return

        self.bids.append(bid)
        logger.info(f"Received bid from {bid.bidder} for ${bid.amount:.2f}")

        if len(self.bids) == self.expected_bidders:
            await self.end_auction()

    async def end_auction(self):
        self.auction_ended = True

        if not self.bids:
            logger.info(f"No bids received for {self.item.name}")
        else:
            winning_bid = max(self.bids, key=lambda x: x.amount)
            result = AuctionResult(winner=winning_bid.bidder, winning_bid=winning_bid.amount)
            await self.broadcast_message(result)
            logger.info(f"Auction ended. Winner: {result.winner}, Winning Bid: ${result.winning_bid:.2f}")
            await self.stop()

        await self.broadcast_message(AuctionEnd())

    @on_run()
    async def handle_run(self, inputs: bytes):
        logger.info(f"Auctioneer started - {self.details().name}")
        while True:
            if self.auction_ended:
                break
            await asyncio.sleep(1)

class Bidder(BaseAgent):
    def __init__(self, name: str, budget: float,
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_peer="",
                 admin_port=8888):
        super().__init__(
            name=name,
            mode=PeerMode.CLIENT,
            role="bidder"
        )
        self.budget = budget
        self.has_bid = False

    @on(AuctionStart)
    async def handle_auction_start(self, auction_start: AuctionStart, time: int, agent: AgentDetail):
        if self.has_bid:
            return

        if self.budget > auction_start.item.starting_price:
            random_multiplier = random.randint(100, 1000) / 100
            bid_amount = min(self.budget, auction_start.item.starting_price * random_multiplier)

            bid = Bid(bidder=self.details().name, amount=bid_amount)
            await self.send_message(agent.id, bid)
            self.has_bid = True
            logger.info(f"{self.details().name} placed bid: ${bid_amount:.2f}")

    @on(AuctionResult)
    async def handle_auction_result(self, result: AuctionResult, time: int, agent: AgentDetail):
        if result.winner == self.details().name:
            self.budget -= result.winning_bid
            logger.info(f"{self.details().name} won the auction for ${result.winning_bid:.2f}")
        else:
            logger.info(f"{self.details().name} lost the auction")

    @on(AuctionEnd)
    async def handle_auction_end(self, end: AuctionEnd, time: int, agent: AgentDetail):
        logger.info(f"{self.details().name} acknowledging auction end")

    @on_run()
    async def handle_run(self, inputs: bytes):
        logger.info(f"Bidder started - {self.details().name}")
        while True:
            await asyncio.sleep(1)

async def main():
    item = Item("Rare Painting", 1000.0)
    auctioneer = Auctioneer(item, expected_bidders=3, port=8455)
    admin_details = auctioneer.details()

    bidders = [
        Bidder("Alice", 1500.0, admin_peer=admin_details.id),
        Bidder("Bob", 1200.0, admin_peer=admin_details.id),
        Bidder("Charlie", 2000.0, admin_peer=admin_details.id),
        Bidder("Jon", 2800.0, admin_peer=admin_details.id)
    ]

    try:
        logger.info("Starting auction system...")
        await auctioneer.start_agent(b"", bidders)
    except KeyboardInterrupt:
        logger.info("Shutting down auction system...")

if __name__ == "__main__":
    logger.info("Initializing auction system...")
    asyncio.run(main())