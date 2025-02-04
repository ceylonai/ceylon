# Building a Distributed Auction System with Ceylon Playground

This tutorial demonstrates how to build a distributed auction system using Ceylon's TaskPlayGround functionality. The system implements a multi-agent auction where bidders compete for items using random bidding strategies.

## System Architecture

````mermaid
graph TB
    subgraph Playground[Auction Playground]
        TM[Task Manager]
        AG[Auction Group]
        GT[Goal Tracker]
    end

    subgraph Agents[Auction Agents]
        B1[Bidder 1]
        B2[Bidder 2]
        B3[Bidder 3]
    end

    subgraph Tasks[Auction Tasks]
        T1[Bid Task 1]
        T2[Bid Task 2]
        T3[Bid Task 3]
    end

    TM --> AG
    AG --> GT
    AG --> |Assigns| T1
    AG --> |Assigns| T2
    AG --> |Assigns| T3
    T1 --> |Executed by| B1
    T2 --> |Executed by| B2
    T3 --> |Executed by| B3
    GT --> |Monitors| T1
    GT --> |Monitors| T2
    GT --> |Monitors| T3
````

## Core Components

### 1. Data Models

First, let's define our core data structures:

```python
@dataclass
class Item:
    name: str
    starting_price: float

@dataclass
class Bid:
    bidder: str
    amount: float
    item_id: str
```

### 2. Auction Agent

The AuctionAgent class represents each bidder in the system:

```python
class AuctionAgent(TaskExecutionAgent):
    def __init__(self, name: str, budget: float, max_concurrent_tasks: int = 1):
        super().__init__(
            name=name,
            worker_role="bidder",
            max_concurrent_tasks=max_concurrent_tasks
        )
        self.budget = budget
        self.bids: Dict[str, Bid] = {}
```

Key features:
- Inherits from TaskExecutionAgent for task management
- Maintains a budget for bidding
- Tracks bid history
- Implements random bidding strategy

### 3. Auction Setup

The setup_auction function configures the playground and creates tasks:

```python
async def setup_auction(
    item: Item,
    bidders: List[AuctionAgent],
    min_bids: int
) -> TaskPlayGround:
    playground = TaskPlayGround(name="auction_system")
    
    # Create auction tasks
    auction_tasks = [
        TaskMessage(
            task_id=f"bid_{bidder.name}_{item.name}",
            name=f"Place bid for {item.name}",
            description=f"Submit bid for {item.name}",
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
    
    # Create task group
    auction_group = TaskManager.create_task_group(...)
    
    return playground, auction_group
```

## Implementation Steps

### 1. Initialize the System

```python
# Create auction item
item = Item("Rare Painting", 1000.0)

# Create bidders with budgets
bidders = [
    AuctionAgent("Alice", 1500.0),
    AuctionAgent("Bob", 1200.0),
    AuctionAgent("Charlie", 2000.0)
]
```

### 2. Configure Bidding Strategy

The random bidding strategy uses two factors:
```python
# Random multiplier (1.0 to 2.0) for starting price
random_multiplier = 1.0 + random.random()

# Random percentage of remaining budget
budget_percentage = random.random()

# Calculate final bid
base_bid = item.starting_price * random_multiplier
budget_portion = (self.budget - base_bid) * budget_percentage
bid_amount = min(self.budget, base_bid + budget_portion)
```

### 3. Run the Auction

```python
async def run_auction(
    item: Item,
    bidders: List[AuctionAgent],
    min_bids: int
) -> Optional[Bid]:
    
    # Setup system
    playground, auction_group = await setup_auction(item, bidders, min_bids)
    
    # Run auction
    async with playground.play(workers=bidders) as active_playground:
        await active_playground.assign_task_groups([auction_group])
        completed_tasks = await active_playground.wait_and_get_completed_tasks()
        
        # Process results
        valid_bids = [
            Bid(**task.metadata['bid'])
            for task in completed_tasks.values()
            if task.completed and 'bid' in (task.metadata or {})
        ]
        
        # Determine winner
        if valid_bids:
            return max(valid_bids, key=lambda x: x.amount)
    return None
```

## Monitoring and Control

