import asyncio
import logging

import orjson

logging.basicConfig(level=logging.INFO)
from rk_core import AgentManager, EventType, Event, Processor


class GameState:
    def __init__(self):
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.current_player = None

    def switch_player(self, player1, player2):
        if self.current_player is None:
            self.current_player = player1
        elif self.current_player == player1:
            self.current_player = player2
        else:
            self.current_player = player1

    def make_move(self, x, y):
        if self.board[x][y] == " " and self.current_player is not None:
            self.board[x][y] = self.current_player.symbol
            return True
        else:
            return False

    def is_game_over(self):
        for row in self.board:
            if row[0] != " " and row[0] == row[1] and row[0] == row[2]:
                return True
        for col in range(3):
            if self.board[0][col] != " " and self.board[0][col] == self.board[1][col] and self.board[0][col] == \
                    self.board[2][col]:
                return True
        if self.board[0][0] != " " and self.board[0][0] == self.board[1][1] and self.board[0][0] == self.board[2][2]:
            return True
        if self.board[0][2] != " " and self.board[0][2] == self.board[1][1] and self.board[0][2] == self.board[2][0]:
            return True
        return False


#
class PlayerAgent:
    def __init__(self, name, symbol):
        self.name = name
        self.symbol = symbol

    @Processor(event_type=EventType.Data)
    async def get_game_board_status(self, event: Event):
        board = orjson.loads(bytearray(event.content))
        print(f"{self.name} received: {board}")


class GameBoardAgent:
    def __init__(self):
        self.name = "GameBoardAgent"
        self.board = [[" " for _ in range(3)] for _ in range(3)]
        self.current_player = None
        print("GameBoardAgent created.")

    @Processor(event_type=EventType.OnBoot)
    async def on_start(self):
        while True:
            await asyncio.sleep(1)
            board = orjson.dumps(self.board)
            print(f"{self.name} board: {board}")
            self.publisher.publish(board)
            print("GameBoardAgent on_start")

    @Processor(event_type=EventType.OnShutdown)
    async def on_shutdown(self):
        print(f"EchoAgent Bye, world! {self.name}")


if __name__ == "__main__":
    player1 = PlayerAgent("Player1", "X")
    player2 = PlayerAgent("Player2", "O")
    game_board = GameBoardAgent()

    agent_manager = AgentManager()
    agent_manager.register(player1, 1)
    agent_manager.register(player2, 2)
    agent_manager.register(game_board, 3)

    agent_manager.start()
