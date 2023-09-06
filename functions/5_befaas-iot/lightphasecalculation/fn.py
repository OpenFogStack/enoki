import befaas

import time
import typing


def isNumber(x: typing.Any) -> bool:
    return isinstance(x, (int, float, complex))


#
#
# Responsible for current traffic light calculation.
# Adapts to results of movement plan, emergency detection and road condition.
# Writes light into database.
#
# Example Request: {
#   "plan": [{
#     "plate": "XXX",
#     "direction": 3,
#     "speed": 63.8
#   }],
#
#   "emergency": {
#     "active": true,
#     "type": "lunatic"
#   },
#
#   "condition": 5
# }
#
# Example Response (empty): { }
#
# /


def initialDBUpdate(
    ctx: str, condition: typing.Any, plan: typing.Any, emergency: typing.Any
) -> None:
    if isinstance(condition, (int, float, complex)):
        befaas.dbset(ctx, "lightcalculationcondition", condition)

    if not plan == None:
        befaas.dbset(ctx, "lightcalculationplates", [car.get("plate") for car in plan])
        befaas.dbset(
            ctx,
            "lightcalculationdirections",
            [car.get("direction") for car in plan],
        )
        befaas.dbset(
            ctx,
            "lightcalculationspeeds",
            [car.get("speed") for car in plan],
        )

    # Active emergencies are handled immediately
    if not emergency == None:
        if not emergency.get("active") == None:
            befaas.dbset(ctx, "lightcalculationlights", ["yellow"])
            befaas.dbset(ctx, "lightcalculationblink", True)
            befaas.dbset(ctx, "lightcalculationemergency", True)
            befaas.dbset(ctx, "lightcalculationemergencytype", emergency["type"])
        else:
            befaas.dbset(ctx, "lightcalculationemergency", False)
            befaas.dbset(ctx, "lightcalculationemergencytype", None)


def checkAndLock(ctx: str) -> bool:
    l = befaas.dbget(ctx, "lightcalculationlock")

    if l == True:
        return True

    befaas.dbset(ctx, "lightcalculationlock", True)

    return False


def checkAndUnlock(ctx: str) -> bool:
    l = befaas.dbget(ctx, "lightcalculationlock")

    if l == False:
        return True

    befaas.dbset(ctx, "lightcalculationlock", False)

    return False


def waitAppropriately(ctx: str) -> None:
    condition = befaas.dbget(ctx, "lightcalculationcondition") or 0

    time.sleep(int(condition / 2 + 2))


def changeLight(ctx: str) -> None:
    # Emergencies rule
    emergency = befaas.dbget(ctx, "lightcalculationemergency")

    if emergency:
        befaas.dbset(ctx, "lightcalculationlights", ["yellow"])
        befaas.dbset(ctx, "lightcalculationblink", True)
        return

    # If no movement plan or cars just say lights are red blink (so pedestrians are happy)
    plates = befaas.dbget(ctx, "lightcalculationplates")

    # We probably really should have 4 different traffic lights
    speeds = befaas.dbget(ctx, "lightcalculationspeeds")

    if not plates or any(speed > 50 for speed in map(float, speeds)):
        befaas.dbset(ctx, "lightcalculationlights", ["yellow"])
        befaas.dbset(ctx, "lightcalculationblink", False)
        waitAppropriately(ctx)
        befaas.dbset(ctx, "lightcalculationlights", ["red"])
        befaas.dbset(ctx, "lightcalculationblink", False)
    else:
        befaas.dbset(ctx, "lightcalculationlights", ["yellow", "red"])
        befaas.dbset(ctx, "lightcalculationblink", False)
        waitAppropriately(ctx)
        befaas.dbset(ctx, "lightcalculationlights", ["green"])
        befaas.dbset(ctx, "lightcalculationblink", False)

    newEmergency = befaas.dbget(ctx, "lightcalculationemergency")
    if newEmergency:
        befaas.dbset(ctx, "lightcalculationlights", ["yellow"])
        befaas.dbset(ctx, "lightcalculationblink", True)


def fn(ctx: str) -> str:
    inputs = befaas.start(ctx)
    plan, emergency, condition = (
        inputs.get("plan"),
        inputs.get("emergency"),
        inputs.get("condition"),
    )

    if not isNumber(condition) and not plan and not emergency:
        # logic of getlightphasecalculation
        # not included in this workload anyway
        lights = befaas.dbget(ctx, "lightcalculationlights")

        blink = befaas.dbget(ctx, "lightcalculationblink") == True

        return befaas.end(ctx, {"lights": lights, "blink": blink})  # type: ignore

    initialDBUpdate(ctx, condition, plan, emergency)

    if checkAndLock(ctx):
        return befaas.end(ctx, None)  # type: ignore
    changeLight(ctx)
    if checkAndUnlock(ctx):
        return befaas.end(ctx, None)  # type: ignore

    return befaas.end(ctx, None)  # type: ignore
