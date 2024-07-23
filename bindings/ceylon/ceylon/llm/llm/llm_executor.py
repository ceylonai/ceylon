from typing import Any

import pydantic
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from ceylon.llm.prompt import PromptWrapper


class LLMExecutor(BaseModel):
    llm: Any = Field(
        default=None, description="Language model that will be used to execute the job"
    )
    type: str = Field(
        default="llm_executor", description="The type of the executor"
    )

    def execute(self, prompt_wrapper: PromptWrapper):
        prompt = prompt_wrapper.template
        if prompt_wrapper.parser is not None:
            try:
                prompt_and_model = prompt | self.llm | prompt_wrapper.parser
                output = prompt_and_model.invoke({
                    **prompt_wrapper.arguments,
                })
                return output
            except pydantic.ValidationError as e:
                print(f"Parsing error: {e}")
                # Handle the error appropriately
                return None  # or a default JobSteps object
        else:
            prompt_and_model = prompt | self.llm
            output = prompt_and_model.invoke({
                **prompt_wrapper.arguments,
            })
            return output.content

    def tool_calling(self, job):
        pass
