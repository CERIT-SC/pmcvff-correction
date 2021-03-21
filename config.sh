#!/bin/bash

#name of the main container
export CONTAINER_NAME="pipeline"
#shared directory between host and containers
export SHARED_DIR="work"
#total path of shared directory
export WORK="$PWD/$SHARED_DIR"
#root to be set in computing environment
export ROOT_TMP="$SCRATCHDIR"
#name of image containing pipeline
export IMAGE_NAME="spectraes/pipeline:22-02-2021"
