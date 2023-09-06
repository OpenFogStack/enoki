import befaas

import typing

#
#
# Tells if there currently is an emergency situation on our street.
#
# Example Payload: {
#   "objects": [{
#     "type": "ambulance",
#     "positionx": 0,
#     "positiony": 0,
#     "boundx": 3,
#     "boundy": 2
#   }]
# }
#
# Example Response: {
#   "emergency": {
#     "active": true
#     "type": "ambulance"
#   }
# }
#
# /


def fn(ctx: str) -> str:
    inputs = befaas.start(ctx)
    objects = inputs.get("objects")

    if not isinstance(objects, list):
        return befaas.end(ctx, {"error": "Wrong payload."})  # type: ignore

    emergencies = ["ambulance", "police", "lunatic"]

    emergency: typing.Dict[str, typing.Any] = {
        "active": False,
        "type": None,
    }

    for k in emergencies:
        if len(list(filter(lambda e: ("type" in e and e["type"] == k), objects))) > 0:
            emergency = {
                "active": True,
                "type": k,
            }
            break

    befaas.call(
        ctx,
        "lightphasecalculation",
        {"emergency": emergency},
        asynchronous=True,
    )

    return befaas.end(ctx, {"emergency": emergency})  # type: ignore