### 1. Goal Tracking

The system uses a goal checker to monitor bid progress:
```python
def check_bid_count(task_groups: dict, completed_tasks: dict) -> bool:
    bid_count = sum(
        1 for task in completed_tasks.values()
        if task.completed and 'bid' in (task.metadata or {})
    )
    return bid_count >= min_bids
```

### 2. Task Status Updates

Monitor task completion and results:
```python
completed_tasks = await active_playground.wait_and_get_completed_tasks()
task_results = active_playground.get_task_results()
```

## Error Handling

The system includes comprehensive error handling:

1. **Task Level**:
```python
try:
    # Process auction task
    task.completed = True
except Exception as e:
    task.completed = False
    task.metadata['error'] = str(e)
```

2. **Auction Level**:
```python
try:
    # Run auction
    async with playground.play(workers=bidders) as active_playground:
        # ... auction logic ...
except Exception as e:
    logger.error(f"Error running auction: {e}")
    return None
```

## Running the System

Complete example of running an auction:

```python
async def main():
    # Setup auction
    item = Item("Rare Painting", 1000.0)
    bidders = [
        AuctionAgent("Alice", 1500.0),
        AuctionAgent("Bob", 1200.0),
        AuctionAgent("Charlie", 2000.0),
        AuctionAgent("David", 2800.0)
    ]
    
    # Run auction
    winning_bid = await run_auction(
        item=item,
        bidders=bidders,
        min_bids=2
    )
    
    # Process results
    if winning_bid:
        logger.info(f"Winner: {winning_bid.bidder}")
        logger.info(f"Amount: ${winning_bid.amount:.2f}")
    else:
        logger.info("Auction failed to complete")

if __name__ == "__main__":
    asyncio.run(main())
```

## System Flow

````mermaid
sequenceDiagram
    participant M as Main
    participant P as Playground
    participant TM as TaskManager
    participant B as Bidders
    
    M->>P: Create Playground
    M->>TM: Create Task Group
    
    loop For each bidder
        TM->>B: Assign Bid Task
        B->>TM: Submit Bid
    end
    
    TM->>P: Check Goal Progress
    
    alt Enough Bids
        P->>M: Return Results
    else Timeout/Failure
        P->>M: Return None
    end
````

## Customization Options

1. **Bidding Strategy**
    - Modify random factors
    - Implement different bidding algorithms
    - Add bid increment rules

2. **Auction Rules**
    - Change minimum bid requirements
    - Add time limits
    - Implement reserve prices

3. **Task Configuration**
    - Adjust task duration
    - Modify concurrent task limits
    - Add task dependencies

## Best Practices

1. **Error Handling**
    - Always include try-except blocks
    - Log errors with context
    - Implement cleanup in finally blocks

2. **Resource Management**
    - Use async context managers
    - Clean up resources properly
    - Monitor system resources

3. **Monitoring**
    - Log important events
    - Track task progress
    - Monitor system health

## Example Output

```
2025-01-26 10:15:30 | INFO | Starting auction for Rare Painting
2025-01-26 10:15:30 | INFO | Starting price: $1000.00
2025-01-26 10:15:30 | INFO | Minimum bids required: 2
2025-01-26 10:15:30 | INFO | Number of bidders: 4

2025-01-26 10:15:31 | INFO | Alice placed bid: $1432.50
2025-01-26 10:15:31 | INFO | Bob placed bid: $1150.75
2025-01-26 10:15:31 | INFO | Charlie placed bid: $1875.25
2025-01-26 10:15:31 | INFO | David placed bid: $2234.80

2025-01-26 10:15:32 | INFO | Auction completed successfully!
2025-01-26 10:15:32 | INFO | Winner: David
2025-01-26 10:15:32 | INFO | Winning bid: $2234.80
```

## Conclusion

This tutorial demonstrated building a distributed auction system using Ceylon's TaskPlayGround. The system provides:
- Scalable multi-agent architecture
- Random bidding strategies
- Comprehensive monitoring
- Robust error handling
- Flexible customization options

For more information, visit the Ceylon documentation at [https://docs.ceylon.ai](https://docs.ceylon.ai)