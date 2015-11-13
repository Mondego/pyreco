__FILENAME__ = apache
class Apache(object):
  '''
    A python class to manage an apache proxypass load balancer
    Each app added to the load balancer will be given its own
    file.  
  '''
  def __init__(self, manager, logger, apache_server):
    self.manager = manager
    self.logger = logger
    self.apache_server = apache_server

  # Adds an app to the load balancer
  def add_vhost(self, app):
    pass

  # Adds an app to the load balancer
  def remove_vhost(self, app):
    pass

########NEW FILE########
__FILENAME__ = app
import unittest

class App(object):
  '''
    An app or application has a hostname,
    cpu_shares, ram, port_list, volumes and a host_server
    it runs on.
  '''
  def __init__(self, container_id, username, hostname, 
    cpu_shares, ram, host_server, docker_image, ssh_port, volume_list=None):

    self.container_id = container_id
    self.username = username
    self.hostname = hostname
    self.cpu_shares = int(cpu_shares)
    self.ram = int(ram)
    self.port_list = []
    self.host_server = host_server
    self.docker_image = docker_image
    self.volume_list = volume_list
    self.ssh_port = int(ssh_port)

  def change_container_id(self, new_container_id):
    self.container_id = new_container_id

  def change_host_server(self, new_host_server):
    self.host_server = new_host_server
  
  def change_ram_limit(self, new_ram_limit):
    self.ram = int(new_ram_limit)

  def change_cpu_shares(self, new_cpu_shares):
    self.cpu_shares = int(new_cpu_shares)

  def change_docker_image(self, new_docker_image):
    self.docker_image = new_docker_image

  def add_port_mapping(self, host_port, container_port):
    port_map = "{host_port}:{container_port}".format(host_port=host_port,
      container_port=container_port)
    self.port_list.append(port_map)

  def get_json(self):
    return  {'container_id': self.container_id, 'username': self.username,
      'hostname': self.hostname, 'cpu_shares': self.cpu_shares,
      'ram': self.ram, 'port_list': self.port_list, 
      'host_server': self.host_server, 'volumes': self.volume_list,
      'ssh_port': self.ssh_port}

class TestApp(unittest.TestCase):
  def test_json_output(self):
    expected_results = {'container_id': 'test',
      'username': 'joe_user', 'hostname': 'test001', 'cpu_shares': 100,
      'ram': 100, 'port_list': [], 'host_server': 'test_server', 
      'volumes': ['/mnt/vol/test_vol'], 'ssh_port': 22}
    a = App('test', 'joe_user', 'test001', 100, 100, 'test_server', 22, 
      ['/mnt/vol/test_vol'])
    self.assertEqual(expected_results, a.get_json())

########NEW FILE########
__FILENAME__ = appbackup
'''
  Automates the backing up of customer containers
'''
import salt.client

from datetime import datetime
from etcd import Etcd
import os
import os.path

class AppBackup(object):
  def __init__(self, manager, logger):
    self.etcd = Etcd(logger)
    self.logger = logger
    self.manager = manager
    self.salt_client = salt.client.LocalClient()

  # Backup this users formation to /mnt/ceph/docker_customer_backups
  def backup_formation(self, user, formation, backup_directory):
    self.logger.info('Saving the formation {formation}'.format(
      formation=formation))
    formation = self.manager.load_formation_from_etcd(user, formation)
    for app in formation.application_list:
      self.logger.info('Running commit on {hostname}'.format(
        hostname=app.hostname))
      # Try to commmit the container and wait 10 mins for this to return
      results = self.salt_client.cmd(app.host_server, 'cmd.run', 
        ['docker commit {container_id}'.format(container_id=app.container_id)],
        expr_form='list', timeout=1200)
      if results:
        self.logger.debug("Salt return: {commit}".format(
          commit=results[app.host_server]))

        if "Error: No such container" in results[app.host_server]:
          self.logger.error('Could not find container')
        else:
          if not os.path.exists(backup_directory):
            #Looks like the backup directory doesn't exist.  Lets create it
            self.logger.info('Creating the missing backup directory')
            os.makedirs(backup_directory)

          current_date = datetime.now()
          commit_id = results[app.host_server]
          self.logger.info('Running save on {hostname}'.format(
            hostname=app.hostname))
          results = self.salt_client.cmd(app.host_server, 'cmd.run', 
            ['docker save {image_id} > {backup_directory}/{hostname}.{year}-{month}-{day}.tar'.format(
                image_id=commit_id[0:12], 
                year=current_date.year,
                month=current_date.month,
                day=current_date.day,
                backup_directory=backup_directory,
                hostname=app.hostname)], 
            expr_form='list', timeout=1200)
          if results:
            self.logger.debug("Salt return: {save}".format(
              save=results[app.host_server]))
          self.logger.info('Cleaning up the commit image')
          self.salt_client.cmd(app.host_server, 'cmd.run',
            ['docker rmi {image_id}'.format(image_id=commit_id[0:12])], 
            expr_form='list')
          self.logger.info('Done saving app')

########NEW FILE########
__FILENAME__ = autodock
import argparse
import ConfigParser
import logging
import os.path
import sys

from appbackup import AppBackup
from edit import FormationEditor
from manager import Manager
from verify import VerifyFormations

