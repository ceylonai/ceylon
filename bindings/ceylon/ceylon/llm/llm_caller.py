from langchain.agents import initialize_agent, AgentType
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import format_tool_to_openai_function

from ceylon.ceylon import AgentDefinition


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
        # agent = prompt | llm | OpenAIFunctionsAgentOutputParser()
        # executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        formatted_prompt = prompt.format(**formatted_inputs)

        agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )
        print(formatted_prompt)
        response = agent.run(formatted_prompt)
        return response
    else:
        print("Not using tools")
        agent = prompt | llm
        response = agent.invoke(formatted_inputs)
        return response.content


if __name__ == '__main__':
    from langchain_community.llms.ollama import Ollama
    from duckduckgo_search import DDGS


    def search_query(query: str):
        """
            Searches the given keywords on DuckDuckGo and returns the search results.
            Parameters:
            keywords (str): The keywords to search for. This should be a string containing the search terms.

            Returns:
            list: A list of dictionaries, where each dictionary contains the following keys:
                - title (str): The title of the search result.
                - href (str): The URL of the search result.
                - body (str): A brief description of the search result.
       """
        print(f"Searching for {query}")
        results = DDGS().text(query, safesearch='off', timelimit='y', max_results=10)
        return results


    # Initialize Ollama
    llm = Ollama(model="llama3")

    # Load tools
    tools = [
        StructuredTool.from_function(search_query, name="Search",
                                     description="Useful for searching the web for current information.")
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
