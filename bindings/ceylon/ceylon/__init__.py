#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).
#

from .ceylon import version
from .ceylon import AgentDetail, AdminAgentConfig, AdminAgent, WorkerAgentConfig, WorkerAgent, MessageHandler, \
    EventHandler, Processor
from .ceylon import enable_log

print(f"ceylon version: {version()}")
print(f"visit https://ceylon.ai for more information")