def parse_config(cfg_file):
  # If a config file is present use it to populate various default
  # values
  config_options = {}
  config = ConfigParser.ConfigParser()
  if os.path.exists(cfg_file):
    config.read(cfg_file)
    # playing it safe with the parsing.  Missing sections will be ignored

    try:
      backup_options = config.items('backup')
      config_options['backup'] = backup_options
    except ConfigParser.NoSectionError:
      config_options['backup'] = None

    try:
      manager_options = config.items('manager')
      config_options['manager'] = manager_options
    except ConfigParser.NoSectionError:
      config_options['manager'] = None

    try:
      verify_options = config.items('verify')
      config_options['verify'] = verify_options
    except ConfigParser.NoSectionError:
      config_options['verify'] = None

    try:
      etcd_options = config.items('etcd')
      config_options['etcd'] = etcd_options
    except ConfigParser.NoSectionError:
      config_options['etcd'] = None

    return config_options

def parse_cli_args():
  parser = argparse.ArgumentParser(prog='autodock', 
    description='Autodock. The docker container automation tool.')
  subparsers = parser.add_subparsers(dest='mode', help='sub-command help')

  # create a parser for the "list" command
  list_parser = subparsers.add_parser('list',
    help='List the formations a user owns.')
  list_parser.add_argument('-u', '--username', required=True, 
    help='The username to list formations for')

  # create a parser for the "edit" command
  edit_parser = subparsers.add_parser('edit',
    help='Edit a formation a user owns.')
  edit_parser.add_argument('-u', '--username', required=True,
    help='The username who owns the formation')

  # create a parser for the "verify" command
  subparsers.add_parser('verify',
    help='Verify the formations in the cluster are working properly.')

  # create a parser for the "backup" command
  backup_parser = subparsers.add_parser('backup',
    help='Backup the formation specified by username and formation name.')
  backup_parser.add_argument('-u', '--username', required=True, 
    help='The username who owns the formation')
  backup_parser.add_argument('-f', '--formation', help='A Formation is a set of'
      ' infrastructure used to host Applications. Each formation includes Nodes'
      'that provide different services to the formation.', required=True)
  backup_parser.add_argument('-d', '--directory', required=True, 
    help='The directory to back up docker containers into')

  # create a parser for the "delete" command
  delete_parser = subparsers.add_parser('delete',
    help='Delete the formation specified by username and formation name.')
  delete_parser.add_argument('-u', '--username', required=True, 
    help='The username who owns the formation')
  delete_parser.add_argument('-f', '--formation', help='A Formation is a set of'
      ' infrastructure used to host Applications. Each formation includes Nodes'
      'that provide different services to the formation.', required=True)

  # create a parser and args for the "create" command
  create_parser = subparsers.add_parser('create', help='Create a new formation')
  create_parser.add_argument('-u', '--username', required=True, 
    help='The username for the formation')

  create_parser.add_argument('-f', '--formation', help='A Formation is a set of'
      ' infrastructure used to host Applications. Each formation includes Nodes'
      'that provide different services to the formation.', required=True)

  create_parser.add_argument('-n', '--number', type=int, 
    help='The number of containers to build, ex: 1. Default=1', default=1)

  create_parser.add_argument('-i', '--image', default='s2disk/baseimage:0.9.8',
    help='The docker image to use, ex: ubuntu-base. Note: This image to use '
    'needs to be identical across your cluster.')

  create_parser.add_argument('-c', '--cpu_shares', type=int, 
    help='A percentage of the cpu that the container is allowed '
      'to use. CPU shares (relative weight) is a number from 1-1024.', 
      default=100)

  create_parser.add_argument('-r', '--ram', type=int, 
    help='Memory limit in megabytes. Default=100MB', default=100)

  create_parser.add_argument('-s', '--hostname_scheme', 
    help='A base hostname scheme to use for the containers. Ex: dlweb '
    'would produce containers with hostnames of dlweb001, dlweb002, etc.', 
    required=True)

  create_parser.add_argument('-p', '--port', action='append', dest='port_list',
    help='Add ports to map to the container. host-port:container-port.  If the'
      ': is missing then host-port and container port are assumed to be '
      'identical', default=[])

  create_parser.add_argument('-z', '--host_server', dest='host_server',
    help='Force the application to be put on a particular host server',
    default=None)

  create_parser.add_argument('-v', '--volume', action='append', 
    dest='volume_list', default=[], help='Create a bind mount. '
      'host-dir:container-dir:rw|ro. If "container-dir" is missing, '
      'then docker creates a new volume.')

  return parser.parse_args()

