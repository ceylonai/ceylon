import os
from typing import Optional, Any, List

import toml
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field


class PromptWrapper(BaseModel):
    template: Any = Field(description="the prompt template")
    arguments: Any = Field(default={}, description="the kwargs of the prompt")
    parser: Any = Field(default=None, description="the parser of the prompt")

    def invoke(self):
        return self.template.format(**{**self.arguments})


class PromptMessage(BaseModel):
    paths: Optional[List[str]] = Field(
        default=[],
        description="the path to the prompt section",
    )

    def build(self, pydantic_object=None, **kwargs):
        prompt_toml = toml.load(os.path.join(os.path.dirname(__file__), "prompts.toml"))
        # path comes like this a.b.c
        # so we need to split it
        prompt = ""
        for path in self.paths:
            path = path.split(".")
            _prompt = prompt_toml
            for p in path:
                _prompt = _prompt[p]
            prompt = prompt + _prompt

        if pydantic_object is not None:
            parser = PydanticOutputParser(pydantic_object=pydantic_object)
            partial_variables = {"format_instructions": parser.get_format_instructions()}
            _prompt = PromptTemplate(template=prompt, partial_variables=partial_variables)
        else:
            parser = None
            _prompt = PromptTemplate(template=prompt)
        return PromptWrapper(template=_prompt, arguments=kwargs, parser=parser)
