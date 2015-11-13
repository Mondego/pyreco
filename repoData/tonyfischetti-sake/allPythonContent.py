__FILENAME__ = acts
#!/usr/bin/env python

###########################################################
##                                                       ##
##   acts.py                                             ##
##                                                       ##
##                Author: Tony Fischetti                 ##
##                        tony.fischetti@gmail.com       ##
##                                                       ##
###########################################################
#
##############################################################################
#                                                                            #
# Copyright (c) 2013, 2014, Tony Fischetti                                   #
#                                                                            #
# MIT License, http://www.opensource.org/licenses/mit-license.php            #
#                                                                            #
# Permission is hereby granted, free of charge, to any person obtaining a    #
# copy of this software and associated documentation files (the "Software"), #
# to deal in the Software without restriction, including without limitation  #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,   #
# and/or sell copies of the Software, and to permit persons to whom the      #
# Software is furnished to do so, subject to the following conditions:       #
#                                                                            #
# The above copyright notice and this permission notice shall be included in #
# all copies or substantial portions of the Software.                        #
#                                                                            #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,   #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL    #
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING    #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER        #
# DEALINGS IN THE SOFTWARE.                                                  #
#                                                                            #
##############################################################################


"""
Various actions that the main entry delegates to
"""

from __future__ import unicode_literals
from __future__ import print_function
from subprocess import Popen
import networkx as nx
import codecs
import os
import re
import fnmatch
import string
import glob
import sys

if sys.version_info[0] < 3:
    import codecs
    open = codecs.open

def clean_path(a_path):
    """
    This function is used to normalize the path (of an output or
    dependency) and also provide the path in relative form. It is
    relative to the current working directory
    """
    return os.path.relpath(os.path.normpath(a_path))


def escp(target_name):
    """
    This function is used by sake help. Since sakefiles allow
    for targets with spaces in them, sake help needs to quote
    all targets with spaces. This takes a target name and
    quotes it if necessary
    """
    if ' ' in target_name:
        return '"{}"'.format(target_name)
    return target_name


def print_help(sakefile):
    """
    Prints the help string of the Sakefile, prettily

    Args:
        A dictionary that is the parsed Sakefile (from sake.py)

    Returns:
        0 if all targets have help messages to print,
        1 otherwise
    """
    full_string = "You can 'sake' one of the following...\n\n"
    errmes = "target '{}' is not allowed to not have help message\n"
    for target in sakefile:
        if target == "all":
            # this doesn't have a help message
            continue
        if "formula" not in sakefile[target]:
            # this means it's a meta-target
            full_string += "{}:\n  - {}\n\n".format(escp(target),
                                                    sakefile[target]["help"])
            for atom_target in sakefile[target]:
                if atom_target == "help":
                    continue
                full_string += "    "
                full_string += "{}:\n      -  {}\n".format(escp(atom_target),
                                       sakefile[target][atom_target]["help"])
            full_string += "\n"
        else:
            full_string += "{}:\n  - {}\n\n".format(escp(target),
                                                    sakefile[target]["help"])
    what_clean_does = "remove all targets' outputs and start from scratch"
    full_string += "clean:\n  -  {}\n\n".format(what_clean_does)
    what_visual_does = "output visual representation of project's dependencies"
    full_string += "visual:\n  -  {}\n".format(what_visual_does)
    print(full_string)


def expand_macros(raw_text):
    """
    This gets called before the Sakefile is parsed. It looks for
    macros defined anywhere in the Sakefile (the start of the line
    is '#!') and then replaces all occurences of '$variable' with the
    value defined in the macro. It then returns the contents of the
    file with the macros expanded
    """
    # gather macros
    macros = {}
    for line in raw_text.split("\n"):
        if re.search("^#!", line):
            try:
                var, val = re.search("^#!\s*(\w+)\s*=\s*(.+$)",
                                     line).group(1, 2)
            except:
                sys.stderr.write("Failed to parse macro {}\n".format(line))
                sys.exit(1)
            macros[var] = val
    raw_text = string.Template(raw_text).safe_substitute(macros)
    return raw_text


