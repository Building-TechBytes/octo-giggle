import sys
import re
import hashlib
import time
import random
from datetime import datetime
from netmiko import ConnectHandler
from netmiko import ssh_exception
from netmiko.ssh_exception import NetmikoTimeoutException
from netmiko.ssh_exception import NetmikoAuthenticationException
from paramiko.ssh_exception import AuthenticationException
from getpass import getpass

space = " - "
response = ""
#log output file name
currentTime = datetime.now()
dt_string = currentTime.strftime("%Y-%m-%d-%H-%M-%S")
logFileName=dt_string+"-NAC-CHECK.txt"

#convert tuples or lists to strings
def convertToString(data):
    str = ' -'.join(data)
    return str

#check code process, compares the baseline code with code that is on the switchport interface. If all of baseline code does not appear in the swich config, missing parts returned.
def non_matching_elements(interface_base_config_list, interface_from_switch_list):
    non_match=[]
    for i in interface_base_config_list:
        if i not in interface_from_switch_list:
            non_match.append(i)
    return non_match

#get current time
def  currentTime():
    time = datetime.now()
    formatedTime = time.strftime("%Y.%m.%d_%H:%M:%S")
    return formatedTime

#open file that contains all the switch IPs
try:
    with open("IP_Address_List_Switches") as doc:
        ip_list = doc.read().splitlines()
except FileNotFoundError:
    print("Switch List Not Found!")
    sys.exit()

#open file that contains the switch interface baseline code. Write baseline & sha256 hash to log file
try:
    with open("Interface_NAC_Baseline") as doc:
        baseline = doc.read()
        baseline_hash = hashlib.sha256(baseline.encode())
        baseline_log = ("Baseline Configuration - " + currentTime() + "\n" + baseline + "\nsha256 hash " + str(baseline_hash.hexdigest()) + "\n" + ("_"*76))
        f = open(logFileName, "w")
        f.write(baseline_log)
        f.close()
        interface_base_config_list = baseline.split("\n") #prepare baseline config to be used in "def non_matching_elements"
except FileNotFoundError:
    print("Baseline code not found!")
    sys.exit()

#collect switch login information (tacacs account should be used)
# user = input("Network Device Login Username: " )
# secret = getpass()
user = "matt" #temp testing
secret ="ciscos" #temp testing



#for each ip from the file "IP_Address_List_Switches" perform the following actions
for ip in ip_list:
    switch = {
        'device_type': 'cisco_ios',
        'host':   ip,
        'username': user,
        'password': secret,
    }
    try:
        net_connect = ConnectHandler(**switch) #connect to the switch
        hostname = net_connect.send_command('show run | include hostname') #run command on switch
        print(hostname.upper(), space, ip + space + currentTime())
        f = open(logFileName, "a")
        hostinfo = "\n\n\n" + hostname.upper() + space + ip + space + currentTime() + "\n"
        hostinfo_len=len(hostinfo)
        underlineHostData=("_"*hostinfo_len) + "\n"
        f.write(hostinfo + underlineHostData)
        access_Vlan_Ports = net_connect.send_command('show vlan brief')#run command on switch
        # access_Vlan_Ports_list=re.findall('([T][w|e][1-8]\/[0]\/\d*)' , access_Vlan_Ports) #regex results of the command and put into list # Cisco 9300
        access_Vlan_Ports_list=re.findall('([E][t][0-8]\/\d*)' , access_Vlan_Ports) #Virtual switch regex pattern
        print(access_Vlan_Ports_list)
        for interface in access_Vlan_Ports_list:#each interface found from the regex, see configs
            interface_from_switch = net_connect.send_command("show run int " + interface)
            interface_from_switch_list = interface_from_switch.split("\n")
            non_match = non_matching_elements(interface_base_config_list , interface_from_switch_list)
            if non_match:
                status = "Failed--> Missing:"
                interface_config_status = currentTime() + space + interface + space + "Status: " + status + convertToString(non_match) + "\n" #timestamp
                # interface_config_status = interface + space + "Status" + space + status + convertToString(non_match) + "\n" no time stamp
            else:
                status = "Passed"
                interface_config_status = currentTime() + space + interface + space + "Status: " + status + "\n" #timestamp
                # interface_config_status = interface + space + "Status" + space + status + "\n" #no time stamp
            print(interface, non_match)
            f.write(interface_config_status)
        f.close()
        net_connect.disconnect()
    except (AuthenticationException, NetmikoAuthenticationException):
        print('Login failed to device' , space , ip)
        sys.exit()
    except (NetmikoTimeoutException):
        print('\n \nTCP connection to device failed for host ' + ip)
        # print('\n \nTCP connection to device failed for host ' + ip + '\n \n Common causes of this problem are:\n 1. Incorrect hostname or IP address.\n 2. Wrong TCP port.\n 3. Intermediate firewall blocking access.\n')
        continue
