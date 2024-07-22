import os
from typing import Optional

import toml
from pydantic import BaseModel, Field


class PromptMessage(BaseModel):
    path: Optional[str] = Field(
        default=None,
        description="the path to the prompt section",
    )

    def build(self, **kwargs):
        prompt_toml = toml.load(os.path.join(os.path.dirname(__file__), "prompts.toml"))
        # path comes like this a.b.c
        # so we need to split it
        path = self.path.split(".")
        _prompt = prompt_toml
        for p in path:
            _prompt = _prompt[p]
        return _prompt.format(**kwargs)
