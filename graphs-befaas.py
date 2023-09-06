#!/usr/bin/env python3

import os
import itertools
import glob
import datetime

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

results_folder = "results/results-befaas"

deployment_modes = ["edge", "cloud"]
repeat = [1, 2, 3]

dfs = []
for m in deployment_modes:
    for r in repeat:
        df = pd.read_csv(f"{results_folder}/{m}-1-25-100-{r}-1-10-600-sorted.csv")
        df["deployment"] = m
        df["repeat"] = r

        dfs.append(df)

df = pd.concat(dfs)

graph_df = df[
    (df["time_type"] == "total")
    & (
        (df["function"] == "weathersensorfilter")
        | (df["function"] == "trafficsensorfilter")
        | (df["function"] == "objectrecognition")
    )
]
graph_df["time_ms"] = graph_df["time"] * 1000
graph_df["Database Location"] = graph_df["deployment"].apply(
    lambda x: "Edge" if x == "edge" else "Cloud"
)

fig, g = plt.subplots(figsize=(2.8, 1.8))
r = 2
g = sns.ecdfplot(
    ax=g,
    data=graph_df[
        (graph_df["function"] == "weathersensorfilter") & (graph_df["repeat"] == r)
    ],
    x="time_ms",
    hue="Database Location",
    palette=["black"] * 2,
)
g.xaxis.set_label_text("Execution Duration (ms)")
g.yaxis.set_label_text("Empirical Cumulative\nDistribution")
for lines, linestyle, legend_handle in zip(
    g.lines[::-1], ["-", "--"], g.legend_.legend_handles
):
    lines.set_linestyle(linestyle)
    legend_handle.set_linestyle(linestyle)
sns.move_legend(g, "lower right", ncol=2)
plt.savefig("graphs/befaas-weathersensorfilter.pdf", bbox_inches="tight")

fig, g = plt.subplots(figsize=(2.8, 1.8))
r = 2
g = sns.ecdfplot(
    ax=g,
    data=graph_df[
        (graph_df["function"] == "trafficsensorfilter") & (graph_df["repeat"] == r)
    ],
    x="time_ms",
    hue="Database Location",
    palette=["black"] * 2,
)
g.xaxis.set_label_text("Execution Duration (ms)")
g.yaxis.set_label_text("Empirical Cumulative\nDistribution")
for lines, linestyle, legend_handle in zip(
    g.lines[::-1], ["-", "--"], g.legend_.legend_handles
):
    lines.set_linestyle(linestyle)
    legend_handle.set_linestyle(linestyle)
sns.move_legend(g, "lower right", ncol=2)
plt.savefig("graphs/befaas-trafficsensorfilter.pdf", bbox_inches="tight")

fig, g = plt.subplots(figsize=(2.8, 1.8))
r = 2
sns.ecdfplot(
    ax=g,
    data=graph_df[
        (graph_df["function"] == "objectrecognition") & (graph_df["repeat"] == r)
    ],
    x="time_ms",
    hue="Database Location",
    palette=["black"] * 2,
)
g.xaxis.set_label_text("Execution Duration (ms)")
g.yaxis.set_label_text("Empirical Cumulative\nDistribution")
for lines, linestyle, legend_handle in zip(
    g.lines[::-1], ["-", "--"], g.legend_.legend_handles
):
    lines.set_linestyle(linestyle)
    legend_handle.set_linestyle(linestyle)
sns.move_legend(g, "lower right", ncol=2)
g.set_xlim(-50, 1550)
plt.savefig("graphs/befaas-objectrecognition.pdf", bbox_inches="tight")
