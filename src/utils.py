import logging
import secrets
from typing import Optional, TypeVar

import aiohttp
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

from src.config import LOGGING_LEVEL

logger = logging.getLogger()

T = TypeVar("T")


def cast_away_optional(arg: Optional[T]) -> T:
    assert arg is not None
    return arg


custom_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(),
    before_sleep=before_sleep_log(logger, LOGGING_LEVEL),
    reraise=True,
)


def generate_id():
    return secrets.token_hex(2)


async def trace_request_start(session, trace_config_ctx, params):
    request_id = generate_id()
    trace_config_ctx.request_id = request_id
    logger.info(
        f"Request [{request_id}]: {params.method} {params.url} {params.headers}"
    )


async def trace_request_chunk_sent(session, trace_config_ctx, params):
    request_id = trace_config_ctx.request_id
    if params.chunk:
        payload = f"Payload: {params.chunk.decode() if isinstance(params.chunk, bytes) else params.chunk}"
    else:
        payload = "Payload: None"
    logger.info(f"Sent [{request_id}]: {payload}")


async def trace_request_end(session, trace_config_ctx, params):
    request_id = trace_config_ctx.request_id
    # body = await params.response.clone().json()
    logger.info(f"Response [{request_id}]: {params.response.status}")


def get_aiohttp_trace_config():
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(trace_request_start)
    trace_config.on_request_chunk_sent.append(trace_request_chunk_sent)
    trace_config.on_request_end.append(trace_request_end)
    return trace_config
