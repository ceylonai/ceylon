from ceylon.auto.manager.agent_taskmanager import AgentTaskManager
from ceylon.auto.worker.agent_executor import TaskExecutorAgent

workspace_id = "ceylon-stm-task-manager"
agent_mgt = AgentTaskManager(name=workspace_id, )

agent_mgt.register_agent(TaskExecutorAgent(
    workspace_id=workspace_id,
    name="executor_agent1",
    role="executor_1",
))
agent_mgt.register_agent(TaskExecutorAgent(
    workspace_id=workspace_id,
    name="executor_agent2",
    role="executor_2",
))
agent_mgt.register_agent(TaskExecutorAgent(
    workspace_id=workspace_id,
    name="executor_agent3",
    role="executor_3",
))

agent_mgt.do()
