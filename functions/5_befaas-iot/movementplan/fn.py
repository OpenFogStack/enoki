import befaas

import typing


def uniqBy(
    l: typing.List[typing.Dict[str, typing.Any]]
) -> typing.List[typing.Dict[str, typing.Any]]:
    unique_dicts = []
    seen_dicts = set()

    for d in l:
        sorted_items = sorted(d.items())
        dict_tuple = tuple(sorted_items)

        if dict_tuple not in seen_dicts:
            seen_dicts.add(dict_tuple)
            unique_dicts.append(d)

    return unique_dicts


#
# bit order: 0b[red][yellow][green]
# {
#   lights: ["red","green", "yellow"],
#   blink: false
# }
#


def fn(ctx: str) -> str:
    inputs = befaas.start(ctx)
    dbObjects = befaas.dbget(ctx, "movementplancars")

    cars = []
    if not dbObjects == None and "cars" in dbObjects:
        cars = dbObjects["cars"]

    if "objects" in inputs:
        cars = cars[: len(inputs["objects"])]
    elif "carDirection" in inputs:
        cars.insert(0, inputs["carDirection"])
        cars = uniqBy(cars)
        cars = cars[:12]

    befaas.dbset(ctx, "movementplancars", {"cars": cars})

    befaas.call(ctx, "lightphasecalculation", {"plan": cars}, asynchronous=True)

    return befaas.end(ctx, None)  # type: ignore
