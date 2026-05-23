from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


def retry_external_call():
    """
    Retry decorator for external API calls.

    Strategy:
    - retry up to 3 times
    - wait exponentially: 1s, 2s, 4s
    - retry on generic Exceptions for now

    Later we can make this more specific for rate limits/timeouts.
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )