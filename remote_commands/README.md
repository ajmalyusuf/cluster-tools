# Remote Operations
A generic tool capable of executing series of commands on a local and remote Linux or Mac machines. It also supports
scp to transfer files and directories from/to a remote machine.

## Dependencies
The tool is written in python 2.7 utilizing the [pexpect](https://pypi.org/project/pexpect/) and [ptyprocess](https://pypi.org/project/ptyprocess/) modules. 
The package files are included in this project to eliminate any external dependency. If you would prefer to install these packages, please remove the **pexpect** and **ptyproces** folders from the project after installing these python modues.

## 1. Framework module [remote.py](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/remote.py)

This is the heart of the tool. This module takes a config file in JSON format (explained below) and executes the list of **actions** specified in the config file. The module supports three types of actions; **local**, **ssh** and **scp**.

  * __local__ action
   
    A **_local_** action will perform the list of commands on the local machine where the program is run. Below are the supported arguments/parameters:
      * **_action_** : a value of ``local`` for local action
      * **_commands_** : list of bash commands to be executed on the local host
   
  * __ssh__ action
   
    A **_ssh_** action will perform the list of commands on the remote machine specified using the parameter *hostname*. Below are the supported arguments/parameters:
      * **_hostname_** : hostname of the remote machine
      * **_username_** : username on the remote machine
      * **_password_** : password for the given username
      * **timeout_secs** : Timeout value in secs, incase the connection is not successful. Default: 60 seconds, if not provided
      * **_shell_prompt_** : the regex pattern for the ssh shell prompt from the remote server. In most Linux flavours, this will be ``\\$ $``
      * **_password_prompt_** : the regex pattern for the ssh password prompt from the remote server. In most Linux flavours, this will be ``password: **``
      * **_sudo_password_prompt_** : the regex pattern for the password prompt, when a sudo command is run. In most Linux flavours, this will be ``password for {username}: ``
   
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
      
      If the **_direction_** is ``get``, then **_target_dir_** will on the local machine and **_source_dir_** will be on the remote machine. If the **_direction_** is ``send``, then the other way around. 
    
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
    
## 2. Config file [conf](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/conf)

A config file is a JSON format file with a set of actions configured. This config file is passed to the [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) program to execute all the set of actions.

**The [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) program is intelligent to run each of the actions for that many iterations as defined by the number of values for each of the variables used in the action.**. Detailed explanation is provided in Section 2.3 Actions section.

A sample config file: [conf/simple_local_ssh_scp_actions.json](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/conf/simple_local_ssh_scp_actions.json)

Each config file has below sections defined as a JSON elements:

### 2.1. "**variables**" and "**constants**" section
  
**variables** and **constants** are optional sections (but very useful) to define variables which can be used as arguments to the actions, values for the arguments and also in the commands. A variable can be used by surrounding inside two curly brackets.
    
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
    "remote_working_dir" : "/home/{username}/{hostname}",
    "file_name" : [ "test_file_1.out", "test_file_2.out" ]
}
```
    
**{run_id}** variable is automatically provided by the [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) program as ``RID_YYYYMMDD_HHMMSS_UTC`` with the UTC timestamp when the program is run. This can be used to identify an instance of the run as the value will be unique.

Both **variables** and **constants** are treated the same way by the [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) program. This is separated only for the convenience of *programatically* replacing the **variables** section and still retaining all the variables defined in the **constants** section.

For example, the [hosts_from_ambari_api.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/hosts_from_ambari_api.py) script reads the Ambari Database, retrieves the hostnames and log file directories for a selected SERVICE, reads the supplied config file, replaces the **variables** section with the retrieved hostnames/usernames/passwords information and invokes the [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) program.

Similarly, the [hosts_from_etc_hosts_file.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/hosts_from_etc_hosts_file.py) script reads the **/etc/hosts** file and gets the list of cluster hostnames; then replaces that info in the **variables** section and runs the [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) program.

### 2.2. "**main**" section
  
This is the point of entry of the actions. This section defines a list of action names, which are defined in the config files. The program will run the actions in the given order.

```
"main" : [
    "create_local_dir",
    "create_remote_dir",
    "create_remote_files",
    "scp_remote_files_to_local_dir"
]
```
All of these actions should be defined in the config file (shown below).

### 2.3. **Action definitions** 

#### 2.3.1 "create_local_dir" action

The below JSON element defines the _create_local_dir_ local action. **_mkdir_** and the **_ls_** commands will be performed on the local machine where the program is run.
```
"create_local_dir" : {
    "action" : "local",
    "commands" : [
        "mkdir -p {local_target_dir}",
        "ls -al {local_target_dir}/../"
    ]
},
```
Please note that the variable _{local_target_dir}_ is defiend in the **constants** section, using two other variables: _{run_id}_ and _{hostname}_.

_{run_id}_ has only one value for any run instance; lets assume it to be "*RID_20181216_152011_UTC*" (automatically generated based on system timestamp when run). But, _{hostname}_ is configured as a list/array of 2 values: "*ajmal-ssh.azurehdinsight.net*", "*ec2.18-234-201.compute-1.amazonaws.com*".

The **remote.py** program, is intellent to resolve the _{local_target_dir}_ variable as two sets of values by taking the **cartesian product** of the values of _{run_id}_ and _{hostname}_
1. ( RID_20181216_152011_UTC, ajmal-ssh.azurehdinsight.net )
2. ( RID_20181216_152011_UTC, ec2.18-234-201.compute-1.amazonaws.com )

So the above action/commands will be run for two iterations as:

First iteration:
```
mkdir -p /Users/ayusuf/CLUSTER_LOGS/RID_20181216_152011_UTC/ajmal-ssh.azurehdinsight.net
ls -al /Users/ayusuf/CLUSTER_LOGS/RID_20181216_152011_UTC/ajmal-ssh.azurehdinsight.net/../
```
Second iteration:
```
mkdir -p /Users/ayusuf/CLUSTER_LOGS/RID_20181216_152011_UTC/ec2.18-234-201.compute-1.amazonaws.com
ls -al /Users/ayusuf/CLUSTER_LOGS/RID_20181216_152011_UTC/ec2.18-234-201.compute-1.amazonaws.com/../
```
So two directories will be created in the local machine:

#### 2.3.2 "create_remote_dir" action

Consider the _{remote_working_dir}_ variable used in this action.

```
"create_remote_dir" : {
    "action" : "ssh",
    "commands" : [
        "mkdir -p {remote_working_dir}"
    ]
},
```
The value of this variable is "_/home/{username}/{hostname}_", which shows that it has two other variables _{username}_ and _{hostname}_
In the **variables** section, both of these variables (and _{password}_) are grouped under _credentials_ name with a dot (.) seperator.
```
    "credentials.hostname" : [ "ajmal-ssh.azurehdinsight.net", "ec2.18-234-201.compute-1.amazonaws.com" ],
    "credentials.username" : [ "sshuser", "ajmal" ],
    "credentials.password" : [ "mypass123@", "somepass123!" ]
