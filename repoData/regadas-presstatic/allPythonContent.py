__FILENAME__ = builder
# -*- coding: utf-8 -*-

import os
import shutil

from jinja2 import Environment, FileSystemLoader
from webassets import Environment as AssetsEnvironment
from webassets.ext.jinja2 import AssetsExtension
from webassets.loaders import YAMLLoader


class TemplateBuilder(object):

    def __init__(self, path, output,
                 static_path='static', static_url='static',
                 asset_config='config.yml'):
        self.path = path
        self.output = output
        self.output_path = os.path.join(path, output)
        self.env = Environment(loader=FileSystemLoader(path),
                               extensions=[AssetsExtension])

        try:
            config_path = os.path.join(self.path, asset_config)
            asset_config = YAMLLoader(config_path)
            self.assets_env = asset_config.load_environment()
        except IOError:
            self.assets_env = AssetsEnvironment()

        if 'directory' not in self.assets_env.config:
            self.assets_env.directory = self.output_path

        if 'url' not in self.assets_env.config:
            self.assets_env.url = static_url

        self.assets_env.load_path = [self.path]
        self.env.assets_environment = self.assets_env

    def build_template(self, template, context={}):
        tmpl = self.env.get_template(template)
        dump_path = os.path.join(self.output_path, template)
        tmpl.stream().dump(dump_path)

    def list_files(self):
        templates, other = set(), set()

        if getattr(self.assets_env, '_named_bundles', None):
            bundles = [fp for name, bundle in self.assets_env._named_bundles.iteritems()
                       for fp in bundle.contents]
        else:
            bundles = []

        for dirpath, dirnames, filenames in os.walk(self.path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename) \
                    [len(self.path):].strip(os.path.sep).replace(os.path.sep, '/')
                if filepath[:2] == './':
                    filepath = filepath[2:]
                if self.output in filepath or filepath in bundles:
                    continue

                elif '.html' in filepath:
                    templates.add(filepath)
                else:
                    other.add(filepath)

        return sorted(templates), sorted(bundles), sorted(other)


class SiteBuilder(object):

    def __init__(self, path, output='public', tmpl_builder_class=TemplateBuilder, **kwargs):

        self.path = path
        self.output_path = os.path.join(path, output)

        self.tmpl_builder = tmpl_builder_class(self.path, output, **kwargs)

    def build(self):
        if not os.path.exists(self.output_path):
            os.mkdir(self.output_path)

        templates, bundles, others = self.tmpl_builder.list_files()

        for template in templates:
            # XXX: for now we are not handling contexts
            self.tmpl_builder.build_template(template)

        for other in others:
            dirname = os.path.join(self.output_path, os.path.dirname(other))
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            shutil.copyfile(os.path.join(self.path, other), os.path.join(self.output_path, other))

########NEW FILE########
__FILENAME__ = help
from string import Template

s3_setup = Template("""
Go to https://console.aws.amazon.com/s3 select your bucket and
add a bucket policy. Here's an example:

{
  "Version":"2008-10-17",
  "Statement":[{
    "Sid":"AddPerm",
        "Effect":"Allow",
      "Principal": {
            "AWS": "*"
         },
      "Action":["s3:GetObject"],
      "Resource":["arn:aws:s3:::$bucket/*"
      ]
    }
  ]
}

For more info you should see:
http://docs.aws.amazon.com/AmazonS3/latest/dev/website-hosting-custom-domain-walkthrough.html
""").substitute
########NEW FILE########
__FILENAME__ = http
# -*- coding: utf-8 -*-

import os
import SocketServer
import SimpleHTTPServer
from threading import Thread


class HttpServer(object):

    def __init__(self, host, port, root_dir):
        os.chdir(root_dir)

        handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        self.server = SocketServer.TCPServer((host, int(port)), handler, False)
        self.server.allow_reuse_address = True

    def start(self):
        self.server.server_bind()
        self.server.server_activate()

        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.start()

    def stop(self):
        self.server.shutdown()
        self.server_thread.join()

########NEW FILE########
__FILENAME__ = s3
# -*- coding: utf-8 -*-

import os

from boto.s3.key import Key
from boto.s3.connection import S3Connection

from presstatic.storage import Storage, FileStorageIntent


class S3FileStorageIntent(FileStorageIntent):

    def __init__(self, from_path, to_path, bucket):
        super(S3FileStorageIntent, self).__init__(from_path, to_path)
        self.bucket = bucket

    def store(self):
        k = Key(self.bucket)
        k.key = self.to_path
        k.set_contents_from_filename(self.from_path)


