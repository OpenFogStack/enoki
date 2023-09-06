import befaas

import base64
import random
import struct
import typing

emergencyObject = {
    "type": "ambulance",
    "positionx": 55,
    "positiony": 135,
    "boundx": 114,
    "boundy": 175,
}

possibleObjects = [
    {"type": "car", "positionx": 175, "positiony": 75, "boundx": 202, "boundy": 135},
    {"type": "car", "positionx": 34, "positiony": 44, "boundx": 61, "boundy": 70},
    {"type": "car", "positionx": 118, "positiony": 94, "boundx": 184, "boundy": 124},
    {"type": "car", "positionx": 158, "positiony": 148, "boundx": 186, "boundy": 219},
    {"type": "person", "positionx": 23, "positiony": 141, "boundx": 60, "boundy": 215},
    {
        "type": "person",
        "positionx": 168,
        "positiony": 120,
        "boundx": 192,
        "boundy": 136,
    },
    {
        "type": "person",
        "positionx": 194,
        "positiony": 129,
        "boundx": 230,
        "boundy": 155,
    },
    {"type": "plate", "positionx": 182, "positiony": 151, "boundx": 232, "boundy": 195},
    {"type": "plate", "positionx": 74, "positiony": 28, "boundx": 99, "boundy": 82},
    {"type": "dog", "positionx": 109, "positiony": 53, "boundx": 175, "boundy": 82},
    {"type": "ball", "positionx": 39, "positiony": 137, "boundx": 109, "boundy": 170},
]


#
#
# The objectRecognition endpoint is responsible for analysing an uploaded image
# from the body.
#
# Example Payload: {
#    "image": <base64encoded jpg file>
# }
#
# Example Response: {
#   "objects": [
#     {
#       "type":"ambulance",
#       "positionx":8,
#       "positiony":64,
#       "boundx":58,
#       "boundy":121
#     },
#     {
#       "type":"car",
#       "positionx":10,
#       "positiony":118,
#       "boundx":85,
#       "boundy":138
#     }
#   ]
# }
#
# /
def fn(ctx: str) -> str:
    inputs = befaas.start(ctx)
    imageb64 = inputs.get("image")

    if not isinstance(imageb64, str):
        return befaas.end(ctx, {"error": "Wrong payload."})  # type: ignore

    # decode image
    decoded_data = base64.b64decode(imageb64)

    # Extract the color of the pixel at (0, 0)
    pixel_offset = 54  # Offset to the pixel data in JPG header
    red_pixel_data = decoded_data[pixel_offset : pixel_offset + 1]  # Assuming RGB

    # Unpack RGB values using struct module
    red_pixel_color = struct.unpack("B", red_pixel_data)[0]

    objects = random.sample(possibleObjects, random.randint(0, len(possibleObjects)))

    if red_pixel_color > 0:  # red
        objects.append(emergencyObject)

    # We loaded a picture successfully and parsed it.

    res = {"objects": objects}
    befaas.call(ctx, "trafficstatistics", res, asynchronous=True)
    befaas.call(ctx, "emergencydetection", res, asynchronous=False)

    befaas.call(ctx, "movementplan", res, asynchronous=False)

    return befaas.end(ctx, res)  # type: ignore
