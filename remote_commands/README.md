# Remote Operations
A generic tool capable of executing series of commands on a local and remote Linux or Mac machines. It also supports
scp to transfer files and directories from/to a remote machine.

## Dependencies
The tool is written in python 2.7 utilizing the [pexpect](https://pypi.org/project/pexpect/) and [ptyprocess](https://pypi.org/project/ptyprocess/) modules. 
The package files are included in this project to eliminate any external dependency. If you would prefer to install these packages, please remove the **pexpect** and **ptyproces** folders from the project after installing these python modues.

## Structure of the project
Below are the different modules and files in the project

### 1. Framework module [remote.py](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/remote.py)

This is the heart of the tool. This module takes a config file in JSON format (explained below) and executes the list of **actions** specified in the config file. The module supports three types of actions; **local**, **ssh** and **scp**.

  * __local__ action
   
    A **_local_** action will perform the list of commands on the local machine where the program is run. Below are the supported arguments/parameters:
      * **_action_** : a value of ``local`` for local action
      * **_commands_** : list of bash commands to be executed on the local host
    
    For example, a **local** action named ``create_local_dir`` with two bash commands would look like:
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
   
    A **_ssh_** action will perform the list of commands on the remote machine specified using the parameter *hostname*. Below are the supported arguments/parameters:
      * **_hostname_** : hostname of the remote machine
      * **_username_** : username on the remote machine
      * **_password_** : password for the given username
      * **timeout_secs** : Timeout value in secs, incase the connection is not successful. Default: 60 seconds, if not provided
      * **_shell_prompt_** : the regex pattern for the ssh shell prompt from the remote server. In most Linux flavours, this will be ``\\$ $``
      * **_password_prompt_** : the regex pattern for the ssh password prompt from the remote server. In most Linux flavours, this will be ``password: **``
      * **_sudo_password_prompt_** : the regex pattern for the password prompt, when a sudo command is run. In most Linux flavours, this will be ``password for {username}: ``
      
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
   
    A **_scp_** action is used to transfer files from or to a remote machine. The supported arguments are:
      * **_hostname_** : hostname of the remote machine
      * **_username_** : username on the remote machine
      * **_password_** : password for the given username
      * **timeout_secs** : Timeout value in secs, incase the connection is not successful. Default: 60 seconds, if not provided
      * **_direction_** : A value of ``send`` or ``get``. Default value is ``get``, if not specified.
      * **_password_prompt_** : the regex pattern for the scp password prompt from the remote server. In most Linux flavours, this will be ``password: ``
      * **_progress_prompt_** : the regex pattern for the file transfer progress. Most scp implementation will have the progress prompt pattern as ``.\*ETA``
      * **_source_dir_** : source directory
      * **_source_files_** : filename (supports unix wild-cards) or a list of filenames 
      * **_target_dir_** : The target directory is where the file(s) will be trasferred to.
      
      Note: If the **_direction_** is ``get``, then **_target_dir_** will on the local machine and **_source_dir_** will be on the remote machine. If the **_direction_** is ``send``, then the other way around. 
    
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
    ***NOTE:*** If you have multiple actions in a config file, the above arguments/parameters can be defined in the **variables** or **constants** section of a config file, instead of repeating on each of the actions. Refer config file description below for details on **variables** and **constants** sections.
    
    **Usage:**
    ```
    python remote.py --help
    usage: remote.py [-h] -f CONF_FILE [--debug]

    Version 1.0. Script to execute configured commands in local and remote hosts.

    optional arguments:
      -h, --help            show this help message and exit
      -f CONF_FILE, --conf-file CONF_FILE
                            Name of the config file in JSON format
      --debug               *NOT IMPLEMENTED YET* With debug flag, the program
                            will ONLY echo/output all the resolved commands after
                            connecting to the remote/local host; but will NOT
                            attempt to run these commands. This is useful while
                            configuring a new requirement to avoid unwanted impact
                            of running certain non-recoverable commands 
                            like "rm -fr"
    ```
    
### 2. Config file [conf](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/conf)

A config file is a JSON format file with a set of actions configured. This config file is passed to the [remote.py] program to execute all the set of actions.

A sample config file: [conf/simple_local_ssh_scp_actions.json](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/conf/simple_local_ssh_scp_actions.json)

Each config has below sections defined as a JSON element:

  * **variables** and **constants** section
  
    These are optional sections (but very useful) to define variables which can be used as arguments to the actions, values for the arguments and also in the commands. A variable can be used by surrounding inside two curly brackets.
    ```
    "variables" : {
        "credentials.hostname" : [ "ajmal-ssh.azurehdinsight.net", "ec2.18-234-201.compute-1.amazonaws.com" ],
        "credentials.username" : [ "sshuser", "ajmal" ],
        "credentials.password" : [ "mypass123@", "somepass123!" ]
    }
    ```
    ```
    "constants" : {
        "timeout_secs" : "30",
        "shell_prompt" : "\\$ $",
        "password_prompt" : "password: ",
        "progress_prompt" : "ETA",
        "sudo_password_prompt" : "password for {username}:",

        "local_target_dir" : "/Users/ayusuf/CLUSTER_LOGS/{run_id}/{hostname}",
        "remote_working_dir" : "/home/{username}/my_temp_dir",
        "file_name" : [ "test_file_1.out", "test_file_2.out" ]
    }
    ```
    **{run_id}** variable is automatically provided by the **remote.py** program as ``RID_YYYYMMDD_HHMMSS_UTC`` with the UTC timestamp when the program is run. This can be used to identify an instance of the run as the value will be unique.

    Both **variables** and **constants** are treated the same way by the **remote.py** program. This is separated only for the convenience of *programatically* replaing the **variables** section and still retaining all the variables defined in the **constants** section.

    For example, the **hosts_from_ambari_api.py** script reads the Ambari Database, retrieves the hostnames and log file directories for a selected SERVICE, reads the supplied confif file and replaces the **variables** section with the new hostnames/usernames/passwords information and invokes the **remote.py** program.

    Similarly, the **hosts_from_etc_hosts_file.py** sript reads the **/etc/hosts** file and gets the list of hostnames cluster hostnames; then replaces that info in the **variables** section and runs the **remote.py** program.

  * **main** section
  
    This is the point of entry of the actions. This section defines a list of action names, which are defined in the config files. The program will run the actions in the provided order.
    ```
    "main" : [
        "create_local_dir",
        "create_remote_dir",
        "create_remote_files",
        "scp_remote_files_to_local_dir"
    ]
    ```
    All of these actions should be defined in the config file (shown below).

    * **action definitions** 
    ```
    "create_local_dir" : {
        "action" : "local",
        "commands" : [
            "mkdir -p {local_target_dir}",
            "ls -al {local_target_dir}/../"
        ]
    },

    "create_remote_dir" : {
        "action" : "ssh",
        "commands" : [
            "mkdir -p {remote_working_dir}"
        ]
    },

    "create_remote_files" : {
        "action" : "ssh",
        "commands" : [
            "cd {remote_working_dir}",
            "echo \"This line is written by the remote program\" > {file_name}"
        ]
    },

    "scp_remote_files_to_local_dir" : {
        "action" : "scp",
        "direction" : "get",
        "source_dir" : "{remote_working_dir}",
        "source_files" : "{file_name}",
        "target_dir" : "{local_target_dir}"
    }
    ```





