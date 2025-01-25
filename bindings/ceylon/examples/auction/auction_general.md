# Building a Distributed Auction System with Ceylon

This tutorial demonstrates how to build a distributed auction system using the Ceylon multi-agent framework. The system consists of an auctioneer agent managing the auction process and multiple bidder agents competing for items.

## System Overview

The auction system implements:
- Single-item auctions with multiple bidders
- Automatic bid placement based on budget constraints
- Real-time auction status updates
- Distributed communication between auctioneer and bidders

## Core Components

### Data Models

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

### Auctioneer Agent

The auctioneer manages the auction process:

```python
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
```

Key methods:
- `handle_connection`: Monitors bidder connections and starts auction when all bidders join
- `handle_bid`: Processes incoming bids
- `end_auction`: Determines winner and broadcasts results

### Bidder Agent

Each bidder participates in the auction:

```python
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
```

Key methods:
- `handle_auction_start`: Places bid when auction begins
- `handle_auction_result`: Processes auction results
- `handle_auction_end`: Acknowledges auction completion

## Bidding Strategy

Bidders use a simple random strategy:
```python
random_multiplier = random.randint(100, 1000) / 100
bid_amount = min(self.budget, auction_start.item.starting_price * random_multiplier)
```

## Running the System

1. Create auction item and auctioneer:
```python
item = Item("Rare Painting", 1000.0)
auctioneer = Auctioneer(item, expected_bidders=3, port=8455)
admin_details = auctioneer.details()
```

2. Create bidders:
```python
bidders = [
    Bidder("Alice", 1500.0, admin_peer=admin_details.id),
    Bidder("Bob", 1200.0, admin_peer=admin_details.id),
    Bidder("Charlie", 2000.0, admin_peer=admin_details.id)
]
```

3. Start the system:
```python
await auctioneer.start_agent(b"", bidders)
```

## Sample Output

```
ceylon version: 0.22.1
visit https://ceylon.ai for more information
2025-01-26 00:04:41.323 | INFO     | __main__:<module>:161 - Initializing auction system...
2025-01-26 00:04:41.327 | INFO     | __main__:main:155 - Starting auction system...
2025-01-26 00:04:41.327 | INFO     | ceylon.base.uni_agent:start_agent:76 - Starting auctioneer agent in ADMIN mode
2025-01-26 00:04:41.389 | INFO     | __main__:handle_run:91 - Auctioneer started - auctioneer
2025-01-26 00:04:41.389 | INFO     | __main__:handle_run:138 - Bidder started - Alice
2025-01-26 00:04:41.389 | INFO     | __main__:handle_run:138 - Bidder started - Bob
2025-01-26 00:04:41.389 | INFO     | __main__:handle_run:138 - Bidder started - Charlie
2025-01-26 00:04:41.389 | INFO     | __main__:handle_run:138 - Bidder started - Jon
2025-01-26 00:04:41.548 | INFO     | __main__:handle_connection:50 - Bidder Alice connected with auctioneer. 0/3 bidders connected.
2025-01-26 00:04:41.548 | INFO     | __main__:handle_connection:57 - Waiting for more bidders to connect...
2025-01-26 00:04:41.549 | INFO     | __main__:handle_connection:50 - Bidder Bob connected with auctioneer. 1/3 bidders connected.
2025-01-26 00:04:41.549 | INFO     | __main__:handle_connection:57 - Waiting for more bidders to connect...
2025-01-26 00:04:41.589 | INFO     | __main__:handle_connection:50 - Bidder Jon connected with auctioneer. 2/3 bidders connected.
2025-01-26 00:04:41.589 | INFO     | __main__:handle_connection:57 - Waiting for more bidders to connect...
2025-01-26 00:04:41.591 | INFO     | __main__:handle_connection:50 - Bidder Charlie connected with auctioneer. 3/3 bidders connected.
2025-01-26 00:04:41.591 | INFO     | __main__:handle_connection:54 - All bidders connected. Starting the auction.
2025-01-26 00:04:41.591 | INFO     | __main__:start_auction:60 - Starting auction for Rare Painting with starting price $1000.0
2025-01-26 00:04:41.654 | INFO     | __main__:handle_auction_start:122 - Bob placed bid: $1200.00
2025-01-26 00:04:41.654 | INFO     | __main__:handle_auction_start:122 - Alice placed bid: $1500.00
2025-01-26 00:04:41.665 | INFO     | __main__:handle_auction_start:122 - Jon placed bid: $2800.00
2025-01-26 00:04:41.669 | INFO     | __main__:handle_auction_start:122 - Charlie placed bid: $2000.00
2025-01-26 00:04:41.685 | INFO     | __main__:handle_bid:70 - Received bid from Jon for $2800.00
2025-01-26 00:04:41.687 | INFO     | __main__:handle_bid:70 - Received bid from Charlie for $2000.00
2025-01-26 00:04:41.695 | INFO     | __main__:handle_bid:70 - Received bid from Bob for $1200.00
2025-01-26 00:04:41.695 | INFO     | __main__:end_auction:84 - Auction ended. Winner: Jon, Winning Bid: $2800.00
```

## Customization Options

- Modify bidding strategy by adjusting the random multiplier range
- Add minimum bid increments
- Implement multiple auction rounds
- Add timeout mechanisms for bidder responses
- Implement different auction types (Dutch, English, etc.)

## Sequence Diagram

````mermaid
sequenceDiagram
    participant A as Auctioneer
    participant B1 as Bidder1
    participant B2 as Bidder2
    participant B3 as Bidder3

    Note over A,B3: Connection Phase
    B1->>A: Connect
    A->>B1: Connection Confirmed
    B2->>A: Connect
    A->>B2: Connection Confirmed
    B3->>A: Connect
    A->>B3: Connection Confirmed

    Note over A,B3: Auction Start
    A->>B1: AuctionStart(item)
    A->>B2: AuctionStart(item)
    A->>B3: AuctionStart(item)

    Note over A,B3: Bidding Phase
    B1-->>A: Bid(amount)
    B2-->>A: Bid(amount)
    B3-->>A: Bid(amount)

    Note over A,B3: Auction End
    A->>B1: AuctionResult(winner, amount)
    A->>B2: AuctionResult(winner, amount)
    A->>B3: AuctionResult(winner, amount)

    A->>B1: AuctionEnd
    A->>B2: AuctionEnd
    A->>B3: AuctionEnd
````