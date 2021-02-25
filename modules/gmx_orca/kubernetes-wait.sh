#!/bin/bash
# First parameter is pod name (base without hash)
# Second parameter is wait time between every pulse

name="$1"
wait_time="$2"

# Get whole name of pod (with Rancher hash)
pod_name="$(kubectl get pods -n mff-user-ns -o json | jq ".items[] | select(.metadata.name|test(\"$name\"))| .metadata.name" | tr -d \")"

if [[ -z $pod_name ]]; then
    echo "error finding pod" && exit 1
fi

# Wait until pod is alive or succeeded
count=0
while true; do
    status="$(kubectl get pods $pod_name -n mff-user-ns -o 'jsonpath={..status.cc
onditions[?(@.type=="Ready")].reason}')"
    if [[ $? != 0 || "$status" == "PodCompleted" ]]; then
        break
    fi
    echo -ne "finished in $count"\\r
    count=$((count+$wait_time))
    sleep $wait_time
done

kubectl logs $pod_name