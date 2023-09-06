#!/usr/bin/env python3

import os
import random
import subprocess
import sys
import typing


class Experiment:
    def __init__(
        self,
        deployment_mode: str,
        threads: int,
        delay_ms: int,
        bandwidth_mbps: int,
        delay_ms_clientedge: int,
        bandwidth_mbps_clientedge: int,
        duration: int,
        repeat: int,
        results_dir: str,
        output_dir: str,
    ):
        self.deployment_mode = deployment_mode
        self.threads = threads
        self.delay_ms = delay_ms
        self.bandwidth_mbps = bandwidth_mbps
        self.delay_ms_clientedge = delay_ms_clientedge
        self.bandwidth_mbps_clientedge = bandwidth_mbps_clientedge
        self.duration = duration
        self.repeat = repeat

        self.results_file = os.path.join(
            results_dir,
            f"{deployment_mode}-{threads}-{delay_ms}-{bandwidth_mbps}-{repeat}-{delay_ms_clientedge}-{bandwidth_mbps_clientedge}-{duration}.csv",
        )

        self.output_file = os.path.join(
            output_dir,
            f"{deployment_mode}-{threads}-{delay_ms}-{bandwidth_mbps}-{repeat}-{delay_ms_clientedge}-{bandwidth_mbps_clientedge}-{duration}.txt",
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
                    "./run-befaas.sh",
                    self.deployment_mode,
                    self.results_file,
                    str(self.threads),
                    str(self.delay_ms),
                    str(self.bandwidth_mbps),
                    str(self.delay_ms_clientedge),
                    str(self.bandwidth_mbps_clientedge),
                    str(self.duration),
                ],
                stdout=f,
                stderr=f,
            )

        print(f"Finished experiment: {self.results_file}")


if __name__ == "__main__":
    deployment_modes = ["edge", "cloud"]  # , "allcloud"]
    threads = 1
    delay_ms = 25  # ms, one-way
    bandwidth_mbps = 100  # Mbps

    delay_ms_clientedge = 1  # ms, one-way
    bandwidth_mbps_clientedge = 10  # Mbps

    repeats = [1, 2, 3]
    # repeats = [1]
    duration = 60 * 10  # 60  # seconds

    results_dir = "results/results-befaas/raw"
    os.makedirs(results_dir, exist_ok=True)

    output_dir = "output/output-befaas"
    os.makedirs(output_dir, exist_ok=True)

    preparation_file = os.path.join(output_dir, "preparation.txt")

    experiments = []

    for m in deployment_modes:
        for r in repeats:
            e = Experiment(
                deployment_mode=m,
                threads=threads,
                delay_ms=delay_ms,
                bandwidth_mbps=bandwidth_mbps,
                delay_ms_clientedge=delay_ms_clientedge,
                bandwidth_mbps_clientedge=bandwidth_mbps_clientedge,
                duration=duration,
                repeat=r,
                results_dir=results_dir,
                output_dir=output_dir,
            )
            experiments.append(e)

    # randomize the order of experiments
    random.seed(0)
    random.shuffle(experiments)

    # prepare
    with open(preparation_file, "w") as f:
        print("Preparing...")
        print(f"Output: {preparation_file}")
        subprocess.run(["./prep-befaas.sh"], stdout=f, stderr=f)

    try:
        for e in experiments:
            e.run()
    except Exception as e:
        print(e)
    except KeyboardInterrupt:
        print("KeyboardInterrupt")

    with open(preparation_file, "a") as f:
        print("Cleaning up...")
        print(f"Output: {preparation_file}")
        subprocess.run(["terraform", "destroy", "-auto-approve"], stdout=f, stderr=f)
