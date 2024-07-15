import asyncio
import pickle

from ceylon.ceylon import AdminAgent, AdminAgentConfig, enable_log


class Admin(AdminAgent):

    def __init__(self, name="admin", port=8888):
        super().__init__(config=AdminAgentConfig(name=name, port=port))

