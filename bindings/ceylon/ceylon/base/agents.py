#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
#

from typing import Optional

from ceylon import PeerMode
from ceylon.base.uni_agent import BaseAgent


class Admin(BaseAgent):

    def __init__(self, name: str, port: Optional[int] = None,
                 admin_peer: Optional[str] = None, admin_ip: Optional[str] = None, workspace_id: str = "default",
                 buffer_size: int = 1024, config_path: Optional[str] = None, role: str = "admin",
                 extra_data: Optional[bytes] = None):
        super().__init__(name, PeerMode.ADMIN, role, port, admin_peer, admin_ip, workspace_id, buffer_size,
                         config_path, extra_data=extra_data)


class Worker(BaseAgent):

    def __init__(self, name: str, role: str = "default", port: Optional[int] = None,
                 admin_peer: Optional[str] = None, admin_ip: Optional[str] = None, workspace_id: str = "default",
                 buffer_size: int = 1024, config_path: Optional[str] = None):
        super().__init__(name, PeerMode.CLIENT, role, port, admin_peer, admin_ip, workspace_id, buffer_size,
                         config_path)
