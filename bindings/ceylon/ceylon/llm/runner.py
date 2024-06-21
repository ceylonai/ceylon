# import asyncio
# import pickle
# from typing import List, Dict
#
# from pydantic import BaseModel
#
# from ceylon.ceylon import Workspace, WorkspaceConfig, uniffi_set_event_loop, AgentCore, AgentDefinition
#
#
# class RunnerInput(BaseModel):
#     request: dict
#     agents: List[AgentDefinition]
#     network: Dict[str, List[str]]
#
#     class Config:
#         arbitrary_types_allowed = True
#
#
# class AgentRunnerError(Exception):
#     pass
#
#
# class AgentRunnerNotLeaderError(AgentRunnerError):
#     pass
#
#
# class AgentRunnerCannotHaveMultipleLeadersError(AgentRunnerError):
#     pass
#
#
# class AgentLLMRunner:
#     agents: List[AgentCore] = []
#     config: WorkspaceConfig
#     leader_agent = None
#
#     def __init__(self, workspace_name, workspace_host="/ip4/0.0.0.0/tcp", workspace_port=8888):
#         self.agents = []
#         self.config = WorkspaceConfig(name=workspace_name, host=workspace_host, port=workspace_port)
#
#     def register_agent(self, agent: AgentCore):
#         # Not accepting multiple leaders
#         if self.leader_agent is None and agent.definition().is_leader:
#             self.leader_agent = agent
#         elif agent.definition().is_leader and self.leader_agent is not None:
#             raise AgentRunnerCannotHaveMultipleLeadersError()
#         self.agents.append(agent)
#
#     async def run(self, request: dict[str, str], network: Dict[str, List[str]] = None):
#         # if self.leader_agent is None:
#         #     raise AgentRunnerNotLeaderError()
#         uniffi_set_event_loop(asyncio.get_event_loop())
#         workspace = Workspace(agents=self.agents, config=self.config)
#
#         input = RunnerInput(
#             request=request,
#             agents=[agent.definition() for agent in self.agents],
#             network=network,
#         )
#
#         await workspace.run(pickle.dumps(input))
#
#     def leader(self):
#         if self.leader_agent is None:
#             raise AgentRunnerNotLeaderError()
#         return self.leader_agent
