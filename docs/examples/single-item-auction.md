# Single-Item Auction System with Ceylon

## Introduction

In this guide, we will walk you through the process of building a single-item auction system using the Ceylon framework. The system simulates an auction where multiple bidders compete to purchase an item, with an auctioneer managing the entire process.

## System Overview

The auction system is composed of two primary components:

1. **Auctioneer**: Manages the auction, collects bids, and determines the winner.
2. **Bidders**: Participate in the auction by placing bids.

Ceylon's agent-based architecture allows seamless communication and coordination between these components, making it ideal for such a system.

## Prerequisites

Before you dive into the code, ensure you have the following:

- Python 3.7 or higher installed on your system.
- The Ceylon framework installed (`pip install ceylon`).
- A basic understanding of asynchronous programming in Python.

## Step-by-Step Implementation

### 1. Defining Data Structures

The first step in building our auction system is to define the data structures that will be used for communication between the auctioneer and bidders. We use Pydantic dataclasses for this purpose:

```python
from pydantic.dataclasses import dataclass

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
```

- **Item**: Represents the item being auctioned, including its name and starting price.
- **Bid**: Represents a bid placed by a bidder, including the bidder's name and the bid amount.
- **AuctionStart**: Signals the start of the auction, carrying information about the item.
- **AuctionResult**: Contains the result of the auction, including the winner's name and the winning bid.
- **AuctionEnd**: Signals the end of the auction process.

### 2. Implementing the Bidder Agent

Next, we'll implement the bidder agent. Each bidder will listen for the start of the auction and place a bid if their budget allows.

```python
import random
from ceylon import Agent, on_message

class Bidder(Agent):
    name: str
    budget: float

    def __init__(self, name: str, budget: float):
        self.name = name
        self.budget = budget
        super().__init__(name=name, workspace_id="single_item_auction", admin_peer="Auctioneer", admin_port=8000, role="bidder")

    @on_message(type=AuctionStart)
    async def on_auction_start(self, data: AuctionStart):
        if self.budget > data.item.starting_price:
            random_i = random.randint(100, 1000)
            bid_amount = min(self.budget, data.item.starting_price * random_i / 100)
            await self.broadcast_data(Bid(bidder=self.name, amount=bid_amount))

    @on_message(type=AuctionResult)
    async def on_auction_result(self, data: AuctionResult):
        if data.winner == self.name:
            self.budget -= data.winning_bid
            print(f"{self.name} won the auction for ${data.winning_bid:.2f}")
```

- **Initialization**: Each `Bidder` is initialized with a name and budget.
- **Handling Auction Start**: The bidder listens for the `AuctionStart` message and places a random bid within their budget.
- **Handling Auction Result**: The bidder listens for the `AuctionResult` message and deducts the winning bid amount from their budget if they win.

### 3. Implementing the Auctioneer

The auctioneer is responsible for managing the auction, including starting it, collecting bids, and determining the winner.

```python
from ceylon import CoreAdmin
from typing import List

class Auctioneer(CoreAdmin):
    item: Item
    bids: List[Bid] = []
    expected_bidders: int
    connected_bidders: int = 0

    def __init__(self, item: Item, expected_bidders: int):
        self.item = item
        self.expected_bidders = expected_bidders
        super().__init__(name="single_item_auction", port=8000)

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
```

- **Initialization**: The `Auctioneer` is initialized with the auction item and the expected number of bidders.
- **Handling Agent Connection**: The auctioneer waits for all bidders to connect before starting the auction.
- **Starting the Auction**: The auctioneer broadcasts the `AuctionStart` message to all bidders.
- **Handling Bids**: The auctioneer collects bids and ends the auction after receiving bids.
- **Ending the Auction**: The auctioneer determines the highest bid and announces the winner.

### 4. Running the Auction System

Finally, we set up the auction environment by creating the auctioneer and bidders, and then running the system.

```python
if __name__ == '__main__':
    item = Item("Rare Painting", 1000)

    bidders = [
        Bidder("Alice", 1500),
        Bidder("Bob", 1200),
        Bidder("Charlie", 2000),
    ]

    auctioneer = Auctioneer(item, expected_bidders=len(bidders))
    auctioneer.run_admin(inputs=b"", workers=bidders)
```

- **Item Creation**: An item to be auctioned is created with a name and starting price.
- **Bidder Creation**: Three bidders are created with different budgets.
- **Auctioneer Setup**: An auctioneer is created with the item and the expected number of bidders.
- **System Execution**: The auction system is run, with the auctioneer managing the process and bidders placing bids.

## Key Ceylon Framework Features Used

1. **Agent-based Architecture**: The system uses `Agent` for bidders and `CoreAdmin` for the auctioneer.
2. **Message Handling**: The `@on_message` decorator handles specific message types, making it easy to react to different events in the auction process.
3. **Asynchronous Programming**: Ceylon leverages Python's async capabilities, ensuring efficient communication and coordination between agents.
4. **Broadcast Messaging**: The `broadcast_data()` method is used to send messages to all agents, ensuring everyone is informed of the auction's progress.

## Potential Enhancements

While the current implementation is functional, there are several ways to extend and enhance the system:

1. Implement a more sophisticated bidding strategy for the bidders.
2. Add support for multiple rounds of bidding.
3. Introduce a time limit for the auction, adding urgency to the bidding process.
4. Implement different auction types, such as Dutch auctions or silent auctions.
5. Improve error handling and account for edge cases, such as network failures or disconnected agents.