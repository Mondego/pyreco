__FILENAME__ = cli
import sys, os
import cmdln
from . import service

class MaestroCli(cmdln.Cmdln):
    """Usage:
        maestro SUBCOMMAND [ARGS...]
        maestro help SUBCOMMAND

    Maestro provides a command to manage multiple Docker containers
    from a single configuration.

    ${command_list}
    ${help_list}
    """
    name = "maestro"

    def __init__(self, *args, **kwargs):
      cmdln.Cmdln.__init__(self, *args, **kwargs)
      cmdln.Cmdln.do_help.aliases.append("h")

    @cmdln.option("-f", "--maestro_file",
                  help='path to the maestro file to use')
    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_build(self, subcmd, opts, *args):
      """Setup and start a set of Docker containers.

        usage:
            build
        
        ${cmd_option_list}
      """
      config = opts.maestro_file
      if not config:
        config = os.path.join(os.getcwd(), 'maestro.yml')

      if not config.startswith('/'):
        config = os.path.join(os.getcwd(), config)

      if not os.path.exists(config):
        sys.stderr.write("No maestro configuration found {0}\n".format(config))
        exit(1)
            
      containers = service.Service(config)
      containers.build()

      environment = opts.environment_file
      name = opts.name      
      if name:
        environment = self._create_global_environment(name)        
      else:
        environment = self._create_local_environment(opts)        

      containers.save(environment)

      print "Launched."
   

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_start(self, subcmd, opts, *args):
      """Start a set of Docker containers that had been previously stopped. Container state is defined in an environment file. 

        usage:
            start [container_name]
        
        ${cmd_option_list}
      """
      container = None
      if (len(args) > 0):
        container = args[0]

      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      if containers.start(container):
        containers.save(environment)
        print "Started."

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_stop(self, subcmd, opts, *args):
      """Stop a set of Docker containers as defined in an environment file. 

        usage:
            stop [container_name]
        
        ${cmd_option_list}
      """
      container = None
      if (len(args) > 0):
        container = args[0]

      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      if containers.stop(container):
        containers.save(environment)
        print "Stopped."

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_restart(self, subcmd, opts, *args):
      """Restart a set of containers as defined in an environment file. 

        usage:
            restart [container_name]
        
        ${cmd_option_list}
      """
      self.do_stop('stop', opts, args)
      self.do_start('start', opts, args)

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_destroy(self, subcmd, opts, *args):
      """Stop and destroy a set of Docker containers as defined in an environment file. 

        usage:
            destroy
        
        ${cmd_option_list}
      """
      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      if containers.destroy():
        containers.save(environment)
        print "Destroyed."
 
    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    @cmdln.option("-a", "--attach", action="store_true",
                  help='Attach to the running container to view output')    
    @cmdln.option("-d", "--dont_add", action="store_true",
                  help='Just run the command and exit. Don\'t add the container to the environment')        
    def do_run(self, subcmd, opts, *args):
      """Start a set of Docker containers that had been previously stopped. Container state is defined in an environment file. 

        usage:
            run template_name [commandline]
        
        ${cmd_option_list}
      """
      container = None
      if (len(args) == 0):
        sys.stderr.write("Error: Container name must be provided\n")
        exit(1)

      environment = self._verify_environment(opts)
      
      template = args[0]
      commandline = args[1:]
      print " ".join(commandline)
      containers = service.Service(environment=environment)
      containers.run(template, commandline, attach=opts.attach, dont_add=opts.dont_add) 
      containers.save(environment)

      if opts.dont_add:
        print "Execution of " + template + " complete."
      else:
        print "Adding a new instance of " + template + "."   

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_ps(self, subcmd, opts, *args):
      """Show the status of a set of containers as defined in an environment file. 

        usage:
            ps
        
        ${cmd_option_list}
      """
      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      print containers.ps() 

    def _verify_global_environment(self, name):
      """
      Setup the global environment.
      """
      # Default to /var/lib/maestro and check there first
      path = '/var/lib/maestro'
      if not os.path.exists(path) or not os.access(path, os.W_OK):            
        env_path = os.path.join(path, name)
        # See if the environment exists in /var/lib maestro
        if not os.path.exists(env_path):              
          # If the environment doesn't exist or is not accessible then we check ~/.maestro instead
          path = os.path.expanduser(os.path.join('~', '.maestro'))
          if not os.path.exists(path):
            sys.stderr.write("Global named environments directory does not exist {0}\n".format(path))
            exit(1)

      env_path = os.path.join(path, name)
      if not os.path.exists(env_path):
        sys.stderr.write("Environment named {0} does not exist\n".format(env_path))
        exit(1)
      
      if not os.access(env_path, os.W_OK):
        sys.stderr.write("Environment named {0} is not writable\n".format(env_path))
        exit(1)

      return os.path.join(env_path, 'environment.yml')

    def _create_global_environment(self, name):
      """
      Setup the global environment.
      """
      # Default to /var/lib/maestro
      # It has to exist and be writable, otherwise we'll just use a directory relative to ~
      path = '/var/lib/maestro'
      if not os.path.exists(path) or not os.access(path, os.W_OK):      
        # If /var/lib/maestro doesn't exist or is not accessible then we use ~/.maestro instead
        path = os.path.expanduser(os.path.join('~', '.maestro'))
        if not os.path.exists(path):
          print "Creating ~/.maestro to hold named environments"
          os.makedirs(path)

      # The environment will live in a directory under path
      env_path = os.path.join(path, name)
      if not os.path.exists(env_path):
        print "Initializing ~/.maestro/" + name
        os.makedirs(env_path)
      return os.path.join(env_path, 'environment.yml')

    def _verify_environment(self, opts):
      """
      Verify that the provided environment file exists.
      """
      if opts.name:
        environment = self._verify_global_environment(opts.name)
      else:
        environment = self._create_local_environment(opts)        
        
        if not os.path.exists(environment):
          sys.stderr.write("Could not locate the environments file {0}\n".format(environment))
          exit(1)

        if not os.access(environment, os.W_OK):
          sys.stderr.write("Environment file {0} is not writable\n".format(environment))
          exit(1)

      return environment
    
    def _create_local_environment(self, opts):
      environment = opts.environment_file
      if not environment:
        base = os.path.join(os.getcwd(), '.maestro')  
        environment = os.path.join(base, 'environment.yml')
        if not os.path.exists(base):
          print "Initializing " + base
          os.makedirs(base)

      return environment
