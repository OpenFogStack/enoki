#!/usr/bin/env python3

import os
import random
import subprocess
import sys
import typing


class Experiment:
    def __init__(
        self,
        function: str,
        threads: int,
        load_requests: int,
        load_frequency: int,
        delay_ms: int,
        bandwidth_mbps: int,
        delay_ms_client_edge: int,
        bandwidth_mbps_client_edge: int,
        delay_ms_edge_edge: int,
        bandwidth_mbps_edge_edge: int,
        deployment_mode: str,
        timeout: int,
        repeat: int,
        results_dir: str,
        output_dir: str,
    ):
        self.function = function
        self.threads = threads
        self.load_requests = load_requests
        self.load_frequency = load_frequency
        self.delay_ms = delay_ms
        self.bandwidth_mbps = bandwidth_mbps
        self.delay_ms_client_edge = delay_ms_client_edge
        self.bandwidth_mbps_client_edge = bandwidth_mbps_client_edge
        self.delay_ms_edge_edge = delay_ms_edge_edge
        self.bandwidth_mbps_edge_edge = bandwidth_mbps_edge_edge
        self.deployment_mode = deployment_mode
        self.timeout = timeout
        self.repeat = repeat

        self.results_file = os.path.join(
            results_dir,
            f"{function}-{threads}-{load_requests}-{load_frequency}-{delay_ms}-{bandwidth_mbps}-{delay_ms_client_edge}-{bandwidth_mbps_client_edge}-{delay_ms_edge_edge}-{bandwidth_mbps_edge_edge}-{deployment_mode}-{repeat}.csv",
        )

        self.output_file = os.path.join(
            output_dir,
            f"{function}-{threads}-{load_requests}-{load_frequency}-{delay_ms}-{bandwidth_mbps}-{delay_ms_client_edge}-{bandwidth_mbps_client_edge}-{delay_ms_edge_edge}-{bandwidth_mbps_edge_edge}-{deployment_mode}-{repeat}.txt",
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
                    "./run-replication.sh",
                    self.function,
                    str(self.threads),
                    str(self.load_requests),
                    str(self.load_frequency),
                    self.results_file,
                    str(self.delay_ms),
                    str(self.bandwidth_mbps),
                    str(self.delay_ms_client_edge),
                    str(self.bandwidth_mbps_client_edge),
                    str(self.delay_ms_edge_edge),
                    str(self.bandwidth_mbps_edge_edge),
                    self.deployment_mode,
                    str(self.timeout),
                ],
                stdout=f,
                stderr=f,
            )

        print(f"Finished experiment: {self.results_file}")

        # give stats
        # print results
        try:
            with open(self.results_file, "r") as f:
                lines = f.readlines()

                # remove header
                lines = [line.strip() for line in lines[1:]]

                # get mean, median, 95th, 99th
                stalenesses = [
                    float(line.split(",")[3]) for line in lines if line[0] == "r"
                ]
                stalenesses.sort()

                mean = sum(stalenesses) / len(stalenesses)
                median = stalenesses[len(stalenesses) // 2]
                p95 = stalenesses[int(len(stalenesses) * 0.95)]
                p99 = stalenesses[int(len(stalenesses) * 0.99)]

                print(f"mean stalenesses: {mean:.3f}s")
                print(f"median stalenesses: {median:.3f}s")
                print(f"95th stalenesses: {p95:.3f}s")
                print(f"99th stalenesses: {p99:.3f}s")

                read_times = [
                    (float(line.split(",")[2]) - float(line.split(",")[1]))
                    for line in lines
                    if line[0] == "r"
                ]
                read_times.sort()

                mean = sum(read_times) / len(read_times)
                median = read_times[len(read_times) // 2]
                p95 = read_times[int(len(read_times) * 0.95)]
                p99 = read_times[int(len(read_times) * 0.99)]

                print(f"mean read times: {mean:.3f}s")
                print(f"median read times: {median:.3f}s")
                print(f"95th read times: {p95:.3f}s")
                print(f"99th read times: {p99:.3f}s")

                write_times = [
                    (float(line.split(",")[2]) - float(line.split(",")[1]))
                    for line in lines
                    if line[0] == "w"
                ]
                write_times.sort()

                mean = sum(write_times) / len(write_times)
                median = write_times[len(write_times) // 2]
                p95 = write_times[int(len(write_times) * 0.95)]
                p99 = write_times[int(len(write_times) * 0.99)]

                print(f"mean write times: {mean:.3f}s")
                print(f"median write times: {median:.3f}s")
                print(f"95th write times: {p95:.3f}s")
                print(f"99th write times: {p99:.3f}s")

        except Exception as e:
            print(e)
            print("Failed to get stats")


if __name__ == "__main__":
    # functions and inputs

    function = "6_replication"
    # experiment length about 5 minutes?
    experiment_length = 5 * 60

    # load frequency about 10 requests per second?
    load_frequency = 10

    # number of requests
    num_requests = experiment_length * load_frequency

    threads = 4

    delay_ms = 25  # ms, one-way
    bandwidth_mbps = 100  # Mbps

    delay_ms_client_edge = 1  # ms, one-way
    bandwidth_mbps_client_edge = 10  # Mbps

    delay_ms_edge_edge = 10  # ms, one-way
    bandwidth_mbps_edge_edge = 100  # Mbps

    deployment_modes = ["edge", "cloud", "p2p"]

    repeats = [1, 2, 3]

    results_dir = "results/results-replication"
    os.makedirs(results_dir, exist_ok=True)

    output_dir = "output/output-replication"
    os.makedirs(output_dir, exist_ok=True)

    preparation_file = os.path.join(output_dir, "preparation.txt")

    experiments = []

    for m in deployment_modes:
        for r in repeats:
            e = Experiment(
                function=function,
                threads=threads,
                load_requests=num_requests,
                load_frequency=load_frequency,
                delay_ms=delay_ms,
                bandwidth_mbps=bandwidth_mbps,
                delay_ms_client_edge=delay_ms_client_edge,
                bandwidth_mbps_client_edge=bandwidth_mbps_client_edge,
                delay_ms_edge_edge=delay_ms_edge_edge,
                bandwidth_mbps_edge_edge=bandwidth_mbps_edge_edge,
                deployment_mode=m,
                timeout=experiment_length + 30,
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
        subprocess.run(["./prep-replication.sh"], stdout=of, stderr=of)

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
        subprocess.run(
            ["terraform", "destroy", "-auto-approve", "-var=second_edge_host=true"],
            stdout=of,
            stderr=of,
        )
