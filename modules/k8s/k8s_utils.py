#!/usr/bin/env python
import ruamel.yaml
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
import subprocess
import time
import os
import sys
import pickle

GMX_IMAGE = "ljocha/gromacs:2021-1"
ORCA_IMAGE = "spectraes/pipeline_orca:latest"
PARMTSNECV_IMAGE = "spectraes/parmtsnecv:28-08-2021"
# Set default filepaths
KUBERNETES_WAIT_PATH = PICKLE_PATH = os.path.dirname(os.path.realpath(__file__))


def write_template(method, command, params, **kwargs):
        with open(f"{os.path.dirname(os.path.realpath(__file__))}/kubernetes-template.yaml") as ifile:
                doc = ruamel.yaml.round_trip_load(ifile, preserve_quotes=True)

                orca_method_file = kwargs.get('orca_method_file', '')
                timestamp = str(time.time()).replace(".", "")
                # Always replace "" with "-" because "" is not kubernetes accepted char in the name
                method = method.replace("_", "-")
                # Set default values
                default_image = ''
                default_name = ''


                if method == "orca":
                    default_image = ORCA_IMAGE
                    default_name = "orca"
                    
                    # Set orca required cpus
                    no_of_procs = get_no_of_procs(orca_method_file)
                    if no_of_procs != -1:
                        doc['spec']['template']['spec']['containers'][0]['resources']['requests']['cpu'] = no_of_procs
                elif method == 'gromacs':
                    default_image = GMX_IMAGE
                    default_name = 'gromacs'

                    double_env = {'name': "GMX_DOUBLE", 'value': DoubleQuotedScalarString("ON" if params["double"] else "OFF")}
                    rdtscp_env = {'name': "GMX_RDTSCP", 'value': DoubleQuotedScalarString("ON" if params["rdtscp"] else "OFF")}
                    arch_env = {'name': "GMX_ARCH", 'value': DoubleQuotedScalarString(params["arch"])}
                    doc['spec']['template']['spec']['containers'][0]['env'] = [double_env, rdtscp_env, arch_env]
                elif method == 'parmtsnecv':
                    default_image = PARMTSNECV_IMAGE
                    default_name = 'parmtsnecv'
                

                identificator = "{}-{}-rdtscp-{}".format(default_name, method, timestamp)
                # Set names
                doc['metadata']['name'] = identificator
                doc['spec']['template']['spec']['containers'][0]['name'] = "{}-{}-deployment-{}".format(default_name, method, timestamp)
                doc['spec']['template']['metadata']['labels']['app'] = identificator
                # Set gromacs/orca command
                doc['spec']['template']['spec']['containers'][0]['args'] = ["/bin/bash", "-c", DoubleQuotedScalarString(command)]
                # Set image
                doc['spec']['template']['spec']['containers'][0]['image'] = default_image if not params["image"] else params["image"]
                # Set working directory
                doc['spec']['template']['spec']['containers'][0]['workingDir'] = "/tmp/"
                if params["workdir"]:
                        doc['spec']['template']['spec']['containers'][0]['workingDir'] += params["workdir"]

                # set PVC
                pvc_name = os.environ['PVC_NAME']
                if len(pvc_name) == 0:
                        raise Exception("Error setting pvc_name, probably problem in setting env variable of actual container")
                doc['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = pvc_name

                # If parallel is enabled set label so kubectl logs can print logs according to label
                if params["parallel"]:
                        with open(f"{PICKLE_PATH}/lock.pkl","rb") as fp:
                                lock_object = pickle.load(fp)
                        if len(lock_object['Parallel_label']) == 0:
                                label = {"Parallel_label": identificator, "Count": 0}
                                with open(f"{PICKLE_PATH}/lock.pkl","wb") as fp:
                                        pickle.dump(label, fp)
                        else:
                                doc['spec']['template']['metadata']['labels']['app'] = lock_object['Parallel_label']

                # Write to file
                ofile_name = "{}-{}-rdtscp.yaml".format(default_name, method)
                with open(ofile_name, "w") as ofile:
                        ruamel.yaml.round_trip_dump(doc, ofile, explicit_start=True)

                return ofile_name, identificator


def run_job(kubernetes_config, label, parallel):
        os.system(f"kubectl apply -f {kubernetes_config}")

        if not parallel:
                return run_wait(f"-l {label} -c 1")
        
        # increment pickle count
        with open(f"{PICKLE_PATH}/lock.pkl","rb") as fp:
                lock_object = pickle.load(fp)
        with open(f"{PICKLE_PATH}/lock.pkl","wb") as fp:
                lock_object['Count'] += 1 
                pickle.dump(lock_object, fp)


def get_no_of_procs(orca_method_file):
        with open(orca_method_file) as ifile:
                for line in ifile.readlines():
                        if "nprocs" in line:
                                return int(line.split()[1])
                return -1


def run_wait(command):
        cmd = f"{KUBERNETES_WAIT_PATH}/kubernetes-wait.sh {command}"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        
        return process.communicate()[0].decode('utf-8', 'ignore')

