__FILENAME__ = chef
#Copyright 2010-2014 Miquel Torres <tobami@gmail.com>
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#
"""Node configuration and syncing
See http://wiki.opscode.com/display/chef/Anatomy+of+a+Chef+Run
"""
import os
import shutil
import json
from copy import deepcopy

from fabric.api import *
from fabric.contrib.files import exists
from fabric import colors
from fabric.utils import abort
from fabric.contrib.project import rsync_project

from littlechef import cookbook_paths, whyrun, lib, solo
from littlechef import LOGFILE, enable_logs as ENABLE_LOGS

# Path to local patch
basedir = os.path.abspath(os.path.dirname(__file__).replace('\\', '/'))


def save_config(node, force=False):
    """Saves node configuration
    if no nodes/hostname.json exists, or force=True, it creates one
    it also saves to tmp_node.json
    """
    filepath = os.path.join("nodes", env.host_string + ".json")
    tmp_filename = 'tmp_{0}.json'.format(env.host_string)
    files_to_create = [tmp_filename]
    if not os.path.exists(filepath) or force:
        # Only save to nodes/ if there is not already a file
        print "Saving node configuration to {0}...".format(filepath)
        files_to_create.append(filepath)
    for node_file in files_to_create:
        with open(node_file, 'w') as f:
            f.write(json.dumps(node, indent=4, sort_keys=True))
    return tmp_filename


def _get_ipaddress(node):
    """Adds the ipaddress attribute to the given node object if not already
    present and it is correctly given by ohai
    Returns True if ipaddress is added, False otherwise
    """
    if "ipaddress" not in node:
        with settings(hide('stdout'), warn_only=True):
            output = sudo('ohai -l warn ipaddress')
        if output.succeeded:
            try:
                node['ipaddress'] = json.loads(output)[0]
            except ValueError:
                abort("Could not parse ohai's output for ipaddress"
                      ":\n  {0}".format(output))
            return True
    return False


def sync_node(node):
    """Builds, synchronizes and configures a node.
    It also injects the ipaddress to the node's config file if not already
    existent.
    """
    if node.get('dummy') or 'dummy' in node.get('tags', []):
        lib.print_header("Skipping dummy: {0}".format(env.host))
        return False
    current_node = lib.get_node(node['name'])
    # Always configure Chef Solo
    solo.configure(current_node)
    ipaddress = _get_ipaddress(node)
    # Everything was configured alright, so save the node configuration
    # This is done without credentials, so that we keep the node name used
    # by the user and not the hostname or IP translated by .ssh/config
    filepath = save_config(node, ipaddress)
    try:
        # Synchronize the kitchen directory
        _synchronize_node(filepath, node)
        # Execute Chef Solo
        _configure_node()
    finally:
        _node_cleanup()
    return True


def _synchronize_node(configfile, node):
    """Performs the Synchronize step of a Chef run:
    Uploads all cookbooks, all roles and all databags to a node and add the
    patch for data bags

    Returns the node object of the node which is about to be configured,
    or None if this node object cannot be found.
    """
    msg = "Synchronizing nodes, environments, roles, cookbooks and data bags..."
    if env.parallel:
        msg = "[{0}]: {1}".format(env.host_string, msg)
    print(msg)
    # First upload node.json
    remote_file = '/etc/chef/node.json'
    put(configfile, remote_file, use_sudo=True, mode=400)
    with hide('stdout'):
        sudo('chown root:$(id -g -n root) {0}'.format(remote_file))
    # Remove local temporary node file
    os.remove(configfile)
    # Synchronize kitchen
    extra_opts = "-q"
    if env.follow_symlinks:
        extra_opts += " --copy-links"
    ssh_opts = ""
    if env.ssh_config_path:
        ssh_opts += " -F %s" % os.path.expanduser(env.ssh_config_path)
    if env.encrypted_data_bag_secret:
        put(env.encrypted_data_bag_secret,
            "/etc/chef/encrypted_data_bag_secret",
            use_sudo=True,
            mode=0600)
        sudo('chown root:$(id -g -n root) /etc/chef/encrypted_data_bag_secret')
    rsync_project(
        env.node_work_path,
        './cookbooks ./data_bags ./roles ./site-cookbooks ./environments',
        exclude=('*.svn', '.bzr*', '.git*', '.hg*'),
        delete=True,
        extra_opts=extra_opts,
        ssh_opts=ssh_opts
    )

    if env.sync_packages_dest_dir and env.sync_packages_local_dir:
      print("Uploading packages from {0} to remote server {2} directory "
        "{1}").format(env.sync_packages_local_dir, env.sync_packages_dest_dir, env.host_string)
      try:
        rsync_project(
          env.sync_packages_dest_dir,
          env.sync_packages_local_dir+"/*",
          exclude=('*.svn', '.bzr*', '.git*', '.hg*'),
          delete=True,
          extra_opts=extra_opts,
          ssh_opts=ssh_opts
        )
      except:
        print("Warning: package upload failed. Continuing cooking...")

    _add_environment_lib()  # NOTE: Chef 10 only


def build_dct(dic, keys, value):
    """Builds a dictionary with arbitrary depth out of a key list"""
    key = keys.pop(0)
    if len(keys):
        dic.setdefault(key, {})
        build_dct(dic[key], keys, value)
    else:
        # Transform cookbook default attribute strings into proper booleans
        if value == "false":
            value = False
        elif value == "true":
            value = True
        # It's a leaf, assign value
        dic[key] = deepcopy(value)


def update_dct(dic1, dic2):
    """Merges two dictionaries recursively
    dic2 will have preference over dic1

    """
    for key, val in dic2.items():
        if isinstance(val, dict):
            dic1.setdefault(key, {})
            update_dct(dic1[key], val)
        else:
            dic1[key] = val


def _add_automatic_attributes(node):
    """Adds some of Chef's automatic attributes:
        http://wiki.opscode.com/display/chef/Recipes#Recipes
        -CommonAutomaticAttributes

    """
    node['fqdn'] = node['name']
    node['hostname'] = node['fqdn'].split('.')[0]
    node['domain'] = ".".join(node['fqdn'].split('.')[1:])


def _add_merged_attributes(node, all_recipes, all_roles):
    """Merges attributes from cookbooks, node and roles

    Chef Attribute precedence:
    http://docs.opscode.com/essentials_cookbook_attribute_files.html#attribute-precedence
    LittleChef implements, in precedence order:
        - Cookbook default
        - Environment default
        - Role default
        - Node normal
        - Role override
        - Environment override

    NOTE: In order for cookbook attributes to be read, they need to be
        correctly defined in its metadata.json

    """
    # Get cookbooks from extended recipes
    attributes = {}
    for recipe in node['recipes']:
        # Find this recipe
        found = False
        for r in all_recipes:
            if recipe == r['name']:
                found = True
                for attr in r['attributes']:
                    if r['attributes'][attr].get('type') == "hash":
                        value = {}
                    else:
                        value = r['attributes'][attr].get('default')
                    # Attribute dictionaries are defined as a single
                    # compound key. Split and build proper dict
                    build_dct(attributes, attr.split("/"), value)
        if not found:
            error = "Could not find recipe '{0}' while ".format(recipe)
            error += "building node data bag for '{0}'".format(node['name'])
            abort(error)

    # Get default role attributes
    for role in node['roles']:
        for r in all_roles:
            if role == r['name']:
                update_dct(attributes, r.get('default_attributes', {}))

    # Get default environment attributes
    environment = lib.get_environment(node['chef_environment'])
    update_dct(attributes, environment.get('default_attributes', {}))

    # Get normal node attributes
    non_attribute_fields = [
        'id', 'name', 'role', 'roles', 'recipes', 'run_list', 'ipaddress']
    node_attributes = {}
    for key in node:
        if key in non_attribute_fields:
            continue
        node_attributes[key] = node[key]
    update_dct(attributes, node_attributes)

    # Get override role attributes
    for role in node['roles']:
        for r in all_roles:
            if role == r['name']:
                update_dct(attributes, r.get('override_attributes', {}))

    # Get override environment attributes
    update_dct(attributes, environment.get('override_attributes', {}))

    # Merge back to the original node object
    node.update(attributes)


def build_node_data_bag():
    """Builds one 'node' data bag item per file found in the 'nodes' directory

    Automatic attributes for a node item:
        'id': It adds data bag 'id', same as filename but with underscores
        'name': same as the filename
        'fqdn': same as the filename (LittleChef filenames should be fqdns)
        'hostname': Uses the first part of the filename as the hostname
            (until it finds a period) minus the .json extension
        'domain': filename minus the first part of the filename (hostname)
            minus the .json extension
    In addition, it will contain the merged attributes from:
        All default cookbook attributes corresponding to the node
        All attributes found in nodes/<item>.json file
        Default and override attributes from all roles
    """
    nodes = lib.get_nodes()
    node_data_bag_path = os.path.join('data_bags', 'node')
    # In case there are leftovers
    remove_local_node_data_bag()
    os.makedirs(node_data_bag_path)
    all_recipes = lib.get_recipes()
    all_roles = lib.get_roles()
    for node in nodes:
        # Dots are not allowed (only alphanumeric), substitute by underscores
        node['id'] = node['name'].replace('.', '_')

        # Build extended role list
        node['role'] = lib.get_roles_in_node(node)
        node['roles'] = node['role'][:]
        for role in node['role']:
            node['roles'].extend(lib.get_roles_in_role(role))
        node['roles'] = list(set(node['roles']))

        # Build extended recipe list
        node['recipes'] = lib.get_recipes_in_node(node)
        # Add recipes found inside each roles in the extended role list
        for role in node['roles']:
            node['recipes'].extend(lib.get_recipes_in_role(role))
        node['recipes'] = list(set(node['recipes']))

        # Add node attributes
        _add_merged_attributes(node, all_recipes, all_roles)
        _add_automatic_attributes(node)

        # Save node data bag item
        with open(os.path.join(
                  'data_bags', 'node', node['id'] + '.json'), 'w') as f:
            f.write(json.dumps(node))


def remove_local_node_data_bag():
    """Removes generated 'node' data_bag locally"""
    node_data_bag_path = os.path.join('data_bags', 'node')
    if os.path.exists(node_data_bag_path):
        shutil.rmtree(node_data_bag_path)


def _remove_remote_node_data_bag():
    """Removes generated 'node' data_bag from the remote node"""
    node_data_bag_path = os.path.join(env.node_work_path, 'data_bags', 'node')
    if exists(node_data_bag_path):
        sudo("rm -rf {0}".format(node_data_bag_path))


def _node_cleanup():
    if env.loglevel is not "debug":
        with hide('running', 'stdout'):
            _remove_remote_node_data_bag()
            with settings(warn_only=True):
                sudo("rm '/etc/chef/node.json'")
                if env.encrypted_data_bag_secret:
                    sudo("rm '/etc/chef/encrypted_data_bag_secret'")


def _add_environment_lib():
    """Adds the chef_solo_envs cookbook, which provides a library that adds
    environment attribute compatibility for chef-solo v10
    NOTE: Chef 10 only

    """
    # Create extra cookbook dir
    lib_path = os.path.join(env.node_work_path, cookbook_paths[0],
                            'chef_solo_envs', 'libraries')
    with hide('running', 'stdout'):
        sudo('mkdir -p {0}'.format(lib_path))
    # Add environment patch to the node's cookbooks
    put(os.path.join(basedir, 'environment.rb'),
        os.path.join(lib_path, 'environment.rb'), use_sudo=True)


