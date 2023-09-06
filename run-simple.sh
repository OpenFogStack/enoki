#!/bin/bash

set -x

# PARAMETERS
# FUNCTION="1_integer" # TODO
# PARAMETER
# THREADS=4
# LOAD_REQUESTS=100
# LOAD_THREADS=1
# LOAD_FREQUENCY=1
# OUTPUT_FILE="results.csv"
# DELAY=10 # ms, one-way
# BANDWIDTH_MBPS=100 # Mbps

# DEPLOYMENT_MODE="edge" # cloud or edge

FUNCTION="$1"
PARAMETER="$2"
THREADS="$3"
LOAD_REQUESTS="$4"
LOAD_THREADS="$5"
LOAD_FREQUENCY="$6"
OUTPUT_FILE="$7"
DELAY="$8"
BANDWIDTH_MBPS="$9"
DELAY_CLIENT_EDGE="${10}"
BANDWIDTH_CLIENT_EDGE_MBPS="${11}"
DEPLOYMENT_MODE="${12}"
TIMEOUT="${13}"

# check that the function exists
if [ ! -d "functions/$FUNCTION" ]; then
    echo "invalid function"
    exit 1
fi

# check that we have the required parameters
if [ -z "$FUNCTION" ] || [ -z "$PARAMETER" ] || [ -z "$THREADS" ] || [ -z "$LOAD_REQUESTS" ] || [ -z "$LOAD_THREADS" ] || [ -z "$LOAD_FREQUENCY" ] || [ -z "$OUTPUT_FILE" ] || [ -z "$DELAY" ] || [ -z "$BANDWIDTH_MBPS" ] || [ -z "$DELAY_CLIENT_EDGE" ] || [ -z "$BANDWIDTH_CLIENT_EDGE_MBPS" ] || [ -z "$DEPLOYMENT_MODE" ] || [ -z "$TIMEOUT" ]; then
    echo "missing parameters"
    echo "usage: ./run-simple.sh <function> <parameter> <threads> <load_requests> <load_threads> <load_frequency> <output_file> <delay> <bandwidth_mbps> <delay_client_edge> <bandwidth_client_edge_mbps> <deployment_mode> <timeout>"
    exit 1
fi

# check that the deployment mode is valid
if [ "$DEPLOYMENT_MODE" != "cloud" ] && [ "$DEPLOYMENT_MODE" != "edge" ]; then
    echo "invalid deployment mode"
    exit 1
fi
# get the instance names

CLOUD_INSTANCE="$(terraform output -json | jq -r '.cloud_name.value')"
EDGE_INSTANCE="$(terraform output -json | jq -r '.edge_name.value')"
CLIENT_INSTANCE="$(terraform output -json | jq -r '.client_name.value')"

ZONE="$(terraform output -json | jq -r '.zone.value')"

CLOUD_NAME="$(terraform output -json | jq -r '.cloud_id.value')"
EDGE_NAME="$(terraform output -json | jq -r '.edge_id.value')"
CLIENT_NAME="$(terraform output -json | jq -r '.client_id.value')"

# restart the machines
gcloud compute instances stop --zone="$ZONE" "$CLOUD_NAME" &
gcloud compute instances stop --zone="$ZONE" "$EDGE_NAME" &
gcloud compute instances stop --zone="$ZONE" "$CLIENT_NAME" &
wait

sleep 5

gcloud compute instances start --zone="$ZONE" "$CLOUD_NAME" &
gcloud compute instances start --zone="$ZONE" "$EDGE_NAME" &
gcloud compute instances start --zone="$ZONE" "$CLIENT_NAME" &
wait

sleep 5

# get the ip addresses

CLOUD_IP="$(gcloud compute instances describe --zone="$ZONE" "$CLOUD_NAME" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
EDGE_IP="$(gcloud compute instances describe --zone="$ZONE" "$EDGE_NAME" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"
CLIENT_IP="$(gcloud compute instances describe --zone="$ZONE" "$CLIENT_NAME" --format='get(networkInterfaces[0].accessConfigs[0].natIP)')"

echo "$CLOUD_IP"
echo "$EDGE_IP"
echo "$CLIENT_IP"

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

ssh "$CLOUD_INSTANCE" docker system prune -f &
ssh "$EDGE_INSTANCE" docker system prune -f &
wait

# generate some certificates
CERTS_DIR=certs
CA_CERT="$CERTS_DIR/ca.crt"

ETCD_CERT="$CERTS_DIR/etcd.crt"
ETCD_KEY="$CERTS_DIR/etcd.key"

