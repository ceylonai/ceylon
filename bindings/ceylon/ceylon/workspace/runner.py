from typing import Any, List, Dict

from pydantic import BaseModel

from ceylon.ceylon import AgentDetail


class RunnerInput(BaseModel):
    request: Any

    class Config:
        arbitrary_types_allowed = True
