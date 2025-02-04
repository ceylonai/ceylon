from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Optional

from loguru import logger
from pydantic import BaseModel

from ceylon import Admin, AgentDetail, on_connect, BaseAgent


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
        self._running = True

    async def finish(self) -> None:
        """Signal the playground to finish"""
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def force_close(self) -> None:
        """Force close all connections and cleanup"""
        logger.warning("Force closing playground...")
        self._running = False

        # Stop all LLM agents first
        for agent_status in self.llm_agents.values():
            try:
                if agent_status.connected:
                    logger.info(f"Stopping agent: {agent_status.agent.name}")
                    await asyncio.wait_for(self.broadcast_message({"type": "shutdown"}), timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout stopping agent: {agent_status.agent.name}")
            except Exception as e:
                logger.error(f"Error stopping agent {agent_status.agent.name}: {e}")

        # Cleanup events
        if self._stop_event:
            self._stop_event.set()

        # Stop self
        try:
            await asyncio.wait_for(self.stop(), timeout=3.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout during playground stop")
        except Exception as e:
            logger.error(f"Error during playground stop: {e}")

        logger.info("Playground force closed")

    @on_connect("*")
    async def on_llm_agent_connected(self, topic: str, agent: AgentDetail):
        self.llm_agents[agent.name] = AgentConnectedStatus(agent=agent, connected=True)
        if self._connected_event and all(status.connected for status in self.llm_agents.values()):
            self._connected_event.set()

    @asynccontextmanager
    async def play(self, workers: Optional[List[BaseAgent]] = None):
        """
        Async context manager for the playground that ensures all agents are connected before proceeding.
        Handles Ctrl+C for graceful shutdown.

        Args:
            workers: Optional list of BaseAgent instances to start

        Yields:
            BasePlayGround: The playground instance
        """
        from asyncio import Event

        # Initialize events
        self._connected_event = Event()
        self._stop_event = Event()
        self._running = True

        # Initialize agent statuses
        if workers:
            for agent in workers:
                self.llm_agents[agent.name] = AgentConnectedStatus(
                    agent=agent.details(),
                    connected=False
                )

        agent_task = None
        try:
            # Start the agent and wait for all connections
            agent_task = asyncio.create_task(self.start_agent(workers=workers))
            await asyncio.wait_for(self._connected_event.wait(), timeout=30.0)

            yield self

            # Normal completion - wait for stop event
            if self._running:
                await self._stop_event.wait()

        except asyncio.TimeoutError:
            logger.error("Timeout waiting for agents to connect")
            await self.force_close()
        except KeyboardInterrupt:
            logger.warning("Received Ctrl+C, initiating force close...")
            await self.force_close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error in playground: {e}")
            await self.force_close()
        finally:
            # Ensure everything is cleaned up
            try:
                if agent_task and not agent_task.done():
                    agent_task.cancel()
                    try:
                        await asyncio.wait_for(agent_task, timeout=2.0)
                    except (asyncio.TimeoutError, asyncio.CancelledError):
                        pass

                # Final cleanup
                self._connected_event = None
                self._stop_event = None
                self._running = False

            except Exception as e:
                logger.error(f"Error during final cleanup: {e}")
