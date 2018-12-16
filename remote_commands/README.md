# Remote Operations
A generic tool capable of executing series of commands on a local and remote Linux or Mac machines. It also supports
scp to transfer files and directories from/to a remote machine.

## Dependencies
The tool is written in python 2.7 utilizing the [pexpect](https://pypi.org/project/pexpect/) and [ptyprocess](https://pypi.org/project/ptyprocess/) modules. 
The package files are included in this project to eliminate any external dependency. If you would prefer to install these packages, please remove the **pexpect** and **ptyproces** folders from the download.

## Structure of the project
Below are the different modules and files in the project

1. Framework module [remote.py](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/remote.py)
This is the heart of the tool. This module takes a config file (explained below) and executes the list of **actions** specified in the config file. The module supports three types of actions; **local**, **ssh** and **scp**.
- **local**
  ddddd

- **ssh**
  wfewfwwf
  
- **scp**
  fweeww

2. Config file [conf](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/conf)
These are JSON format files with instructions on list of commands. 
stored in 'conf' directory
- Contains the variables and script definitions to configure a set actions and commands to be performed on local or
remote host machines




