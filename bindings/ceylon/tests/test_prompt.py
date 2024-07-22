from unittest import TestCase

from ceylon.llm.prompt import PromptMessage


class TestPromptMessage(TestCase):
    def test_build(self):
        prompt = PromptMessage(path="prompts.agent")
        prompt_txt = prompt.build(name="test", role="test-role", objective="test-objective", context="test-context")
        print(prompt_txt)
