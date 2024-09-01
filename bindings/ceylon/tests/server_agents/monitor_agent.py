import asyncio
import pickle
from datetime import datetime

import socketio
from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from ceylon import Agent
from ceylon.ceylon import enable_log

app = FastAPI()
origins = ["*"]
app.add_middleware(CORSMiddleware,
                   allow_origins=origins,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

sio_asgi_app = socketio.ASGIApp(socketio_server=sio, other_asgi_app=app)


class Message(BaseModel):
    message: str = Field(min_length=1, max_length=100)
    sender: str = Field(min_length=1, max_length=100)
    time: datetime = Field(default_factory=datetime.now)
    type: str = Field(min_length=1, max_length=100)


class TaskMonitorAgent(Agent):

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        logger.info(f"Monitor Agent Got message: {data}")

    async def run(self, inputs: "bytes"):
        @app.get("/")
        async def read_root():
            return {"message": "Hello World"}

        @app.post("/api/chat")
        async def send_message(message: Message):
            await self.broadcast_data(message)
            logger.info(f"Sent message: {message}")

        # Example Socket.IO event handler
        @sio.event
        async def connect(sid, environ):
            pass

        @sio.event
        async def disconnect(sid):
            logger.debug(f"Client disconnected: {sid}")

            # Start the Socket.IO server

        config = Config(app=sio_asgi_app, host="0.0.0.0", port=7878, log_level="error")
        server = Server(config)
        await server.serve()


task_monitor = TaskMonitorAgent(name="worker_2",
                                role="server_admin",
                                admin_port=8888,
                                workspace_id="ceylon_agent_stack",
                                admin_ip="23.94.182.52",
                                admin_peer="12D3KooWEUH7vcsHUQ72xfExPZLHawWiYZrybZL5Hj9t6RvkcHpX")

enable_log("INFO")
asyncio.run(task_monitor.arun_worker(pickle.dumps({})))
