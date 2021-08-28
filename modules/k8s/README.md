# Gromacs and Orca Kubernetes wrapper
Every minor software package needed is contained in the main pipeline image. [Gromacs](https://www.gromacs.org/) and [Orca](https://sites.google.com/site/orcainputlibrary/home) are considered too large to be contained in the main container. Therefore these packages are divided into another two independent images.

This implies there is a need of connecting the main pipeline container with Gromacs and Orca containers. A wrapper has been written exactly for this purpose.  The wrapper is written in *Python* and converts the Gromacs/Orca command along with its arguments to a .yaml (Kubernetes job) configuration file. Based on this file the Kubernetes job is spawned where all computations happen. 

# **Gromacs**
## gmx_run()
***Mandatory argument:***

```
string gmx_command       -       gromacs command to be evaluated
```

***Optional arguments:***

```
int mpi_run              -       request number of cpus for mpi_run software
string groups            -       specify interactive groups for gromacs (1)
string make_ndx          -       specify interactive make_ndx input for gromacs make_ndx (2)
string image             -       specify used gromacs image
string workdir           -       specify directory where should the calculation take place
string arch              -       specify CPU architecture
bool double              -       double precision for mdrun (3)
bool rdtscp              -       enable rdtscp
bool parallel            -       run jobs in parallel (independently). Disabled by default
```

1. https://manual.gromacs.org/documentation/2019-rc1/reference-manual/analysis/using-groups.html
2. https://manual.gromacs.org/archive/5.0.4/programs/gmx-make_ndx.html
3. https://manual.gromacs.org/current/onlinehelp/gmx-mdrun.html

---

***Example usages:***

```
gmx_run('mdrun -deffnm em1 -ntomp 2')
gmx_run('mdrun -deffnm mtd1 -replex 500 -plumed plumed.dat', mpi_run=6')
gmx_run('mdrun -deffnm em1', image='user/gromacs:123')
gmx_run('mdrun -deffnm em1 -ntomp 2', arch='AVX256')
gmx_run('mdrun -deffnm em1 -ntomp 2', workdir='/home', double=True, arch='AVX256')
```


# ***Orca***
## orca_run()
***Mandatory arguments:***
```
string orca_command      -       orca method (file) used for computation (1)
string log               -       log file to store the output of computation
```

***Optional arguments:***
```
string image             -       specify used Orca image
string workdir           -       specify directory where should the calculation take place
bool parallel            -       run jobs in parallel (independently). Disabled by default
```

1. https://sites.google.com/site/orcainputlibrary/generalinput

---

***Example usages:***

```
orca_run('method1.inp', 'output1.out", workdir='/home', parallel=True)
```


# ***Gromacs/Orca***
## parallel_wait()
This method has to be placed after a `gmx_run()` or `orca_run()` with *parallel* enabled. It is a wait mechanism to detect if all jobs running in parallel finished. Afterwards logs of these jobs are printed. 

```
orca_run('method1.inp', 'output1.out", workdir='/home', parallel=True)
orca_run('method2.inp', 'output2.out", workdir='/home', parallel=True)

parallel_wait()

---

for i in range 6:
    orca_run(f'method{i}.inp', f'output{i}.out", workdir='/home', parallel=True)
parallel_wait()
```
