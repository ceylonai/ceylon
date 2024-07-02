import unittest
from unittest.mock import Mock, patch

from langchain_community.llms.ollama import Ollama

from ceylon.ceylon import AgentDefinition
from ceylon.llm.llm_caller import process_agent_request
from ceylon.tools.search_tool import SearchTool


class TestProcessAgentRequest(unittest.TestCase):

    def setUp(self):
        self.llm = Ollama(model="phi3:instruct")
        self.search_tool = SearchTool()
        self.tools = [self.search_tool]

    @patch('ceylon.llm.llm_caller.process_agent_request')
    def test_process_agent_request(self, mock_process_agent_request):
        # Arrange
        expected_result = "Mocked result of process_agent_request"
        mock_process_agent_request.return_value = expected_result

        inputs = {"task_info": "How LLM Work"}
        agent_definition = AgentDefinition(
            name="Agent 1",
            position="Content Publisher",
            responsibilities=[
                "Write content based on the given topic.",
                "Write content to file",
            ],
            instructions=[
                "Write given content in a clear and concise manner.",
            ],
            id="Agent 1"
        )

        # Act
        result = process_agent_request(
            self.llm,
            inputs=inputs,
            agent_definition=agent_definition,
            tools=self.tools
        )

        print(result)

    def test_ollama_initialization(self):
        # Arrange
        expected_model = "phi3:instruct"

        llm = Ollama(model=expected_model)

        # Assert
        self.assertEqual(llm.model, expected_model)
