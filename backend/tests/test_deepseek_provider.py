import asyncio
import unittest

import httpx
from fastapi import HTTPException

from app.config import Settings
from app.llm.deepseek_provider import DeepSeekProvider


def success_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        request=request,
        json={"choices": [{"message": {"content": "scored response"}}]},
    )


class DeepSeekProviderTests(unittest.TestCase):
    def test_retries_transport_errors_and_recovers(self):
        calls = 0
        delays: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise httpx.ReadTimeout("slow response", request=request)
            return success_response(request)

        async def record_sleep(delay: float) -> None:
            delays.append(delay)

        provider = DeepSeekProvider(
            Settings(deepseek_api_key="test-key"),
            transport=httpx.MockTransport(handler),
            sleep=record_sleep,
            jitter=lambda: 0.0,
        )

        result = asyncio.run(provider.chat([{"role": "user", "content": "score"}]))

        self.assertEqual(result, "scored response")
        self.assertEqual(calls, 3)
        self.assertEqual(delays, [2.0, 4.0])

    def test_retries_503_then_returns_status_after_exhaustion(self):
        calls = 0
        delays: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(503, request=request)

        async def record_sleep(delay: float) -> None:
            delays.append(delay)

        provider = DeepSeekProvider(
            Settings(deepseek_api_key="test-key"),
            transport=httpx.MockTransport(handler),
            sleep=record_sleep,
            jitter=lambda: 0.0,
        )

        with self.assertRaisesRegex(HTTPException, "DeepSeek API error: 503"):
            asyncio.run(provider.chat([{"role": "user", "content": "score"}]))

        self.assertEqual(calls, 4)
        self.assertEqual(delays, [2.0, 4.0, 8.0])

    def test_does_not_retry_authentication_errors(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(401, request=request)

        async def fail_if_called(_: float) -> None:
            self.fail("Authentication errors must not be retried.")

        provider = DeepSeekProvider(
            Settings(deepseek_api_key="test-key"),
            transport=httpx.MockTransport(handler),
            sleep=fail_if_called,
        )

        with self.assertRaisesRegex(HTTPException, "DeepSeek API error: 401"):
            asyncio.run(provider.chat([{"role": "user", "content": "score"}]))

        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
