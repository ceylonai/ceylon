import asyncio
import random
from dataclasses import dataclass
from typing import List, Dict, Optional
from loguru import logger

from ceylon.task import TaskPlayGround
from ceylon.task.data import TaskMessage, TaskGroup, TaskGroupGoal, GoalStatus
from ceylon.task.manager import TaskManager
from ceylon.task.agent import TaskExecutionAgent

# Data Models
@dataclass
class Item:
    name: str
    starting_price: float

@dataclass
class Bid:
    bidder: str
    amount: float
    item_id: str

# Auction Agent Implementation
class AuctionAgent(TaskExecutionAgent):
    def __init__(self, name: str, budget: float, max_concurrent_tasks: int = 1):
        super().__init__(
            name=name,
            worker_role="bidder",
            max_concurrent_tasks=max_concurrent_tasks
        )
        self.budget = budget
        self.bids: Dict[str, Bid] = {}

    async def execute_task(self, task: TaskMessage) -> None:
        """Process auction tasks"""
        try:
            if task.metadata.get('type') == 'auction_bid':
                # Extract auction details from task
                item = Item(**task.metadata['item'])
                if self.budget >= item.starting_price:
                    # Calculate random bid amount between starting price and budget
                    # Random multiplier between 1.0 and 2.0 for starting price
                    random_multiplier = 1.0 + random.random()
                    # Random percentage of remaining budget (0% to 100%)
                    budget_percentage = random.random()

                    # Combine both random factors
                    base_bid = item.starting_price * random_multiplier
                    budget_portion = (self.budget - base_bid) * budget_percentage
                    bid_amount = min(
                        self.budget,
                        base_bid + budget_portion
                    )

                    # Record bid
                    bid = Bid(
                        bidder=self.name,
                        amount=bid_amount,
                        item_id=task.metadata['item_id']
                    )
                    self.bids[task.task_id] = bid

                    # Update task with bid information
                    task.completed = True
                    task.metadata['bid'] = bid.__dict__
                    logger.info(f"{self.name} placed bid: ${bid_amount:.2f}")
                else:
                    logger.info(f"{self.name} cannot afford starting price of ${item.starting_price:.2f}")
                    task.completed = True

            task.end_time = asyncio.get_event_loop().time()
            await self.broadcast_message(task)

        except Exception as e:
            logger.error(f"Error in auction task execution: {e}")
            task.completed = False
            task.metadata['error'] = str(e)
            await self.broadcast_message(task)

async def setup_auction(
        item: Item,
        bidders: List[AuctionAgent],
        min_bids: int
) -> TaskPlayGround:
    """Setup and configure the auction playground"""

    # Initialize playground
    playground = TaskPlayGround(name="auction_system")

    def check_bid_count(task_groups: dict, completed_tasks: dict) -> bool:
        """Check if we've received enough valid bids"""
        bid_count = sum(
            1 for task in completed_tasks.values()
            if task.completed and 'bid' in (task.metadata or {})
        )
        logger.info(f"Current bid count: {bid_count}/{min_bids}")
        return bid_count >= min_bids

    # Create auction tasks for each bidder
    auction_tasks = [
        TaskMessage(
            task_id=f"bid_{bidder.name}_{item.name}",
            name=f"Place bid for {item.name}",
            instructions=f"Submit bid for {item.name} (Starting price: ${item.starting_price:.2f})",
            duration=1,
            required_role="bidder",
            metadata={
                'type': 'auction_bid',
                'item': item.__dict__,
                'item_id': item.name,
            }
        )
        for bidder in bidders
    ]

    # Create task group with goal
    auction_group = TaskManager.create_task_group(
        name=f"Auction: {item.name}",
        description=f"Auction process for {item.name}",
        subtasks=auction_tasks,
        goal=TaskGroupGoal(
            name="Minimum Bids Received",
            description=f"Receive at least {min_bids} valid bids",
            check_condition=check_bid_count,
            success_message=f"Successfully received {min_bids} bids!",
            failure_message="Failed to receive enough valid bids."
        ),
        priority=1
    )

    return playground, auction_group

async def run_auction(
        item: Item,
        bidders: List[AuctionAgent],
        min_bids: int
) -> Optional[Bid]:
    """Run an auction and return the winning bid"""

    # Setup auction system
    playground, auction_group = await setup_auction(item, bidders, min_bids)

    try:
        logger.info(f"\nStarting auction for {item.name}")
        logger.info(f"Starting price: ${item.starting_price:.2f}")
        logger.info(f"Minimum bids required: {min_bids}")
        logger.info(f"Number of bidders: {len(bidders)}")

        # Run the auction
        async with playground.play(workers=bidders) as active_playground:
            # Start the auction group
            await active_playground.assign_task_groups([auction_group])

            # Wait for completion
            completed_tasks = await active_playground.wait_and_get_completed_tasks()

            # Process results
            valid_bids = [
                Bid(**task.metadata['bid'])
                for task in completed_tasks.values()
                if task.completed and 'bid' in (task.metadata or {})
            ]

            if valid_bids:
                winning_bid = max(valid_bids, key=lambda x: x.amount)
                logger.info(f"\nAuction completed successfully!")
                logger.info(f"Winner: {winning_bid.bidder}")
                logger.info(f"Winning bid: ${winning_bid.amount:.2f}")
                return winning_bid
            else:
                logger.info("\nNo valid bids received")
                return None

    except Exception as e:
        logger.error(f"Error running auction: {e}")
        return None

async def main():
    # Setup test auction
    item = Item("Rare Painting", 1000.0)

    # Create bidders with different budgets
    bidders = [
        AuctionAgent("Alice", 1500.0),
        AuctionAgent("Bob", 1200.0),
        AuctionAgent("Charlie", 2000.0),
        AuctionAgent("David", 2800.0)
    ]

    # Run the auction
    winning_bid = await run_auction(
        item=item,
        bidders=bidders,
        min_bids=2  # Require at least 2 valid bids
    )

    if winning_bid:
        logger.info(f"Winner: {winning_bid.bidder}")
        logger.info(f"Winning bid: ${winning_bid.amount:.2f}")
        logger.info("Auction completed successfully!")
    else:
        logger.info("Auction failed to complete")

if __name__ == "__main__":
    asyncio.run(main())