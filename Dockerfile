FROM ubuntu:18.04

USER root

#add basic user
RUN bash -c "useradd --uid 1001 --create-home --shell /bin/bash magic_user"

#set variables
ARG INTELPYTHON
ENV DEBIAN_FRONTEND=noninteractive 
ENV TZ=Europe/Prague
ENV BASE=/home/base
ENV SHARED_DIR=/work

#install IntelPython from manually downloaded package specified in build script
COPY ${INTELPYTHON} /tmp
RUN cd /opt && \
    tar xzf /tmp/${INTELPYTHON} && \
    cd intelpython3 && \
    ./setup_intel_python.sh && \
    echo source /opt/intelpython3/bin/activate  >>/etc/bash.bashrc && rm /tmp/${INTELPYTHON}

#install jupyter, python tools and widgets used for visualisation
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y ruamel_yaml"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c conda-forge jupyter"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -n base -c conda-forge widgetsnbextension"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c conda-forge ipywidgets"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y --freeze-installed -c conda-forge pypdb pydoe mdtraj nglview"
RUN bash -c "source /opt/intelpython3/bin/activate && jupyter-nbextension enable nglview --py --sys-prefix"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y pandas"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c rmg py3dmol"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c conda-forge tqdm"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c plotly plotly"

#install openbabel, amber, molvs
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c openbabel openbabel"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y ambertools=19 -c ambermd"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c conda-forge molvs"

#install LibXrender1 needed for RDkit library
RUN bash -c "apt-get update && apt-get install -y libxrender1 libgfortran3"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c rdkit rdkit"

#install acpype and its needed packages xorg-libxext and pillow
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c conda-forge acpype"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c conda-forge xorg-libxext"
RUN bash -c "source /opt/intelpython3/bin/activate && conda install -y -c conda-forge pillow"

#install parmtSNE
RUN bash -c "apt-get update && apt-get install -y git"
RUN bash -c "cd /opt && git clone https://github.com/spiwokv/parmtSNEcv.git" 
RUN bash -c "source /opt/intelpython3/bin/activate && pip install 'ruamel.yaml<=0.15.94' && cd /opt/parmtSNEcv && pip install . && pip install --ignore-installed six tensorflow"

#install kubectl
RUN bash -c "apt-get update && apt-get install -y apt-transport-https gnupg2 curl xz-utils"
RUN bash -c "curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -"
RUN bash -c "echo 'deb https://apt.kubernetes.io/ kubernetes-xenial main' | tee -a /etc/apt/sources.list.d/kubernetes.list"
RUN bash -c "apt-get update && apt-get install -y kubectl"

#install other tools
ARG distribution=ubuntu18.04
RUN bash -c "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -"
RUN bash -c "echo 'deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable' >>/etc/apt/sources.list"
RUN bash -c "curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -"
RUN bash -c "curl -s -L -o /etc/apt/sources.list.d/nvidia-docker.list https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list" 
RUN bash -c "apt update && apt install -y docker-ce-cli nvidia-container-toolkit"
RUN bash -c "apt-get install sudo -y"
RUN bash -c "apt-get install jq -y"

#copy all necessary files to run force field correction evaluation
COPY modules ${BASE}/modules/
COPY ./gromacs-plumed-docker/gromacs/gmx-docker orca-docker podman-run.py /opt/
COPY tleapin.txt ${SHARED_DIR}/

#give permissions
RUN bash -c "chmod -R a+rX /opt /home"

WORKDIR ${SHARED_DIR}
EXPOSE 8888


#run Jupyter Notebook when container is executed
CMD bash -c "sleep 2 && curl -LO https://gitlab.ics.muni.cz/467814/magicforcefield-pipeline/-/raw/kubernetes/pipelineJupyter.ipynb && source /opt/intelpython3/bin/activate && jupyter notebook --ip 0.0.0.0 --allow-root --port 8888"
