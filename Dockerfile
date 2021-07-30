FROM ubuntu:20.04 as build

USER root

ENV DEBIAN_FRONTEND=noninteractive 
ENV TZ=Europe/Prague

RUN apt update && apt install -y python3-pip git
# RUN pip3 install six tensorflow
RUN pip3 install jupyter 
RUN pip3 install jupyter_packaging 
RUN pip3 install nglview
RUN jupyter-nbextension enable nglview --py --sys-prefix
RUN pip3 install Pillow tqdm molvs matplotlib mdtraj
RUN pip3 install py3Dmol plotly ruamel_yaml 
RUN pip3 install pandas
RUN apt-get install -y python3-rdkit librdkit1 rdkit-data

##? 
#RUN bash -c "apt-get update && apt-get install -y libxrender1 libgfortran3 git sudo jq apt-transport-https gnupg2 curl xz-utils"

#COPY --from=spectraes/pmcv-pipeline-python:2021-04-19 /opt/intelpython3 /opt/intelpython3
#COPY --from=lachlanevenson/k8s-kubectl:v1.20.2 /usr/local/bin/kubectl /usr/local/bin/kubectl

#RUN bash -c "source /opt/intelpython3/bin/activate && jupyter-nbextension enable nglview --py --sys-prefix"

#install parmtSNE
WORKDIR /opt
RUN git clone https://github.com/spiwokv/parmtSNEcv.git
#RUN pip3 install 'ruamel.yaml<=0.15.94'
WORKDIR /opt/parmtSNEcv
RUN pip3 install .

#install other tools
#ARG DISTRIBUTION=ubuntu18.04  !!! at 20.04 now
#ARG NVIDIA_DOCKER_LIST="https://nvidia.github.io/nvidia-docker/${DISTRIBUTION}/nvidia-docker.list"

#RUN apt install -y curl
#RUN bash -c "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -"
#RUN bash -c "echo 'deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable' >>/etc/apt/sources.list"
#RUN bash -c "curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | apt-key add -"
#RUN bash -c "curl -s -L -o /etc/apt/sources.list.d/nvidia-docker.list ${NVIDIA_DOCKER_LIST}" 
#RUN apt install -y docker-ce-cli
#RUN apt install -y nvidia-container-toolkit

FROM ubuntu:20.04

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Prague

RUN apt update
RUN apt-get install -y python3-distutils python3-rdkit librdkit1 rdkit-data

RUN apt install -y curl
RUN curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
RUN bash -c 'echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" >/etc/apt/sources.list.d/kubernetes.list'
RUN apt update
RUN apt install -y kubectl

COPY --from=build /usr/local /usr/local/

#copy all necessary files to run PMCV force field correction pipeline
COPY modules /home/base/modules/
COPY tleapin.txt /work/
COPY init.sh /opt/
RUN chown -R 1001:1001 /work

ENV PYTHONPATH=/home/base
ENV HOME=/work

WORKDIR /work
EXPOSE 8888




# CMD bash -c "/opt/init.sh && \
#    sleep 2 && \
#    curl -LO https://gitlab.ics.muni.cz/467814/magicforcefield-pipeline/-/raw/kubernetes/pipelineJupyter.ipynb && \
#    source /opt/intelpython3/bin/activate && \
#    jupyter notebook --ip 0.0.0.0 --allow-root --port 8888"
