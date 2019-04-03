# Remote Operations
A generic tool capable of executing series of commands on a local and remote Linux or Mac machines. It also supports
scp to transfer files and directories from/to a remote machine.

## Dependencies
The tool is written in python 2.7 utilizing the [pexpect](https://pypi.org/project/pexpect/) and [ptyprocess](https://pypi.org/project/ptyprocess/) modules. 
The package files are included in this project to eliminate any external dependency. If you would prefer to install these packages, please remove the **pexpect** and **ptyproces** folders from the project after installing these python modues.

## 1. Main program [run_remote.py](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/run_remote.py)
This python file is the main program which can be used to execute a series of commands interactively or automatically (configued as a JSON config file) in local and remote hosts. The program is capable of running any UNIX shell command(s) on any host with credentials.

The program supports **4 subcommands** namely **conf**, **hosts**, **cred** and **ambari**. These subcommands can be effectively used to retrieve **hostnames**, **credentials** and any other useful properties and then pass it along with the JSON config file to the [remote.py](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/remote.py) module.

**Usage:**
```
python run_remote.py --help
usage: run_remote.py [-h] [-v] {conf,hosts,cred,ambari} ...

Script to execute configured commands in local and remote hosts. The program
is capable of running any UNIX command on any host with credentials

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit

subcommands:
  Following subcommands are supported:

  {conf,hosts,cred,ambari}
    conf                Uses hostnames from the config file itself or comma
                        seperated parameter
    hosts               Uses hostnames from /etc/hosts file
    cred                Uses hostnames from the a credential csv file having
                        hostname,username,password as columns
    ambari              Uses hostnames, log directories for a specific
                        service/component from Ambari API
```
The subcommand is **NOT optional** and should be supplied. Each subcommand has _specific arguments_ in addition to a set of common arguments.

Below are the **_common arguments_** for all the subcommands:
```
optional arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        SSH username to connect to hosts
  -p PASSWORD, --password PASSWORD
                        SSH password to connect to hosts
  --run-id RUN_ID       Unique RUN ID. Default: Will be automatically
                        generated in the format RID_YYYYMMDD_HHMISS_UTC.
                        "run_id" can be used inside the config file as a
                        variable to create unique directories/filenames etc to
                        uniquely identify a run instance
  --live-run            The program is capable of running any UNIX command on
                        any host with credentials. To AVOID any unwanted
                        consequences of running certain non-recoverable
                        commands like "rm -fr", the program will EXECUTE the
                        commands only if this flag is enabled. If False, the
                        program will ONLY print all the resolved commands.

only one or the other:
  -f CONF_FILE, --conf-file CONF_FILE
                        Name of the config file in JSON format
  --interactive         Flag to enable SSH in an interactive mode
```
**NOTE:**

For the sake of easiness or repetitive use, you may configure default values for **username**, **password** and **live-run** in the [default_properties.json](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/default_properties.json) file. This file also contains default values for some of the program internal variables like shell, timeouts, prompts etc.
```
{
    "--any variable starting with a -- is commented or ignored" : "this line is ignoded",

    "default_live_run" : "False",
    "username" : "sshuser",
    "password" : "mypass!",

    "shell" : "bash",
    "timeout_secs" : "60",
    "shell_prompt" : "[#\\$] $",
    "password_prompt" : "password: ",
    "sudo_password_prompt" : "password for {username}: ",
    "progress_prompt" : "ETA",

    "ambari_server" : "headnodehost",
    "ambari_port" : "8080",
    "ambari_username" : "admin",
    "--ambari_password" : "mypass!"
}
```

Lets take a look at each of the subcommands.

### 1.1. Using subcommand "conf"
With this subcommand you may optionally pass a list of hostname(s) as comma separated by using the argument `-n or --hostnames`. If the argument is NOT used, then the hostname variable inside the config (JSON) file will be used.
**Usage:**
```
python run_remote.py conf --help
usage: run_remote.py conf [-h] [-u USERNAME] [-p PASSWORD] [--run-id RUN_ID]
                          [--live-run] [-f CONF_FILE | --interact]
                          [-n HOSTNAMES]

optional arguments:
  ... <refer common arguments above> ...

optional subcommand (conf) arguments:
  -n HOSTNAMES, --hostnames HOSTNAMES
                        Hostname(s). Comma separated for multiple values
```

**Sample commands:**

a) Below command will execute the commands configured in the [conf/sample_config.json](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/conf/sample_config.json) config file on the 3 hosts supplied as -n argument
```
python run_remote.py conf -n hn0-myhdi.cloudapp.net,hn1-myhdi.cloudapp.net,wn0-myhdi.cloudapp.net -f conf/sample_config.json
```
b) Below command will use the hostnames configured in the JSON config file.
**NOTE:** If a config variable is configured as `:p?` or `:pp?` (for passwords), the program will **_prompt the user_** for the value.
```
python run_remote.py conf -f conf/sample_config.json
```
c) Below command will run as interactive mode on the first host and then you will be prompted if you need to run all the interactive commands on the remaining hosts automatically.
```
python run_remote.py conf -n hdi1-265,hdi2-265 --interact -u ajmal -p :pp?
```
**Note:** since interactive option does not use a config file, you may need to supply the `username` and `password` as parametes or configure default values in [default_properties.json](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/default_properties.json). Alternatively, you may use `:pp?` for silent prompt (without showing what you type or `:p?` for normal prompt. For example:
```
ayusuf@MacBook-Pro:~/git/cluster-tools/remote_commands$ python run_remote.py conf -n hdi1-265,hdi2-265 --interact -u ajmal -p :pp?
Enter the value for password [exit]:
```

### 1.2. Using subcommand "hosts"
With this subcommand the program will use all the hostname(s) configured in `/etc/hosts` file. Optionally you may use `-i/--include-prefix` or `-e/--exclude-prefix` to filter hostnames.
**Usage:**
```
python run_remote.py hosts --help
usage: run_remote.py hosts [-h] [-u USERNAME] [-p PASSWORD] [--run-id RUN_ID]
                           [--live-run] [-f CONF_FILE | --interact]
                           [-i INCLUDE_PREFIX] [-e EXCLUDE_PREFIX]

optional arguments:
  ... <refer common arguments above> ...

optional subcommand (hosts) arguments:
  -i INCLUDE_PREFIX, --include-prefix INCLUDE_PREFIX
                        Hostname prefixes to be included
  -e EXCLUDE_PREFIX, --exclude-prefix EXCLUDE_PREFIX
                        Hostname prefixes to be excluded. If include_prefix is
                        provided, that takes preference
```

**Sample commands:**

a) Below command will use all the hostnames from the `/etc/hosts` file except anything starting with `gw`.
```
python run_remote.py hosts -e gw -f conf/sample_config.json -u sshuser -p mypass!
```
b) Below command will run on all the hosts starting with wn. In Azure HDI clusters, worker nodes will have hostnames starting with `wn`. So this will ONLY be run on worker nodes.
```
python run_remote.py hosts -i wn --interact -u sshuser -p :pp?
```

