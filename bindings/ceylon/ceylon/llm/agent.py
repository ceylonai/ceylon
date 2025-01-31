#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
from __future__ import annotations

from typing import TypeVar, Sequence

from pydantic import BaseModel

from ceylon import Worker
from ceylon.base.uni_agent import BaseAgentData

ResponseType = TypeVar("ResponseType")


class AgentRequest(BaseModel):
    input_data: str
    dependencies: Sequence[str]


class LLMAgentConfig(BaseModel):
    system_prompt: str | Sequence[str]
    response_type: type[ResponseType] | None


class LLMAgent(Worker):
    def __init__(
            self,
            name: str,
            role: str,
            system_prompt: str | Sequence[str] = (),
            response_type: type[ResponseType] = None
    ):
        super().__init__(name, role)
        self.config = LLMAgentConfig(
            system_prompt=system_prompt,
            response_type=response_type
        )
