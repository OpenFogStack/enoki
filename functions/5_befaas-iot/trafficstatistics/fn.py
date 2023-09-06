import befaas

import time
import typing


def count_by(
    collection: typing.List[typing.Dict[str, typing.Any]], key: str
) -> typing.Dict[str, int]:
    result: typing.Dict[str, int] = {}
    for item in collection:
        k = item[key]
        result[k] = result.get(k, 0) + 1
    return result


#
#
# Store counts of detected objects in the scene with a current timestamp.
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
#  "ambulance": 1,
#  "car": 10
# }
#
#
def fn(ctx: str) -> str:
    inputs = befaas.start(ctx)
    objects = inputs.get("objects")

    if not isinstance(objects, list):
        return befaas.end(ctx, {"error": "Wrong payload."})  # type: ignore

    statistics = count_by(objects, "type")

    timestamp = int(time.time())

    befaas.dbset(ctx, f"trafficstatistics{timestamp}", statistics)

    return befaas.end(ctx, statistics)  # type: ignore
