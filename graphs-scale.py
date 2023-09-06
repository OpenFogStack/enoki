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

results_dir = "results/results-scale"

dfs = []

for results_file in os.listdir(results_dir):
    df = pd.read_csv(os.path.join(results_dir, results_file))

    (
        function,
        parameter,
        threads,
        load_time,
        load_threads,
        delay_ms,
        bandwidth_mbps,
        delay_ms_client_edge,
        bandwidth_mbps_client_edge,
        deploymentmode,
        repeat,
    ) = Path(results_file).stem.split("-")

    df["function"] = str(function)
    df["parameter"] = int(parameter)
    df["threads"] = int(threads)
    df["load_time"] = float(load_time)
    df["load_threads"] = int(load_threads)
    df["delay_ms"] = int(delay_ms)
    df["bandwidth_mbps"] = int(bandwidth_mbps)
    df["delay_ms_client_edge"] = int(delay_ms_client_edge)
    df["bandwidth_mbps_client_edge"] = int(bandwidth_mbps_client_edge)
    df["deploymentmode"] = deploymentmode
    df["repeat"] = int(repeat)

    df["end_time"] = pd.to_datetime(df["end"])

    # filter non-200 responses
    df = df[df["res"] == 200]

    # sort by start time
    df = df.sort_values(by="end_time")

    # calculate the 10s rolling throughput by counting the rows in 10s windows
    df["throughput"] = (
        df.rolling(pd.Timedelta(value=10, unit="s"), on="end_time")["end"].count() / 10
    )

    # make the throughput in bytes
    df["throughput_bytes"] = df["throughput"] * df["parameter"]

    # cut off first 10 seconds
    df = df[df["start"] > df["start"].min() + 10]
    # cut off last 10 seconds
    df = df[df["start"] < df["start"].max() - 10]

    dfs.append(df)

df = pd.concat(dfs)

df["time"] = df["end"] - df["start"]

# convert to ms
df["time_ms"] = df["time"] * 1000

df.head()

# give unique experiments
# need function and parameter combinations that are unique
print(df[["function", "parameter"]].drop_duplicates())

# a better throughput dataframe
# count the rows, divide by the time between the start of the first and end of the last
df["bytes"] = df["parameter"]
throughput_df = df.groupby(["function", "parameter", "deploymentmode", "repeat"]).agg(
    {
        "bytes": "sum",
        "parameter": "first",
        "start": "min",
        "end": "max",
        "function": "first",
        "deploymentmode": "first",
        "repeat": "first",
    }
)
throughput_df = throughput_df.reset_index(drop=True)
throughput_df["throughput_bytes"] = throughput_df["bytes"] / (
    throughput_df["end"] - throughput_df["start"]
)
throughput_df.head()

# make it nicer to look at
throughput_df["Database Location"] = throughput_df["deploymentmode"].apply(
    lambda x: "Edge" if x == "edge" else "Cloud"
)
throughput_df["throughput_mbyteps"] = throughput_df["throughput_bytes"] / 1000000

# graph 1: reading!
r = 1
g = sns.lineplot(
    data=throughput_df[
        (throughput_df["function"] == "2_read") & (throughput_df["repeat"] == r)
    ],
    x="parameter",
    y="throughput_mbyteps",
    style="Database Location",
    legend="full",
    errorbar=("ci", 95),
    estimator="median",
    color="black",
    style_order=["Edge", "Cloud"],
    markers=["o", "^"],
)
# g.yaxis.set_major_formatter(matplotlib.ticker.EngFormatter(unit="B/s"))
g.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.1f"))
# g.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(5.0))
g.xaxis.set_major_formatter(matplotlib.ticker.EngFormatter(unit="B"))
g.xaxis.set_label_text("Data Item Size")
g.yaxis.set_label_text("Throughput (MB/s)")
sns.move_legend(g, "lower right", ncol=2)
plt.savefig("graphs/scale-read.pdf", bbox_inches="tight")

# graph 2: writing!
r = 1
g = sns.lineplot(
    data=throughput_df[
        (throughput_df["function"] == "3_write") & (throughput_df["repeat"] == r)
    ],
    x="parameter",
    y="throughput_mbyteps",
    style="Database Location",
    legend="full",
    errorbar=("ci", 95),
    estimator="median",
    color="black",
    style_order=["Edge", "Cloud"],
    markers=["o", "^"],
)
# g.yaxis.set_major_formatter(matplotlib.ticker.EngFormatter(unit="B/s"))
g.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.1f"))
g.xaxis.set_major_formatter(matplotlib.ticker.EngFormatter(unit="B"))
g.xaxis.set_label_text("Data Item Size")
g.yaxis.set_label_text("Throughput (MB/s)")
g.set(ylim=(-0.5, 10.5))
sns.move_legend(g, "lower right", ncol=2)
plt.savefig("graphs/scale-write.pdf", bbox_inches="tight")
