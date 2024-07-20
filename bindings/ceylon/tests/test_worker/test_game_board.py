import asyncio
import pickle

from pydantic.dataclasses import dataclass

from ceylon.ceylon import WorkerAgent, MessageHandler, Processor, WorkerAgentConfig, enable_log
from ceylon.workspace.admin import Admin
from ceylon.workspace.runner import RunnerInput


class BoardAdmin(Admin):
    def __init__(self, name="admin", port=8888):
        super().__init__(name=name, port=port)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print(f"BoardAdmin on_message  {self.details().name}", agent_id, data, time)

    async def run(self, inputs: "bytes"):
        print(f"BoardAdmin run  {self.details().name}", inputs)


@dataclass
class GameBoard:
    grid: list

    def __str__(self):
        return str(self.grid)


def find_position(grid, item):
    for row_idx, row in enumerate(grid):
        for col_idx, cell in enumerate(row):
            if cell == item:
                return row_idx, col_idx
    return None


class SimpleAgent(WorkerAgent, MessageHandler, Processor):
    def __init__(self, name="admin", workspace_id="admin", admin_peer=None, admin_port=8888):
        super().__init__(config=WorkerAgentConfig(name=name,
                                                  admin_peer=admin_peer,
                                                  admin_port=admin_port,
                                                  work_space_id=workspace_id), processor=self, on_message=self)
        self.goal = None
        self.agent_position = None

    async def run(self, inputs: "bytes"):
        agent_def = self.details()
        input_request: RunnerInput = pickle.loads(inputs)
        game_board: GameBoard = input_request.request

        if not self.goal or not self.agent_position:
            self.goal = find_position(game_board.grid, 'G')
            self.agent_position = find_position(game_board.grid, 'A')

        await self.move(game_board)
        print(agent_def.name, game_board)

        await self.broadcast(pickle.dumps(game_board))

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        game_board: GameBoard = pickle.loads(data)
        print("Game board", game_board)

        await self.move(game_board)
        await self.broadcast(pickle.dumps(game_board))

    async def move(self, game_board):
        row, col = self.agent_position
        goal_row, goal_col = self.goal

        # Determine the direction to move
        if row < goal_row and game_board.grid[row + 1][col] != 1:
            new_position = (row + 1, col)
        elif row > goal_row and game_board.grid[row - 1][col] != 1:
            new_position = (row - 1, col)
        elif col < goal_col and game_board.grid[row][col + 1] != 1:
            new_position = (row, col + 1)
        elif col > goal_col and game_board.grid[row][col - 1] != 1:
            new_position = (row, col - 1)
        else:
            new_position = self.agent_position  # No move possible

        # Update the agent's position
        await self.update_position(game_board, new_position)

    async def update_position(self, game_board, new_position):
        old_row, old_col = self.agent_position
        new_row, new_col = new_position

        game_board.grid[old_row][old_col] = 0
        game_board.grid[new_row][new_col] = 'A'
        self.agent_position = new_position

        print(f"Agent {(self.details()).name} moved from ({old_row}, {old_col}) to ({new_row}, {new_col})")


async def run():
    admin = BoardAdmin(
        name="admin",
        port=8000
    )
    worker1 = SimpleAgent(
        name="worker1",
        admin_port=8000,
        admin_peer="admin",
        workspace_id="admin"
    )
    worker2 = SimpleAgent(
        name="worker2",
        admin_port=8000,
        admin_peer="admin",
        workspace_id="admin"
    )

    game_board = GameBoard(
        grid=[
            [0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0],
            [0, 0, 0, 1, 0],
            [0, 1, 0, 0, 0],
            ['A', 0, 0, 1, 'G']
        ]
    )

    await admin.run_admin(game_board, [
        worker1,
        worker2
    ])


if __name__ == '__main__':
    enable_log("INFO")
    asyncio.run(run())
