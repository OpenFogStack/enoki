#!/usr/bin/env python3
import base64
import datetime
import os
import random
import json
import sys
import typing
import urllib.request
import urllib.error
import uuid
import time
import threading
import multiprocessing as mp

import tqdm

THREADS = 10
OUTPUT = "output.txt"

DURATION = int(os.getenv("DURATION", 60))


def _getcurrtime() -> str:
    return datetime.datetime.now(tz=datetime.timezone.utc).isoformat()


def trafficsensorfilter_getjson() -> typing.Dict[str, typing.Any]:
    return {
        "carDirection": {
            "plate": "OD DI 98231",
            "direction": 4,
            # this was in the original workload, no idea what the intention is
            "speed": random.choice([10, 800]),
        }
    }


def weathersensorfilter_getjson() -> typing.Dict[str, typing.Any]:
    return {
        "temperature": 10.0,
        "humidity": 50.0,
        "wind": 5.0,
        "rain": random.choice([True, False]),
    }


image_ambulance = base64.b64encode(open("image-ambulance.jpg", "rb").read()).decode(
    "ascii"
)
image_noambulance = base64.b64encode(open("image-noambulance.jpg", "rb").read()).decode(
    "ascii"
)


START_TIME = time.time()


def objectrecognition_getjson() -> typing.Dict[str, typing.Any]:
    f = "placeholder"

    # reasonable change every 20 seconds for 5 seconds
    if time.time() - START_TIME % 20 < 5:
        f = image_ambulance
    else:
        f = image_noambulance

    return {
        "image": f,
    }


workload = {
    "phases": [
        {
            "duration": DURATION,
            "arrivalRate": 5,
        }
    ],
    "scenarios": [
        {
            "func": "trafficsensorfilter",
            "getjson": trafficsensorfilter_getjson,
            "async": False,
            "name": "trafficsensorfilter",
            "weight": 45,
        },
        {
            "func": "weathersensorfilter",
            "getjson": weathersensorfilter_getjson,
            "async": False,
            "name": "weatherSensorFilter",
            "weight": 10,
        },
        {
            "func": "objectrecognition",
            "getjson": objectrecognition_getjson,
            "async": False,
            "name": "objectrecognition",
            "weight": 45,
        },
    ],
}


def worker(
    task_queue: "mp.Queue[typing.Dict[str, typing.Any]]",
    output_queue: "mp.Queue[str]",
    pipe: "mp.connection.Connection",
) -> None:
    while True:
        # get the next task from the queue

        try:
            task = task_queue.get(timeout=5)
        except:
            # timeout
            if pipe.poll():
                # parent is done, we can exit
                pipe.recv()
                pipe.close()
                return
            continue

        try:
            r = urllib.request.Request(
                task["endpoint"],
                data=task["data"],
                headers=task["headers"],
            )

            start = f"BEFAAS;{_getcurrtime()};client;{task['xpair']};{task['xpair']};{task['xcontext']};start-call-{task['function']}"

            res = urllib.request.urlopen(r)

            # get the result

        except urllib.error.HTTPError as e:
            print(e)

        except Exception as e:
            print(e)

        end = f"BEFAAS;{_getcurrtime()};client;{task['xpair']};{task['xpair']};{task['xcontext']};end-call-{task['function']}"

        output_queue.put(start)
        output_queue.put(end)

    return


def logger(
    output: str,
    output_queue: "mp.Queue[str]",
    pipe: "mp.connection.Connection",
) -> None:
    with open(output, "w") as f:
        while True:
            # get the next task from the queue

            try:
                entry = output_queue.get(timeout=5)
            except:
                # timeout
                if pipe.poll():
                    # parent is done, we can exit
                    pipe.recv()
                    pipe.close()
                    return
                continue

            f.write(f"node=client handler=nil stream=stdout {_getcurrtime()} {entry}\n")


if __name__ == "__main__":
    # no args, assume everything we need is in os.environ

    task_queue: "mp.Queue[typing.Dict[str, typing.Any]]" = mp.Queue()
    output_queue: "mp.Queue[str]" = mp.Queue()

    # start the workers
    p: typing.Dict[int, mp.Process] = {}
    pipes = []

    for i in range(THREADS):
        pipe_parent, pipe_child = mp.Pipe()

        p[i] = mp.Process(
            target=worker,
            args=(task_queue, output_queue, pipe_child),
        )

        p[i].start()
        pipes.append(pipe_parent)

    # start the logger
    logger_pipe_parent, logger_pipe_child = mp.Pipe()
    logger_proc = mp.Process(
        target=logger, args=(OUTPUT, output_queue, logger_pipe_child)
    )
    logger_proc.start()

    # start the task generator
    for phase in workload["phases"]:  # type: ignore
        start = time.perf_counter()
        end = start + phase["duration"]

        weights = [s["weight"] for s in workload["scenarios"]]  # type: ignore

        while True:
            if time.perf_counter() > end:
                break

            start_time = time.perf_counter()

            selected_scenario = random.choices(workload["scenarios"], weights=weights)[  # type: ignore
                0
            ]

            # get the parameters
            j = selected_scenario["getjson"]()

            # generate xpair and xcontext
            xpair = str(uuid.uuid4())
            xcontext = str(uuid.uuid4())

            data = {
                "data": j,
                "xpair": xpair,
                "xcontext": xcontext,
            }

            headers = {
                "Content-Type": "application/json",
            }

            if selected_scenario["async"]:
                headers["X-tinyFaaS-Async"] = "True"

            # generate the task
            task = {
                "desc": selected_scenario["name"],
                "endpoint": os.getenv(f"ENDPOINT_{selected_scenario['func'].upper()}"),
                "data": json.dumps(data).encode("utf-8"),
                "headers": headers,
                "xpair": xpair,
                "xcontext": xcontext,
                "function": selected_scenario["func"],
            }

            # put the task in the queue
            task_queue.put(task)

            # sleep
            end_time = time.perf_counter()
            took = end_time - start_time

            st = 1 / selected_scenario["weight"] - took
            time.sleep(max(st, 0))

    # inform the workers that we are done
    # wait that the queue is empty
    while not task_queue.empty():
        time.sleep(1)

    for pipe in pipes:
        pipe.send(True)
        pipe.close()
    logger_pipe_parent.send(True)

    # wait for the workers to finish
    for i in range(THREADS):
        p[i].join()

    logger_proc.join()

    sys.exit(0)
