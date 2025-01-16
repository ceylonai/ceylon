from copy import copy as shallow_copy
from typing import Any

import langchain_core
import pydantic
from langchain.agents import AgentExecutor
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.utils.function_calling import format_tool_to_openai_function
from pydantic import BaseModel, Field

from ceylon.llm.prompt import PromptWrapper


class LLMExecutor(BaseModel):
    llm: Any = Field(
        default=None, description="Language model that will be used to execute the job"
    )
    type: str = Field(
        default="llm_executor", description="The type of the executor"
    )

    def execute(self, prompt_wrapper: PromptWrapper, tools: list = []):

        if tools and len(tools) > 0:
            execution_llm = shallow_copy(self.llm).bind(
                functions=[langchain_core.utils.function_calling.convert_to_openai_function(t) for t in tools]
            )
            # return self.tool_calling(prompt_wrapper, tools)
        else:
            execution_llm = shallow_copy(self.llm)

        prompt = prompt_wrapper.template
        if prompt_wrapper.parser is not None:
            try:
                prompt_and_model = prompt | execution_llm | prompt_wrapper.parser
                output = prompt_and_model.invoke({
                    **prompt_wrapper.arguments,
                })
                return output
            except pydantic.ValidationError as e:
                print(f"Parsing error: {e}")
                # Handle the error appropriately
                return None  # or a default JobSteps object
        else:
            prompt_and_model = prompt | execution_llm
            output = prompt_and_model.invoke({
                **prompt_wrapper.arguments,
            })
            return output.content

    def tool_calling(self, prompt_wrapper: PromptWrapper, tools: list):
        prompt = prompt_wrapper.template
        execution_llm = shallow_copy(self.llm)
        llm = execution_llm.bind(
            functions=[langchain_core.utils.function_calling.convert_to_openai_function(t) for t in tools])
        agent = prompt | llm | OpenAIFunctionsAgentOutputParser()
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10,
                                 return_intermediate_steps=True)
        llm_response = executor.invoke({**prompt_wrapper.arguments, })
        return llm_response["output"]