def main():
  logger = logging.getLogger()
  stream = logging.StreamHandler(sys.stdout)
  stream.setLevel(logging.INFO)
  formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - '
    '%(message)s')
  stream.setFormatter(formatter)
  logger.addHandler(stream)

  args = parse_cli_args()

  #if os.path.exists('autodock.config'):
  #  config_dict = parse_config('autodock.config')
    
  m = Manager(logger)
  if args.mode == 'list':
    logger.info('Listing the formations')
    m.list_formations(args.username)
    return 0
  elif args.mode == 'edit':
    logger.info('Editing the formation')
    e = FormationEditor(m, logger)
    e.edit_formation('args')
    return 0
  elif args.mode == 'verify':
    logger.info('Verifying the formation') 
    v = VerifyFormations(m, logger)
    v.start_verifying()
    return 0
  elif args.mode == 'backup':
    logger.info('Backing up a formation')
    b = AppBackup(m, logger)
    b.backup_formation(args.username, args.formation, args.directory)
    return 0
  elif args.mode == 'delete':
    logger.info('Deleting a formation')
    m.delete_formation(args.username, args.formation)
  else:
    logger.info('Creating a new formation')
    m.create_containers(args.username,
      args.number, args.formation, args.cpu_shares, args.ram,
      args.port_list, args.hostname_scheme, args.volume_list, 
      args.image, args.host_server)
    return 0

if __name__ == "__main__":
  sys.exit(main())

########NEW FILE########
__FILENAME__ = circularlist
import unittest

class CircularList(list):
    '''
    A list that wraps around instead of throwing an index error.
    
    Works like a regular list:
    >>> cl = CircularList([1,2,3])
    >>> cl
    [1, 2, 3]
    
    >>> cl[0]
    1
    
    >>> cl[-1]
    3
    
    >>> cl[2]
    3
    
    Except wraps around:
    >>> cl[3]
    1
    
    >>> cl[-4]
    3
    
    Slices work
    >>> cl[0:2]
    [1, 2]
    
    but only in range.
    '''
    def __getitem__(self, key):
      # try normal list behavior
      try:
        return super(CircularList, self).__getitem__(key)
      except IndexError:
        pass
      # key can be either integer or slice object,
      # only implementing int now.
      try:
        index = int(key)
        index = index % self.__len__()
        return super(CircularList, self).__getitem__(index)
      except ValueError:
        raise TypeError

class TestCircularList(unittest.TestCase):
  def test_cicular_list_wrap_forward(self):
    cl = CircularList([1,2,3])
    #make sure it wraps properly
    self.assertEqual(cl[3], 1)

  def test_cicular_list_wrap_backward(self):
    cl = CircularList([1,2,3])
    #make sure it wraps properly
    self.assertEqual(cl[-1], 3)

########NEW FILE########
__FILENAME__ = edit
'''
  This class will edit a formation currently
  stored in etcd. 
'''
from etcd import Etcd
class FormationEditor(object):
  def __init__(self, manager, logger):
    self.logger = logger
    self.manager = manager
    self.etcd = Etcd(logger)


########NEW FILE########
__FILENAME__ = etcd
import json
import logging
import pycurl
import re
import requests
import socket
import sys
import unittest

from StringIO import StringIO

class EtcdError(BaseException):
  #Generic etcd error
  pass

class Etcd(object):
  def __init__(self, logger, server=None):
    if server:
      self.server = server
    else:
      self.server = socket.gethostname()
    self.url = 'http://%(hostname)s:4001/v2/keys' % {
      'hostname': self.server}
    self.logger = logger

  def set_key(self, key, value):
    url = '%(base)s/%(key)s' % {
      'base': self.url,
      'key': key
    }
    data = 'value=%s' % value

    self.logger.debug("Saving data: %(data)s to %(url)s" %{
      'data': data,
      'url': url
    })
    storage = StringIO()

    curl = pycurl.Curl()
    curl.setopt(curl.URL, url)
    curl.setopt(curl.POSTFIELDS, data)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(curl.WRITEFUNCTION, storage.write)
    curl.setopt(pycurl.CUSTOMREQUEST, "PUT")
    curl.perform()
    response = curl.getinfo(pycurl.HTTP_CODE)
    curl.close()

    if response == requests.codes.ok:
      return True
    elif response == requests.codes.created:
      return True
    else:
      self.logger.error("ETCD returned %(status)s %(text)s" % {
        'status': response,
        'text': storage.getvalue()})
      return None

  def get_key(self, key):
    url = '%(base)s/%(key)s' % {
      'base': self.url,
      'key': key
    }
    self.logger.debug('Getting url: ' + url)
    response = requests.get(url)
    self.logger.debug('Response: ' + response.text)

    res = json.loads(response.text)
    if isinstance(res, list):
      raise ValueError('Key "%s" is a directory, expecting leaf (use \
list_directory() to get directory listing).' % key)      

    #Check to see if Etcd returned an error
    if 'errorCode' in res:
      raise EtcdError(res['errorCode'], res['message']) 

    try:
      return str(res['node']['value'])
    except KeyError:
      #Fallback on v1 functionality
      return str(res['value'])

  def delete_key(self, key):
    url = '%(base)s/%(key)s' % {
      'base': self.url,
      'key': key
    }

    response = requests.delete(url)
    if response.status_code == requests.codes.ok:
      return response.text
    else:
      response.raise_for_status()
      return None

  def list_directory(self, path):
    url = '%(base)s/%(path)s' % {
      'base': self.url,
      'path': path
    }
    response = requests.get(url)
    if response.status_code == requests.codes.ok:
      directory_list = []
      json_txt = json.loads(response.text)
      try:
        for entry in json_txt['node']['nodes']: 
          directory_list.append(str(entry['key']))
        return directory_list
      except KeyError:
        self.logger.error("Key ['node']['nodes'] not found in %(data)s" %{
          'data': json_txt
          })
    else:
      response.raise_for_status()
      return None

  def get_machines(self):
    url = '%(base)s/_etcd/machines' % {
      'base': self.url}
    res = json.loads(requests.get(url).text)

    #Check to see if Etcd returned an error
    if 'errorCode' in res:
      raise EtcdError(res['errorCode'], res['message']) 

    server_list = []
    for entry in res:
      server_list.append(str(entry['value']))

    return server_list

