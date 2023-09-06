#!/usr/bin/env python3

import typing
import kv

KEY = "data"
LEN_BYTES = 1024


def fn(i: typing.Optional[str]) -> typing.Optional[str]:
    """ignore the input, read LEN_BYTES from db"""

    key = KEY
    len_bytes = LEN_BYTES

    if i is not None:
        s = i.split("-")
        if len(s) > 0:
            key = key + s[0]

        if len(s) > 1:
            len_bytes = int(s[1])

    try:
        _ = kv.read(key)
    except:
        print("data is not defined, writing now")

        try:
            kv.update(key, "a" * len_bytes)
            return "write"
        except Exception as e:
            print("writing failed")
            raise Exception("writing failed: " + str(e))

    return "read"
