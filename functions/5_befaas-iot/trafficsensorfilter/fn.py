import befaas

import typing
import re


#
# Filters incoming traffic sensor data, such as removing erroneous data or NaN
# values.
#
# Ex Payload Body: {
#   "carDirection": {
#     "plate": "OD DI 98231"
#     "direction": 4
#     "speed": 1.7
#   }
# }
#
# Response: { } or {
#   "carDirection": {
#     "plate": "OD DI 98231"
#     "direction": 4
#     "speed": 1.7
#   }
# }
#
def fn(ctx: str) -> str:
    inputs = befaas.start(ctx)
    carDirection = inputs.get("carDirection")

    # check the type
    if not isinstance(carDirection["direction"], (int, float)):
        return befaas.end(ctx, None)  # type: ignore

    if carDirection["direction"] < 0 or carDirection["direction"] > 4:
        return befaas.end(ctx, None)  # type: ignore

    if not isinstance(carDirection["plate"], str):
        return befaas.end(ctx, None)  # type: ignore

    if not re.match(r"^[A-Z]{2} [A-Z]{2} \d{1,7}$", carDirection["plate"]):
        return befaas.end(ctx, None)  # type: ignore

    if carDirection["speed"] < -20.0 or carDirection["speed"] > 38.8889:
        return befaas.end(ctx, None)  # type: ignore

    befaas.call(
        ctx,
        "movementplan",
        {"carDirection": carDirection},
        asynchronous=False,
    )

    return befaas.end(ctx, None)  # type: ignore
