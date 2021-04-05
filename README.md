Run instructions:

1. Go to https://pmcvff-correction.cerit-sc.cz/
2. Log in via Elixir
3. Start your own pipeline
4. Use the pipeline

---

Bonus info:
- you can check output of each orca method in orca_output directory

---
---
---

Build instructions:

Before executing build script, you need to get all necessary software
which has to be downloaded/set manually:

* Podman or Docker: https://podman.io/ or https://www.docker.com/
* IntelPython: https://software.intel.com/en-us/distribution-for-python/choose-download
    * note1: if there has been released new version, which is not set in Dockerfile, contact me or just set new version in Dockerfile manually
    * note2: download it to pipeline directory (where Dockerfile is)
* Git clone: https://gitlab.ics.muni.cz/3086/gromacs-plumed-docker
    * note: clone it inside pipeline directory

1. Execute script build.sh with flag -p for podman (no flag for docker) which will build the image for pipeline