class TestEtcd(unittest.TestCase):
  def setUp(self):
    logger = logging.getLogger()
    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    self.etcd = Etcd(logger)

  def test_a_setkey(self):
    ret = self.etcd.set_key('message', 'Hello World')
    self.assertTrue(ret)

  def test_b_getkey(self):
    self.etcd.set_key('message', 'Hello World')
    text = self.etcd.get_key('message')
    self.assertEqual(text, 'Hello World')

  def test_c_deletekey(self):
    #Set the key first before deleting it
    self.etcd.set_key('message', 'Hello World')

    text = self.etcd.delete_key('message')
    regex = re.compile(r'{"action":"delete","node":{"key":"/message",'
      '"modifiedIndex":\d+,"createdIndex":\d+},"prevNode":{"key":"/message"'
      ',"value":"Hello World","modifiedIndex":\d+,"createdIndex":\d+}}')
    self.assertRegexpMatches(text, regex)

  def test_d_directorylist(self):
    #List a directory in Etcd
    dir_list = self.etcd.list_directory('formations/cholcomb')
    self.assertIsInstance(dir_list, list)

########NEW FILE########
__FILENAME__ = formation
import json
import unittest

from app import App

class Formation(object):
  '''
    A formation represents a group of application servers that are 
    working together to serve a common goal
    [ { "container_id": "61a6cb898d23",
        "username": "cholcomb",
        "hostname": "owncloud01", 
        "cpu-shares": 102, 
        "ram": 100, 
        "ports": [{"host_port":8080,"container_port":8080}], 
        "host-server": "dldocker01", 
        "mounts": [...]}, 
      {...}]
  '''

  def __init__(self, username, name, url_to_serve=None):
    self.application_list = []
    self.name = name
    self.username = username
    # The url that should be added to the load balancer for the apps to serve up
    self.url_to_serve = url_to_serve

  def add_app(self,
    container_id,
    hostname, 
    cpu_shares, 
    ram, 
    port_list,
    ssh_host_port, 
    ssh_container_port,
    host_server, 
    docker_image,
    volumes=None):
    '''
      NOTE - No support for volumes yet.  
      STRING          container_id #The container this app runs in
      STRING          hostname
      INTEGER         cpu_shares
      INTEGER         ram
      List of Ints    port_list
      INTEGER         host_port
      INTEGER         container_port
      STRING          host_server
      #LIST of        [host-dir]:[container-dir]:[rw|ro]
    '''
    app = App(container_id, self.username, hostname, cpu_shares, ram, 
      host_server, docker_image, ssh_host_port, volumes)

    #For each port in the port_list add it to the app
    for port in port_list:
      #Check to see if the host port is free first?
      #Throw an error if it is or just increment it?
      if ':' in port:
        port_list = port.split(':')
        app.add_port_mapping(port_list[0], port_list[1])
      else:
        app.add_port_mapping(port, port)

    #Add the default SSH port mapping
    app.add_port_mapping(ssh_host_port, ssh_container_port)

    self.application_list.append(app)

  def __str__(self):
    json_list = [x.get_json() for x in self.application_list]
    return json.dumps(json.dumps(json_list))

class TestFormation(unittest.TestCase):
  def test_addApp(self):
    self.assertEquals(1, 0)

########NEW FILE########
__FILENAME__ = load
class Load(object):
  '''
    An object representing the one, five and fifteen
    load on a host
  '''
  def __init__(self, hostname, one, five, fifteen):
    self.hostname = hostname
    self.one_min_load = float(one)
    self.five_min_load = float(five)
    self.fifteen_min_load = float(fifteen)

  def __str__(self):
    return  "host={host}, one={one}, five={five}, fifteen={fifteen}".format(
      host=self.hostname, one=self.one_min_load,
      five=self.five_min_load, fifteen=self.fifteen_min_load)

########NEW FILE########
__FILENAME__ = manager
import json
import logging
import paramiko
from paramiko import SSHException
from pyparsing import Combine, Literal, OneOrMore, nums, srange, Word
import salt.client
import subprocess
from subprocess import PIPE
import sys
import unittest

from circularlist import CircularList
from etcd import Etcd
from formation import Formation
from load import Load

class ManagerError(BaseException):
  # Generic manager error
  pass

