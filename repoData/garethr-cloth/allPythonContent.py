__FILENAME__ = tasks
#! /usr/bin/env python

from collections import defaultdict

from fabric.api import run, env, sudo, task, runs_once, roles

from cloth.utils import instances, use


env.nodes = []
env.roledefs = defaultdict(list)


@task
def all():
    "All nodes"
    for node in instances():
        use(node)

@task
def preview():
    "Preview nodes"
    for node in instances('^preview-'):
        use(node)

@task
def production():
    "Production nodes"
    for node in instances('^production-'):
        use(node)

@task
def nodes(exp):
    "Select nodes based on a regular expression"
    for node in instances(exp):
        use(node)

@task
@runs_once
def list():
    "List EC2 name and public and private ip address"
    for node in env.nodes:
        print "%s (%s, %s)" % (node.tags["Name"], node.ip_address,
            node.private_ip_address)

@task
def uptime():
    "Show uptime and load"
    run('uptime')

@task
def free():
    "Show memory stats"
    run('free')

@task
def updates():
    "Show package counts needing updates"
    run("cat /var/lib/update-notifier/updates-available")

@task
def upgrade():
    "Upgrade packages with apt-get"
    sudo("apt-get update; apt-get upgrade -y")


########NEW FILE########
__FILENAME__ = utils
#! /usr/bin/env python

import re
import os

import boto.ec2
from fabric.api import env


REGION = os.environ.get("AWS_EC2_REGION")

def ec2_instances():
    "Use the EC2 API to get a list of all machines"
    region = boto.ec2.get_region(REGION)
    reservations = region.connect().get_all_instances()
    instances = []
    for reservation in reservations:
        instances += reservation.instances
    return instances

def ip(node):
    if node.ip_address:
        return node.ip_address
    else:
        return node.private_ip_address

def instances(exp=".*"):
    "Filter list of machines matching an expression"
    expression = re.compile(exp)
    instances = []
    for node in ec2_instances():
        if node.tags and ip(node):
            try:
                if expression.match(node.tags.get("Name")):
                    instances.append(node)
            except TypeError:
                pass
    return instances

def use(node):
    "Set the fabric environment for the specifed node"
    try:
        role = node.tags.get("Name").split('-')[1]
        env.roledefs[role] += [ip(node)]
    except IndexError:
        pass
    env.nodes += [node]
    env.hosts += [ip(node)]

########NEW FILE########