### 1.3. Using subcommand "cred"
With this subcommand the program will use the list of hostname, username and passwords configured in credential CSV file, which has to be passed as `-c/--cred-file` argument.
**Usage:**
```
python run_remote.py cred --help
usage: run_remote.py cred [-h] [-u USERNAME] [-p PASSWORD] [--run-id RUN_ID]
                          [--live-run] [-f CONF_FILE | --interact]
                          -c CRED_FILE

optional arguments:
  ... <refer common arguments above> ...

optional subcommand (cred) arguments:
  -c CRED_FILE, --cred-file CRED_FILE
                        CSV file with hostname,username,password as columns.
                        The password (last) column will NOT be trimmed and can
                        have white spaces.
```

Example **cred** CSV file (You may use # to comment a line)
```
# hostname/ip, ssh_username, ssh_password (after second comma unitl \n; including spaces)
hdi1-265.openstacklocal, ajmal,ajmal12
hdi2-265.openstacklocal, ,ajmal12
hdi3-265.openstacklocal, ajmal,
#hdi4-265.openstacklocal, ajmal,
abchadoop-ssh.azurehdinsight.net, sshuser,ssHpa$$!
```

**Sample commands:**

a) Below command will use the credentials from the CSV file (azure.csv)
If you are suppying `username` and `password` as arguments, those will be used for hostnames with missing username or password in the CSV file.
```
python run_remote.py cred -c azure.csv -f conf/sample_config.json -u sshuser -p mypass!
```
b) Below command can be used for interative mode
```
python run_remote.py cred -c azure.csv --interact -u sshuser -p :pp?
```

### 1.3. Using subcommand "ambari"
With this subcommand the program will use the supplied AMBARI information, use Ambari REST API to collect hostnames and log directories for a given SERVICE and COMPONENT.
**Usage:**
```
python run_remote.py ambari --help
usage: run_remote.py ambari [-h] [-u USERNAME] [-p PASSWORD] [--run-id RUN_ID]
                            [--live-run] [-f CONF_FILE | --interactive]
                            [-a AMBARI_SERVER] [-r PORT] [-x AMBARI_USER]
                            [-y AMBARI_PASS] [-n CLUSTERNAME] [-s SERVICE]
                            [-c COMPONENT]

optional arguments:
  ... <refer common arguments above> ...

optional subcommand (ambari) arguments:
  -a AMBARI_SERVER, --ambari-server AMBARI_SERVER
                        IP/Hostname of the Ambari Server
  -r PORT, --port PORT  Port number for Ambari Server. Default: 8080
  -x AMBARI_USER, --ambari-user AMBARI_USER
                        Username for Ambari UI. Default: admin.
  -y AMBARI_PASS, --ambari-pass AMBARI_PASS
                        Password for Ambari UI. Default: admin
  -n CLUSTERNAME, --clustername CLUSTERNAME
                        Name of the cluster. Default: First available cluster
                        name in Ambari
  -s SERVICE, --service SERVICE
                        Service Name
  -c COMPONENT, --component COMPONENT
                        Component Name
```

