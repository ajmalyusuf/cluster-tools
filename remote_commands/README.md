# Remote Operations
A generic tool capable of executing series of commands on a local and remote Linux or Mac machines. It also supports
scp to transfer files and directories from/to a remote machine.

## Dependencies
The tool is written in python 2.7 utilizing the [pexpect](https://pypi.org/project/pexpect/) and [ptyprocess](https://pypi.org/project/ptyprocess/) modules. 
The package files are included in this project to eliminate any external dependency. If you would prefer to install these packages, please remove the **pexpect** and **ptyproces** folders from the project after installing these python modues.

## Structure of the project
Below are the different modules and files in the project

1. Framework module [remote.py](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/remote.py)

This is the heart of the tool. This module takes a config file in JSON format (explained below) and executes the list of **actions** specified in the config file. The module supports three types of actions; **local**, **ssh** and **scp**.

  * __local__ action
   
    A *local* action will perform the list of commands on the local machine where the program is run. Below are the supported arguments/parameters:
      * **_action_** : a value of "**local**" for local action
      * **_commands_** : list of bash commands to be executed on the local host
    
    For example, a **local** action named '*create_local_dir*' with two bash commands would look like:
    ```python
    "create_local_dir" : {
        "action" : "local",
        "commands" : [
            "mkdir -p {local_target_dir}",
            "ls -al {local_target_dir}/../"
        ]
    },
    ```
    
  * __ssh__ action
   
    A *ssh* action will perform the list of commands on the remote machine specified using the parameter *hostname*. Below are the supported arguments/parameters:
      * **_hostname_** : hostname of the remote machine
      * **_username_** : username on the remote machine
      * **_password_** : password for the given username
      * **_shell_prompt_** : the regex pattern for the ssh shell prompt from the remote server. In most Linux flavours, this will be "``\\$ $``".
      * **_password_prompt_** : the regex pattern for the ssh password prompt from the remote server. In most Linux flavours, this will be "``password: **``".
      * **_sudo_password_prompt_** : the regex pattern for the password prompt, when a sudo command is run. In most Linux flavours, this will be "``password for {username}: ``".
      
    Example of a **ssh** action:
    ```python
    "create_remote_files" : {
        "action" : "ssh",
        "shell_prompt" : "\\$ $",
        "password_prompt" : "password: ",
        "sudo_password_prompt" : "password for {username}:",
        "commands" : [
            "cd {remote_working_dir}",
            "echo \"This line is written by the remote program\" > {file_name}"
        ]
    },
    ```
  
  * __scp__ action
   
    A *scp* action is used to transfer files from or to a remote machine. The supported arguments are:
      * **_hostname_** : hostname of the remote machine
      * **_username_** : username on the remote machine
      * **_password_** : password for the given username
      * **_direction_** : A value of "``send``" or "``get``". Default value is "``get``", if not specified.
      * **_password_prompt_** : the regex pattern for the scp password prompt from the remote server. In most Linux flavours, this will be "``password: ``".
      * **_progress_prompt_** : the regex pattern for the file transfer progress. Most scp implementation will have the progress prompt pattern as "``.\*ETA``".
      * **_source_dir_** : source directory
      * **_source_files_** : filename (supports unix wild-cards) or a list of filenames 
      * **_target_dir_** : The target directory is where the file(s) will be trasferred to.
      
      Note: If the **_direction_** is "``get``", then **_target_dir_** will on the local machine and **_source_dir_** will be on the remote machine. If the **_direction_** is "``send``", then the other way around. 
    
    Example of a **scp** action:
    ```python
    "scp_remote_files_to_local_dir" : {
        "action" : "scp",
        "direction" : "get",
        "password_prompt" : "password: ",
        "progress_prompt" : "ETA",
        "source_dir" : "{remote_working_dir}",
        "source_files" : "{file_name}",
        "target_dir" : "{local_target_dir}"
    }
    ```   
    
2. Config file [conf](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/conf)

A config file is a JSON format file with set of actions configured. 
stored in 'conf' directory
- Contains the variables and script definitions to configure a set actions and commands to be performed on local or
remote host machines