########NEW FILE########
__FILENAME__ = container
import os, sys
from exceptions import ContainerError
import utils, StringIO, logging
import py_backend

class Container:
  def __init__(self, name, state, config, mounts=None):
    self.log = logging.getLogger('maestro')
    
    self.state = state    
    self.config = config
    self.name = name
    self.mounts = mounts

    if 'hostname' not in self.config:
      self.config['hostname'] = name
      
    #if 'command' not in self.config:
    #  self.log.error("Error: No command specified for container " + name + "\n")
    #  raise ContainerError('No command specified in configuration') 
      
    self.backend = py_backend.PyBackend()

  def create(self):
    self._start_container(False) 

  def run(self):
    self._start_container()

  def rerun(self):
    # Commit the current container and then use that image_id to restart.
    self.state['image_id'] = self.backend.commit_container(self.state['container_id'])['Id']
    self._start_container()

  def start(self):
    utils.status("Starting container %s - %s" % (self.name, self.state['container_id'])) 
    self.backend.start_container(self.state['container_id'], self.mounts)
  
  def stop(self, timeout=10):
    utils.status("Stopping container %s - %s" % (self.name, self.state['container_id']))     
    self.backend.stop_container(self.state['container_id'], timeout=timeout)
    
  def destroy(self, timeout=None):
    self.stop(timeout)
    utils.status("Destroying container %s - %s" % (self.name, self.state['container_id']))         
    self.backend.remove_container(self.state['container_id'])    

  def get_ip_address(self):
    return self.backend.get_ip_address(self.state['container_id']) 

  def inspect(self):
    return self.backend.inspect_container(self.state['container_id'])   

  def attach(self):
    # should probably catch ctrl-c here so that the process doesn't abort
    for line in self.backend.attach_container(self.state['container_id']):
      sys.stdout.write(line)
    
  def _start_container(self, start=True):
    # Start the container
    self.state['container_id'] = self.backend.create_container(self.state['image_id'], self.config)
    
    if (start):
      self.start()

    self.log.info('Container started: %s %s', self.name, self.state['container_id'])     

########NEW FILE########
__FILENAME__ = environment
class Environment:
  def __init__(self):
    # Maintains a list of services ordered in start order
    self.services = []

  def start(self):
    pass

  def stop(self):
    pass

  def destroy(self):
    pass

  def load(self):
    pass

  


########NEW FILE########
__FILENAME__ = exceptions

class MaestroError(Exception):
  pass

class TemplateError(MaestroError):
  pass

class ContainerError(MaestroError):
  pass
########NEW FILE########
__FILENAME__ = py_backend
import docker

class PyBackend:
  def __init__(self):
    self.docker_client = docker.Client()

  ## Container management

  def create_container(self, image_id, config):
    return self._start_container(image_id, config, False) 

  def run_container(self, image_id, config):
    return self._start_container(image_id, config)

  def start_container(self, container_id, mounts=None):
    self.docker_client.start(container_id, binds=mounts)
  
  def stop_container(self, container_id, timeout=10):
    self.docker_client.stop(container_id, timeout=timeout)
    
  def remove_container(self, container_id, timeout=None):
    self.stop_container(timeout)
    self.docker_client.remove_container(container_id)    

  def inspect_container(self, container_id):
    return self.docker_client.inspect_container(container_id)

  def commit_container(self, container_id):
    return self.docker_client.commit(container_id)  
  
  def attach_container(self, container_id):
    return self.docker_client.attach(container_id)  
  
  ## Image management

  def build_image(self, fileobj=None, path=None):
    return self.docker_client.build(path=path, fileobj=fileobj)

  def remove_image(self, image_id):
    self.docker_client.remove_image(image_id)

  def inspect_image(self, image_id):
    return self.docker_client.inspect_image(image_id)

  def images(self, name):
    return self.docker_client.images(name=name)

  def tag_image(self, image_id, name, tag):
    self.docker_client.tag(image_id, name, tag=tag)

  def pull_image(self, name):
    return self.docker_client.pull(name)
  
  ## Helpers

  def get_ip_address(self, container_id):
    state = self.docker_client.inspect_container(container_id)    
    return state['NetworkSettings']['IPAddress']

  def _start_container(self, image_id, config, start=True):
    # Start the container
    container_id = self.docker_client.create_container(image_id, **config)['Id']
    
    if (start):
      self.start_container(container_id)

    return container_id
