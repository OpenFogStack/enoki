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
    num_request: int,
    frequency: float,
    q: "mp.Queue[typing.Tuple[int, float, float, int]]",
) -> None:
    # run the function

    data = (str(thread) + "-" + parameter).encode("ascii")

    for i in range(num_request):
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

        st = 1 / frequency - (end - start)
        time.sleep(max(st, 0))

    q.put((thread, -1, -1, -1))
    return


if __name__ == "__main__":
    # get args
    # tinyfaas endpoint
    # function name
    # parameter
    # number of requests (per thread)
    # number of threads
    # frequency of requests (per second per thread)
    # output file
    if len(sys.argv) != 9:
        print(
            "usage: python3 load-simple.py <endpoint> <function> <parameter> <requests> <threads> <frequency> <output <timeout_s>"
        )
        sys.exit(1)

    try:
        host = sys.argv[1]
        function = sys.argv[2]
        parameter = sys.argv[3]
        num_requests = int(sys.argv[4])
        threads = int(sys.argv[5])
        frequency = float(sys.argv[6])
        output = sys.argv[7]
        timeout_s = int(sys.argv[8])

        if num_requests < 1 or threads < 1 or frequency <= 0:
            raise ValueError("invalid arguments")

    except:
        print("invalid arguments")
        print(
            "usage: python3 load-simple.py <endpoint> <function> <parameter> <requests> <threads> <frequency> <output> <timeout_s>"
        )
        sys.exit(1)

    print(
        f"parameters: host={host}, function={function}, parameter={parameter}, num_requests={num_requests}, threads={threads}, frequency={frequency}, output={output}, timeout_s={timeout_s}"
    )

    # run the function
    q: "mp.Queue[typing.Tuple[int, float, float, int]]" = mp.Queue()

    p: typing.Dict[int, mp.Process] = {}

    for i in range(threads):
        # staggered start
        time.sleep((1 / frequency) / threads)

        p[i] = mp.Process(
            target=invoke,
            args=(i, host, function, parameter, num_requests, frequency, q),
        )

        p[i].start()

    start_time = time.perf_counter()

    with open(output, "w") as f:
        f.write("start,end,res\n")

        with tqdm.tqdm(total=threads * num_requests, position=1) as pbar:
            while len(p) > 0:
                try:
                    t, start, end, res = q.get(timeout=10)

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
                    if time.perf_counter() - start_time > timeout_s:
                        print("reached experiment timeout")
                        for t in p:
                            p[t].terminate()
                            # del p[t]
                        break

    print("experiment finished in {:.3f}s".format(time.perf_counter() - start_time))

    # print results
    with open(output, "r") as f:
        lines = f.readlines()

        # remove header
        lines = [line.strip() for line in lines[1:]]

        # get mean, median, 95th, 99th
        times = [
            float(line.split(",")[1]) - float(line.split(",")[0]) for line in lines
        ]
        times.sort()

        mean = sum(times) / len(times)
        median = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        p99 = times[int(len(times) * 0.99)]

        print(f"mean: {mean:.3f}s")
        print(f"median: {median:.3f}s")
        print(f"95th: {p95:.3f}s")
        print(f"99th: {p99:.3f}s")