def check_for_dep_in_outputs(dep, verbose, G):
    """
    Function to help construct_graph() identify dependencies

    Args:
        A dependency
        A flag indication verbosity
        A (populated) NetworkX DiGraph

    Returns:
        A list of targets that build given dependency

    """
    if verbose:
        print("checking dep {}".format(dep))
    ret_list = []
    for node in G.nodes(data=True):
        if "output" not in node[1]:
            continue
        for out in node[1]['output']:
            if fnmatch.fnmatch(out, dep):
                ret_list.append(node[0])
                break
    return ret_list


def construct_graph(sakefile, verbose, G):
    """
    Takes the sakefile dictionary and builds a NetworkX graph

    Args:
        A dictionary that is the parsed Sakefile (from sake.py)
        A flag indication verbosity
        A NetworkX GiGraph object to populate

    Returns:
        A NetworkX graph
    """
    if verbose:
        print("Going to construct Graph")
    for target in sakefile:
        if target == "all":
            # we don't want this node
            continue
        if "formula" not in sakefile[target]:
            # that means this is a meta target
            for atomtarget in sakefile[target]:
                if atomtarget == "help":
                    continue
                if verbose:
                    print("Adding '{}'".format(atomtarget))
                data_dict = sakefile[target][atomtarget]
                data_dict["parent"] = target
                G.add_node(atomtarget, data_dict)
        else:
            if verbose:
                print("Adding '{}'".format(target))
            G.add_node(target, sakefile[target])
    if verbose:
        print("Nodes are built\nBuilding connections")
    for node in G.nodes(data=True):
        if verbose:
            print("checking node {} for dependencies".format(node[0]))
        # normalize all paths in output
        for k, v in node[1].items():
            if v is None: node[1][k] = []
        if "output" in node[1]:
            for index, out in enumerate(node[1]['output']):
                node[1]['output'][index] = clean_path(node[1]['output'][index])
        if "dependencies" not in node[1]:
            continue
        if verbose:
            print("it has dependencies")
        connects = []
        # normalize all paths in dependencies
        for index, dep in enumerate(node[1]['dependencies']):
            dep = os.path.normpath(dep)
            shrt = "dependencies"
            node[1]['dependencies'][index] = clean_path(node[1][shrt][index])
    for node in G.nodes(data=True):
        connects = []
        if "dependencies" not in node[1]:
            continue
        for dep in node[1]['dependencies']:
            matches = check_for_dep_in_outputs(dep, verbose, G)
            if not matches:
                continue
            for match in matches:
                if verbose:
                    print("Appending {} to matches".format(match))
                connects.append(match)
        if connects:
            for connect in connects:
                G.add_edge(connect, node[0])
    return G


def get_all_outputs(node_dict):
    """
    This function takes a node dictionary and returns a list of
    the node's output files. Some of the entries in the 'output'
    attribute may be globs, and without this function, sake won't
    know how to handle that. This will unglob all globs and return
    the true list of *all* outputs.
    """
    outlist = []
    for item in node_dict['output']:
        glist = glob.glob(item)
        if glist:
            for oneglob in glist:
                outlist.append(oneglob)
        else:
            outlist.append(item)
    return outlist


def clean_all(G, verbose, quiet, recon):
    """
    Removes all the output files from all targets. Takes
    the graph as the only argument

    Args:
        The networkx graph object
        A flag indicating verbosity
        A flag indicating quiet mode

    Returns:
        0 if successful
        1 if removing even one file failed
    """
    all_outputs = []
    for node in G.nodes(data=True):
        if "output" in node[1]:
            for item in get_all_outputs(node[1]):
                all_outputs.append(item)
    all_outputs.append(".shastore")
    retcode = 0
    for item in all_outputs:
        if os.path.isfile(item):
            if recon:
                print("Would remove file: {}".format(item))
                continue
            if verbose:
                mesg = "Attempting to remove file '{}'"
                print(mesg.format(item))
            try:
                os.remove(item)
                if verbose:
                    print("Removed file")
            except:
                errmeg = "Error: file '{}' failed to be removed\n"
                sys.stderr.write(errmeg.format(item))
                retcode = 1
    if not retcode and not recon:
        print("All clean")
    return retcode


