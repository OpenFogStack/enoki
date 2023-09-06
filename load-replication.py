#!/usr/bin/env python3

import sys
import typing
import uuid
import urllib.request
import urllib.error
import time
import threading
import multiprocessing as mp

import tqdm


def writer(
    endpoint: str,
    num_request: int,
    frequency: float,
    reader_update_pipe: "mp.connection.Connection",
    out_queue: "mp.Queue[typing.Tuple[str, float, float, int]]",
) -> None:
    # run the function
    for i in range(num_request):
        # make a new string
        data = uuid.uuid4().hex

        try:
            start = time.perf_counter()

            r = urllib.request.Request(
                endpoint,
                data=data.encode("ascii"),
                headers={"Content-Type": "text/plain"},
            )

            res = urllib.request.urlopen(r).status

            end = time.perf_counter()

        except urllib.error.HTTPError as e:
            res = e.code

            end = time.perf_counter()

        # inform the reader that we have updated the value
        reader_update_pipe.send((end, data))

        # get the result
        out_queue.put(("w", start, end, res))

        st = 1 / frequency - (end - start)
        time.sleep(max(st, 0))

    out_queue.put(("w", -1, -1, -1))
    return


def reader(
    endpoint: str,
    num_request: int,
    frequency: float,
    update_pipe: "mp.connection.Connection",
    out_queue: "mp.Queue[typing.Tuple[str, float, float, float, int]]",
) -> None:
    # make a dict to keep track of when we last updated the values
    curr_data: str = ""
    data: typing.Dict[str, float] = {}

    for i in range(num_request):
        try:
            start = time.perf_counter()

            r = urllib.request.Request(
                endpoint,
                headers={"Content-Type": "text/plain"},
            )

            res = urllib.request.urlopen(r)
            end = time.perf_counter()

            # get the result
            status_code = res.status
            res = res.read().decode("ascii")

            # check if we have the right value
            staleness = 0

            # try getting new data first
            while update_pipe.poll():
                update_time, d = update_pipe.recv()
                # note when old data was overwritten
                data[curr_data] = update_time
                curr_data = d
                # print(f"added data {d} to dict")

            if res == curr_data:
                # we do! no staleness detected
                pass
            else:
                # we don't! check when we last updated the value
                if res in data:
                    staleness = end - data[res]  # type: ignore
                    staleness = max(staleness, 0)
                else:
                    # print(f"could not find data {res} in dict")
                    # that means its a new value
                    staleness = 0

            # get the result
            out_queue.put(("r", start, end, staleness, status_code))

        except urllib.error.HTTPError as e:
            print(e)

            res = e.code

            end = time.perf_counter()

            # get the result
            out_queue.put(("r", start, end, -1, res))

        st = 1 / frequency - (end - start)
        time.sleep(max(st, 0))

    out_queue.put(("r", -1, -1, -1, -1))

    return


if __name__ == "__main__":
    # get args
    # tinyfaas endpoint
    # function name
    # number of requests in total
    # frequency of requests (per second)
    # output file
    if len(sys.argv) != 7:
        print(
            "usage: python3 load-replication.py <endpoint-writer> <endpoint-reader> <requests> <frequency> <output <timeout_s>"
        )
        sys.exit(1)

    try:
        host_writer = sys.argv[1]
        host_reader = sys.argv[2]
        num_requests = int(sys.argv[3])
        frequency = int(sys.argv[4])
        output = sys.argv[5]
        timeout_s = int(sys.argv[6])

        if num_requests < 1 or frequency < 1:
            raise ValueError("invalid arguments")

    except:
        print("invalid arguments")
        print(
            "usage: python3 load-replication.py <endpoint-writer> <endpoint-reader> <requests> <frequency> <output <timeout_s>"
        )
        sys.exit(1)

    print(
        f"parameters: endpoint_writer={host_writer}, endpoint_reader={host_reader}, num_requests={num_requests}, frequency={frequency}, output={output}, timeout_s={timeout_s}"
    )

    # run the function
    q: "mp.Queue[typing.Tuple[str, int, float, float, int]]" = mp.Queue()

    reader_update_pipe, writer_update_pipe = mp.Pipe(duplex=False)

    writer_p = mp.Process(
        target=writer,
        args=(
            host_writer,
            num_requests,
            frequency,
            writer_update_pipe,
            q,
        ),
    )

    reader_p = mp.Process(
        target=reader,
        args=(
            host_reader,
            num_requests,
            frequency,
            reader_update_pipe,
            q,
        ),
    )

    start_time = time.perf_counter()

    writer_p.start()
    reader_p.start()

    with open(output, "w") as f:
        f.write("client,start,end,staleness,res\n")

        total_results = 0
        with tqdm.tqdm(total=2 * num_requests) as pbar:
            while total_results < 2 * num_requests:
                try:
                    m = q.get(timeout=1)

                    if m[0] == "w":
                        if m[1] == -1:
                            # thread is done
                            writer_p.join()
                            continue

                        # print(f"{t}: {end-start:.3f}s")
                        f.write(f"w,{m[1]},{m[2]},,{m[3]}\n")
                        total_results += 1
                        pbar.update(1)

                    elif m[0] == "r":
                        if m[1] == -1:
                            # thread is done
                            reader_p.join()
                            continue

                        # print(f"{t}: {end-start:.3f}s")
                        f.write(f"r,{m[1]},{m[2]},{m[3]},{m[4]}\n")
                        total_results += 1
                        pbar.update(1)

                except:
                    # note that this timeout will not work if results still come in
                    if time.perf_counter() - start_time > timeout_s:
                        print("reached experiment timeout")
                        reader_p.terminate()
                        writer_p.terminate()
                        break

    print("experiment finished in {:.3f}s".format(time.perf_counter() - start_time))