########NEW FILE########
__FILENAME__ = service
import docker
import os, sys, yaml, copy, string, StringIO
import maestro, template, utils
from requests.exceptions import HTTPError
from .container import Container

class ContainerError(Exception):
  pass

class Service:
  def __init__(self, conf_file=None, environment=None):
    self.log = utils.setupLogging()
    self.containers = {}
    self.templates = {}
    self.state = 'live'

    if environment:
      self.load(environment)      
    else:
      # If we didn't get an absolute path to a file, look for it in the current directory.
      if not conf_file.startswith('/'):
        conf_file = os.path.join(os.path.dirname(sys.argv[0]), conf_file)

      data = open(conf_file, 'r')
      self.config = yaml.load(data)
      
    # On load, order templates into the proper startup sequence      
    self.start_order = utils.order(self.config['templates'])

  def get(self, container):
    return self.containers[container]

  def build(self, wait_time=60):
    # Setup and build all the templates
    for tmpl in self.start_order:          
      if not self.config['templates'][tmpl]:
        sys.stderr.write('Error: no configuration found for template: ' + tmpl + '\n')
        exit(1)

      config = self.config['templates'][tmpl]
      
      # Create the template. The service name and version will be dynamic once the new config format is implemented
      utils.status('Building template %s' % (tmpl))
      tmpl_instance = template.Template(tmpl, config, 'service', '0.1')
      tmpl_instance.build()


      self.templates[tmpl] = tmpl_instance

      # We'll store the running instances as a dict under the template
      self.containers[tmpl] = {}

    # Start the envrionment
    for tmpl in self.start_order:            
      self._handleRequire(tmpl, wait_time)

      tmpl_instance = self.templates[tmpl]
      config = self.config['templates'][tmpl]
      
      # If count is defined in the config then we're launching multiple instances of the same thing
      # and they'll need to be tagged accordingly. Count only applies on build.
      count = tag_name = 1
      if 'count' in config:
        count = tag_name = config['count']  
      
      while count > 0:      
        name = tmpl
        if tag_name > 1:
          name = name + '__' + str(count)

        utils.status('Launching instance of template %s named %s' % (tmpl, name))      
        instance = tmpl_instance.instantiate(name)
        instance.run()

        self.containers[tmpl][name] = instance
        
        count = count - 1
      
  def destroy(self, timeout=None):       
    for tmpl in reversed(self.start_order):
      for container in self.containers[tmpl]:
        self.log.info('Destroying container: %s', container)      
        self.containers[tmpl][container].destroy(timeout) 

    self.state = 'destroyed'    
    return True
    
  def start(self, container=None, wait_time=60):
    if not self._live():
      utils.status('Environment has been destroyed and can\'t be started')
      return False

    # If a container is provided we just start that container
    # TODO: may need an abstraction here to handle names of multi-container groups
    if container:
      tmpl = self._getTemplate(container)
      
      rerun = self._handleRequire(tmpl, wait_time)
      
      # We need to see if env has changed and then commit and run a new container.
      # This rerun functionality should only be a temporary solution as each time the
      # container is restarted this way it will consume a layer.
      # This is only necessary because docker start won't take a new set of env vars
      if rerun:
        self.containers[tmpl][container].rerun()  
      else:
        self.containers[tmpl][container].start()  
    else:
      for tmpl in self.start_order:  
        rerun = self._handleRequire(tmpl, wait_time)
        
        for container in self.containers[tmpl]:
          if rerun:
            self.containers[tmpl][container].rerun()
          else:
            self.containers[tmpl][container].start()

    return True
    
  def stop(self, container=None, timeout=None):
    if not self._live():
      utils.status('Environment has been destroyed and can\'t be stopped.')
      return False
     
    if container:
      self.containers[self._getTemplate(container)][container].stop(timeout)
    else:
      for tmpl in reversed(self.start_order):  
        for container in self.containers[tmpl]:             
          self.containers[tmpl][container].stop(timeout)

    return True

  def load(self, filename='envrionment.yml'):
    self.log.info('Loading environment from: %s', filename)      
    
    with open(filename, 'r') as input_file:
      self.config = yaml.load(input_file)

      self.state = self.config['state']
      
      for tmpl in self.config['templates']:
        # TODO fix hardcoded service name and version
        self.templates[tmpl] = template.Template(tmpl, self.config['templates'][tmpl], 'service', '0.1')
        self.containers[tmpl] = {}

      self.start_order = utils.order(self.config['templates'])
      for container in self.config['containers']:
        tmpl = self.config['containers'][container]['template']
      
        self.containers[tmpl][container] = Container(container, self.config['containers'][container], 
          self.config['templates'][tmpl]['config'])
      
  def save(self, filename='environment.yml'):
    self.log.info('Saving environment state to: %s', filename)      
      
    with open(filename, 'w') as output_file:
      output_file.write(self.dump())

  def run(self, template, commandline=None, wait_time=60, attach=False, dont_add=False):
    if template in self.templates:
      self._handleRequire(template, wait_time)
      
      name = template + "-" + str(os.getpid())
      # TODO: name need to be dynamic here. Need to handle static and temporary cases.
      container = self.templates[template].instantiate(name, commandline)
      container.run()

      # For temporary containers we may not want to save it in the environment
      if not dont_add:
        self.containers[template][name] = container
      
      # for dynamic runs there  needs to be a way to display the output of the command.
      if attach:
        container.attach()
      return container
    else:
      # Should handle arbitrary containers
      raise ContainerError('Unknown template')

  def ps(self):
    columns = '{0:<14}{1:<19}{2:<44}{3:<11}{4:<15}\n'
    result = columns.format('ID', 'NODE', 'COMMAND', 'STATUS', 'PORTS')

    for tmpl in self.templates:
      for container in self.containers[tmpl]:
        container_id = self.containers[tmpl][container].state['container_id']
        
        node_name = (container[:15] + '..') if len(container) > 17 else container

        command = ''
        status = 'Stopped'
        ports = ''
        try:
          state = docker.Client().inspect_container(container_id)
          command = string.join([state['Path']] + state['Args'])
          command = (command[:40] + '..') if len(command) > 42 else command
          p = []
          if state['NetworkSettings']['PortMapping']:
            p = state['NetworkSettings']['PortMapping']['Tcp']
          
          for port in p:
            if ports:
              ports += ', '
            ports += p[port] + '->' + port 
          if state['State']['Running']:
            status = 'Running'
        except HTTPError:
          status = 'Destroyed'

        result += columns.format(container_id, node_name, command, status, ports)

    return result.rstrip('\n')

  def dump(self):
    result = {}
    result['state'] = self.state
    result['templates'] = {}
    result['containers'] = {}
    
    for template in self.templates:      
      result['templates'][template] = self.templates[template].config

      for container in self.containers[template]:      
        result['containers'][container] = self.containers[template][container].state

    return yaml.dump(result, Dumper=yaml.SafeDumper)
  
  def _getTemplate(self, container):
    # Find the template for this container
    for tmpl in self.containers:
      if container in self.containers[tmpl]:
        return tmpl

  def _live(self):
    return self.state == 'live'

  def _pollService(self, container, service, name, port, wait_time):
    # Based on start_order the service should already be running
    service_ip = self.containers[service][name].get_ip_address()
    utils.status('Starting %s: waiting for service %s on ip %s and port %s' % (container, service, service_ip, port))
     
    result = utils.waitForService(service_ip, int(port), wait_time)
    if result < 0:
      utils.status('Never found service %s on port %s' % (service, port))
      raise ContainerError('Couldn\d find required services, aborting')

    utils.status('Found service %s on ip %s and port %s' % (service, service_ip, port))
    
    #return service_ip + ":" + str(port)
    return service_ip

  def _handleRequire(self, tmpl, wait_time):
    env = []
    # Wait for any required services to finish registering        
    config = self.config['templates'][tmpl]
    if 'require' in config:
      try:
        # Containers can depend on mulitple services
        for service in config['require']:
          service_env = []
          port = config['require'][service]['port']          
          if port:
            # If count is defined then we need to wait for all instances to start                    
            count = config['require'][service].get('count', 1)          
            if count > 1:
              while count > 0:
                name = service + '__' + str(count)
                service_env.append(self._pollService(tmpl, service, name, port, wait_time))
                count = count - 1                
            else:
              service_env.append(self._pollService(tmpl, service, service, port, wait_time))

            env.append(service.upper() + '=' + ' '.join(service_env))
      except:
        utils.status('Failure on require. Shutting down the environment')
        self.destroy()
        raise
      
      # If the environment changes then dependent containers will need to be re-run not just restarted
      rerun = False
      # Setup the env for dependent services      
      if 'environment' in config['config']:
        for entry in env:
          name, value = entry.split('=')
          result = []
          replaced = False
          # See if an existing variable exists and needs to be updated
          for var in config['config']['environment']:
            var_name, var_value = var.split('=')
            if var_name == name and var_value != value:
              replaced = True
              rerun = True
              result.append(entry)
            elif var_name == name and var_value == value:
              # Just drop any full matches. We'll add it back later
              pass
            else:
              result.append(var)

          if not replaced:
            result.append(entry)
    
        config['config']['environment'] = result 
      else:
        config['config']['environment'] = env

      # Determines whether or not a container can simply be restarted
      return rerun
    
