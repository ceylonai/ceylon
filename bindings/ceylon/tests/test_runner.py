import asyncio
import random
import time
import unittest

from ceylon import AgentRunner
from ceylon.ceylon import AgentCore, MessageHandler, Processor, AgentHandler, AgentDefinition, AgentConfig
from ceylon.runner import AgentRunnerNotLeaderError, AgentRunnerCannotHaveMultipleLeadersError


class Agent(AgentCore, MessageHandler, Processor, AgentHandler):
    def __init__(self, name, is_leader):
        super().__init__(
            definition=AgentDefinition(name=name, is_leader=is_leader, position="agent", responsibilities=[],
                                       instructions=[]),
            config=AgentConfig(memory_context_size=10),
            on_message=self,
            processor=self,
            agent_handler=self,
            event_handlers={},
            meta={}
        )

    async def on_message(self, agent_id, message):
        print(f"{self.name()} Received message from = '{agent_id}' message= {message}", agent_id, message)

    async def run(self, inputs):
        print(f"{self.name()} run", inputs)
        while True:
            await self.broadcast("Hi from " + self.name() + " at " + str(time.time()))
            print(f"{self.name()} Broadcast message")
            await asyncio.sleep(random.randint(1, 5))
            if random.randint(1, 10) % 5 == 0:
                break

    def on_agent(self, agent: "AgentDefinition"):
        print(f"{self.name()} on_agent {agent.name}")

    def on_start(self, input: "bytes"):
        print(f"{self.name()} on_start {input}")


class TestAgentRunner(unittest.IsolatedAsyncioTestCase):
    async def test_cannot_run_without_leader(self):
        runner = AgentRunner(workspace_name="ceylon-ai-test")
        runner.register_agent(Agent(name="ceylon-ai-1", is_leader=False))
        runner.register_agent(Agent(name="ceylon-ai-2", is_leader=False))
        runner.register_agent(Agent(name="ceylon-ai-3", is_leader=False))
        runner.register_agent(Agent(name="ceylon-ai-4", is_leader=False))

        with self.assertRaises(AgentRunnerNotLeaderError) as cm:
            await runner.run({})

    async def test_cannot_have_multiple_leaders(self):
        runner = AgentRunner(workspace_name="ceylon-ai-test")
        runner.register_agent(Agent(name="ceylon-ai-1", is_leader=True))

        with self.assertRaises(AgentRunnerCannotHaveMultipleLeadersError) as cm:
            runner.register_agent(Agent(name="ceylon-ai-2", is_leader=True))
