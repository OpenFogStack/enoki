import befaas

import typing


#
# Calculate road condition. With 0 being perfect condition and 5 being worst
# condition.
# /
def calculateRoadCondition(
    temperature: int, humidity: int, wind: int, rain: int
) -> int:
    condition = 0
    if temperature < 4.0:
        condition += 1

    if humidity > 75.0:
        condition += 1

    # beaufort 7
    if wind > 15.0:
        condition += 1

    # beaufort 10
    if wind > 25.0:
        condition += 1

    if rain:
        condition += 1

    return condition


#
# Calculate road condition and pass to light phase calculation.
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

    condition = calculateRoadCondition(temperature, humidity, wind, rain)

    befaas.call(
        ctx,
        "lightphasecalculation",
        {
            "condition": condition,
        },
        asynchronous=False,
    )

    return befaas.end(ctx, None)  # type: ignore
