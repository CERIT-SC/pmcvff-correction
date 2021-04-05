#!/usr/bin/env python
import ruamel_yaml
from ruamel_yaml.scalarstring import DoubleQuotedScalarString
import subprocess
import time
import os
import sys
import pickle

# Set image to be used for gromacs calculations
GMX_IMAGE = "ljocha/gromacs:2021-1"
# Set image to be used for orca calculations
ORCA_IMAGE = "spectraes/pipeline_orca:latest"
# Set default filepaths
KUBERNETES_WAIT_PATH = PICKLE_PATH = os.path.dirname(os.path.realpath(__file__))


def gmx_run(gmx_command, **kwargs):
	"""
    Convert gmx command into yaml file which is then run by kubernetes

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

	mpi_run = kwargs.get('mpi_run', None)
	groups = kwargs.get('groups', None)
	make_ndx = kwargs.get('make_ndx', None)
	image = kwargs.get('image', None)
	workdir = kwargs.get('workdir', None)
	double = kwargs.get('double', False)
	rdtscp = kwargs.get('rdtscp', False)
	arch = kwargs.get('arch', '')
	parallel = kwargs.get('parallel', False)

	gmx_method = gmx_command.split()[0]
	application = "gmx"
	if gmx_method == "driver":
		application = "plumed"
	elif gmx_method == "mdrun":
		application = ""

	gmx = "{} {}".format(application, gmx_command)

	if mpi_run:
		gmx = "mpirun -np {} {}".format(mpi_run, gmx)

	if groups:
		gmx = ") | {}".format(gmx)
		for i in range(len(groups)):
			# Write in reverse order because you insert from right to left
			gmx = "echo {} {}".format(groups[::-1][i], gmx)
			if i == (len(groups) - 1):
				gmx = "({}".format(gmx)
				break
			gmx = "; sleep 1; {}".format(gmx)

	if make_ndx:
		gmx = "| {}".format(gmx)
		gmx = "(echo \'{}\'; sleep 1; echo q) {}".format(make_ndx, gmx)

	kubernetes_config, label = write_template(gmx_method, image, gmx, workdir, parallel, double=double, rdtscp=rdtscp,
									   arch=arch)
	print(run_job(kubernetes_config, label, parallel))


def orca_run(orca_method, log, **kwargs):
	"""
    Convert orca command into yaml file which is then run by kubernetes

    :param str orca_command: orca method used for computation
    :param str log: log file to store output of computation
    :kwargs str image: specify used image
    :kwargs str workdir: specify directory where should the calculation take place
    """
	image = kwargs.get('image', None)
	workdir = kwargs.get('workdir', None)
	parallel = kwargs.get('parallel', False)

	log = f"/tmp/{log}"
	application = "orca"
	orca = "/opt/orca/{} {} > {}".format(application, orca_method, log)

	kubernetes_config, label = write_template(application, image, orca, workdir,parallel, orca_method_file=f"{workdir}/{orca_method}")
	print(run_job(kubernetes_config, label, parallel))


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

	print(run_wait(f"-l {label} -c {count}"))


def write_template(method, image, command, workdir, parallel, **kwargs):
	with open(f"{os.path.dirname(os.path.realpath(__file__))}/kubernetes-template.yaml") as ifile:
		doc = ruamel_yaml.round_trip_load(ifile, preserve_quotes=True)

		double = kwargs.get('double', 'OFF')
		rdtscp = kwargs.get('rdtscp', 'OFF')
		orca_method_file = kwargs.get('orca_method_file', '')
		arch = kwargs.get('arch', '')

		# Set default values
		default_image = GMX_IMAGE
		default_name = "gromacs"
		if method == "orca":
			default_image = ORCA_IMAGE
			default_name = "orca"

		# Always replace "" with "-" because "" is not kubernetes accepted char in the name
		method = method.replace("_", "-")

		# Set names
		timestamp = str(time.time()).replace(".", "")
		identificator = "{}-{}-rdtscp-{}".format(default_name, method, timestamp)
		doc['metadata']['name'] = identificator
		doc['spec']['template']['spec']['containers'][0]['name'] = "{}-{}-deployment-{}".format(default_name, method, timestamp)
		doc['spec']['template']['metadata']['labels']['app'] = identificator

		# Set gromacs args
		doc['spec']['template']['spec']['containers'][0]['args'] = ["/bin/bash", "-c", DoubleQuotedScalarString(command)]

		# If not orca, set options for gmx container
		if method != "orca":
			double_env = {'name': "GMX_DOUBLE", 'value': DoubleQuotedScalarString("ON" if double else "OFF")}
			rdtscp_env = {'name': "GMX_RDTSCP", 'value': DoubleQuotedScalarString("ON" if rdtscp else "OFF")}
			arch_env = {'name': "GMX_ARCH", 'value': DoubleQuotedScalarString(arch)}
			doc['spec']['template']['spec']['containers'][0]['env'] = [double_env, rdtscp_env, arch_env]

		# If parallel is enabled set label so kubectl logs can print logs according to label
		if parallel:
			with open(f"{PICKLE_PATH}/lock.pkl","rb") as fp:
				lock_object = pickle.load(fp)
			if len(lock_object['Parallel_label']) == 0:
				label = {"Parallel_label": identificator, "Count": 0}
				with open(f"{PICKLE_PATH}/lock.pkl","wb") as fp:
					pickle.dump(label, fp)
			else:
				doc['spec']['template']['metadata']['labels']['app'] = lock_object['Parallel_label']


		# Set image
		doc['spec']['template']['spec']['containers'][0]['image'] = default_image if not image else image

		# Set working directory
		doc['spec']['template']['spec']['containers'][0]['workingDir'] = "/tmp/"
		if workdir:
			doc['spec']['template']['spec']['containers'][0]['workingDir'] += workdir

		# set PVC
		pvc_name = os.environ['PVC_NAME']
		if len(pvc_name) == 0:
			raise Exception("Error setting pvc_name, probably problem in setting env variable of actual container")
		doc['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = pvc_name

		# Set orca required cpus
		if method == "orca":
			no_of_procs = get_no_of_procs(orca_method_file)
			if no_of_procs != -1:
				doc['spec']['template']['spec']['containers'][0]['resources']['requests']['cpu'] = no_of_procs

		# Write to file
		ofile_name = "{}-{}-rdtscp.yaml".format(default_name, method)
		with open(ofile_name, "w") as ofile:
			ruamel_yaml.round_trip_dump(doc, ofile, explicit_start=True)

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
	# Run the shell script to wait until kubernetes pod - container finishes
	cmd = f"{KUBERNETES_WAIT_PATH}/kubernetes-wait.sh {command}"
	process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
	
	# Wait until k8s (kubernetes-wait.sh) finishes and return the output
	return None if "-p" in command else process.communicate()[0].decode('utf-8', 'ignore')
	
