#!/bin/bash
unset id
application="docker"

while getopts ":pi:" opt; do
  case $opt in
    p)
      application="podman"
      echo "building with podman.." >&2
      ;;
    i)
      id="-${OPTARG}"
      echo "building with id $id"
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

intelpython="l_pythoni3_p_2019.5.098.tar.gz"
name="spectraes/pipeline:$(date +%F)${id}"
build="${application} build --build-arg INTELPYTHON=${intelpython} -t ${name} ."
push="${application} push ${name}"

eval "${build} && ${push}"

if [[ $? == 0 ]]; then
	echo "successfully built and pushed image ${name}"
fi