class Manager(object):
  '''
    A manager to orchestrate the creation and 
    deletion of container clusters
  '''
  def __init__(self, logger):
    self.salt_client = salt.client.LocalClient()
    self.etcd = Etcd(logger)
    self.logger = logger
    # Parse out the username and formation name 
    # from the ETCD directory string
    self.formation_parser = Literal('/formations/') + \
      Word(srange("[0-9a-zA-Z_-]")).setResultsName('username') + Literal('/') + \
      Word(srange("[0-9a-zA-Z_-]")).setResultsName('formation_name')

  def fqdn_to_shortname(self, fqdn):
    if '.' in fqdn:
      return fqdn.split('.')[0]
    else:
      return fqdn

  def check_salt_key_used(self, hostname):
    self.logger.info("Checking if the key for {host} is already used".format(
      host=hostname))
    s = subprocess.Popen('salt-key', shell=True, stdout=PIPE)
    salt_list = s.communicate()[0]

    if hostname in salt_list:
      return True
    else:
      return False

  def check_port_used(self, host, port):
    self.logger.info("Checking if {port} on {host} is open with salt-client".format(
      host=host, port=port))
    results = self.salt_client.cmd(host, 'cmd.run', 
      ['netstat -an | grep %s | grep tcp | grep -i listen' % port], 
      expr_form='list')
    self.logger.debug("Salt return: {lsof}".format(lsof=results[host]))

    if results[host] is not '':
      return True
    else:
      return False

  # TODO
  def check_for_existing_formation(self, formation_name):
    # If the user passed in an existing formation name lets append to it
    pass

  def get_docker_cluster(self):
    # Return a list of docker hosts
    cluster = self.etcd.get_key('docker_cluster')
    if cluster is not None:
      return cluster.split(',')
    else:
      return None

  def get_load_balancer_cluster(self):
    # Return a list of nginx hosts
    cluster = self.etcd.get_key('nginx_cluster')
    if cluster is not None:
      return cluster.split(',')
    else:
      return None

  def order_cluster_by_load(self, cluster_list):
    # Sample salt output
    # {'dlceph01.drwg.local': '0.27 0.16 0.15 1/1200 26234'}

    # define grammar
    point = Literal('.')
    number = Word(nums) 
    floatnumber = Combine( number + point + number)
    float_list = OneOrMore(floatnumber)

    results = self.salt_client.cmd(','.join(cluster_list), 'cmd.run', ['cat /proc/loadavg'], expr_form='list')
    load_list = []
    self.logger.debug("Salt load return: {load}".format(load=results))

    for host in results:
      host_load = results[host]
      match = float_list.parseString(host_load)
      if match:
        one_min = match[0]
        five_min = match[1]
        fifteen_min = match[2]
        self.logger.debug("Adding Load({host}, {one_min}, {five_min}, {fifteen_min}".format(
          host=host, one_min=one_min, five_min=five_min, fifteen_min=fifteen_min))
        load_list.append(Load(host, one_min, five_min, fifteen_min))
      else:
        self.logger.error("Could not parse host load output")

    # Sort the list by fifteen min load
    load_list = sorted(load_list, key=lambda x: x.fifteen_min_load)
    for load in load_list:
      self.logger.debug("Sorted load list: " + str(load))

    return load_list

  # Retun a list of formations the user owns
  def list_formations(self, username):
    formation_list = []
    formations = self.etcd.list_directory('formations/'+username)
    for formation in formations:
      parse_results = self.formation_parser.parseString(formation)
      if parse_results:
        formation_name = parse_results['formation_name']
        formation_list.append(formation_name)
      else:
        self.logger.error("Could not parse the ETCD string")
    self.logger.info('Formation list {formations} for user {user}'.format(
      formations=formation_list, user=username))
    return formation_list

  # Load the formation and return a Formation object
  def load_formation_from_etcd(self, username, formation_name):
    f = Formation(username,formation_name) 
    app_list = json.loads(json.loads(
      self.etcd.get_key('/formations/{username}/{formation_name}'.format(
        username=username, formation_name=formation_name))))
    for app in app_list:
      # If our host doesn't support swapping we're going to get some garbage 
      # message in here
      if "WARNING" in app['container_id']:
        app['container_id'] = app['container_id'].replace("WARNING: Your "\
          "kernel does not support memory swap capabilities. Limitation discarded.\n","")
        #Message changed in docker 0.8.0
        app['container_id'] = app['container_id'].replace("WARNING: WARNING:"\
          "Your kernel does not support swap limit capabilities. Limitation "\
          "discarded.\n","")
      app['container_id'].strip('\n')

      # Set volumes if needed
      volumes = None
      if app['volumes']:
        self.logger.info("Setting volumes to: " + ''.join(app['volumes']))
        volumes = app['volumes']

      f.add_app(app['container_id'], app['hostname'], app['cpu_shares'],
        app['ram'], app['port_list'], app['ssh_port'], 22, app['host_server'], volumes)

    # Return fully parsed and populated formation object
    return f

  def save_formation_to_etcd(self, formation):
    name = formation.name
    username = formation.username

    self.etcd.set_key('formations/{username}/{formation_name}'.format(
      username=username, formation_name=name), formation)

  # TODO write code to add new apps to load balancer
  def add_app_to_nginx(self, app):
    pass

  # TODO write code to add new apps to the load balancer
  def add_app_to_apache(self, app):
    pass

  def start_application(self, app):
    # Run a salt cmd to startup the formation
    docker_command = "docker run -c={cpu_shares} -d -i -t -h=\"{hostname}\" -m={ram}m "\
      "--name={hostname} {port_list} {volume_list} {image} /sbin/my_init -- bash"

    self.logger.info("Port list %s" % app.port_list)
    port_list = ' '.join(map(lambda x: '-p ' + x, app.port_list))

    # Only create this list if needed
    volume_list = ''
    if app.volume_list:
      volume_list = ' '.join(map(lambda x: '-v ' + x, app.volume_list))

    d = docker_command.format(cpu_shares=app.cpu_shares, 
      hostname=app.hostname, ram=app.ram, image=app.docker_image, 
      port_list=port_list, volume_list=volume_list) 

    self.logger.info("Starting up docker container on {host_server} with cmd: {docker_cmd}".format(
      host_server=app.host_server, docker_cmd=d))

    salt_process = self.salt_client.cmd(app.host_server,'cmd.run', [d], expr_form='list')
    container_id = salt_process[app.host_server]
    if container_id:
      if "WARNING" in container_id:
        container_id = container_id.replace("WARNING: "\
          "Your kernel does not support swap limit capabilities. Limitation "\
          "discarded.\n","")
        container_id.strip("\n")
      #Docker only uses the first 12 chars to identify a container
      app.change_container_id(container_id[0:12])

  def bootstrap_application(self, app):
    # Log into the host with paramiko and run the salt bootstrap script 
    host_server = self.fqdn_to_shortname(app.host_server)

    self.logger.info("Bootstrapping {hostname} on server: {host_server} port: {port}".format(
      hostname=app.hostname, 
      host_server=host_server,
      port=app.ssh_port))

    try:
      ssh = paramiko.SSHClient()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      ssh.connect(hostname=host_server, port=app.ssh_port, 
        username='root', password='newroot')

      transport = paramiko.Transport((host_server, app.ssh_port))
      transport.connect(username = 'root', password = 'newroot')
      sftp = paramiko.SFTPClient.from_transport(transport)
      sftp.put('bootstrap.sh', '/root/bootstrap.sh')
      sftp.put('start.sh', '/root/start.sh')

      ssh.exec_command("chmod +x /root/bootstrap.sh")
      ssh.exec_command("chmod +x /root/start.sh")
      stdin, stdout, stderr = ssh.exec_command("bash /root/start.sh")
      self.logger.debug(''.join(stdout.readlines()))
      ssh.close()
    except SSHException:
      self.logger.error("Failed to log into server.  Shutting it down and cleaning up the mess.")
      self.delete_container(app.host_server, app.container_id)

  # Stops and deletes a container
  def delete_container(self, host_server, container_id):
    results = self.salt_client.cmd(host_server, 'cmd.run', 
      ['docker stop {container_id}'.format(container_id=container_id)], 
      expr_form='list')
    self.logger.debug("Salt return: {stop_cmd}".format(stop_cmd=results[host_server]))

    results = self.salt_client.cmd(host_server, 'cmd.run', 
      ['docker rm {container_id}'.format(container_id=container_id)], 
      expr_form='list')
    self.logger.debug("Salt return: {rm_cmd}".format(rm_cmd=results[host_server]))

  # Stops and deletes a formation. Use with caution
  def delete_formation(self, user, formation_name):
    formation_list = self.list_formations(user)
    if formation_name in formation_list:
      pass
    else:
      self.logger.error("Formation name not found!")

  def list_containers(self, user, formation_name):
    pass

  def create_containers(self, user, number, formation_name,
    cpu_shares, ram, port_list, hostname_scheme, volume_list, 
    docker_image, force_host_server=None):

    f = Formation(user, formation_name)
    # Convert ram to bytes from MB
    ram = ram * 1024 * 1024

    # Get the cluster machines on each creation
    cluster_list = self.get_docker_cluster()
    circular_cluster_list = CircularList(self.order_cluster_by_load(cluster_list))

    # Loop for the requested amount of containers to be created
    for i in range(1, number+1):
      # [{"host_port":ssh_host_port, "container_port":ssh_container_port}]
      ssh_host_port = 9022 + i
      ssh_container_port = 22
      host_server = circular_cluster_list[i].hostname
      hostname = '{hostname}{number}'.format(
        hostname=hostname_scheme,
        number=str(i).zfill(3))

      # First check if we can add this host to salt.  If not exit with -1
      if self.check_salt_key_used(hostname):
        self.logger.error('Salt key is already taken for {hostname}'.format(
          hostname=hostname))
        sys.exit(-1)

      # We are being asked to overwrite this
      if force_host_server:
        host_server = force_host_server
      validated_ports = []

      while self.check_port_used(host_server, ssh_host_port):
        ssh_host_port = ssh_host_port +1

      for port in port_list:
        self.logger.info("Checking if port {port} on {host} is in use".format(
          port=port, host=host_server))
        if ':' in port:
          ports = port.split(':')

          # Only check if the host port is free.  The container port should be free
          while self.check_port_used(host_server, ports[0]):
            ports[0] = int(ports[0]) + 1

          # Add this to the validated port list
          validated_ports.append('{host_port}:{container_port}'.format(
            host_port = str(ports[0]),
            container_port = str(ports[1])))
        else:
          while self.check_port_used(host_server, port):
            port = int(port) + 1
          validated_ports.append(str(port))

      self.logger.info('Adding app to formation {formation_name}: {hostname} cpu_shares={cpu} '
        'ram={ram} ports={ports} host_server={host_server} docker_image={docker_image}'.format(
          formation_name=formation_name, hostname=hostname, 
          cpu=cpu_shares, ram=ram, ports=validated_ports, host_server=host_server,
          docker_image=docker_image))

      f.add_app(None, '{hostname}'.format(hostname=hostname), 
        cpu_shares, ram, validated_ports, ssh_host_port, 
        ssh_container_port, host_server, docker_image, volume_list)

    # Lets get this party started
    for app in f.application_list:
      self.start_application(app)
      #self.logger.info("Sleeping 2 seconds while the container starts")
      #time.sleep(2)
      #self.bootstrap_application(app)

    self.logger.info("Saving the formation to ETCD")
    self.save_formation_to_etcd(f)