```
This indicates the remote.py program to use all of these variables (_{hostname}, {username} and {password}_) together as a group when performing a **cartesian product** with other variables. This is very important because, we do not one username or password to be used by the other hostname.

So the below command will first be resolved to the other variables and then run only for two iterations.
```
"mkdir -p {remote_working_dir}" RESOLVED TO "mkdir -p /home/{username}/{hostname}"
```
Two sets of value:
1. ( sshuser, ajmal-ssh.azurehdinsight.net )
2. ( ajmal, ec2.18-234-201.compute-1.amazonaws.com )

First iteration:
```
"mkdir -p /home/sshuser/ajmal-ssh.azurehdinsight.net"
```
Second iteration:
```
"mkdir -p /home/ajmal/ec2.18-234-201.compute-1.amazonaws.com"
```
**Note:** It will **NOT** create a directory something like /home/**sshuser**/ec2.18-234-201.compute-1.amazonaws.com as each set of values are grouped by the _credentials_ group name. You can give any name for a group; but all the variables in a group should have the same name (prefix before dot)

#### 2.3.3 "create_remote_dir" action
Similarly, the below action has three variables _{username}_, _{hostname}_ (resolved from _{remote_working_dir}_) and _{file_name}_
```
"create_remote_files" : {
    "action" : "ssh",
    "commands" : [
        "cd {remote_working_dir}",
        "echo \"This line is written by the remote program\" > {file_name}"
    ]
},
```
_{username}_ and _{hostname} are grouped as _credentials_; so those have only two values

_{file_name}_ is a list/array of two values "test_file_1.out" and "test_file_2.out"

So the **cartesian product** will be between:
( sshuser, ajmal-ssh.azurehdinsight.net ) , ( ajmal, ec2.18-234-201.compute-1.amazonaws.com )
and
test_file_1.out and test_file_2.out

Resulting in 4 sets of values:
1. sshuser, ajmal-ssh.azurehdinsight.net, test_file_1.out
2. sshuser, ajmal-ssh.azurehdinsight.net, test_file_2.out
3. ajmal, ec2.18-234-201.compute-1.amazonaws.com, test_file_1.out
4. ajmal, ec2.18-234-201.compute-1.amazonaws.com, test_file_2.out

The **cd** and **echo** commands will be run for 4 iterations.
```
"cd /home/sshuser/ajmal-ssh.azurehdinsight.net",
"echo \"This line is written by the remote program\" > test_file_1.out"

"cd /home/sshuser/ajmal-ssh.azurehdinsight.net",
"echo \"This line is written by the remote program\" > test_file_2.out"

"cd /home/ajmal/ec2.18-234-201.compute-1.amazonaws.com",
"echo \"This line is written by the remote program\" > test_file_1.out"

"cd /home/ajmal/ec2.18-234-201.compute-1.amazonaws.com",
"echo \"This line is written by the remote program\" > test_file_2.out"     
```
#### 2.3.4 "scp_remote_files_to_local_dir" action
I am tired to explain this; please figure it out as an exercise :-)
```
"scp_remote_files_to_local_dir" : {
    "action" : "scp",
    "direction" : "get",
    "source_dir" : "{remote_working_dir}",
    "source_files" : "{file_name}",
    "target_dir" : "{local_target_dir}"
}
```





