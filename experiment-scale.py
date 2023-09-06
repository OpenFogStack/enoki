#!/usr/bin/env python3

import math
import os
import random
import subprocess
import sys
import typing


class Experiment:
    def __init__(
        self,
        function: str,
        parameter: str,
        threads: int,
        load_time: int,
        load_threads: int,
        delay_ms: int,
        bandwidth_mbps: int,
        delay_ms_client_edge: int,
        bandwidth_mbps_client_edge: int,
        deployment_mode: str,
        timeout: int,
        repeat: int,
        results_dir: str,
        output_dir: str,
    ):
        self.function = function
        self.parameter = parameter
        self.threads = threads
        self.load_time = load_time
        self.load_threads = load_threads
        self.delay_ms = delay_ms
        self.bandwidth_mbps = bandwidth_mbps
        self.delay_ms_client_edge = delay_ms_client_edge
        self.bandwidth_mbps_client_edge = bandwidth_mbps_client_edge
        self.deployment_mode = deployment_mode
        self.timeout = timeout

        self.results_file = os.path.join(
            results_dir,
            f"{function}-{parameter}-{threads}-{load_time}-{load_threads}-{delay_ms}-{bandwidth_mbps}-{delay_ms_client_edge}-{bandwidth_mbps_client_edge}-{deployment_mode}-{repeat}.csv",
        )

        self.output_file = os.path.join(
            output_dir,
            f"{function}-{parameter}-{threads}-{load_time}-{load_threads}-{delay_ms}-{bandwidth_mbps}-{delay_ms_client_edge}-{bandwidth_mbps_client_edge}-{deployment_mode}-{repeat}.txt",
        )

    def run(self) -> None:
        # if the results file exists already, we can skip this experiment
        if os.path.exists(self.results_file):
            print(f"Skipping experiment: {self.results_file}")
            return

        print(f"Running experiment: {self.results_file}")
        print(f"Output: {self.output_file}")

        with open(self.output_file, "w") as f:
            subprocess.run(
                [
                    "./run-scale.sh",
                    self.function,
                    str(self.parameter),
                    str(self.threads),
                    str(self.load_time),
                    str(self.load_threads),
                    self.results_file,
                    str(self.delay_ms),
                    str(self.bandwidth_mbps),
                    str(self.delay_ms_client_edge),
                    str(self.bandwidth_mbps_client_edge),
                    self.deployment_mode,
                    str(self.timeout),
                ],
                stdout=f,
                stderr=f,
            )

        print(f"Finished experiment: {self.results_file}")

        # give stats
        # print results
        with open(self.results_file, "r") as f:
            lines = f.readlines()

            # remove header
            lines = [line.strip() for line in lines[1:]]

            # get the throughput by dividing the number of requests by the total time
            throughput = len(lines) / self.load_time
            print(f"Throughput: {throughput:.3f} requests/s")

            # get the bytes per second by multiplying the throughput by the size of the request
            try:
                bytes_per_second = throughput * float(self.parameter)
                print(f"Bytes per second: {bytes_per_second:.3f} bytes/s")
            except:
                pass


if __name__ == "__main__":
    # functions and inputs
    func = ["2_read", "3_write"]

    # what are some good parameters between 1 and 1024*1024?
    # gRPC has a 4MB limit
    param = [
        1,
        100,
        1000,
        10000,
        100000,
        250000,
        500000,
        750000,
        1000000,
    ]  # , 1000000, 5000000, 10000000, 5000000]
    # param = [1000000]

    functions = {f: param for f in func}

    threads = [4]
    # load_requests = 1
    # target_frequency = 20  # Hz
    load_threads = 100
    load_time = 120 + 30  # s
    # load_frequency = [0.025]
    # load_frequency = target_frequency / load_threads
    delay_ms = 25  # ms, one-way
    bandwidth_mbps = 100  # Mbps
    delay_ms_client_edge = 1  # ms, one-way
    bandwidth_mbps_client_edge = 10  # Mbps
    deployment_modes = ["edge", "cloud"]
    repeats = [1, 2, 3]

    results_dir = "results/results-scale"
    os.makedirs(results_dir, exist_ok=True)

    output_dir = "output/output-scale"
    os.makedirs(output_dir, exist_ok=True)

    preparation_file = os.path.join(output_dir, "preparation.txt")

    experiments = []

    for f in functions:
        for p in functions[f]:
            for t in threads:
                for m in deployment_modes:
                    for r in repeats:
                        # experiment should run about 2 minutes
                        # load_requests = math.ceil((2 * 60) * load_frequency)
                        timeout = 3 * 60

                        e = Experiment(
                            function=f,
                            parameter=str(p),
                            threads=t,
                            load_time=int(load_time),
                            load_threads=load_threads,
                            delay_ms=delay_ms,
                            bandwidth_mbps=bandwidth_mbps,
                            delay_ms_client_edge=delay_ms_client_edge,
                            bandwidth_mbps_client_edge=bandwidth_mbps_client_edge,
                            deployment_mode=m,
                            timeout=timeout,
                            repeat=r,
                            results_dir=results_dir,
                            output_dir=output_dir,
                        )
                        experiments.append(e)

    # randomize the order of experiments
    random.seed(0)
    random.shuffle(experiments)

    # prepare
    with open(preparation_file, "w") as of:
        print("Preparing...")
        print(f"Output: {preparation_file}")
        subprocess.run(["./prep.sh"], stdout=of, stderr=of)

    try:
        for e in experiments:
            e.run()
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("KeyboardInterrupt")

    with open(preparation_file, "a") as of:
        print("Cleaning up...")
        print(f"Output: {preparation_file}")
        subprocess.run(["terraform", "destroy", "-auto-approve"], stdout=of, stderr=of)
