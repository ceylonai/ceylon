# Single-Item Distributed Auction System

This project demonstrates a simple distributed auction system using the Ceylon framework. It simulates an auction where
multiple bidders compete for a single item, managed by an auctioneer.

## Overview

The system consists of two main types of agents:

1. **Bidders**: Represent individuals with a budget who can place bids on the item.
2. **Auctioneer**: Manages the auction process, including starting the auction and determining the winner.

## Components

### Data Classes

- `Item`: Represents the item being auctioned, with a name and starting price.
- `Bid`: Represents a bid made by a bidder, including the bidder's name and bid amount.
- `AuctionStart`: Signals the start of the auction with the item details.
- `AuctionResult`: Represents the result of the auction, including the winner and winning bid amount.
- `AuctionEnd`: Signals the end of the auction, allowing bidders to acknowledge the auction completion.

### Agents

1. **Bidder (Worker)**
   - Manages individual budgets and places bids.
   - Uses a random bidding strategy with multiplier between 1.0 and 10.0 times the starting price.
   - Only bids if budget is higher than the starting price.
   - Methods:
      - `on_message`: Handles incoming auction messages (AuctionStart, AuctionResult, AuctionEnd) and places bids.
      - `run`: Maintains the bidder's event loop.

2. **Auctioneer (Admin)**
   - Manages the overall auction process.
   - Methods:
      - `on_agent_connected`: Tracks connected bidders and starts the auction when all are connected.
      - `start_auction`: Initiates the auction by broadcasting the item details.
      - `on_message`: Processes incoming bids.
      - `end_auction`: Determines the winner and broadcasts the result when all bids are received.
      - `run`: Maintains the auctioneer's event loop.

## How It Works

1. The Auctioneer is initialized with an item and expected number of bidders.
2. Bidders are created with individual budgets and connected to the Auctioneer.
3. The Auctioneer waits for all Bidders to connect.
4. Once all Bidders are connected, the Auctioneer starts the auction by broadcasting the item details.
5. Bidders receive the auction start message and place their bids using a random multiplier strategy.
6. The Auctioneer collects all bids and ends the auction after receiving bids from all bidders.
7. The Auctioneer determines the winner (highest bidder) and broadcasts the result.
8. Bidders receive the result, update their budgets if they won, and acknowledge the auction end.

## Running the Code

To run the single-item auction simulation:

1. Ensure you have the required dependencies installed:
   ```
   pip install asyncio loguru ceylon
   ```

2. Save the code in a file (e.g., `single_item_auction.py`).

3. Run the script:
   ```
   python single_item_auction.py
   ```

## Default Configuration

The default setup includes:

- A "Rare Painting" item with starting price of $1,000
- Three bidders:
   - Alice (Budget: $1,500)
   - Bob (Budget: $1,200)
   - Charlie (Budget: $2,000)
- Random bidding strategy with multipliers between 1.0x and 10.0x the starting price

## Customization

You can customize the simulation by modifying the `main` function:

- Adjust the item's name and starting price in the Item initialization
- Change the number of bidders and their budgets
- Modify the bidding strategy in the `Bidder.on_message` method
- Adjust the random multiplier range for more conservative or aggressive bidding

## Note

This implementation uses the Ceylon framework for agent communication and the Loguru library for logging. Make sure you have these libraries properly installed in your environment.

## Limitations and Potential Improvements

- The auction ends after receiving bids from all bidders, with no support for multiple bidding rounds
- The random bidding strategy is relatively simple and could be enhanced with more sophisticated algorithms
- There's no timeout mechanism for bidders who fail to submit a bid
- Error handling could be improved for edge cases like network failures or disconnected bidders
- The system could be extended to support multiple items or concurrent auctions
- Bidder authentication and bid verification could be added for security

These limitations provide opportunities for extending and improving the system for more realistic auction simulations.