class S3Storage(Storage):

    def __init__(self, bucket_name):
        self.connection = S3Connection(os.environ.get('AWS_ACCESS_KEY_ID'),
                                       os.environ.get('AWS_SECRET_ACCESS_KEY'))
        self.bucket = self.connection.create_bucket(bucket_name)

    def storage_intent(self, from_path, to_path):
        return S3FileStorageIntent(from_path, to_path, self.bucket)

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-

import hashlib


def hashfile(path, algorithm='md5', blocksize=65536):
    hasher = hashlib.new(algorithm)
    with open(path, 'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        return hasher.hexdigest()

########NEW FILE########
__FILENAME__ = watcher
# -*- coding: utf-8 -*-

import logging

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class BaseWatcher(object):

    def __init__(self, path, recursive=True):
        self.path = path
        self.recursive = recursive
        self.observer = Observer()

    def event_handler(self):
        raise NotImplementedError()

    def start(self):
        handler = self.event_handler()
        self.observer.schedule(handler, self.path, self.recursive)
        self.observer.start()

    def stop(self):
        self.observer.stop()


class EventHandler(PatternMatchingEventHandler):

    def __init__(self, builder):
        self.builder = builder
        ignore = '{0}*'.format(builder.output_path)
        super(EventHandler, self).__init__(ignore_patterns=[ignore])

    # XXX: we should not build everything on every event. Works for now
    def on_any_event(self, event):
        super(EventHandler, self).on_any_event(event)
        self.builder.build()

    def on_moved(self, event):
        super(EventHandler, self).on_moved(event)

        what = 'directory' if event.is_directory else 'file'
        logging.info("Moved %s: from %s to %s", what, event.src_path,
                     event.dest_path)

    def on_created(self, event):
        super(EventHandler, self).on_created(event)

        what = 'directory' if event.is_directory else 'file'
        logging.info("Created %s: %s", what, event.src_path)

    def on_deleted(self, event):
        super(EventHandler, self).on_deleted(event)

        what = 'directory' if event.is_directory else 'file'
        logging.info("Deleted %s: %s", what, event.src_path)

    def on_modified(self, event):
        super(EventHandler, self).on_modified(event)

        what = 'directory' if event.is_directory else 'file'
        logging.info("Modified %s: %s", what, event.src_path)


class Watcher(BaseWatcher):

    def __init__(self, builder, **kwargs):
        super(Watcher, self).__init__(builder.path, **kwargs)
        self.builder = builder

    def event_handler(self):
        return EventHandler(self.builder)

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import signal
import argparse
import logging

from clint.textui import colored, puts, indent

from presstatic import help
from presstatic.builder import SiteBuilder
from presstatic.storage import s3
from presstatic.http import HttpServer
from presstatic.watcher import Watcher


http_server = None
watcher = None

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


def signal_handler(signal, frame):
    puts('You pressed Ctrl+C!')

    if http_server:
        http_server.stop()
    if watcher:
        watcher.stop()

    sys.exit(0)


def main():
    global http_server, watcher

    cli_parser = argparse.ArgumentParser(prog='presstatic')
    cli_parser.add_argument('-output',
                            help="relative directory for the generated files.",
                            default='public')
    cli_parser.add_argument('-http',
                            metavar='HOST:PORT',
                            help="creates an HTTP Server with <directory> as root dir.")
    cli_parser.add_argument('-s3',
                            help="deploy on the specified S3 bucket.",
                            metavar='bucket')
    cli_parser.add_argument('directory',
                            help='directory containing the static website.')

    cli_args = cli_parser.parse_args()

    site_builder = SiteBuilder(cli_args.directory, output=cli_args.output)
    site_builder.build()

    if cli_args.http:
        signal.signal(signal.SIGINT, signal_handler)

        host, port = cli_args.http.split(':')
        root_dir = os.path.join(cli_args.directory, cli_args.output)

        http_server = HttpServer(host, port, root_dir)
        http_server.start()

        watcher = Watcher(site_builder)
        watcher.start()

        with indent(4, quote='>>'):
            puts(colored.green("Serving {path} @ {host}:{port}".format(path=root_dir,
                                                                       host=host,
                                                                       port=port)))

        signal.pause()

    elif cli_args.s3:
        s3.S3Storage(cli_args.s3).store(site_builder.output_path)
        puts(help.s3_setup(bucket=cli_args.s3))


if __name__ == '__main__':
    main()

########NEW FILE########
