"""Tests for the chat-stream retry helper (api.routes.chat._astream_with_retry).

A transient upstream 503 ('high demand') happens BEFORE the first token, so we
retry there; once any token is emitted we must not retry (no duplicate output).
"""
import anyio
import pytest

from api.routes.chat import _astream_with_retry


class _Chain:
    """Fake chain whose astream fails the first `fail_times` calls, then streams."""
    def __init__(self, fail_times, tokens=("Hello ", "world"), fail_after=None):
        self.calls = 0
        self.fail_times = fail_times
        self.tokens = tokens
        self.fail_after = fail_after  # emit this many tokens then raise (mid-stream)

    def astream(self, payload):
        self.calls += 1
        call = self.calls
        outer = self

        async def gen():
            if call <= outer.fail_times:
                raise RuntimeError("Error code: 503 - high demand")
            for i, tok in enumerate(outer.tokens):
                if outer.fail_after is not None and i == outer.fail_after:
                    raise RuntimeError("mid-stream boom")
                yield tok
        return gen()


def _collect(chain, retries):
    async def run():
        out = []
        async for chunk in _astream_with_retry(chain, {}, retries, backoff=0):
            out.append(chunk)
        return out
    return anyio.run(run)


def test_retries_before_first_token_then_succeeds():
    chain = _Chain(fail_times=1)
    assert _collect(chain, retries=2) == ["Hello ", "world"]
    assert chain.calls == 2  # one failure + one success


def test_gives_up_after_retries_exhausted():
    chain = _Chain(fail_times=5)
    with pytest.raises(RuntimeError, match="503"):
        _collect(chain, retries=2)
    assert chain.calls == 3  # initial + 2 retries


def test_does_not_retry_after_a_token_was_emitted():
    # Fails mid-stream (after 1 token) → must propagate, not restart.
    chain = _Chain(fail_times=0, fail_after=1)
    with pytest.raises(RuntimeError, match="mid-stream"):
        _collect(chain, retries=3)
    assert chain.calls == 1  # no retry once streaming started


def test_no_failure_streams_normally():
    chain = _Chain(fail_times=0)
    assert _collect(chain, retries=2) == ["Hello ", "world"]
    assert chain.calls == 1
