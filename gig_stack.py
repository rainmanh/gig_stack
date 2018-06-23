#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
import requests
import time
import os
import sys
import socket
import paramiko
import urllib.request
import pprint

exec(open("python_variables.txt").read())
PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(PATH, 'templates')),
    trim_blocks=False)

BASE_URL = "https://" + BASE_URL + "/restmachine/"
headers = {'Authorization': str('Bearer ' + jwt_token), 'Content-type': 'application/json'}

def render_template(template_filename, context):
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)


def create_hosts_ansible(webserver_private_ip,application_priv_ips,database_priv_ip):
    print ("Preparing Ansible Hosts File...")
    #Remove file if exists.
    hosts_files = "hosts"
    if os.path.isfile(hosts_files):
        os.remove(hosts_files)

    fname = "hosts"
    context = {
    '__WEBSERVER_PUBLIC_IP__': webserver_private_ip,
    '__APPLICATION_PUBLIC_IPS__': application_priv_ips,
    '__DATABASE_PUBLIC_IP__': database_priv_ip,
    'webserver_list_ports': webserver_list_ports,
    'application_list_ports': application_list_ports,
    'database_list_ports': database_list_ports
    }
    #
    with open(fname, 'w') as f:
        hosts_yaml_file = render_template('hosts.j2', context)
        f.write(hosts_yaml_file)
        f.close()

def create_group_vars(application_priv_ips):
    #Remove file if exists.
    group_vars_file = "group_vars/all"
    if os.path.isfile(group_vars_file):
        os.remove(group_vars_file)

    fname = "group_vars/all"
    context = {
    'application_priv_ips': application_priv_ips
    }
    #
    with open(fname, 'w') as f:
        group_vars_yaml_file = render_template('all.j2', context)
        f.write(group_vars_yaml_file)
        f.close()

def create_wordpress_config(application_priv_ips):
    #Remove file if exists.
    wp_files = "roles/wordpress/files/wp-config.php"
    if os.path.isfile(wp_files):
        os.remove(wp_files)
    wp_salt = ""
    #wp_salt = urllib.request.urlopen("https://api.wordpress.org/secret-key/1.1/salt/").read()
    fname = "roles/wordpress/files/wp-config.php"
    context = {
    'wp_db_name': wp_db_name,
    'wp_db_user': wp_db_user,
    'wp_db_password': wp_db_password,
    'database_priv_ip': database_priv_ip,
    'wp_salt': wp_salt
    }
    #
    with open(fname, 'w') as f:
        wp_yaml_file = render_template('wp-config.php.j2', context)
        f.write(wp_yaml_file)
        f.close()


def create_port_forward(vm_cloudspaceId,publicIp,publicPort,vm_id,vm_localPort,protocol):
    try:
        params_port = {'cloudspaceId': vm_cloudspaceId,'publicIp': publicIp,'publicPort': publicPort,'machineId': vm_id,'localPort': vm_localPort,'protocol': protocol }
        port_forward = requests.post(BASE_URL + 'cloudapi/portforwarding/create',params=params_port,headers=headers).json()
    except Exception as e:
        print("Error Provisioning a Port Forwarder!!")
        print(e)
        sys.exit(1)

def create_vm(vm_cloudspaceId, vm_name, vm_sizeId, vm_imageId, vm_disksize):
    try:
        params = {'cloudspaceId': vm_cloudspaceId,'name': vm_name,'sizeId': vm_sizeId,'imageId': vm_imageId,'disksize': vm_disksize }
        vm_id = requests.post(BASE_URL + 'cloudapi/machines/create',params=params,headers=headers).json()
    except Exception as e:
        print("Error Provisioning a Port Forwarder!!")
        print(e)
        sys.exit(1)

    print ("VM_ID=" + str(vm_id))
    return  vm_id

