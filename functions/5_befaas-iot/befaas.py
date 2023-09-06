import kv

import datetime
import os
import json
import time
import threading
import typing
import urllib.request
import uuid

# cache holds a cached parsed ctx object
cache: typing.Dict[str, typing.Any] = {}

log_lock = threading.Lock()

function = os.getenv("FUNCTION_NAME", "unknown")


def _dictcopy(d: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
    return {k: v for k, v in d.items()}


def _getcurrtime() -> str:
    return datetime.datetime.now(tz=datetime.timezone.utc).isoformat()


def _logperf(xpair: str, xexecution: str, xcontext: str, event: str) -> None:
    # not a fan of this but it is what it is
    with log_lock:
        print(
            f"BEFAAS;{_getcurrtime()};{function};{xpair};{xexecution};{xcontext};{event}"
        )


def _logdebug(event: str) -> None:
    with log_lock:
        print(f"DEBUG;{_getcurrtime()};{function};{repr(event)}")


def _parse(ctx_s: str) -> typing.Dict[str, typing.Any]:
    if ctx_s not in cache:
        try:
            cache[ctx_s] = json.loads(ctx_s)
        except Exception as e:
            raise Exception(f"error parsing ctx {ctx_s}: {e}")

    return cache[ctx_s]  # type: ignore


def start(ctx_s: str) -> typing.Dict[str, typing.Any]:
    _logdebug(f"starting request with context {ctx_s} (len {len(ctx_s)})")
    ctx = _parse(ctx_s)

    _logperf(ctx["xpair"], ctx["xpair"], ctx["xcontext"], "start")

    _logdebug(f"parsed ctx to {ctx}")

    return ctx["data"]  # type: ignore


def end(ctx_s: str, data: typing.Optional[typing.Any]) -> str:
    _logdebug("ending request")

    new_ctx = _dictcopy(_parse(ctx_s))
    new_ctx["data"] = data or {}

    _logperf(new_ctx["xpair"], new_ctx["xpair"], new_ctx["xcontext"], "end")

    output = json.dumps(new_ctx)

    _logdebug(f"returning {output}")

    return output


def call(
    ctx_s: str, func: str, i: typing.Dict[str, typing.Any], asynchronous: bool = False
) -> typing.Dict[str, typing.Any]:
    _logdebug(f"calling {func} with input {i}")

    # new context by copying the old one
    new_ctx = _dictcopy(_parse(ctx_s))

    # xexecution is the original xpair of this request
    xexecution = new_ctx["xpair"]

    # generate a new xpair
    new_ctx["xpair"] = str(uuid.uuid4())

    # put in the new data
    new_ctx["data"] = i

    _logperf(new_ctx["xpair"], xexecution, new_ctx["xcontext"], f"start-call-{func}")

    try:
        data = json.dumps(new_ctx).encode("utf-8")
        headers = (
            {
                "X-tinyFaaS-Async": "True",
            }
            if asynchronous
            else {}
        )
        endpoint = os.getenv(f"ENDPOINT_{func.upper()}")
        req = urllib.request.Request(
            f"{endpoint}", data=data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            # Process response_data as needed
    except Exception as e:
        _logdebug(f"error calling {func}: {e}")

    _logperf(new_ctx["xpair"], xexecution, new_ctx["xcontext"], f"end-call-{func}")

    # if async, return immediately
    # no data to parse
    if asynchronous:
        return {}

    try:
        data = json.loads(response_data.decode("utf-8"))["data"]
    except Exception as e:
        _logdebug(
            f"error parsing response {response_data.decode('utf-8')} from {func}: {e}"
        )

    _logdebug(f"got response {response_data.decode('utf-8')} from {func}")

    return data  # type: ignore


def dbget(ctx_s: str, key: str) -> typing.Any:
    _logdebug(f"getting {key} from db")

    ctx = _parse(ctx_s)

    # generate a new xpair
    xpair = str(uuid.uuid4())

    xexecution = ctx["xpair"]

    _logperf(xpair, xexecution, ctx["xcontext"], f"start-db-get")

    v: typing.Any = ""
    try:
        v = kv.read(key)[0]
    except Exception as e:
        _logdebug(f"error getting {key} from db (returning None): {e}")

    _logperf(xpair, xexecution, ctx["xcontext"], f"end-db-get")

    if v == "":
        return None

    _logdebug(f"got {v} from db for {key}")

    # unmarshal the value from json
    try:
        v = json.loads(v)
    except:
        _logdebug(f"error unmarshalling {v} from db")

    return v


def dbset(ctx_s: str, key: str, value: typing.Any) -> None:
    _logdebug(f"setting {key} to {value} in db")

    ctx = _parse(ctx_s)

    xexecution = ctx["xpair"]

    # generate a new xpair
    xpair = str(uuid.uuid4())

    _logperf(xpair, xexecution, ctx["xcontext"], f"start-db-set")

    # marshal the value to json
    try:
        value = json.dumps(value)
    except:
        _logdebug(f"error marshalling {value} to db")

    try:
        kv.update(key, value)
    except Exception as e:
        _logdebug(f"error setting {key} to {value} in db: {e}")

    _logperf(xpair, xexecution, ctx["xcontext"], f"end-db-set")

    _logdebug(f"set {key} to {value} in db")