def _configure_node():
    """Exectutes chef-solo to apply roles and recipes to a node"""
    print("")
    msg = "Cooking..."
    if env.parallel:
        msg = "[{0}]: {1}".format(env.host_string, msg)
    print(msg)
    # Backup last report
    with settings(hide('stdout', 'warnings', 'running'), warn_only=True):
        sudo("mv {0} {0}.1".format(LOGFILE))
    # Build chef-solo command
    cmd = "RUBYOPT=-Ku chef-solo"
    if whyrun:
        cmd += " --why-run"
    cmd += ' -l {0} -j /etc/chef/node.json'.format(env.loglevel)
    if ENABLE_LOGS:
        cmd += ' | tee {0}'.format(LOGFILE)
    if env.loglevel == "debug":
        print("Executing Chef Solo with the following command:\n"
              "{0}".format(cmd))
    with settings(hide('warnings', 'running'), warn_only=True):
        output = sudo(cmd)
    if (output.failed or "FATAL: Stacktrace dumped" in output or
            ("Chef Run complete" not in output and
             "Report handlers complete" not in output)):
        if 'chef-solo: command not found' in output:
            print(
                colors.red(
                    "\nFAILED: Chef Solo is not installed on this node"))
            print(
                "Type 'fix node:{0} deploy_chef' to install it".format(
                    env.host))
            abort("")
        else:
            print(colors.red(
                "\nFAILED: chef-solo could not finish configuring the node\n"))
            import sys
            sys.exit(1)
    else:
        msg = "\n"
        if env.parallel:
            msg += "[{0}]: ".format(env.host_string)
        msg += "SUCCESS: Node correctly configured"
        print(colors.green(msg))

########NEW FILE########
__FILENAME__ = exceptions
#Copyright 2010-2014 Miquel Torres <tobami@gmail.com>
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#


class FileNotFoundError(Exception):
    pass

########NEW FILE########
__FILENAME__ = lib
#Copyright 2010-2013 Miquel Torres <tobami@gmail.com>
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#
"""Library for parsing and printing role, cookbook and node information"""
import os
import json
import subprocess
import imp

from fabric import colors
from fabric.api import env
from fabric.contrib.console import confirm
from fabric.utils import abort

from littlechef import cookbook_paths
from littlechef.exceptions import FileNotFoundError

knife_installed = True


def _resolve_hostname(name):
    """Returns resolved hostname using the ssh config"""
    if env.ssh_config is None:
        return name
    elif not os.path.exists(os.path.join("nodes", name + ".json")):
        resolved_name = env.ssh_config.lookup(name)['hostname']
        if os.path.exists(os.path.join("nodes", resolved_name + ".json")):
            name = resolved_name
    return name


def get_env_host_string():
    if not env.host_string:
        abort('no node specified\nUsage: fix node:<MYNODES> <COMMAND>')
    if '@' in env.host_string:
        env.user = env.host_string.split('@')[0]
    return _resolve_hostname(env.host_string)


def env_from_template(name):
    """Returns a basic environment structure"""
    return {
        "name": name,
        "default_attributes": {},
        "json_class": "Chef::Environment",
        "chef_type": "environment",
        "description": "",
        "cookbook_versions": {}
    }


def get_environment(name):
    """Returns a JSON environment file as a dictionary"""
    if name == "_default":
        return env_from_template(name)
    filename = os.path.join("environments", name + ".json")
    try:
        with open(filename) as f:
            try:
                return json.loads(f.read())
            except ValueError as e:
                msg = 'LittleChef found the following error in'
                msg += ' "{0}":\n                {1}'.format(filename, str(e))
                abort(msg)
    except IOError:
        raise FileNotFoundError('File {0} not found'.format(filename))


def get_environments():
    """Gets all environments found in the 'environments' directory"""
    envs = []
    for root, subfolders, files in os.walk('environments'):
        for filename in files:
            if filename.endswith(".json"):
                path = os.path.join(
                    root[len('environments'):], filename[:-len('.json')])
                envs.append(get_environment(path))
    return sorted(envs, key=lambda x: x['name'])


def get_node(name, merged=False):
    """Returns a JSON node file as a dictionary"""
    if merged:
        node_path = os.path.join("data_bags", "node", name.replace('.', '_') + ".json")
    else:
        node_path = os.path.join("nodes", name + ".json")
    if os.path.exists(node_path):
        # Read node.json
        with open(node_path, 'r') as f:
            try:
                node = json.loads(f.read())
            except ValueError as e:
                msg = 'LittleChef found the following error in'
                msg += ' "{0}":\n                {1}'.format(node_path, str(e))
                abort(msg)
    else:
        print "Creating new node file '{0}.json'".format(name)
        node = {'run_list': []}
    # Add node name so that we can tell to which node it is
    node['name'] = name
    if not node.get('chef_environment'):
        node['chef_environment'] = '_default'
    return node


def get_nodes(environment=None):
    """Gets all nodes found in the nodes/ directory"""
    if not os.path.exists('nodes'):
        return []
    nodes = []
    for filename in sorted(
            [f for f in os.listdir('nodes')
             if (not os.path.isdir(f)
                 and f.endswith(".json") and not f.startswith('.'))]):
        fqdn = ".".join(filename.split('.')[:-1])  # Remove .json from name
        node = get_node(fqdn)
        if environment is None or node.get('chef_environment') == environment:
            nodes.append(node)
    return nodes


def get_nodes_with_role(role_name, environment=None):
    """Get all nodes which include a given role,
    prefix-searches are also supported

    """
    prefix_search = role_name.endswith("*")
    if prefix_search:
        role_name = role_name.rstrip("*")
    for n in get_nodes(environment):
        roles = get_roles_in_node(n, recursive=True)
        if prefix_search:
            if any(role.startswith(role_name) for role in roles):
                yield n
        else:
            if role_name in roles:
                yield n


def get_nodes_with_tag(tag, environment=None, include_guests=False):
    """Get all nodes which include a given tag"""
    nodes = get_nodes(environment)
    nodes_mapping = dict((n['name'], n) for n in nodes)
    for n in nodes:
        if tag in n.get('tags', []):
            # Remove from node mapping so it doesn't get added twice by
            # guest walking below
            try:
                del nodes_mapping[n['fqdn']]
            except KeyError:
                pass
            yield n
            # Walk guest if it is a host
            if include_guests and n.get('virtualization', {}).get('role') == 'host':
                for guest in n['virtualization']['guests']:
                    try:
                        yield nodes_mapping[guest['fqdn']]
                    except KeyError:
                        # we ignore guests which are not in the same
                        # chef environments than their hosts for now
                        pass


def get_nodes_with_recipe(recipe_name, environment=None):
    """Get all nodes which include a given recipe,
    prefix-searches are also supported

    """
    prefix_search = recipe_name.endswith("*")
    if prefix_search:
        recipe_name = recipe_name.rstrip("*")
    for n in get_nodes(environment):
        recipes = get_recipes_in_node(n)
        for role in get_roles_in_node(n, recursive=True):
            recipes.extend(get_recipes_in_role(role))
        if prefix_search:
            if any(recipe.startswith(recipe_name) for recipe in recipes):
                yield n
        else:
            if recipe_name in recipes:
                yield n


def print_node(node, detailed=False):
    """Pretty prints the given node"""
    nodename = node['name']
    print(colors.yellow("\n" + nodename))
    # Roles
    if detailed:
        for role in get_roles_in_node(node):
            print_role(_get_role(role), detailed=False)
    else:
        print('  Roles: {0}'.format(", ".join(get_roles_in_node(node))))
    # Recipes
    if detailed:
        for recipe in get_recipes_in_node(node):
            print "  Recipe:", recipe
            print "    attributes: {0}".format(node.get(recipe, ""))
    else:
        print('  Recipes: {0}'.format(", ".join(get_recipes_in_node(node))))
    # Node attributes
    print "  Node attributes:"
    for attribute in node.keys():
        if attribute == "run_list" or attribute == "name":
            continue
        print "    {0}: {1}".format(attribute, node[attribute])


def print_nodes(nodes, detailed=False):
    """Prints all the given nodes"""
    found = 0
    for node in nodes:
        found += 1
        print_node(node, detailed=detailed)
    print("\nFound {0} node{1}".format(found, "s" if found != 1 else ""))


