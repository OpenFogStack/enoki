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
mpl.rcParams["figure.figsize"] = (4.5, 2)
mpl.rcParams["figure.dpi"] = 100

results_dir = "results/results-replication"

write_dfs = []
read_dfs = []

for results_file in os.listdir(results_dir):
    df = pd.read_csv(os.path.join(results_dir, results_file))

    (
        function,
        threads,
        load_time,
        load_frequency,
        delay_ms,
        bandwidth_mbps,
        delay_ms_client_edge,
        bandwidth_mbps_client_edge,
        delay_ms_edge_edge,
        bandwidth_mpbs_edge_edge,
        deploymentmode,
        repeat,
    ) = Path(results_file).stem.split("-")

    df["deploymentmode"] = deploymentmode
    df["repeat"] = int(repeat)

    # filter non-200 responses
    print(f"dropping {len(df[df['res'] != 200])} non-200 responses")
    df = df[df["res"] == 200]

    # cut off first 10 seconds
    df = df[df["start"] > df["start"].min() + 10]
    # cut off last 10 seconds
    df = df[df["start"] < df["start"].max() - 10]

    df["staleness_ms"] = df["staleness"] * 1000

    read_dfs.append(df[df["client"] == "r"])
    write_dfs.append(df[df["client"] == "w"])


write_df = pd.concat(write_dfs)
read_df = pd.concat(read_dfs)

write_df["time"] = write_df["end"] - write_df["start"]
read_df["time"] = read_df["end"] - read_df["start"]

# convert to ms
write_df["time_ms"] = write_df["time"] * 1000
read_df["time_ms"] = read_df["time"] * 1000

read_df["Replication Mode"] = read_df["deploymentmode"].apply(
    lambda x: "Cloud"
    if x == "cloud"
    else "Edge (No Repl.)"
    if x == "p2p"
    else "Edge (Repl.)"
)

write_df["Replication Mode"] = write_df["deploymentmode"].apply(
    lambda x: "Cloud"
    if x == "cloud"
    else "Edge (No Repl.)"
    if x == "p2p"
    else "Edge (Repl.)"
)

r = 1
fig, g = plt.subplots(figsize=(2.8, 1.8))

sns.ecdfplot(
    ax=g,
    data=read_df[(read_df["repeat"] == r)],
    x="time_ms",
    hue="Replication Mode",
    palette=["black"] * 3,
    hue_order=["Cloud", "Edge (No Repl.)", "Edge (Repl.)"],
)
g.xaxis.set_label_text("Request-Response Latency (ms)")
g.yaxis.set_label_text("Empirical Cumulative\nDistribution")
for lines, linestyle, legend_handle in zip(
    g.lines[::-1], ["solid", "dashed", "dotted"], g.legend_.legend_handles
):
    lines.set_linestyle(linestyle)
    legend_handle.set_linestyle(linestyle)
sns.move_legend(g, "lower center")
g.set(xlim=(-0.5, 70.5))
plt.savefig("graphs/replication-read.pdf", bbox_inches="tight")

r = 1
fig, g = plt.subplots(figsize=(2.8, 1.8))

sns.ecdfplot(
    ax=g,
    data=write_df[(write_df["repeat"] == r)],
    x="time_ms",
    hue="Replication Mode",
    palette=["black"] * 3,
    hue_order=["Cloud", "Edge (No Repl.)", "Edge (Repl.)"],
)
g.xaxis.set_label_text("Request-Response Latency (ms)")
g.yaxis.set_label_text("Empirical Cumulative\nDistribution")
for lines, linestyle, legend_handle in zip(
    g.lines[::-1], ["solid", "dashed", "dotted"], g.legend_.legend_handles
):
    lines.set_linestyle(linestyle)
    legend_handle.set_linestyle(linestyle)
sns.move_legend(g, "lower center")
g.set(xlim=(-0.5, 70.5))
plt.savefig("graphs/replication-write.pdf", bbox_inches="tight")

r = 1
fig, g = plt.subplots(figsize=(2.8, 1.8))

sns.ecdfplot(
    ax=g,
    data=read_df[(read_df["repeat"] == r)],
    x="staleness_ms",
    hue="Replication Mode",
    palette=["black"] * 3,
    hue_order=["Cloud", "Edge (No Repl.)", "Edge (Repl.)"],
)
g.xaxis.set_label_text("Read Staleness (ms)")
g.yaxis.set_label_text("Empirical Cumulative\nDistribution")
for lines, linestyle, legend_handle in zip(
    g.lines[::-1], ["solid", "dashed", "dotted"], g.legend_.legend_handles
):
    lines.set_linestyle(linestyle)
    legend_handle.set_linestyle(linestyle)
sns.move_legend(g, "lower right")
g.set(xlim=(-0.5, 8.5))
plt.savefig("graphs/replication-staleness.pdf", bbox_inches="tight")
