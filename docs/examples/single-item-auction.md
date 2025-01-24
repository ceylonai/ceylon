## Single Item Auction

## Introduction

This guide demonstrates how to build a real-time single-item auction system using the Ceylon framework. The system enables multiple bidders to compete for an item while an auctioneer manages the bidding process using Ceylon's agent-based architecture.

## System Overview

The auction system consists of two main components:

1. **Auctioneer (Admin Agent)**: Controls the auction flow by:
    - Managing bidder connections
    - Broadcasting auction start
    - Collecting and processing bids
    - Determining and announcing the winner

2. **Bidders (Worker Agents)**: Participate in the auction by:
    - Connecting to the auction system
    - Placing bids within their budget
    - Receiving auction results

## Prerequisites

- Python 3.7 or higher
- Ceylon framework (`pip install ceylon`)
- Basic understanding of:
    - Asynchronous programming in Python
    - Agent-based architectures
    - The Ceylon framework

## Implementation Details

### Data Models

The system uses dataclasses for message passing between agents:

```python
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
```

### Auctioneer Implementation

The Auctioneer extends Ceylon's `Admin` class and manages the auction lifecycle:

```python
class Auctioneer(Admin):
    def __init__(self, item: Item, expected_bidders: int, name="auctioneer", port=8888):
        super().__init__(name=name, port=port)
        self.item = item
        self.expected_bidders = expected_bidders
        self.bids = []
        self.auction_ended = False
```

Key features:
- Tracks connected bidders
- Broadcasts auction start when all bidders connect
- Processes incoming bids
- Determines and announces the winner
- Manages auction completion

### Bidder Implementation

Bidders extend Ceylon's `Worker` class and handle auction participation:

```python
class Bidder(Worker):
    def __init__(self, name: str, budget: float, workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_peer="", admin_port=8888):
        super().__init__(name=name, workspace_id=workspace_id,
                        admin_peer=admin_peer, admin_port=admin_port)
        self.budget = budget
        self.has_bid = False
```

Key features:
- Maintains bidder budget
- Implements bidding strategy
- Processes auction messages
- Handles win/loss results

## Running the System

To start the auction system:

```python
async def main():
    # Create auction item
    item = Item("Rare Painting", 1000.0)

    # Initialize auctioneer
    auctioneer = Auctioneer(item, expected_bidders=3)
    admin_details = auctioneer.details()

    # Create bidders
    bidders = [
        Bidder("Alice", 1500.0, admin_peer=admin_details.id),
        Bidder("Bob", 1200.0, admin_peer=admin_details.id),
        Bidder("Charlie", 2000.0, admin_peer=admin_details.id)
    ]

    # Run the auction
    await auctioneer.arun_admin(b"", bidders)

if __name__ == "__main__":
    asyncio.run(main())
```

## System Features

- **Real-time Bidding**: Immediate bid processing and updates
- **Automatic Winner Selection**: Highest bid wins automatically
- **Budget Management**: Bidders cannot exceed their budget
- **Graceful Completion**: Clean shutdown after auction ends
- **Error Handling**: Robust message processing with error logging

## Advanced Features

The current implementation includes:
- Random bidding strategy with multipliers
- Budget constraints
- Automatic auction completion
- Logging with loguru

## Future Enhancements

Consider these potential improvements:
1. Multiple round support
2. Time-based auction endings
3. Different auction types (Dutch, Silent, etc.)
4. Reserve prices and minimum bid increments
5. Proxy bidding support
6. Real-time bid updates to all participants
7. Transaction history and audit logs
8. Automated testing suite

## Contributing

Feel free to submit issues and enhancement requests. Contributions are welcome!

---

Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).