#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
#

from .ceylon import version
from .ceylon import AgentDetail, MessageHandler, \
    EventHandler, Processor, UnifiedAgent, UnifiedAgentConfig, PeerMode
from .ceylon import enable_log
from .base.agents import Admin, Worker
from .base.uni_agent import BaseAgent
from .base.support import AgentCommon, on, on_run, on_connect
from .static_val import *

print(f"ceylon version: {version()}")
print(f"visit https://ceylon.ai for more information")
