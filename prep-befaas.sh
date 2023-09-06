#!/bin/bash

set -x

# compile tinyfaas
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o manager -v github.com/OpenFogStack/tinyFaaS/cmd/manager
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o rproxy -v github.com/OpenFogStack/tinyFaaS/cmd/rproxy

# terraform init
terraform init

terraform apply -auto-approve

# get the ip addresses

CLOUD_IP="$(terraform output -json | jq -r '.cloud_ip.value')"
EDGE_IP="$(terraform output -json | jq -r '.edge_ip.value')"
CLIENT_IP="$(terraform output -json | jq -r '.client_ip.value')"

echo $CLOUD_IP
echo $EDGE_IP
echo $CLIENT_IP

# get the instance names

CLOUD_INSTANCE="$(terraform output -json | jq -r '.cloud_name.value')"
EDGE_INSTANCE="$(terraform output -json | jq -r '.edge_name.value')"
CLIENT_INSTANCE="$(terraform output -json | jq -r '.client_name.value')"

gcloud compute config-ssh

until ssh -o StrictHostKeyChecking=no "$CLOUD_INSTANCE" echo
do
  echo "cloud instance not ready yet"
  sleep 1
done

until ssh -o StrictHostKeyChecking=no "$EDGE_INSTANCE" echo
do
  echo "edge instance not ready yet"
  sleep 1
done

until ssh -o StrictHostKeyChecking=no "$CLIENT_INSTANCE" echo
do
  echo "client instance not ready yet"
  sleep 1
done

# generate some certificates
CERTS_DIR=certs

mkdir -p "$CERTS_DIR"
openssl genrsa -out "$CERTS_DIR/ca.key" 2048

CA_CERT="$CERTS_DIR/ca.crt"
openssl req -x509 -new -nodes -key "$CERTS_DIR/ca.key" -days 1825 -sha512 -out "$CA_CERT" -subj "/C=DE/L=Berlin/O=OpenFogStack/OU=enoki"

./gen-cert.sh "$CERTS_DIR" etcd "$CLOUD_IP"

./gen-cert.sh "$CERTS_DIR" fredcloud "$CLOUD_IP"

./gen-cert.sh "$CERTS_DIR" frededge "$EDGE_IP"

# copy the files
scp -r "$CERTS_DIR" "$CLOUD_INSTANCE:~"
scp -r "$CERTS_DIR" "$EDGE_INSTANCE:~"

scp manager "$CLOUD_INSTANCE:~"
scp rproxy "$CLOUD_INSTANCE:~"
scp -r runtimes "$CLOUD_INSTANCE:~"

scp manager "$EDGE_INSTANCE:~"
scp rproxy "$EDGE_INSTANCE:~"
scp -r runtimes "$EDGE_INSTANCE:~"

scp load-befaas.py "$CLIENT_INSTANCE:~"
scp misc/image-ambulance.jpg "$CLIENT_INSTANCE:~"
scp misc/image-noambulance.jpg "$CLIENT_INSTANCE:~"

# install docker
ssh "$CLOUD_INSTANCE" curl -fsSL https://get.docker.com -o get-docker.sh
ssh "$CLOUD_INSTANCE" sudo sh get-docker.sh &

ssh "$EDGE_INSTANCE" curl -fsSL https://get.docker.com -o get-docker.sh
ssh "$EDGE_INSTANCE" sudo sh get-docker.sh &
wait

# prepare the cloud
user=$(ssh "$CLOUD_INSTANCE" whoami)

ssh "$CLOUD_INSTANCE" sudo usermod -aG docker "$user"

# prepare the edge
user=$(ssh "$EDGE_INSTANCE" whoami)

ssh "$EDGE_INSTANCE" sudo usermod -aG docker "$user"

# prepare the client
ssh "$CLIENT_INSTANCE" sudo apt-get update
ssh "$CLIENT_INSTANCE" sudo apt-get install -y python3-pip
ssh "$CLIENT_INSTANCE" python3 -m pip install tqdm==4.65.0


# destroy the machines
set +x

echo "to destroy the machines run: terraform destroy -auto-approve"