FREDCLOUD_CERT="$CERTS_DIR/fredcloud.crt"
FREDCLOUD_KEY="$CERTS_DIR/fredcloud.key"

FREDEDGE_CERT="$CERTS_DIR/frededge.crt"
FREDEDGE_KEY="$CERTS_DIR/frededge.key"

# run the cloud
home=$(ssh "$CLOUD_INSTANCE" pwd)

## start etcd instance
ssh "$CLOUD_INSTANCE" docker run \
    -v "$home/$ETCD_CERT:/cert/etcd.crt" \
    -v "$home/$ETCD_KEY:/cert/etcd.key" \
    -v "$home/$CA_CERT:/cert/ca.crt" \
    -p 2379:2379 \
    -d \
    gcr.io/etcd-development/etcd:v3.5.7 \
    etcd --name s-1 \
    --data-dir /tmp/etcd/s-1 \
    --listen-client-urls https://0.0.0.0:2379 \
    --advertise-client-urls "https://$CLOUD_IP:2379" \
    --listen-peer-urls http://0.0.0.0:2380 \
    --initial-advertise-peer-urls http://0.0.0.0:2380 \
    --initial-cluster s-1=http://0.0.0.0:2380 \
    --initial-cluster-token tkn \
    --initial-cluster-state new \
    --cert-file=/cert/etcd.crt \
    --key-file=/cert/etcd.key \
    --client-cert-auth \
    --trusted-ca-file=/cert/ca.crt

## start fred instance
ssh "$CLOUD_INSTANCE" docker run \
    -v "$home/$FREDCLOUD_CERT:/cert/node.crt" \
    -v "$home/$FREDCLOUD_KEY:/cert/node.key" \
    -v "$home/$CA_CERT:/cert/ca.crt" \
    -p 9001:9001 \
    -p 5555:5555 \
    -d \
    git.tu-berlin.de:5000/mcc-fred/fred/fred:v0.2.18 \
    --nodeID fredcloud \
    --nase-host "$CLOUD_IP:2379" \
    --nase-cached \
    --adaptor badgerdb \
    --badgerdb-path ./db \
    --host 0.0.0.0:9001 \
    --advertise-host "$CLOUD_IP:9001" \
    --peer-host 0.0.0.0:5555 \
    --peer-advertise-host "$CLOUD_IP:5555" \
    --log-level debug \
    --handler dev \
    --cert /cert/node.crt \
    --key /cert/node.key \
    --ca-file /cert/ca.crt \
    --skip-verify \
    --peer-cert /cert/node.crt \
    --peer-key /cert/node.key \
    --peer-ca /cert/ca.crt \
    --peer-skip-verify \
    --nase-cert /cert/node.crt \
    --nase-key /cert/node.key \
    --nase-ca /cert/ca.crt \
    --nase-skip-verify \
    --trigger-cert /cert/node.crt \
    --trigger-key /cert/node.key \
    --trigger-ca /cert/ca.crt \
    --trigger-skip-verify

## start tinyfaas instance
ssh "$CLOUD_INSTANCE" \
    TF_BACKEND=dockerkv \
    DOCKERKV_CERTS_DIR=${CERTS_DIR} \
    DOCKERKV_CA_CERT_PATH=${CERTS_DIR}/ca.crt \
    DOCKERKV_CA_KEY_PATH=${CERTS_DIR}/ca.key \
    DOCKERKV_HOST="$CLOUD_IP" \
    DOCKERKV_PORT=9001 \
    ./manager &

# run the edge
home=$(ssh "$EDGE_INSTANCE" pwd)

## start tinyfaas instance

### if deployment mode is edge, also start fred on edge

if [ "$DEPLOYMENT_MODE" == "edge" ]; then
    ssh "$EDGE_INSTANCE" docker run \
        -v "$home/$FREDEDGE_CERT:/cert/node.crt" \
        -v "$home/$FREDEDGE_KEY:/cert/node.key" \
        -v "$home/$CA_CERT:/cert/ca.crt" \
        -p 9001:9001 \
        -p 5555:5555 \
        -d \
        git.tu-berlin.de:5000/mcc-fred/fred/fred:v0.2.18 \
        --nodeID frededge \
        --nase-host "$CLOUD_IP:2379" \
        --nase-cached \
        --adaptor badgerdb \
        --badgerdb-path ./db \
        --host 0.0.0.0:9001 \
        --advertise-host "$EDGE_IP:9001" \
        --peer-host 0.0.0.0:5555 \
        --peer-advertise-host "$EDGE_IP:5555" \
        --log-level debug \
        --handler dev \
        --cert /cert/node.crt \
        --key /cert/node.key \
        --ca-file /cert/ca.crt \
        --skip-verify \
        --peer-cert /cert/node.crt \
        --peer-key /cert/node.key \
        --peer-ca /cert/ca.crt \
        --peer-skip-verify \
        --nase-cert /cert/node.crt \
        --nase-key /cert/node.key \
        --nase-ca /cert/ca.crt \
        --nase-skip-verify \
        --trigger-cert /cert/node.crt \
        --trigger-key /cert/node.key \
        --trigger-ca /cert/ca.crt \
        --trigger-skip-verify
