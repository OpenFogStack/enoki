# Enoki: Stateful Distributed FaaS from Edge to Cloud

Enoki is a prototype FaaS platform for the edge-cloud that integrates replicated data access.

## Research

If you use this software in a publication, please cite it as:

### Text

T. Pfandzelter and D. Bermbach, **Enoki: Stateful Distributed FaaS from Edge to Cloud**, Proceedings of the 2nd International Workshop on Middleware for the Edge (MiddleWEdge '23), Bologna, Italy. ACM New York, NY, USA, 2023.

### BibTeX

```bibtex
@inproceedings{pfandzelter2023enoki,
    author = "Pfandzelter, Tobias and Bermbach, David",
    title = "Enoki: Stateful Distributed FaaS from Edge to Cloud",
    booktitle = "Proceedings of the 2nd International Workshop on Middleware for the Edge (MiddleWEdge '23)",
    month = dec,
    year = 2023,
    publisher = "ACM",
    address = "New York, NY, USA",
    location = "Bologna, Italy",
    doi = "10.1145/3630180.3631203"
}

```

A preprint is available on [arXiv](https://arxiv.org/abs/2309.03584).
For a full list of publications, please see [our website](https://www.tu.berlin/en/mcc/research/publications).

### License

The code in this repository is licensed under the terms of the [MIT](./LICENSE) license.

## Usage

To run Enoki locally, we recommend checking out the `prep-simple.sh` and `run-simple.sh` scripts.
At its core, Enoki requires a running `fred` instance and certificates to start.

## Experiments

To replicate the experiments used in our paper, use the provided scripts.

### Prerequisites

To run experiments, you will need:

- a local machine running Debian 11 or a similar Linux distribution (modifications are needed for other distributions and macOS)
- an active Google Cloud Platform project (note the project ID)

Install these dependencies on your local machine:

```sh
sudo apt-get update
sudo apt-get install apt-transport-https ca-certificates gnupg curl sudo rsync jq zip bc multitail python3-pip
python3 -m pip install -r requirements.txt
```

Install the `gcloud` CLI according to [the documentation](https://cloud.google.com/sdk/docs/install#deb).
Configure the `gcloud` CLI for your project with `gcloud auth login --no-launch-browser`.

Install `terraform` (>v1.0) as outlined in [the documentation](https://developer.hashicorp.com/terraform/downloads).
Configure your Google Cloud credentials for Terraform with `gcloud auth application-default login` and then run `terraform init`.

Install Go (>=v1.20):

```sh
wget <https://go.dev/dl/go1.20.7.linux-amd64.tar.gz>
rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.20.7.linux-amd64.tar.gz
echo "export PATH=$PATH:/usr/local/go/bin" >> .bashrc
source .bashrc
go version
```

### Running Experiments

Before you run any experiments, make sure to update the settings in `variables.tf`.
Configure your Google Cloud project ID and your preferred Google Cloud Compute region and availability zone.

For each of the four experiments outlined in our paper (`simple`, `scale`, `replication`, and `befaas`), we include an automated `experiment-*.py` Python script.
The scripts provide only limited output on `stdout`, with most output piped to the `output` directory.

Run each script in a separate screen and then monitor output using `multitail`:

```sh
# open a new screen
screen
# start the experiment
./experiment-NAME.py
# exit the screen with CTRL-A + D

# monitor progress
multitail -cT ANSI -iw "output-NAME/*" 5
```

Resources on Google Cloud platform are automatically started and destroyed for you.
Note that it might be necessary to remove old results in the `results` directory before you can run new experiments.

### Analysis

To run the analysis and generate graphs, use the included `graphs-*.py` scripts.
Note that for the BeFaaS experiments, a separate cleaning step is necessary:

```sh
./sortlogs-befaas.py ./results/results-befaas/raw ./results/results-befaas
```
