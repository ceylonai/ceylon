#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import dataclasses
import uuid


@dataclasses.dataclass
class LLMMessage:
    role: str
    content: str
    instructions: str
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))


@dataclasses.dataclass
class LLMResponse:
    role: str
    content: str
    request_id: str
    id: str = dataclasses.field(default_factory=lambda: str(uuid.uuid4()))
