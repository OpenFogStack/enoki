#!/usr/bin/env python3

import sys
import typing
import urllib.request
import urllib.error
import time
import threading
import multiprocessing as mp

import tqdm


def invoke(
    thread: int,
    endpoint: str,
    function: str,
    parameter: str,
    load_time: float,
    q: "mp.Queue[typing.Tuple[int, float, float, int]]",
) -> None:
    # run the function

    data = (str(thread) + "-" + parameter).encode("ascii")

    start_time = time.perf_counter()
    end_time = start_time + load_time

    while time.perf_counter() < end_time:
        try:
            start = time.perf_counter()

            r = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "text/plain"},
            )

            res = urllib.request.urlopen(r)

            end = time.perf_counter()

            # get the result
            q.put((thread, start, end, res.status))

        except urllib.error.HTTPError as e:
            res = e.code

            end = time.perf_counter()

            # get the result
            q.put((thread, start, end, res))

        except Exception as e:
            print(e)
            q.put((thread, 0, 0, 0))

    q.put((thread, -1, -1, -1))
    return


if __name__ == "__main__":
    # get args
    # tinyfaas endpoint
    # function name
    # parameter
    # time to run (in seconds)
    # number of threads
    # frequency of requests (per second per thread)
    # output file
    if len(sys.argv) != 8:
        print(
            "usage: python3 load-scale.py <endpoint> <function> <parameter> <load time s> <threads> <output <timeout_s>"
        )
        sys.exit(1)

    try:
        host = sys.argv[1]
        function = sys.argv[2]
        parameter = sys.argv[3]
        load_time = int(sys.argv[4])
        threads = int(sys.argv[5])
        output = sys.argv[6]
        timeout_s = int(sys.argv[7])

        if threads < 1 or load_time < 1 or timeout_s < 1:
            raise ValueError("invalid arguments")

    except:
        print("invalid arguments")
        print(
            "usage: python3 load-scale.py <endpoint> <function> <parameter> <load time s> <threads> <output <timeout_s>"
        )
        sys.exit(1)

    print(
        f"parameters: host={host}, function={function}, parameter={parameter}, load_time={load_time}, threads={threads}, output={output}, timeout_s={timeout_s}"
    )

    # run the function
    q: "mp.Queue[typing.Tuple[int, float, float, int]]" = mp.Queue()

    p: typing.Dict[int, mp.Process] = {}

    for i in range(threads):
        # staggered start
        time.sleep(1 / threads)

        p[i] = mp.Process(
            target=invoke,
            args=(
                i,
                host,
                function,
                parameter,
                load_time + (1 / threads * (threads - 1)),
                q,
            ),
        )

        p[i].start()

    start_time = time.perf_counter()

    with open(output, "w") as f:
        f.write("start,end,res\n")

        with tqdm.tqdm(total=float("inf"), position=1, miniters=500) as pbar:
            while time.perf_counter() - start_time <= load_time:
                try:
                    t, start, end, res = q.get(timeout=0.1)

                    if start == -1:
                        # thread is done
                        p[t].join()
                        del p[t]

                    else:
                        # print(f"{t}: {end-start:.3f}s")
                        f.write(f"{start},{end},{res}\n")
                        pbar.update(1)

                except:
                    # note that this timeout will not work if results still come in
                    pass

    for t in p:
        p[t].terminate()

    print("experiment finished in {:.3f}s".format(time.perf_counter() - start_time))