def write_dot_file(G, filename):
    """
    Writes the graph G in dot file format for graphviz visualization.

    Args:
        a Networkx graph
        A filename to name the dot files
    """
    fh = open(filename, "w", encoding="utf-8")
    fh.write("strict digraph DependencyDiagram {\n")
    edge_list = G.edges()
    node_list = set(G.nodes())
    if edge_list:
        for edge in G.edges():
            source, targ = edge
            node_list = node_list - set(source)
            node_list = node_list - set(targ)
            line = '"{}" -> "{}";\n'
            fh.write(line.format(source, targ))
    # draw nodes with no links
    if node_list:
        for node in node_list:
            line = '"{}"\n'.format(node)
            fh.write(line)
    fh.write("}")


def visualize(G, filename="dependencies", no_graphviz=False):
    """
    Uses networkX to draw a graphviz dot file either (a) calls the
    graphviz command "dot" to turn it into a SVG and remove the
    dotfile (default), or (b) if no_graphviz is True, just output
    the graphviz dot file

    Args:
        a NetworkX DiGraph
        a filename (a default is provided
        a flag indicating whether graphviz should *not* be called

    Returns:
        0 if everything worked
        will cause fatal error on failure
    """
    if no_graphviz:
        write_dot_file(G, filename)
        return 0
    write_dot_file(G, "tempdot")
    command = "dot -Tsvg tempdot -o {}.svg".format(filename)
    p = Popen(command, shell=True)
    p.communicate()
    if p.returncode:
        errmes = "Either graphviz is not installed, or its not on PATH"
        sys.stderr.write(errmes)
        sys.exit(1)
    os.remove("tempdot")
    return 0

########NEW FILE########
__FILENAME__ = audit
#!/usr/bin/env python

###########################################################
##                                                       ##
##   audit.py                                            ##
##                                                       ##
##                Author: Tony Fischetti                 ##
##                        tony.fischetti@gmail.com       ##
##                                                       ##
###########################################################
#
##############################################################################
#                                                                            #
# Copyright (c) 2013, 2014, Tony Fischetti                                   #
#                                                                            #
# MIT License, http://www.opensource.org/licenses/mit-license.php            #
#                                                                            #
# Permission is hereby granted, free of charge, to any person obtaining a    #
# copy of this software and associated documentation files (the "Software"), #
# to deal in the Software without restriction, including without limitation  #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,   #
# and/or sell copies of the Software, and to permit persons to whom the      #
# Software is furnished to do so, subject to the following conditions:       #
#                                                                            #
# The above copyright notice and this permission notice shall be included in #
# all copies or substantial portions of the Software.                        #
#                                                                            #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,   #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL    #
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING    #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER        #
# DEALINGS IN THE SOFTWARE.                                                  #
#                                                                            #
##############################################################################


"""
Various audit actions to check formating and
adherence to specification
"""

from __future__ import unicode_literals
from __future__ import print_function
import sys


def check_integrity(sakefile, verbose):
    """
    Checks the format of the sakefile dictionary
    to ensure it conforms to specification

    Args:
        A dictionary that is the parsed Sakefile (from sake.py)
        A flag indicating verbosity
    Returns:
        True if the Sakefile is conformant
        False if not
    """
    if verbose:
        print("Call to check_integrity issued")
    if not sakefile:
        sys.stderr.write("Sakefile is empty\n")
        return False
    # checking for duplicate targets
    if len(sakefile.keys()) != len(set(sakefile.keys())):
        sys.stderr.write("Sakefile contains duplicate targets\n")
        return False
    for target in sakefile:
        if target == "all":
            if not check_target_integrity(target, sakefile["all"], all=True):
                sys.stderr.write("Failed to accept target 'all'\n")
                return False
            continue
        if "formula" not in sakefile[target]:
            if not check_target_integrity(target, sakefile[target],
                                          meta=True):
                errmes = "Failed to accept meta-target '{}'\n".format(target)
                sys.stderr.write(errmes)
                return False
            for atom_target in sakefile[target]:
                if atom_target == "help":
                    continue
                if not check_target_integrity(atom_target,
                                              sakefile[target][atom_target],
                                              parent=target):
                    errmes = "Failed to accept target '{}'\n".format(
                                                                atom_target)
                    sys.stderr.write(errmes)
                    return False
            continue
        if not check_target_integrity(target, sakefile[target]):
            errmes = "Failed to accept target '{}'\n".format(target)
            sys.stderr.write(errmes)
            return False
    return True


