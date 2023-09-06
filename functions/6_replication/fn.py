#!/usr/bin/env python3

import typing
import kv
import uuid

KEY = "counter"


def fn(i: typing.Optional[str]) -> typing.Optional[str]:
    """calculate moving average"""

    key = KEY

    if i is None or i == "":
        # it's a read!
        try:
            v = kv.read(key)
        except:
            # no value yet
            return "No value yet"

        if len(v) == 0:
            return "No value yet"

        if len(v) != 1:
            print(f"have {len(v)} values, choosing first")

        return str(v[0])

    # else: it's a write!
    # just write the input value to the key

    kv.update(key, i)

    return None
