from pydantic.dataclasses import dataclass


@dataclass
class AdminRequest:
    name: str
    message: str


@dataclass
class WorkerResponse:
    name: str
    message: str