########NEW FILE########
__FILENAME__ = template
import exceptions, utils, container, py_backend
import StringIO, copy, logging, sys
from requests.exceptions import HTTPError

class Template:
  def __init__(self, name, config, service, version):
    self.name     = name    
    self.config   = config
    self.service  = service
    self.version  = version
    self.log      = logging.getLogger('maestro')

    self.backend = py_backend.PyBackend()

  def build(self):
    # If there is a docker file or url hand off to Docker builder    
    if 'buildspec' in self.config:
      if self.config['buildspec']:
        if 'dockerfile' in self.config['buildspec']:
          self._build(dockerfile=self.config['buildspec']['dockerfile'])
        elif 'url' in self.config['buildspec']:
          self._build(url=self.config['buildspec']['url'])
      else:
        raise exceptions.TemplateError("Template: " + self.name + " Buildspec specified but no dockerfile or url found.")
    else:
      # verify the base image and pull it if necessary
      try:
        base = self.config['base_image']    
        self.backend.inspect_image(base)
      except HTTPError:
        # Attempt to pull the image.
        self.log.info('Attempting to pull base: %s', base)
        result = self.backend.pull_image(base)
        if 'error' in result:
          self.log.error('No base image could be pulled under the name: %s', base)      
          raise exceptions.TemplateError("No base image could be pulled under the name: " + base)
      except KeyError:
        raise exceptions.TemplateError("Template: " + self.name + "No base image specified.")

      # There doesn't seem to be a way to currently remove tags so we'll generate a new image.
      # More consistent for all cases this way too but it does feel kinda wrong.
      dockerfile = """
      FROM %s
      MAINTAINER %s
      """ % (base, self._mid())
      self._build(dockerfile=dockerfile)

    return True

  # Launches an instance of the template in a new container
  def instantiate(self, name, command=None):    
    config = copy.deepcopy(self.config['config'])

    # Setup bind mounts to the host system    
    bind_mounts = {}
    if 'mounts' in self.config:
      bind_mounts = self.config['mounts']
      for src, dest in self.config['mounts'].items():
        if 'volumes' not in config:          
          config['volumes'] = {}
        
        config['volumes'][dest] = {}

    if command:
      if isinstance(command, basestring):
        config['command'] = command
      else:
        config['command'] = " ".join(command)
      
    return container.Container(name, {'template': self.name, 'image_id': self.config['image_id']}, config, mounts=bind_mounts)

  def destroy(self):
    # If there is an image_id then we need to destroy the image.
    if 'image_id' in self.config:      
      self.backend.remove_image(self.config['image_id'])
    
  def full_name(self):
    return self.service + "." + self.name

  def _base_id(self, base):
    tag = 'latest'
    if ':' in base:
      base, tag = base.split(':')
    
    result = self.backend.images(name=base)
    for image in result:
      if image['Tag'] == tag:
        return image['Id']

    return None

  # Generate the meastro specific ID for this template.
  def _mid(self):
    return self.service + "." + self.name + ":" + self.version

  def _build(self, dockerfile=None, url=None):
    self.log.info('Building container: %s', self._mid())      

    if (dockerfile):
      result = self.backend.build_image(fileobj=StringIO.StringIO(dockerfile))
    elif (url):
      result = self.backend.build_image(path=url)
    else:
      raise exceptions.TemplateError("Can't build if no buildspec is provided: " + self.name)
    
    if result[0] == None:
      # TODO: figure out what to do with the result of this execution
      print result
      raise exceptions.TemplateError("Build failed for template: " + self.name)

    self.config['image_id'] = result[0]
    
    self._tag(self.config['image_id'])

    self.log.info('Container registered with tag: %s', self._mid())   

  def _tag(self, image_id):
    # Tag the container with the name and process id
    self.backend.tag_image(image_id, self.service + "." + self.name, tag=self.version)
    
    # TODO: make sure this is always appropriate to do as there may be cases where tagging a build as latest isn't desired.
    self.backend.tag_image(image_id, self.service + "." + self.name, tag='latest')
     

