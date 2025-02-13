#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
#

import asyncio
import pickle
import time
import traceback
from statistics import mean, median
from typing import Dict

from loguru import logger

from ceylon import AgentDetail
from ceylon import PeerMode
from ceylon.base.uni_agent import BaseAgent
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_CONF_FILE, DEFAULT_WORKSPACE_PORT, DEFAULT_WORKSPACE_IP


class PerformanceMetrics:
    def __init__(self):
        self.message_latencies = []
        self.messages_per_second = []
        self.total_messages = 0
        self.start_time = time.time()

    def add_latency(self, latency: float):
        self.message_latencies.append(latency)

    def update_message_rate(self):
        elapsed = time.time() - self.start_time
        self.messages_per_second.append(self.total_messages / elapsed)

    def get_stats(self) -> dict:
        if not self.message_latencies:
            return {}

        return {
            "avg_latency_ms": mean(self.message_latencies) * 1000,
            "median_latency_ms": median(self.message_latencies) * 1000,
            "msgs_per_second": mean(self.messages_per_second),
            "total_messages": self.total_messages
        }


class NetworkManager(BaseAgent):
    def __init__(self, name="admin", port=8888):
        super().__init__(name=name, port=port, mode=PeerMode.ADMIN, role="network_manager")
        self.metrics = PerformanceMetrics()
        self.message_timestamps: Dict[str, float] = {}

    async def on_agent_connected(self, topic: str, agent: AgentDetail):
        await super().on_agent_connected(topic, agent)
        logger.info(f"Network Manager: New agent connected - {agent.name} ({agent.id})")

        # Start performance test
        test_msg = {
            "type": "perf_test",
            "timestamp": time.time(),
            "message_id": f"test_{self.metrics.total_messages}"
        }
        self.message_timestamps[test_msg["message_id"]] = test_msg["timestamp"]
        await self.send_message(agent.id, test_msg)

    async def on_message(self, agent: AgentDetail, data: bytes, time_: int):
        try:
            message = pickle.loads(data)
            current_time = time.time()

            if isinstance(message, dict):
                if message.get("type") == "perf_response":
                    # Calculate round-trip time
                    msg_id = message.get("original_message_id")
                    if msg_id in self.message_timestamps:
                        start_time = self.message_timestamps.pop(msg_id)
                        latency = current_time - start_time
                        self.metrics.add_latency(latency)
                        self.metrics.total_messages += 1
                        self.metrics.update_message_rate()

                        # Send next test message immediately
                        next_msg = {
                            "type": "perf_test",
                            "timestamp": current_time,
                            "message_id": f"test_{self.metrics.total_messages}"
                        }
                        self.message_timestamps[next_msg["message_id"]] = current_time
                        await self.send_message(agent.id, next_msg)

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error processing message: {e}")

    async def run(self, inputs: bytes):
        logger.info(f"Network Manager started - {self.details().name} ({self.details().id})")
        while True:
            stats = self.metrics.get_stats()
            if stats:
                logger.info(f"Performance Stats: {stats}")
            await asyncio.sleep(1)


class WorkingAgent(BaseAgent):
    def __init__(self, name="worker",
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 conf_file=DEFAULT_CONF_FILE,
                 admin_peer="",
                 admin_port=DEFAULT_WORKSPACE_PORT,
                 role="worker",
                 admin_ip=DEFAULT_WORKSPACE_IP):
        super().__init__(name=name,
                         role=role,
                         mode=PeerMode.CLIENT,
                         )
        self.messages_processed = 0
        self.start_time = time.time()

    async def on_message(self, agent: AgentDetail, data: bytes, time_: int):
        try:
            message = pickle.loads(data)

            if isinstance(message, dict) and message.get("type") == "perf_test":
                # Immediately respond to performance test messages
                response = {
                    "type": "perf_response",
                    "original_message_id": message["message_id"],
                    "worker_name": self.details().name,
                    "processed_time": time.time()
                }
                await self.send_message(agent.id, response)

                self.messages_processed += 1
                elapsed = time.time() - self.start_time
                if self.messages_processed % 100 == 0:
                    logger.info(f"Worker {self.details().name} processing rate: "
                                f"{self.messages_processed / elapsed:.2f} msgs/sec")

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error processing message: {e}")

    async def run(self, inputs: bytes):
        logger.info(f"Worker started - {self.details().name} ({self.details().id})")
        while True:
            await asyncio.sleep(60)


async def main():
    # Create network manager (admin)
    network_manager = NetworkManager()

    # Create worker agents
    worker_names = [f"Agent {i}" for i in range(1, 5)]  # Added more agents for better testing
    workers = []

    admin_details = network_manager.details()

    for name in worker_names:
        worker = WorkingAgent(
            name=name,
            admin_peer=admin_details.id
        )
        workers.append(worker)

    try:
        logger.info("Starting performance test...")
        await network_manager.start_agent(b"", workers)
    except KeyboardInterrupt:
        # Print final statistics
        final_stats = network_manager.metrics.get_stats()
        logger.info("Final Performance Statistics:")
        for metric, value in final_stats.items():
            logger.info(f"{metric}: {value:.2f}")
        logger.info("Shutting down...")
    finally:
        # Cleanup code here if needed
        pass


if __name__ == "__main__":
    logger.info("Starting network performance test...")
    asyncio.run(main())