def check_target_integrity(key, values, meta=False, all=False, parent=None):
    """
    Checks the integrity of a specific target. Gets called
    multiple times from check_integrity()

    Args:
        The target name
        The dictionary values of that target
        A boolean representing whether it is a meta-target
        A boolean representing whether it is the "all" target
        A string representing name of parent (default None)

    Returns:
        True is the target is conformant
        False if not
    """

    # logic to audit "all" target
    if all:
        if not values:
            print("Warning: target 'all' is empty")
        # will check if it has unrecognized target later
        return True

    errmes = "target '{}' is not allowed to be missing a help message\n"

    # logic to audit a meta-target
    if meta:
        # check if help is missing
        if "help" not in values:
            sys.stderr.write(errmes.format(key))
            return False
        # checking if empty
        if len(values.keys()) == 1:
            sys.stderr.write("Meta-target '{}' is empty\n".format(key))
            return False
        return True

    # logic to audit any other target
    expected_fields = ["dependencies", "help", "output", "formula"]
    expected_fields = set(expected_fields)
    try:
        our_keys_set = set(values.keys())
    except:
        sys.stderr.write("Error processing target '{}'\n".format(key))
        sys.stderr.write("Are you sure '{}' is a meta-target?\n".format(
                                                                     parent))
        sys.stderr.write("If it's not, it's missing a formula\n")
        return False
    difference = our_keys_set - expected_fields
    if difference:
        print("The following fields were not recognized and will be ignored")
        for item in difference:
            print("  - " + item)
    if "help" not in values:
        sys.stderr.write(errmes.format(key))
        return False
    # can't be missing formula either
    if "formula" not in values:
        sys.stderr.write("Target '{}' is missing formula\n".format(key))
        return False
    return True

########NEW FILE########
__FILENAME__ = build
#!/usr/bin/env python

###########################################################
##                                                       ##
##   build.py                                            ##
##                                                       ##
##                Author: Tony Fischetti                 ##
##                        tony.fischetti@gmail.com       ##
##                                                       ##
###########################################################
#
##############################################################################
#                                                                            #
# Copyright (c) 2013, 2014, Tony Fischetti                                   #
#                                                                            #
# MIT License, http://www.opensource.org/licenses/mit-license.php            #
#                                                                            #
# Permission is hereby granted, free of charge, to any person obtaining a    #
# copy of this software and associated documentation files (the "Software"), #
# to deal in the Software without restriction, including without limitation  #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,   #
# and/or sell copies of the Software, and to permit persons to whom the      #
# Software is furnished to do so, subject to the following conditions:       #
#                                                                            #
# The above copyright notice and this permission notice shall be included in #
# all copies or substantial portions of the Software.                        #
#                                                                            #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,   #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL    #
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING    #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER        #
# DEALINGS IN THE SOFTWARE.                                                  #
#                                                                            #
##############################################################################

"""
Various functions that perform the building with the
dependency resolution
"""

from __future__ import unicode_literals
from __future__ import print_function
import hashlib
import io
import networkx as nx
import os.path
import sys
import yaml
import glob
from subprocess import Popen, PIPE

from . import acts

if sys.version_info[0] < 3:
    import codecs
    old_open = open
    open = codecs.open
else:
    old_open = open


def get_sha(a_file):
    """
    Returns sha1 hash of the file supplied as an argument
    """
    try:
        the_hash = hashlib.sha1(old_open(a_file, "rb").read()).hexdigest()
    except IOError:
        errmes = "File '{}' could not be read! Exiting!\n".format(a_file)
        sys.stdout.write(errmes)
        sys.exit(1)
    except:
        errmes = "Unspecified error returning sha1 hash. Exiting!\n"
        sys.stdout.write(errmes)
        sys.exit(1)
    return the_hash


def write_shas_to_shastore(sha_dict):
    """
    Writes a sha1 dictionary stored in memory to
    the .shastore file
    """
    fh = open(".shastore", "w", encoding="utf-8")
    fh.write("---\n")
    if sha_dict:
        for key in sha_dict:
            fh.write("{}: {}\n".format(key, sha_dict[key]))
    fh.write("...")
    fh.close()