class TestManager(unittest.TestCase):
  def test_checkPortUsed(self):
    self.assertEquals(1, 0)

  def test_getDockerCluster(self):
    self.assertEquals(1, 0)

  def test_getLoadBalancerCluster(self):
    self.assertEquals(1, 0)

  def test_orderClusterByLoad(self):
    self.assertEquals(1, 0)

  def test_deleteContainer(self):
    self.assertEquals(1, 0)

  def test_saveFormationToEtcd(self):
    logger = logging.getLogger()
    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    manager = Manager(logger)
    expected_text = '[{"username": "cholcomb", "cpu-shares": 102, '\
      '"ram": 100, "hostname": "app01", "ports": [{"host_port": 8080, '\
      '"container_port": 8080}], "host_server": "dlceph02"}]'
    username = 'cholcomb'
    formation_name = 'test_formation'
    f = Formation(username, formation_name)
    f.add_app(username, 'app01', 102, 100, [{"host_port":8080, "container_port":8080}], 'dlceph02')
    manager.save_formation_to_etcd(f)
    etcd_ret = manager.etcd.get_key('{username}/{hostname}'.format(username=username, hostname=formation_name))

    logger.debug("Etcd_ret: %s" % etcd_ret)
    logger.debug("Expected text: %s" % expected_text)
    self.assertEquals(etcd_ret, expected_text)