fi

DOCKERKV_HOST="$CLOUD_IP"
if [ "$DEPLOYMENT_MODE" == "edge" ]; then
    DOCKERKV_HOST="$EDGE_IP"
fi

ssh "$EDGE_INSTANCE" \
    TF_BACKEND=dockerkv \
    DOCKERKV_CERTS_DIR=${CERTS_DIR} \
    DOCKERKV_CA_CERT_PATH=${CERTS_DIR}/ca.crt \
    DOCKERKV_CA_KEY_PATH=${CERTS_DIR}/ca.key \
    DOCKERKV_HOST="$DOCKERKV_HOST" \
    DOCKERKV_PORT=9001 \
    ./manager &

## deploy the function
NAME="func"

until curl "http://$EDGE_IP:8080/logs"
do
  echo "edge tf not ready yet"
  sleep 1
done
sleep 1

pushd "functions/$FUNCTION" || exit
curl "http://$EDGE_IP:8080/upload" --data "{\"name\": \"$NAME\", \"env\": \"python3-kv\", \"threads\": $THREADS, \"zip\": \"$(zip -r - ./* | base64 | tr -d '\n')\"}"
popd || exit

## add a delay between edge and cloud
INTERFACE=ens4

# generated using tcset ens4 --bandwidth 100Mbps --delay 100ms --network 192.168.0.0 --tc-command

# some magic for bitrates
BITRATE=$(bc -l <<< "$BANDWIDTH_MBPS * 1000.0" | awk '{printf "%.1f", $0}')
BURSTRATE=$(bc -l <<< "$BITRATE / 8" | awk '{printf "%.1f", $0}')

BITRATE_CLIENT_EDGE=$(bc -l <<< "$BANDWIDTH_CLIENT_EDGE_MBPS * 1000.0" | awk '{printf "%.1f", $0}')
BURSTRATE_CLIENT_EDGE=$(bc -l <<< "$BITRATE_CLIENT_EDGE / 8" | awk '{printf "%.1f", $0}')

ssh "$EDGE_INSTANCE" sudo tc qdisc add dev "$INTERFACE" root handle 1a1a: htb default 1
ssh "$EDGE_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:1 htb rate 32000000.0kbit

ssh "$EDGE_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:68 htb rate "$BITRATE"Kbit ceil "$BITRATE"Kbit burst "$BURSTRATE"KB cburst "$BURSTRATE"KB
ssh "$EDGE_INSTANCE" sudo tc qdisc add dev "$INTERFACE" parent 1a1a:68 handle 2a34: netem delay "$DELAY.0ms"
ssh "$EDGE_INSTANCE" sudo tc filter add dev "$INTERFACE" protocol ip parent 1a1a: prio 5 u32 match ip dst "$CLOUD_IP/32" match ip src 0.0.0.0/0 flowid 1a1a:68

ssh "$EDGE_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:69 htb rate "$BITRATE_CLIENT_EDGE"Kbit ceil "$BITRATE_CLIENT_EDGE"Kbit burst "$BURSTRATE_CLIENT_EDGE"KB cburst "$BURSTRATE_CLIENT_EDGE"KB
ssh "$EDGE_INSTANCE" sudo tc qdisc add dev "$INTERFACE" parent 1a1a:69 handle 2a35: netem delay "$DELAY_CLIENT_EDGE.0ms"
ssh "$EDGE_INSTANCE" sudo tc filter add dev "$INTERFACE" protocol ip parent 1a1a: prio 5 u32 match ip dst "$CLIENT_IP/32" match ip src 0.0.0.0/0 flowid 1a1a:69

# and opposite direction
ssh "$CLOUD_INSTANCE" sudo tc qdisc add dev "$INTERFACE" root handle 1a1a: htb default 1
ssh "$CLOUD_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:1 htb rate 32000000.0kbit

