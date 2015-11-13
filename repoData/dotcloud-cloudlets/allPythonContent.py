__FILENAME__ = cloudlets

import os
import re
import sys
import shutil
import tarfile
import subprocess
from tempfile import mkdtemp, mktemp
from distutils.dir_util import copy_tree

import js
import metashelf
import vm2vm.raw
import jsonschema
import simplejson as json
from ejs import EJSTemplate
import mercurial.hg, mercurial.ui, mercurial.error, mercurial.dispatch

class DictSchema(dict):
    """ An object in the JSON-Schema format """

    def __init__(self, *args, **kw):
        input = dict(*args, **kw)
        if "type" in input:
            dict.__init__(self, input)
        else:
            dict.__init__(self, {"type": "object", "properties": input})
        if "properties" in self:
            for (k, prop) in self["properties"].items():
                if "type" not in prop:
                    self["properties"][k] = dict(DictSchema(prop))

    @property
    def defaults(self):
        return dict(
            (k, prop["default"])
            for (k, prop) in self.get("properties", {}).items()
            if "default" in prop
        )

    def validate(self, data):
        data = dict(self.defaults, **data)
        jsonschema.validate(data, dict(self))
        return data


def filter_path(path, include, exclude):
    if not hasattr(include, "__iter__"):
        include = [include]
    if not hasattr(exclude, "__iter__"):
        exclude = [exclude]
    def match_filters(path, filters):
        return any([f.match(path) if hasattr(f, "match") else f == path for f in filters])
    return match_filters(path, include) or not match_filters(path, exclude)

class Manifest(dict):
    """A dictionary holding an image's metadata"""

    kernel = {
            "optional"      : True,
            "type"          : "object",
            "description"   : "Kernel version information",
            "properties"    : {
                "os"        : {"optional" : True, "type": "string", "description": "Operating system"},
                "version"   : {"optional" : True, "type": "string", "description": "Version"},
                "flavor"    : {"optional" : True, "type": "string", "description": "Flavor"},
            },
    }

    specs = DictSchema(
        {
            "name"          : {"optional": True,  "type": "string", "description": "User defined name"},
            "description"   : {"optional": True,  "type": "string", "description": "User defined description"},
            "arch"          : {"optional": True,  "type": "string", "description": "Hardware architecture. example: i386"},
            "args"          : {"optional": True,  "type": "object", "description": "List of accepted user-specified configuration arguments", "default": {}},
            "templates"     : {"optional": True,  "type": "array", "description": "List of files which are templates", "default": []},
            "persistent"    : {"optional": True,  "type": "array", "description": "List of files or directories holding persistent data", "default": []},
            "volatile"      : {"optional": True,  "type": "array", "description": "List of patterns for files whose changes should be ignored", "default": []},
            "entry_points"  : {
                "optional"      : True,
                "default"       : {},
                "type"          : "object",
                "description"   : "List of entry points available for this image",
                "properties"    : {
                    "kernel"    : kernel,
                    "init"      : {
                        "optional"      : True,
                        "type"          : "object",
                        "description"   : "Kernel requirements",
                        "properties"    : {
                            "kernel" : kernel
                        }
                    },
                    "chroot"    : {
                        "optional"      : True,
                        "type"          : "object",
                        "description"   : "Chroot command and enter & exit hooks",
                        "properties"    : {
                            "command" : {"optional": True, "type": "string", "description": "Command to execute on chroot"},
                            "enter" : {"optional": True, "type": "string", "description": "Hook to execute when entering"},
                            "exit" : {"optional": True, "type": "string", "description": "Hook to execute when exiting"}
                        }
                    }
                }
            }
        }
    )
    
    def get_args_schema(self):
        """ Return the json schema which will be used to validate the user-specified arguments as part of the image's overall configuration. """
        return DictSchema(self.get("args", {}))
    args_schema = property(get_args_schema)

    def get_config_schema(self):
        """ Return the json schema which will be used to validate this image's configuration. """
        return  ConfigAndArgsSchema(
                    config_schema = {
                        "dns": {
                            "nameservers": {"type": "array"}
                        },
                        "ip": {
                            "interfaces": {"type": "array"}
                        }
                    },
                    args_schema = self.args_schema
                )
    config_schema = property(get_config_schema)

    def validate(self):
        """Validate contents of the manifest against the cloudlets spec"""
        return self.specs.validate(self)

    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self.update(self.validate())

class ConfigAndArgsSchema(object):

    def __init__(self, config_schema, args_schema):
        self.config_schema = DictSchema(config_schema)
        self.args_schema = DictSchema(args_schema)

    def validate(self, data):
        config = dict((k, v) for (k, v) in data.items() if k != "args")
        args = data.get("args", {})
        return dict(
            self.config_schema.validate(config),
            args=self.args_schema.validate(args)
        )

