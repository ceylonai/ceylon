#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
# usage.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class Usage:
    """Tracks token and request usage"""
    requests: int = 0
    request_tokens: int = 0
    response_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: 'Usage') -> None:
        """Add usage from another Usage instance"""
        self.requests += other.requests
        self.request_tokens += other.request_tokens
        self.response_tokens += other.response_tokens
        self.total_tokens += other.total_tokens


@dataclass
class UsageLimits:
    """Defines usage limits"""
    request_limit: Optional[int] = None
    request_tokens_limit: Optional[int] = None
    response_tokens_limit: Optional[int] = None
