#!/bin/bash

# add production user and permissions
useradd --uid 1001 --create-home --shell /bin/bash magic_user
chmod a+rwx /home/base/modules/gmx_orca/lock.pkl
# chmod -R a+rX /opt /home
chmod -R a+rX /home

# create all directories used in computations
cd /work
mkdir -p em
mkdir -p md
mkdir -p mtd
mkdir -p pdb_opt
mkdir -p visualization/traj
mkdir -p -m 757 gaff
mkdir -p -m 757 clustering/{outClustersPDB,outClustersXYZ,outClusters}
mkdir -p -m 757 am1/{input,output}
mkdir -p -m 757 bp86svp/{input,output}
mkdir -p -m 757 orca_output/{am1,bp86svp,bp86tzvp}
mkdir -p -m 757 bp86tzvp/{input,output}