def take_shas_of_all_files(G, verbose):
    """
    Takes sha1 hash of all dependencies and outputs of all targets

    Args:
        The graph we are going to build
        A flag indicating verbosity

    Returns:
        A dictionary where the keys are the filenames and the
        value is the sha1 hash
    """
    sha_dict = {}
    all_files = []
    for target in G.nodes(data=True):
        if verbose:
            print("About to take shas of files in target '{}'".format(
                                                                   target[0]))
        if 'dependencies' in target[1]:
            if verbose:
                print("It has dependencies")
            deplist = []
            for dep in target[1]['dependencies']:
                glist = glob.glob(dep)
                if glist:
                    for oneglob in glist:
                        deplist.append(oneglob)
                else:
                    deplist.append(dep)
            target[1]['dependencies'] = list(deplist)
            for dep in target[1]['dependencies']:
                if verbose:
                    print("  - {}".format(dep))
                all_files.append(dep)
        if 'output' in target[1]:
            if verbose:
                print("It has outputs")
            for out in acts.get_all_outputs(target[1]):
                if verbose:
                    print("  - {}".format(out))
                all_files.append(out)
    if len(all_files):
        for item in all_files:
            if os.path.isfile(item):
                sha_dict[item] = get_sha(item)
        return sha_dict
    if verbose:
        print("No dependencies")


def needs_to_run(G, target, in_mem_shas, from_store, verbose, force):
    """
    Determines if a target needs to run. This can happen in two ways:
    (a) If a dependency of the target has changed
    (b) If an output of the target is missing

    Args:
        The graph we are going to build
        The name of the target
        The dictionary of the current shas held in memory
        The dictionary of the shas from the shastore
        A flag indication verbosity
        A flag indicating whether a rebuild should be forced

    Returns:
        True if the target needs to be run
        False if not
    """
    if(force):
        if verbose:
            print("Target rebuild is being forced so {} needs to run".format(
                                                                      target))
        return True
    node_dict = get_the_node_dict(G, target)
    if 'output' in node_dict:
        for output in acts.get_all_outputs(node_dict):
            if not os.path.isfile(output):
                if verbose:
                    outstr = "Output file '{}' is missing so it needs to run"
                    print(outstr.format(output))
                return True
    if 'dependencies' not in node_dict:
        # if it has no dependencies, it always needs to run
        if verbose:
            print("Target {} has no dependencies and needs to run".format(
                                                                      target))
        return True
    for dep in node_dict['dependencies']:
        # because the shas are updated after all targets build,
        # its possible that the dependency's sha doesn't exist
        # in the current "in_mem" dictionary. If this is the case,
        # then the target needs to run
        if dep not in in_mem_shas:
            if verbose:
                outstr = "Dep '{}' doesn't exist in memory so it needs to run"
                print(outstr.format(dep))
            return True
        now_sha = in_mem_shas[dep]
        if dep not in from_store:
            if verbose:
                outst = "Dep '{}' doesn't exist in shastore so it needs to run"
                print(outst.format(dep))
            return True
        old_sha = from_store[dep]
        if now_sha != old_sha:
            if verbose:
                outstr = "There's a mismatch for dep {} so it needs to run"
                print(outstr.format(dep))
            return True
    if verbose:
        print("Target '{}' doesn't need to run".format(target))
    return False


