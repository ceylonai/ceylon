import logging
from multiprocessing import allow_connection_pickling
from threading import Thread
from time import sleep

from rk_core.__agent_wrapper import AgentWrapper


class AgentManager:

    def __init__(self):
        self.agents = []

    def register(self, agent, order=0):
        """"
        Register an agent
        :param agent:
        :param order: Highest on start first
        """
        self.agents.append({
            "agent": AgentWrapper(agent),
            "order": order
        })

    def unregister(self, agent):
        self.agents = list(filter(lambda x: x["agent"].agent.name != agent.name, self.agents))

    def get_agents(self):
        return [x["agent"] for x in self.agents]

    def start(self):
        allow_connection_pickling()

        ordered_agents = reversed(sorted(self.agents, key=lambda x: x["order"]))
        ordered_agents = [x["agent"] for x in ordered_agents]

        agents_thread = []
        for agent in ordered_agents:
            logging.info(("Starting agent", agent.agent.name))
            t = Thread(target=agent.start)
            agents_thread.append(t)
            t.start()
            sleep(0.01)
        logging.info("Waiting for agents")