########NEW FILE########
__FILENAME__ = utils
import logging
import os, sys, time, socket
import docker

def setupLogging():
  log = logging.getLogger('maestro')
  if not len(log.handlers):
    log.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s %(levelname)-10s %(message)s")
    filehandler = logging.FileHandler('maestro.log')
    filehandler.setLevel(logging.DEBUG)
    filehandler.setFormatter(formatter)
    log.addHandler(filehandler)  
  return log

quiet=False
def setQuiet(state=True):
  global quiet
  quiet = state

# Display the status 
def status(string):
  global quiet
  log = logging.getLogger('maestro')  
  log.info(string)
  
  if not quiet:
    print string

def order(raw_list):
  def _process(wait_list):
    new_wait = []
    for item in wait_list:
      match = False
      for dependency in raw_list[item]['require']:
        if dependency in ordered_list:
          match = True  
        else:
          match = False
          break

      if match:
        ordered_list.append(item)
      else:
        new_wait.append(item)

    if len(new_wait) > 0:
      # Guard against circular dependencies
      if len(new_wait) == len(wait_list):
        raise Exception("Unable to satisfy the require for: " + item)

      # Do it again for any remaining items
      _process(new_wait)

  ordered_list = []
  wait_list = []
  # Start by building up the list of items that do not have any dependencies
  for item in raw_list:  
    if 'require' not in raw_list[item]:
      ordered_list.append(item)
    else:
      wait_list.append(item)

  # Then recursively order the items that do define dependencies
  _process(wait_list)

  return ordered_list

def waitForService(ip, port, retries=60):      
  while retries >= 0:
    try:        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((ip, port))
        s.close()
        break
    except:
      time.sleep(0.5)
      retries = retries - 1
      continue
    
  return retries

def findImage(name, tag="latest"):
  result =  docker.Client().images(name=name)

  for image in result:
    if image['Tag'] == tag:
      return image['Id']
  return None
########NEW FILE########
__FILENAME__ = test_container
import unittest, sys
sys.path.append('.')
from maestro import container, exceptions, utils
from requests.exceptions import HTTPError

utils.setQuiet(True)

class TestContainer(unittest.TestCase):
  def testInit(self):
  #  with self.assertRaises(exceptions.ContainerError) as e:
  #      container.Container('test_container', { 'image_id': utils.findImage('ubuntu') }, {})
    pass
  def testGetIpAddress(self):
    # TODO: image_id will change
    c = container.Container('test_container', { 'image_id': utils.findImage('ubuntu') }, {'command': 'ps aux'})

    c.run()

    self.assertIsNotNone(c.state['container_id'])    
    self.assertIsNotNone(c.get_ip_address())

  def testDestroy(self):
    c = container.Container('test_container', { 'image_id': utils.findImage('ubuntu') }, {'command': 'ps aux'})

    c.run()

    self.assertIsNotNone(c.state['container_id'])

    c.destroy()

    with self.assertRaises(HTTPError) as e:
      c.backend.inspect_container(c.state['container_id'])
    
    self.assertEqual(str(e.exception), '404 Client Error: Not Found')
    
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_maestro
import unittest, sys
sys.path.append('.')
import maestro