class Image(object):

    def __init__(self, path, manifest=None):
        if not os.path.isdir(path):
            raise ValueError("%s doesn't exist or is not a directory" % path)
        self.path = os.path.abspath(path)
        self.__manifest_file = manifest

    def raw(self, out, config, size, **filters):
        """ Create a raw image of the cloudlet """
        with vm2vm.raw.RawImage(out, "w") as img:
            img.mkfs(size)
            with vm2vm.raw.Mountpoint(img.name) as mnt:
                self.copy(dest=mnt, config=config, **filters)

    def ec2(self, out, name, config, size, ec2_user, ec2_cert_path, ec2_pk_path, kernel, ramdisk, register=False, access_key=None, secret_key=None, bucket_name=None, region=None, **filters):
        image = mktemp()
        self.raw(image, config, size, **filters)
        try:
            bundle = vm2vm.ec2.create_bundle(image_path=image, arch=self.manifest["arch"], name=name, ec2_user=ec2_user, ec2_cert_path=ec2_cert_path, ec2_pk_path=ec2_pk_path, kernel=kernel, ramdisk=ramdisk)
            os.rename(bundle, out)
            if register:
                vm2vm.ec2.upload_bundle(out, access_key, secret_key, region, bucket_name)
                vm2vm.ec2.register_bundle(path=out, name=name, private_key=ec2_pk_path, cert=ec2_cert_path, region=region, bucket_name=bucket_name)
        finally:
            if os.path.exists(image):
                os.unlink(image)

    def copy(self, dest=None, *args, **kw):
        """ Copy the image to a new directory at <dest>. If dest is None, a temporary directory is created. <dest> is returned. All options are passed to Image.tar() for lossless transfer. """
        if dest is None:
            dest = mkdtemp()
        tmptar = file(mktemp(), "wb")
        self.tar(out=tmptar, *args, **kw)
        tmptar.close()
        tarfile.open(tmptar.name, "r").extractall(dest)
        return dest

    def tar(self, out=sys.stdout, config=None, *args, **kw):
        """ Wrap the image in an uncompressed tar stream, ignoring volatile files, and write it to stdout """
        if config is not None:
            config = self.manifest.config_schema.validate(config)
            if self.manifest.get("templates"):
                templates_dir = self.copy(templates=True)
                for template in self.find(templates=True):
                    EJSTemplate(templates_dir + template).apply(templates_dir + template, config)
        tar = tarfile.open("", mode="w|", fileobj=out)
        templates = self.manifest.get("templates")
        for path in self.find(*args, **kw):
            if config and path in templates:
                real_path = templates_dir + path
                EJSTemplate(real_path).apply(real_path, config)
            else:
                real_path = self.unchroot_path(path)
            tar.add(real_path, path, recursive=False)
        tar.close()

    def get_files(self, include=[], exclude=[]):
        """ Iterate over all paths in the image. Paths are "chrooted", ie. relative to the image with a prefix of "/" """
        for (basepath, dpaths, fpaths) in os.walk(self.path, topdown=True):
            for subpath in dpaths + fpaths:
                path = os.path.join(self.chroot_path(basepath), subpath)
                if filter_path(path, include, exclude):
                    yield path
    files = property(get_files)

    def chroot_path(self, path):
        if self.path == "/":
            return path
        if os.path.normpath(path) == self.path:
            return "/"
        return path.replace(self.path, "")

    def unchroot_path(self, path):
        return os.path.join(self.path, re.sub("^/+", "", path))

    def find(self, templates=False, volatile=False, persistent=False, other=False):
        include = []
        exclude = []
        if other:
            if not templates:
                exclude += self.manifest.get("templates", [])
            if not volatile:
                exclude += map(re.compile, self.manifest.get("volatile", []))
            if not persistent:
                exclude += [re.compile("^{0}($|/)".format(p)) for p in self.manifest.get("persistent", [])]
        else:
            exclude = re.compile(".*")
            if templates:
                include += self.manifest.get("templates", [])
            if volatile:
                include += map(re.compile, self.manifest.get("volatile", []))
            if persistent:
                include += [re.compile("^{0}($|/)".format(p)) for p in self.manifest.get("persistent", [])]
        return self.get_files(include=include, exclude=exclude)

    def get_cloudletdir(self):
        """ Return the path of the directory containing the image's metadata. """
        return os.path.join(self.path, ".cloudlet")
    cloudletdir = property(get_cloudletdir)

    def get_manifestfile(self):
        """ Return the manifest file containing the image's metadata. """
        if self.__manifest_file is None:
            return os.path.join(self.cloudletdir, "manifest")
        return self.__manifest_file
    manifestfile = property(get_manifestfile)

    def get_manifest(self):
        """ Return a dictionary containing the image's metadata. """
        if os.path.exists(self.manifestfile):
            return Manifest(json.loads(file(self.manifestfile).read()))
        return Manifest({})
    manifest = property(get_manifest)

    def get_config_file(self):
        """ Return the path to the file holding the currently applied configuration. If no configuration is applied, the file should not exist. """
        return os.path.join(self.cloudletdir, "applied_config")
    config_file = property(get_config_file)

    def get_config(self):
        """ Return a dictionary holding the configuration currently applied on the image. If no config is applied, return None."""
        if not os.path.exists(self.config_file):
            return None
        return json.loads(file(self.config_file).read())

    def set_config(self, config):
        """ Apply a new configuration on the image. If a configuration is already in place, an exception will be raised. """
        if self.config:
            raise ValueError("Already configured: %s" % self.config)
        file(self.config_file, "w").write("")
        config = self.manifest.config_schema.validate(config)
        for template in self.manifest.get("templates", []):
            print "Applying template %s with %s" % (template, config)
            EJSTemplate(self.unchroot_path(template)).apply(self.unchroot_path(template), config)
        file(self.config_file, "w").write(json.dumps(config, indent=1))

    def overlay(self, overlay):
        manifest = self.manifest
        copy_tree(overlay, self.path)
        overlay_manifest = Image(overlay).manifest
        overlay_entry_points = overlay_manifest['entry_points']
        manifest['persistent'] = list(set(manifest['persistent'] + overlay_manifest['persistent']))
        manifest['volatile'] = list(set(manifest['volatile'] + overlay_manifest['volatile']))
        for entry_point in overlay_entry_points.keys():
            manifest['entry_points'][entry_point] = overlay_entry_points[entry_point]
        file(self.manifestfile, 'w').write(json.dumps(manifest, indent=4))

    def hg(self, *cmd):
        """ Run a mercurial command, using the image as a repository """
        hgrc_path = os.path.join(self.path, ".hg", "hgrc")
        hgignore_path = os.path.join(self.path, ".hgignore")
        if os.path.exists(hgrc_path):
            os.unlink(hgrc_path)
        if os.path.exists(hgignore_path):
            os.unlink(hgignore_path)
        try:
            repo = mercurial.hg.repository(mercurial.ui.ui(), path=self.path, create=False)
        except mercurial.error.RepoError:
            repo = mercurial.hg.repository(mercurial.ui.ui(), path=self.path, create=True)
        ignore = ["^.hgignore$"] + [re.sub("^/", "^", p) for p in self.manifest.get("volatile", [])]
        file(hgignore_path, "w").write("\n".join(ignore))
        hgrc = """[hooks]
pre-commit.metashelf = python:metashelf.hg.hook_remember
pre-status.metashelf = python:metashelf.hg.hook_remember
pre-diff.metashelf = python:metashelf.hg.hook_remember
post-update.metashelf = python:metashelf.hg.hook_restore
        """
        file(hgrc_path, "w").write(hgrc)
        mercurial.dispatch.dispatch(list(("-R", self.path) + cmd))

    def chroot(self, *cmd):
        cmd = list(cmd)
        chroot = self.manifest['entry_points'].get('chroot', {})
        if not cmd:
            cmd = chroot.get('command', '').split()
        enter = chroot.get('enter', '').split()
        if enter:
            subprocess.call(["chroot", self.path] + enter)
        subprocess.call(["chroot", self.path] + cmd)
        exit = chroot.get('exit', '').split()
        if exit:
            subprocess.call(["chroot", self.path] + exit)

    config = property(get_config, set_config)


