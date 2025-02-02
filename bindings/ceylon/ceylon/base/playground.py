from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from loguru import logger
from pydantic import BaseModel

from ceylon import Admin, AgentDetail, on_connect, BaseAgent


@dataclass
class TaskOutput:
    task_id: str
    name: str
    completed: bool
    start_time: Optional[float]
    end_time: Optional[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class AgentConnectedStatus(BaseModel):
    agent: AgentDetail
    connected: bool

    class Config:
        arbitrary_types_allowed = True


class BasePlayGround(Admin):
    def __init__(self, name="playground", port=8888):
        super().__init__(name=name, port=port, role="playground")
        self.llm_agents: Dict[str, AgentConnectedStatus] = {}
        self._connected_event = None
        self._stop_event = None
        self._all_tasks_completed_events: Dict[str, asyncio.Event] = {}
        self._completed_tasks: Dict[str, TaskOutput] = {}
        self._task_results: Dict[str, Any] = {}

    async def finish(self) -> None:
        if self._stop_event:
            self._stop_event.set()

    def add_completed_task(self, task_id: str, task_output: TaskOutput) -> None:
        """Add a completed task to the output collection"""
        self._completed_tasks[task_id] = task_output

    def add_task_result(self, task_id: str, result: Any) -> None:
        """Add a task result to the results collection"""
        self._task_results[task_id] = result

    def get_completed_tasks(self) -> Dict[str, TaskOutput]:
        """Get all completed tasks"""
        return self._completed_tasks.copy()

    async def wait_and_get_completed_tasks(self) -> Dict[str, TaskOutput]:
        for event in self._all_tasks_completed_events.values():
            await event.wait()
        return self.get_completed_tasks()

    def get_task_results(self) -> Dict[str, Any]:
        """Get all task results"""
        return self._task_results.copy()

    @on_connect("*")
    async def on_llm_agent_connected(self, topic: str, agent: AgentDetail):
        self.llm_agents[agent.name] = AgentConnectedStatus(agent=agent, connected=True)
        if self._connected_event and all(status.connected for status in self.llm_agents.values()):
            self._connected_event.set()

    @asynccontextmanager
    async def play(self, workers: Optional[List[BaseAgent]] = None):
        """
        Async context manager for the playground that ensures all agents are connected before proceeding.
        Returns completed task information when finished.

        Args:
            workers: Optional list of BaseAgent instances to start

        Yields:
            tuple[BasePlayGround, Dict[str, TaskOutput]]: The playground instance and completed tasks
        """
        from asyncio import Event

        # Initialize events and collections
        self._connected_event = Event()
        self._stop_event = Event()
        self._completed_tasks.clear()
        self._task_results.clear()

        # Initialize agent statuses
        if workers:
            for agent in workers:
                self.llm_agents[agent.name] = AgentConnectedStatus(
                    agent=agent.details(),
                    connected=False
                )

        try:
            # Start the agent and wait for all connections
            asyncio.create_task(self.start_agent(workers=workers))
            await self._connected_event.wait()

            yield self

        finally:
            # Wait for stop event and cleanup
            await self._stop_event.wait()

            # Log completion statistics
            logger.info(f"Playground finished with {len(self._completed_tasks)} completed tasks")
            for task_id, output in self._completed_tasks.items():
                if output.completed:
                    duration = output.end_time - output.start_time if output.end_time and output.start_time else None
                    logger.info(
                        f"Task {task_id} ({output.name}) completed in {duration:.2f}s" if duration else f"Task {task_id} ({output.name}) completed")
                else:
                    logger.warning(f"Task {task_id} ({output.name}) failed: {output.error}")

            # Cleanup
            self._connected_event = None
            self._stop_event = None
            await self.stop()
