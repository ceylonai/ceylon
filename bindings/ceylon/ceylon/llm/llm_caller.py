from langchain.agents import AgentExecutor
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.utils.function_calling import format_tool_to_openai_function


def process_agent_request(llm, inputs, agent_definition, tools=None):
    template = """
    **Role:** {role}
    **Responsibilities:** {responsibilities}
    **Instructions:** {instructions}
    **Task:**
    {task_info}
    """

    prompt = PromptTemplate(
        template=template,
        input_variables=["role", "responsibilities", "instructions", "task_info"]
    )

    formatted_inputs = {
        "role": agent_definition.position,
        "responsibilities": " ".join(agent_definition.responsibilities),
        "instructions": " ".join(agent_definition.instructions),
        "task_info": "\n".join(f"**{key.capitalize()}:** {value}" for key, value in inputs.items())
    }

    if tools:
        print(f"Using tools {tools} for {agent_definition.name}")
        llm = llm.bind(functions=[format_tool_to_openai_function(t) for t in tools])
        agent = prompt | llm | OpenAIFunctionsAgentOutputParser()
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        response = executor.invoke(formatted_inputs)
        return response["output"]
    else:
        print("Not using tools")
        agent = prompt | llm
        response = agent.invoke(formatted_inputs)
        return response.content
