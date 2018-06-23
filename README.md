[![Build Status](https://travis-ci.org/rainmanh/jenkins_gig.svg)](https://travis-ci.org/rainmanh/jenkins_gig)


GIG Deployment
==============

This is a PoC for Generation a stack of Wordpress using GIG Solutions.


There are 2 different proposed solutions:

 * ansible_vm.py
 * ays_vm.py


 These PoC includes:
  * Testing through Travis


 # ansible_vm.py


The "base image" Selected for this Build is an "Ubuntu 16.04 x64". It hasn't been tested on any other distribution at the present.


Also *NOTE* this a a deployment for an Intranet, so you need the OpenVPN against your Cloud Space open for your deployment.

Requirements
------------

  You need the following packages:
   * python3
   * Ansible
   * sshpass
   * Python Libraries:
    * paramiko
    * jinja2


Instructions
------------

 # ansible_vm.py

  * From your session just execute file *ansible_vm.py* against the GIG and python along with Ansible will do the rest!

  You got The following variable files:

  * python: python_variables.txt at the root directory.

 # ays_run.py

This script has been written to perform an AYS deployment.

This script has to be run in an environment with got all the JS9/AYS9 tools an libraries in it.

At the present it relies on the VM newly created to have a PUBLIC IP for the purposes of the Jenkins installation.

Requirements
------------

You need the following:
 * python3
 * Ansible
 * sshpass
 * Python Libraries:
  * paramiko
  * jinja2
  * All the Libraries required by JS9/AYS9

Also, at the present you need a GIG Development environment in place and to have the G9 container built. (otherwise you can setup your environment in a different way...)
* https://github.com/Jumpscale/developer/blob/master/README.md
* https://github.com/Jumpscale/ays9/


This script will deploy several templates previous to the AYS blueprint run:

* create_vm.yaml


This script will deploy several templates previous to the ansible run:

 * all
 * hosts
 * wp-config.php

  Further Details
  ---------------

  *Wordpress is by default running at port 80*



  *http://_public_ip_*

## Sources and Further reading

* jinja2 http://jinja.pocoo.org
* ansible https://www.ansible.com
* GIG AYS9 https://github.com/Jumpscale/ays9/
* GIG Developer https://github.com/Jumpscale/developer
