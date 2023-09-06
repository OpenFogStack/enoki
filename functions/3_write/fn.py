#!/usr/bin/env python3

import typing
import kv
import uuid

LEN_BYTES = 1024


def fn(i: typing.Optional[str]) -> typing.Optional[str]:
    """write LEN_BYTES to db"""

    len_bytes = LEN_BYTES

    if i is not None:
        s = i.split("-")

        if len(s) > 1:
            len_bytes = int(s[1])

    random_key = str(uuid.uuid4())
    # remove the dashes
    random_key = random_key.replace("-", "")

    try:
        kv.update(random_key, "a" * len_bytes)

    except Exception as e:
        print("failed to write")
        raise Exception("writing failed: " + str(e))

    return random_key
