# Custom Monitoring solution


## Introduction

The python script will look in the processes file, will collect metrics about each process and it will send the data to the metrics explorer in OCI.
Because the python script needs to send data continuously it needs to run as a service.

The Ansible playbook will do all the work, it will copy the processes file and the python script on the list of hosts and it will create a service based on the python script on both Windows and Linux hosts.


## Inside the solution's folder you will find:

* ansible_script.yaml - ansible playbook
* inventory.ini - ansible inventory file
* Readme.md - Readme file
* files - folder
    * custom-metrics.py - python script
    * linux_processes_to_monitor.txt - file containing the processes to monitor for Linux hosts
    * win_processes_to_monitor.txt - file containing the processes to monitor fin Windows hosts
* templates - folder
    * custom_metrics.service - template file used to make the python script run as a service


## Requirements

- Ansible installed. [click here for documentation](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
- Python3 installed.
- Run the following commands:
```
ansible-galaxy collection install oracle.oci
ansible-galaxy collection install chocolatey.chocolatey
sudo python3 -m pip install pywinrm
```
- ssh acces to all the Linux hosts on which you want to deploy the monitoring solution
- All the hosts on which you want to monitor the processes needs to have instance principal privileges
    - To do that, you need to either create a dynamic group or edit an existing one and add a mathing rule to contain the instances compartment ocid; and create a policy for it.
    - For the dynamic group add the following matching rule:
        - All {instance.compartment.id = 'ocid1.compartment.oc1..aa'}
        - If you have instances in different compartments add them inside the map with a comma between them like this:

          All {instance.compartment.id = 'ocid1.compartment.oc1..aaaaaaaavrz54', instance.compartment.id = 'ocid1.compartment.oc1..aaaabcsfsafffaa'}
    - For the policy, edit an existing policy or create a new one with the following statement:
        - Allow dynamic-group **dynamic_group_name** to manage metrics in compartment **compartment_name**
        - Where **dynamic_group_name** is the name of the dynamic group that has the matching rule from above and **compartment_name** is the name of the compartment on which you will be able to see the metrics    

## Extra requirements for Windows hosts
- winrm needs to be configured on the Windows hosts:
    - Run the following commmand in a powershell,or for new windows hosts add it in the cloud inint:
        - winrm quickconfig -quiet

- The instances needs to have access to the internet to download python:
    - The subnet in which the instance resides needs to have a route to a NAT gateway(for private subnets) or Internet gateway(public subnets)       


- If the password is stored in a vault, the instance running the ansible playbook will need access to it:
    - The instance needs to be in a dynamic group:
        - instance.compartment.id = 'ocid1.compartment.oc1..aaaaaaaavrz'
    - Three(3) policies needs to be set for this dynamic group:
        - Allow dynamic-group **dynamic_group_name** to read vaults in compartment **compartment_name**
        - Allow dynamic-group **dynamic_group_name** to read secret-family in compartment **compartment_name**
        - Allow dynamic-group **dynamic_group_name** to use keys in compartment **compartment_name**
        - Where **dynamic_group_name** is the name of the dynamic group that has the matching rule from above and **compartment_name** is the compartment containing the vault
        


## Steps to deploy it

  - Edit the Linux and Windows **processes_to_monitor.txt** found inside the **files** folder and add the processes you want to monitor
  - Edit the **inventory.ini** file
  - Run the Ansible playbook **ansible-playbook ansible_script.yaml -i inventory.ini -vvv**



## Deployment details

### **File containing the processes to be monitored**



- Because a process can contain too many characters, for this solution to work you have to name each process, so add a meaningful name to each one.

For example, if you have the following processes:
```
/usr/bin/dbus-daemon --system --address=systemd: --nofork --nopidfile --systemd-activation --syslog-only
/sbin/dhclient -d -q -sf /usr/libexec/nm-dhcp-helper
```
The **processes_to_monitor.txt** file should look like this:
```
proc1=/usr/bin/dbus-daemon --system --address=systemd: --nofork --nopidfile --systemd-activation --syslog-only
proc2=/sbin/dhclient -d -q -sf /usr/libexec/nm-dhcp-helper

proc1 and proc2 are names for the processes.
```

### Ansible



- Since Ansible uses ssh to connect to Linux hosts, you need to be able to connect on those hosts via ssh.
- For windows hosts, Ansible uses winrm, so it will need the host password.
- For the Ansible part you will need to only modify the inventory.ini file as following:

* Example
```

[Windows]
130.60.132.2





##################################################################
[Linux]






##################################################################
[Windows:vars] 

use_vault=yes
vault_ocid =ocid1.vault.oc1.eu-frankfurt-1.cbrvu72
win_secret_name=windows_password_secret
run_from_local=yes
ansible_winrm_user=opc
input_windows_password=Password

#DON'T EDIT BELOW VARIABLES
ansible_winrm_password="{% if use_vault == 'yes'%}{{ secret_content.secret_bundle.secret_bundle_content.content | b64decode }}{% else %}{{input_windows_password}}{% endif %}"
ansible_connection=winrm
ansible_winrm_server_cert_validation=ignore
ansible_winrm_transport=basic
ansible_pipelining=false
###################################################################
[Linux:vars]

ansible_user=opc
ansible_ssh_private_key_file=~/.ssh/id_rsa

###################################################################
[all:vars]

region_for_telemetry=eu-frankfurt-1
compartment_id=ocid1.compartment.oc1..aaaaaaaayspf

#metric_namespace accepts only lower case and underscore and must start with a letter
metric_namespace=process_monitoring
metric_name=Process_metric

###################################################################




#DON'T EDIT BELOW VARIABLES

win_processes_file_location=/files/win_processes_to_monitor.txt 
win_processes_file_destination=C:/processes_metrics/
win_custom_metric_script_destination=C:/processes_metrics/
linux_processes_file_location=/files/linux_processes_to_monitor.txt 
processes_file_destination=/home/opc/processes_metrics/
custom_metric_script_destination=/home/opc/processes_metrics/
telemetry_url="https://telemetry-ingestion.{{region_for_telemetry}}.oraclecloud.com"

```
* Variables explained
```
[Windows] - Group for Windows Instances Hosts.
Windows Instance ip.
Windows Instance ip.


##################################################################
[Linux] - Group for Linux Instances Hosts.
Linux Instance ip.
Linux Instance ip.



##################################################################
[Windows:vars]  - Specific Variables for Windows Hosts.

use_vault = If Ansible should get the Windows password from the OCI Vault (yes or no).
vault_ocid = The OCI Vault ocid.
win_secret_name = The name of the secret containing the Windows password.
run_from_local= If you run the Ansible script from your computer put yes. If you run from an Instance put no.
ansible_winrm_user = Windows Login User.
input_windows_password = Put the Windows Instances password here if you're not using the OCI Vault.

#DON'T EDIT BELOW VARIABLES
ansible_winrm_password = If use_vault is set to yes, will use the password from the vault. If not, it will take the value from input_windows_password.
ansible_connection = Type of connection for Windows Hosts.
ansible_winrm_server_cert_validation = If it should validate winrm_server_cert.
ansible_winrm_transport = Type of winrm transport.
ansible_pipelining = Pipelining is set to false.
###################################################################
[Linux:vars] - Specific Variables for Linux Hosts.

ansible_user = Linux Login User.
ansible_ssh_private_key_file = Path to ssh private key.

###################################################################
[all:vars] - Variables that are not specific to any type of Hosts.

region_for_telemetry = The region identifier where to send the metrics.
compartment_id = The Compartment ocid where to send the metrics.

#metric_namespace accepts only lower case and underscore and must start with a letter
metric_namespace = Set a name for the metric namespace.
metric_name = Set a name for the metric.

###################################################################


#DON'T EDIT BELOW VARIABLES

win_processes_file_location = The path to the Windows processes file to monitor
win_processes_file_destination = The path to put the Windows processes file on the Windows Hosts.
win_custom_metric_script_destination = The path to put the metric Python script on the Windows Hosts.
linux_processes_file_location = The path to the Linux processes file to monitor
processes_file_destination = The path to put the Linux processes file on the Linux Hosts.
custom_metric_script_destination = The path to put the metric Python script on the Linux Hosts.
telemetry_url = The Telemetry url where to send the metrics.

```

### Python script

- The python script will look in the file containing the processes that needs to be monitored and it will do the following for each process:
    - check if the process is active
    - get the cpu usage
    - get the memory usage
    - post these 3 metrics every 30 seconds in the metrics explorer in OCI




## Checking the metrics in OCI

- In the OCI Console, search for **Metrics Explorer**, or from the Hamburger Menu > Obervability & Management > Monitoring > Metrics Explorer
- Click on **Edit queries** button if the queries are not shown
- Specify compartment, metric namespace, metric name
- Under Metric dimensions you will have Dimensions name and Dimensions value
    - Dimension name - here you will see the name of the instance 
    - Dimension value - here you will see the process names and metric names