class TestMaestro(unittest.TestCase):
  def testCreateGlobalEnvironment(self):
    maestro.init_environment()
    
  def testCreateLocalEnvironment(self):
    env = maestro.init_environment("testEnvironment")

    self.assertIsNotNone(env)
  
  def testCreateExistingEnvironment(self):
    maestro.init_environment()
  
  def testGetEnvironment(self):
    pass

  def testListEnvironment(self):
    pass

  def testDestroyLocalEnvironment(self):
    pass

  def testDestroyGlobalEnvironment(self):
    pass

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_py_backend
import unittest, sys, StringIO
sys.path.append('.')
from maestro import py_backend, exceptions, utils
from requests.exceptions import HTTPError

utils.setQuiet(True)

class TestContainer(unittest.TestCase):
  #@unittest.skip("skipping")
  def testStartStopRm(self):
    p = py_backend.PyBackend()
    
    c = p.create_container(utils.findImage('ubuntu'), {'command': '/bin/bash -c "while true; do echo hello world; sleep 60; done;"'})
    state = p.docker_client.inspect_container(c)
    self.assertFalse(state['State']['Running'])

    p.start_container(c)
    state = p.docker_client.inspect_container(c)
    self.assertTrue(state['State']['Running'])

    p.stop_container(c, 1)
    state = p.docker_client.inspect_container(c)
    self.assertFalse(state['State']['Running'])
        
    p.remove_container(c, 1)
    with self.assertRaises(HTTPError) as e:
      p.docker_client.inspect_container(c)
      
    self.assertEqual(str(e.exception), '404 Client Error: Not Found')
    
  def testBuildImage(self):
    dockerfile = """
      FROM ubuntu
      MAINTAINER test
      """
    p = py_backend.PyBackend()
    image_id = p.build_image(fileobj=StringIO.StringIO(dockerfile))[0]
    self.assertEqual(p.inspect_image(image_id)['author'], 'test') 

    p.remove_image(image_id)
    with self.assertRaises(HTTPError) as e:
      p.inspect_image(image_id)

  #@unittest.skip("skipping")  
  def testGetIpAddress(self):
    # TODO: image_id will change
    p = py_backend.PyBackend()
    
    c = p.run_container(utils.findImage('ubuntu'), {'command': 'ps aux'})

    self.assertIsNotNone(c)    
    
    self.assertIsNotNone(p.get_ip_address(c))
    
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_service
import unittest, sys, yaml
import docker
sys.path.append('.')
from maestro import service, utils
from requests.exceptions import HTTPError

utils.setQuiet(True)