def run_commands(commands, verbose, quiet):
    """
    Runs the commands supplied as an argument
    It will exit the program if the commands return a
    non-zero code

    Args:
        the commands to run
        A flag indicating verbosity
        A flag indicatingf quiet mode
    """
    commands = commands.rstrip()
    if verbose:
        print("About to run commands '{}'".format(commands))
    if not quiet:
        print(commands)
        p = Popen(commands, shell=True)
    else:
        p = Popen(commands, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    if p.returncode:
        print(err)
        sys.exit("Command failed to run")


def run_the_target(G, target, verbose, quiet):
    """
    Wrapper function that sends to commands in a target's 'formula'
    to run_commands()

    Args:
        The graph we are going to build
        The target to run
        A flag indicating verbosity
        A flag indicating quiet mode
    """
    print("Running target {}".format(target))
    the_formula = get_the_node_dict(G, target)["formula"]
    run_commands(the_formula, verbose, quiet)


def get_the_node_dict(G, name):
    """
    Helper function that returns the node data
    of the node with the name supplied
    """
    for node in G.nodes(data=True):
        if node[0] == name:
            return node[1]


def get_direct_ancestors(G, list_of_nodes):
    """
    Returns a list of nodes that are the parents
    from all of the nodes given as an argument.
    This is for use in the parallel topo sort
    """
    parents = []
    for item in list_of_nodes:
        anc = G.predecessors(item)
        for one in anc:
            parents.append(one)
    return parents


def get_sinks(G):
    """
    A sink is a node with no children.
    This means that this is the end of the line,
    and it should be run last in topo sort. This
    returns a list of all sinks in a graph
    """
    sinks = []
    for node in G.nodes():
        if not G.successors(node):
            sinks.append(node)
    return sinks


def get_levels(G):
    """
    For the parallel topo sort to work, the targets have
    to be executed in layers such that there is no
    dependency relationship between any nodes in a layer.
    What is returned is a list of lists representing all
    the layers, or levels
    """
    levels = []
    ends = get_sinks(G)
    levels.append(ends)
    while get_direct_ancestors(G, ends):
        ends = get_direct_ancestors(G, ends)
        levels.append(ends)
    levels.reverse()
    return levels


def remove_redundancies(levels):
    """
    There are repeats in the output from get_levels(). We
    want only the earliest occurrence (after it's reversed)
    """
    seen = []
    final = []
    for line in levels:
        new_line = []
        for item in line:
            if item not in seen:
                seen.append(item)
                new_line.append(item)
        final.append(new_line)
    return final


def parallel_sort(G):
    """
    Returns a list of list such that the inner lists
    can be executed in parallel (no interdependencies)
    and the outer lists ought to be run in order to
    satisfy dependencies
    """
    levels = get_levels(G)
    return remove_redundancies(levels)


def parallel_run_these(G, list_of_targets, in_mem_shas, from_store,
                       verbose, quiet):
    """
    The parallel equivalent of "run_this_target()"
    It receives a list of targets to execute in parallel.
    Unlike "run_this_target()" it has to update the shas
    (in memory and in the store) withing the function.
    This is because one of the targets may fail but many can
    succeed, and those outputs need to be updated

    Args:
        G
        A graph
        A list of targets that we need to build in parallel
        The dictionary containing the in-memory sha store
        The dictionary containing the contents of the .shastore file
        A flag indicating verbosity
        A flag indicating quiet mode
    """
    if len(list_of_targets) == 1:
        target = list_of_targets[0]
        if verbose:
            print("Going to run target '{}' serially".format(target))
        run_the_target(G, target, verbose, quiet)
        node_dict = get_the_node_dict(G, target)
        if "output" in node_dict:
            for output in acts.get_all_outputs(node_dict):
                if from_store:
                    if output in from_store:
                        in_mem_shas[output] = get_sha(output)
                        write_shas_to_shastore(in_mem_shas)
        return True
    a_failure_occurred = False
    out = "Going to run these targets '{}' in parallel"
    print(out.format(", ".join(list_of_targets)))
    info = [(target, get_the_node_dict(G, target))
              for target in list_of_targets]
    commands = [item[1]['formula'].rstrip() for item in info]
    if not quiet:
        procs = [Popen(command, shell=True) for command in commands]
    else:
        procs = [Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
                   for command in commands]
    for index, process in enumerate(procs):
        if process.wait():
            sys.stderr.write("Target '{}' failed!\n".format(info[index][0]))
            a_failure_occurred = True
        else:
            if "output" in info[index][1]:
                for output in acts.get_all_outputs(info[index][1]):
                    if from_store:
                        if output in from_store:
                            in_mem_shas[output] = get_sha(output)
                            write_shas_to_shastore(in_mem_shas)
    if a_failure_occurred:
        sys.exit("A command failed to run")
    return True


def merge_from_store_and_in_mems(from_store, in_mem_shas):
    """
    If we don't merge the shas from the sha store and if we build a
    subgraph, the .shastore will only contain the shas of the files
    from the subgraph and the rest of the graph will have to be
    rebuilt
    """
    if not from_store:
        return in_mem_shas
    for key in from_store:
        if key not in in_mem_shas:
            in_mem_shas[key] = from_store[key]
    return in_mem_shas


def build_this_graph(G, verbose, quiet, force, recon, parallel):
    """
    This is the master function that performs the building.

    Args:
        A graph (often a subgraph)
        A flag indicating verbosity
        A flag indicating quiet mode
        A flag indicating whether a rebuild should be forced
        A flag indicating whether this is a dry run (recon)
        A flag indicating whether the graph targets should
          build in parallel

    Returns:
        0 if successful
        UN-success results in a fatal error so it will return 0 or nothing
    """
    if verbose:
        print("Checking that graph is directed acyclic")
    if not nx.is_directed_acyclic_graph(G):
        errmes = "Dependency resolution is impossible; "
        errmes += "graph is not directed and acyclic"
        errmes += "\nCheck the Sakefile\n"
        sys.stderr.write(errmes)
        sys.exit(1)
    if verbose:
        print("Dependency resolution is possible")
    in_mem_shas = take_shas_of_all_files(G, verbose)
    from_store = {}
    if not os.path.isfile(".shastore"):
        write_shas_to_shastore(in_mem_shas)
        in_mem_shas = {}
    from_store = yaml.load(open(".shastore", "r").read())
    if not from_store:
        write_shas_to_shastore(in_mem_shas)
        in_mem_shas = {}
        from_store = yaml.load(open(".shastore", "r").read())
    # parallel
    if parallel:
        for line in parallel_sort(G):
            if verbose:
                out = "Checking if targets '{}' need to be run"
                print(out.format(", ".join(line)))
            to_build = []
            for item in line:
                if needs_to_run(G, item, in_mem_shas, from_store, verbose,
                                force):
                    to_build.append(item)
            if to_build:
                if recon:
                    if len(to_build) == 1:
                        out = "Would run target '{}'"
                        print(out.format(to_build[0]))
                    else:
                        out = "Would run targets '{}' in parallel"
                        print(out.format(", ".join(to_build)))
                    continue
                parallel_run_these(G, to_build, in_mem_shas, from_store,
                                   verbose, quiet)
    # not parallel
    else:
        for target in nx.topological_sort(G):
            if verbose:
                outstr = "Checking if target '{}' needs to be run"
                print(outstr.format(target))
            if needs_to_run(G, target, in_mem_shas, from_store, verbose,
                            force):
                if recon:
                    print("Would run target: {}".format(target))
                    continue
                run_the_target(G, target, verbose, quiet)
                node_dict = get_the_node_dict(G, target)
                if "output" in node_dict:
                    for output in acts.get_all_outputs(node_dict):
                        if from_store:
                            if output in from_store:
                                in_mem_shas[output] = get_sha(output)
    if recon:
        return 0
    in_mem_shas = take_shas_of_all_files(G, verbose)
    if in_mem_shas:
        in_mem_shas = merge_from_store_and_in_mems(from_store, in_mem_shas)
        write_shas_to_shastore(in_mem_shas)
    print("Done")
    return 0


########NEW FILE########
__FILENAME__ = constants
#!/usr/bin/env python

###########################################################
##                                                       ##
##   constants.py                                        ##
##                                                       ##
##                Author: Tony Fischetti                 ##
##                        tony.fischetti@gmail.com       ##
##                                                       ##
###########################################################
#
##############################################################################
#                                                                            #
# Copyright (c) 2013, 2014, Tony Fischetti                                   #
#                                                                            #
# MIT License, http://www.opensource.org/licenses/mit-license.php            #
#                                                                            #
# Permission is hereby granted, free of charge, to any person obtaining a    #
# copy of this software and associated documentation files (the "Software"), #
# to deal in the Software without restriction, including without limitation  #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,   #
# and/or sell copies of the Software, and to permit persons to whom the      #
# Software is furnished to do so, subject to the following conditions:       #
#                                                                            #
# The above copyright notice and this permission notice shall be included in #
# all copies or substantial portions of the Software.                        #
#                                                                            #
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,   #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL    #
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING    #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER        #
# DEALINGS IN THE SOFTWARE.                                                  #
#                                                                            #
##############################################################################

from __future__ import unicode_literals
from __future__ import print_function

# Version number
VERSION = "0.9.4"

# Name of application
NAME = 'master-sake'

# Title of project
TITLE = 'Sake'

# Main description
DESCRIPTION = 'A self-documenting build automation tool'

# Website for project
URL = 'http://tonyfischetti.github.io/sake'

# Git URL
SOURCE_URL = 'https://github.com/tonyfischetti/sake'

# Author name
AUTHOR_NAME = "Tony Fischetti"

# Author email
AUTHOR_EMAIL = "tony.fischetti@gmail.com"

########NEW FILE########