########NEW FILE########
__FILENAME__ = nginx
class Nginx(object):
  '''
    A python class to manage the nginx cluster

  An example nginx load balancing config:
  http {
    upstream web_rack {
      server 10.0.0.1:80;
      server 10.0.0.2:80;
      server 10.0.0.3:80;
    }
 
    server {
      listen 80;
      server_name www.example.com;
      location / {
          proxy_pass http://web_rack;
      }
    }
  }
  '''
  def __init__(self, manager, logger):
    self.manager = manager
    self.salt = manager.salt_client
    self.logger = logger

  #TODO 
  def add_vhost(self, cluster_config):
    #If the site file exists, blow it away and recreate it
    #We need a server list, ports and a listen name
    nginx_cluster = self.manager.get_load_balancer_cluster()

  #TODO
  def remove_vhost(self, cluster_config):
    pass

  def reload_nginx(self, host):
    #Tells nginx to reload its config
    self.salt.cmd(host, 'cmd.run', ['service nginx reload'], expr_form='list')


########NEW FILE########
__FILENAME__ = systemd
class Systemd(object):
  '''
  Systemd will create/delete systemd files to make sure
  that the containers can survive a reboot

  The systemd files are configuration so they may need to live
  in the salt repo.  This is still to be determined.  Writing out a 
  yaml file to salt would fix this problem.  Write it to salt and 
  forget about it
  '''
  def __init__(self, manager, salt):
    self.manager = manager
    self.salt = manager.salt_client


########NEW FILE########
__FILENAME__ = upstart
class Upstart(object):
  '''
  Upstart will create/delete upstart files to make sure
  that the containers can survive a reboot

  The upstart files are configuration so they may need to live
  in the salt repo.  This is still to be determined.  Writing out a 
  yaml file to salt would fix this problem.  Write it to salt and 
  forget about it
  '''
  def __init__(self, manager, salt):
    self.manager = manager
    self.salt = manager.salt_client


########NEW FILE########
__FILENAME__ = verify
'''
  This class performs a few functions:
  1. If the host is up and the container is down it starts the container
  2. Verifies a container is running
  3. Verifies a container has cron running.  Calls start.sh if needed.

'''
import paramiko
import salt.client
import time

from circularlist import CircularList
from etcd import Etcd
from paramiko import SSHException
from pyparsing import Literal, srange, Word

