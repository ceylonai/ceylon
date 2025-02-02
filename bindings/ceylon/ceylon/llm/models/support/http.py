#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
# http.py
from typing import Optional, Any
import aiohttp
from functools import lru_cache


class AsyncHTTPClient:
    """Async HTTP client wrapper"""

    def __init__(
            self,
            session: Optional[aiohttp.ClientSession] = None,
            **kwargs: Any
    ):
        self.session = session or aiohttp.ClientSession(**kwargs)

    async def close(self) -> None:
        """Close the session"""
        if self.session:
            await self.session.close()

    async def get(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make GET request"""
        return await self.session.get(url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> aiohttp.ClientResponse:
        """Make POST request"""
        return await self.session.post(url, **kwargs)


@lru_cache()
def cached_async_http_client(**kwargs: Any) -> AsyncHTTPClient:
    """Get a cached HTTP client instance"""
    return AsyncHTTPClient(**kwargs)
