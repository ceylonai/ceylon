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
- `AuctionEnd`: Signals the end of the auction.

### Agents

1. **Bidder (Worker)**
    - Manages individual budgets and places bids.
    - Uses a random bidding strategy to determine bid amounts.
    - Methods:
        - `on_message`: Handles incoming auction messages and places bids.

2. **Auctioneer (Admin)**
    - Manages the overall auction process.
    - Methods:
        - `on_agent_connected`: Tracks connected bidders and starts the auction when all are connected.
        - `start_auction`: Initiates the auction by broadcasting the item details.
        - `on_message`: Processes incoming bids and ends the auction after each bid.
        - `end_auction`: Determines the winner and broadcasts the result.

## How It Works

1. The Auctioneer waits for all Bidders to connect.
2. Once all Bidders are connected, the Auctioneer starts the auction by broadcasting the item details.
3. Bidders receive the auction start message and place their bids using a random strategy.
4. The Auctioneer receives each bid and immediately ends the auction after processing it.
5. The Auctioneer determines the winner (highest bidder) and broadcasts the result.
6. Bidders receive the result and update their status (won/lost).

## Running the Code

To run the single-item auction simulation:

1. Ensure you have the required dependencies installed:
   ```
   pip install asyncio pydantic ceylon
   ```

2. Save the code in a file (e.g., `single_item_auction.py`).

3. Run the script:
   ```
   python single_item_auction.py
   ```

4. The script will simulate the auction process and output the results, including connections, bids, and the final
   auction result.

## Customization

You can customize the simulation by modifying the `main` function:

- Adjust the item's name and starting price.
- Change the number of Bidders and their budgets.
- Modify the bidding strategy in the `Bidder` class for more complex behavior.

## Note

This example uses the Ceylon framework for agent communication. Ensure you have the Ceylon library properly installed
and configured in your environment.

## Limitations and Potential Improvements

- The current implementation ends the auction after the first bid, which may not be realistic for most auction
  scenarios.
- There's no mechanism for multiple bidding rounds or time-based auction closure.
- The random bidding strategy might result in unrealistic bid amounts.
- Error handling and edge cases (e.g., no bids received) could be improved.

These limitations provide opportunities for extending and improving the system for more realistic auction simulations.