def _generate_metadata(path, cookbook_path, name):
    """Checks whether metadata.rb has changed and regenerate metadata.json"""
    global knife_installed
    if not knife_installed:
        return
    metadata_path_rb = os.path.join(path, 'metadata.rb')
    metadata_path_json = os.path.join(path, 'metadata.json')
    if (os.path.exists(metadata_path_rb) and
            (not os.path.exists(metadata_path_json) or
             os.stat(metadata_path_rb).st_mtime >
             os.stat(metadata_path_json).st_mtime)):
        error_msg = "Warning: metadata.json for {0}".format(name)
        error_msg += " in {0} is older that metadata.rb".format(cookbook_path)
        error_msg += ", cookbook attributes could be out of date\n\n"
        try:
            proc = subprocess.Popen(
                ['knife', 'cookbook', 'metadata', '-o', cookbook_path, name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            resp, error = proc.communicate()
            if ('ERROR:' in resp or 'FATAL:' in resp
                    or 'Generating metadata for' not in resp):
                if("No user specified, pass via -u or specifiy 'node_name'"
                        in error):
                    error_msg += "You need to have an up-to-date (>=0.10.x)"
                    error_msg += " version of knife installed locally in order"
                    error_msg += " to generate metadata.json.\nError "
                else:
                    error_msg += "Unkown error "
                error_msg += "while executing knife to generate "
                error_msg += "metadata.json for {0}".format(path)
                print(error_msg)
                print resp
            if env.loglevel == 'debug':
                print "\n".join(resp.split("\n")[:2])
        except OSError:
            knife_installed = False
            error_msg += "If you locally install Chef's knife tool, LittleChef"
            error_msg += " will regenerate metadata.json files automatically\n"
            print(error_msg)
        else:
            print("Generated metadata.json for {0}\n".format(path))


def get_recipes_in_cookbook(name):
    """Gets the name of all recipes present in a cookbook
    Returns a list of dictionaries

    """
    recipes = {}
    path = None
    cookbook_exists = False
    metadata_exists = False
    for cookbook_path in cookbook_paths:
        path = os.path.join(cookbook_path, name)
        path_exists = os.path.exists(path)
        # cookbook exists if present in any of the cookbook paths
        cookbook_exists = cookbook_exists or path_exists
        if not path_exists:
            continue

        _generate_metadata(path, cookbook_path, name)

        # Now try to open metadata.json
        try:
            with open(os.path.join(path, 'metadata.json'), 'r') as f:
                try:
                    cookbook = json.loads(f.read())
                except ValueError as e:
                    msg = "Little Chef found the following error in your"
                    msg += " {0} file:\n  {1}".format(
                        os.path.join(path, 'metadata.json'), e)
                    abort(msg)
                # Add each recipe defined in the cookbook
                metadata_exists = True
                recipe_defaults = {
                    'description': '',
                    'version': cookbook.get('version'),
                    'dependencies': cookbook.get('dependencies', {}).keys(),
                    'attributes': cookbook.get('attributes', {})
                }
                for recipe in cookbook.get('recipes', []):
                    recipes[recipe] = dict(
                        recipe_defaults,
                        name=recipe,
                        description=cookbook['recipes'][recipe]
                    )
            # Cookbook metadata.json was found, don't try next cookbook path
            # because metadata.json in site-cookbooks has preference
            break
        except IOError:
            # metadata.json was not found, try next cookbook_path
            pass
    if not cookbook_exists:
        abort('Unable to find cookbook "{0}"'.format(name))
    elif not metadata_exists:
        abort('Cookbook "{0}" has no metadata.json'.format(name))
    # Add recipes found in the 'recipes' directory but not listed
    # in the metadata
    for cookbook_path in cookbook_paths:
        recipes_dir = os.path.join(cookbook_path, name, 'recipes')
        if not os.path.isdir(recipes_dir):
            continue
        for basename in os.listdir(recipes_dir):
            fname, ext = os.path.splitext(basename)
            if ext != '.rb':
                continue
            if fname != 'default':
                recipe = '%s::%s' % (name, fname)
            else:
                recipe = name
            if recipe not in recipes:
                recipes[recipe] = dict(recipe_defaults, name=recipe)
    # When a recipe has no default recipe (libraries?),
    # add one so that it is listed
    if not recipes:
        recipes[name] = dict(
            recipe_defaults,
            name=name,
            description='This cookbook has no default recipe'
        )
    return recipes.values()


def get_recipes_in_role(rolename):
    """Gets all recipes defined in a role's run_list"""
    recipes = get_recipes_in_node(_get_role(rolename))
    return recipes


def get_recipes_in_node(node):
    """Gets the name of all recipes present in the run_list of a node"""
    recipes = []
    for elem in node.get('run_list', []):
        if elem.startswith("recipe"):
            recipe = elem.split('[')[1].split(']')[0]
            recipes.append(recipe)
    return recipes


def get_recipes():
    """Gets all recipes found in the cookbook directories"""
    dirnames = set()
    for path in cookbook_paths:
        dirnames.update([d for d in os.listdir(path) if os.path.isdir(
                            os.path.join(path, d)) and not d.startswith('.')])
    recipes = []
    for dirname in dirnames:
        recipes.extend(get_recipes_in_cookbook(dirname))
    return sorted(recipes, key=lambda x: x['name'])


def print_recipe(recipe):
    """Pretty prints the given recipe"""
    print(colors.yellow("\n{0}".format(recipe['name'])))
    print "  description:  {0}".format(recipe['description'])
    print "  version:      {0}".format(recipe['version'])
    print "  dependencies: {0}".format(", ".join(recipe['dependencies']))
    print "  attributes:   {0}".format(", ".join(recipe['attributes']))


def get_roles_in_role(rolename):
    """Gets all roles defined in a role's run_list"""
    return get_roles_in_node(_get_role(rolename))


def get_roles_in_node(node, recursive=False, depth=0):
    """Returns a list of roles found in the run_list of a node
    * recursive: True feches roles recursively
    * depth: Keeps track of recursion depth

    """
    LIMIT = 5
    roles = []
    for elem in node.get('run_list', []):
        if elem.startswith("role"):
            role = elem.split('[')[1].split(']')[0]
            if role not in roles:
                roles.append(role)
                if recursive and depth <= LIMIT:
                    roles.extend(get_roles_in_node(_get_role(role),
                                                   recursive=True,
                                                   depth=depth + 1))
    return list(set(roles))


def _get_role(rolename):
    """Reads and parses a file containing a role"""
    path = os.path.join('roles', rolename + '.json')
    if not os.path.exists(path):
        abort("Couldn't read role file {0}".format(path))
    with open(path, 'r') as f:
        try:
            role = json.loads(f.read())
        except ValueError as e:
            msg = "Little Chef found the following error in your"
            msg += " {0}.json file:\n  {1}".format(rolename, str(e))
            abort(msg)
        role['fullname'] = rolename
        return role


def get_roles():
    """Gets all roles found in the 'roles' directory"""
    roles = []
    for root, subfolders, files in os.walk('roles'):
        for filename in files:
            if filename.endswith(".json"):
                path = os.path.join(
                    root[len('roles'):], filename[:-len('.json')])
                roles.append(_get_role(path))
    return sorted(roles, key=lambda x: x['fullname'])


def print_role(role, detailed=True):
    """Pretty prints the given role"""
    if detailed:
        print(colors.yellow(role.get('fullname')))
    else:
        print("  Role: {0}".format(role.get('fullname')))
    if detailed:
        print("    description: {0}".format(role.get('description')))
    if 'default_attributes' in role:
        print("    default_attributes:")
        _pprint(role['default_attributes'])
    if 'override_attributes' in role:
        print("    override_attributes:")
        _pprint(role['override_attributes'])
    if detailed:
        print("    run_list: {0}".format(role.get('run_list')))
    print("")


def print_plugin_list():
    """Prints a list of available plugins"""
    print("List of available plugins:")
    for plugin in get_plugins():
        _pprint(plugin)


def get_plugins():
    """Gets available plugins by looking into the plugins/ directory"""
    if os.path.exists('plugins'):
        for filename in sorted([f for f in os.listdir('plugins')
                if not os.path.isdir(f) and f.endswith(".py")]):
            plugin_name = filename[:-3]
            try:
                plugin = import_plugin(plugin_name)
            except SystemExit as e:
                description = "Plugin has a syntax error"
            else:
                description = plugin.__doc__ or "No description found"
            yield {plugin_name: description}


def import_plugin(name):
    """Imports plugin python module"""
    path = os.path.join("plugins", name + ".py")
    try:
        with open(path, 'rb') as f:
            try:
                plugin = imp.load_module(
                    "p_" + name, f, name + '.py',
                    ('.py', 'rb', imp.PY_SOURCE)
                )
            except SyntaxError as e:
                error = "Found plugin '{0}', but it seems".format(name)
                error += " to have a syntax error: {0}".format(str(e))
                abort(error)
    except IOError:
        abort("Sorry, could not find '{0}.py' in the plugin directory".format(
              name))
    return plugin


def get_cookbook_path(cookbook_name):
    """Returns path to the cookbook for the given cookbook name"""
    for cookbook_path in cookbook_paths:
        path = os.path.join(cookbook_path, cookbook_name)
        if os.path.exists(path):
            return path
    raise IOError('Can\'t find cookbook with name "{0}"'.format(cookbook_name))


def global_confirm(question, default=True):
    """Shows a confirmation that applies to all hosts
    by temporarily disabling parallel execution in Fabric
    """
    if env.abort_on_prompts:
        return True
    original_parallel = env.parallel
    env.parallel = False
    result = confirm(question, default)
    env.parallel = original_parallel
    return result


def _pprint(dic):
    """Prints a dictionary with one indentation level"""
    for key, value in dic.items():
        print("        {0}: {1}".format(key, value))


def print_header(string):
    """Prints a colored header"""
    print(colors.yellow("\n== {0} ==".format(string)))


def get_margin(length):
    """Add enough tabs to align in two columns"""
    if length > 23:
        margin_left = "\t"
        chars = 1
    elif length > 15:
        margin_left = "\t\t"
        chars = 2
    elif length > 7:
        margin_left = "\t\t\t"
        chars = 3
    else:
        margin_left = "\t\t\t\t"
        chars = 4
    return margin_left

########NEW FILE########
__FILENAME__ = runner
#Copyright 2010-2014 Miquel Torres <tobami@gmail.com>
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#
"""LittleChef: Configuration Management using Chef Solo"""
import ConfigParser
import os
import sys
import json

from fabric.api import *
from fabric.contrib.console import confirm
from paramiko.config import SSHConfig as _SSHConfig

import littlechef
from littlechef import solo, lib, chef

# Fabric settings
import fabric
fabric.state.output['running'] = False
env.loglevel = littlechef.loglevel
env.verbose = littlechef.verbose
env.abort_on_prompts = littlechef.noninteractive
env.chef_environment = littlechef.chef_environment
env.node_work_path = littlechef.node_work_path

if littlechef.concurrency:
    env.output_prefix = True
    env.parallel = True
    env.pool_size = littlechef.concurrency
else:
    env.output_prefix = False

__testing__ = False


@hosts('setup')
def new_kitchen():
    """Create LittleChef directory structure (Kitchen)"""
    def _mkdir(d, content=""):
        if not os.path.exists(d):
            os.mkdir(d)
            # Add a README so that it can be added to version control
            readme_path = os.path.join(d, 'README')
            if not os.path.exists(readme_path):
                with open(readme_path, "w") as readme:
                    print >> readme, content
            print "{0}/ directory created...".format(d)

    content = "# The /nodes directory contains your nodes as JSON files "
    content += "representing a node.\n"
    content += "# Example node file `nodes/myfqdn.json`:\n"
    data = {
        "chef_environment": "production",
        "apt": {"cacher_port": 3143},
        "run_list": ["recipe[apt]"]
    }
    content += "{0}".format(json.dumps(data, indent=2))
    _mkdir("nodes", content)
    _mkdir("roles")
    _mkdir("data_bags")
    _mkdir("environments")
    for cookbook_path in littlechef.cookbook_paths:
        _mkdir(cookbook_path)
    # Add skeleton config file
    if not os.path.exists(littlechef.CONFIGFILE):
        with open(littlechef.CONFIGFILE, 'w') as configfh:
            print >> configfh, "[userinfo]"
            print >> configfh, "user = "
            print >> configfh, "password = "
            print >> configfh, "keypair-file = "
            print >> configfh, "ssh-config = "
            print >> configfh, "encrypted_data_bag_secret = "
            print >> configfh, "[kitchen]"
            print >> configfh, "node_work_path = /tmp/chef-solo/"
            print "{0} file created...".format(littlechef.CONFIGFILE)


def nodes_with_role(rolename):
    """Configures a list of nodes that have the given role in their run list"""
    nodes = [n['name'] for n in
             lib.get_nodes_with_role(rolename, env.chef_environment)]
    if not len(nodes):
        print("No nodes found with role '{0}'".format(rolename))
        sys.exit(0)
    return node(*nodes)


def nodes_with_recipe(recipename):
    """Configures a list of nodes that have the given recipe in their run list
    """
    nodes = [n['name'] for n in
             lib.get_nodes_with_recipe(recipename, env.chef_environment)]
    if not len(nodes):
        print("No nodes found with recipe '{0}'".format(recipename))
        sys.exit(0)
    return node(*nodes)


def nodes_with_tag(tag):
    """Sets a list of nodes that have the given tag assigned and calls node()"""
    nodes = lib.get_nodes_with_tag(tag, env.chef_environment,
                                   littlechef.include_guests)
    nodes = [n['name'] for n in nodes]
    if not len(nodes):
        print("No nodes found with tag '{0}'".format(tag))
        sys.exit(0)
    return node(*nodes)


@hosts('setup')
def node(*nodes):
    """Selects and configures a list of nodes. 'all' configures all nodes"""
    chef.build_node_data_bag()
    if not len(nodes) or nodes[0] == '':
        abort('No node was given')
    elif nodes[0] == 'all':
        # Fetch all nodes and add them to env.hosts
        for node in lib.get_nodes(env.chef_environment):
            env.hosts.append(node['name'])
        if not len(env.hosts):
            abort('No nodes found in /nodes/')
        message = "Are you sure you want to configure all nodes ({0})".format(
            len(env.hosts))
        if env.chef_environment:
            message += " in the {0} environment".format(env.chef_environment)
        message += "?"
        if not __testing__:
            if not lib.global_confirm(message):
                abort('Aborted by user')
    else:
        # A list of nodes was given
        env.hosts = list(nodes)
    env.all_hosts = list(env.hosts)  # Shouldn't be needed

    # Check whether another command was given in addition to "node:"
    if not(littlechef.__cooking__ and
            'node:' not in sys.argv[-1] and
            'nodes_with_role:' not in sys.argv[-1] and
            'nodes_with_recipe:' not in sys.argv[-1] and
            'nodes_with_tag:' not in sys.argv[-1]):
        # If user didn't type recipe:X, role:Y or deploy_chef,
        # configure the nodes
        with settings():
            execute(_node_runner)
        chef.remove_local_node_data_bag()


def _configure_fabric_for_platform(platform):
    """Configures fabric for a specific platform"""
    if platform == "freebsd":
        env.shell = "/bin/sh -c"


def _node_runner():
    """This is only used by node so that we can execute in parallel"""
    env.host_string = lib.get_env_host_string()
    node = lib.get_node(env.host_string)

    _configure_fabric_for_platform(node.get("platform"))

    if __testing__:
        print "TEST: would now configure {0}".format(env.host_string)
    else:
        lib.print_header("Configuring {0}".format(env.host_string))
        chef.sync_node(node)


def deploy_chef(gems="no", ask="yes", version="0.10", distro_type=None,
                distro=None, platform=None, stop_client='yes', method=None):
    """Install chef-solo on a node"""
    env.host_string = lib.get_env_host_string()
    deprecated_parameters = [distro_type, distro, platform]
    if any(param is not None for param in deprecated_parameters) or gems != 'no':
        print("DeprecationWarning: the parameters 'gems', distro_type',"
              " 'distro' and 'platform' will no longer be supported "
              "in future versions of LittleChef. Use 'method' instead")
    if distro_type is None and distro is None:
        distro_type, distro, platform = solo.check_distro()
    elif distro_type is None or distro is None:
        abort('Must specify both or neither of distro_type and distro')
    if method:
        if method not in ['omnibus', 'gentoo', 'pacman']:
            abort('Invalid omnibus method {0}. Supported methods are '
                  'omnibus, gentoo and pacman'.format(method))
        msg = "{0} using the {1} installer".format(version, method)
    else:
        if gems == "yes":
            msg = 'using gems for "{0}"'.format(distro)
        else:
            msg = '{0} using "{1}" packages'.format(version, distro)
    if method == 'omnibus' or ask == "no" or littlechef.noninteractive:
        print("Deploying Chef {0}...".format(msg))
    else:
        message = ('\nAre you sure you want to install Chef '
                   '{0} on node {1}?'.format(msg, env.host_string))
        if not confirm(message):
            abort('Aborted by user')

    _configure_fabric_for_platform(platform)

    if not __testing__:
        solo.install(distro_type, distro, gems, version, stop_client, method)
        solo.configure()

        # Build a basic node file if there isn't one already
        # with some properties from ohai
        with settings(hide('stdout'), warn_only=True):
            output = sudo('ohai -l warn')
        if output.succeeded:
            try:
                ohai = json.loads(output)
            except ValueError:
                abort("Could not parse ohai's output"
                      ":\n  {0}".format(output))
            node = {"run_list": []}
            for attribute in ["ipaddress", "platform", "platform_family",
                              "platform_version"]:
                if ohai.get(attribute):
                    node[attribute] = ohai[attribute]
            chef.save_config(node)


def recipe(recipe):
    """Apply the given recipe to a node
    Sets the run_list to the given recipe
    If no nodes/hostname.json file exists, it creates one

    """
    env.host_string = lib.get_env_host_string()
    lib.print_header(
        "Applying recipe '{0}' on node {1}".format(recipe, env.host_string))

    # Create configuration and sync node
    data = lib.get_node(env.host_string)
    data["run_list"] = ["recipe[{0}]".format(recipe)]
    if not __testing__:
        chef.sync_node(data)


def role(role):
    """Apply the given role to a node
    Sets the run_list to the given role
    If no nodes/hostname.json file exists, it creates one

    """
    env.host_string = lib.get_env_host_string()
    lib.print_header(
        "Applying role '{0}' to {1}".format(role, env.host_string))

    # Now create configuration and sync node
    data = lib.get_node(env.host_string)
    data["run_list"] = ["role[{0}]".format(role)]
    if not __testing__:
        chef.sync_node(data)


def ssh(name):
    """Executes the given command"""
    env.host_string = lib.get_env_host_string()
    print("\nExecuting the command '{0}' on node {1}...".format(
          name, env.host_string))
    # Execute remotely using either the sudo or the run fabric functions
    with settings(hide("warnings"), warn_only=True):
        if name.startswith("sudo "):
            sudo(name[5:])
        else:
            run(name)


def plugin(name):
    """Executes the selected plugin
    Plugins are expected to be found in the kitchen's 'plugins' directory

    """
    env.host_string = lib.get_env_host_string()
    plug = lib.import_plugin(name)
    lib.print_header("Executing plugin '{0}' on "
                     "{1}".format(name, env.host_string))
    node = lib.get_node(env.host_string)
    if node == {'run_list': []}:
        node['name'] = env.host_string
    plug.execute(node)
    print("Finished executing plugin")


@hosts('api')
def list_nodes():
    """List all configured nodes"""
    lib.print_nodes(lib.get_nodes(env.chef_environment))


@hosts('api')
def list_nodes_detailed():
    """Show a detailed list of all nodes"""
    lib.print_nodes(lib.get_nodes(env.chef_environment), detailed=True)


@hosts('api')
def list_nodes_with_recipe(recipe):
    """Show all nodes which have assigned a given recipe"""
    lib.print_nodes(lib.get_nodes_with_recipe(recipe, env.chef_environment))


@hosts('api')
def list_nodes_with_role(role):
    """Show all nodes which have assigned a given role"""
    lib.print_nodes(lib.get_nodes_with_role(role, env.chef_environment))


@hosts('api')
def list_envs():
    """List all environments"""
    for env in lib.get_environments():
        margin_left = lib.get_margin(len(env['name']))
        print("{0}{1}{2}".format(
            env['name'], margin_left,
            env.get('description', '(no description)')))


@hosts('api')
def list_nodes_with_tag(tag):
    """Show all nodes which have assigned a given tag"""
    lib.print_nodes(lib.get_nodes_with_tag(tag, env.chef_environment,
                                           littlechef.include_guests))


@hosts('api')
def list_recipes():
    """Show a list of all available recipes"""
    for recipe in lib.get_recipes():
        margin_left = lib.get_margin(len(recipe['name']))
        print("{0}{1}{2}".format(
            recipe['name'], margin_left, recipe['description']))


@hosts('api')
def list_recipes_detailed():
    """Show detailed information for all recipes"""
    for recipe in lib.get_recipes():
        lib.print_recipe(recipe)


@hosts('api')
def list_roles():
    """Show a list of all available roles"""
    for role in lib.get_roles():
        margin_left = lib.get_margin(len(role['fullname']))
        print("{0}{1}{2}".format(
            role['fullname'], margin_left,
            role.get('description', '(no description)')))


@hosts('api')
def list_roles_detailed():
    """Show detailed information for all roles"""
    for role in lib.get_roles():
        lib.print_role(role)


@hosts('api')
def list_plugins():
    """Show all available plugins"""
    lib.print_plugin_list()


def _check_appliances():
    """Looks around and return True or False based on whether we are in a
    kitchen
    """
    filenames = os.listdir(os.getcwd())
    missing = []
    for dirname in ['nodes', 'environments', 'roles', 'cookbooks', 'data_bags']:
        if (dirname not in filenames) or (not os.path.isdir(dirname)):
            missing.append(dirname)
    return (not bool(missing)), missing


def _readconfig():
    """Configures environment variables"""
    config = ConfigParser.SafeConfigParser()
    try:
        found = config.read(littlechef.CONFIGFILE)
    except ConfigParser.ParsingError as e:
        abort(str(e))
    if not len(found):
        try:
            found = config.read(['config.cfg', 'auth.cfg'])
        except ConfigParser.ParsingError as e:
            abort(str(e))
        if len(found):
            print('\nDeprecationWarning: deprecated config file name \'{0}\'.'
                  ' Use {1}'.format(found[0], littlechef.CONFIGFILE))
        else:
            abort('No {0} file found in the current '
                  'directory'.format(littlechef.CONFIGFILE))

    in_a_kitchen, missing = _check_appliances()
    missing_str = lambda m: ' and '.join(', '.join(m).rsplit(', ', 1))
    if not in_a_kitchen:
        abort("Couldn't find {0}. "
              "Are you executing 'fix' outside of a kitchen?\n"
              "To create a new kitchen in the current directory "
              " type 'fix new_kitchen'".format(missing_str(missing)))

    # We expect an ssh_config file here,
    # and/or a user, (password/keyfile) pair
    try:
        env.ssh_config_path = config.get('userinfo', 'ssh-config')
    except ConfigParser.NoSectionError:
        abort('You need to define a "userinfo" section'
              ' in the config file. Refer to the README for help '
              '(http://github.com/tobami/littlechef)')
    except ConfigParser.NoOptionError:
        env.ssh_config_path = None

    if env.ssh_config_path:
        env.ssh_config = _SSHConfig()
        env.ssh_config_path = os.path.expanduser(env.ssh_config_path)
        env.use_ssh_config = True
        try:
            env.ssh_config.parse(open(env.ssh_config_path))
        except IOError:
            abort("Couldn't open the ssh-config file "
                  "'{0}'".format(env.ssh_config_path))
        except Exception:
            abort("Couldn't parse the ssh-config file "
                  "'{0}'".format(env.ssh_config_path))
    else:
        env.ssh_config = None

    # check for a gateway
    try:
        env.gateway = config.get('connection', 'gateway')
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        env.gateway = None

    # Check for an encrypted_data_bag_secret file and set the env option
    try:
        env.encrypted_data_bag_secret = config.get('userinfo',
                                                   'encrypted_data_bag_secret')
    except ConfigParser.NoOptionError:
        env.encrypted_data_bag_secret = None

    if env.encrypted_data_bag_secret:
        env.encrypted_data_bag_secret = os.path.expanduser(
            env.encrypted_data_bag_secret)
        try:
            open(env.encrypted_data_bag_secret)
        except IOError as e:
            abort("Failed to open encrypted_data_bag_secret file at "
                  "'{0}'".format(env.encrypted_data_bag_secret))

    try:
        sudo_prefix = config.get('ssh', 'sudo_prefix', raw=True)
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        pass
    else:
        env.sudo_prefix = sudo_prefix

    try:
        env.user = config.get('userinfo', 'user')
    except ConfigParser.NoOptionError:
        if not env.ssh_config_path:
            msg = 'You need to define a user in the "userinfo" section'
            msg += ' of {0}. Refer to the README for help'
            msg += ' (http://github.com/tobami/littlechef)'
            abort(msg.format(littlechef.CONFIGFILE))
        user_specified = False
    else:
        user_specified = True

    try:
        env.password = config.get('userinfo', 'password') or None
    except ConfigParser.NoOptionError:
        pass

    try:
        #If keypair-file is empty, assign None or fabric will try to read key "
        env.key_filename = config.get('userinfo', 'keypair-file') or None
    except ConfigParser.NoOptionError:
        pass

    if (user_specified and not env.password and not env.key_filename
            and not env.ssh_config):
        abort('You need to define a password, keypair file, or ssh-config '
              'file in {0}'.format(littlechef.CONFIGFILE))

    # Node's Chef Solo working directory for storing cookbooks, roles, etc.
    try:
        env.node_work_path = os.path.expanduser(config.get('kitchen',
                                                'node_work_path'))
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        env.node_work_path = littlechef.node_work_path
    else:
        if not env.node_work_path:
            abort('The "node_work_path" option cannot be empty')

    # Follow symlinks
    try:
        env.follow_symlinks = config.getboolean('kitchen', 'follow_symlinks')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        env.follow_symlinks = False

    # Upload Directory
    try:
        env.sync_packages_dest_dir = config.get('sync-packages',
                                                'dest-dir')
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        env.sync_packages_dest_dir = None

    # Local Directory
    try:
        env.sync_packages_local_dir = config.get('sync-packages',
                                                 'local-dir')
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        env.sync_packages_local_dir = None

# Only read config if fix is being used and we are not creating a new kitchen
if littlechef.__cooking__:
    # Called from command line
    if env.chef_environment:
        print("\nEnvironment: {0}".format(env.chef_environment))
    if env.verbose:
        print("\nVerbose output on")
    if env.loglevel == "debug":
        print("\nDebug level on")
    if 'new_kitchen' not in sys.argv:
        _readconfig()
else:
    # runner module has been imported
    env.ssh_config = None
    env.follow_symlinks = False
    env.encrypted_data_bag_secret = None
    env.sync_packages_dest_dir = None
    env.sync_packages_local_dir = None

########NEW FILE########
__FILENAME__ = solo
#Copyright 2010-2014 Miquel Torres <tobami@gmail.com>
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#
"""Chef Solo deployment"""
import os
import re

from fabric.api import *
from fabric import colors
from fabric.contrib.files import append, exists, upload_template
from fabric.utils import abort

from littlechef import cookbook_paths
from littlechef import LOGFILE

# Path to local patch
BASEDIR = os.path.abspath(os.path.dirname(__file__).replace('\\', '/'))


def install(distro_type, distro, gems, version, stop_client, method):
    """Calls the appropriate installation function for the given distro"""
    if distro_type == "debian":
        if gems == "yes":
            _gem_apt_install()
        elif method == "omnibus":
            _omnibus_install(version=version)
        else:
            chef_versions = ["0.9", "0.10"]
            if version not in chef_versions:
                abort('Wrong Chef version specified. Valid versions are {0}'.format(
                    ", ".join(chef_versions)))
            _apt_install(distro, version, stop_client)
    elif distro_type == "rpm":
        if gems == "yes":
            _gem_rpm_install()
        elif method == "omnibus":
            _omnibus_install(version=version)
        else:
            _rpm_install()
    elif distro_type == "gentoo":
        _emerge_install()
    elif distro_type == "pacman":
        _gem_pacman_install()
    elif distro_type == "freebsd":
        _gem_ports_install()
    else:
        abort('wrong distro type: {0}'.format(distro_type))


def configure(current_node=None):
    """Deploy chef-solo specific files"""
    current_node = current_node or {}
    # Ensure that the /tmp/chef-solo/cache directory exist
    cache_dir = "{0}/cache".format(env.node_work_path)
    # First remote call, could go wrong
    try:
        cache_exists = exists(cache_dir)
    except EOFError as e:
        abort("Could not login to node, got: {0}".format(e))
    if not cache_exists:
        with settings(hide('running', 'stdout'), warn_only=True):
            output = sudo('mkdir -p {0}'.format(cache_dir))
        if output.failed:
            error = "Could not create {0} dir. ".format(env.node_work_path)
            error += "Do you have sudo rights?"
            abort(error)
    # Change ownership of /tmp/chef-solo/ so that we can rsync
    with hide('running', 'stdout'):
        with settings(warn_only=True):
            output = sudo(
                'chown -R {0} {1}'.format(env.user, env.node_work_path))
        if output.failed:
            error = "Could not modify {0} dir. ".format(env.node_work_path)
            error += "Do you have sudo rights?"
            abort(error)
    # Set up chef solo configuration
    logging_path = os.path.dirname(LOGFILE)
    if not exists(logging_path):
        sudo('mkdir -p {0}'.format(logging_path))
    if not exists('/etc/chef'):
        sudo('mkdir -p /etc/chef')
    # Set parameters and upload solo.rb template
    reversed_cookbook_paths = cookbook_paths[:]
    reversed_cookbook_paths.reverse()
    cookbook_paths_list = '[{0}]'.format(', '.join(
        ['"{0}/{1}"'.format(env.node_work_path, x) \
            for x in reversed_cookbook_paths]))
    data = {
        'node_work_path': env.node_work_path,
        'cookbook_paths_list': cookbook_paths_list,
        'environment': current_node.get('chef_environment', '_default'),
        'verbose': "true" if env.verbose else "false"
    }
    with settings(hide('everything')):
        try:
            upload_template(os.path.join(BASEDIR, 'solo.rb'), '/etc/chef/',
                            context=data, use_sudo=True, backup=False,
                            mode=0400)
        except SystemExit:
            error = ("Failed to upload '/etc/chef/solo.rb'\nThis "
                     "can happen when the deployment user does not have a "
                     "home directory, which is needed as a temporary location")
            abort(error)
    with hide('stdout'):
        sudo('chown root:$(id -g -n root) {0}'.format('/etc/chef/solo.rb'))


def check_distro():
    """Check that the given distro is supported and return the distro type"""
    def print_supported_distros(platform):
        supported_distros = (
            "Currently supported distros are:"
            " Debian, Ubuntu, RHEL (CentOS, RHEL, SL),"
            " Gentoo, Arch Linux or FreeBSD")
        print supported_distros
        abort("Unsupported distro '{0}'".format(platform))

    with settings(hide('warnings', 'running', 'stdout', 'stderr'),
                  warn_only=True):
        # use /bin/sh to determine our OS. FreeBSD doesn't have /bin/bash
        original_shell = env.shell
        env.shell = "/bin/sh -c"
        os_implementation = run('uname -o')
        if 'Linux' in os_implementation:
            env.shell = original_shell
            output = sudo('cat /etc/issue')
            if 'Debian GNU/Linux 5.0' in output:
                distro = "lenny"
                distro_type = "debian"
                platform = "debian"
            elif 'Debian GNU/Linux 6.0' in output:
                distro = "squeeze"
                distro_type = "debian"
                platform = "debian"
            elif 'Debian GNU/Linux 7' in output:
                distro = "wheezy"
                distro_type = "debian"
                platform = "debian"
            elif 'Ubuntu' in output:
                distro = sudo('lsb_release -cs')
                distro_type = "debian"
                platform = "ubuntu"
            elif 'CentOS' in output:
                distro = "CentOS"
                distro_type = "rpm"
                platform = "centos"
            elif 'Red Hat Enterprise Linux' in output:
                distro = "Red Hat"
                distro_type = "rpm"
                platform = "redhat"
            elif 'Scientific Linux' in output:
                distro = "Scientific Linux"
                distro_type = "rpm"
                platform = "scientific"
            elif 'This is \\n.\\O (\\s \\m \\r) \\t' in output:
                distro = "Gentoo"
                distro_type = "gentoo"
                platform = "gentoo"
            elif 'Arch Linux \\r  (\\n) (\\l)' in output:
                distro = "Arch Linux"
                distro_type = "pacman"
                platform = "arch"
            else:
                print_supported_distros(output)
        elif 'FreeBSD' in os_implementation:
            env.shell = "/bin/sh -c"
            distro = "FreeBSD"
            distro_type = "freebsd"
            platform = "freebsd"
        else:
            print_supported_distros(os_implementation)

    return distro_type, distro, platform


def _gem_install():
    """Install Chef from gems"""
    # Install RubyGems from Source
    rubygems_version = "1.8.10"
    ruby_version = "'~> 10.0'"
    run('wget http://production.cf.rubygems.org/rubygems/rubygems-{0}.tgz'
        .format(rubygems_version))
    run('tar zxf rubygems-{0}.tgz'.format(rubygems_version))
    with cd('rubygems-{0}'.format(rubygems_version)):
        sudo('ruby setup.rb --no-format-executable'.format(rubygems_version))
    sudo('rm -rf rubygems-{0} rubygems-{0}.tgz'.format(rubygems_version))
    sudo('gem install --no-rdoc --no-ri chef -v {0}'.format(ruby_version))


def _gem_apt_install():
    """Install Chef from gems for apt based distros"""
    with hide('stdout', 'running'):
        sudo('apt-get update')
    prefix = "DEBIAN_FRONTEND=noninteractive"
    packages = "ruby ruby-dev libopenssl-ruby irb build-essential wget"
    packages += " ssl-cert rsync"
    sudo('{0} apt-get --yes install {1}'.format(prefix, packages))
    _gem_install()


def _gem_rpm_install():
    """Install Chef from gems for rpm based distros"""
    _add_rpm_repos()
    needed_packages = "make ruby ruby-shadow gcc gcc-c++ ruby-devel wget rsync"
    with show('running'):
        sudo('yum -y install {0}'.format(needed_packages))
    _gem_install()


def _gem_pacman_install():
    """Install Chef from gems for pacman based distros"""
    with hide('stdout', 'running'):
        sudo('pacman -Syu --noconfirm')
    with show('running'):
        sudo('pacman -S --noconfirm ruby base-devel wget rsync')
    sudo('gem install --no-rdoc --no-ri chef')


def _gem_ports_install():
    """Install Chef from gems for FreeBSD"""
    with hide('stdout', 'running'):
        sudo('grep -q RUBY_VER /etc/make.conf || echo \'RUBY_VER=1.9\' >> /etc/make.conf')
        sudo('grep -q RUBY_DEFAULT_VER /etc/make.conf || echo \'RUBY_DEFAULT_VER=1.9\' >> /etc/make.conf')
    with show('running'):
        sudo('which -s rsync || pkg_add -r rsync')
        sudo('which -s perl || pkg_add -r perl')
        sudo('which -s m4 || pkg_add -r m4')
        sudo('which -s chef || (cd /usr/ports/sysutils/rubygem-chef && make -DBATCH install)')


def _omnibus_install(version):
    """Install Chef using the omnibus installer"""
    url = "https://www.opscode.com/chef/install.sh"
    with hide('stdout', 'running'):
        local("""python -c "import urllib; print urllib.urlopen('{0}').read()" > /tmp/install.sh""".format(url))
        put('/tmp/install.sh', '/tmp/install.sh')
    print("Downloading and installing Chef {0}...".format(version))
    with hide('stdout'):
        sudo("""bash /tmp/install.sh -v {0}""".format(version))


def _apt_install(distro, version, stop_client='yes'):
    """Install Chef for debian based distros"""
    with settings(hide('stdout', 'running')):
        with settings(hide('warnings'), warn_only=True):
            wget_is_installed = sudo('which wget')
            if wget_is_installed.failed:
                # Install wget
                print "Installing wget..."
                # we may not be able to install wget without updating first
                sudo('apt-get update')
                output = sudo('apt-get --yes install wget')
                if output.failed:
                    print(colors.red("Error while installing wget:"))
                    abort(output.lstrip("\\n"))
            rsync_is_installed = sudo('which rsync')
            if rsync_is_installed.failed:
                # Install rsync
                print "Installing rsync..."
                # we may not be able to install rsync without updating first
                sudo('apt-get update')
                output = sudo('apt-get --yes install rsync')
                if output.failed:
                    print(colors.red("Error while installing rsync:"))
                    abort(output.lstrip("\\n"))
        # Add Opscode Debian repo
        print("Setting up Opscode repository...")
        if version == "0.9":
            version = ""
        else:
            version = "-" + version
        append('opscode.list',
            'deb http://apt.opscode.com/ {0}{1} main'.format(distro, version),
                use_sudo=True)
        sudo('mv opscode.list /etc/apt/sources.list.d/')
        # Add repository GPG key
        gpg_key = "http://apt.opscode.com/packages@opscode.com.gpg.key"
        sudo('wget -qO - {0} | sudo apt-key add -'.format(gpg_key))
        # Load package list from new repository
        with settings(hide('warnings'), warn_only=True):
            output = sudo('apt-get update')
            if output.failed:
                print(colors.red(
                    "Error while executing 'apt-get install chef':"))
                abort(output)
        # Install Chef Solo
        print("Installing Chef Solo")
        # Ensure we don't get asked for the Chef Server
        command = "echo chef chef/chef_server_url select ''"
        command += " | debconf-set-selections"
        sudo(command)
        # Install package
        with settings(hide('warnings'), warn_only=True):
            output = sudo('apt-get --yes install ucf chef')
            if output.failed:
                print(colors.red(
                    "Error while executing 'apt-get install chef':"))
                abort(output)
        if stop_client == 'yes':
            # We only want chef-solo, stop chef-client and remove it from init
            sudo('update-rc.d -f chef-client remove')
            with settings(hide('warnings'), warn_only=True):
                # The logrotate entry will force restart of chef-client
                sudo('rm /etc/logrotate.d/chef')
            with settings(hide('warnings'), warn_only=True):
                output = sudo('service chef-client stop')
            if output.failed:
                # Probably an older distro without the newer "service" command
                sudo('/etc/init.d/chef-client stop')


def _add_rpm_repos():
    """Add RPM repositories for Chef
    Opscode doesn't officially support an ELFF resporitory any longer:
    http://wiki.opscode.com/display/chef/Installation+on+RHEL+and+CentOS+5+with
    +RPMs

    Using http://rbel.frameos.org/

    """
    version_string = sudo('cat /etc/redhat-release')
    try:
        rhel_version = re.findall("\d[\d.]*", version_string)[0].split('.')[0]
    except IndexError:
        print "Warning: could not correctly detect the Red Hat version"
        print "Defaulting to 5 packages"
        rhel_version = "5"

    epel_release = "epel-release-5-4.noarch"
    if rhel_version == "6":
        epel_release = "epel-release-6-8.noarch"
    with show('running'):
        # Install the EPEL Yum Repository.
        with settings(hide('warnings', 'running'), warn_only=True):
            repo_url = "http://dl.fedoraproject.org"
            repo_path = "/pub/epel/{0}/i386/".format(rhel_version)
            repo_path += "{0}.rpm".format(epel_release)
            output = sudo('rpm -Uvh {0}{1}'.format(repo_url, repo_path))
            installed = "package {0} is already installed".format(epel_release)
            if output.failed and installed not in output:
                abort(output)
        # Install the FrameOS RBEL Yum Repository.
        with settings(hide('warnings', 'running'), warn_only=True):
            repo_url = "http://rbel.co"
            repo_path = "/rbel{0}".format(rhel_version)
            output = sudo('rpm -Uvh {0}{1}'.format(repo_url, repo_path))
            installed = "package rbel{0}-release-1.0-2.el{0}".format(
                        rhel_version)
            installed += ".noarch is already installed"
            if output.failed and installed not in output:
                abort(output)


def _rpm_install():
    """Install Chef for rpm based distros"""
    _add_rpm_repos()
    with show('running'):
        # Ensure we have an up-to-date ruby, as we need >=1.8.7
        sudo('yum -y upgrade ruby*')
        # Install Chef
        sudo('yum -y install rubygem-chef')


def _emerge_install():
    """Install Chef for Gentoo"""
    with show('running'):
        sudo("USE='-test' ACCEPT_KEYWORDS='~amd64' emerge -u chef")

########NEW FILE########
__FILENAME__ = save_ip
"""Gets the IP and adds or updates the ipaddress attribute of a node"""
import subprocess
import os
import re

from fabric.api import env

from littlechef import chef


def parse_ip(text):
    """Extract an IPv4 IP from a text string
    Uses an IP Address Regex: http://www.regular-expressions.info/examples.html

    """
    ip_matches = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)
    ip = ip_matches[0] if ip_matches else None
    return ip


def execute(node):
    proc = subprocess.Popen(['ping', '-c', '1', node['name']],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    resp, error = proc.communicate()
    if not error:
        # Split output into lines and parse the first line to get the IP
        ip = parse_ip(resp.split("\n")[0])
        if not ip:
            print "Warning: could not get IP address from node {0}".format(
                node['name'])
        print "Node {0} has IP {1}".format(node['name'], ip)
        # Update with the ipaddress field in the corresponding node.json
        node['ipaddress'] = ip
        os.remove(chef.save_config(node, ip))
    else:
        print "Warning: could not resolve node {0}".format(node['name'])

########NEW FILE########
__FILENAME__ = save_xen_info
"""Saves some virtualization attributes in case the node is a Xen host"""
import subprocess
import os
import json

from fabric.api import env, sudo, abort, hide

from littlechef import chef, lib


def execute(node):
    """Uses ohai to get virtualization information which is then saved to then
    node file

    """
    with hide('everything'):
        virt = json.loads(sudo('ohai virtualization'))
    if not len(virt) or virt[0][1] != "host":
        # It may work for virtualization solutions other than Xen
        print("This node is not a Xen host, doing nothing")
        return
    node['virtualization'] = {
        'role': 'host',
        'system': 'xen',
        'vms': [],
    }
    # VMs
    with hide('everything'):
        vm_list = sudo("xm list")
    for vm in vm_list.split("\n")[2:]:
        data = vm.split()
        if len(data) != 6:
            break
        node['virtualization']['vms'].append({
            'fqdn': data[0], 'RAM': data[2], 'cpus': data[3]})
    print("Found {0} VMs for this Xen host".format(
          len(node['virtualization']['vms'])))
    # Save node file and remove the returned temp file
    del node['name']
    os.remove(chef.save_config(node, True))

########NEW FILE########
__FILENAME__ = bad
"""Bad LittleChef plugin"""


def execute():
    """I am not actually valid Python code"""
    I am a syntax error

########NEW FILE########
__FILENAME__ = dummy
"""Dummy LittleChef plugin"""


def execute():
    """Working plugin"""
    print "Worked!"

########NEW FILE########
__FILENAME__ = test_base
import os
import unittest

from littlechef import runner


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.nodes = [
            'nestedroles1',
            'testnode1',
            'testnode2',
            'testnode3.mydomain.com',
            'testnode4'
        ]
        runner.__testing__ = True

    def tearDown(self):
        for nodename in self.nodes + ["extranode"]:
            filename = 'tmp_' + nodename + '.json'
            if os.path.exists(filename):
                os.remove(filename)
        extra_node = os.path.join("nodes", "extranode" + '.json')
        if os.path.exists(extra_node):
            os.remove(extra_node)
        runner.env.chef_environment = None
        runner.env.hosts = []
        runner.env.all_hosts = []
        runner.env.ssh_config = None
        runner.env.key_filename = None
        runner.env.node_work_path = None
        runner.env.encrypted_data_bag_secret = None

########NEW FILE########
__FILENAME__ = test_command
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#
import unittest
import subprocess
import os
import platform
import shutil
from os.path import join, normpath, abspath, split

import sys
env_path = "/".join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1])
sys.path.insert(0, env_path)

