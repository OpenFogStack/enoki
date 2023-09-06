#!/usr/bin/env python3

import typing
import kv

KEY = "counter"


def fn(i: typing.Optional[str]) -> typing.Optional[str]:
    """ignore the input, add 1 to the list"""

    key = KEY

    if i is not None:
        s = i.split("-")
        if len(s) > 0:
            key = key + s[0]

    try:
        c = kv.read(key)
    except:
        c = ["0"]
        print("counter is not defined, reset to 0")

    if len(c) != 1:
        print(f"have {len(c)} counters, choosing max")
        c = max(c)
    else:
        c = c[0]

    try:
        c = int(c)
    except:
        c = 0
        print("counter is not an integer, reset to 0")

    c = c + 1

    kv.update(key, str(c))

    return str(c)
