#!/usr/bin/env python
import ruamel.yaml
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
import subprocess
import time
import os
import sys
import pickle

import k8s_utils


def gmx_run(gmx_command, **kwargs):
        """
        Converts gmx command into yaml file which is then run by kubernetes
        
        :param str gmx_command: gromacs command
        :kwargs int mpi_run: request number of cpus for mpi_run
        :kwargs str groups: specify interactive groups for gromacs
        :kwargs str make_ndx: specify interactive make_ndx input for gromacs make_ndx
        :kwargs str image: specify used image
        :kwargs str workdir: specify directory where should the calculation take place
        :kwargs str arch: specify architecture
        :kwargs bool double: double precision for mdrun
        :kwargs bool rdtscp: enable rndscp
        :kwargs bool parallel: run jobs as parallel
        """

        params = {
                "mpi_run": kwargs.get('mpi_run', None),
                "groups": kwargs.get('groups', None),
                "make_ndx": kwargs.get('make_ndx', None),
                "image": kwargs.get('image', None),
                "workdir": kwargs.get('workdir', None),
                "double": kwargs.get('double', None),
                "rdtscp": kwargs.get('rdtscp', None),
                "arch": kwargs.get('arch', ""),
                "parallel": kwargs.get('parallel', None)
        }

        gmx_method = gmx_command.split()[0]
        application = "gmx"
        if gmx_method == "driver":
                application = "plumed"
        elif gmx_method == "mdrun":
                application = ""

        gmx = "{} {}".format(application, gmx_command)

        if params["mpi_run"]:
                gmx = "mpirun -np {} {}".format(params["mpi_run"], gmx)

        if params["groups"]:
                gmx = ") | {}".format(gmx)
                for i in range(len(params["groups"])):
                        gmx = "echo {} {}".format(params["groups"][::-1][i], gmx)
                        if i == (len(params["groups"]) - 1):
                                gmx = "({}".format(gmx)
                                break
                        gmx = "; sleep 1; {}".format(gmx)

        if params["make_ndx"]:
                gmx = "| {}".format(gmx)
                gmx = "(echo \'{}\'; sleep 1; echo q) {}".format(params["make_ndx"], gmx)

        kubernetes_config, label = k8s_utils.write_template(gmx_method, gmx, params)         
        print(k8s_utils.run_job(kubernetes_config, label, params["parallel"]))


def orca_run(orca_method, log, **kwargs):
        """
        Convert orca command into yaml file which is then run by kubernetes

        :param str orca_command: orca method used for computation
        :param str log: log file to store output of computation
        :kwargs str image: specify used image
        :kwargs str workdir: specify directory where should the calculation take place
        """

        params = {
                "image": kwargs.get('image', None),
                "workdir": kwargs.get('workdir', None),
                "parallel": kwargs.get('parallel', None)
        }

        log = f"/tmp/{log}"
        application = "orca"
        orca = "/opt/orca/{} {} > {}".format(application, orca_method, log)
        method_path = "{}/{}".format(params['workdir'], orca_method)

        kubernetes_config, label = k8s_utils.write_template(application, orca, params, orca_method_file=method_path)
        print(k8s_utils.run_job(kubernetes_config, label, params["parallel"]))


def parmtsnecv_run(command, **kwargs):
        '''
        Convert parmtSNEcv command into yaml file which is then run by kubernetes

        :kwargs str image: specify used image
        :kwargs str workdir: specify directory where should the calculation take place
        '''

        params = {
                "image": kwargs.get('image', None),
                "workdir": kwargs.get('workdir', None),
                "parallel": None
        }

        application = 'parmtsnecv'
        kubernetes_config, label = k8s_utils.write_template(application, command, params)
        print(k8s_utils.run_job(kubernetes_config, label, None))


def parallel_wait():
        """
        Wait for all currently running parallel tasks to finish

        :return: Nothing
        """
        with open(f"{PICKLE_PATH}/lock.pkl","rb") as fp:
                lock_object = pickle.load(fp)
                label = lock_object['Parallel_label']
                count = lock_object['Count']
                if len(label) == 0 or count <= 0:
                        print(f"Nothing to wait for with label => {label}", file=sys.stderr)
                        return 1

        # reset pickle
        with open(f"{PICKLE_PATH}/lock.pkl","wb") as fp:
                values = {"Parallel_label": "", "Count": 0}
                pickle.dump(values, fp)

        print(k8s_utils.run_wait(f"-l {label} -c {count}"))

