class Agent:
    def __init__(self, role, responsibility, instructions):
        self.role = role
        self.responsibility = responsibility
        self.instructions = instructions


class Job:
    def __init__(self, instruction):
        self.instruction = instruction


class TaskForce:
    def __init__(self, name, description, agents, jobs):
        self.name = name
        self.description = description
        self.agents = agents
        self.jobs = jobs

    def execute(self, inputs):
        print(f"Executing TaskForce: {self.name}")
        print(f"Description: {self.description}")
        for agent in self.agents:
            print(f"Agent Role: {agent.role}")
            print(f"Responsibility: {agent.responsibility}")
            print(f"Instructions: {agent.instructions}")
        for job in self.jobs:
            print(f"Job Instruction: {job.instruction}")
        print(f"Topic: {inputs['topic']}")
        # Simulate the execution of the task force
        print("Researching on the topic...")
        print("Writing the article...")
