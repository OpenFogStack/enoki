#!/bin/bash

set -x

# some possible parameters
DEPLOYMENT_MODE="$1"
OUTPUT_FILE="$2"
THREADS="$3"
DELAY="$4"
BANDWIDTH_MBPS="$5"
DELAY_CLIENT_EDGE="$6"
BANDWIDTH_CLIENT_EDGE_MBPS="$7"
DURATION="$8"

# DEPLOYMENT_MODE="edge" # edge, cloud, allcloud
# THREADS=1
# DELAY=25
# BANDWIDTH_MBPS=100
# OUTPUT_FILE="logs.txt"

FUNCTION_FOLDER="./functions/5_befaas-iot"

# check that we have all parameters
if [ -z "$DEPLOYMENT_MODE" ] || [ -z "$OUTPUT_FILE" ] || [ -z "$THREADS" ] || [ -z "$DELAY" ] || [ -z "$BANDWIDTH_MBPS" ] || [ -z "$DELAY_CLIENT_EDGE" ] || [ -z "$BANDWIDTH_CLIENT_EDGE_MBPS" ] || [ -z "$DURATION" ]; then
    echo "missing parameters"
    echo "usage: ./run-befaas.sh <deployment_mode> <output_file> <threads> <delay> <bandwidth_mbps>"
    exit 1
fi

# check that the deployment mode is valid
if [ "$DEPLOYMENT_MODE" != "cloud" ] && [ "$DEPLOYMENT_MODE" != "edge" ] && [ "$DEPLOYMENT_MODE" != "allcloud" ]; then
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

CERTS_DIR=certs
CA_CERT="$CERTS_DIR/ca.crt"

ETCD_CERT="$CERTS_DIR/etcd.crt"
ETCD_KEY="$CERTS_DIR/etcd.key"

FREDCLOUD_CERT="$CERTS_DIR/fredcloud.crt"
FREDCLOUD_KEY="$CERTS_DIR/fredcloud.key"

FREDEDGE_CERT="$CERTS_DIR/frededge.crt"
FREDEDGE_KEY="$CERTS_DIR/frededge.key"

# run the edge
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

until curl "http://$EDGE_IP:8080/logs"
do
  echo "edge tf not ready yet"
  sleep 1
done
sleep 1

# prepare befaas functions

## make a tmp folder
mkdir -p ./tmp
TMP_FOLDER=$(mktemp -d --tmpdir=tmp)

