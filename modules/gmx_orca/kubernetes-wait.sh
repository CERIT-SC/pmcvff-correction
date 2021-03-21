#!/bin/bash

unset label
while getopts ":l:" opt; do
  case $opt in

    l)
      label="$OPTARG"
      echo "waiting for jobs with label $label" >&2
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

label_flag=""
if [[ -n $label ]]; then
    label_flag="jobs -l app=$label"
fi

#workaround to experimental not working kubernetes wait - wait until all jobs with label finish
kubectl logs -f -l app=$label > /dev/null

sleep 2 && kubectl logs -l app=$label --tail=-1
