from ceylon import *

print(version())

agent = Agent(
    id="test",
    name="test",
    workspace_id="1.0.0",
)

print(agent.name)
print(agent.id)
print(agent.workspace_id)
