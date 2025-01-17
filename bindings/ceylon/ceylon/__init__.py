from .ceylon import version
from .ceylon import AgentDetail, AdminAgentConfig, AdminAgent, WorkerAgentConfig, WorkerAgent, MessageHandler, \
    EventHandler, Processor
from .ceylon import enable_log

print(f"ceylon version: {version()}")
print(f"visit https://ceylon.ai for more information")