import littlechef


# Set some convenience variables
test_path = split(normpath(abspath(__file__)))[0]
littlechef_top = normpath(join(test_path, '..'))

if platform.system() == 'Windows':
    fix = join(littlechef_top, 'fix.cmd')
    WIN32 = True
else:
    fix = join(littlechef_top, 'fix')
    WIN32 = False


class BaseTest(unittest.TestCase):
    def setUp(self):
        """Change to the test directory"""
        self.set_location()

    def set_location(self, location=test_path):
        """Change directories to a known location"""
        os.chdir(location)

    def execute(self, call):
        """Executes a command and returns stdout and stderr"""
        if WIN32:
            proc = subprocess.Popen(call,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        else:
            proc = subprocess.Popen(call,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        return proc.communicate()


class TestConfig(BaseTest):

    def tearDown(self):
        self.set_location()

    def test_not_a_kitchen(self):
        """Should exit with error when not a kitchen directory"""
        # Change to parent dir, which has no nodes/cookbooks/roles dir
        self.set_location(littlechef_top)
        # Call fix from the current directory above "tests/"
        resp, error = self.execute([fix, 'node:a'])
        self.assertTrue("Fatal error" in error, resp)
        self.assertTrue(
            'No {0} file found'.format(littlechef.CONFIGFILE) in error, error)
        self.assertEquals(resp, "", resp)

    def test_version(self):
        """Should output the correct Little Chef version"""
        resp, error = self.execute([fix, '-v'])
        self.assertEquals(resp, "",
                          "Response should be empty, version should be in stderr")
        self.assertTrue(
            'LittleChef {0}'.format(littlechef.__version__) in error)

    def test_list_commands(self):
        """Should output a list of available commands"""
        resp, error = self.execute([fix, '-l'])
        self.assertEquals(error, "")
        expected = "Starts a Chef Solo configuration run"
        self.assertTrue(expected in resp)
        commands = resp.split('\nAvailable commands:\n')[-1]
        commands = filter(None, commands.split('\n'))
        self.assertEquals(len(commands), 21)

    def test_verbose(self):
        """Should turn on verbose output"""
        resp, error = self.execute([fix, '--verbose', 'list_nodes'])
        self.assertEquals(error, "", error)
        self.assertTrue('Verbose output on' in resp, resp)

    def test_debug(self):
        """Should turn on debug loglevel"""
        resp, error = self.execute([fix, '--debug', 'list_nodes'])
        self.assertEquals(error, "", error)
        self.assertTrue('Debug level on' in resp, resp)


class TestEnvironment(BaseTest):
    def test_no_valid_value(self):
        """Should error out when the env value is empty or is a fabric task"""
        resp, error = self.execute([fix, 'list_nodes', '--env'])
        self.assertEquals(resp, "")
        self.assertTrue(
            "error: argument -e/--env: expected one argument" in error, error)

        resp, error = self.execute([fix, '--env', 'list_nodes'])
        self.assertEquals(resp, "")
        self.assertTrue("error: No value given for --env" in error, error)

        cmd = [fix, '--env', 'nodes_with_role:base', 'role:base']
        resp, error = self.execute(cmd)
        self.assertEquals(resp, "")
        self.assertTrue("error: No value given for --env" in error, error)

    def test_valid_environment(self):
        """Should set the chef_environment value when one is given"""
        resp, error = self.execute([fix, 'list_nodes', '--env', 'staging'])
        self.assertEquals(error, "", error)
        self.assertTrue("Environment: staging" in resp, resp)


class TestRunner(BaseTest):
    def test_no_node_given(self):
        """Should abort when no node is given"""
        resp, error = self.execute([fix, 'node:'])
        self.assertTrue("Fatal error: No node was given" in error)

    def test_plugin(self):
        """Should execute the given plugin"""
        resp, error = self.execute([fix, 'node:testnode1', 'plugin:notthere'])
        expected = ", could not find 'notthere.py' in the plugin directory"
        self.assertTrue(expected in error, resp + error)

        resp, error = self.execute([fix, 'node:testnode1', 'plugin:bad'])
        expected = "Found plugin 'bad', but it seems to have a syntax error:"
        expected += " invalid syntax (bad.py, line 6)"
        self.assertTrue(expected in error, resp + error)

        resp, error = self.execute([fix, 'node:testnode1', 'plugin:dummy'])
        expected = "Executing plugin '{0}' on {1}".format("dummy", "testnode1")
        self.assertTrue(expected in resp, resp + error)

    def test_list_plugins(self):
        """Should print a list of available plugins"""
        resp, error = self.execute([fix, 'list_plugins'])
        self.assertTrue("List of available plugins:" in resp, resp)
        self.assertTrue("bad: Plugin has a syntax error" in resp, resp)
        self.assertTrue("dummy: Dummy LittleChef plugin" in resp, resp)


class TestCookbooks(BaseTest):
    def test_list_recipes(self):
        """Should list available recipes"""
        resp, error = self.execute([fix, 'list_recipes'])
        self.assertEquals(error, "")
        self.assertTrue('subversion::client' in resp)
        self.assertTrue('subversion::server' in resp)

    def test_list_recipes_site_cookbooks(self):
        """Should give priority to site-cookbooks information"""
        resp, error = self.execute([fix, 'list_recipes'])
        self.assertTrue('Modified by site-cookbooks' in resp)

    def test_list_recipes_detailed(self):
        """Should show a detailed list of available recipes"""
        resp, error = self.execute([fix, 'list_recipes_detailed'])
        self.assertTrue('subversion::client' in resp)
        for field in ['description', 'version', 'dependencies', 'attributes']:
            self.assertTrue(field in resp)

    def test_list_recipes_detailed_site_cookbooks(self):
        """Should show a detailed list of available recipes with site-cookbook
        priority

        """
        resp, error = self.execute([fix, 'list_recipes_detailed'])
        self.assertTrue('0.8.4' in resp)

    def test_no_metadata(self):
        """Should abort if cookbook has no metadata.json"""
        bad_cookbook = join(test_path, 'cookbooks', 'bad_cookbook')
        os.mkdir(bad_cookbook)
        try:
            resp, error = self.execute([fix, 'list_recipes'])
        except OSError:
            self.fail("Couldn't execute {0}".format(fix))
        finally:
            os.rmdir(bad_cookbook)
        expected = 'Fatal error: Cookbook "bad_cookbook" has no metadata.json'
        self.assertTrue(expected in error)


class TestListRoles(BaseTest):
    def test_list_roles(self):
        """Should list all roles"""
        resp, error = self.execute([fix, 'list_roles'])
        self.assertTrue('base' in resp and 'example aplication' in resp)

    def test_list_roles_detailed(self):
        """Should show a detailed list of all roles"""
        resp, error = self.execute([fix, 'list_roles_detailed'])
        self.assertTrue('base' in resp and 'example aplication' in resp)


class TestListNodes(BaseTest):
    def test_list_nodes(self):
        """Should list all nodes"""
        resp, error = self.execute([fix, 'list_nodes'])
        for node in ['testnode1', 'testnode2', 'testnode3.mydomain.com']:
            self.assertTrue(node in resp)
        self.assertTrue('Recipes: subversion' in resp)

    def test_list_nodes_in_env(self):
        """Should list all nodes in an environment"""
        resp, error = self.execute([fix, '--env', 'staging', 'list_nodes'])
        self.assertTrue('testnode2' in resp)
        self.assertFalse('testnode1' in resp)
        self.assertFalse('testnode3.mydomain.com' in resp)

    def test_list_nodes_detailed(self):
        """Should show a detailed list of all nodes"""
        resp, error = self.execute([fix, 'list_nodes_detailed'])
        self.assertTrue('testnode1' in resp)
        self.assertTrue('Recipe: subversion' in resp)

    def test_list_nodes_with_recipe(self):
        """Should list all nodes with a recipe in the run list"""
        resp, error = self.execute([fix, 'list_nodes_with_recipe:subversion'])
        self.assertTrue('testnode1' in resp)
        self.assertTrue('Recipes: subversion' in resp)

        resp, error = self.execute([fix, 'list_nodes_with_recipe:apache2'])
        self.assertFalse('testnode1' in resp)


class TestNewKitchen(BaseTest):

    def setUp(self):
        self.new_kitchen = join(test_path, 'test_new_kitchen')
        os.mkdir(self.new_kitchen)
        self.set_location(self.new_kitchen)

    def tearDown(self):
        shutil.rmtree(self.new_kitchen)
        self.set_location()

    def test_new_kitchen_creates_required_directories(self):
        resp, error = self.execute([fix, 'new_kitchen'])
        kitchen_contents = os.listdir(os.getcwd())

        self.assertTrue('roles' in kitchen_contents)
        self.assertTrue('cookbooks' in kitchen_contents)
        self.assertTrue('site-cookbooks' in kitchen_contents)
        self.assertTrue('data_bags' in kitchen_contents)
        self.assertTrue('nodes' in kitchen_contents)
        self.assertTrue('environments' in kitchen_contents)
        self.assertTrue(littlechef.CONFIGFILE in kitchen_contents)

    def test_new_kitchen_can_list_nodes(self):
        self.execute([fix, 'new_kitchen'])

        with open(littlechef.CONFIGFILE, "w") as configfh:
            print >> configfh, "[userinfo]"
            print >> configfh, "user = testuser"
            print >> configfh, "password = testpassword"

        resp, error = self.execute([fix, 'list_nodes'])
        self.assertFalse(error)
        self.assertTrue('Found 0 nodes' in resp)
        self.assertEqual('', error)

########NEW FILE########
__FILENAME__ = test_lib
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
#
import os
import json

from fabric.api import env
from mock import patch
from nose.tools import raises

import sys
env_path = "/".join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1])
sys.path.insert(0, env_path)

