# 🚦 Getting Started

This guide will help you get started with Ceylon by walking you through the creation of a simple multi-agent system. We'll build an example where agents collaborate to schedule a meeting based on participants' availability.

### Step 1: Install Ceylon

First, you'll need to install the Ceylon framework. You can do this via pip:

```bash
pip install ceylon
```

### Step 2: Define Your Agents

In this example, we'll create three agents:

1. **AvailabilityAgent**: Checks the availability of participants.
2. **SchedulerAgent**: Proposes possible meeting times based on availability.
3. **NotifierAgent**: Notifies participants about the scheduled meeting.

Here's how you can define these agents:

```python
from ceylon import Agent, AgentJobStepRequest, AgentJobResponse, JobRequest, JobSteps, Step, RunnerAgent

class AvailabilityAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        # Simulate checking participant availability
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"available_times": ["10:00 AM", "2:00 PM", "4:00 PM"]}
        )

class SchedulerAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        available_times = request.job_data["available_times"]
        # Simulate selecting the best time (e.g., the first available slot)
        best_time = available_times[0]
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"scheduled_time": best_time}
        )

class NotifierAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        scheduled_time = request.job_data["scheduled_time"]
        # Simulate notifying participants
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"notification": f"Meeting scheduled at {scheduled_time}"}
        )
```

### Step 3: Create a Runner Agent

The RunnerAgent will orchestrate the execution of the job. We need to create instances of our agents and then define the sequence in which they will be executed.

```python
# Create agent instances
availability_agent = AvailabilityAgent(name="availability", role="Check Availability")
scheduler_agent = SchedulerAgent(name="scheduler", role="Schedule Meeting")
notifier_agent = NotifierAgent(name="notifier", role="Notify Participants")

# Create the runner agent
chief = RunnerAgent(workers=[availability_agent, scheduler_agent, notifier_agent])
```

### Step 4: Define the Job

Next, we'll define the job that these agents will execute. The job consists of multiple steps, each handled by a different agent.

```python
# Define the job
job = JobRequest(
    title="Meeting Scheduler",
    explanation="Schedule a meeting based on participant availability",
    steps=JobSteps(steps=[
        Step(worker="availability", explanation="Check participant availability", dependencies=[]),
        Step(worker="scheduler", explanation="Schedule the meeting", dependencies=["availability"]),
        Step(worker="notifier", explanation="Notify participants of the meeting time", dependencies=["scheduler"])
    ])
)
```

### Step 5: Execute the Job

Finally, we'll execute the job and print the result:

```python
# Execute the job
result = chief.execute(job)
print(result)
```

### Complete Code Example

Here’s the complete code for the example:

```python
from ceylon import Agent, AgentJobStepRequest, AgentJobResponse, JobRequest, JobSteps, Step, RunnerAgent

class AvailabilityAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"available_times": ["10:00 AM", "2:00 PM", "4:00 PM"]}
        )

class SchedulerAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        available_times = request.job_data["available_times"]
        best_time = available_times[0]
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"scheduled_time": best_time}
        )

class NotifierAgent(Agent):
    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        scheduled_time = request.job_data["scheduled_time"]
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"notification": f"Meeting scheduled at {scheduled_time}"}
        )

# Create agent instances
availability_agent = AvailabilityAgent(name="availability", role="Check Availability")
scheduler_agent = SchedulerAgent(name="scheduler", role="Schedule Meeting")
notifier_agent = NotifierAgent(name="notifier", role="Notify Participants")

# Create the runner agent
chief = RunnerAgent(workers=[availability_agent, scheduler_agent, notifier_agent])

# Define the job
job = JobRequest(
    title="Meeting Scheduler",
    explanation="Schedule a meeting based on participant availability",
    steps=JobSteps(steps=[
        Step(worker="availability", explanation="Check participant availability", dependencies=[]),
        Step(worker="scheduler", explanation="Schedule the meeting", dependencies=["availability"]),
        Step(worker="notifier", explanation="Notify participants of the meeting time", dependencies=["scheduler"])
    ])
)

# Execute the job
result = chief.execute(job)
print(result)
```

### What This Example Does

- **AvailabilityAgent** checks the availability of participants and returns possible meeting times.
- **SchedulerAgent** selects the best available time for the meeting.
- **NotifierAgent** sends a notification with the scheduled meeting time.

This simple example demonstrates how to set up a multi-agent system with Ceylon, where each agent has a specific role and contributes to completing the overall task.

---

Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).