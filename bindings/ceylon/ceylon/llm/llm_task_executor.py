from langchain.agents import AgentExecutor
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.utils.function_calling import format_tool_to_openai_function


def execute_llm_with_function_calling(llm, prompt, tools):
    llm = llm.bind(functions=[format_tool_to_openai_function(t) for t in tools])
    agent = prompt | llm | OpenAIFunctionsAgentOutputParser()
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    llm_response = executor.invoke({})
    return llm_response["output"]


def execute_llm(llm, prompt):
    agent = prompt | llm
    response = agent.invoke({})
    return response.content


def execute_llm_with_json_out(llm, prompt, dict_schema):
    structured_llm = llm.with_structured_output(dict_schema, include_raw=True)
    response = structured_llm.invoke(prompt)
    return response["parsed"]