class VerifyFormations(object):
  def __init__(self, manager, logger):
    self.logger = logger
    self.salt_client = salt.client.LocalClient()
    self.manager = manager
    self.etcd = Etcd(logger)

  def start_verifying(self):
    # Parse out the username and formation name 
    # from the ETCD directory string
    formation_parser = Literal('/formations/') + \
      Word(srange("[0-9a-zA-Z_-]")).setResultsName('username') + Literal('/') + \
      Word(srange("[0-9a-zA-Z_-]")).setResultsName('formation_name')

    # call out to ETCD and load all the formations
    formation_list = []

    user_list = self.etcd.list_directory('formations')
    if user_list:
      for user in user_list:
        formations = self.etcd.list_directory(user)
        for formation in formations:
          parse_results = formation_parser.parseString(formation)
          if parse_results:
            formation_name = parse_results['formation_name']
            username = parse_results['username']

            self.logger.info('Attempting to load formation: {formation_name} '
              'with username: {username}'.format(formation_name=formation_name,
                username=username))
            f = self.manager.load_formation_from_etcd(username, formation_name)
            formation_list.append(f)
          else:
            self.logger.error("Could not parse the ETCD string")

      if formation_list:
        # TODO Use background salt jobs
        # Start verifying things
        # Ask salt to do these things for me and give me back an job_id
        # results = self.salt_client.cmd_async(host, 'cmd.run', 
        #   ['netstat -an | grep %s | grep tcp | grep -i listen' % port], 
        #   expr_form='list')
        # 
        # salt-run jobs.lookup_jid <job id number>
        for f in formation_list:
          for app in f.application_list:
            # Check to make sure it's up and running
            self.logger.info("Running verification on app: "
              "{app_name}".format(app_name=app.hostname))
            self.logger.info('{server} docker ps | grep {container_id}'.format(
              server=app.host_server, 
              container_id=app.container_id))
            results = self.salt_client.cmd(app.host_server, 'cmd.run', 
              ['docker ps | grep {container_id}'.format(container_id=app.container_id)], 
              expr_form='list')
            if results:
              self.logger.debug("Salt return: {docker_results}".format(
                docker_results=results[app.host_server]))
              if results[app.host_server] == "":
                self.logger.error("App {app} is not running!".format(
                  app=app.hostname))
                # Start the app back up and run start.sh on there
                self.start_application(app)
              else:
                self.logger.info("App {app} is running.  Checking if "
                  "cron is running also".format(app=app.hostname))
                # Check if cron is running on the container and bring it back 
                # up if needed
                # Log in with ssh and check if cron is up and running
                self.logger.info("Sleeping 2 seconds while the container starts")
                time.sleep(2)
                self.check_running_application(app)
            else:
              self.logger.error("Call out to server {server} failed. Moving it".format(
                server=app.host_server))
              # move the container
              self.move_application(app)

  # Start an application that isn't running
  def start_application(self, app):
    # Start the application and run start.sh to kick off cron
    self.logger.info("Starting app {app} with docker id: {app_id} up".format(
      app=app.hostname, app_id=app.container_id))
    results = self.salt_client.cmd(app.host_server, 'cmd.run', 
      ['docker start {container_id}'.format(container_id=app.container_id)], 
      expr_form='list')
    self.logger.debug(results)
    if results:
      if "Error: No such container" in results[app.host_server]:
        # We need to recreate the container
        self.logger.error("Container is missing on the host!. "
          "Trying to recreate")
        self.manager.start_application(app)
        self.logger.info("Sleeping 2 seconds while the container starts")
        time.sleep(2)
        self.manager.bootstrap_application(app)
      elif "Error: start: No such container:" in results[app.host_server]:
        # Seems the container already exists but won't start.  Bug?
        self.logger.error("Container failed to start")
        self.move_application(app)
      else:
        self.logger.info("Waiting 2 seconds for docker to start the container")
        time.sleep(2)
        self.check_running_application(app)
    else:
      # Move the container to another host, this host is messed up
      self.logger.error("Failed to start {container_id} on host {host}".format(
        container_id=app.container_id, host=app.host_server))
      self.move_application(app)

  # Move an application to another host and record the change in etcd
  def move_application(self, app):
    old_host = app.host_server
    cluster_list = self.manager.get_docker_cluster()
    circular_cluster_list = CircularList(
      self.manager.order_cluster_by_load(cluster_list))

    if app.host_server in circular_cluster_list:
      index = circular_cluster_list.index(app.host_server)
      app.host_server = circular_cluster_list[index+1].hostname
    else:
      # Assign the first one in the list if not found above
      app.host_server = circular_cluster_list[0].hostname

    self.logger.info("Moving app {app_name} from {old_host} to {new_host}".format(
      app_name=app.hostname, old_host=old_host, new_host=app.host_server))

    self.logger.info("Bootstrapping the application on the new host")
    self.start_application(app)

  # Log into the application via ssh and check everything
  def check_running_application(self, app):
    # TODO
    # Use the docker top command to see if cron is running instead of using ssh
    try:
      ssh = paramiko.SSHClient()
      ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      # Move this user/pass into a config file
      self.logger.info('SSHing into host {hostname}:{port}'.format(
        hostname=app.host_server, port=app.ssh_port))
      ssh.connect(hostname=app.host_server, port=app.ssh_port, 
        username='root', password='newroot')
      # Is cron running?
      # If not run start.sh
      stdin, stdout, stderr = ssh.exec_command("pgrep cron")
      output = stdout.readlines()
      self.logger.debug(output)

      if len(output) == 0:
        # cron isn't running
        self.logger.info("Cron is not running.  Starting it back up")
        stdin, stdout, stderr = ssh.exec_command("/root/start.sh")
      else:
        self.logger.info("Cron is running.")
      ssh.close()
    except SSHException:
      self.logger.error("Failed to log into server.")
      # TODO should we delete this or ignore it?
      #self.delete_container(app.host_server, app.container_id)

########NEW FILE########