class TestContainer(unittest.TestCase):
  def setUp(self):
    self.mix = service.Service('fixtures/default.yml')
    self.mix.build()
    
  def tearDown(self):
    self.mix.destroy(timeout=1)
  
  #@unittest.skip("skipping")  
  def testBuild(self):
    env = yaml.load(self.mix.dump())
    self._configCheck(env)   

  #@unittest.skip("Skipping")
  def testBuildDockerfile(self):
    mix = service.Service('fixtures/dockerfile.yml')
    mix.build()
    env = yaml.load(mix.dump())
        
    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      self.assertIsNotNone(state)
      self.assertIn(container, ['test_server_1', 'test_server_2'])

      self.assertEqual(state['State']['ExitCode'], 0)

      if container == 'test_server_1':
        self.assertNotEqual(state['Config']['Image'], 'ubuntu')
        self.assertEqual(state['Path'], 'ns')
        self.assertEqual(state['Args'][0], '-l')
        
      #elif container == 'test_server_2':
      #  self.assertNotEqual(state['Config']['Image'], 'ubuntu')
       # self.assertEqual(state['Path'], 'ls')
       # self.assertEqual(state['Args'][0], '-l')  

    mix.destroy(timeout=1)
        
  
  #@unittest.skip("skipping")
  def testPorts(self):
    env = yaml.load(self.mix.dump())
    self.mix.save()
    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      self.assertIsNotNone(state)
      if container == 'test_server_1':
        self.assertIn('8080', state['NetworkSettings']['PortMapping']['Tcp'])
      elif container == 'test_server_2':
        self.assertEqual(state['NetworkSettings']['PortMapping']['Tcp'], {})
      else:
        # Shouldn't get here
        self.assertFalse(True)
  
  #@unittest.skip("skipping")
  def testDestroy(self):
    mix = service.Service('fixtures/default.yml')
    mix.build()
   
    env = yaml.load(mix.dump())
    mix.destroy(timeout=1)

    for container in env['containers']:
      with self.assertRaises(HTTPError) as e:
        docker.Client().inspect_container(env['containers'][container]['container_id'])

      self.assertEqual(str(e.exception), '404 Client Error: Not Found')
  
  #@unittest.skip("skipping")  
  def testSave(self):
    self.mix.save()
    with open('environment.yml', 'r') as input_file:
      env = yaml.load(input_file)

    self._configCheck(env)  

  #@unittest.skip("skipping")
  def testDependencyEnv(self):
    mix = service.Service('fixtures/count.yml')
        
    mix.build()
    
    # Verify that all three services are running
    env = yaml.load(mix.dump())    
    
    self.assertEqual(len(env['containers']), 4)

    state = docker.Client().inspect_container(env['containers']['service_post']['container_id'])
    #self.assertIn("SERVICE1", state['Config']['Env'])
      
    mix.destroy(timeout=1)
  
  #@unittest.skip("skipping")
  def testCount(self):
    mix = service.Service('fixtures/count.yml')
        
    mix.build(180)
    
    # Verify that all three services are running
    env = yaml.load(mix.dump())    
    
    self.assertEqual(len(env['containers']), 4)

    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      #Verify the containers are running
      self.assertTrue(state['State']['Running'])
      self.assertEqual(state['State']['ExitCode'], 0)
    
    mix.destroy(timeout=1)

  #@unittest.skip("skipping")
  def testRequire(self):
    mix = service.Service('fixtures/require.yml')
    
    # Verify that it determined the correct start order
    start_order = mix.start_order
    self.assertEqual(start_order[0], 'test_server_2')
    self.assertEqual(start_order[1], 'test_server_1')
    self.assertEqual(start_order[2], 'test_server_3')
    
    mix.build()
    
    # Verify that all three services are running
    env = yaml.load(mix.dump())    
    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      #Verify the containers are running
      self.assertTrue(state['State']['Running'])
      self.assertEqual(state['State']['ExitCode'], 0)
    
    mix.destroy(timeout=1)

  #@unittest.skip("skipping")
  def testStop(self):
    mix = service.Service('fixtures/startstop.yml')
    mix.build()
    
    env = yaml.load(mix.dump())    
    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      #Verify the containers are running
      self.assertTrue(state['State']['Running'])
      self.assertEqual(state['State']['ExitCode'], 0)
    
    mix.stop(timeout=1)
    env = yaml.load(mix.dump())    
    
    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      #Verify the containers are stopped 
      self.assertFalse(state['State']['Running'])
      self.assertNotEqual(state['State']['ExitCode'], 0)

    # restart the environment and then stop one of the containers
    mix.start()
    mix.stop('test_server_2', timeout=1)

    #Verify that test_server_2 is stopped
    state = docker.Client().inspect_container(env['containers']['test_server_2']['container_id'])      
    self.assertFalse(state['State']['Running'])
    self.assertNotEqual(state['State']['ExitCode'], 0)

    #But test_server_1 should still be running
    state = docker.Client().inspect_container(env['containers']['test_server_1']['container_id'])      
    self.assertTrue(state['State']['Running'])
    self.assertEqual(state['State']['ExitCode'], 0)

    mix.destroy(timeout=1)

  #@unittest.skip("skipping")
  def testStart(self):  
    mix = service.Service('fixtures/startstop.yml')
    mix.build()
    
    mix.stop(timeout=1)
    env = yaml.load(mix.dump())    
    
    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      # Verify the containers are stopped
      self.assertFalse(state['State']['Running'])
      self.assertNotEqual(state['State']['ExitCode'], 0)
    
    mix.start()
    env = yaml.load(mix.dump())    
    
    for container in env['containers']:
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])
      
      # Verify the containers are running again
      self.assertTrue(state['State']['Running'])
      self.assertEqual(state['State']['ExitCode'], 0)
    
    mix.stop(timeout=1)
    mix.start('test_server_1')

    #Verify that test_server_2 is still stopped
    state = docker.Client().inspect_container(env['containers']['test_server_2']['container_id'])      
    self.assertFalse(state['State']['Running'])
    self.assertNotEqual(state['State']['ExitCode'], 0)

    #But test_server_1 should now be running
    state = docker.Client().inspect_container(env['containers']['test_server_1']['container_id'])      
    self.assertTrue(state['State']['Running'])
    self.assertEqual(state['State']['ExitCode'], 0)

    mix.destroy(timeout=1)
  
  #@unittest.skip("skipping")
  def testStatus(self):
    mix = service.Service('fixtures/startstop.yml')
    mix.build()
    
    status = mix.ps() 

    lines = status.split("\n")
    # Skip over the headers
    del(lines[0])
    for line in lines:
      if len(line) > 0:
        self.assertIn(line[14:29].rstrip(),  ['test_server_1', 'test_server_2'])
        self.assertEqual(line[77:87].rstrip(), "Running")

    mix.destroy(timeout=1)

    status = mix.ps() 

    lines = status.split("\n")
    # Skip over the headers
    del(lines[0])
    for line in lines:
      if len(line) > 0:
        self.assertIn(line[14:29].rstrip(),  ['test_server_1', 'test_server_2'])
        self.assertEqual(line[77:87].rstrip(), "Destroyed")

  #@unittest.skip("skipping")
  def testLoad(self):
    self.mix.save()
    mix = service.Service(environment = 'environment.yml')
    
    env = yaml.load(mix.dump())    
    
    self._configCheck(env)    

  #@unittest.skip("skipping")
  def testRun(self):
    # Test the default command run
    container = self.mix.run("test_server_1")
    state = docker.Client().inspect_container(container.state['container_id'])
    self.assertEqual(state['State']['ExitCode'], 0)
    self.assertNotEqual(state['Config']['Image'], 'ubuntu')
    self.assertEqual(state['Path'], 'ps')
    
    # Test run of an overridden command 
    container = self.mix.run("test_server_1", "uptime")
    state = docker.Client().inspect_container(container.state['container_id'])
    self.assertEqual(state['State']['ExitCode'], 0)
    self.assertEqual(state['Path'], 'uptime')


  def _configCheck(self, env):
    self.assertIsNotNone(env)
    
    for container in env['containers']:
      self.assertIn(container, ['test_server_1', 'test_server_2'])
      
      state = docker.Client().inspect_container(env['containers'][container]['container_id'])

      self.assertEqual(state['State']['ExitCode'], 0)

      if container == 'test_server_1':
        self.assertEqual(state['Path'], 'ps')
        self.assertEqual(state['Args'][0], 'aux')
        self.assertEqual(state['Config']['Hostname'], 'test_server_1')
        self.assertEqual(state['Config']['User'], 'root')
        self.assertTrue(state['Config']['OpenStdin'])
        self.assertTrue(state['Config']['Tty'])
        self.assertEqual(state['Config']['Memory'], 2560000)
        self.assertIn("ENV_VAR=testing", state['Config']['Env'])
        self.assertIn("8.8.8.8", state['Config']['Dns'])
        
      elif container == 'test_server_2':
        self.assertEqual(state['Path'], 'ls')
        self.assertEqual(state['Args'][0], '-l')  
        self.assertEqual(state['Config']['Hostname'], 'test_server_2')
      
