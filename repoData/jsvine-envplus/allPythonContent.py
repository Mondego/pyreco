__FILENAME__ = cli
#!/usr/bin/env python
import sys, os
import argparse
from subprocess import Popen
from envplus import pathfile, helpers
if "VIRTUAL_ENV" not in os.environ:
    raise Exception("$VIRTUAL_ENV missing. It seems you're not currently in a virtualenv.")
else: pass

def run_in_env(pf, args):
    env = os.environ.copy()
    paths = env["PATH"].split(":")
    bin_paths = pf.get_binpaths()
    new_paths = paths[:1] + bin_paths + paths[1:]
    env["PATH"] = ":".join(new_paths)
    sp = Popen(args, env=env)
    out, err = sp.communicate()
    return out

def cmd_add(pf, args):
    map(pf.add_env, args.envs)
    pf.save()

def cmd_rm(pf, args):
    map(pf.remove_env, args.envs)
    pf.save()

def cmd_pause(pf, args):
    envs = args.envs if len(args.envs) else pf.ls()
    map(pf.pause_env, envs)
    pf.save()

def cmd_resume(pf, args):
    envs = args.envs if len(args.envs) else pf.ls_paused()
    map(pf.resume_env, envs)
    pf.save()

def cmd_ls(pf, args):
    active = set(pf.ls())
    paused = set(pf.ls_paused())
    envs = (paused if args.paused else active) | \
        ((paused | active) if args.all else set())
    out = "".join(e + "\n" for e in envs)
    sys.stdout.write(out)

def cmd_cat(pf, args):
    sys.stdout.write(pf.to_string())

def cmd_edit(pf, args):
    editor = os.environ["EDITOR"]
    run_in_env(pf, [ editor, pf.filepath ])

def cmd_path(pf, args):
    sys.stdout.write(pf.filepath + "\n")

def cmd_run(pf, args):
    command = " ".join(args.cmd)
    run_in_env(pf, [ os.environ["SHELL"], "-c", "-i", command ])

def parse_args():
    parser = argparse.ArgumentParser(description="Combine your virtualenvs.", prog="envplus")
    subparsers = parser.add_subparsers(title="Subcommands", dest="command")

    # envplus add
    parser_add = subparsers.add_parser("add")
    parser_add.add_argument("envs",
        nargs="+",
        help="virtualenvs to add to current virtualenv's path")

    # envplus rm
    parser_rm = subparsers.add_parser("rm")
    parser_rm.add_argument("envs",
        nargs="+",
        help="virtualenvs to remove from current virtualenv's path")

    # envplus pause
    parser_pause = subparsers.add_parser("pause")
    parser_pause.add_argument("envs",
        nargs="*",
        help="virtualenvs to pause. Defaults to all.")

    # envplus resume
    parser_resume = subparsers.add_parser("resume")
    parser_resume.add_argument("envs",
        nargs="*",
        help="virtualenvs to resume. Defaults to all.")

    # envplus ls
    parser_ls = subparsers.add_parser("ls")
    parser_ls.add_argument("--paused", "-p",
        action="store_true",
        help="Show paused virtualenvs instead of active ones.")
    parser_ls.add_argument("--all", "-a",
        action="store_true",
        help="Show paused *and* active virtualenvs")

    # envplus run
    parser_run = subparsers.add_parser("run")
    parser_run.add_argument("cmd",
        nargs=argparse.REMAINDER,
        help="Command to run, with optional arguments.")

    # envplus path
    parser_path = subparsers.add_parser("path")

    # envplus cat
    parser_cat = subparsers.add_parser("cat")

    # envplus edit
    parser_edit = subparsers.add_parser("edit")

    args = parser.parse_args()
    return args

def get_pathfile_path(pathfile_name="_envplus.pth"):
    sp_dir = helpers.get_site_packages_dir(os.environ["VIRTUAL_ENV"])
    pathfile_path = os.path.join(sp_dir, pathfile_name)
    return pathfile_path

def dispatch_command(args):
    commands = {
        "run": cmd_run,
        "add": cmd_add,
        "rm": cmd_rm,
        "pause": cmd_pause,
        "resume": cmd_resume,
        "ls": cmd_ls,
        "cat": cmd_cat,
        "path": cmd_path,
        "edit": cmd_edit,
    } 
    pf = pathfile.PathFile(get_pathfile_path())
    commands[args.command](pf, args)

def main():
    args = parse_args()
    dispatch_command(args)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = env
import re
import os

class Env(object):
    @classmethod
    def from_line(cls, line):
        pause_pattern = r"^(?P<pause># *)"
        path = re.sub(pause_pattern, "", line)
        split = path.split("/")
        name = split[4]
        paused = bool(re.match(pause_pattern, line))
        return cls(name, path, paused)

    def __init__(self, name, path, paused=False):
        self.name = name
        self.path = path
        self.paused = paused

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def to_string(self):
        return (self.paused * "# ") + self.path

########NEW FILE########
__FILENAME__ = helpers
import os
from glob import glob
try: from collections import OrderedDict
except: from ordereddict import OrderedDict

def get_site_packages_dir(envname):
    sections = [
        os.environ["WORKON_HOME"],
        envname,
        "lib",
        "*",
        "site-packages"
    ]
    joined = os.path.join(*sections)
    matching = glob(joined)
    return matching[0] if len(matching) else None


########NEW FILE########
__FILENAME__ = pathfile
import os
import re
from envplus.env import Env
from envplus.helpers import OrderedDict, get_site_packages_dir

linebreak_pattern = re.compile(r"[\n\r]")

class PathFile(object):
    def __init__(self, filepath):
        self.filepath = filepath
        self.envs = self.load()

    def read_pathfile(self):
        if os.path.isfile(self.filepath):
            with open(self.filepath) as f:
                return f.read()
        else: return ""

    def load(self):
        raw = self.read_pathfile()
        lines = [ x.strip()
            for x in re.split(linebreak_pattern, raw)
            if x.strip() ]
        env_list = map(Env.from_line, lines)
        env_names = [ env.name for env in env_list ]
        envs = OrderedDict(zip(env_names, env_list))
        return envs

    def add_env(self, envname):
        sp_dir = get_site_packages_dir(envname)
        if not sp_dir:
            raise Exception("Could not find virtualenv named {}".format(envname))
        if envname in self.envs: del self.envs[envname] 
        local_sp = os.path.split(self.filepath)[0]
        rel = os.path.relpath(sp_dir, local_sp)
        self.envs[envname] = Env(envname, rel)

    def check_env(self, envname):
        if not envname in self.envs:
            raise Exception("No virtualenv named {}".format(envname))

    def remove_env(self, envname):
        self.check_env(envname)
        del self.envs[envname]

    def pause_env(self, envname):
        self.check_env(envname)
        self.envs[envname].pause()        

    def resume_env(self, envname):
        self.check_env(envname)
        self.envs[envname].resume()        

    def to_string(self):
        lines = [ env.to_string() for env in self.envs.values() ]
        joined = "\n".join(lines)
        return joined + "\n"

    def save(self):
        with open(self.filepath, "w") as f:
            content = self.to_string()
            f.write(content)

    def ls(self):
        return [ key for key,env in self.envs.items()
            if not env.paused ]

    def ls_paused(self):
        return [ key for key,env in self.envs.items()
            if env.paused ]

    def get_binpaths(self):
        workon = os.environ["WORKON_HOME"]
        tmpl = os.path.join("{0}", "{1}", "bin")
        def to_binpath(envname):
            return tmpl.format(workon, envname)
        return map(to_binpath, self.ls())

########NEW FILE########