########NEW FILE########
__FILENAME__ = tests

from unittest import TestCase
import cloudlets


class TestSchema(TestCase):

    def test_a(self):
        input = {"foo": {"type": "string"}, "bar": {"type": "string"}}
        self.assertEqual(cloudlets.DictSchema(input), {"type": "object", "properties": input})

    def test_validate_default_used(self):
        input = {"foo": {"type": "string", "default": "abc"}}
        self.assertEqual(cloudlets.DictSchema(input).validate({}), {"foo": "abc"})

    def test_validate_default_not_used(self):
        input = {"foo": {"type": "string", "default": "abc"}}
        self.assertEqual(cloudlets.DictSchema(input).validate({"foo": "bar"}), {"foo": "bar"})

    def test_validate_no_default(self):
        input = {"foo": {"type": "string"}}
        self.assertEqual(cloudlets.DictSchema(input).validate({"foo": "bar"}), {"foo": "bar"})

    def test_noop(self):
        schema = {"type": "string", "optional": True}
        self.assertEqual(cloudlets.DictSchema(schema), schema)

class TestManifest(TestCase):

    manifest_min = cloudlets.Manifest({
                "arch"      : "i386",
                "volatile"  : []
            })

    manifest_simple_args = cloudlets.Manifest(manifest_min,
            args = {"hostname": {"type": "string", "default": "noname"}}
            )
    

    def test_smallest_possible(self):
        self.manifest_min.validate()

    def test_args_schema(self):
        self.assertEqual(self.manifest_simple_args.args_schema.validate({"hostname": "foo"}), {"hostname": "foo"})
        self.assertEqual(self.manifest_simple_args.args_schema.validate({}), {"hostname": "noname"})

    def test_config_schema(self):
        config_in  = {"dns": {"nameservers": []}, "ip": {"interfaces": []}, "args": {}}
        config_out = {"dns": {"nameservers": []}, "ip": {"interfaces": []}, "args": {"hostname": "noname"}}
        self.assertEqual(self.manifest_simple_args.config_schema.validate(config_in), config_out)

    def test_defaults(self):
        self.assertEqual(self.manifest_min.validate()["templates"], [])
        self.assertEqual(self.manifest_min.validate()["persistent"], [])

########NEW FILE########