ssh "$CLOUD_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:68 htb rate "$BITRATE"Kbit ceil "$BITRATE"Kbit burst "$BURSTRATE"KB cburst "$BURSTRATE"KB
ssh "$CLOUD_INSTANCE" sudo tc qdisc add dev "$INTERFACE" parent 1a1a:68 handle 2a34: netem delay "$DELAY.0ms"
ssh "$CLOUD_INSTANCE" sudo tc filter add dev "$INTERFACE" protocol ip parent 1a1a: prio 5 u32 match ip dst "$EDGE_IP/32" match ip src 0.0.0.0/0 flowid 1a1a:68

ssh "$CLOUD_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:69 htb rate "$BITRATE"Kbit ceil "$BITRATE"Kbit burst "$BURSTRATE"KB cburst "$BURSTRATE"KB
ssh "$CLOUD_INSTANCE" sudo tc qdisc add dev "$INTERFACE" parent 1a1a:69 handle 2a35: netem delay "$DELAY.0ms"
ssh "$CLOUD_INSTANCE" sudo tc filter add dev "$INTERFACE" protocol ip parent 1a1a: prio 5 u32 match ip dst "$CLIENT_IP/32" match ip src 0.0.0.0/0 flowid 1a1a:69

# also add delay from client to cloud
ssh "$CLIENT_INSTANCE" sudo tc qdisc add dev "$INTERFACE" root handle 1a1a: htb default 1
ssh "$CLIENT_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:1 htb rate 32000000.0kbit

ssh "$CLIENT_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:68 htb rate "$BITRATE_CLIENT_EDGE"Kbit ceil "$BITRATE_CLIENT_EDGE"Kbit burst "$BURSTRATE_CLIENT_EDGE"KB cburst "$BURSTRATE_CLIENT_EDGE"KB
ssh "$CLIENT_INSTANCE" sudo tc qdisc add dev "$INTERFACE" parent 1a1a:68 handle 2a34: netem delay "$DELAY.0ms"
ssh "$CLIENT_INSTANCE" sudo tc filter add dev "$INTERFACE" protocol ip parent 1a1a: prio 5 u32 match ip dst "$CLOUD_IP/32" match ip src 0.0.0.0/0 flowid 1a1a:68

ssh "$CLIENT_INSTANCE" sudo tc class add dev "$INTERFACE" parent 1a1a: classid 1a1a:69 htb rate "$BITRATE_CLIENT_EDGE"Kbit ceil "$BITRATE_CLIENT_EDGE"Kbit burst "$BURSTRATE_CLIENT_EDGE"KB cburst "$BURSTRATE_CLIENT_EDGE"KB
ssh "$CLIENT_INSTANCE" sudo tc qdisc add dev "$INTERFACE" parent 1a1a:69 handle 2a35: netem delay "$DELAY_CLIENT_EDGE.0ms"
ssh "$CLIENT_INSTANCE" sudo tc filter add dev "$INTERFACE" protocol ip parent 1a1a: prio 5 u32 match ip dst "$EDGE_IP/32" match ip src 0.0.0.0/0 flowid 1a1a:69


# start the experiment on the client
# python3 load.py <endpoint> <function> <requests> <threads> <frequency> <output>"
RES_FILE="results.txt"

# ready to run!
start_time=$(date +%s)
echo "-------------------"
echo "running experiment with parameters:"
echo "function: $FUNCTION"
echo "parameter: $PARAMETER"
echo "threads: $THREADS"
echo "load requests: $LOAD_REQUESTS"
echo "load threads: $LOAD_THREADS"
echo "load frequency: $LOAD_FREQUENCY"
echo "output file: $OUTPUT_FILE"
echo "delay: $DELAY"
echo "bandwidth: $BANDWIDTH_MBPS"
echo "deployment mode: $DEPLOYMENT_MODE"
echo "timeout: $TIMEOUT"
echo "start time: $(date)"
echo "-------------------"

ssh "$CLIENT_INSTANCE" \
    PYTHONUNBUFFERED=1 \
    python3 load-simple.py \
    "http://$EDGE_IP:8000/$NAME" \
    "$FUNCTION" \
    "$PARAMETER" \
    "$LOAD_REQUESTS" \
    "$LOAD_THREADS" \
    "$LOAD_FREQUENCY" \
    "$RES_FILE" \
    "$TIMEOUT"

echo "-------------------"
echo "experiment finished"
echo "end time: $(date)"
echo "total time: $(($(date +%s) - start_time)) seconds"
echo "-------------------"

# copy the results
scp "$CLIENT_INSTANCE:~/$RES_FILE" "$OUTPUT_FILE"

# collect the logs
curl "http://$EDGE_IP:8080/logs"

# destroy the machines
set +x

echo "to destroy the machines run: terraform destroy -auto-approve"