if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = test_template
import unittest, sys, yaml, os

sys.path.append('.')
from maestro import template, utils, exceptions

utils.setQuiet(True)

class TestTemplate(unittest.TestCase):

  def testBuild(self):
    # Test correct build    
    config = self._loadFixture("valid_base.yml")
    # This will create a template named test.service.template_test:0.1
    t = template.Template('template_test', config, 'test.service', '0.1')
    self.assertTrue(t.build())

    # Verify the image really exists with docker.
    self.assertIsNotNone(utils.findImage(t.full_name(), t.version))
    t.destroy()

    # Test correct build  with a tag
    config = self._loadFixture("valid_base_tag.yml")
    t = template.Template('template_test', config, 'test.service', '0.1')
    self.assertTrue(t.build())
    self.assertIsNotNone(utils.findImage(t.full_name(), t.version))
    t.destroy()

    # Test invalid base image    
    config = self._loadFixture("invalid_base.yml")    
    t = template.Template('template_test', config, 'test.service', '0.1')
    with self.assertRaises(exceptions.TemplateError) as e:
      t.build()
    t.destroy()

    # Test no base image specified
    config = self._loadFixture("no_base.yml")    
    t = template.Template('template_test', config, 'test.service', '0.1')
    with self.assertRaises(exceptions.TemplateError) as e:
      t.build()
    t.destroy()

  def testBuildDockerfile(self):
    # Test correct build using a minimal Dockerfile
    config = self._loadFixture("valid_dockerfile.yml")     
    t = template.Template('template_test', config, 'test.service', '0.1')
    self.assertTrue(t.build())
    t.destroy()

    # Test error on incorrectly formatted Dockerfile
    config = self._loadFixture("invalid_dockerfile.yml")    
    t = template.Template('template_test', config, 'test.service', '0.1')
    with self.assertRaises(exceptions.TemplateError) as e:
      t.build()
    t.destroy()

    # Test error on incorrect format for buildspec
    config = self._loadFixture("invalid_buildspec.yml") 
    t = template.Template('template_test', config, 'test.service', '0.1')
    with self.assertRaises(exceptions.TemplateError) as e:
      t.build()
    t.destroy()

  def testBuildUrl(self):
    # Test correct build using a minimal Dockerfile
    config = self._loadFixture("valid_build_url.yml")
    t = template.Template('template_test', config, 'test.service', '0.1')
    self.assertTrue(t.build())
    t.destroy()

  def testMount(self):
    config = self._loadFixture("mount.yml")
    t = template.Template('template_test', config, 'test.service', '0.1')
    self.assertTrue(t.build())

    container = t.instantiate('template_test')
    container.run()
    self.assertIsNotNone(container.inspect()['Volumes']['/var/www'])
    container.destroy()
    t.destroy()

  def testInstantiate(self):
    config = self._loadFixture("valid_base.yml")
    t = template.Template('template_test', config, 'test.service', '0.1')
    self.assertTrue(t.build())

    container = t.instantiate('template_test')
    container.run()
    self.assertIsNotNone(container.get_ip_address())
    container.destroy()
    t.destroy()

  def testDestroy(self):    
    config = self._loadFixture("valid_base.yml")
    t = template.Template('template_test', config, 'test.service', '0.1')
    self.assertTrue(t.build())

    # Make sure the image is there
    self.assertIsNotNone(self._findImage(t, t.full_name(), t.version))
    t.destroy()
    # Now make sure it's gone
    self.assertIsNone(self._findImage(t, t.full_name(), t.version))


  def _loadFixture(self, name):
    return yaml.load(file(os.path.join(os.path.dirname(__file__), "fixtures/template", name), "r"))

  def _findImage(self, t, name, tag="latest"):
    result =  t.backend.images(name=name)

    for image in result:
      if image['Tag'] == tag:
        return image['Id']
    return None
    
if __name__ == '__main__':
  unittest.main()
########NEW FILE########
