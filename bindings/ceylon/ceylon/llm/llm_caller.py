from langchain.agents import AgentExecutor
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.utils.function_calling import format_tool_to_openai_function


async def process_agent_request(llm, inputs, agent_definition, tools=[]):
    template = """
        **Role:** {role}
        **Responsibilities:** {responsibilities}
        **Instructions:** {instructions}
        **Task:**
        {task_info}
        """

    # Create a PromptTemplate instance
    prompt = PromptTemplate(template=template,
                            input_variables=["role", "responsibilities", "instructions", "task_info"])

    # Define a ToolChain to use the Retriever and Processor tools

    if tools is not None and len(tools) > 0:
        llm.bind(
            functions=[format_tool_to_openai_function(t) for t in tools],
        )
        agent = (
                prompt
                | llm
                | OpenAIFunctionsAgentOutputParser()
        )
        # Initialize the agent executor
        agent_executor = AgentExecutor(agent=agent,
                                       tools=tools if tools is not None else [],
                                       verbose=True)

        response = agent_executor.invoke({
            "role": agent_definition.position,
            "responsibilities": " ".join(agent_definition.responsibilities),
            "instructions": " ".join(agent_definition.instructions),
            "task_info": "\n".join(
                [f"**{key.capitalize()}:** {value}" for key, value in inputs.items()])
        })
        response = response.get("output")
    else:
        agent = (
                prompt
                | llm
        )
        response = agent.invoke(
            {
                "role": agent_definition.position,
                "responsibilities": " ".join(agent_definition.responsibilities),
                "instructions": " ".join(agent_definition.instructions),
                "task_info": "\n".join(
                    [f"**{key.capitalize()}:** {value}" for key, value in inputs.items()])
            }
        )
        response = response.content

    return response