from littlechef import chef, lib, solo, exceptions
from test_base import BaseTest

littlechef_src = os.path.split(os.path.normpath(os.path.abspath(__file__)))[0]
littlechef_top = os.path.normpath(os.path.join(littlechef_src, '..'))


class TestSolo(BaseTest):
    def test_configure_no_sudo_rights(self):
        """Should abort when user has no sudo rights"""
        env.host_string = "extranode"
        with patch.object(solo, 'exists') as mock_exists:
            mock_exists.return_value = False
            with patch.object(solo, 'sudo') as mock_sudo:
                mock_sudo.failed = True
                self.assertRaises(SystemExit, solo.configure)

    @raises(SystemExit)
    @patch('littlechef.solo.exists')
    def test_configure_bad_credentials(self, mock_exists):
        """Should return True when node has been synced"""
        mock_exists.side_effect = EOFError(
            '/usr/lib64/python2.6/getpass.py:83: GetPassWarning: '
            'Can not control echo on the terminal.')
        solo.configure()


class TestLib(BaseTest):

    def test_get_node_not_found(self):
        """Should get empty template when node is not found"""
        name = 'Idon"texist'
        expected = {'chef_environment': '_default', 'name': name, 'run_list': []}
        self.assertEqual(lib.get_node(name), expected)

    def test_get_node_found(self):
        """Should get node data when node is found"""
        expected = {
            'chef_environment': 'production',
            'name': 'testnode1',
            'run_list': ['recipe[subversion]'],
        }
        self.assertEqual(lib.get_node('testnode1'), expected)

    def test_get_node_default_env(self):
        """Should set env to _default when node sets no chef_environment"""
        expected = {
            'chef_environment': '_default',
            'name': 'nestedroles1',
            'run_list': ['role[top_level_role]'],
            'tags': ['top'],
        }
        self.assertEqual(lib.get_node('nestedroles1'), expected)

    def test_get_nodes(self):
        """Should return all configured nodes when no environment is given"""
        found_nodes = lib.get_nodes()
        self.assertEqual(len(found_nodes), len(self.nodes))
        expected_keys = ['name', 'chef_environment', 'run_list']
        for node in found_nodes:
            self.assertTrue(all([key in node for key in expected_keys]))

    def test_get_nodes_in_env(self):
        """Should list all nodes in the given environment"""
        self.assertEqual(len(lib.get_nodes("production")), 3)
        self.assertEqual(len(lib.get_nodes("staging")), 1)

    def test_nodes_with_role(self):
        """Should return nodes when role is present in the explicit run_list"""
        nodes = list(lib.get_nodes_with_role('all_you_can_eat'))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], 'testnode2')
        self.assertTrue('role[all_you_can_eat]' in nodes[0]['run_list'])

    def test_nodes_with_role_expanded(self):
        """Should return nodes when role is present in the expanded run_list"""
        # nested role 'base'
        nodes = list(lib.get_nodes_with_role('base'))
        self.assertEqual(len(nodes), 2)
        expected_nodes = ['nestedroles1', 'testnode2']
        for node in nodes:
            self.assertTrue(node['name'] in expected_nodes)
            expected_nodes.remove(node['name'])

        # Find node regardless of recursion level of role sought
        for role in ['top_level_role', 'sub_role', 'sub_sub_role']:
            nodes = list(lib.get_nodes_with_role(role))
            self.assertEqual(len(nodes), 1)
            self.assertTrue(nodes[0]['name'], 'nestedroles1')

    def test_nodes_with_role_wildcard(self):
        """Should return node when wildcard is given and role is asigned"""
        nodes = list(lib.get_nodes_with_role('all_*'))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], 'testnode2')
        # Prefix with no wildcard
        nodes = list(lib.get_nodes_with_role('all_'))
        self.assertEqual(len(nodes), 0)
        # Nodes with at least one role
        nodes = list(lib.get_nodes_with_role('*'))

        self.assertEqual(len(nodes), 2)
        nodes = list(lib.get_nodes_with_role(''))
        self.assertEqual(len(nodes), 0)

    def test_nodes_with_role_in_env(self):
        """Should return node when role is asigned and environment matches"""
        nodes = list(lib.get_nodes_with_role('all_you_can_eat', 'staging'))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], 'testnode2')
        # No nodes in production with this role
        nodes = list(lib.get_nodes_with_role('all_you_can_eat', 'production'))
        self.assertFalse(len(nodes))

    def test_nodes_with_recipe(self):
        """Should return node when recipe is in the explicit run_list"""
        nodes = list(lib.get_nodes_with_recipe('vim'))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]['name'], 'testnode3.mydomain.com')

    def test_nodes_with_recipe_expanded(self):
        """Should return node when recipe is in the expanded run_list"""
        # 'subversion' is in the 'base' role
        nodes = list(lib.get_nodes_with_recipe('subversion'))
        self.assertEqual(len(nodes), 4)

        # man recipe inside role "all_you_can_eat" and in testnode4
        nodes = list(lib.get_nodes_with_recipe('man'))
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0]['name'], 'testnode2')

    def test_nodes_with_recipe_wildcard(self):
        """Should return node when wildcard is given and role is asigned"""
        nodes = list(lib.get_nodes_with_recipe('sub*'))
        self.assertEqual(len(nodes), 4)

        # Get node with at least one recipe
        nodes = list(lib.get_nodes_with_recipe('*'))
        self.assertEqual(len(nodes), 5)
        nodes = list(lib.get_nodes_with_role(''))
        self.assertEqual(len(nodes), 0)

    def test_nodes_with_recipe_in_env(self):
        """Should return all nodes with a given recipe and in the given env"""
        nodes = list(lib.get_nodes_with_recipe('subversion', 'production'))
        self.assertEqual(len(nodes), 2)
        self.assertEqual(nodes[0]['name'], 'testnode1')
        nodes = list(lib.get_nodes_with_recipe('subversion', 'staging'))
        self.assertEqual(len(nodes), 1)
        # No nodes in staging with this role
        nodes = list(lib.get_nodes_with_recipe('vim', 'staging'))
        self.assertFalse(len(nodes))

    def test_get_nodes_with_tag(self):
        """Should list all nodes with tag 'top'"""
        nodes = list(lib.get_nodes_with_tag('top'))
        self.assertEqual(len(nodes), 1)

    def test_get_nodes_with_tag_in_env(self):
        """Should list all nodes with tag 'top' in the given environment"""
        nodes = list(lib.get_nodes_with_tag('top', 'production'))
        self.assertEqual(len(nodes), 0)
        nodes = list(lib.get_nodes_with_tag('top', '_default'))
        self.assertEqual(len(nodes), 1)

    def test_list_recipes(self):
        recipes = lib.get_recipes()
        self.assertEqual(len(recipes), 6)
        self.assertEqual(recipes[1]['name'], 'subversion')
        self.assertEqual(recipes[1]['description'],
                         'Includes the client recipe. Modified by site-cookbooks')
        self.assertEqual(recipes[2]['name'], 'subversion::client')
        self.assertEqual(recipes[2]['description'],
                         'Subversion Client installs subversion and some extra svn libs')
        self.assertEqual(recipes[3]['name'], 'subversion::server')
        self.assertIn('subversion::testrecipe', [r['name'] for r in recipes])

    def test_import_plugin(self):
        """Should import the given plugin"""
        plugin = lib.import_plugin("dummy")
        expected = "Dummy LittleChef plugin"
        self.assertEqual(plugin.__doc__, expected)

        # Should fail to import a bad plugin module
        self.assertRaises(SystemExit, lib.import_plugin, "bad")

    def test_get_plugins(self):
        """Should get a list of available plugins"""
        plugins = [p for p in lib.get_plugins()]
        self.assertEqual(len(plugins), 2)
        self.assertEqual(plugins[0]['bad'], "Plugin has a syntax error")

    def test_get_environments(self):
        """Should get a list of all environments"""
        environments = lib.get_environments()
        self.assertEqual(sorted(env['name'] for env in environments),
                         ['production', 'staging'])

    def test_get_existing_environment(self):
        """Should return an existing environment object from the kitchen"""
        environment = lib.get_environment('production')
        self.assertTrue('subversion' in environment['default_attributes'])
        self.assertEqual(environment['default_attributes']['subversion']['user'], 'tom')

    def test_get__default_environment(self):
        """Should return empty env when name is '_default'"""
        expected = {
            "name": "_default",
            "default_attributes": {},
            "json_class": "Chef::Environment",
            "chef_type": "environment",
            "description": "",
            "cookbook_versions": {}
        }
        self.assertEqual(lib.get_environment('_default'), expected)

    @raises(exceptions.FileNotFoundError)
    def test_get_nonexisting_environment(self):
        """Should raise FileNotFoundError when environment does not exist"""
        lib.get_environment('not-exists')


