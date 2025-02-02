#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
# settings.py
from dataclasses import dataclass
from typing import Any, Optional, TypedDict


class ModelSettingsDict(TypedDict, total=False):
    max_tokens: Optional[int]
    temperature: Optional[float]
    top_p: Optional[float]
    timeout: Optional[float]
    parallel_tool_calls: Optional[int]
    seed: Optional[int]
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    logit_bias: Optional[dict[int, float]]


@dataclass
class ModelSettings:
    """Configuration settings for model requests"""
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    timeout: Optional[float] = None
    parallel_tool_calls: Optional[int] = None
    seed: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[dict[int, float]] = None

    def to_dict(self) -> ModelSettingsDict:
        """Convert settings to a dictionary"""
        return {
            k: v for k, v in self.__dict__.items()
            if v is not None
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return getattr(self, key, default)
