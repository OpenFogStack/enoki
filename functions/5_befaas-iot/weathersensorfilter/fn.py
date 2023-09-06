import befaas

import typing


def isNaN(x: typing.Any) -> bool:
    if x == None:
        return True
    return False


#
# Check that temperature is both valid and a number. Value is in celsius.
#
def checkTemperature(temperature: typing.Optional[float]) -> bool:
    if temperature and not isNaN(temperature):
        return temperature >= -273.15 and temperature <= 100.0

    return False


#
# Check that humidity is both valid and a number. Value is in %.
#
def checkHumidity(humidity: typing.Optional[float]) -> bool:
    if humidity and not isNaN(humidity):
        return humidity >= 0.0 and humidity <= 100.0

    return False


#
# Check that wind is both valid and a number. Value is in m/s.
#
def checkWind(wind: typing.Optional[float]) -> bool:
    if wind and not isNaN(wind):
        return wind >= 0.0 and wind <= 150.0

    return False


#
# Check that rain is a true boolean.
#
def checkRain(rain: typing.Any) -> bool:
    return isinstance(rain, bool)


#
# Filters incoming weather sensor data, such as removing erroneous data or NaN
# values.
#
# Ex Payload Body: {
#    "temperature": 10.0,
#    "humidity": 50.0,
#    "wind": 20.0,
#    "rain": true,
# }
#
# Response: { }
# /
def fn(ctx: str) -> str:
    inputs = befaas.start(ctx)
    temperature, humidity, wind, rain = (
        inputs.get("temperature"),
        inputs.get("humidity"),
        inputs.get("wind"),
        inputs.get("rain"),
    )

    if not checkTemperature(temperature):
        return befaas.end(ctx, {"error": "Invalid temperature."})  # type: ignore

    if not checkHumidity(humidity):
        return befaas.end(ctx, {"error": "Invalid humidity."})  # type: ignore

    if not checkWind(wind):
        return befaas.end(ctx, {"error": "Invalid wind."})  # type: ignore

    if not checkRain(rain):
        return befaas.end(ctx, {"error": "Invalid rain."})  # type: ignore

    # only care if it rains :)
    if not rain:
        return befaas.end(ctx, None)  # type: ignore

    befaas.call(
        ctx,
        "roadcondition",
        {
            "temperature": temperature,
            "humidity": humidity,
            "wind": wind,
            "rain": rain,
        },
        asynchronous=True,
    )

    return befaas.end(ctx, None)  # type: ignore
