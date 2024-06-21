from pydantic.dataclasses import dataclass


@dataclass
class JobRequest:
    id = None
    agent_id = None
    message = None
