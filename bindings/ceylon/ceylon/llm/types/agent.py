from typing import List

from pydantic import BaseModel, PrivateAttr, Field

from ceylon.llm.prompt import PromptMessage


class AgentDefinition(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    name: str = Field(description="the name of the agent")
    role: str = Field(description="the role of the agent")
    objective: str = Field(description="the objective of the agent")
    context: str = Field(description="the context of the agent")
    tools: str = Field(description="the tools of the agent", default="")

    _prompt: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.agent"),
    )

    @property
    def intro(self):
        return {
            "name": self.name,
            "role": self.role,
            "objective": self.objective,
            "context": self.context
        }

    @property
    def prompt(self):
        return self._prompt.build(**self.intro)