def get_password_ip(vm_id):
    params = { 'machineId': vm_id }
    vm_pwd = requests.post(BASE_URL + 'cloudapi/machines/get',params=params,headers=headers).json()

    for accounts in vm_pwd['accounts']:
        vm_password = accounts['password']

    for item in vm_pwd['interfaces']:
        vm_ip = item['ipAddress']
        #print (vm_ip)

    return vm_password,vm_ip

def ip_wait(vm_id):
    while run['state'] != 'ok':
        password,ip = get_password_ip(vm_id)
        if ip == "Undefined":
            time.sleep(2)
            print ("Waiting for the DHCP Server to lease an IP to the VM...")

def wait_ssh(ip):
    print("Waiting for ssh socket....")
    time.sleep(5)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, 22))
        print("Port 22 reachable")
    except socket.error as e:
        prit("Error on connect: %s" % e)
    s.close()

def ssh_updates(ip,password):
    #password,ip = get_password_ip(vm_id)
    #Preparing the vars/main.yaml file for the Ansible deployment

    print("The VM got Private IP=" + ip)
    print("Installing Python...")

    command = "echo " + password + " | sudo -S apt-get install python -y"

    retry_count = 0
    while retry_count < 5:
        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip, port=22, username=user_name, password=password,timeout=60)
            stdin, stdout, stderr = client.exec_command(command)
            print(stdout.read())
            client.close()
            break
        except Exception as e:
            retry_count = retry_count + 1
            print(e)
            print("Wait 5 Secs....")
            time.sleep(5)
            continue
        return False

def ansible(ip,password,limit):

    print ("Executing Ansible Command...")
    print ('ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook main.yml -i hosts -l %s --user=%s --extra-vars "ansible_ssh_pass=Password ansible_sudo_pass=Password" -vv' % (limit,user_name))
    os.system('ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook main.yml -i hosts -l %s --user=%s --extra-vars "ansible_ssh_pass=%s ansible_sudo_pass=%s" -vv'  % (limit,user_name, password, password))

########################################

if __name__ == "__main__":

    vm_ips = []
    vm_pasword = []
    webserver_list_ports = application_list_ports = database_list_ports = "22"
    #application_priv_ips = []
    ip = ""

    #create_yaml_python(BASE_URL,jwt_token,vm_location,vm_vdc,account_name,vm_name,vm_disksize,vm_osimage,vm_memory)
    for vm_name in vm_names:
        print("Creating=" + vm_name)
        vm_id = create_vm(vm_cloudspaceId, vm_name, vm_sizeId, vm_imageId, vm_disksize)
        password,ip = get_password_ip(vm_id)
        #ip_wait(vm_id)
        while ip == 'Undefined':
            print ("Waiting for the DHCP Server to lease an IP to the VM...")
            password,ip = get_password_ip(vm_id)
            time.sleep(2)

        vm_pasword.append(password)
        vm_ips.append(ip)

        if 'NGINX' in vm_name:
            print("Adding Port Forwarding to"  + vm_name + " .Port " + publicPort)
            create_port_forward(vm_cloudspaceId,publicIp,publicPort,vm_id,vm_localPort,protocol)


    webserver_private_ip = vm_ips[2]
    application_priv_ips = vm_ips[1]
    database_priv_ip = vm_ips[0]

    webserver_password = vm_pasword[2]
    application_password = vm_pasword[1]
    database_password = vm_pasword[0]

    create_hosts_ansible(webserver_private_ip,application_priv_ips,database_priv_ip)
    create_group_vars(application_priv_ips)
    create_wordpress_config(application_priv_ips)

    ssh_updates(database_priv_ip,database_password)
    ssh_updates(application_priv_ips,application_password)
    ssh_updates(webserver_private_ip,webserver_password)

    ansible(database_priv_ip,database_password,'database')
    ansible(application_priv_ips,application_password,'application')
    ansible(webserver_private_ip,webserver_password,'webserver')

    print("WordPress is running at: http://" + publicIp)
