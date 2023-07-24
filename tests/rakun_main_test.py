import logging

import rakun

logging.basicConfig(level=logging.DEBUG)


class AgentBasic:

    def __init__(self, name):
        self.name = name

    async def __state__(self, state):
        logging.info(f"Agent:{self.name} State: {state}")

    async def __process__(self, message):
        pass

    async def background(self):
        pass

    async def process_message(self, message):
        pass


if __name__ == '__main__':
    agent_manager = rakun.AgentManager()
    agent_manager.register_agent(AgentBasic("AGENT1"))
    agent_manager.register_agent(AgentBasic("AGENT2"))
    agent_manager.start()