class TestChef(BaseTest):
    def tearDown(self):
        chef.remove_local_node_data_bag()
        super(TestChef, self).tearDown()

    def test_save_config(self):
        """Should create a tmp_extranode.json and a nodes/extranode.json config
        file

        """
        # Save a new node
        env.host_string = 'extranode'
        run_list = ["role[base]"]
        chef.save_config({"run_list": run_list})
        file_path = os.path.join('nodes', 'extranode.json')
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, 'r') as f:
            data = json.loads(f.read())
        self.assertEqual(data['run_list'], run_list)

        # It should't overwrite existing config files
        env.host_string = 'testnode1'  # This node exists
        run_list = ["role[base]"]
        chef.save_config({"run_list": run_list})
        with open(os.path.join('nodes', 'testnode1.json'), 'r') as f:
            data = json.loads(f.read())
            # It should *NOT* have "base" assigned
            self.assertEqual(data['run_list'], ["recipe[subversion]"])

    def test_get_ipaddress(self):
        """Should add ipaddress attribute when ohai returns correct IP address
        """
        class MockSudoReturnValue(str):
            succeeded = True

        node = {}
        fake_ip = "1.1.1.2"
        with patch.object(chef, 'sudo') as mock_method:
            mocked_ohai_response = '["{0}"]'.format(fake_ip)
            mock_method.return_value = MockSudoReturnValue(mocked_ohai_response)
            response = chef._get_ipaddress(node)
        self.assertTrue(response)
        self.assertEqual(node['ipaddress'], fake_ip)

    def test_get_ipaddress_attribute_exists(self):
        """Should not save ipaddress when attribute exists"""
        class MockSudoReturnValue(str):
            succeeded = True

        node = {'ipaddress': '1.1.1.1'}
        with patch.object(chef, 'sudo') as mock_method:
            mocked_ohai_response = '["{0}"]'.format("1.1.1.2")
            mock_method.return_value = MockSudoReturnValue(mocked_ohai_response)
            response = chef._get_ipaddress(node)
        self.assertFalse(response)
        self.assertEqual(node['ipaddress'], '1.1.1.1')

    def test_get_ipaddress_bad_ohai_output(self):
        """Should abort when ohai's output cannot be parsed"""
        class MockSudoReturnValue(str):
            succeeded = True

        with patch.object(chef, 'sudo') as mock_method:
            mocked_ohai_response = ('Invalid gemspec '
                                    '["{0}"]'.format("1.1.1.2"))
            mock_method.return_value = MockSudoReturnValue(mocked_ohai_response)
            self.assertRaises(SystemExit, chef._get_ipaddress, {})

    def test_build_node_data_bag(self):
        """Should create a node data bag with one item per node"""
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode1.json')
        self.assertTrue(os.path.exists(item_path))
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('id' in data and data['id'] == 'testnode1')
        self.assertTrue('name' in data and data['name'] == 'testnode1')
        self.assertTrue(
            'recipes' in data and data['recipes'] == ['subversion'])
        self.assertTrue(
            'recipes' in data and data['role'] == [])
        item_path = os.path.join('data_bags', 'node', 'testnode2.json')
        self.assertTrue(os.path.exists(item_path))
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('id' in data and data['id'] == 'testnode2')
        self.assertTrue('recipes' in data)
        self.assertEqual(data['recipes'], [u'subversion', u'man'])
        self.assertTrue('recipes' in data)
        self.assertEqual(data['role'], [u'all_you_can_eat'])
        self.assertEqual(data['roles'], [u'base', u'all_you_can_eat'])

    def test_build_node_data_bag_nonalphanumeric(self):
        """Should create a node data bag when node name contains invalid chars
        """
        chef.build_node_data_bag()
        # A node called testnode3.mydomain.com will have the data bag id
        # 'testnode3', because dots are not allowed.
        filename = 'testnode3_mydomain_com'
        nodename = filename.replace("_", ".")
        item_path = os.path.join('data_bags', 'node', filename + '.json')
        self.assertTrue(os.path.exists(item_path), "node file does not exist")
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('id' in data and data['id'] == filename)
        self.assertTrue('name' in data and data['name'] == nodename)

    def test_automatic_attributes(self):
        """Should add Chef's automatic attributes"""
        chef.build_node_data_bag()
        # Check node with single word fqdn
        testnode1_path = os.path.join('data_bags', 'node', 'testnode1.json')
        with open(testnode1_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('fqdn' in data and data['fqdn'] == 'testnode1')
        self.assertTrue('hostname' in data and data['hostname'] == 'testnode1')
        self.assertTrue('domain' in data and data['domain'] == '')

        # Check node with complex fqdn
        testnode3_path = os.path.join(
            'data_bags', 'node', 'testnode3_mydomain_com.json')
        with open(testnode3_path, 'r') as f:
            print testnode3_path
            data = json.loads(f.read())
        self.assertTrue(
            'fqdn' in data and data['fqdn'] == 'testnode3.mydomain.com')
        self.assertTrue('hostname' in data and data['hostname'] == 'testnode3')
        self.assertTrue('domain' in data and data['domain'] == 'mydomain.com')

    def test_attribute_merge_cookbook_not_found(self):
        """Should print a warning when merging a node and a cookbook is not
        found

        """
        # Save new node with a non-existing cookbook assigned
        env.host_string = 'extranode'
        chef.save_config({"run_list": ["recipe[phantom_cookbook]"]})
        self.assertRaises(SystemExit, chef.build_node_data_bag)

    def test_attribute_merge_cookbook_default(self):
        """Should have the value found in recipe/attributes/default.rb"""
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode2.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('subversion' in data)
        self.assertTrue(data['subversion']['repo_name'] == 'repo')

    def test_attribute_merge_environment_default(self):
        """Should have the value found in environment/ENV.json"""
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode1.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('subversion' in data)
        self.assertEqual(data['subversion']['user'], 'tom')

    def test_attribute_merge_cookbook_boolean(self):
        """Should have real boolean values for default cookbook attributes"""
        chef.build_node_data_bag()
        item_path = os.path.join(
            'data_bags', 'node', 'testnode3_mydomain_com.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('vim' in data)
        self.assertTrue(data['vim']['sucks'] is True)

    def test_attribute_merge_site_cookbook_default(self):
        """Should have the value found in
        site_cookbooks/xx/recipe/attributes/default.rb

        """
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode2.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('subversion' in data)
        self.assertTrue(data['subversion']['repo_dir'] == '/srv/svn2')

    def test_attribute_merge_role_not_found(self):
        """Should print a warning when an assigned role if not found"""
        # Save new node with a non-existing cookbook assigned
        env.host_string = 'extranode'
        chef.save_config({"run_list": ["role[phantom_role]"]})
        self.assertRaises(SystemExit, chef.build_node_data_bag)

    def test_attribute_merge_role_default(self):
        """Should have the value found in the roles default attributes"""
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode2.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('subversion' in data)
        self.assertEqual(
            data['subversion']['repo_server'], 'role_default_repo_server')
        self.assertTrue('other_attr' in data)
        self.assertEqual(data['other_attr']['other_key'], 'nada')

    def test_attribute_merge_node_normal(self):
        """Should have the value found in the node attributes"""
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode2.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('subversion' in data)
        self.assertEqual(data['subversion']['user'], 'node_user')

    def test_attribute_merge_role_override(self):
        """Should have the value found in the roles override attributes"""
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode2.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('subversion' in data)
        self.assertEqual(data['subversion']['password'], 'role_override_pass')

    def test_attribute_merge_environment_override(self):
        """Should have the value found in the environment override attributes"""
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode1.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('subversion' in data)
        self.assertEqual(data['subversion']['password'], 'env_override_pass')

    def test_attribute_merge_deep_dict(self):
        """Should deep-merge a dict when it is defined in two different places
        """
        chef.build_node_data_bag()
        item_path = os.path.join('data_bags', 'node', 'testnode2.json')
        with open(item_path, 'r') as f:
            data = json.loads(f.read())
        self.assertTrue('other_attr' in data)
        expected = {
            "deep_dict": {
                "deep_key1": "node_value1",
                "deep_key2": "role_value2"
            }
        }
        self.assertTrue(data['other_attr']['deep_dict'], expected)

    def test_sync_node_dummy_attr(self):
        """Should return False when node has a dummy tag or dummy=true"""
        self.assertFalse(chef.sync_node({'name': 'extranode', 'dummy': True}))
        self.assertFalse(chef.sync_node({'name': 'extranode', 'tags': ['dummy']}))

    @patch('littlechef.chef.solo.configure')
    @patch('littlechef.chef._get_ipaddress')
    @patch('littlechef.chef._synchronize_node')
    @patch('littlechef.chef._configure_node')
    @patch('littlechef.chef._node_cleanup')
    def test_sync_node(self, mock_method1, mock_ipaddress, mock_method3,
                       mock_method4, mock_method5):
        """Should return True when node has been synced"""
        env.host_string = 'extranode'
        mock_ipaddress.return_value = False
        test_node = {'name': 'extranode', 'dummy': False, 'run_list': []}
        self.assertTrue(chef.sync_node(test_node))

########NEW FILE########
__FILENAME__ = test_runner
from ConfigParser import SafeConfigParser

from mock import patch
from nose.tools import raises

from littlechef import runner
from test_base import BaseTest


class TestConfig(BaseTest):

    def test_get_config(self):
        """Should read configuration from config file when config.cfg is found
        """
        runner._readconfig()
        self.assertEqual(runner.env.ssh_config_path, None)
        self.assertEqual(runner.env.ssh_config, None)
        self.assertEqual(runner.env.user, "testuser")
        self.assertEqual(runner.env.password, "testpass")
        self.assertEqual(runner.env.key_filename, None)
        self.assertEqual(runner.env.node_work_path, "/tmp/chef-solo")
        self.assertEqual(runner.env.encrypted_data_bag_secret, None)
        self.assertEqual(runner.env.sync_packages_dest_dir, "/srv/repos")
        self.assertEqual(runner.env.sync_packages_local_dir, "./repos")

    def test_not_a_kitchen(self):
        """Should abort when no config file found"""
        with patch.object(SafeConfigParser, 'read') as mock_method:
            mock_method.return_value = []
            self.assertRaises(SystemExit, runner._readconfig)


class TestNode(BaseTest):

    def test_node_one(self):
        """Should configure one node when an existing node name is given"""
        runner.node('testnode1')
        self.assertEqual(runner.env.hosts, ['testnode1'])

    def test_node_several(self):
        """Should configure several nodes"""
        runner.node('testnode1', 'testnode2')
        self.assertEqual(runner.env.hosts, ['testnode1', 'testnode2'])

    def test_node_all(self):
        """Should configure all nodes when 'all' is given"""
        runner.node('all')
        self.assertEqual(runner.env.hosts, self.nodes)

    def test_node_all_in_env(self):
        """Should configure all nodes in a given environment when 'all' is
        given and evironment is set"""
        runner.env.chef_environment = "staging"
        runner.node('all')
        self.assertEqual(runner.env.hosts, ['testnode2'])


class TestNodesWithRole(BaseTest):

    def test_nodes_with_role(self):
        """Should return a list of nodes with the given role in the run_list"""
        runner.nodes_with_role('base')
        self.assertEqual(runner.env.hosts, ['nestedroles1', 'testnode2'])

    def test_nodes_with_role_in_env(self):
        """Should return a filtered list of nodes with role when an env is given
        """
        runner.env.chef_environment = "staging"
        runner.nodes_with_role('base')
        self.assertEqual(runner.env.hosts, ['testnode2'])

    @raises(SystemExit)
    def test_nodes_with_role_in_env_not_found(self):
        """Should abort when no nodes with given role found in the environment
        """
        runner.env.chef_environment = "production"
        runner.nodes_with_role('base')


class TestNodesWithRecipe(BaseTest):

    def test_nodes_with_role(self):
        """Should return a list of nodes with the given recipe in the run_list"""
        runner.nodes_with_recipe('man')
        self.assertEqual(runner.env.hosts, ['testnode2', 'testnode4'])

    def test_nodes_with_role_in_env(self):
        """Should return a filtered list of nodes with recipe when an env is given
        """
        runner.env.chef_environment = "staging"
        runner.nodes_with_recipe('man')
        self.assertEqual(runner.env.hosts, ['testnode2'])

    @raises(SystemExit)
    def test_nodes_with_role_in_env_not_found(self):
        """Should abort when no nodes with given recipe found in the environment
        """
        runner.env.chef_environment = "_default"
        runner.nodes_with_recipe('man')


class TestNodesWithTag(BaseTest):

    def test_nodes_with_tag(self):
        """Should return a list of nodes with the given tag"""
        runner.nodes_with_tag('top')
        self.assertEqual(runner.env.hosts, ['nestedroles1'])

    def test_nodes_with_tag_in_env(self):
        """Should return a filtered list of nodes with tag when an env is given
        """
        runner.env.chef_environment = "production"
        runner.nodes_with_tag('dummy')
        self.assertEqual(runner.env.hosts, ['testnode4'])

    @raises(SystemExit)
    def test_nodes_with_tag_in_env_not_found(self):
        """Should abort when no nodes with given tag found in the environment
        """
        runner.env.chef_environment = "production"
        runner.nodes_with_role('top')

########NEW FILE########
