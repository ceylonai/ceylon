import asyncio
import logging

import orjson

logging.basicConfig(level=logging.INFO)
from rk_core import AgentManager, EventType, Event, Processor


#
class PlayerAgent:
    def __init__(self, name, symbol):
        self.name = name
        self.symbol = symbol

    @Processor(event_type=EventType.Data)
    async def get_game_board_status(self, event: Event):
        print(f"{self.name} received: {event.content}")


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
            self.publisher.publish(f"{board}")
            print("GameBoardAgent on_start")

    @Processor(event_type=EventType.OnShutdown)
    async def on_shutdown(self):
        print(f"EchoAgent Bye, world! {self.name}")

    # @Processor(event_type=EventType.Data)
    # async def update_board(self, event: Event):
    #     self.current_player, move = event.content
    #     x, y = move
    #     if self.board[x][y] == " ":
    #         self.board[x][y] = self.current_player.symbol
    #         if self.check_for_winner():
    #             print(f"{self.current_player.name} won!")
    #             await self.publisher.publish((self.current_player.name, "won"))
    #         else:
    #             print(f"{self.current_player.name} made a move at {move}.")
    #             await self.publisher.publish("next_turn")
    #     else:
    #         # Invalid move, ask the player to move again\
    #         print(f"{self.current_player.name} couldn't make a move. The game might be over.")
    #         await self.publisher.publish((self.current_player.name, "invalid_move"))
    #
    # def check_for_winner(self):
    #     # Check rows
    #     for i in range(3):
    #         if self.board[i][0] == self.board[i][1] == self.board[i][2] != " ":
    #             return True
    #     # Check columns
    #     for i in range(3):
    #         if self.board[0][i] == self.board[1][i] == self.board[2][i] != " ":
    #             return True
    #     # Check diagonals
    #     if self.board[0][0] == self.board[1][1] == self.board[2][2] != " " or \
    #             self.board[0][2] == self.board[1][1] == self.board[2][0] != " ":
    #         return True
    #
    #     # If no one has won yet, return False
    #     return False


if __name__ == "__main__":
    player1 = PlayerAgent("Player1", "X")
    player2 = PlayerAgent("Player2", "O")
    game_board = GameBoardAgent()

    agent_manager = AgentManager()
    agent_manager.register(player1, 1)
    agent_manager.register(player2, 2)
    agent_manager.register(game_board, 3)

    agent_manager.start()
