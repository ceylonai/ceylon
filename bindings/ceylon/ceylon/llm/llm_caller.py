from langchain.agents import initialize_agent, AgentType
from langchain_core.prompts import PromptTemplate
from langchain_core.utils.function_calling import format_tool_to_openai_function

from ceylon.ceylon import AgentDefinition
from ceylon.tools.search_tool import SearchTool


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
        llm = llm.bind(functions=[format_tool_to_openai_function(t) for t in tools])
        formatted_prompt = prompt.format(**formatted_inputs)

        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )
        response = agent.run(formatted_prompt)
        print(response)
        return response
    else:
        print("Not using tools")
        agent = prompt | llm
        response = agent.invoke(formatted_inputs)
        return response.content


if __name__ == '__main__':
    from langchain_community.llms.ollama import Ollama

    # Initialize Ollama
    llm = Ollama(model="llama3:instruct")

    # Load tools
    tools = [
        SearchTool(),
    ]

    res = process_agent_request(llm,
                                inputs={"task_info": "How LLM Work"},
                                agent_definition=AgentDefinition(
                                    name="Agent 1",
                                    position="Content Researcher",
                                    responsibilities=[
                                        "Conducting thorough and accurate research to support content creation.",

                                    ],
                                    instructions=[
                                        "Must only Find the most relevant 2 or 3 sources."
                                        "Find credible sources, verify information,"
                                        " and provide comprehensive and relevant "
                                        "data while ensuring ethical "
                                        "standards and privacy are maintained.",
                                        "Must  summarize output without source references."
                                    ],
                                    id="Agent 1"
                                ), tools=tools)
    print(res)
