#!/usr/bin/env python
import ruamel_yaml
from ruamel_yaml.scalarstring import DoubleQuotedScalarString
import subprocess
import time
import os

#set image to be used for gromacs calculations
GMX_IMAGE = "ljocha/gromacs_universal:2020.02.06-1"
#set image to be used for orca calculations
ORCA_IMAGE = "spectraes/pipeline_orca:latest"

def gmx_run(gmx_command, **kwargs):
	'''
	Convert gmx command into yaml file which is then run by kubernetes

	:param str gmx_command: gromacs command
	:kwargs int mpi_run: request number of cpus for mpi_run
	:kwargs str groups: specify interactive groups for gromacs
	:kwargs str make_ndx: specify interactive make_ndx input for gromacs make_ndx
	:kwargs str image: specify used image
	:kwargs str workdir: specify directory where should the calculation take place
	:kwargs bool double: double precision for mdrun
	:kwargs bool rdtscp: enable rndscp
	'''

	mpi_run = kwargs.get('mpi_run', None)
	groups = kwargs.get('groups', None)
	make_ndx = kwargs.get('make_ndx', None)
	image = kwargs.get('image', None)
	workdir = kwargs.get('workdir', None)
	double = kwargs.get('double', False)
	rdtscp = kwargs.get('rdtscp', False)
	arch = kwargs.get('arch', '')

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

	kubernetes_config, name = write_template(gmx_method, image, gmx, workdir, double=double, rdtscp=rdtscp, arch=arch)

	# Run pod
	os.system(f"kubectl apply -f {kubernetes_config}")

	# Wait for pod to finish - timeout is 4hours
	os.system(f"kubectl wait --for=condition=complete -f {kubernetes_config} --timeout 14400s")

	# Print log
	rancher_pod_name = f'kubectl get pods -n mff-user-ns -o json | jq ".items[] | select(.metadata.name|test(\\"{name}\\"))| .metadata.name" | tr -d \\\"'
	gmx_log = os.popen(f"kubectl logs $({rancher_pod_name})").read()
	print(gmx_log)
	print('--------')


def orca_run(orca_method, log, **kwargs):
	'''
	Convert orca command into yaml file which is then run by kubernetes
	
	:param str orca_command: orca method used for computation
	:param str log: log file to store output of computation
	:kwargs str image: specify used image
	:kwargs str workdir: specify directory where should the calculation take place
	'''
	image = kwargs.get('image', None)
	workdir = kwargs.get('workdir', None)

	application = "orca"
	orca = "/opt/orca/{} {} > {}".format(application, orca_method, log)
	
	kubernetes_config = write_template(application, image, orca, workdir)
	os.system("kubectl apply -f {}".format(kubernetes_config))


def write_template(method, image, command, workdir, **kwargs):
	'''
	Writes information about gromacs/orca container run into kubernetes configuration file

	:param str method: file name based on used method
	:param str image: image used for calculation
	:param str command: command passed to gromacs/orca application (also can be plumed) 
	:param str workdir: specify directory where should the calculation take place
	:kwargs bool double: enable double precision for gmx
	:kwargs bool rdtscp: enable rdtscp for gmx
	:return: name of kubernetes configuration file
	'''
	with open(f"{os.path.dirname(os.path.realpath(__file__))}/kubernetes-template.yaml") as ifile:
		doc = ruamel_yaml.round_trip_load(ifile, preserve_quotes=True)

		double = kwargs.get('double', 'OFF')
		rdtscp = kwargs.get('rdtscp', 'OFF')
		arch = kwargs.get('arch', '')

		#set default values
		default_image = GMX_IMAGE
		default_name = "gromacs"
		if method == "orca":
			default_image = ORCA_IMAGE
			default_name = "orca"			

		# Replace "_" with "-" because "_" is not kubernetes accepted char in the name
		method = method.replace("_","-")
		
		#set names
		timestamp = str(time.time()).replace(".", "")	
		doc['metadata']['name'] = "{}-{}-rdtscp-{}".format(default_name, method, timestamp)
		doc['spec']['template']['metadata']['labels']['app'] = "{}-{}-rdtscp-{}".format(default_name, method, timestamp)
		doc['spec']['template']['spec']['containers'][0]['name'] = "{}-{}-deployment-{}".format(default_name, method, timestamp)

		#set gromacs args
		doc['spec']['template']['spec']['containers'][0]['args'] = ["/bin/bash", "-c", DoubleQuotedScalarString(command)]

		#if not orca, set options for gmx container
		if method != "orca":
			double_env = {'name' : "DOUBLE", 'value' : DoubleQuotedScalarString("ON" if double == True else "OFF")}
			rdtscp_env = {'name' : "RDTSCP", 'value' : DoubleQuotedScalarString("ON" if rdtscp == True else "OFF")}
			arch_env = {'name' : "ARCH", 'value' : DoubleQuotedScalarString(arch)}
			doc['spec']['template']['spec']['containers'][0]['env'] = [double_env, rdtscp_env, arch_env]

		#set image
		doc['spec']['template']['spec']['containers'][0]['image'] = default_image if not image else image	

		#set working directory
		if workdir:
			doc['spec']['template']['spec']['containers'][0]['workingDir'] = f"/tmp/{workdir}"

		#set PVC
		pvc_name = os.environ['PVC_NAME']
		if len(pvc_name) == 0:
			raise Exception("Error setting pvc_name, probably problem in setting env variable of actual container")
		doc['spec']['template']['spec']['volumes'][0]['persistentVolumeClaim']['claimName'] = pvc_name

		#write to file	
		ofile_name = "{}-{}-rdtscp.yaml".format(default_name, method) 
		with open(ofile_name, "w") as ofile:
			ruamel_yaml.round_trip_dump(doc, ofile, explicit_start=True)

		return ofile_name, doc['metadata']['name']
