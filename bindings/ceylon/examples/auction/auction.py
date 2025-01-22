#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import pickle
import random
from dataclasses import dataclass
from typing import List

from loguru import logger

from ceylon import AgentDetail, enable_log
from ceylon.base.uni_agent import BaseAgent
from ceylon.ceylon import PeerMode

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


class AuctioneerAgent(BaseAgent):
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

    async def on_agent_connected(self, topic: str, agent: AgentDetail) -> None:
        await super().on_agent_connected(topic, agent)
        logger.info(
            f"Bidder {agent.name} connected. {len(self.get_connected_agents())}/{self.expected_bidders} bidders connected.")

        if len(self.get_connected_agents()) == self.expected_bidders:
            logger.info("All bidders connected. Starting the auction.")
            await self.start_auction()

    async def start_auction(self):
        logger.info(f"Starting auction for {self.item.name} with starting price ${self.item.starting_price}")
        start_msg = AuctionStart(item=self.item)
        await self.broadcast_message(start_msg)

    async def on_message(self, agent_id: str, data: bytes, time: int) -> None:
        if self.auction_ended:
            return

        try:
            message = pickle.loads(data)

            if isinstance(message, Bid):
                self.bids.append(message)
                logger.info(f"Received bid from {message.bidder} for ${message.amount:.2f}")

                # Check if we've received bids from all bidders
                if len(self.bids) == self.expected_bidders:
                    await self.end_auction()

        except Exception as e:
            logger.error(f"Error processing message: {e}")

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

    async def run(self, inputs: bytes) -> None:
        logger.info(f"Auctioneer started - {self.details().name}")
        while True:
            await self.broadcast_message(AuctionStart(item=self.item))
            if self.auction_ended:
                break
            await asyncio.sleep(1)


class BidderAgent(BaseAgent):
    def __init__(self,
                 name: str,
                 budget: float,
                 admin_peer: str = None,
                 admin_port: int = 8888,
                 admin_ip: str = "127.0.0.1"):
        super().__init__(
            name=name,
            mode=PeerMode.CLIENT,
            role="bidder",
            admin_peer=admin_peer,
            port=admin_port,
            admin_ip=admin_ip
        )
        self.budget = budget
        self.has_bid = False

    async def on_message(self, agent_id: str, data: bytes, time: int) -> None:
        try:
            message = pickle.loads(data)

            if isinstance(message, AuctionStart) and not self.has_bid:
                if self.budget > message.item.starting_price:
                    # Simple bidding strategy with random multiplier
                    random_multiplier = random.randint(100, 1000) / 100
                    bid_amount = min(self.budget, message.item.starting_price * random_multiplier)

                    bid = Bid(bidder=self.get_agent_details().name, amount=bid_amount)
                    await self.send_direct(agent_id, bid)
                    self.has_bid = True
                    logger.info(f"{self.get_agent_details().name} placed bid: ${bid_amount:.2f}")

            elif isinstance(message, AuctionResult):
                if message.winner == self.get_agent_details().name:
                    self.budget -= message.winning_bid
                    logger.info(f"{self.get_agent_details().name} won the auction for ${message.winning_bid:.2f}")
                else:
                    logger.info(f"{self.get_agent_details().name} lost the auction")

            elif isinstance(message, AuctionEnd):
                logger.info(f"{self.get_agent_details().name} acknowledging auction end")
                await self.stop()

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def run(self, inputs: bytes) -> None:
        logger.info(f"Bidder started - {self.get_agent_details().name}")
        while True:
            await asyncio.sleep(1)


async def main():
    # Create auction item
    item = Item("Rare Painting", 1000.0)

    # Create auctioneer
    auctioneer = AuctioneerAgent(item, expected_bidders=3, port=5454)

    # Create bidders
    bidders = [
        BidderAgent("Alice", 1500.0),
        BidderAgent("Bob", 1200.0),
        BidderAgent("Charlie", 2000.0)
    ]

    await auctioneer.start(b"", bidders)
    # Start all bidders

    try:
        # Keep the main task running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down auction system...")
        await auctioneer.stop()
        for bidder in bidders:
            await bidder.stop()


if __name__ == "__main__":
    logger.info("Initializing auction system...")
    asyncio.run(main())
