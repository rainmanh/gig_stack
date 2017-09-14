#!/usr/bin/env python3

from aysclient.client import Client
from js9 import j
from jinja2 import Environment, FileSystemLoader
import requests
import time
import os
import sys
import paramiko
import pprint

exec(open("python_variables.txt").read())
PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(PATH, 'templates')),
    trim_blocks=False)

def render_template(template_filename, context):
    return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)

def create_yaml_python(BASE_URL,jwt_token,vm_location,vm_vdc,account_name,vm_name,vm_port,vm_disksize,vm_osimage,vm_memory):

    fname = "create_vm_" +  vm_name + ".yaml"
    var_nginx = ""
    if "NGINX" in vm_name:
        var_nginx = 'yes'

    context = {
    '__BASE_URL__': BASE_URL,
    '__JWT_TOKEN__': jwt_token,
    '__VM_LOCATION__': vm_location,
    '__VM_VDC__': vm_vdc,
    '__ACCOUNT_NAME__': account_name,
    '__VM_NAME__': vm_name,
    '__VM_PORT__': vm_port,
    '__BOOT_DISK_SIZE__': vm_disksize,
    '__VM_MEMORY__': vm_memory,
    '__OS_IMAGE__': vm_osimage,
    'var_nginx': var_nginx
    }
    #
    with open(fname, 'w') as f:
        yaml_file = render_template('create_vm.yaml.j2', context)
        f.write(yaml_file)
        f.close()

def create_hosts_ansible(database_public_ip,database_list_ports,application_public_ips,application_list_ports,webserver_public_ip,webserver_list_ports):
    print ("Preparing Ansible Hosts File...")
    #Remove file if exists.
    hosts_files = "hosts"
    if os.path.isfile(hosts_files):
        os.remove(hosts_files)

    fname = "hosts"
    context = {
    '__WEBSERVER_PUBLIC_IP__': webserver_public_ip,
    'webserver_list_ports': webserver_list_ports,
    '__APPLICATION_PUBLIC_IPS__': application_public_ips,
    'application_list_ports': application_list_ports,
    '__DATABASE_PUBLIC_IP__': database_public_ip,
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

def create_wordpress_config(wp_db_name,wp_db_user,wp_db_password,database_priv_ip):
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

def create_vm(file_name,vm_name,repo_name):
    client = Client(ays_client)
    blueprint_file = open(file_name,'r')
    blueprint = blueprint_file.read()
    cl = j.clients.atyourservice.get().api.ays

    data = {'name': file_name, 'content':blueprint}
    #print(str(data))
    try:
      bp = client.ays.createBlueprint(data, repo_name)
      bp = client.ays.executeBlueprint('',file_name, repo_name)

      run = cl.createRun('', repo_name)
      run = cl.executeRun(repository=repo_name, data=None, runid=run.json()['key']).json()
      run = cl.getRun(repository=repo_name, runid=run['key']).json()
      while run['state'] != 'ok':
          time.sleep(2)
          run = cl.getRun(repository=repo_name, runid=run['key']).json()
          rv = cl.getServiceByName(role="node", name=vm_name, repository=repo_name).json()

      vm_id = rv['data']['machineId']
      vm_passwd = str(rv['data']['sshPassword'])
      vm_pub_ip = str(rv['data']['ipPublic'])
      vm_priv_ip = str(rv['data']['ipPrivate'])
      #vm_port = str(rv['data']['sshPort'])
      vm_login = str(rv['data']['sshLogin'])

      return {'vm_id':vm_id,'vm_passwd':vm_passwd,'vm_pub_ip':vm_pub_ip,'vm_priv_ip':vm_priv_ip,'vm_login':vm_login}

    except Exception as e:
        print("Error Provisioning!!")
        print(e)
        sys.exit(1)

def ssh_updates(vm_passwd,vm_pub_ip,vm_port,vm_login):

    print ("Installing Python...")
    #Ensure sshd is up and running and Can access the internet
    #time.sleep(20)
    command = "echo " + vm_passwd + " | sudo -S apt-get install python -y;echo " + vm_passwd + " | sudo -S systemctl stop apt-daily.service; echo " + vm_passwd + " | sudo -S systemctl stop apt-daily.timer"
    #print("Commands:" + vm_passwd + " " + vm_pub_ip + " " + str(vm_port) + " " + vm_login)
    retry_count = 0
    while retry_count < 10:
        try:
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(vm_pub_ip, port=vm_port, username=vm_login, password=vm_passwd,timeout=120)
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

def ansible(vm_passwd,vm_pub_ip,vm_login,limit):

    print("Executing Ansible Command...")
    print('ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook main.yml -i hosts -l %s --user=%s --extra-vars "ansible_ssh_pass=password ansible_sudo_pass=password" -vv' % (limit, vm_login))
    os.system('ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook main.yml -i hosts -l %s --user=%s --extra-vars "ansible_ssh_pass=%s ansible_sudo_pass=%s" -vv'  % (limit, vm_login, vm_passwd, vm_passwd))

def main():

    vm_public_ips = []
    vm_private_ips = []
    vm_password = []
    list_ports = []
    vm_login = []
    vm_port = 4000

    for vm_name in vm_names:
        print("Creating Blueprint for " + vm_name)
        create_yaml_python(BASE_URL,jwt_token,vm_location,vm_vdc,account_name,vm_name,vm_port,vm_disksize,vm_osimage,vm_memory)

        print("Creating=" + vm_name)
        file_name = "create_vm_" +  vm_name + ".yaml"
        vm_data = create_vm(file_name,vm_name,repo_name)
        #vm_data = create_vm(vm_cloudspaceId, vm_name, vm_sizeId, vm_imageId, vm_disksize)

        vm_password.append(vm_data['vm_passwd'])
        vm_public_ips.append(vm_data['vm_pub_ip'])
        vm_private_ips.append(vm_data['vm_priv_ip'])
        vm_login.append(vm_data['vm_login'])
        list_ports.append(vm_port)

        ssh_updates(vm_data['vm_passwd'],vm_data['vm_pub_ip'],int(vm_port),vm_data['vm_login'])
        vm_port = vm_port + 1

    database_public_ip = vm_public_ips[0]
    application_public_ips = vm_public_ips[1]
    webserver_public_ip = vm_public_ips[2]

    database_password = vm_password[0]
    application_password = vm_password[1]
    webserver_password = vm_password[2]

    database_list_ports = list_ports[0]
    application_list_ports = list_ports[1]
    webserver_list_ports = list_ports[2]

    database_login = vm_login[0]
    application_login = vm_login[1]
    webserver_login = vm_login[2]

    database_priv_ip = vm_private_ips[0]
    application_priv_ips = vm_private_ips[1]


    print("Creating Ansible host file...")
    create_hosts_ansible(database_public_ip,database_list_ports,application_public_ips,application_list_ports,webserver_public_ip,webserver_list_ports)
    print("Creating Ansible's content of group_vars...")
    create_group_vars(application_priv_ips)
    print("Creating Config file for Wordpress...")
    create_wordpress_config(wp_db_name,wp_db_user,wp_db_password,database_priv_ip)

    ansible(database_password,database_public_ip,database_login,'database')
    ansible(application_password,application_public_ips,application_login,'application')
    ansible(webserver_password,webserver_public_ip,webserver_login,'webserver')

    print("WordPress is at: http://" + vm_public_ips[2])

########################################

if __name__ == "__main__":
    main()
