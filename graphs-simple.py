#!/usr/bin/env python3
import os
import itertools
import glob
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.ticker
import matplotlib.pyplot as plt

sns.set(font_scale=0.9, style="whitegrid", font="CMU Sans Serif")
pal = sns.color_palette(
    ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]
)
sns.set_palette(pal)

mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
mpl.rcParams["figure.figsize"] = (4.5, 1.8)
mpl.rcParams["figure.dpi"] = 100

results_dir = "results/results-simple"

dfs = []

for results_file in os.listdir(results_dir):
    df = pd.read_csv(os.path.join(results_dir, results_file))

    (
        function,
        parameter,
        threads,
        load_requests,
        load_threads,
        load_frequency,
        delay_ms,
        bandwidth_mbps,
        delay_ms_client_edge,
        bandwidth_mbps_client_edge,
        deploymentmode,
        repeat,
    ) = Path(results_file).stem.split("-")

    df["function"] = str(function)
    df["parameter"] = str(parameter)
    df["threads"] = int(threads)
    df["load_requests"] = int(load_requests)
    df["load_threads"] = int(load_threads)
    df["load_frequency"] = int(load_frequency)
    df["delay_ms"] = int(delay_ms)
    df["bandwidth_mbps"] = int(bandwidth_mbps)
    df["delay_ms_client_edge"] = int(delay_ms_client_edge)
    df["bandwidth_mbps_client_edge"] = int(bandwidth_mbps_client_edge)
    df["deploymentmode"] = deploymentmode
    df["repeat"] = int(repeat)

    # cut off the first 20 seconds of each experiment
    df = df[df["start"] > df["start"].min() + 20]

    dfs.append(df)

df = pd.concat(dfs)

df["time"] = df["end"] - df["start"]
# some nice ECDF plots again
graph_df = df[(df["load_frequency"] == 1) & (df["load_threads"] == 10)]

graph_df["time_ms"] = graph_df["time"] * 1000

graph_df["Database Location"] = graph_df["deploymentmode"].apply(
    lambda x: "Edge" if x == "edge" else "Cloud"
)

r = 2
fig, g = plt.subplots(figsize=(4.5, 1.8))

sns.ecdfplot(
    ax=g,
    data=graph_df[(graph_df["repeat"] == r)],
    x="time_ms",
    hue="Database Location",
    palette=["black"] * 2,
    hue_order=["Edge", "Cloud"],
)
g.xaxis.set_label_text("Request-Response Latency (ms)")
g.yaxis.set_label_text("Empirical Cumulative\nDistribution")
for lines, linestyle, legend_handle in zip(
    g.lines[::-1], ["-", "--"], g.legend_.legend_handles
):
    lines.set_linestyle(linestyle)
    legend_handle.set_linestyle(linestyle)
sns.move_legend(g, "lower center", ncol=2)
# g.set(xlim=(-10, 260))

plt.savefig("graphs/simple-movingaverage.pdf", bbox_inches="tight")