**Sample commands:**

a) Below command will connect to ambari and get the hostname for HIVE service and HIVE_SERVER component and run the commands on that hose. The JSON config file [ambari_copy_and_tar_logs_to_headnodehost.json](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/conf/ambari_copy_and_tar_logs_to_headnodehost.json) is configured to collect the log files for the SERVICE/COMPONENT(s).
```
python run_remote.py ambari -a headnodehost -x admin -y admin12 -s HIVE -c HIVE_SERVER -f conf/ambari_copy_and_tar_logs_to_headnodehost.json -u sshuser -p sshpass!
```
b) Below command will prompt you to select one of the available service and a component (or all components) and the program will connect to the hosts having those components.
```
python run_remote.py ambari -a headnodehost -x admin -y admin12 -s HIVE -c HIVE_SERVER -f conf/ambari_copy_and_tar_logs_to_headnodehost.json -u sshuser -p sshpass!
```
For example:
```
python run_remote.py ambari -a hdi1-265.openstacklocal -x admin -y admin12 -f conf/ambari_copy_and_tar_logs_to_headnodehost.json -u ajmal -p ajmal12

Connecting to Ambari REST API: http://hdi1-265.openstacklocal:8080/api/v1

1. AMBARI_METRICS
2. HDFS
3. HIVE
4. MAPREDUCE2
5. PIG
6. SLIDER
7. SMARTSENSE
8. SPARK
9. SPARK2
10. SQOOP
11. TEZ
12. YARN
13. ZEPPELIN
14. ZOOKEEPER
Select a service [Exit]: 3

1. HCAT
2. HIVE_CLIENT
3. HIVE_METASTORE
4. HIVE_SERVER
5. HIVE_SERVER_INTERACTIVE
6. MYSQL_SERVER
7. WEBHCAT_SERVER
8. All of the above
Select HIVE component [Exit]: 8

Below are the hosts/nodes for HIVE:
1. hdi1-265.openstacklocal
    - HCAT
    - HIVE_CLIENT
2. hdi2-265.openstacklocal
    - HCAT
    - HIVE_CLIENT
3. hdi3-265.openstacklocal
    - HCAT
    - HIVE_CLIENT
4. hdi4-265.openstacklocal
    - HCAT
    - HIVE_CLIENT
    - HIVE_METASTORE
    - HIVE_SERVER
    - HIVE_SERVER_INTERACTIVE
    - MYSQL_SERVER
    - WEBHCAT_SERVER
 
 Reading config from: conf/ambari_copy_and_tar_logs_to_headnodehost.json
 ...
 ...
 ```
 

## 2. JSON Config file

The config file supports three types of actions; **local**, **ssh** and **scp**.

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
      * **_shell_prompt_** : the regex pattern for the ssh shell prompt from the remote server. In most Linux flavours, this will be ``\$ $`` for user and ``\# $`` for root. So the default value is ``[\$\#]? $`` (supporting both) 
      * **_password_prompt_** : the regex pattern for the ssh password prompt from the remote server. In most Linux flavours, this will be ``password: ``
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
    

## 2.1 Config file (examples in [conf](https://github.com/ajmalyusuf/cluster-tools/edit/master/remote_commands/conf) folder)

A config file is a JSON format file with a set of actions configured. This config file is passed to the [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) module to execute all the set of actions.

**The [remote.py](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/remote.py) module is intelligent to run each of the actions for that many iterations as defined by the number of values for each of the variables used in the action.**. Detailed explanation is provided in Section 2.3 Actions section.

A sample config file: [conf/simple_local_ssh_scp_actions.json](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/conf/simple_local_ssh_scp_actions.json)

Each config file has below sections defined as a JSON elements:

### 2.1. "**variables**" section
  
**variables** is a optional sections (but very useful) to define variables which can be used as arguments to the actions, values for the arguments and also in the commands. A variable can be used by surrounding inside two curly brackets.
    
```
"variables" : {
    "credentials.hostname" : [ "ajmal-ssh.azurehdinsight.net", "ec2.18-234-201.compute-1.amazonaws.com" ],
    "credentials.username" : [ "sshuser", "ajmal" ],
    "credentials.password" : [ "mypass123@", "somepass123!" ]

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
    
**{run_id}** variable is automatically provided by the program as ``RID_YYYYMMDD_HHMMSS_UTC`` with the UTC timestamp when the program is run. This can be used to identify an instance of the run as the value will be unique.


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

The **remote.py** module, is intellent to resolve the _{local_target_dir}_ variable as two sets of values by taking the **cartesian product** of the values of _{run_id}_ and _{hostname}_
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
A sample output screenshot:
[sample_output.jpg](https://github.com/ajmalyusuf/cluster-tools/blob/master/remote_commands/sample_output.jpg)




