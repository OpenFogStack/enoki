#!/usr/bin/env python3

import typing
import kv
import uuid

# the default pointer
# points to the current largest key (so we know from where to scan)
POINTER = "aaaacurr"

# a prefix for data
# this allows us to skip the pointer when scanning
PREFIX = "data"

# the window size
WINDOW = 10


def fn(i: typing.Optional[str]) -> typing.Optional[str]:
    """calculate moving average"""

    # get the pointer
    pointer = POINTER
    data_prefix = PREFIX

    # if there is a parameter, it is of the form
    # {thread}-{data}
    # the thread part is used to differentiate between pointers and prefixes
    if i is not None:
        s = i.split("-")
        if len(s) > 0:
            # the prefix is s[0]

            # let's convert this number to a string
            # this is to avoid collisions somewhat
            p = str(chr(int(s[0]) + ord("b")))

            # the new pointer is prefixpointer
            pointer = pointer + p
            # the new data prefix is prefixprefix
            data_prefix = p

            # the new input is in s[1]
            i = int(s[1])

    # see if we can get the current pointer
    try:
        curr = kv.read(pointer)
        # read returns an array
        curr = curr[0]
        # get the integer value
        curr = int(curr[len(data_prefix) :])
    except Exception as e:
        print(f"could not read pointer {pointer}")
        print("pointer is not defined, reset to 0")
        print(e)
        # this means there is no data yet
        # write it
        try:
            kv.update(pointer, data_prefix + str(0))
        except Exception as e:
            print(f"failed to update pointer {pointer} to {data_prefix + str(0)}")
            print(e)

        curr = 0

    # reset pointer if it is larger than WINDOW
    if curr >= WINDOW:
        curr = 0

    # read the last WINDOW-1 values
    values = []

    try:
        values = kv.scan(data_prefix + str(0), WINDOW)
    except Exception as e:
        print(f"failed to scan {WINDOW} values from {data_prefix + str(0)}")
        print(e)

    print(f"have {len(values)} values")

    # only the first element for each value
    values = [v[0] for v in values]

    # put the current value into the array at position curr
    if len(values) > curr:
        values[curr] = i
    else:
        # if for some reason we do not have enough values
        # just append it whereever
        print(f"have {len(values)} values, but curr is {curr}")
        values.append(i)

    # calculate the average
    mean = sum([float(v) for v in values]) / len(values)

    # write the new value we got
    try:
        kv.update(data_prefix + str(curr), str(i))
    except Exception as e:
        print(f"failed to write value {i} to {data_prefix + str(curr)}")
        print(e)

    # write the newest value and update the pointer
    curr = curr + 1

    try:
        kv.update(pointer, data_prefix + str(curr))
    except Exception as e:
        print(f"failed to update pointer {pointer} to {data_prefix + str(curr)}")
        print(e)

    return str(mean)