## copy the functions
cp -r "$FUNCTION_FOLDER"/* "$TMP_FOLDER"

## copy the befaas.py into the function folders
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/emergencydetection/
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/movementplan/
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/objectrecognition/
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/roadcondition/
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/lightphasecalculation/
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/trafficsensorfilter/
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/trafficstatistics/
cp "$FUNCTION_FOLDER"/befaas.py "$TMP_FOLDER"/weathersensorfilter/

# where to deploy the functions
# unless allcloud, deploy the edge functions to the edge and the cloud functions to the cloud
# in allcloud, deploy all functions to the cloud

## emergencydetection -> edge
ENDPOINT_EMERGENCYDETECTION="http://$EDGE_IP:8000/emergencydetection"
## movementplan -> edge
ENDPOINT_MOVEMENTPLAN="http://$EDGE_IP:8000/movementplan"
## objectrecognition -> edge
ENDPOINT_OBJECTRECOGNITION="http://$EDGE_IP:8000/objectrecognition"
## trafficsensorfilter -> edge
ENDPOINT_TRAFFICSENSORFILTER="http://$EDGE_IP:8000/trafficsensorfilter"
## weathersensorfilter -> edge
ENDPOINT_WEATHERSENSORFILTER="http://$EDGE_IP:8000/weathersensorfilter"

if [ "$DEPLOYMENT_MODE" == "allcloud" ]; then
    ENDPOINT_EMERGENCYDETECTION="http://$CLOUD_IP:8000/emergencydetection"
    ENDPOINT_MOVEMENTPLAN="http://$CLOUD_IP:8000/movementplan"
    ENDPOINT_OBJECTRECOGNITION="http://$CLOUD_IP:8000/objectrecognition"
    ENDPOINT_TRAFFICSENSORFILTER="http://$CLOUD_IP:8000/trafficsensorfilter"
    ENDPOINT_WEATHERSENSORFILTER="http://$CLOUD_IP:8000/weathersensorfilter"
fi

## roadcondition -> cloud
ENDPOINT_ROADCONDITION="http://$CLOUD_IP:8000/roadcondition"
## lightphasecalculation -> cloud
ENDPOINT_LIGHTPHASECALCULATION="http://$CLOUD_IP:8000/lightphasecalculation"
## trafficstatistics -> cloud
ENDPOINT_TRAFFICSTATISTICS="http://$CLOUD_IP:8000/trafficstatistics"

# deploy befaas functions

## start with the edge functions
for func in emergencydetection movementplan objectrecognition  trafficsensorfilter weathersensorfilter
do
    pushd "$TMP_FOLDER/$func" || exit
    envs="[\"ENDPOINT_EMERGENCYDETECTION=$ENDPOINT_EMERGENCYDETECTION\",\"ENDPOINT_MOVEMENTPLAN=$ENDPOINT_MOVEMENTPLAN\", \"ENDPOINT_OBJECTRECOGNITION=$ENDPOINT_OBJECTRECOGNITION\", \"ENDPOINT_ROADCONDITION=$ENDPOINT_ROADCONDITION\", \"ENDPOINT_LIGHTPHASECALCULATION=$ENDPOINT_LIGHTPHASECALCULATION\", \"ENDPOINT_TRAFFICSENSORFILTER=$ENDPOINT_TRAFFICSENSORFILTER\", \"ENDPOINT_TRAFFICSTATISTICS=$ENDPOINT_TRAFFICSTATISTICS\", \"ENDPOINT_WEATHERSENSORFILTER=$ENDPOINT_WEATHERSENSORFILTER\",
        \"FUNCTION_NAME=$func\"]"

    DEPLOY_TO="$EDGE_IP"

    if [ "$DEPLOYMENT_MODE" == "allcloud" ]; then
        DEPLOY_TO="$CLOUD_IP"
    fi

    curl "http://$DEPLOY_TO:8080/upload" --data "{\"name\": \"$func\", \"env\": \"python3-kv\", \"threads\": $THREADS, \"envs\": $envs, \"zip\": \"$(zip -r - ./* | base64 | tr -d '\n')\"}"
    popd || exit
done

## then the cloud functions
for func in roadcondition lightphasecalculation trafficstatistics
do
    pushd "$TMP_FOLDER/$func" || exit
    envs="[\"ENDPOINT_EMERGENCYDETECTION=$ENDPOINT_EMERGENCYDETECTION\",\"ENDPOINT_MOVEMENTPLAN=$ENDPOINT_MOVEMENTPLAN\", \"ENDPOINT_OBJECTRECOGNITION=$ENDPOINT_OBJECTRECOGNITION\", \"ENDPOINT_ROADCONDITION=$ENDPOINT_ROADCONDITION\", \"ENDPOINT_LIGHTPHASECALCULATION=$ENDPOINT_LIGHTPHASECALCULATION\", \"ENDPOINT_TRAFFICSENSORFILTER=$ENDPOINT_TRAFFICSENSORFILTER\", \"ENDPOINT_TRAFFICSTATISTICS=$ENDPOINT_TRAFFICSTATISTICS\", \"ENDPOINT_WEATHERSENSORFILTER=$ENDPOINT_WEATHERSENSORFILTER\",
        \"FUNCTION_NAME=$func\"]"
    curl "http://$CLOUD_IP:8080/upload" --data "{\"name\": \"$func\", \"env\": \"python3-kv\", \"threads\": $THREADS, \"envs\": $envs, \"zip\": \"$(zip -r - ./* | base64 | tr -d '\n')\"}"
    popd || exit
done

# ready to run!
start_time=$(date +%s)
echo "-------------------"
echo "running befaas experiment with parameters:"
echo "output file: $OUTPUT_FILE"
echo "deployment mode: $DEPLOYMENT_MODE"
echo "duration: $DURATION"
echo "start time: $(date)"
echo "-------------------"

# start "artillery"
ssh "$CLIENT_INSTANCE" \
    PYTHONUNBUFFERED=1 \
    ENDPOINT_EMERGENCYDETECTION=$ENDPOINT_EMERGENCYDETECTION \
    ENDPOINT_MOVEMENTPLAN=$ENDPOINT_MOVEMENTPLAN \
    ENDPOINT_OBJECTRECOGNITION=$ENDPOINT_OBJECTRECOGNITION \
    ENDPOINT_ROADCONDITION=$ENDPOINT_ROADCONDITION \
    ENDPOINT_LIGHTPHASECALCULATION=$ENDPOINT_LIGHTPHASECALCULATION \
    ENDPOINT_TRAFFICSENSORFILTER=$ENDPOINT_TRAFFICSENSORFILTER \
    ENDPOINT_TRAFFICSTATISTICS=$ENDPOINT_TRAFFICSTATISTICS \
    ENDPOINT_WEATHERSENSORFILTER=$ENDPOINT_WEATHERSENSORFILTER \
    DURATION=$DURATION \
    python3 load-befaas.py

echo "-------------------"
echo "experiment finished"
echo "end time: $(date)"
echo "total time: $(($(date +%s) - start_time)) seconds"
echo "-------------------"

# wait for the async functions to finish
sleep 30

# get the logs
# client logs
echo "client logs"
ssh "$CLIENT_INSTANCE" cat output.txt > "$OUTPUT_FILE"

# edge logs
echo "edge logs"
curl "http://$EDGE_IP:8080/logs" >> "$OUTPUT_FILE"

# cloud logs
echo "cloud logs"
curl "http://$CLOUD_IP:8080/logs" >> "$OUTPUT_FILE"

# destroy the machines
set +x
