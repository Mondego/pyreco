__FILENAME__ = engine
# -*- coding: utf-8 -*-
"""
Implements the hyde entry point commands
"""
from hyde.exceptions import HydeException
from hyde.layout import Layout, HYDE_DATA
from hyde.model import Config
from hyde.site import Site
from hyde.version import __version__

from commando import (
    Application,
    command,
    store,
    subcommand,
    true,
    version
)
from commando.util import getLoggerWithConsoleHandler
from fswrap import FS, Folder

HYDE_LAYOUTS = "HYDE_LAYOUTS"


class Engine(Application):

    def __init__(self, raise_exceptions=False):
        logger = getLoggerWithConsoleHandler('hyde')
        super(Engine, self).__init__(
            raise_exceptions=raise_exceptions,
            logger=logger
        )

    @command(description='hyde - a python static website generator',
        epilog='Use %(prog)s {command} -h to get help on individual commands')
    @true('-v', '--verbose', help="Show detailed information in console")
    @true('-x', '--raise-exceptions', default=None,
        help="Don't handle exceptions.")
    @version('--version', version='%(prog)s ' + __version__)
    @store('-s', '--sitepath', default='.', help="Location of the hyde site")
    def main(self, args):
        """
        Will not be executed. A sub command is required. This function exists
        to provide common parameters for the subcommands and some generic stuff
        like version and metadata
        """
        sitepath = Folder(args.sitepath).fully_expanded_path
        if args.raise_exceptions in (True, False):
            self.raise_exceptions = args.raise_exceptions
        return Folder(sitepath)

    @subcommand('create', help='Create a new hyde site.')
    @store('-l', '--layout', default='basic', help='Layout for the new site')
    @true('-f', '--force', default=False, dest='overwrite',
                            help='Overwrite the current site if it exists')
    def create(self, args):
        """
        The create command. Creates a new site from the template at the given
        sitepath.
        """
        sitepath = self.main(args)
        markers = ['content', 'layout', 'site.yaml']
        exists = any((FS(sitepath.child(item)).exists for item in markers))

        if exists and not args.overwrite:
            raise HydeException(
                    "The given site path [%s] already contains a hyde site."
                    " Use -f to overwrite." % sitepath)
        layout = Layout.find_layout(args.layout)
        self.logger.info(
            "Creating site at [%s] with layout [%s]" % (sitepath, layout))
        if not layout or not layout.exists:
            raise HydeException(
            "The given layout is invalid. Please check if you have the"
            " `layout` in the right place and the environment variable(%s)"
            " has been setup properly if you are using custom path for"
            " layouts" % HYDE_DATA)
        layout.copy_contents_to(args.sitepath)
        self.logger.info("Site creation complete")

    @subcommand('gen', help='Generate the site')
    @store('-c', '--config-path', default='site.yaml', dest='config',
            help='The configuration used to generate the site')
    @store('-d', '--deploy-path', dest='deploy', default=None,
                        help='Where should the site be generated?')
    @true('-r', '--regen', dest='regen', default=False,
                        help='Regenerate the whole site, including unchanged files')
    def gen(self, args):
        """
        The generate command. Generates the site at the given
        deployment directory.
        """
        sitepath = self.main(args)
        site = self.make_site(sitepath, args.config, args.deploy)
        from hyde.generator import Generator
        gen = Generator(site)
        incremental = True
        if args.regen:
            self.logger.info("Regenerating the site...")
            incremental = False
        gen.generate_all(incremental=incremental)
        self.logger.info("Generation complete.")

    @subcommand('serve', help='Serve the website')
    @store('-a', '--address', default='localhost', dest='address',
            help='The address where the website must be served from.')
    @store('-p', '--port', type=int, default=8080, dest='port',
            help='The port where the website must be served from.')
    @store('-c', '--config-path', default='site.yaml', dest='config',
            help='The configuration used to generate the site')
    @store('-d', '--deploy-path', dest='deploy', default=None,
                    help='Where should the site be generated?')
    def serve(self, args):
        """
        The serve command. Serves the site at the given
        deployment directory, address and port. Regenerates
        the entire site or specific files based on the request.
        """
        sitepath = self.main(args)
        site = self.make_site(sitepath, args.config, args.deploy)
        from hyde.server import HydeWebServer
        server = HydeWebServer(site, args.address, args.port)
        self.logger.info("Starting webserver at [%s]:[%d]", args.address, args.port)
        try:
            server.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Received shutdown request. Shutting down...")
            server.shutdown()
            self.logger.info("Server successfully stopped")
            exit()

    @subcommand('publish', help='Publish the website')
    @store('-c', '--config-path', default='site.yaml', dest='config',
            help='The configuration used to generate the site')
    @store('-p', '--publisher', dest='publisher', default='default',
            help='Points to the publisher configuration.')
    @store('-m', '--message', dest='message',
            help='Optional message.')
    def publish(self, args):
        """
        Publishes the site based on the configuration from the `target`
        parameter.
        """
        sitepath = self.main(args)
        site = self.make_site(sitepath, args.config)
        from hyde.publisher import Publisher
        publisher = Publisher.load_publisher(site,
                        args.publisher,
                        args.message)
        publisher.publish()


    def make_site(self, sitepath, config, deploy=None):
        """
        Creates a site object from the given sitepath and the config file.
        """
        config = Config(sitepath, config_file=config)
        if deploy:
            config.deploy_root = deploy
        return Site(sitepath, config)
########NEW FILE########
__FILENAME__ = exceptions
class HydeException(Exception):
    """
    Base class for exceptions from hyde
    """

    @staticmethod
    def reraise(message, exc_info):
        _, _, tb = exc_info
        raise HydeException(message), None, tb



########NEW FILE########
__FILENAME__ = blog
# -*- coding: utf-8 -*-
"""

Plugins that are useful to blogs hosted with hyde.

"""

from hyde.plugin import Plugin


class DraftsPlugin(Plugin):


    def begin_site(self):

        in_production = self.site.config.mode.startswith('prod')
        if not in_production:
            self.logger.info(
                'Generating draft posts as the site is not in production mode.')
            return

        for resource in self.site.content.walk_resources():
            if not resource.is_processable:
                continue

            try:
                is_draft = resource.meta.is_draft
            except AttributeError:
                is_draft = False

            if is_draft:
                resource.is_processable = False

            self.logger.info(
                '%s is%s draft' % (resource,
                    '' if is_draft else ' not'))
########NEW FILE########
__FILENAME__ = css
# -*- coding: utf-8 -*-
"""
CSS plugins
"""


from hyde.plugin import CLTransformer, Plugin
from hyde.exceptions import HydeException

import os
import re
import subprocess
import sys

from fswrap import File

#
# Less CSS
#

class LessCSSPlugin(CLTransformer):
    """
    The plugin class for less css
    """

    def __init__(self, site):
        super(LessCSSPlugin, self).__init__(site)
        self.import_finder = \
            re.compile('^\\s*@import\s+(?:\'|\")([^\'\"]*)(?:\'|\")\s*\;\s*$',
                       re.MULTILINE)


    @property
    def executable_name(self):
        return "lessc"

    def _should_parse_resource(self, resource):
        """
        Check user defined
        """
        return resource.source_file.kind == 'less' and \
               getattr(resource, 'meta', {}).get('parse', True)

    def _should_replace_imports(self, resource):
        return getattr(resource, 'meta', {}).get('uses_template', True)

    def begin_site(self):
        """
        Find all the less css files and set their relative deploy path.
        """
        for resource in self.site.content.walk_resources():
            if self._should_parse_resource(resource):
                new_name = resource.source_file.name_without_extension + ".css"
                target_folder = File(resource.relative_deploy_path).parent
                resource.relative_deploy_path = target_folder.child(new_name)

    def begin_text_resource(self, resource, text):
        """
        Replace @import statements with {% include %} statements.
        """

        if not self._should_parse_resource(resource) or \
           not self._should_replace_imports(resource):
            return text

        def import_to_include(match):
            if not match.lastindex:
                return ''
            path = match.groups(1)[0]
            afile = File(resource.source_file.parent.child(path))
            if len(afile.kind.strip()) == 0:
                afile = File(afile.path + '.less')
            ref = self.site.content.resource_from_path(afile.path)
            if not ref:
                raise HydeException("Cannot import from path [%s]" % afile.path)
            ref.is_processable = False
            return self.template.get_include_statement(ref.relative_path)
        text = self.import_finder.sub(import_to_include, text)
        return text


    @property
    def plugin_name(self):
        """
        The name of the plugin.
        """
        return "less"

    def text_resource_complete(self, resource, text):
        """
        Save the file to a temporary place and run less compiler.
        Read the generated file and return the text as output.
        Set the target path to have a css extension.
        """
        if not self._should_parse_resource(resource):
            return

        supported = [
            "verbose",
            ("silent", "s"),
            ("compress", "x"),
            "O0",
            "O1",
            "O2",
            "include-path="
        ]

        less = self.app
        source = File.make_temp(text)
        target = File.make_temp('')
        args = [unicode(less)]
        args.extend(self.process_args(supported))
        args.extend([unicode(source), unicode(target)])
        try:
            self.call_app(args)
        except subprocess.CalledProcessError:
             HydeException.reraise(
                    "Cannot process %s. Error occurred when "
                    "processing [%s]" % (self.app.name, resource.source_file),
                    sys.exc_info())

        return target.read_all()


#
# Stylus CSS
#

class StylusPlugin(CLTransformer):
    """
    The plugin class for stylus css
    """

    def __init__(self, site):
        super(StylusPlugin, self).__init__(site)
        self.import_finder = \
            re.compile('^\\s*@import\s+(?:\'|\")([^\'\"]*)(?:\'|\")\s*\;?\s*$',
                       re.MULTILINE)

    def begin_site(self):
        """
        Find all the styl files and set their relative deploy path.
        """
        for resource in self.site.content.walk_resources():
            if resource.source_file.kind == 'styl':
                new_name = resource.source_file.name_without_extension + ".css"
                target_folder = File(resource.relative_deploy_path).parent
                resource.relative_deploy_path = target_folder.child(new_name)

    def begin_text_resource(self, resource, text):
        """
        Replace @import statements with {% include %} statements.
        """

        if not resource.source_file.kind == 'styl':
            return

        def import_to_include(match):
            """
            Converts a css import statement to include statement.
            """
            if not match.lastindex:
                return ''
            path = match.groups(1)[0]
            afile = File(File(resource.source_file.parent.child(path)).fully_expanded_path)
            if len(afile.kind.strip()) == 0:
                afile = File(afile.path + '.styl')

            ref = self.site.content.resource_from_path(afile.path)

            if not ref:
                try:
                    include = self.settings.args.include
                except AttributeError:
                    include = False
                if not include:
                    raise HydeException(
                        "Cannot import from path [%s]" % afile.path)
            else:
                ref.is_processable = False
                return "\n" + \
                        self.template.get_include_statement(ref.relative_path) + \
                        "\n"
            return '@import "' + path + '"\n'

        text = self.import_finder.sub(import_to_include, text)
        return text

    @property
    def defaults(self):
        """
        Returns `compress` if not in development mode.
        """
        try:
            mode = self.site.config.mode
        except AttributeError:
            mode = "production"

        defaults = {"compress":""}
        if mode.startswith('dev'):
            defaults = {}
        return defaults

    @property
    def plugin_name(self):
        """
        The name of the plugin.
        """
        return "stylus"

    def text_resource_complete(self, resource, text):
        """
        Save the file to a temporary place and run stylus compiler.
        Read the generated file and return the text as output.
        Set the target path to have a css extension.
        """
        if not resource.source_file.kind == 'styl':
            return
        stylus = self.app
        source = File.make_temp(text.strip())
        target = source
        supported = [("compress", "c"), ("include", "I")]

        args = [unicode(stylus)]
        args.extend(self.process_args(supported))
        args.append(unicode(source))
        try:
            self.call_app(args)
        except subprocess.CalledProcessError:
            HydeException.reraise(
                    "Cannot process %s. Error occurred when "
                    "processing [%s]" % (stylus.name, resource.source_file),
                    sys.exc_info())
        return target.read_all()


#
# Clever CSS
#

class CleverCSSPlugin(Plugin):
    """
    The plugin class for CleverCSS
    """

    def __init__(self, site):
        super(CleverCSSPlugin, self).__init__(site)
        try:
            import clevercss
        except ImportError, e:
            raise HydeException('Unable to import CleverCSS: ' + e.message)
        else:
            self.clevercss = clevercss

    def _should_parse_resource(self, resource):
        """
        Check user defined
        """
        return resource.source_file.kind == 'ccss' and \
               getattr(resource, 'meta', {}).get('parse', True)

    def _should_replace_imports(self, resource):
        return getattr(resource, 'meta', {}).get('uses_template', True)

    def begin_site(self):
        """
        Find all the clevercss files and set their relative deploy path.
        """
        for resource in self.site.content.walk_resources():
            if self._should_parse_resource(resource):
                new_name = resource.source_file.name_without_extension + ".css"
                target_folder = File(resource.relative_deploy_path).parent
                resource.relative_deploy_path = target_folder.child(new_name)

    def begin_text_resource(self, resource, text):
        """
        Replace @import statements with {% include %} statements.
        """

        if not self._should_parse_resource(resource) or \
           not self._should_replace_imports(resource):
            return text

        import_finder = re.compile(
                            '^\\s*@import\s+(?:\'|\")([^\'\"]*)(?:\'|\")\s*\;\s*$',
                            re.MULTILINE)

        def import_to_include(match):
            if not match.lastindex:
                return ''
            path = match.groups(1)[0]
            afile = File(resource.source_file.parent.child(path))
            if len(afile.kind.strip()) == 0:
                afile = File(afile.path + '.ccss')
            ref = self.site.content.resource_from_path(afile.path)
            if not ref:
                raise HydeException("Cannot import from path [%s]" % afile.path)
            ref.is_processable = False
            return self.template.get_include_statement(ref.relative_path)
        text = import_finder.sub(import_to_include, text)
        return text

    def text_resource_complete(self, resource, text):
        """
        Run clevercss compiler on text.
        """
        if not self._should_parse_resource(resource):
            return

        return self.clevercss.convert(text, self.settings)

#
# Sassy CSS
#

class SassyCSSPlugin(Plugin):
    """
    The plugin class for SassyCSS
    """

    def __init__(self, site):
        super(SassyCSSPlugin, self).__init__(site)
        try:
            import scss
        except ImportError, e:
            raise HydeException('Unable to import pyScss: ' + e.message)
        else:
            self.scss = scss

    def _should_parse_resource(self, resource):
        """
        Check user defined
        """
        return resource.source_file.kind == 'scss' and \
               getattr(resource, 'meta', {}).get('parse', True)

    @property
    def options(self):
        """
        Returns options depending on development mode
        """
        try:
            mode = self.site.config.mode
        except AttributeError:
            mode = "production"

        debug = mode.startswith('dev')
        opts = {'compress': not debug, 'debug_info': debug}
        site_opts = self.settings.get('options', {})
        opts.update(site_opts)
        return opts

    @property
    def vars(self):
        """
        Returns scss variables.
        """
        return self.settings.get('vars', {})

    @property
    def includes(self):
        """
        Returns scss load paths.
        """
        return self.settings.get('includes', [])


    def begin_site(self):
        """
        Find all the sassycss files and set their relative deploy path.
        """
        self.scss.STATIC_URL = self.site.content_url('/')
        self.scss.STATIC_ROOT = self.site.config.content_root_path.path
        self.scss.ASSETS_URL = self.site.media_url('/')
        self.scss.ASSETS_ROOT = self.site.config.deploy_root_path.child(
                                    self.site.config.media_root)

        for resource in self.site.content.walk_resources():
            if self._should_parse_resource(resource):
                new_name = resource.source_file.name_without_extension + ".css"
                target_folder = File(resource.relative_deploy_path).parent
                resource.relative_deploy_path = target_folder.child(new_name)

    def text_resource_complete(self, resource, text):
        """
        Run sassycss compiler on text.
        """
        if not self._should_parse_resource(resource):
            return

        includes = [resource.node.path] + self.includes
        includes = [path.rstrip(os.sep) + os.sep for path in includes]
        options = self.options
        if not 'load_paths' in options:
            options['load_paths'] = []
        options['load_paths'].extend(includes)
        scss = self.scss.Scss(scss_opts=options, scss_vars=self.vars )
        return scss.compile(text)

########NEW FILE########
__FILENAME__ = depends
# -*- coding: utf-8 -*-
"""
Depends plugin

/// Experimental: Not working yet.
"""

from hyde.plugin import Plugin

class DependsPlugin(Plugin):
    """
    The plugin class setting explicit dependencies.
    """

    def __init__(self, site):
        super(DependsPlugin, self).__init__(site)

    def begin_site(self):
           """
           Initialize dependencies.

           Go through all the nodes and resources to initialize
           dependencies at each level.
           """
           for resource in self.site.content.walk_resources():
               self._update_resource(resource)


    def _update_resource(self, resource):
        """
        If the meta data for the resource contains a depends attribute,
        this plugin adds an entry to the depends property of the
        resource.

        The dependency can contain the following template variables:
        node, resource, site, context.

        The following strings are valid:
        '{node.module}/dependencies/{resource.source.name_without_extension}.inc'
        '{context.dependency_folder}/{resource.source.name_without_extension}.{site.meta.depext}'
        """
        depends = []
        try:
            depends = resource.meta.depends
        except AttributeError:
            return

        if not hasattr(resource, 'depends') or not resource.depends:
            resource.depends = []

        if isinstance(depends, basestring):
            depends = [depends]

        for dep in depends:
            resource.depends.append(dep.format(node=resource.node,
                                    resource=resource,
                                    site=self.site,
                                    context=self.site.context))
        resource.depends = list(set(resource.depends))

########NEW FILE########
__FILENAME__ = images
# -*- coding: utf-8 -*-
"""
Contains classes to handle images related things

# Requires PIL or pillow
"""

from hyde.plugin import CLTransformer, Plugin


import glob
import os
import re

from fswrap import File

from hyde.exceptions import HydeException


class PILPlugin(Plugin):

    def __init__(self, site):
        super(PILPlugin, self).__init__(site)
        try:
            from PIL import Image
        except ImportError:
            # No pillow
            try:
                import Image
            except ImportError, e:
                raise HydeException('Unable to load PIL: ' + e.message)

        self.Image = Image


#
# Image sizer
#


class ImageSizerPlugin(PILPlugin):
    """
    Each HTML page is modified to add width and height for images if
    they are not already specified.

    # Requires PIL
    """

    def __init__(self, site):
        super(ImageSizerPlugin, self).__init__(site)
        self.cache = {}


    def _handle_img(self, resource, src, width, height):
        """Determine what should be added to an img tag"""
        if height is not None and width is not None:
            return ""           # Nothing
        if src is None:
            self.logger.warn("[%s] has an img tag without src attribute" % resource)
            return ""           # Nothing
        if src not in self.cache:
            if src.startswith(self.site.config.media_url):
                path = src[len(self.site.config.media_url):].lstrip("/")
                path = self.site.config.media_root_path.child(path)
                image = self.site.content.resource_from_relative_deploy_path(path)
            elif re.match(r'([a-z]+://|//).*', src):
                # Not a local link
                return ""       # Nothing
            elif src.startswith("/"):
                # Absolute resource
                path = src.lstrip("/")
                image = self.site.content.resource_from_relative_deploy_path(path)
            else:
                # Relative resource
                path = resource.node.source_folder.child(src)
                image = self.site.content.resource_from_path(path)
            if image is None:
                self.logger.warn(
                    "[%s] has an unknown image" % resource)
                return ""       # Nothing
            if image.source_file.kind not in ['png', 'jpg', 'jpeg', 'gif']:
                self.logger.warn(
                        "[%s] has an img tag not linking to an image" % resource)
                return ""       # Nothing
            # Now, get the size of the image
            try:
                self.cache[src] = self.Image.open(image.path).size
            except IOError:
                self.logger.warn(
                    "Unable to process image [%s]" % image)
                self.cache[src] = (None, None)
                return ""       # Nothing
            self.logger.debug("Image [%s] is %s" % (src,
                                                    self.cache[src]))
        new_width, new_height = self.cache[src]
        if new_width is None or new_height is None:
            return ""           # Nothing
        if width is not None:
            return 'height="%d" ' % (int(width)*new_height/new_width)
        elif height is not None:
            return 'width="%d" ' % (int(height)*new_width/new_height)
        return 'height="%d" width="%d" ' % (new_height, new_width)

    def text_resource_complete(self, resource, text):
        """
        When the resource is generated, search for img tag and specify
        their sizes.

        Some img tags may be missed, this is not a perfect parser.
        """
        try:
            mode = self.site.config.mode
        except AttributeError:
            mode = "production"

        if not resource.source_file.kind == 'html':
            return

        if mode.startswith('dev'):
            self.logger.debug("Skipping sizer in development mode.")
            return

        pos = 0                 # Position in text
        img = None              # Position of current img tag
        state = "find-img"
        while pos < len(text):
            if state == "find-img":
                img = text.find("<img", pos)
                if img == -1:
                    break           # No more img tag
                pos = img + len("<img")
                if not text[pos].isspace():
                    continue        # Not an img tag
                pos = pos + 1
                tags = {"src": "",
                        "width": "",
                        "height": ""}
                state = "find-attr"
                continue
            if state == "find-attr":
                if text[pos] == ">":
                    # We get our img tag
                    insert = self._handle_img(resource,
                                              tags["src"] or None,
                                              tags["width"] or None,
                                              tags["height"] or None)
                    img = img + len("<img ")
                    text = "".join([text[:img], insert, text[img:]])
                    state = "find-img"
                    pos = pos + 1
                    continue
                attr = None
                for tag in tags:
                    if text[pos:(pos+len(tag)+1)] == ("%s=" % tag):
                        attr = tag
                        pos = pos + len(tag) + 1
                        break
                if not attr:
                    pos = pos + 1
                    continue
                if text[pos] in ["'", '"']:
                    pos = pos + 1
                state = "get-value"
                continue
            if state == "get-value":
                if text[pos] == ">":
                    state = "find-attr"
                    continue
                if text[pos] in ["'", '"'] or text[pos].isspace():
                    # We got our value
                    pos = pos + 1
                    state = "find-attr"
                    continue
                tags[attr] = tags[attr] + text[pos]
                pos = pos + 1
                continue

        return text

def scale_aspect(a, b1, b2):
  from math import ceil
  """
  Scales a by b2/b1 rounding up to nearest integer
  """
  return int(ceil(a * b2 / float(b1)))


def thumb_scale_size(orig_width, orig_height, width, height):
    """
    Determine size to scale to scale for thumbnailst Params

    Params:
      orig_width, orig_height: original image dimensions
      width, height: thumbnail dimensions
    """
    if width is None:
        width = scale_aspect(orig_width, orig_height, height)
    elif height is None:
        height = scale_aspect(orig_height, orig_width, width)
    elif orig_width*height >= orig_height*width:
        width = scale_aspect(orig_width, orig_height, height)
    else:
        height = scale_aspect(orig_height, orig_width, width)

    return width, height

#
# Image Thumbnails
#

class ImageThumbnailsPlugin(PILPlugin):
    """
    Provide a function to get thumbnail for any image resource.

    Example of usage:
    Setting optional defaults in site.yaml:
        thumbnails:
          width: 100
          height: 120
          prefix: thumbnail_

    Setting thumbnails options in nodemeta.yaml:
        thumbnails:
          - width: 50
            prefix: thumbs1_
            include:
            - '*.png'
            - '*.jpg'
          - height: 100
            prefix: thumbs2_
            include:
            - '*.png'
            - '*.jpg'
          - larger: 100
            prefix: thumbs3_
            include:
            - '*.jpg'
          - smaller: 50
            prefix: thumbs4_
            include:
            - '*.jpg'
    which means - make four thumbnails from every picture with different prefixes
    and sizes

    It is only valid to specify either width/height or larger/smaller, but not to
    mix the two types.

    If larger/smaller are specified, then the orientation (i.e., landscape or
    portrait) is preserved while thumbnailing.

    If both width and height (or both larger and smaller) are defined, the
    image is cropped. You can define crop_type as one of these values:
    "topleft", "center" and "bottomright".  "topleft" is default.
    """

    def __init__(self, site):
        super(ImageThumbnailsPlugin, self).__init__(site)

    def thumb(self, resource, width, height, prefix, crop_type, preserve_orientation=False):
        """
        Generate a thumbnail for the given image
        """
        name = os.path.basename(resource.get_relative_deploy_path())
        # don't make thumbnails for thumbnails
        if name.startswith(prefix):
            return
        # Prepare path, make all thumnails in single place(content/.thumbnails)
        # for simple maintenance but keep original deploy path to preserve
        # naming logic in generated site
        path = os.path.join(".thumbnails",
                            os.path.dirname(resource.get_relative_deploy_path()),
                            "%s%s" % (prefix, name))
        target = resource.site.config.content_root_path.child_file(path)
        res = self.site.content.add_resource(target)
        res.set_relative_deploy_path(res.get_relative_deploy_path().replace('.thumbnails/', '', 1))

        target.parent.make()
        if os.path.exists(target.path) and os.path.getmtime(resource.path) <= os.path.getmtime(target.path):
            return
        self.logger.debug("Making thumbnail for [%s]" % resource)

        im = self.Image.open(resource.path)
        if im.mode != 'RGBA':
            im = im.convert('RGBA')
        format = im.format

        if preserve_orientation and im.size[1] > im.size[0]:
          width, height = height, width

        resize_width, resize_height = thumb_scale_size(im.size[0], im.size[1], width, height)

        self.logger.debug("Resize to: %d,%d" % (resize_width, resize_height))
        im = im.resize((resize_width, resize_height), self.Image.ANTIALIAS)
        if width is not None and height is not None:
            shiftx = shifty = 0
            if crop_type == "center":
                shiftx = (im.size[0] - width)/2
                shifty = (im.size[1] - height)/2
            elif crop_type == "bottomright":
                shiftx = (im.size[0] - width)
                shifty = (im.size[1] - height)
            im = im.crop((shiftx, shifty, width + shiftx, height + shifty))
            im.load()

        options = dict(optimize=True)
        if format == "JPEG":
          options['quality'] = 75

        im.save(target.path, **options)

    def begin_site(self):
        """
        Find any image resource that should be thumbnailed and call thumb on it.
        """
        # Grab default values from config
        config = self.site.config
        defaults = { "width": None,
                     "height": None,
                     "larger": None,
                     "smaller": None,
                     "crop_type": "topleft",
                     "prefix": 'thumb_'}
        if hasattr(config, 'thumbnails'):
            defaults.update(config.thumbnails)

        for node in self.site.content.walk():
            if hasattr(node, 'meta') and hasattr(node.meta, 'thumbnails'):
                for th in node.meta.thumbnails:
                    if not hasattr(th, 'include'):
                        self.logger.error("Include is not set for node [%s]" % node)
                        continue
                    include = th.include
                    prefix = th.prefix if hasattr(th, 'prefix') else defaults['prefix']
                    height = th.height if hasattr(th, 'height') else defaults['height']
                    width = th.width if hasattr(th, 'width') else defaults['width']
                    larger = th.larger if hasattr(th, 'larger') else defaults['larger']
                    smaller = th.smaller if hasattr(th, 'smaller') else defaults['smaller']
                    crop_type = th.crop_type if hasattr(th, 'crop_type') else defaults['crop_type']
                    if crop_type not in ["topleft", "center", "bottomright"]:
                        self.logger.error("Unknown crop_type defined for node [%s]" % node)
                        continue
                    if width is None and height is None and larger is None and smaller is None:
                        self.logger.error("At least one of width, height, larger, or smaller must be set for node [%s]" % node)
                        continue

                    if ((larger is not None or smaller is not None) and
                        (width is not None or height is not None)):
                        self.logger.error("It is not valid to specify both one of width/height and one of larger/smaller for node [%s]" % node)
                        continue

                    if larger is None and smaller is None:
                      preserve_orientation = False
                      dim1, dim2 = width, height
                    else:
                      preserve_orientation = True
                      dim1, dim2 = larger, smaller

                    match_includes = lambda s: any([glob.fnmatch.fnmatch(s, inc) for inc in include])

                    for resource in node.resources:
                        if match_includes(resource.path):
                            self.thumb(resource, dim1, dim2, prefix, crop_type, preserve_orientation)

#
# JPEG Optimization
#

class JPEGOptimPlugin(CLTransformer):
    """
    The plugin class for JPEGOptim
    """

    def __init__(self, site):
        super(JPEGOptimPlugin, self).__init__(site)

    @property
    def plugin_name(self):
        """
        The name of the plugin.
        """
        return "jpegoptim"

    def binary_resource_complete(self, resource):
        """
        If the site is in development mode, just return.
        Otherwise, run jpegoptim to compress the jpg file.
        """

        try:
            mode = self.site.config.mode
        except AttributeError:
            mode = "production"

        if not resource.source_file.kind == 'jpg':
            return

        if mode.startswith('dev'):
            self.logger.debug("Skipping jpegoptim in development mode.")
            return

        supported = [
            "force",
            "max=",
            "strip-all",
            "strip-com",
            "strip-exif",
            "strip-iptc",
            "strip-icc",
        ]
        target = File(self.site.config.deploy_root_path.child(
                                resource.relative_deploy_path))
        jpegoptim = self.app
        args = [unicode(jpegoptim)]
        args.extend(self.process_args(supported))
        args.extend(["-q", unicode(target)])
        self.call_app(args)


class JPEGTranPlugin(CLTransformer):
    """
    Almost like jpegoptim except it uses jpegtran. jpegtran allows to make
    progressive JPEG. Unfortunately, it only does lossless compression. If
    you want both, you need to combine this plugin with jpegoptim one.
    """

    def __init__(self, site):
        super(JPEGTranPlugin, self).__init__(site)

    @property
    def plugin_name(self):
        """
        The name of the plugin.
        """
        return "jpegtran"

    def option_prefix(self, option):
        return "-"

    def binary_resource_complete(self, resource):
        """
        If the site is in development mode, just return.
        Otherwise, run jpegtran to compress the jpg file.
        """

        try:
            mode = self.site.config.mode
        except AttributeError:
            mode = "production"

        if not resource.source_file.kind == 'jpg':
            return

        if mode.startswith('dev'):
            self.logger.debug("Skipping jpegtran in development mode.")
            return

        supported = [
            "optimize",
            "progressive",
            "restart",
            "arithmetic",
            "perfect",
            "copy",
        ]
        source = File(self.site.config.deploy_root_path.child(
                resource.relative_deploy_path))
        target = File.make_temp('')
        jpegtran = self.app
        args = [unicode(jpegtran)]
        args.extend(self.process_args(supported))
        args.extend(["-outfile", unicode(target), unicode(source)])
        self.call_app(args)
        target.copy_to(source)
        target.delete()



#
# PNG Optimization
#

class OptiPNGPlugin(CLTransformer):
    """
    The plugin class for OptiPNG
    """

    def __init__(self, site):
        super(OptiPNGPlugin, self).__init__(site)

    @property
    def plugin_name(self):
        """
        The name of the plugin.
        """
        return "optipng"

    def option_prefix(self, option):
        return "-"

    def binary_resource_complete(self, resource):
        """
        If the site is in development mode, just return.
        Otherwise, run optipng to compress the png file.
        """

        try:
            mode = self.site.config.mode
        except AttributeError:
            mode = "production"

        if not resource.source_file.kind == 'png':
            return

        if mode.startswith('dev'):
            self.logger.debug("Skipping optipng in development mode.")
            return

        supported = [
            "o",
            "fix",
            "force",
            "preserve",
            "quiet",
            "log",
            "f",
            "i",
            "zc",
            "zm",
            "zs",
            "zw",
            "full",
            "nb",
            "nc",
            "np",
            "nz"
        ]
        target = File(self.site.config.deploy_root_path.child(
                                resource.relative_deploy_path))
        optipng = self.app
        args = [unicode(optipng)]
        args.extend(self.process_args(supported))
        args.extend([unicode(target)])
        self.call_app(args)

########NEW FILE########
__FILENAME__ = js
# -*- coding: utf-8 -*-
"""
JavaScript plugins
"""
import subprocess
import sys

from hyde.exceptions import HydeException
from hyde.plugin import CLTransformer

from fswrap import File


#
# Uglify JavaScript
#

class UglifyPlugin(CLTransformer):
    """
    The plugin class for Uglify JS
    """

    def __init__(self, site):
        super(UglifyPlugin, self).__init__(site)

    @property
    def executable_name(self):
        return "uglifyjs"

    @property
    def plugin_name(self):
        """
        The name of the plugin.
        """
        return "uglify"

    def text_resource_complete(self, resource, text):
        """
        If the site is in development mode, just return.
        Otherwise, save the file to a temporary place
        and run the uglify app. Read the generated file
        and return the text as output.
        """

        try:
            mode = self.site.config.mode
        except AttributeError:
            mode = "production"

        if not resource.source_file.kind == 'js':
            return

        if mode.startswith('dev'):
            self.logger.debug("Skipping uglify in development mode.")
            return

        supported = [
            "source-map",
            "source-map-root",
            "source-map-url",
            "in-source-map",
            "screw-ie8",
            "expr",
            ("prefix", "p"),
            ("beautify", "b"),
            ("mangle", "m"),
            ("reserved", "r"),
            ("compress", "c"),
            ("define", "d"),
            ("enclose", "e"),
            "comments",
            "stats",
            "wrap",
            "lint",
            "verbose"
        ]

        uglify = self.app
        source = File.make_temp(text)
        target = File.make_temp('')
        args = [unicode(uglify)]
        args.extend(self.process_args(supported))
        args.extend(["-o", unicode(target), unicode(source)])
        self.call_app(args)
        out = target.read_all()
        return out

class RequireJSPlugin(CLTransformer):
    """
    requirejs plugin

    Calls r.js optimizer in order to proces javascript files,
    bundle them into one single file and compress it.

    The call to r.js is being made with options -o and out. Example:

        r.js -o rjs.conf out=app.js

    whereas rjs.conf is the require.js configuration file pointing
    to the main javascript file as well as passing options to r.js.
    The bundled and compressed result is written to 'app.js' file
    within the deployment structure.

    Please see the homepage of requirejs for usage details.
    """
    def __init__(self, site):
        super(RequireJSPlugin, self).__init__(site)

    @property
    def executable_name(self):
        return "r.js"

    def begin_site(self):
        for resource in self.site.content.walk_resources():
            if resource.source_file.name == "rjs.conf":
                new_name = "app.js"
                target_folder = File(resource.relative_deploy_path).parent
                resource.relative_deploy_path = target_folder.child(new_name)

    def text_resource_complete(self, resource, text):
        if not resource.source_file.name == 'rjs.conf':
            return

        rjs = self.app
        target = File.make_temp('')
        args = [unicode(rjs)]
        args.extend(['-o', unicode(resource), ("out=" + target.fully_expanded_path)])

        try:
            self.call_app(args)
        except subprocess.CalledProcessError:
             HydeException.reraise(
                    "Cannot process %s. Error occurred when "
                    "processing [%s]" % (self.app.name, resource.source_file),
                    sys.exc_info())

        return target.read_all()


class CoffeePlugin(CLTransformer):
    """
    The plugin class for Coffeescript
    """

    def __init__(self, site):
        super(CoffeePlugin, self).__init__(site)

    @property
    def executable_name(self):
        return "coffee"

    @property
    def plugin_name(self):
        """
        The name of the plugin.
        """
        return "Coffee"

    def begin_site(self):
        """
        Find all the coffee files and set their relative deploy path.
        """
        for resource in self.site.content.walk_resources():
            if resource.source_file.kind == 'coffee':
                new_name = resource.source_file.name_without_extension + ".js"
                target_folder = File(resource.relative_deploy_path).parent
                resource.relative_deploy_path = target_folder.child(new_name)

    def text_resource_complete(self, resource, text):
        """
        Save the file to a temporary place and run the Coffee
        compiler. Read the generated file and return the text as
        output.
        """

        if not resource.source_file.kind == 'coffee':
            return

        coffee = self.app
        source = File.make_temp(text)
        args = [unicode(coffee)]
        args.extend(["-c", "-p", unicode(source)])
        return self.call_app(args)

########NEW FILE########
__FILENAME__ = languages
# -*- coding: utf-8 -*-
"""
Contains classes to help manage multi-language pages.
"""

from hyde.plugin import Plugin

class LanguagePlugin(Plugin):
    """
    Each page should be tagged with a language using `language` meta
    data. Each page should also have an UUID stored in `uuid` meta
    data. Pages with different languages but the same UUID will be
    considered a translation of each other.

    For example, consider that you have the following content tree:
       - `en/`
       - `fr/`

    In `en/meta.yaml`, you set `language: en` and in `fr/meta.yaml`, you
    set `language: fr`. In `en/my-first-page.html`, you put something like
    this::
         -------
         uuid: page1
         -------
         My first page

     And in `fr/ma-premiere-page.html`, you put something like this::
         -------
         uuid: page1
         -------
         Ma première page

    You'll get a `translations` attribute attached to the resource
    with the list of resources that are a translation of this one.
    """

    def __init__(self, site):
        super(LanguagePlugin, self).__init__(site)
        self.languages = {} # Associate a UUID to the list of resources available

    def begin_site(self):
        """
        Initialize plugin. Build the language tree for each node
        """
        # Build association between UUID and list of resources
        for node in self.site.content.walk():
            for resource in node.resources:
                try:
                    uuid = resource.meta.uuid
                    language = resource.meta.language
                except AttributeError:
                    continue
                if uuid not in self.languages:
                    self.languages[uuid] = []
                self.languages[uuid].append(resource)
        # Add back the information about other languages
        for uuid, resources in self.languages.items():
            for resource in resources:
                language = resource.meta.language
                resource.translations = \
                    [r for r in resources
                     if r.meta.language != language]
                translations = ",".join([t.meta.language for t in resource.translations])
                self.logger.debug(
                    "Adding translations for resource [%s] from %s to %s" % (resource,
                                                                             language,
                                                                             translations))

########NEW FILE########
__FILENAME__ = meta
# -*- coding: utf-8 -*-
"""
Contains classes and utilities related to meta data in hyde.
"""

from collections import namedtuple
from functools import partial
from itertools import ifilter
from operator import attrgetter
import re
import sys

from hyde.exceptions import HydeException
from hyde.model import Expando
from hyde.plugin import Plugin
from hyde.site import Node, Resource
from hyde.util import add_method, add_property, pairwalk


from fswrap import File, Folder
import yaml


#
# Metadata
#

class Metadata(Expando):
    """
    Container class for yaml meta data.
    """

    def __init__(self, data, parent=None):

        super(Metadata, self).__init__({})
        if parent:
            self.update(parent.__dict__)
        if data:
            self.update(data)

    def update(self, data):
        """
        Updates the metadata with new stuff
        """
        if isinstance(data, basestring):
            super(Metadata, self).update(yaml.load(data))
        else:
            super(Metadata, self).update(data)


class MetaPlugin(Plugin):
    """
    Metadata plugin for hyde. Loads meta data in the following order:

    1. meta.yaml: files in any folder
    2. frontmatter: any text file with content enclosed within three dashes
        or three equals signs.
        Example:
        ---
        abc: def
        ---

    Supports YAML syntax.
    """

    def __init__(self, site):
        super(MetaPlugin, self).__init__(site)
        self.yaml_finder = re.compile(
                    r"^\s*(?:---|===)\s*\n((?:.|\n)+?)\n\s*(?:---|===)\s*\n*",
                    re.MULTILINE)

    def begin_site(self):
        """
        Initialize site meta data.

        Go through all the nodes and resources to initialize
        meta data at each level.
        """
        config = self.site.config
        metadata = config.meta if hasattr(config, 'meta') else {}
        self.site.meta = Metadata(metadata)
        self.nodemeta = 'nodemeta.yaml'
        if hasattr(self.site.meta, 'nodemeta'):
            self.nodemeta = self.site.meta.nodemeta
        for node in self.site.content.walk():
            self.__read_node__(node)
            for resource in node.resources:
                if not hasattr(resource, 'meta'):
                    resource.meta = Metadata({}, node.meta)
                if resource.source_file.is_text and not resource.simple_copy:
                    self.__read_resource__(resource, resource.source_file.read_all())

    def __read_resource__(self, resource, text):
        """
        Reads the resource metadata and assigns it to
        the resource. Load meta data by looking for the marker.
        Once loaded, remove the meta area from the text.
        """
        self.logger.debug("Trying to load metadata from resource [%s]" % resource)
        match = re.match(self.yaml_finder, text)
        if not match:
            self.logger.debug("No metadata found in resource [%s]" % resource)
            data = {}
        else:
            text = text[match.end():]
            data = match.group(1)

        if not hasattr(resource, 'meta') or not resource.meta:
            if not hasattr(resource.node, 'meta'):
                resource.node.meta = Metadata({})
            resource.meta = Metadata(data, resource.node.meta)
        else:
            resource.meta.update(data)
        self.__update_standard_attributes__(resource)
        self.logger.debug("Successfully loaded metadata from resource [%s]"
                        % resource)
        return text or ' '

    def __update_standard_attributes__(self, obj):
        """
        Updates standard attributes on the resource and
        page based on the provided meta data.
        """
        if not hasattr(obj, 'meta'):
            return
        standard_attributes = ['is_processable', 'uses_template']
        for attr in standard_attributes:
            if hasattr(obj.meta, attr):
                setattr(obj, attr, getattr(obj.meta, attr))

    def __read_node__(self, node):
        """
        Look for nodemeta.yaml (or configured name). Load and assign it
        to the node.
        """
        nodemeta = node.get_resource(self.nodemeta)
        parent_meta = node.parent.meta if node.parent else self.site.meta
        if nodemeta:
            nodemeta.is_processable = False
            metadata = nodemeta.source_file.read_all()
            if hasattr(node, 'meta') and node.meta:
                node.meta.update(metadata)
            else:
                node.meta = Metadata(metadata, parent=parent_meta)
        else:
            node.meta = Metadata({}, parent=parent_meta)
        self.__update_standard_attributes__(node)

    def begin_node(self, node):
        """
        Read node meta data.
        """
        self.__read_node__(node)

    def begin_text_resource(self, resource, text):
        """
        Update the meta data again, just in case it
        has changed. Return text without meta data.
        """
        return self.__read_resource__(resource, text)


#
# Auto Extend
#

class AutoExtendPlugin(Plugin):
    """
    The plugin class for extending templates using metadata.
    """

    def __init__(self, site):
        super(AutoExtendPlugin, self).__init__(site)

    def begin_text_resource(self, resource, text):
        """
        If the meta data for the resource contains a layout attribute,
        and there is no extends statement, this plugin automatically adds
        an extends statement to the top of the file.
        """

        if not resource.uses_template:
            return text

        layout = None
        block = None
        try:
            layout = resource.meta.extends
        except AttributeError:
            pass

        try:
            block = resource.meta.default_block
        except AttributeError:
            pass

        if layout:
            self.logger.debug("Autoextending %s with %s" % (
                resource.relative_path, layout))
            extends_pattern = self.template.patterns['extends']

            if not re.search(extends_pattern, text):
                extended_text = self.template.get_extends_statement(layout)
                extended_text += '\n'
                if block:
                    extended_text += ('%s\n%s\n%s' %
                                        (self.t_block_open_tag(block),
                                            text,
                                            self.t_block_close_tag(block)))
                else:
                    extended_text += text
                return extended_text
        return text


#
# Tagging
#

class Tag(Expando):
    """
    A simple object that represents a tag.
    """

    def __init__(self, name):
        """
        Initialize the tag with a name.
        """
        self.name = name
        self.resources = []

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


def get_tagger_sort_method(site):
    config = site.config
    content = site.content
    walker = 'walk_resources'
    sorter = None
    try:
        sorter = attrgetter('tagger.sorter')(config)
        walker = walker + '_sorted_by_%s' % sorter
    except AttributeError:
        pass

    try:
        walker = getattr(content, walker)
    except AttributeError:
        HydeException.reraise(
            "Cannot find the sorter: %s" % sorter,
            sys.exc_info())
    return walker

def walk_resources_tagged_with(node, tag):
    tags = set(unicode(tag).split('+'))
    walker = get_tagger_sort_method(node.site)
    for resource in walker():
        try:
            taglist = set(attrgetter("meta.tags")(resource))
        except AttributeError:
            continue
        if tags <= taglist:
            yield resource

class TaggerPlugin(Plugin):
    """
    Tagger plugin for hyde. Adds the ability to do tag resources and search
    based on the tags.

    Configuration example
    ---------------------
    #yaml
    sorter:
        kind:
            attr: source.kind
    tagger:
       sorter: kind # How to sort the resources in a tag
       archives:
            blog:
               template: tagged_posts.j2
               source: blog
               target: blog/tags
               archive_extension: html
    """
    def __init__(self, site):
        super(TaggerPlugin, self).__init__(site)

    def begin_site(self):
        """
        Initialize plugin. Add tag to the site context variable
        and methods for walking tagged resources.
        """
        self.logger.debug("Adding tags from metadata")
        config = self.site.config
        content = self.site.content
        tags = {}
        add_method(Node,
            'walk_resources_tagged_with', walk_resources_tagged_with)
        walker = get_tagger_sort_method(self.site)
        for resource in walker():
            self._process_tags_in_resource(resource, tags)
        self._process_tag_metadata(tags)
        self.site.tagger = Expando(dict(tags=tags))
        self._generate_archives()

    def _process_tag_metadata(self, tags):
        """
        Parses and adds metadata to the tagger object, if the tagger
        configuration contains metadata.
        """
        try:
            tag_meta = self.site.config.tagger.tags.to_dict()
        except AttributeError:
            tag_meta = {}

        for tagname, meta in tag_meta.iteritems():
            # Don't allow name and resources in meta
            if 'resources' in meta:
                del(meta['resources'])
            if 'name' in meta:
                del(meta['name'])
            if tagname in tags:
                tags[tagname].update(meta)

    def _process_tags_in_resource(self, resource, tags):
        """
        Reads the tags associated with this resource and
        adds them to the tag list if needed.
        """
        try:
            taglist = attrgetter("meta.tags")(resource)
        except AttributeError:
            return

        for tagname in taglist:
            if not tagname in tags:
                tag = Tag(tagname)
                tags[tagname] = tag
                tag.resources.append(resource)
                add_method(Node,
                    'walk_resources_tagged_with_%s' % tagname,
                    walk_resources_tagged_with,
                    tag=tag)
            else:
                tags[tagname].resources.append(resource)
            if not hasattr(resource, 'tags'):
                setattr(resource, 'tags', [])
            resource.tags.append(tags[tagname])

    def _generate_archives(self):
        """
        Generates archives if the configuration demands.
        """
        archive_config = None

        try:
            archive_config = attrgetter("tagger.archives")(self.site.config)
        except AttributeError:
            return

        self.logger.debug("Generating archives for tags")

        for name, config in archive_config.to_dict().iteritems():
            self._create_tag_archive(config)


    def _create_tag_archive(self, config):
        """
        Generates archives for each tag based on the given configuration.
        """
        if not 'template' in config:
            raise HydeException("No Template specified in tagger configuration.")
        content = self.site.content.source_folder
        source = Folder(config.get('source', ''))
        target = content.child_folder(config.get('target', 'tags'))
        if not target.exists:
            target.make()

        # Write meta data for the configuration
        meta = config.get('meta', {})
        meta_text = u''
        if meta:
            import yaml
            meta_text = yaml.dump(meta, default_flow_style=False)

        extension = config.get('extension', 'html')
        template = config['template']

        archive_text = u"""
---
extends: false
%(meta)s
---

{%% set tag = site.tagger.tags['%(tag)s'] %%}
{%% set source = site.content.node_from_relative_path('%(node)s') %%}
{%% set walker = source['walk_resources_tagged_with_%(tag)s'] %%}
{%% extends "%(template)s" %%}
"""
        for tagname, tag in self.site.tagger.tags.to_dict().iteritems():
            tag_data = {
                "tag": tagname,
                "node": source.name,
                "template": template,
                "meta": meta_text
            }
            text = archive_text % tag_data
            archive_file = File(target.child("%s.%s" % (tagname, extension)))
            archive_file.delete()
            archive_file.write(text.strip())
            self.site.content.add_resource(archive_file)


#
# Sorting
#

def filter_method(item, settings=None):
    """
    Returns true if all the filters in the
    given settings evaluate to True.
    """
    all_match = True
    default_filters = {}
    filters = {}
    if hasattr(settings, 'filters'):
        filters.update(default_filters)
        filters.update(settings.filters.__dict__)

    for field, value in filters.items():
        try:
            res = attrgetter(field)(item)
        except:
            res = None
        if res != value:
            all_match = False
            break
    return all_match

def attributes_checker(item, attributes=None):
    """
    Checks if the given list of attributes exist.
    """
    try:
      attrgetter(*attributes)(item)
      return True
    except AttributeError:
      return False

def sort_method(node, settings=None):
    """
    Sorts the resources in the given node based on the
    given settings.
    """
    attr = 'name'
    if settings and hasattr(settings, 'attr') and settings.attr:
        attr = settings.attr
    reverse = False
    if settings and hasattr(settings, 'reverse'):
        reverse = settings.reverse
    if not isinstance(attr, list):
        attr = [attr]
    filter_ = partial(filter_method, settings=settings)

    excluder_ = partial(attributes_checker, attributes=attr)

    resources = ifilter(lambda x: excluder_(x) and filter_(x),
                        node.walk_resources())
    return sorted(resources,
                    key=attrgetter(*attr),
                    reverse=reverse)


class SorterPlugin(Plugin):
    """
    Sorter plugin for hyde. Adds the ability to do
    sophisticated sorting by expanding the site objects
    to support prebuilt sorting methods. These methods
    can be used in the templates directly.

    Configuration example
    ---------------------
    #yaml

    sorter:
        kind:
            # Sorts by this attribute name
            # Uses `attrgetter` on the resource object
            attr: source_file.kind

            # The filters to be used before sorting
            # This can be used to remove all the items
            # that do not apply. For example,
            # filtering non html content
            filters:
                source_file.kind: html
                is_processable: True
                meta.is_listable: True
    """

    def __init__(self, site):
        super(SorterPlugin, self).__init__(site)

    def begin_site(self):
        """
        Initialize plugin. Add a sort and match method
        for every configuration mentioned in site settings
        """

        config = self.site.config
        if not hasattr(config, 'sorter'):
            return

        for name, settings in config.sorter.__dict__.items():
            sort_method_name = 'walk_resources_sorted_by_%s' % name
            self.logger.debug("Adding sort methods for [%s]" % name)
            add_method(Node, sort_method_name, sort_method, settings=settings)
            match_method_name = 'is_%s' % name
            add_method(Resource, match_method_name, filter_method, settings)

            prev_att = 'prev_by_%s' % name
            next_att = 'next_by_%s' % name

            setattr(Resource, prev_att, None)
            setattr(Resource, next_att, None)

            walker = getattr(self.site.content,
                                sort_method_name,
                                self.site.content.walk_resources)
            first, last = None, None
            for prev, next in pairwalk(walker()):
                if not first:
                    first = prev
                last = next
                setattr(prev, next_att, next)
                setattr(next, prev_att, prev)

            try:
                circular = settings.circular
            except AttributeError:
                circular = False

            if circular and first:
                setattr(first, prev_att, last)
                setattr(last, next_att, first)


#
# Grouping
#

Grouper = namedtuple('Grouper', 'group resources')

class Group(Expando):
    """
    A wrapper class for groups. Adds methods for
    grouping resources.
    """

    def __init__(self, grouping, parent=None):
        self.name = 'groups'
        self.parent = parent
        self.root = self
        self.root = parent.root if parent else self
        self.groups = []
        self.sorter = getattr(grouping, 'sorter', None)
        if hasattr(parent, 'sorter'):
            self.sorter = parent.sorter
        super(Group, self).__init__(grouping)

        add_method(Node,
                'walk_%s_groups' % self.name,
                Group.walk_groups_in_node,
                group=self)
        add_method(Node,
                'walk_resources_grouped_by_%s' % self.name,
                Group.walk_resources,
                group=self)
        add_property(Resource,
                    '%s_group' % self.name,
                    Group.get_resource_group,
                    group=self)
        add_method(Resource,
                    'walk_%s_groups' % self.name,
                    Group.walk_resource_groups,
                    group=self)

    def set_expando(self, key, value):
        """
        If the key is groups, creates group objects instead of
        regular expando objects.
        """
        if key == "groups":
            self.groups = [Group(group, parent=self) for group in value]
        else:
            return super(Group, self).set_expando(key, value)

    @staticmethod
    def get_resource_group(resource, group):
        """
        This method gets attached to the resource object.
        Returns group and its ancestors that the resource
        belongs to, in that order.
        """
        try:
            group_name = getattr(resource.meta, group.root.name)
        except AttributeError:
            group_name = None

        return next((g for g in group.walk_groups()
                            if g.name == group_name), None) \
                    if group_name \
                    else None

    @staticmethod
    def walk_resource_groups(resource, group):
        """
        This method gets attached to the resource object.
        Returns group and its ancestors that the resource
        belongs to, in that order.
        """
        try:
            group_name = getattr(resource.meta, group.root.name)
        except AttributeError:
            group_name = None
        if group_name:
            for g in group.walk_groups():
                if g.name == group_name:
                    return reversed(list(g.walk_hierarchy()))
        return []

    @staticmethod
    def walk_resources(node, group):
        """
        The method that gets attached to the node
        object for walking the resources in the node
        that belong to this group.
        """
        for group in group.walk_groups():
            for resource in group.walk_resources_in_node(node):
                yield resource

    @staticmethod
    def walk_groups_in_node(node, group):
        """
        The method that gets attached to the node
        object for walking the groups in the node.
        """
        walker = group.walk_groups()
        for g in walker:
            lister = g.walk_resources_in_node(node)
            yield Grouper(group=g, resources=lister)

    def walk_hierarchy(self):
        """
        Walks the group hierarchy starting from
        this group.
        """
        g = self
        yield g
        while g.parent:
            yield g.parent
            g = g.parent

    def walk_groups(self):
        """
        Walks the groups in the current group
        """
        yield self
        for group in self.groups:
            for child in group.walk_groups():
                yield child

    def walk_resources_in_node(self, node):
        """
        Walks the resources in the given node
        sorted based on sorter configuration in this
        group.
        """
        walker = 'walk_resources'
        if hasattr(self, 'sorter') and self.sorter:
            walker = 'walk_resources_sorted_by_' + self.sorter
        walker = getattr(node, walker, getattr(node, 'walk_resources'))
        for resource in walker():
            try:
                group_value = getattr(resource.meta, self.root.name)
            except AttributeError:
                continue
            if group_value == self.name:
                yield resource

class GrouperPlugin(Plugin):
    """
    Grouper plugin for hyde. Adds the ability to do
    group resources and nodes in an arbitrary
    hierarchy.

    Configuration example
    ---------------------
    #yaml
    sorter:
        kind:
            attr: source.kind
    grouper:
       hyde:
           # Categorizes the nodes and resources
           # based on the groups specified here.
           # The node and resource should be tagged
           # with the categories in their metadata
           sorter: kind # A reference to the sorter
           description: Articles about hyde
           groups:
                -
                    name: announcements
                    description: Hyde release announcements
                -
                    name: making of
                    description: Articles about hyde design decisions
                -
                    name: tips and tricks
                    description: >
                        Helpful snippets and tweaks to
                        make hyde more awesome.
    """
    def __init__(self, site):
        super(GrouperPlugin, self).__init__(site)

    def begin_site(self):
        """
        Initialize plugin. Add the specified groups to the
        site context variable.
        """
        config = self.site.config
        if not hasattr(config, 'grouper'):
            return
        if not hasattr(self.site, 'grouper'):
            self.site.grouper = {}

        for name, grouping in self.site.config.grouper.__dict__.items():
            grouping.name = name
            prev_att = 'prev_in_%s' % name
            next_att = 'next_in_%s' % name
            setattr(Resource, prev_att, None)
            setattr(Resource, next_att, None)
            self.site.grouper[name] = Group(grouping)
            walker = Group.walk_resources(
                            self.site.content, self.site.grouper[name])

            for prev, next in pairwalk(walker):
                setattr(next, prev_att, prev)
                setattr(prev, next_att, next)


########NEW FILE########
__FILENAME__ = sphinx
# -*- coding: utf-8 -*-
"""
Sphinx plugin.

This plugin lets you easily include sphinx-generated documentation as part
of your Hyde site.  It is simultaneously a Hyde plugin and a Sphinx plugin.

To make this work, you need to:

    * install sphinx, obviously
    * include your sphinx source files in the Hyde source tree
    * put the sphinx conf.py file in the Hyde site directory
    * point conf.py:master_doc at an appropriate file in the source tree

For example you might have your site set up like this::

    site.yaml    <--  hyde config file
    conf.py      <--  sphinx config file
    contents/
        index.html     <-- non-sphinx files, handled by hyde
        other.html
        api/
            index.rst      <-- files to processed by sphinx
            mymodule.rst

When the site is built, the .rst files will first be processed by sphinx
to generate a HTML docuent, which will then be passed through the normal
hyde templating workflow.  You would end up with::

    deploy/
        index.html     <-- files generated by hyde
        other.html
        api/
            index.html      <-- files generated by sphinx, then hyde
            mymodule.html

"""

#  We need absolute import so that we can import the main "sphinx"
#  module even though this module is also called "sphinx". Ugh.
from __future__ import absolute_import

import os
import json
import tempfile

from hyde.plugin import Plugin
from hyde.model import Expando
from hyde.ext.plugins.meta import MetaPlugin as _MetaPlugin

from commado.util import getLoggerWithNullHandler
from fswrap import File, Folder

logger = getLoggerWithNullHandler('hyde.ext.plugins.sphinx')

try:
    import sphinx
    from sphinx.builders.html import JSONHTMLBuilder
except ImportError:
    logger.error("The sphinx plugin requires sphinx.")
    logger.error("`pip install -U sphinx` to get it.")
    raise


class SphinxPlugin(Plugin):
    """The plugin class for rendering sphinx-generated documentation."""

    def __init__(self, site):
        self.sphinx_build_dir = None
        self._sphinx_config = None
        super(SphinxPlugin, self).__init__(site)

    @property
    def plugin_name(self):
        """The name of the plugin, obivously."""
        return "sphinx"

    @property
    def settings(self):
        """Settings for this plugin.

        This property combines default settings with those specified in the
        site config to produce the final settings for this plugin.
        """
        settings = Expando({})
        settings.sanity_check = True
        settings.conf_path = "."
        settings.block_map = {}
        try:
            user_settings = getattr(self.site.config, self.plugin_name)
        except AttributeError:
            pass
        else:
            for name in dir(user_settings):
                if not name.startswith("_"):
                    setattr(settings,name,getattr(user_settings,name))
        return settings

    @property
    def sphinx_config(self):
        """Configuration options for sphinx.

        This is a lazily-generated property giving the options from the
        sphinx configuration file.  It's generated by actualy executing
        the config file, so don't do anything silly in there.
        """
        if self._sphinx_config is None:
            conf_path = self.settings.conf_path
            conf_path = self.site.sitepath.child_folder(conf_path)
            #  Sphinx always execs the config file in its parent dir.
            conf_file = conf_path.child("conf.py")
            self._sphinx_config = {"__file__":conf_file}
            curdir = os.getcwd()
            os.chdir(conf_path.path)
            try:
                execfile(conf_file,self._sphinx_config)
            finally:
                os.chdir(curdir)
        return self._sphinx_config

    def begin_site(self):
        """Event hook for when site processing begins.

        This hook checks that the site is correctly configured for building
        with sphinx, and adjusts any sphinx-controlled resources so that
        hyde will process them correctly.
        """
        settings = self.settings
        if settings.sanity_check:
            self._sanity_check()
        #  Find and adjust all the resource that will be handled by sphinx.
        #  We need to:
        #    * change the deploy name from .rst to .html
        #    * if a block_map is given, switch off default_block
        suffix = self.sphinx_config.get("source_suffix",".rst")
        for resource in self.site.content.walk_resources():
            if resource.source_file.path.endswith(suffix):
                new_name = resource.source_file.name_without_extension + ".html"
                target_folder = File(resource.relative_deploy_path).parent
                resource.relative_deploy_path = target_folder.child(new_name)
                if settings.block_map:
                    resource.meta.default_block = None

    def begin_text_resource(self,resource,text):
        """Event hook for processing an individual resource.

        If the input resource is a sphinx input file, this method will replace
        replace the text of the file with the sphinx-generated documentation.

        Sphinx itself is run lazily the first time this method is called.
        This means that if no sphinx-related resources need updating, then
        we entirely avoid running sphinx.
        """
        suffix = self.sphinx_config.get("source_suffix",".rst")
        if not resource.source_file.path.endswith(suffix):
            return text
        if self.sphinx_build_dir is None:
            self._run_sphinx()
        output = []
        settings = self.settings
        sphinx_output = self._get_sphinx_output(resource)
        #  If they're set up a block_map, use the specific blocks.
        #  Otherwise, output just the body for use by default_block.
        if not settings.block_map:
            output.append(sphinx_output["body"])
        else:
            for (nm,content) in sphinx_output.iteritems():
                try:
                    block = getattr(settings.block_map,nm)
                except AttributeError:
                    pass
                else:
                    output.append("{%% block %s %%}" % (block,))
                    output.append(content)
                    output.append("{% endblock %}")
        return "\n".join(output)

    def site_complete(self):
        """Event hook for when site processing ends.

        This simply cleans up any temorary build file.
        """
        if self.sphinx_build_dir is not None:
            self.sphinx_build_dir.delete()

    def _sanity_check(self):
        """Check the current site for sanity.

        This method checks that the site is propertly set up for building
        things with sphinx, e.g. it has a config file, a master document,
        the hyde sphinx extension is enabled, and so-on.
        """
        #  Check that the sphinx config file actually exists.
        try:
            sphinx_config = self.sphinx_config
        except EnvironmentError:
            logger.error("Could not read the sphinx config file.")
            conf_path = self.settings.conf_path
            conf_path = self.site.sitepath.child_folder(conf_path)
            conf_file = conf_path.child("conf.py")
            logger.error("Please ensure %s is a valid sphinx config",conf_file)
            logger.error("or set sphinx.conf_path to the directory")
            logger.error("containing your sphinx conf.py")
            raise
        #  Check that the hyde_json extension is loaded
        extensions = sphinx_config.get("extensions",[])
        if "hyde.ext.plugins.sphinx" not in extensions:
            logger.error("The hyde_json sphinx extension is not configured.")
            logger.error("Please add 'hyde.ext.plugins.sphinx' to the list")
            logger.error("of extensions in your sphinx conf.py file.")
            logger.info("(set sphinx.sanity_check=false to disable this check)")
            raise RuntimeError("sphinx is not configured correctly")
        #  Check that the master doc exists in the source tree.
        master_doc = sphinx_config.get("master_doc","index")
        master_doc += sphinx_config.get("source_suffix",".rst")
        master_doc = os.path.join(self.site.content.path,master_doc)
        if not os.path.exists(master_doc):
            logger.error("The sphinx master document doesn't exist.")
            logger.error("Please create the file %s",master_doc)
            logger.error("or change the 'master_doc' setting in your")
            logger.error("sphinx conf.py file.")
            logger.info("(set sphinx.sanity_check=false to disable this check)")
            raise RuntimeError("sphinx is not configured correctly")
        #  Check that I am *before* the other plugins,
        #  with the possible exception of MetaPlugin
        for plugin in self.site.plugins:
            if plugin is self:
                break
            if not isinstance(plugin,_MetaPlugin):
                logger.error("The sphinx plugin is installed after the")
                logger.error("plugin %r.",plugin.__class__.__name__)
                logger.error("It's quite likely that this will break things.")
                logger.error("Please move the sphinx plugin to the top")
                logger.error("of the plugins list.")
                logger.info("(sphinx.sanity_check=false to disable this check)")
                raise RuntimeError("sphinx is not configured correctly")

    def _run_sphinx(self):
        """Run sphinx to generate the necessary output files.

        This method creates a temporary directory for sphinx's output, then
        run sphinx against the Hyde input directory.
        """
        logger.info("running sphinx")
        self.sphinx_build_dir = Folder(tempfile.mkdtemp())
        conf_path = self.site.sitepath.child_folder(self.settings.conf_path)
        sphinx_args = ["sphinx-build"]
        sphinx_args.extend([
            "-b", "hyde_json",
            "-c", conf_path.path,
            self.site.content.path,
            self.sphinx_build_dir.path
        ])
        if sphinx.main(sphinx_args) != 0:
            raise RuntimeError("sphinx build failed")

    def _get_sphinx_output(self,resource):
        """Get the sphinx output for a given resource.

        This returns a dict mapping block names to HTML text fragments.
        The most important fragment is "body" which contains the main text
        of the document.  The other fragments are for things like navigation,
        related pages and so-on.
        """
        relpath = File(resource.relative_path)
        relpath = relpath.parent.child(relpath.name_without_extension+".fjson")
        with open(self.sphinx_build_dir.child(relpath),"rb") as f:
            return json.load(f)



class HydeJSONHTMLBuilder(JSONHTMLBuilder):
    """A slightly-customised JSONHTMLBuilder, for use by Hyde.

    This is a Sphinx builder that serilises the generated HTML fragments into
    a JSON docuent, so they can be later retrieved and dealt with at will.

    The only customistion we do over the standard JSONHTMLBuilder is to
    reference documents with a .html suffix, so that internal link will
    work correctly once things have been processed by Hyde.
    """
    name = "hyde_json"
    def get_target_uri(self, docname, typ=None):
        return docname + ".html"


def setup(app):
    """Sphinx plugin setup function.

    This function allows the module to act as a Sphinx plugin as well as a
    Hyde plugin.  It simply registers the HydeJSONHTMLBuilder class.
    """
    app.add_builder(HydeJSONHTMLBuilder)



########NEW FILE########
__FILENAME__ = structure
# -*- coding: utf-8 -*-
"""
Plugins related to structure
"""

from hyde.ext.plugins.meta import Metadata
from hyde.plugin import Plugin
from hyde.site import Resource
from hyde.util import pairwalk

from fswrap import File, Folder

import os
from fnmatch import fnmatch
import operator


#
# Folder Flattening
#

class FlattenerPlugin(Plugin):
    """
    The plugin class for flattening nested folders.
    """
    def __init__(self, site):
        super(FlattenerPlugin, self).__init__(site)

    def begin_site(self):
        """
        Finds all the folders that need flattening and changes the
        relative deploy path of all resources in those folders.
        """
        items = []
        try:
            items = self.site.config.flattener.items
        except AttributeError:
            pass

        for item in items:
            node = None
            target = ''
            try:
                node = self.site.content.node_from_relative_path(item.source)
                target = Folder(item.target)
            except AttributeError:
                continue
            if node:
                for resource in node.walk_resources():
                    target_path = target.child(resource.name)
                    self.logger.debug(
                        'Flattening resource path [%s] to [%s]' %
                            (resource, target_path))
                    resource.relative_deploy_path = target_path
                for child in node.walk():
                    child.relative_deploy_path = target.path


#
# Combine
#

class CombinePlugin(Plugin):
    """
    To use this combine, the following configuration should be added
    to meta data::
         combine:
            sort: false #Optional. Defaults to true.
            root: content/media #Optional. Path must be relative to content folder - default current folder
            recurse: true #Optional. Default false.
            files:
                - ns1.*.js
                - ns2.*.js
            where: top
            remove: yes

    `files` is a list of resources (or just a resource) that should be
    combined. Globbing is performed. `where` indicate where the
    combination should be done. This could be `top` or `bottom` of the
    file. `remove` tell if we should remove resources that have been
    combined into the resource.
    """

    def __init__(self, site):
        super(CombinePlugin, self).__init__(site)

    def _combined(self, resource):
        """
        Return the list of resources to combine to build this one.
        """
        try:
            config = resource.meta.combine
        except AttributeError:
            return []    # Not a combined resource
        try:
            files = config.files
        except AttributeError:
            raise AttributeError("No resources to combine for [%s]" % resource)
        if type(files) is str:
            files = [ files ]

        # Grab resources to combine

        # select site root
        try:
            root = self.site.content.node_from_relative_path(resource.meta.combine.root)
        except AttributeError:
            root = resource.node

        # select walker
        try:
            recurse = resource.meta.combine.recurse
        except AttributeError:
            recurse = False

        walker = root.walk_resources() if recurse else root.resources

        # Must we sort?
        try:
            sort = resource.meta.combine.sort
        except AttributeError:
            sort = True

        if sort:
            resources = sorted([r for r in walker if any(fnmatch(r.name, f) for f in files)],
                                                    key=operator.attrgetter('name'))
        else:
            resources = [(f, r) for r in walker for f in files if fnmatch(r.name, f)]
            resources = [r[1] for f in files for r in resources if f in r]

        if not resources:
            self.logger.debug("No resources to combine for [%s]" % resource)
            return []

        return resources

    def begin_site(self):
        """
        Initialize the plugin and search for the combined resources
        """
        for node in self.site.content.walk():
            for resource in node.resources:
                resources = self._combined(resource)
                if not resources:
                    continue

                # Build depends
                if not hasattr(resource, 'depends'):
                    resource.depends = []
                resource.depends.extend(
                    [r.relative_path for r in resources
                     if r.relative_path not in resource.depends])

                # Remove combined resources if needed
                if hasattr(resource.meta.combine, "remove") and \
                        resource.meta.combine.remove:
                    for r in resources:
                        self.logger.debug(
                            "Resource [%s] removed because combined" % r)
                        r.is_processable = False

    def begin_text_resource(self, resource, text):
        """
        When generating a resource, add combined file if needed.
        """
        resources = self._combined(resource)
        if not resources:
            return

        where = "bottom"
        try:
            where = resource.meta.combine.where
        except AttributeError:
            pass

        if where not in [ "top", "bottom" ]:
            raise ValueError("%r should be either `top` or `bottom`" % where)

        self.logger.debug(
            "Combining %d resources for [%s]" % (len(resources),
                                                 resource))
        if where == "top":
            return "".join([r.source.read_all() for r in resources] + [text])
        else:
            return "".join([text] + [r.source.read_all() for r in resources])


#
# Pagination
#

class Page:
    def __init__(self, posts, number):
        self.posts = posts
        self.number = number

class Paginator:
    """
    Iterates resources which have pages associated with them.
    """

    file_pattern = 'page$PAGE/$FILE$EXT'

    def __init__(self, settings):
        self.sorter = getattr(settings, 'sorter', None)
        self.size = getattr(settings, 'size', 10)
        self.file_pattern = getattr(settings, 'file_pattern', self.file_pattern)

    def _relative_url(self, source_path, number, basename, ext):
        """
        Create a new URL for a new page.  The first page keeps the same name;
        the subsequent pages are named according to file_pattern.
        """
        path = File(source_path)
        if number != 1:
            filename = self.file_pattern.replace('$PAGE', str(number)) \
                                    .replace('$FILE', basename) \
                                    .replace('$EXT', ext)
            path = path.parent.child(os.path.normpath(filename))
        return path

    def _new_resource(self, base_resource, node, page_number):
        """
        Create a new resource as a copy of a base_resource, with a page of
        resources associated with it.
        """
        res = Resource(base_resource.source_file, node)
        res.node.meta = Metadata(node.meta)
        res.meta = Metadata(base_resource.meta, res.node.meta)
        path = self._relative_url(base_resource.relative_path,
                                page_number,
                                base_resource.source_file.name_without_extension,
                                base_resource.source_file.extension)
        res.set_relative_deploy_path(path)
        return res

    @staticmethod
    def _attach_page_to_resource(page, resource):
        """
        Hook up a page and a resource.
        """
        resource.page = page
        page.resource = resource

    @staticmethod
    def _add_dependencies_to_resource(dependencies, resource):
        """
        Add a bunch of resources as dependencies to another resource.
        """
        if not hasattr(resource, 'depends'):
            resource.depends = []
        resource.depends.extend([dep.relative_path for dep in dependencies
                                if dep.relative_path not in resource.depends])

    def _walk_pages_in_node(self, node):
        """
        Segregate each resource into a page.
        """
        walker = 'walk_resources'
        if self.sorter:
            walker = 'walk_resources_sorted_by_%s' % self.sorter
        walker = getattr(node, walker, getattr(node, 'walk_resources'))

        posts = list(walker())
        number = 1
        while posts:
            yield Page(posts[:self.size], number)
            posts = posts[self.size:]
            number += 1

    def walk_paged_resources(self, node, resource):
        """
        Group the resources and return the new page resources.
        """
        added_resources = []
        pages = list(self._walk_pages_in_node(node))
        if pages:
            deps = reduce(list.__add__, [page.posts for page in pages], [])

            Paginator._attach_page_to_resource(pages[0], resource)
            Paginator._add_dependencies_to_resource(deps, resource)
            for page in pages[1:]:
                # make new resource
                new_resource = self._new_resource(resource, node, page.number)
                Paginator._attach_page_to_resource(page, new_resource)
                new_resource.depends = resource.depends
                added_resources.append(new_resource)

            for prev, next in pairwalk(pages):
                next.previous = prev
                prev.next = next

        return added_resources


class PaginatorPlugin(Plugin):
    """
    Paginator plugin.

    Configuration: in a resource's metadata:

        paginator:
            sorter: time
            size: 5
            file_pattern: page$PAGE/$FILE$EXT   # optional

    then in the resource's content:

        {% for res in resource.page.posts %}
        {% refer to res.relative_path as post %}
        {{ post }}
        {% endfor %}

        {{ resource.page.previous }}
        {{ resource.page.next }}

    """
    def __init__(self, site):
        super(PaginatorPlugin, self).__init__(site)

    def begin_site(self):
        for node in self.site.content.walk():
            added_resources = []
            paged_resources = (res for res in node.resources
                                 if hasattr(res.meta, 'paginator'))
            for resource in paged_resources:
                paginator = Paginator(resource.meta.paginator)
                added_resources += paginator.walk_paged_resources(node, resource)

            node.resources += added_resources


########NEW FILE########
__FILENAME__ = text
# -*- coding: utf-8 -*-
"""
Text processing plugins
"""

from hyde.plugin import Plugin,TextyPlugin


#
# Blockdown
#

class BlockdownPlugin(TextyPlugin):
    """
    The plugin class for block text replacement.
    """
    def __init__(self, site):
        super(BlockdownPlugin, self).__init__(site)

    @property
    def tag_name(self):
        """
        The block tag.
        """
        return 'block'

    @property
    def default_open_pattern(self):
        """
        The default pattern for block open text.
        """
        return '^\s*===+([A-Za-z0-9_\-\.]+)=*\s*$'

    @property
    def default_close_pattern(self):
        """
        The default pattern for block close text.
        """
        return '^\s*===+/+\s*=*/*([A-Za-z0-9_\-\.]*)[\s=/]*$'

    def text_to_tag(self, match, start=True):
        """
        Replace open pattern (default:===[====]blockname[===========])
        with
        {% block blockname %} or equivalent and
        Replace close pattern (default===[====]/[blockname][===========])
        with
        {% endblock blockname %} or equivalent
        """
        return super(BlockdownPlugin, self).text_to_tag(match, start)


#
# Mark Text
#

class MarkingsPlugin(TextyPlugin):
    """
    The plugin class for mark text replacement.
    """
    def __init__(self, site):
        super(MarkingsPlugin, self).__init__(site)

    @property
    def tag_name(self):
        """
        The mark tag.
        """
        return 'mark'

    @property
    def default_open_pattern(self):
        """
        The default pattern for mark open text.
        """
        return u'^§§+\s*([A-Za-z0-9_\-]+)\s*$'

    @property
    def default_close_pattern(self):
        """
        The default pattern for mark close text.
        """
        return u'^§§+\s*/([A-Za-z0-9_\-]*)\s*$'

    def text_to_tag(self, match, start=True):
        """
        Replace open pattern (default:§§ CSS)
        with
        {% mark CSS %} or equivalent and
        Replace close pattern (default: §§ /CSS)
        with
        {% endmark %} or equivalent
        """
        return super(MarkingsPlugin, self).text_to_tag(match, start)


#
# Reference Text
#

class ReferencePlugin(TextyPlugin):
    """
    The plugin class for reference text replacement.
    """
    def __init__(self, site):
        super(ReferencePlugin, self).__init__(site)

    @property
    def tag_name(self):
        """
        The refer tag.
        """
        return 'refer to'

    @property
    def default_open_pattern(self):
        """
        The default pattern for mark open text.
        """
        return u'^※\s*([^\s]+)\s*as\s*([A-Za-z0-9_\-]+)\s*$'

    @property
    def default_close_pattern(self):
        """
        No close pattern.
        """
        return None

    def text_to_tag(self, match, start=True):
        """
        Replace open pattern (default: ※ inc.md as inc)
        with
        {% refer to "inc.md" as inc %} or equivalent.
        """
        if not match.lastindex:
            return ''
        params = '"%s" as %s' % (match.groups(1)[0], match.groups(1)[1])
        return self.template.get_open_tag(self.tag_name, params)


#
# Syntax Text
#

class SyntextPlugin(TextyPlugin):
    """
    The plugin class for syntax text replacement.
    """
    def __init__(self, site):
        super(SyntextPlugin, self).__init__(site)

    @property
    def tag_name(self):
        """
        The syntax tag.
        """
        return 'syntax'

    @property
    def default_open_pattern(self):
        """
        The default pattern for block open text.
        """
        return '^\s*~~~+\s*([A-Za-z0-9_\-\.:\']+)\s*~*\s*$'

    @property
    def default_close_pattern(self):
        """
        The default pattern for block close text.
        """
        return '^\s*~~~+\s*$'


    def get_params(self, match, start=True):
        """
        ~~~css~~~ will return css
        ~~~css/style.css will return css,style.css
        """
        params = super(SyntextPlugin, self).get_params(match, start)
        if ':' in params:
            (lex, _, filename) = params.rpartition(':')
            params = 'lex=\'%(lex)s\',filename=\'%(filename)s\'' % locals()
        return params

    def text_to_tag(self, match, start=True):
        """
        Replace open pattern (default:~~~~~css~~~~~~)
        with
        {% syntax css %} or equivalent and
        Replace close pattern (default: ~~~~~~)
        with
        {% endsyntax %} or equivalent
        """
        return super(SyntextPlugin, self).text_to_tag(match, start)


#
# Text Links
#

class TextlinksPlugin(Plugin):
    """
    The plugin class for text link replacement.
    """
    def __init__(self, site):
        super(TextlinksPlugin, self).__init__(site)
        import re
        self.content_link = re.compile('\[\[([^\]^!][^\]]*)\]\]',
                                       re.UNICODE|re.MULTILINE)
        self.media_link = re.compile('\[\[\!\!([^\]]*)\]\]',
                                     re.UNICODE|re.MULTILINE)

    def begin_text_resource(self, resource, text):
        """
        Replace content url pattern [[/abc/def]])
        with
        {{ content_url('/abc/def') }} or equivalent and
        Replace media url pattern [[!!/abc/def]]
        with
        {{ media_url('/abc/def') }} or equivalent.
        """
        if not resource.uses_template:
            return text
        def replace_content(match):
            return self.template.get_content_url_statement(match.groups(1)[0])
        def replace_media(match):
            return self.template.get_media_url_statement(match.groups(1)[0])
        text = self.content_link.sub(replace_content, text)
        text = self.media_link.sub(replace_media, text)
        return text


########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""
Contains classes and utilities related to hyde urls.
"""
from hyde.plugin import Plugin
from hyde.site import Site

from functools import wraps
from fswrap import File

class UrlCleanerPlugin(Plugin):
    """
    Url Cleaner plugin for hyde. Adds to hyde the ability to generate clean
    urls.

    Configuration example
    ---------------------
    #yaml
    urlcleaner:
        index_file_names:
            # Identifies the files that represents a directory listing.
            # These file names are automatically stripped away when
            # the content_url function is called.
            - index.html
        strip_extensions:
            # The following extensions are automatically removed when
            # generating the urls using content_url function.
            - html
        # This option will append a slash to the end of directory paths
        append_slash: true
    """

    def __init__(self, site):
        super(UrlCleanerPlugin, self).__init__(site)

    def begin_site(self):
        """
        Replace the content_url method in the site object with a custom method
        that cleans urls based on the given configuration.
        """
        config = self.site.config

        if not hasattr(config, 'urlcleaner'):
            return

        if (hasattr(Site, '___url_cleaner_patched___')):
            return

        settings = config.urlcleaner

        def clean_url(urlgetter):
            @wraps(urlgetter)
            def wrapper(site, path, safe=None):
                url = urlgetter(site, path, safe)
                index_file_names = getattr(settings,
                                        'index_file_names',
                                        ['index.html'])
                rep = File(url)
                if rep.name in index_file_names:
                    url = rep.parent.path.rstrip('/')
                    if hasattr(settings, 'append_slash') and \
                        settings.append_slash:
                        url += '/'
                elif hasattr(settings, 'strip_extensions'):
                    if rep.kind in settings.strip_extensions:
                        url = rep.parent.child(rep.name_without_extension)
                return url or '/'
            return wrapper

        Site.___url_cleaner_patched___ = True
        Site.content_url = clean_url(Site.content_url)

########NEW FILE########
__FILENAME__ = vcs
# -*- coding: utf-8 -*-
"""
Contains classes and utilities to extract information from repositories
"""

from hyde.plugin import Plugin

from datetime import datetime
from dateutil.parser import parse
import os.path
import subprocess


class VCSDatesPlugin(Plugin):
    """
    Base class for getting resource timestamps from VCS.
    """
    def __init__(self, site, vcs_name='vcs'):
        super(VCSDatesPlugin, self).__init__(site)
        self.vcs_name = vcs_name

    def begin_site(self):
        for node in self.site.content.walk():
            for resource in node.resources:
                created = None
                modified = None
                try:
                    created = resource.meta.created
                    modified = resource.meta.modified
                except AttributeError:
                    pass

                # Everything is already overrided
                if created != self.vcs_name and modified != self.vcs_name:
                    continue

                date_created, date_modified = self.get_dates(resource)

                if created == "git":
                    created = date_created or \
                                datetime.utcfromtimestamp(
                                    os.path.getctime(resource.path))
                    created = created.replace(tzinfo=None)
                    resource.meta.created = created

                if modified == "git":
                    modified = date_modified or resource.source.last_modified
                    modified = modified.replace(tzinfo=None)
                    resource.meta.modified = modified


    def get_dates(self):
        """
        Extract creation and last modification date from the vcs and include
        them in the meta data if they are set to "<vcs_name>". Creation date
        is put in `created` and last modification date in `modified`.
        """
        return None, None

#
# Git Dates
#
class GitDatesPlugin(VCSDatesPlugin):
    def __init__(self, site):
        super(GitDatesPlugin, self).__init__(site, 'git')

    def get_dates(self, resource):
        """
        Retrieve dates from git
        """
        # Run git log --pretty=%ai
        try:
            commits = subprocess.check_output([
                "git",
                "log",
                "--pretty=%ai",
                resource.path
            ]).split("\n")
            commits = commits[:-1]
        except subprocess.CalledProcessError:
            self.logger.warning("Unable to get git history for [%s]" % resource)
            commits = None

        if commits:
            created = parse(commits[-1].strip())
            modified = parse(commits[0].strip())
        else:
            self.logger.warning("No git history for [%s]" % resource)
            created, modified = None, None

        return created, modified

#
# Mercurial Dates
#
class MercurialDatesPlugin(VCSDatesPlugin):

    def __init__(self, site):
        super(MercurialDatesPlugin, self).__init__(site, 'hg')

    def get_dates(self, resource):
        """
        Retrieve dates from mercurial
        """
        # Run hg log --template={date|isodatesec}
        try:
            commits = subprocess.check_output([
                            "hg", "log", "--template={date|isodatesec}\n",
                                               resource.path]).split('\n')
            commits = commits[:-1]
        except subprocess.CalledProcessError:
            self.logger.warning("Unable to get mercurial history for [%s]"
                                             % resource)
            commits = None

        if not commits:
            self.logger.warning("No mercurial history for [%s]" % resource)
            return None, None

        created = parse(commits[-1].strip())
        modified = parse(commits[0].strip())
        return created, modified

########NEW FILE########
__FILENAME__ = dvcs
"""
Contains classes and utilities that help publishing a hyde website to
distributed version control systems.
"""

from hyde.publisher import Publisher

import abc
from subprocess import Popen, PIPE

class DVCS(Publisher):
    __metaclass__ = abc.ABCMeta

    def initialize(self, settings):
        self.settings = settings
        self.path = self.site.sitepath.child_folder(settings.path)
        self.url = settings.url
        self.branch = getattr(settings, 'branch', 'master')
        self.switch(self.branch)

    @abc.abstractmethod
    def pull(self): pass

    @abc.abstractmethod
    def push(self): pass

    @abc.abstractmethod
    def commit(self, message): pass

    @abc.abstractmethod
    def switch(self, branch): pass

    @abc.abstractmethod
    def add(self, path="."): pass

    @abc.abstractmethod
    def merge(self, branch): pass


    def publish(self):
        super(DVCS, self).publish()
        if not self.path.exists:
            raise Exception("The destination repository must exist.")
        self.site.config.deploy_root_path.copy_contents_to(self.path)
        self.add()
        self.commit(self.message)
        self.push()



class Git(DVCS):
    """
    Acts as a publisher to a git repository. Can be used to publish to
    github pages.
    """

    def add(self, path="."):
        cmd = Popen('git add "%s"' % path,
                        cwd=unicode(self.path), stdout=PIPE, shell=True)
        cmdresult = cmd.communicate()[0]
        if cmd.returncode:
            raise Exception(cmdresult)

    def pull(self):
        self.switch(self.branch)
        cmd = Popen("git pull origin %s" % self.branch,
                    cwd=unicode(self.path),
                    stdout=PIPE,
                    shell=True)
        cmdresult = cmd.communicate()[0]
        if cmd.returncode:
            raise Exception(cmdresult)

    def push(self):
        cmd = Popen("git push origin %s" % self.branch,
                    cwd=unicode(self.path), stdout=PIPE,
                    shell=True)
        cmdresult = cmd.communicate()[0]
        if cmd.returncode:
            raise Exception(cmdresult)


    def commit(self, message):
        cmd = Popen('git commit -a -m"%s"' % message,
                    cwd=unicode(self.path), stdout=PIPE, shell=True)
        cmdresult = cmd.communicate()[0]
        if cmd.returncode:
            raise Exception(cmdresult)

    def switch(self, branch):
        self.branch = branch
        cmd = Popen('git checkout %s' % branch,
                    cwd=unicode(self.path), stdout=PIPE, shell=True)
        cmdresult = cmd.communicate()[0]
        if cmd.returncode:
            raise Exception(cmdresult)

    def merge(self, branch):
        cmd = Popen('git merge %s' % branch,
                    cwd=unicode(self.path), stdout=PIPE, shell=True)
        cmdresult = cmd.communicate()[0]
        if cmd.returncode:
            raise Exception(cmdresult)
########NEW FILE########
__FILENAME__ = pyfs
"""
Contains classes and utilities that help publishing a hyde website to
a filesystem using PyFilesystem FS objects.

This publisher provides an easy way to publish to FTP, SFTP, WebDAV or other
servers by specifying a PyFS filesystem URL.  For example, the following
are valid URLs that can be used with this publisher:

    ftp://my.server.com/~username/my_blog/
    dav:https://username:password@my.server.com/path/to/my/site

"""

import getpass
import hashlib


from hyde.publisher import Publisher

from commando.util import getLoggerWithNullHandler

logger = getLoggerWithNullHandler('hyde.ext.publishers.pyfs')


try:
    from fs.osfs import OSFS
    from fs.path import pathjoin
    from fs.opener import fsopendir
except ImportError:
    logger.error("The PyFS publisher requires PyFilesystem v0.4 or later.")
    logger.error("`pip install -U fs` to get it.")
    raise



class PyFS(Publisher):

    def initialize(self, settings):
        self.settings = settings
        self.url = settings.url
        self.check_mtime = getattr(settings,"check_mtime",False)
        self.check_etag = getattr(settings,"check_etag",False)
        if self.check_etag and not isinstance(self.check_etag,basestring):
            raise ValueError("check_etag must name the etag algorithm")
        self.prompt_for_credentials()
        self.fs = fsopendir(self.url)

    def prompt_for_credentials(self):
        credentials = {}
        if "%(username)s" in self.url:
            print "Username: ",
            credentials["username"] = raw_input().strip()
        if "%(password)s" in self.url:
            credentials["password"] = getpass.getpass("Password: ")
        if credentials:
            self.url = self.url % credentials

    def publish(self):
        super(PyFS, self).publish()
        deploy_fs = OSFS(self.site.config.deploy_root_path.path)
        for (dirnm,local_filenms) in deploy_fs.walk():
            logger.info("Making directory: %s",dirnm)
            self.fs.makedir(dirnm,allow_recreate=True)
            remote_fileinfos = self.fs.listdirinfo(dirnm,files_only=True)
            #  Process each local file, to see if it needs updating.
            for filenm in local_filenms:
                filepath = pathjoin(dirnm,filenm)
                #  Try to find an existing remote file, to compare metadata.
                for (nm,info) in remote_fileinfos:
                    if nm == filenm:
                        break
                else:
                    info = {}
                #  Skip it if the etags match
                if self.check_etag and "etag" in info:
                    with deploy_fs.open(filepath,"rb") as f:
                        local_etag = self._calculate_etag(f)
                    if info["etag"] == local_etag:
                        logger.info("Skipping file [etag]: %s",filepath)
                        continue
                #  Skip it if the mtime is more recent remotely.
                if self.check_mtime and "modified_time" in info:
                    local_mtime = deploy_fs.getinfo(filepath)["modified_time"]
                    if info["modified_time"] > local_mtime:
                        logger.info("Skipping file [mtime]: %s",filepath)
                        continue
                #  Upload it to the remote filesystem.
                logger.info("Uploading file: %s",filepath)
                with deploy_fs.open(filepath,"rb") as f:
                    self.fs.setcontents(filepath,f)
            #  Process each remote file, to see if it needs deleting.
            for (filenm,info) in remote_fileinfos:
                filepath = pathjoin(dirnm,filenm)
                if filenm not in local_filenms:
                    logger.info("Removing file: %s",filepath)
                    self.fs.remove(filepath)

    def _calculate_etag(self,f):
        hasher = getattr(hashlib,self.check_etag.lower())()
        data = f.read(1024*64)
        while data:
            hasher.update(data)
            data = f.read(1024*64)
        return hasher.hexdigest()


########NEW FILE########
__FILENAME__ = pypi
"""
Contains classes and utilities that help publishing a hyde website to
the documentation hosting on http://packages.python.org/.

"""

import os
import getpass
import zipfile
import tempfile
import httplib
import urlparse
from base64 import standard_b64encode
import ConfigParser

from hyde.publisher import Publisher

from commando.util import getLoggerWithNullHandler
logger = getLoggerWithNullHandler('hyde.ext.publishers.pypi')




class PyPI(Publisher):

    def initialize(self, settings):
        self.settings = settings
        self.project = settings.project
        self.url = getattr(settings,"url","https://pypi.python.org/pypi/")
        self.username = getattr(settings,"username",None)
        self.password = getattr(settings,"password",None)
        self.prompt_for_credentials()

    def prompt_for_credentials(self):
        pypirc_file = os.path.expanduser("~/.pypirc")
        if not os.path.isfile(pypirc_file):
            pypirc = None
        else:
            pypirc = ConfigParser.RawConfigParser()
            pypirc.read([pypirc_file])
        missing_errs = (ConfigParser.NoSectionError,ConfigParser.NoOptionError)
        #  Try to find username in .pypirc
        if self.username is None:
            if pypirc is not None:
                try:
                    self.username = pypirc.get("server-login","username")
                except missing_errs:
                    pass
        #  Prompt for username on command-line
        if self.username is None:
            print "Username: ",
            self.username = raw_input().strip()
        #  Try to find password in .pypirc
        if self.password is None:
            if pypirc is not None:
                try:
                    self.password = pypirc.get("server-login","password")
                except missing_errs:
                    pass
        #  Prompt for username on command-line
        if self.password is None:
            self.password = getpass.getpass("Password: ")
        #  Validate the values.
        if not self.username:
            raise ValueError("PyPI requires a username")
        if not self.password:
            raise ValueError("PyPI requires a password")

    def publish(self):
        super(PyPI, self).publish()
        tf = tempfile.TemporaryFile()
        try:
            #  Bundle it up into a zipfile
            logger.info("building the zipfile")
            root = self.site.config.deploy_root_path
            zf = zipfile.ZipFile(tf,"w",zipfile.ZIP_DEFLATED)
            try:
                for item in root.walker.walk_files():
                    logger.info("  adding file: %s",item.path)
                    zf.write(item.path,item.get_relative_path(root))
            finally:
                zf.close()
            #  Formulate the necessary bits for the HTTP POST.
            #  Multipart/form-data encoding.  Yuck.
            authz = self.username + ":" + self.password
            authz = "Basic " + standard_b64encode(authz)
            boundary = "-----------" + os.urandom(20).encode("hex")
            sep_boundary = "\r\n--" + boundary
            end_boundary = "\r\n--" + boundary + "--\r\n"
            content_type = "multipart/form-data; boundary=%s" % (boundary,)
            items = ((":action","doc_upload"),("name",self.project))
            body_prefix = ""
            for (name,value) in items:
                body_prefix += "--" + boundary + "\r\n"
                body_prefix += "Content-Disposition: form-data; name=\""
                body_prefix += name + "\"\r\n\r\n"
                body_prefix += value + "\r\n"
            body_prefix += "--" + boundary + "\r\n"
            body_prefix += "Content-Disposition: form-data; name=\"content\""
            body_prefix += "; filename=\"website.zip\"\r\n\r\n"
            body_suffix = "\r\n--" + boundary + "--\r\n"
            content_length = len(body_prefix) + tf.tell() + len(body_suffix)
            #  POST it up to PyPI
            logger.info("uploading to PyPI")
            url = urlparse.urlparse(self.url)
            if url.scheme == "https":
                con = httplib.HTTPSConnection(url.netloc)
            else:
                con = httplib.HTTPConnection(url.netloc)
            con.connect()
            try:
                con.putrequest("POST", self.url)
                con.putheader("Content-Type",content_type)
                con.putheader("Content-Length",str(content_length))
                con.putheader("Authorization",authz)
                con.endheaders()
                con.send(body_prefix)
                tf.seek(0)
                data = tf.read(1024*32)
                while data:
                    con.send(data)
                    data = tf.read(1024*32)
                con.send(body_suffix)
                r = con.getresponse()
                try:
                    #  PyPI tries to redirect to the page on success.
                    if r.status in (200,301,):
                        logger.info("success!")
                    else:
                        msg = "Upload failed: %s %s" % (r.status,r.reason,)
                        raise Exception(msg)
                finally:
                    r.close()
            finally:
                con.close()
        finally:
            tf.close()



########NEW FILE########
__FILENAME__ = ssh
"""
SSH publisher
=============
Contains classes and utilities that help publishing a hyde website
via ssh/rsync.

Usage
-----
In site.yaml, add the following lines

    publisher:
        ssh:
            type: hyde.ext.publishers.ssh.SSH
            username: username
            server: ssh.server.com
            target: /www/username/mysite/
            command: rsync
            opts: -r -e ssh

Note that the final two settings (command and opts) are optional, and the
values shown are the default. Username is also optional.
With this set, generate and publish the site as follows:

    >$ hyde gen
    >$ hyde publish -p ssh

For the above options, this will lead to execution of the following command
within the ``deploy/`` directory:

    rsync -r -e ssh ./ username@ssh.server.com:/www/username/mysite/

"""
from hyde.publisher import Publisher

from subprocess import Popen, PIPE

class SSH(Publisher):
    def initialize(self, settings):
        self.settings = settings
        self.username = settings.username
        self.server = settings.server
        self.target = settings.target
        self.command = getattr(settings, 'command', 'rsync')
        self.opts = getattr(settings, 'opts', '-r -e ssh')

    def publish(self):
        command = "{command} {opts} ./ {username}{server}:{target}".format(
            command=self.command,
            opts=self.opts,
            username=self.username+'@' if self.username else '',
            server=self.server,
            target=self.target)
        deploy_path = self.site.config.deploy_root_path.path

        cmd = Popen(command, cwd=unicode(deploy_path), stdout=PIPE, shell=True)
        cmdresult = cmd.communicate()[0]
        if cmd.returncode:
            raise Exception(cmdresult)

########NEW FILE########
__FILENAME__ = jinja
# -*- coding: utf-8 -*-
"""
Jinja template utilties
"""

from datetime import datetime, date
import itertools
import os
import re
import sys
from urllib import quote, unquote

from hyde.exceptions import HydeException
from hyde.model import Expando
from hyde.template import HtmlWrap, Template
from operator import attrgetter

from jinja2 import (
    contextfunction,
    Environment,
    FileSystemLoader,
    FileSystemBytecodeCache
)
from jinja2 import contextfilter, environmentfilter, Markup, Undefined, nodes
from jinja2.ext import Extension
from jinja2.exceptions import TemplateError

from commando.util import getLoggerWithNullHandler

logger = getLoggerWithNullHandler('hyde.engine.Jinja2')

class SilentUndefined(Undefined):
    """
    A redefinition of undefined that eats errors.
    """
    def __getattr__(self, name):
        return self

    __getitem__ = __getattr__

    def __call__(self, *args, **kwargs):
        return self

@contextfunction
def media_url(context, path, safe=None):
    """
    Returns the media url given a partial path.
    """
    return context['site'].media_url(path, safe)

@contextfunction
def content_url(context, path, safe=None):
    """
    Returns the content url given a partial path.
    """
    return context['site'].content_url(path, safe)

@contextfunction
def full_url(context, path, safe=None):
    """
    Returns the full url given a partial path.
    """
    return context['site'].full_url(path, safe)

@contextfilter
def urlencode(ctx, url, safe=None):
    if safe is not None:
        return quote(url.encode('utf8'), safe)
    else:
        return quote(url.encode('utf8'))

@contextfilter
def urldecode(ctx, url):
    return unquote(url).decode('utf8')

@contextfilter
def date_format(ctx, dt, fmt=None):
    if not dt:
        dt = datetime.now()
    if not isinstance(dt, datetime) or \
        not isinstance(dt, date):
        logger.error("Date format called on a non date object")
        return dt

    format = fmt or "%a, %d %b %Y"
    if not fmt:
        global_format = ctx.resolve('dateformat')
        if not isinstance(global_format, Undefined):
            format = global_format
    return dt.strftime(format)


def islice(iterable, start=0, stop=3, step=1):
    return itertools.islice(iterable, start, stop, step)

def top(iterable, count=3):
    return islice(iterable, stop=count)

def xmldatetime(dt):
    if not dt:
        dt = datetime.now()
    zprefix = "Z"
    tz = dt.strftime("%z")
    if tz:
        zprefix = tz[:3] + ":" + tz[3:]
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + zprefix

@environmentfilter
def asciidoc(env, value):
    """
    (simple) Asciidoc filter
    """
    try:
        from asciidocapi import AsciiDocAPI
    except ImportError:
        print u"Requires AsciiDoc library to use AsciiDoc tag."
        raise

    import StringIO
    output = value

    asciidoc = AsciiDocAPI()
    asciidoc.options('--no-header-footer')
    result = StringIO.StringIO()
    asciidoc.execute(StringIO.StringIO(output.encode('utf-8')), result, backend='html4')
    return unicode(result.getvalue(), "utf-8")

@environmentfilter
def markdown(env, value):
    """
    Markdown filter with support for extensions.
    """
    try:
        import markdown as md
    except ImportError:
        logger.error(u"Cannot load the markdown library.")
        raise TemplateError(u"Cannot load the markdown library")
    output = value
    d = {}
    if hasattr(env.config, 'markdown'):
        d['extensions'] = getattr(env.config.markdown, 'extensions', [])
        d['extension_configs'] = getattr(env.config.markdown,
                                        'extension_configs',
                                        Expando({})).to_dict()
        if hasattr(env.config.markdown, 'output_format'):
            d['output_format'] = env.config.markdown.output_format
    marked = md.Markdown(**d)

    return marked.convert(output)

@environmentfilter
def restructuredtext(env, value):
    """
    RestructuredText filter
    """
    try:
        from docutils.core import publish_parts
    except ImportError:
        logger.error(u"Cannot load the docutils library.")
        raise TemplateError(u"Cannot load the docutils library.")

    highlight_source = False
    if hasattr(env.config, 'restructuredtext'):
        highlight_source = getattr(env.config.restructuredtext, 'highlight_source', False)
        extensions = getattr(env.config.restructuredtext, 'extensions', [])
        import imp
        for extension in extensions:
            imp.load_module(extension, *imp.find_module(extension))

    if highlight_source:
        import hyde.lib.pygments.rst_directive

    parts = publish_parts(source=value, writer_name="html")
    return parts['html_body']

@environmentfilter
def syntax(env, value, lexer=None, filename=None):
    """
    Processes the contained block using `pygments`
    """
    try:
        import pygments
        from pygments import lexers
        from pygments import formatters
    except ImportError:
        logger.error(u"pygments library is required to"
                        " use syntax highlighting tags.")
        raise TemplateError("Cannot load pygments")

    pyg = (lexers.get_lexer_by_name(lexer)
                if lexer else
                    lexers.guess_lexer(value))
    settings = {}
    if hasattr(env.config, 'syntax'):
        settings = getattr(env.config.syntax,
                            'options',
                            Expando({})).to_dict()

    formatter = formatters.HtmlFormatter(**settings)
    code = pygments.highlight(value, pyg, formatter)
    code = code.replace('\n\n', '\n&nbsp;\n').replace('\n', '<br />')
    caption = filename if filename else pyg.name
    if hasattr(env.config, 'syntax'):
        if not getattr(env.config.syntax, 'use_figure', True):
            return Markup(code)
    return Markup(
            '<div class="codebox"><figure class="code">%s<figcaption>%s</figcaption></figure></div>\n\n'
                        % (code, caption))

class Spaceless(Extension):
    """
    Emulates the django spaceless template tag.
    """

    tags = set(['spaceless'])

    def parse(self, parser):
        """
        Parses the statements and calls back to strip spaces.
        """
        lineno = parser.stream.next().lineno
        body = parser.parse_statements(['name:endspaceless'],
                drop_needle=True)
        return nodes.CallBlock(
                    self.call_method('_render_spaceless'),
                    [], [], body).set_lineno(lineno)

    def _render_spaceless(self, caller=None):
        """
        Strip the spaces between tags using the regular expression
        from django. Stolen from `django.util.html` Returns the given HTML
        with spaces between tags removed.
        """
        if not caller:
            return ''
        return re.sub(r'>\s+<', '><', unicode(caller().strip()))

class Asciidoc(Extension):
    """
    A wrapper around the asciidoc filter for syntactic sugar.
    """
    tags = set(['asciidoc'])

    def parse(self, parser):
        """
        Parses the statements and defers to the callback for asciidoc processing.
        """
        lineno = parser.stream.next().lineno
        body = parser.parse_statements(['name:endasciidoc'], drop_needle=True)

        return nodes.CallBlock(
                    self.call_method('_render_asciidoc'),
                        [], [], body).set_lineno(lineno)

    def _render_asciidoc(self, caller=None):
        """
        Calls the asciidoc filter to transform the output.
        """
        if not caller:
            return ''
        output = caller().strip()
        return asciidoc(self.environment, output)

class Markdown(Extension):
    """
    A wrapper around the markdown filter for syntactic sugar.
    """
    tags = set(['markdown'])

    def parse(self, parser):
        """
        Parses the statements and defers to the callback for markdown processing.
        """
        lineno = parser.stream.next().lineno
        body = parser.parse_statements(['name:endmarkdown'], drop_needle=True)

        return nodes.CallBlock(
                    self.call_method('_render_markdown'),
                        [], [], body).set_lineno(lineno)

    def _render_markdown(self, caller=None):
        """
        Calls the markdown filter to transform the output.
        """
        if not caller:
            return ''
        output = caller().strip()
        return markdown(self.environment, output)

class restructuredText(Extension):
    """
    A wrapper around the restructuredtext filter for syntactic sugar
    """
    tags = set(['restructuredtext'])

    def parse(self, parser):
        """
        Simply extract our content
        """
        lineno = parser.stream.next().lineno
        body = parser.parse_statements(['name:endrestructuredtext'], drop_needle=True)

        return nodes.CallBlock(self.call_method('_render_rst'), [],  [], body
                              ).set_lineno(lineno)

    def _render_rst(self, caller=None):
        """
        call our restructuredtext filter
        """
        if not caller:
            return ''
        output = caller().strip()
        return restructuredtext(self.environment, output)

class YamlVar(Extension):
    """
    An extension that converts the content between the tags
    into an yaml object and sets the value in the given
    variable.
    """

    tags = set(['yaml'])

    def parse(self, parser):
        """
        Parses the contained data and defers to the callback to load it as
        yaml.
        """
        lineno = parser.stream.next().lineno
        var = parser.stream.expect('name').value
        body = parser.parse_statements(['name:endyaml'], drop_needle=True)
        return [
                nodes.Assign(
                    nodes.Name(var, 'store'),
                    nodes.Const({})
                    ).set_lineno(lineno),
                nodes.CallBlock(
                    self.call_method('_set_yaml',
                            args=[nodes.Name(var, 'load')]),
                            [], [], body).set_lineno(lineno)
                ]


    def _set_yaml(self, var, caller=None):
        """
        Loads the yaml data into the specified variable.
        """
        if not caller:
            return ''
        try:
            import yaml
        except ImportError:
            return ''

        out = caller().strip()
        var.update(yaml.load(out))
        return ''

def parse_kwargs(parser):
    """
    Parses keyword arguments in tags.
    """
    name = parser.stream.expect('name').value
    parser.stream.expect('assign')
    if parser.stream.current.test('string'):
        value = parser.parse_expression()
    else:
        value = nodes.Const(parser.stream.next().value)
    return (name, value)

class Syntax(Extension):
    """
    A wrapper around the syntax filter for syntactic sugar.
    """

    tags = set(['syntax'])


    def parse(self, parser):
        """
        Parses the statements and defers to the callback for pygments processing.
        """
        lineno = parser.stream.next().lineno
        lex = nodes.Const(None)
        filename = nodes.Const(None)

        if not parser.stream.current.test('block_end'):
            if parser.stream.look().test('assign'):
                name = value = value1 = None
                (name, value) = parse_kwargs(parser)
                if parser.stream.skip_if('comma'):
                    (_, value1) = parse_kwargs(parser)

                (lex, filename) = (value, value1) \
                                        if name == 'lex' \
                                            else (value1, value)
            else:
                lex = nodes.Const(parser.stream.next().value)
                if parser.stream.skip_if('comma'):
                    filename = parser.parse_expression()

        body = parser.parse_statements(['name:endsyntax'], drop_needle=True)
        return nodes.CallBlock(
                    self.call_method('_render_syntax',
                        args=[lex, filename]),
                        [], [], body).set_lineno(lineno)


    def _render_syntax(self, lex, filename, caller=None):
        """
        Calls the syntax filter to transform the output.
        """
        if not caller:
            return ''
        output = caller().strip()
        return syntax(self.environment, output, lex, filename)

class IncludeText(Extension):
    """
    Automatically runs `markdown` and `typogrify` on included
    files.
    """

    tags = set(['includetext'])

    def parse(self, parser):
        """
        Delegates all the parsing to the native include node.
        """
        node = parser.parse_include()
        return nodes.CallBlock(
                    self.call_method('_render_include_text'),
                        [], [], [node]).set_lineno(node.lineno)

    def _render_include_text(self, caller=None):
        """
        Runs markdown and if available, typogrigy on the
        content returned by the include node.
        """
        if not caller:
            return ''
        output = caller().strip()
        output = markdown(self.environment, output)
        if 'typogrify' in self.environment.filters:
            typo = self.environment.filters['typogrify']
            output = typo(output)
        return output

MARKINGS = '_markings_'

class Reference(Extension):
    """
    Marks a block in a template such that its available for use
    when referenced using a `refer` tag.
    """

    tags = set(['mark', 'reference'])

    def parse(self, parser):
        """
        Parse the variable name that the content must be assigned to.
        """
        token = parser.stream.next()
        lineno = token.lineno
        tag = token.value
        name = parser.stream.next().value
        body = parser.parse_statements(['name:end%s' % tag], drop_needle=True)
        return nodes.CallBlock(
                    self.call_method('_render_output',
                        args=[nodes.Name(MARKINGS, 'load'), nodes.Const(name)]),
                        [], [], body).set_lineno(lineno)


    def _render_output(self, markings, name, caller=None):
        """
        Assigns the result of the contents to the markings variable.
        """
        if not caller:
            return ''
        out = caller()
        if isinstance(markings, dict):
            markings[name] = out
        return out

class Refer(Extension):
    """
    Imports content blocks specified in the referred template as
    variables in a given namespace.
    """
    tags = set(['refer'])

    def parse(self, parser):
        """
        Parse the referred template and the namespace.
        """
        token = parser.stream.next()
        lineno = token.lineno
        parser.stream.expect('name:to')
        template = parser.parse_expression()
        parser.stream.expect('name:as')
        namespace = parser.stream.next().value
        includeNode = nodes.Include(lineno=lineno)
        includeNode.with_context = True
        includeNode.ignore_missing = False
        includeNode.template = template

        temp = parser.free_identifier(lineno)

        return [
                nodes.Assign(
                    nodes.Name(temp.name, 'store'),
                    nodes.Name(MARKINGS, 'load')
                ).set_lineno(lineno),
                nodes.Assign(
                    nodes.Name(MARKINGS, 'store'),
                    nodes.Const({})).set_lineno(lineno),
                nodes.Assign(
                    nodes.Name(namespace, 'store'),
                    nodes.Const({})).set_lineno(lineno),
                nodes.CallBlock(
                    self.call_method('_push_resource',
                            args=[
                                nodes.Name(namespace, 'load'),
                                nodes.Name('site', 'load'),
                                nodes.Name('resource', 'load'),
                                template]),
                            [], [], []).set_lineno(lineno),
                nodes.Assign(
                    nodes.Name('resource', 'store'),
                    nodes.Getitem(nodes.Name(namespace, 'load'),
                        nodes.Const('resource'), 'load')
                    ).set_lineno(lineno),
                nodes.CallBlock(
                    self.call_method('_assign_reference',
                            args=[
                                nodes.Name(MARKINGS, 'load'),
                                nodes.Name(namespace, 'load')]),
                            [], [], [includeNode]).set_lineno(lineno),
                nodes.Assign(nodes.Name('resource', 'store'),
                            nodes.Getitem(nodes.Name(namespace, 'load'),
                            nodes.Const('parent_resource'), 'load')
                    ).set_lineno(lineno),
                    nodes.Assign(
                        nodes.Name(MARKINGS, 'store'),
                        nodes.Name(temp.name, 'load')
                    ).set_lineno(lineno),
        ]

    def _push_resource(self, namespace, site, resource, template, caller):
        """
        Saves the current references in a stack.
        """
        namespace['parent_resource'] = resource
        if not hasattr(resource, 'depends'):
            resource.depends = []
        if not template in resource.depends:
            resource.depends.append(template)
        namespace['resource'] = site.content.resource_from_relative_path(
                                    template)
        return ''

    def _assign_reference(self, markings, namespace, caller):
        """
        Assign the processed variables into the
        given namespace.
        """

        out = caller()
        for key, value in markings.items():
            namespace[key] = value
        namespace['html'] = HtmlWrap(out)
        return ''


class HydeLoader(FileSystemLoader):
    """
    A wrapper around the file system loader that performs
    hyde specific tweaks.
    """

    def __init__(self, sitepath, site, preprocessor=None):
        config = site.config if hasattr(site, 'config') else None
        if config:
            super(HydeLoader, self).__init__([
                            unicode(config.content_root_path),
                            unicode(config.layout_root_path),
                        ])
        else:
            super(HydeLoader, self).__init__(unicode(sitepath))

        self.site = site
        self.preprocessor = preprocessor

    def get_source(self, environment, template):
        """
        Calls the plugins to preprocess prior to returning the source.
        """
        template = template.strip()
        # Fixed so that jinja2 loader does not have issues with
        # seprator in windows
        #
        template = template.replace(os.sep, '/')
        logger.debug("Loading template [%s] and preprocessing" % template)
        try:
            (contents,
                filename,
                    date) = super(HydeLoader, self).get_source(
                                        environment, template)
        except UnicodeDecodeError:
            HydeException.reraise(
                "Unicode error when processing %s" % template, sys.exc_info())
        except TemplateError, exc:
            HydeException.reraise('Error when processing %s: %s' % (
                template,
                unicode(exc)
            ), sys.exc_info())

        if self.preprocessor:
            resource = self.site.content.resource_from_relative_path(template)
            if resource:
                contents = self.preprocessor(resource, contents) or contents
        return (contents, filename, date)


# pylint: disable-msg=W0104,E0602,W0613,R0201
class Jinja2Template(Template):
    """
    The Jinja2 Template implementation
    """

    def __init__(self, sitepath):
        super(Jinja2Template, self).__init__(sitepath)

    def configure(self, site, engine=None):
        """
        Uses the site object to initialize the jinja environment.
        """
        self.site = site
        self.engine = engine
        self.preprocessor = (engine.preprocessor
                            if hasattr(engine, 'preprocessor') else None)

        self.loader = HydeLoader(self.sitepath, site, self.preprocessor)

        default_extensions = [
                IncludeText,
                Spaceless,
                Asciidoc,
                Markdown,
                restructuredText,
                Syntax,
                Reference,
                Refer,
                YamlVar,
                'jinja2.ext.do',
                'jinja2.ext.loopcontrols',
                'jinja2.ext.with_'
        ]

        defaults = {
            'line_statement_prefix': '$$$',
            'trim_blocks': True,
        }

        settings = dict()
        settings.update(defaults)
        settings['extensions'] = list()
        settings['extensions'].extend(default_extensions)
        settings['filters'] = {}

        conf = {}

        try:
            conf = attrgetter('config.jinja2')(site).to_dict()
        except AttributeError:
            pass

        settings.update(
            dict([(key, conf[key]) for key in defaults if key in conf]))

        extensions = conf.get('extensions', [])
        if isinstance(extensions, list):
            settings['extensions'].extend(extensions)
        else:
            settings['extensions'].append(extensions)

        filters = conf.get('filters', {})
        if isinstance(filters, dict):
            for name, value in filters.items():
                parts = value.split('.')
                module_name = '.'.join(parts[:-1])
                function_name = parts[-1]
                module = __import__(module_name, fromlist=[function_name])
                settings['filters'][name] = getattr(module, function_name)

        self.env = Environment(
                    loader=self.loader,
                    undefined=SilentUndefined,
                    line_statement_prefix=settings['line_statement_prefix'],
                    trim_blocks=True,
                    bytecode_cache=FileSystemBytecodeCache(),
                    extensions=settings['extensions'])
        self.env.globals['media_url'] = media_url
        self.env.globals['content_url'] = content_url
        self.env.globals['full_url'] = full_url
        self.env.globals['engine'] = engine
        self.env.globals['deps'] = {}
        self.env.filters['urlencode'] = urlencode
        self.env.filters['urldecode'] = urldecode
        self.env.filters['asciidoc'] = asciidoc
        self.env.filters['markdown'] = markdown
        self.env.filters['restructuredtext'] = restructuredtext
        self.env.filters['syntax'] = syntax
        self.env.filters['date_format'] = date_format
        self.env.filters['xmldatetime'] = xmldatetime
        self.env.filters['islice'] = islice
        self.env.filters['top'] = top
        self.env.filters.update(settings['filters'])

        config = {}
        if hasattr(site, 'config'):
            config = site.config

        self.env.extend(config=config)

        try:
            from typogrify.templatetags import jinja_filters
        except ImportError:
            jinja_filters = False

        if jinja_filters:
            jinja_filters.register(self.env)

    def clear_caches(self):
        """
        Clear all caches to prepare for regeneration
        """
        if self.env.bytecode_cache:
            self.env.bytecode_cache.clear()


    def get_dependencies(self, path):
        """
        Finds dependencies hierarchically based on the included
        files.
        """
        text = self.env.loader.get_source(self.env, path)[0]
        from jinja2.meta import find_referenced_templates
        try:
            ast = self.env.parse(text)
        except Exception, e:
            HydeException.reraise(
                "Error processing %s: \n%s" % (path, unicode(e)),
                sys.exc_info())

        tpls = find_referenced_templates(ast)
        deps = list(self.env.globals['deps'].get('path', []))
        for dep in tpls:
            deps.append(dep)
            if dep:
                deps.extend(self.get_dependencies(dep))
        return list(set(deps))

    @property
    def exception_class(self):
        """
        The exception to throw. Used by plugins.
        """
        return TemplateError

    @property
    def patterns(self):
        """
        The pattern for matching selected template statements.
        """
        return {
           "block_open": '\s*\{\%\s*block\s*([^\s]+)\s*\%\}',
           "block_close": '\s*\{\%\s*endblock\s*([^\s]*)\s*\%\}',
           "include": '\s*\{\%\s*include\s*(?:\'|\")(.+?\.[^.]*)(?:\'|\")\s*\%\}',
           "extends": '\s*\{\%\s*extends\s*(?:\'|\")(.+?\.[^.]*)(?:\'|\")\s*\%\}'
        }

    def get_include_statement(self, path_to_include):
        """
        Returns an include statement for the current template,
        given the path to include.
        """
        return '{%% include \'%s\' %%}' % path_to_include

    def get_extends_statement(self, path_to_extend):
        """
        Returns an extends statement for the current template,
        given the path to extend.
        """
        return '{%% extends \'%s\' %%}' % path_to_extend

    def get_open_tag(self, tag, params):
        """
        Returns an open tag statement.
        """
        return '{%% %s %s %%}' % (tag, params)

    def get_close_tag(self, tag, params):
        """
        Returns an open tag statement.
        """
        return '{%% end%s %%}' % tag

    def get_content_url_statement(self, url):
        """
        Returns the content url statement.
        """
        return '{{ content_url(\'%s\') }}' % url

    def get_media_url_statement(self, url):
        """
        Returns the media url statement.
        """
        return '{{ media_url(\'%s\') }}' % url

    def get_full_url_statement(self, url):
        """
        Returns the full url statement.
        """
        return '{{ full_url(\'%s\') }}' % url

    def render_resource(self, resource, context):
        """
        Renders the given resource using the context
        """
        try:
            template = self.env.get_template(resource.relative_path)
            out = template.render(context)
        except:
            raise
        return out

    def render(self, text, context):
        """
        Renders the given text using the context
        """
        template = self.env.from_string(text)
        return template.render(context)

########NEW FILE########
__FILENAME__ = generator
# -*- coding: utf-8 -*-
"""
The generator class and related utility functions.
"""

from commando.util import getLoggerWithNullHandler
from fswrap import File, Folder
from hyde.exceptions import HydeException
from hyde.model import Context, Dependents
from hyde.plugin import Plugin
from hyde.template import Template
from hyde.site import Resource

from contextlib import contextmanager
from datetime import datetime
from shutil import copymode
import sys

logger = getLoggerWithNullHandler('hyde.engine')


class Generator(object):
    """
    Generates output from a node or resource.
    """

    def __init__(self, site):
        super(Generator, self).__init__()
        self.site = site
        self.generated_once = False
        self.deps = Dependents(site.sitepath)
        self.waiting_deps = {}
        self.create_context()
        self.template = None
        Plugin.load_all(site)

        self.events = Plugin.get_proxy(self.site)

    def create_context(self):
        site = self.site
        self.__context__ = dict(site=site)
        if hasattr(site.config, 'context'):
            site.context = Context.load(site.sitepath, site.config.context)
            self.__context__.update(site.context)


    @contextmanager
    def context_for_resource(self, resource):
        """
        Context manager that intializes the context for a given
        resource and rolls it back after the resource is processed.
        """
        self.__context__.update(
            resource=resource,
            node=resource.node,
            time_now=datetime.now())
        yield self.__context__
        self.__context__.update(resource=None, node=None)

    def context_for_path(self, path):
        resource = self.site.resource_from_path(path)
        if not resource:
            return {}
        ctx = self.__context__.copy
        ctx.resource = resource
        return ctx

    def load_template_if_needed(self):
        """
        Loads and configures the template environment from the site
        configuration if it's not done already.
        """

        class GeneratorProxy(object):
            """
            An interface to templates and plugins for
            providing restricted access to the methods.
            """

            def __init__(self, preprocessor=None, postprocessor=None, context_for_path=None):
                self.preprocessor = preprocessor
                self.postprocessor = postprocessor
                self.context_for_path = context_for_path

        if not self.template:
            logger.info("Generating site at [%s]" % self.site.sitepath)
            self.template = Template.find_template(self.site)
            logger.debug("Using [%s] as the template",
                            self.template.__class__.__name__)

            logger.info("Configuring the template environment")
            self.template.configure(self.site,
                        engine=GeneratorProxy(
                            context_for_path=self.context_for_path,
                            preprocessor=self.events.begin_text_resource,
                            postprocessor=self.events.text_resource_complete))
            self.events.template_loaded(self.template)

    def initialize(self):
        """
        Start Generation. Perform setup tasks and inform plugins.
        """
        logger.debug("Begin Generation")
        self.events.begin_generation()

    def load_site_if_needed(self):
        """
        Checks if the site requires a reload and loads if
        necessary.
        """
        self.site.reload_if_needed()

    def finalize(self):
        """
        Generation complete. Inform plugins and cleanup.
        """
        logger.debug("Generation Complete")
        self.events.generation_complete()

    def get_dependencies(self, resource):
        """
        Gets the dependencies for a given resource.
        """

        rel_path = resource.relative_path
        deps = self.deps[rel_path] if rel_path in self.deps \
                    else self.update_deps(resource)
        return deps

    def update_deps(self, resource):
        """
        Updates the dependencies for the given resource.
        """
        if not resource.source_file.is_text:
            return []
        rel_path = resource.relative_path
        self.waiting_deps[rel_path] = []
        deps = []
        if hasattr(resource, 'depends'):
            user_deps = resource.depends
            for dep in user_deps:
                deps.append(dep)
                dep_res = self.site.content.resource_from_relative_path(dep)
                if dep_res:
                    if dep_res.relative_path in self.waiting_deps.keys():
                        self.waiting_deps[dep_res.relative_path].append(rel_path)
                    else:
                        deps.extend(self.get_dependencies(dep_res))
        if resource.uses_template:
            deps.extend(self.template.get_dependencies(rel_path))
        deps = list(set(deps))
        if None in deps:
            deps.remove(None)
        self.deps[rel_path] = deps
        for path in self.waiting_deps[rel_path]:
            self.deps[path].extend(deps)
        return deps

    def has_resource_changed(self, resource):
        """
        Checks if the given resource has changed since the
        last generation.
        """
        logger.debug("Checking for changes in %s" % resource)
        self.load_template_if_needed()
        self.load_site_if_needed()

        target = File(self.site.config.deploy_root_path.child(
                                resource.relative_deploy_path))
        if not target.exists or target.older_than(resource.source_file):
            logger.debug("Found changes in %s" % resource)
            return True
        if resource.source_file.is_binary:
            logger.debug("No Changes found in %s" % resource)
            return False
        if self.site.config.needs_refresh() or \
           not target.has_changed_since(self.site.config.last_modified):
            logger.debug("Site configuration changed")
            return True

        deps = self.get_dependencies(resource)
        if not deps or None in deps:
            logger.debug("No changes found in %s" % resource)
            return False
        content = self.site.content.source_folder
        layout = Folder(self.site.sitepath).child_folder('layout')
        logger.debug("Checking for changes in dependents:%s" % deps)
        for dep in deps:
            if not dep:
                return True
            source = File(content.child(dep))
            if not source.exists:
                source = File(layout.child(dep))
            if not source.exists:
                return True
            if target.older_than(source):
                return True
        logger.debug("No changes found in %s" % resource)
        return False

    def generate_all(self, incremental=False):
        """
        Generates the entire website
        """
        logger.info("Reading site contents")
        self.load_template_if_needed()
        self.template.clear_caches()
        self.initialize()
        self.load_site_if_needed()
        self.events.begin_site()
        logger.info("Generating site to [%s]" %
                        self.site.config.deploy_root_path)
        self.__generate_node__(self.site.content, incremental)
        self.events.site_complete()
        self.finalize()
        self.generated_once = True

    def generate_node_at_path(self, node_path=None, incremental=False):
        """
        Generates a single node. If node_path is non-existent or empty,
        generates the entire site.
        """
        if not self.generated_once and not incremental:
            return self.generate_all()
        self.load_template_if_needed()
        self.load_site_if_needed()
        node = None
        if node_path:
            node = self.site.content.node_from_path(node_path)
        self.generate_node(node, incremental)

    @contextmanager
    def events_for(self, obj):
        if not self.generated_once:
            self.events.begin_site()
            if isinstance(obj, Resource):
                self.events.begin_node(obj.node)
        yield
        if not self.generated_once:
            if isinstance(obj, Resource):
                self.events.node_complete(obj.node)
            self.events.site_complete()
            self.generated_once = True

    def generate_node(self, node=None, incremental=False):
        """
        Generates the given node. If node is invalid, empty or
        non-existent, generates the entire website.
        """
        if not node or not self.generated_once and not incremental:
            return self.generate_all()

        self.load_template_if_needed()
        self.initialize()
        self.load_site_if_needed()

        try:
            with self.events_for(node):
                self.__generate_node__(node, incremental)
            self.finalize()
        except HydeException:
            self.generate_all()

    def generate_resource_at_path(self,
                    resource_path=None,
                    incremental=False):
        """
        Generates a single resource. If resource_path is non-existent or empty,
        generates the entire website.
        """
        if not self.generated_once and not incremental:
            return self.generate_all()

        self.load_template_if_needed()
        self.load_site_if_needed()
        resource = None
        if resource_path:
            resource = self.site.content.resource_from_path(resource_path)
        self.generate_resource(resource, incremental)

    def generate_resource(self, resource=None, incremental=False):
        """
        Generates the given resource. If resource is invalid, empty or
        non-existent, generates the entire website.
        """
        if not resource or not self.generated_once and not incremental:
            return self.generate_all()

        self.load_template_if_needed()
        self.initialize()
        self.load_site_if_needed()

        try:
            with self.events_for(resource):
                self.__generate_resource__(resource, incremental)
        except HydeException:
            self.generate_all()

    def refresh_config(self):
        if self.site.config.needs_refresh():
            logger.debug("Refreshing configuration and context")
            self.site.refresh_config()
            self.create_context()

    def __generate_node__(self, node, incremental=False):
        self.refresh_config()
        for node in node.walk():
            logger.debug("Generating Node [%s]", node)
            self.events.begin_node(node)
            for resource in node.resources:
                self.__generate_resource__(resource, incremental)
            self.events.node_complete(node)


    def __generate_resource__(self, resource, incremental=False):
        self.refresh_config()
        if not resource.is_processable:
            logger.debug("Skipping [%s]", resource)
            return
        if incremental and not self.has_resource_changed(resource):
            logger.debug("No changes found. Skipping resource [%s]", resource)
            return
        logger.debug("Processing [%s]", resource)
        with self.context_for_resource(resource) as context:
            target = File(self.site.config.deploy_root_path.child(
                                    resource.relative_deploy_path))
            target.parent.make()
            if resource.simple_copy:
                logger.debug("Simply Copying [%s]", resource)
                resource.source_file.copy_to(target)
            elif resource.source_file.is_text:
                self.update_deps(resource)
                if resource.uses_template:
                    logger.debug("Rendering [%s]", resource)
                    try:
                        text = self.template.render_resource(resource,
                                        context)
                    except Exception, e:
                        HydeException.reraise("Error occurred when"
                            " processing template: [%s]: %s" %
                            (resource, repr(e)),
                            sys.exc_info()
                        )
                else:
                    text = resource.source_file.read_all()
                    text = self.events.begin_text_resource(resource, text) or text

                text = self.events.text_resource_complete(
                                        resource, text) or text
                target.write(text)
                copymode(resource.source_file.path, target.path)
            else:
                logger.debug("Copying binary file [%s]", resource)
                self.events.begin_binary_resource(resource)
                resource.source_file.copy_to(target)
                self.events.binary_resource_complete(resource)

########NEW FILE########
__FILENAME__ = layout
# -*- coding: utf-8 -*-
"""
Classes, functions and utilties related to hyde layouts
"""
import os

from fswrap import File, Folder

HYDE_DATA = "HYDE_DATA"
LAYOUTS = "layouts"


class Layout(object):
    """
    Represents a layout package
    """

    @staticmethod
    def find_layout(layout_name='basic'):
        """
        Find the layout with a given name.
        Search order:
        1. env(HYDE_DATA)
        2. <hyde script path>/layouts/
        """
        layout_folder = None
        if HYDE_DATA in os.environ:
            layout_folder = Layout._get_layout_folder(
                                os.environ[HYDE_DATA], layout_name)
        if not layout_folder:
            layout_folder = Layout._get_layout_folder(
                                File(__file__).parent, layout_name)
        return layout_folder

    @staticmethod
    def _get_layout_folder(root, layout_name='basic'):
        """
        Finds the layout folder from the given root folder.
        If it does not exist, return None
        """
        layouts_folder = Folder(unicode(root)).child_folder(LAYOUTS)
        layout_folder = layouts_folder.child_folder(layout_name)
        return layout_folder if layout_folder.exists else None

########NEW FILE########
__FILENAME__ = rst_directive
# -*- coding: utf-8 -*-
"""
    The Pygments reStructuredText directive
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This fragment is a Docutils_ 0.5 directive that renders source code
    (to HTML only, currently) via Pygments.

    To use it, adjust the options below and copy the code into a module
    that you import on initialization.  The code then automatically
    registers a ``sourcecode`` directive that you can use instead of
    normal code blocks like this::

        .. sourcecode:: python

            My code goes here.

    If you want to have different code styles, e.g. one with line numbers
    and one without, add formatters with their names in the VARIANTS dict
    below.  You can invoke them instead of the DEFAULT one by using a
    directive option::

        .. sourcecode:: python
            :linenos:

            My code goes here.

    Look at the `directive documentation`_ to get all the gory details.

    .. _Docutils: http://docutils.sf.net/
    .. _directive documentation:
       http://docutils.sourceforge.net/docs/howto/rst-directives.html

    :copyright: Copyright 2006-2011 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Options
# ~~~~~~~

# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False

from pygments.formatters import HtmlFormatter

# The default formatter
DEFAULT = HtmlFormatter(noclasses=INLINESTYLES)

# Add name -> formatter pairs for every variant you want to use
VARIANTS = {
    'linenos': HtmlFormatter(noclasses=INLINESTYLES, linenos=True),
}


from docutils import nodes
from docutils.parsers.rst import directives, Directive

from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer

class Pygments(Directive):
    """ Source code syntax hightlighting.
    """
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = dict([(key, directives.flag) for key in VARIANTS])
    has_content = True

    def run(self):
        self.assert_has_content()
        try:
            lexer = get_lexer_by_name(self.arguments[0])
        except ValueError:
            # no lexer found - use the text one instead of an exception
            lexer = TextLexer()
        # take an arbitrary option if more than one is given
        formatter = self.options and VARIANTS[self.options.keys()[0]] or DEFAULT
        parsed = highlight(u'\n'.join(self.content), lexer, formatter)
        return [nodes.raw('', parsed, format='html')]

directives.register_directive('sourcecode', Pygments)

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The hyde executable
"""
from hyde.engine import Engine

def main():
    """Main"""
    Engine().run()

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
"""
Contains data structures and utilities for hyde.
"""
import codecs
import yaml
from datetime import datetime
from UserDict import IterableUserDict

from commando.util import getLoggerWithNullHandler
from fswrap import File, Folder

logger = getLoggerWithNullHandler('hyde.engine')

SEQS = (tuple, list, set, frozenset)

def make_expando(primitive):
    """
    Creates an expando object, a sequence of expando objects or just
    returns the primitive based on the primitive's type.
    """
    if isinstance(primitive, dict):
        return Expando(primitive)
    elif isinstance(primitive, SEQS):
        seq = type(primitive)
        return seq(make_expando(attr) for attr in primitive)
    else:
        return primitive


class Expando(object):
    """
    A generic expando class that creates attributes from
    the passed in dictionary.
    """

    def __init__(self, d):
        super(Expando, self).__init__()
        self.update(d)

    def __iter__(self):
        """
        Returns an iterator for all the items in the
        dictionary as key value pairs.
        """
        return self.__dict__.iteritems()

    def update(self, d):
        """
        Updates the expando with a new dictionary
        """
        d = d or {}
        if isinstance(d, dict):
            for key, value in d.items():
                self.set_expando(key, value)
        elif isinstance(d, Expando):
            self.update(d.to_dict())

    def set_expando(self, key, value):
        """
        Sets the expando attribute after
        transforming the value.
        """
        setattr(self, unicode(key).encode('utf-8'), make_expando(value))


    def __repr__(self):
        return unicode(self.to_dict())

    def to_dict(self):
        """
        Reverse transform an expando to dict
        """
        result = {}
        d = self.__dict__
        for k, v in d.items():
            if isinstance(v, Expando):
                result[k] = v.to_dict()
            elif isinstance(v, SEQS):
                seq = type(v)
                result[k] = seq(item.to_dict()
                    if isinstance(item, Expando)
                    else item for item in v
                )
            else:
                result[k] = v
        return result

    def get(self, key, default=None):
        """
        Dict like get helper method
        """
        return self.__dict__.get(key, default)


class Context(object):
    """
    Wraps the context related functions and utilities.
    """

    @staticmethod
    def load(sitepath, ctx):
        """
        Load context from config data and providers.
        """
        context = {}
        try:
            context.update(ctx.data.__dict__)
        except AttributeError:
            # No context data found
            pass

        providers = {}
        try:
            providers.update(ctx.providers.__dict__)
        except AttributeError:
            # No providers found
            pass

        for provider_name, resource_name in providers.items():
            res = File(Folder(sitepath).child(resource_name))
            if res.exists:
                data = make_expando(yaml.load(res.read_all()))
                context[provider_name] = data

        return context

class Dependents(IterableUserDict):
    """
    Represents the dependency graph for hyde.
    """

    def __init__(self, sitepath, depends_file_name='.hyde_deps'):
        self.sitepath = Folder(sitepath)
        self.deps_file = File(self.sitepath.child(depends_file_name))
        self.data = {}
        if self.deps_file.exists:
            self.data = yaml.load(self.deps_file.read_all())
        import atexit
        atexit.register(self.save)

    def save(self):
        """
        Saves the dependency graph (just a dict for now).
        """
        if self.deps_file.parent.exists:
            self.deps_file.write(yaml.dump(self.data))

def _expand_path(sitepath, path):
    child = sitepath.child_folder(path)
    return Folder(child.fully_expanded_path)

class Config(Expando):
    """
    Represents the hyde configuration file
    """

    def __init__(self, sitepath, config_file=None, config_dict=None):
        self.default_config = dict(
            mode='production',
            simple_copy = [],
            content_root='content',
            deploy_root='deploy',
            media_root='media',
            layout_root='layout',
            media_url='/media',
            base_url="/",
            encode_safe=None,
            not_found='404.html',
            plugins = [],
            ignore = [ "*~", "*.bak", ".hg", ".git", ".svn"],
            meta = {
                "nodemeta": 'meta.yaml'
            }
        )
        self.config_file = config_file
        self.config_dict = config_dict
        self.load_time = datetime.min
        self.config_files = []
        self.sitepath = Folder(sitepath)
        super(Config, self).__init__(self.load())

    @property
    def last_modified(self):
        return max((conf.last_modified for conf in self.config_files))

    def needs_refresh(self):
        if not self.config_files:
            return True
        return any((conf.has_changed_since(self.load_time)
                        for conf in self.config_files))

    def load(self):
        conf = dict(**self.default_config)
        conf.update(self.read_config(self.config_file))
        if self.config_dict:
            conf.update(self.config_dict)
        return conf

    def reload(self):
        if not self.config_file:
            return
        self.update(self.load())


    def read_config(self, config_file):
        """
        Reads the configuration file and updates this
        object while allowing for inherited configurations.
        """
        conf_file = self.sitepath.child(
                            config_file if
                                    config_file else 'site.yaml')
        conf = {}
        if File(conf_file).exists:
            self.config_files.append(File(conf_file))
            logger.info("Reading site configuration from [%s]", conf_file)
            with codecs.open(conf_file, 'r', 'utf-8') as stream:
                conf = yaml.load(stream)
                if 'extends' in conf:
                    parent = self.read_config(conf['extends'])
                    parent.update(conf)
                    conf = parent
        self.load_time = datetime.now()
        return conf


    @property
    def deploy_root_path(self):
        """
        Derives the deploy root path from the site path
        """
        return _expand_path(self.sitepath, self.deploy_root)

    @property
    def content_root_path(self):
        """
        Derives the content root path from the site path
        """
        return _expand_path(self.sitepath, self.content_root)

    @property
    def media_root_path(self):
        """
        Derives the media root path from the content path
        """
        path = Folder(self.content_root).child(self.media_root)
        return _expand_path(self.sitepath, path)

    @property
    def layout_root_path(self):
        """
        Derives the layout root path from the site path
        """
        return _expand_path(self.sitepath, self.layout_root)

########NEW FILE########
__FILENAME__ = plugin
# -*- coding: utf-8 -*-
"""
Contains definition for a plugin protocol and other utiltities.
"""
from hyde.exceptions import HydeException
from hyde.util import first_match, discover_executable
from hyde.model import Expando

import abc
from functools import partial
import fnmatch
import os
import re
import subprocess
import sys
import traceback

from commando.util import getLoggerWithNullHandler, load_python_object
from fswrap import File

logger = getLoggerWithNullHandler('hyde.engine')

# Plugins have been reorganized. Map old plugin paths to new.
PLUGINS_OLD_AND_NEW = {
    "hyde.ext.plugins.less.LessCSSPlugin" : "hyde.ext.plugins.css.LessCSSPlugin",
    "hyde.ext.plugins.stylus.StylusPlugin" : "hyde.ext.plugins.css.StylusPlugin",
    "hyde.ext.plugins.jpegoptim.JPEGOptimPlugin" : "hyde.ext.plugins.images.JPEGOptimPlugin",
    "hyde.ext.plugins.optipng.OptiPNGPlugin" : "hyde.ext.plugins.images.OptiPNGPlugin",
    "hyde.ext.plugins.jpegtran.JPEGTranPlugin" : "hyde.ext.plugins.images.JPEGTranPlugin",
    "hyde.ext.plugins.uglify.UglifyPlugin": "hyde.ext.plugins.js.UglifyPlugin",
    "hyde.ext.plugins.requirejs.RequireJSPlugin": "hyde.ext.plugins.js.RequireJSPlugin",
    "hyde.ext.plugins.coffee.CoffeePlugin": "hyde.ext.plugins.js.CoffeePlugin",
    "hyde.ext.plugins.sorter.SorterPlugin": "hyde.ext.plugins.meta.SorterPlugin",
    "hyde.ext.plugins.grouper.GrouperPlugin": "hyde.ext.plugins.meta.GrouperPlugin",
    "hyde.ext.plugins.tagger.TaggerPlugin": "hyde.ext.plugins.meta.TaggerPlugin",
    "hyde.ext.plugins.auto_extend.AutoExtendPlugin": "hyde.ext.plugins.meta.AutoExtendPlugin",
    "hyde.ext.plugins.folders.FlattenerPlugin": "hyde.ext.plugins.structure.FlattenerPlugin",
    "hyde.ext.plugins.combine.CombinePlugin": "hyde.ext.plugins.structure.CombinePlugin",
    "hyde.ext.plugins.paginator.PaginatorPlugin": "hyde.ext.plugins.structure.PaginatorPlugin",
    "hyde.ext.plugins.blockdown.BlockdownPlugin": "hyde.ext.plugins.text.BlockdownPlugin",
    "hyde.ext.plugins.markings.MarkingsPlugin": "hyde.ext.plugins.text.MarkingsPlugin",
    "hyde.ext.plugins.markings.ReferencePlugin": "hyde.ext.plugins.text.ReferencePlugin",
    "hyde.ext.plugins.syntext.SyntextPlugin": "hyde.ext.plugins.text.SyntextPlugin",
    "hyde.ext.plugins.textlinks.TextlinksPlugin": "hyde.ext.plugins.text.TextlinksPlugin",
    "hyde.ext.plugins.git.GitDatesPlugin": "hyde.ext.plugins.vcs.GitDatesPlugin"
}

class PluginProxy(object):
    """
    A proxy class to raise events in registered  plugins
    """

    def __init__(self, site):
        super(PluginProxy, self).__init__()
        self.site = site

    def __getattr__(self, method_name):
        if hasattr(Plugin, method_name):
            def __call_plugins__(*args):
                res = None
                if self.site.plugins:
                    for plugin in self.site.plugins:
                        if hasattr(plugin, method_name):
                            checker = getattr(plugin, 'should_call__' + method_name)
                            if checker(*args):
                                function = getattr(plugin, method_name)
                                try:
                                    res = function(*args)
                                except:
                                    HydeException.reraise(
                                        'Error occured when calling %s' %
                                        plugin.plugin_name, sys.exc_info())
                                targs = list(args)
                                if len(targs):
                                    last = targs.pop()
                                    res = res if res else last
                                    targs.append(res)
                                    args = tuple(targs)
                return res

            return __call_plugins__
        raise HydeException(
                "Unknown plugin method [%s] called." % method_name)

class Plugin(object):
    """
    The plugin protocol
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, site):
        super(Plugin, self).__init__()
        self.site = site
        self.logger = getLoggerWithNullHandler(
                            'hyde.engine.%s' % self.__class__.__name__)
        self.template = None


    def template_loaded(self, template):
        """
        Called when the template for the site has been identified.

        Handles the template loaded event to keep
        a reference to the template object.
        """
        self.template = template

    def __getattribute__(self, name):
        """
        Syntactic sugar for template methods
        """
        result = None
        if name.startswith('t_') and self.template:
            attr = name[2:]
            if hasattr(self.template, attr):
                result = self.template[attr]
            elif attr.endswith('_close_tag'):
                tag = attr.replace('_close_tag', '')
                result = partial(self.template.get_close_tag, tag)
            elif attr.endswith('_open_tag'):
                tag = attr.replace('_open_tag', '')
                result = partial(self.template.get_open_tag, tag)
        elif name.startswith('should_call__'):
            (_, _, method) = name.rpartition('__')
            if (method in ('begin_text_resource', 'text_resource_complete',
                            'begin_binary_resource', 'binary_resource_complete')):
                result = self._file_filter
            elif (method in ('begin_node', 'node_complete')):
                result = self._dir_filter
            else:
                def always_true(*args, **kwargs):
                    return True
                result = always_true

        return  result if result else super(Plugin, self).__getattribute__(name)

    @property
    def settings(self):
        """
        The settings for this plugin the site config.
        """

        opts = Expando({})
        try:
            opts = getattr(self.site.config, self.plugin_name)
        except AttributeError:
            pass
        return opts


    @property
    def plugin_name(self):
        """
        The name of the plugin. Makes an intelligent guess.

        This is used to lookup the settings for the plugin.
        """

        return self.__class__.__name__.replace('Plugin', '').lower()

    def begin_generation(self):
        """
        Called when generation is about to take place.
        """
        pass

    def begin_site(self):
        """
        Called when the site is loaded completely. This implies that all the
        nodes and resources have been identified and are accessible in the
        site variable.
        """
        pass

    def begin_node(self, node):
        """
        Called when a node is about to be processed for generation.
        This method is called only when the entire node is generated.
        """
        pass

    def _file_filter(self, resource, *args, **kwargs):
        """
        Returns True if the resource path matches the filter property in
        plugin settings.
        """

        if not self._dir_filter(resource.node, *args, **kwargs):
            return False

        try:
            filters = self.settings.include_file_pattern
            if not isinstance(filters, list):
                filters = [filters]
        except AttributeError:
            filters = None
        result = any(fnmatch.fnmatch(resource.path, f)
                                        for f in filters) if filters else True
        return result

    def _dir_filter(self, node, *args, **kwargs):
        """
        Returns True if the node path is a descendant of the include_paths property in
        plugin settings.
        """
        try:
            node_filters = self.settings.include_paths
            if not isinstance(node_filters, list):
                node_filters = [node_filters]
            node_filters = [self.site.content.node_from_relative_path(f)
                                        for f in node_filters]
        except AttributeError:
            node_filters = None
        result = any(node.source == f.source or
                        node.source.is_descendant_of(f.source)
                                        for f in node_filters if f) \
                                        if node_filters else True
        return result

    def begin_text_resource(self, resource, text):
        """
        Called when a text resource is about to be processed for generation.
        The `text` parameter contains the resource text at this point
        in its lifecycle. It is the text that has been loaded and any
        plugins that are higher in the order may have tampered with it.
        But the text has not been processed by the template yet. Note that
        the source file associated with the text resource may not be modifed
        by any plugins.

        If this function returns a value, it is used as the text for further
        processing.
        """
        return text

    def begin_binary_resource(self, resource):
        """
        Called when a binary resource is about to be processed for generation.

        Plugins are free to modify the contents of the file.
        """
        pass

    def text_resource_complete(self, resource, text):
        """
        Called when a resource has been processed by the template.
        The `text` parameter contains the resource text at this point
        in its lifecycle. It is the text that has been processed by the
        template and any plugins that are higher in the order may have
        tampered with it. Note that the source file associated with the
        text resource may not be modifed by any plugins.

        If this function returns a value, it is used as the text for further
        processing.
        """
        return text

    def binary_resource_complete(self, resource):
        """
        Called when a binary resource has already been processed.

        Plugins are free to modify the contents of the file.
        """
        pass

    def node_complete(self, node):
        """
        Called when all the resources in the node have been processed.
        This method is called only when the entire node is generated.
        """
        pass

    def site_complete(self):
        """
        Called when the entire site has been processed. This method is called
        only when the entire site is generated.
        """
        pass

    def generation_complete(self):
        """
        Called when generation is completed.
        """
        pass

    @staticmethod
    def load_all(site):
        """
        Loads plugins based on the configuration. Assigns the plugins to
        'site.plugins'
        """
        def load_plugin(name):
            plugin_name = PLUGINS_OLD_AND_NEW.get(name, name)
            return load_python_object(plugin_name)(site)

        site.plugins = [load_plugin(name)
                            for name in site.config.plugins]

    @staticmethod
    def get_proxy(site):
        """
        Returns a new instance of the Plugin proxy.
        """
        return PluginProxy(site)

class CLTransformer(Plugin):
    """
    Handy class for plugins that simply call a command line app to
    transform resources.
    """
    @property
    def defaults(self):
        """
        Default command line options. Can be overridden
        by specifying them in config.
        """

        return {}

    @property
    def executable_name(self):
        """
        The executable name for the plugin. This can be overridden in the
        config. If a configuration option is not provided, this is used
        to guess the complete path of the executable.
        """
        return self.plugin_name

    @property
    def executable_not_found_message(self):
        """
        Message to be displayed if the command line application
        is not found.
        """

        return ("%(name)s executable path not configured properly. "
        "This plugin expects `%(name)s.app` to point "
        "to the full path of the `%(exec)s` executable." %
        {
            "name":self.plugin_name, "exec": self.executable_name
        })

    @property
    def app(self):
        """
        Gets the application path from the site configuration.

        If the path is not configured, attempts to guess the path
        from the sytem path environment variable.
        """

        try:
            app_path = getattr(self.settings, 'app')
        except AttributeError:
            app_path = self.executable_name

        # Honour the PATH environment variable.
        if app_path is not None and not os.path.isabs(app_path):
            app_path = discover_executable(app_path, self.site.sitepath)

        if app_path is None:
            raise HydeException(self.executable_not_found_message)
        app = File(app_path)

        if not app.exists:
            raise HydeException(self.executable_not_found_message)

        return app

    def option_prefix(self, option):
        """
        Return the prefix for the given option.

        Defaults to --.
        """
        return "--"

    def process_args(self, supported):
        """
        Given a list of supported arguments, consutructs an argument
        list that could be passed on to the call_app function.
        """
        args = {}
        args.update(self.defaults)
        try:
            args.update(self.settings.args.to_dict())
        except AttributeError:
            pass

        params = []
        for option in supported:
            if isinstance(option, tuple):
                (descriptive, short) = option
            else:
                descriptive = short = option

            options = [descriptive.rstrip("="), short.rstrip("=")]
            match = first_match(lambda arg: arg in options, args)
            if match:
                val = args[match]
                param = "%s%s" % (self.option_prefix(descriptive),
                                        descriptive)
                if descriptive.endswith("="):
                    param += val
                    val = None
                params.append(param)
                if val:
                    params.append(val)
        return params

    def call_app(self, args):
        """
        Calls the application with the given command line parameters.
        """
        try:
            self.logger.debug(
                "Calling executable [%s] with arguments %s" %
                    (args[0], unicode(args[1:])))
            return subprocess.check_output(args)
        except subprocess.CalledProcessError, error:
            self.logger.error(error.output)
            raise

class TextyPlugin(Plugin):
    """
    Base class for text preprocessing plugins.

    Plugins that desire to provide syntactic sugar for
    commonly used hyde functions for various templates
    can inherit from this class.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, site):
        super(TextyPlugin, self).__init__(site)
        self.open_pattern = self.default_open_pattern
        self.close_pattern = self.default_close_pattern
        self.template = None
        config = getattr(site.config, self.plugin_name, None)

        if config and hasattr(config, 'open_pattern'):
            self.open_pattern = config.open_pattern

        if self.close_pattern and config and hasattr(config, 'close_pattern'):
            self.close_pattern = config.close_pattern

    @property
    def plugin_name(self):
        """
        The name of the plugin. Makes an intelligent guess.
        """
        return self.__class__.__name__.replace('Plugin', '').lower()

    @abc.abstractproperty
    def tag_name(self):
        """
        The tag that this plugin tries add syntactic sugar for.
        """
        return self.plugin_name

    @abc.abstractproperty
    def default_open_pattern(self):
        """
        The default pattern for opening the tag.
        """
        return None

    @abc.abstractproperty
    def default_close_pattern(self):
        """
        The default pattern for closing the tag.
        """
        return None

    def get_params(self, match, start=True):
        """
        Default implementation for getting template args.
        """
        return match.groups(1)[0] if match.lastindex else ''

    @abc.abstractmethod
    def text_to_tag(self, match, start=True):
        """
        Replaces the matched text with tag statement
        given by the template.
        """
        params = self.get_params(match, start)
        return (self.template.get_open_tag(self.tag_name, params)
                if start
                else self.template.get_close_tag(self.tag_name, params))

    def begin_text_resource(self, resource, text):
        """
        Replace a text base pattern with a template statement.
        """
        text_open = re.compile(self.open_pattern, re.UNICODE|re.MULTILINE)
        text = text_open.sub(self.text_to_tag, text)
        if self.close_pattern:
            text_close = re.compile(self.close_pattern, re.UNICODE|re.MULTILINE)
            text = text_close.sub(
                    partial(self.text_to_tag, start=False), text)
        return text

########NEW FILE########
__FILENAME__ = publisher
import abc
from operator import attrgetter

from commando.util import getLoggerWithNullHandler, load_python_object

"""
Contains abstract classes and utilities that help publishing a website to a
server.
"""

class Publisher(object):
    """
    The abstract base class for publishers.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, site, settings, message):
        super(Publisher, self).__init__()
        self.logger = getLoggerWithNullHandler(
                            'hyde.engine.%s' % self.__class__.__name__)
        self.site = site
        self.message = message
        self.initialize(settings)

    @abc.abstractmethod
    def initialize(self, settings): pass

    @abc.abstractmethod
    def publish(self):
        if not self.site.config.deploy_root_path.exists:
            raise Exception("Please generate the site first")

    @staticmethod
    def load_publisher(site, publisher, message):
        logger = getLoggerWithNullHandler('hyde.engine.publisher')
        try:
            settings = attrgetter("publisher.%s" % publisher)(site.config)
        except AttributeError:
            settings = False

        if not settings:
            # Find the first configured publisher
            try:
                publisher = site.config.publisher.__dict__.iterkeys().next()
                logger.warning("No default publisher configured. Using: %s" % publisher)
                settings = attrgetter("publisher.%s" % publisher)(site.config)
            except (AttributeError, StopIteration):
                logger.error(
                    "Cannot find the publisher configuration: %s" % publisher)
                raise

        if not hasattr(settings, 'type'):
            logger.error(
                "Publisher type not specified: %s" % publisher)
            raise Exception("Please specify the publisher type in config.")

        pub_class = load_python_object(settings.type)
        return pub_class(site, settings, message)
########NEW FILE########
__FILENAME__ = server
# -*- coding: utf-8 -*-
"""
Contains classes and utilities for serving a site
generated from hyde.
"""
import threading
import urlparse
import urllib
import traceback
from datetime import datetime
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

from hyde.generator import Generator

from fswrap import File, Folder

from commando.util import getLoggerWithNullHandler
logger = getLoggerWithNullHandler('hyde.server')

class HydeRequestHandler(SimpleHTTPRequestHandler):
    """
    Serves files by regenerating the resource (or)
    everything when a request is issued.
    """

    def do_GET(self):
        """
        Identify the requested path. If the query string
        contains `refresh`, regenerat the entire site.
        Otherwise, regenerate only the requested resource
        and serve.
        """
        self.server.request_time = datetime.now()
        logger.debug("Processing request: [%s]" % self.path)
        result = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(result.query)
        if 'refresh' in query or result.query=='refresh':
            self.server.regenerate()
            if 'refresh' in query:
                del query['refresh']
            parts = list(tuple(result))
            parts[4] = urllib.urlencode(query)
            parts = tuple(parts)
            new_url = urlparse.urlunparse(parts)
            logger.info('Redirecting... [%s]' % new_url)
            self.redirect(new_url)
        else:
            SimpleHTTPRequestHandler.do_GET(self)


    def translate_path(self, path):
        """
        Finds the absolute path of the requested file by
        referring to the `site` variable in the server.
        """
        site = self.server.site
        result = urlparse.urlparse(urllib.unquote(self.path).decode('utf-8'))
        logger.debug("Trying to load file based on request: [%s]" % result.path)
        path = result.path.lstrip('/')
        res = None
        if path.strip() == "" or File(path).kind.strip() == "":
            deployed = site.config.deploy_root_path.child(path)
            deployed = Folder.file_or_folder(deployed)
            if isinstance(deployed, Folder):
                node = site.content.node_from_relative_path(path)
                res = node.get_resource('index.html')
            elif hasattr(site.config, 'urlcleaner') and hasattr(site.config.urlcleaner, 'strip_extensions'):
                for ext in site.config.urlcleaner.strip_extensions:
                    res = site.content.resource_from_relative_deploy_path(path + '.' + ext)
                    if res:
                        break
                for ext in site.config.urlcleaner.strip_extensions:
                    new_path = site.config.deploy_root_path.child(path + '.' + ext)
                    if File(new_path).exists:
                        return new_path
        else:
            res = site.content.resource_from_relative_deploy_path(path)

        if not res:
            logger.error("Cannot load file: [%s]" % path)
            return site.config.deploy_root_path.child(path)
        else:
            self.server.generate_resource(res)
        new_path = site.config.deploy_root_path.child(
                    res.relative_deploy_path)
        return new_path

    def do_404(self):
        """
        Sends a 'not found' response.
        """
        site = self.server.site
        if self.path != site.config.not_found:
            self.redirect(site.config.not_found)
        else:
            res = site.content.resource_from_relative_deploy_path(
                    site.config.not_found)

            message = "Requested resource not found"
            if not res:
                logger.error(
                    "Cannot find the 404 template [%s]."
                        % site.config.not_found)
            else:
                f404 = File(self.translate_path(site.config.not_found))
                if f404.exists:
                    message = f404.read_all()
            self.send_response(200, message)

    def redirect(self, path, temporary=True):
        """
        Sends a redirect header with the new location.
        """
        self.send_response(302 if temporary else 301)
        self.send_header('Location', path)
        self.end_headers()


class HydeWebServer(HTTPServer):
    """
    The hyde web server that regenerates the resource, node or site when
    a request is issued.
    """

    def __init__(self, site, address, port):
        self.site = site
        self.site.load()
        self.generator = Generator(self.site)
        self.request_time = datetime.strptime('1-1-1999', '%m-%d-%Y')
        self.regeneration_time = datetime.strptime('1-1-1998', '%m-%d-%Y')
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False
        self.map_extensions()
        HTTPServer.__init__(self, (address, port),
                                            HydeRequestHandler)

    def map_extensions(self):
        """
        Maps extensions specified in the configuration.
        """
        try:
            extensions = self.site.config.server.extensions.to_dict()
        except AttributeError:
            extensions = {}

        for extension, type in extensions.iteritems():
            ext = "." + extension if not extension == 'default' else ''
            HydeRequestHandler.extensions_map[ext] = type

    def regenerate(self):
        """
        Regenerates the entire site.
        """
        try:
            logger.info('Regenerating the entire site')
            self.regeneration_time = datetime.now()
            if self.site.config.needs_refresh():
                self.site.config.reload()
            self.site.load()
            self.generator.generate_all(incremental=False)
        except Exception, exception:
            logger.error('Error occured when regenerating the site [%s]'
                            % exception.message)
            logger.debug(traceback.format_exc())

    def generate_node(self, node):
        """
        Generates the given node.
        """

        deploy = self.site.config.deploy_root_path
        if not deploy.exists:
            return self.regenerate()

        try:
            logger.debug('Serving node [%s]' % node)
            self.generator.generate_node(node, incremental=True)
        except Exception, exception:
            logger.error(
                'Error [%s] occured when generating the node [%s]'
                        % (repr(exception), node))
            logger.debug(traceback.format_exc())

    def generate_resource(self, resource):
        """
        Regenerates the given resource.
        """
        deploy = self.site.config.deploy_root_path
        if not deploy.exists:
            return self.regenerate()
        dest = deploy.child_folder(resource.node.relative_path)
        if not dest.exists:
            return self.generate_node(resource.node)
        try:
            logger.debug('Serving resource [%s]' % resource)
            self.generator.generate_resource(resource, incremental=True)
        except Exception, exception:
            logger.error(
                'Error [%s] occured when serving the resource [%s]'
                        % (repr(exception), resource))
            logger.debug(traceback.format_exc())

########NEW FILE########
__FILENAME__ = site
# -*- coding: utf-8 -*-
"""
Parses & holds information about the site to be generated.
"""
import os
import fnmatch
import sys
import urlparse
from functools import wraps
from urllib import quote

from hyde.exceptions import HydeException
from hyde.model import Config

from commando.util import getLoggerWithNullHandler
from fswrap import FS, File, Folder

def path_normalized(f):
    @wraps(f)
    def wrapper(self, path):
        return f(self, unicode(path).replace('/', os.sep))
    return wrapper

logger = getLoggerWithNullHandler('hyde.engine')

class Processable(object):
    """
    A node or resource.
    """

    def __init__(self, source):
        super(Processable, self).__init__()
        self.source = FS.file_or_folder(source)
        self.is_processable = True
        self.uses_template = True
        self._relative_deploy_path = None

    @property
    def name(self):
        """
        The resource name
        """
        return self.source.name

    def __repr__(self):
        return self.path

    @property
    def path(self):
        """
        Gets the source path of this node.
        """
        return self.source.path

    def get_relative_deploy_path(self):
        """
        Gets the path where the file will be created
        after its been processed.
        """
        return self._relative_deploy_path \
                    if self._relative_deploy_path is not None \
                    else self.relative_path

    def set_relative_deploy_path(self, path):
        """
        Sets the path where the file ought to be created
        after its been processed.
        """
        self._relative_deploy_path = path
        self.site.content.deploy_path_changed(self)

    relative_deploy_path = property(get_relative_deploy_path, set_relative_deploy_path)

    @property
    def url(self):
        """
        Returns the relative url for the processable
        """
        return '/' + self.relative_deploy_path

    @property
    def full_url(self):
        """
        Returns the full url for the processable.
        """
        return self.site.full_url(self.relative_deploy_path)


class Resource(Processable):
    """
    Represents any file that is processed by hyde
    """

    def __init__(self, source_file, node):
        super(Resource, self).__init__(source_file)
        self.source_file = source_file
        if not node:
            raise HydeException("Resource cannot exist without a node")
        if not source_file:
            raise HydeException("Source file is required"
                                " to instantiate a resource")
        self.node = node
        self.site = node.site
        self.simple_copy = False

    @property
    def relative_path(self):
        """
        Gets the path relative to the root folder (Content)
        """
        return self.source_file.get_relative_path(self.node.root.source_folder)

    @property
    def slug(self):
        #TODO: Add a more sophisticated slugify method
        return self.source.name_without_extension

class Node(Processable):
    """
    Represents any folder that is processed by hyde
    """

    def __init__(self, source_folder, parent=None):
        super(Node, self).__init__(source_folder)
        if not source_folder:
            raise HydeException("Source folder is required"
                                " to instantiate a node.")
        self.root = self
        self.module = None
        self.site = None
        self.source_folder = Folder(unicode(source_folder))
        self.parent = parent
        if parent:
            self.root = self.parent.root
            self.module = self.parent.module if self.parent.module else self
            self.site = parent.site
        self.child_nodes = []
        self.resources = []

    def contains_resource(self, resource_name):
        """
        Returns True if the given resource name exists as a file
        in this node's source folder.
        """

        return File(self.source_folder.child(resource_name)).exists

    def get_resource(self, resource_name):
        """
        Gets the resource if the given resource name exists as a file
        in this node's source folder.
        """

        if self.contains_resource(resource_name):
            return self.root.resource_from_path(
                        self.source_folder.child(resource_name))
        return None

    def add_child_node(self, folder):
        """
        Creates a new child node and adds it to the list of child nodes.
        """

        if folder.parent != self.source_folder:
            raise HydeException("The given folder [%s] is not a"
                                " direct descendant of [%s]" %
                                (folder, self.source_folder))
        node = Node(folder, self)
        self.child_nodes.append(node)
        return node

    def add_child_resource(self, afile):
        """
        Creates a new resource and adds it to the list of child resources.
        """

        if afile.parent != self.source_folder:
            raise HydeException("The given file [%s] is not"
                                " a direct descendant of [%s]" %
                                (afile, self.source_folder))
        resource = Resource(afile, self)
        self.resources.append(resource)
        return resource

    def walk(self):
        """
        Walks the node, first yielding itself then
        yielding the child nodes depth-first.
        """
        yield self
        for child in self.child_nodes:
            for node in child.walk():
                yield node

    def rwalk(self):
        """
        Walk the node upward, first yielding itself then
        yielding its parents.
        """
        x = self
        while x:
            yield x
            x = x.parent

    def walk_resources(self):
        """
        Walks the resources in this hierarchy.
        """
        for node in self.walk():
            for resource in node.resources:
                yield resource

    @property
    def relative_path(self):
        """
        Gets the path relative to the root folder (Content, Media, Layout)
        """
        return self.source_folder.get_relative_path(self.root.source_folder)

class RootNode(Node):
    """
    Represents one of the roots of site: Content, Media or Layout
    """

    def __init__(self, source_folder, site):
        super(RootNode, self).__init__(source_folder)
        self.site = site
        self.node_map = {}
        self.node_deploy_map = {}
        self.resource_map = {}
        self.resource_deploy_map = {}

    @path_normalized
    def node_from_path(self, path):
        """
        Gets the node that maps to the given path.
        If no match is found it returns None.
        """
        if Folder(path) == self.source_folder:
            return self
        return self.node_map.get(unicode(Folder(path)), None)

    @path_normalized
    def node_from_relative_path(self, relative_path):
        """
        Gets the content node that maps to the given relative path.
        If no match is found it returns None.
        """
        return self.node_from_path(
                    self.source_folder.child(unicode(relative_path)))

    @path_normalized
    def resource_from_path(self, path):
        """
        Gets the resource that maps to the given path.
        If no match is found it returns None.
        """
        return self.resource_map.get(unicode(File(path)), None)

    @path_normalized
    def resource_from_relative_path(self, relative_path):
        """
        Gets the content resource that maps to the given relative path.
        If no match is found it returns None.
        """
        return self.resource_from_path(
                    self.source_folder.child(relative_path))

    def deploy_path_changed(self, item):
        """
        Handles the case where the relative deploy path of a
        resource has changed.
        """
        self.resource_deploy_map[unicode(item.relative_deploy_path)] = item

    @path_normalized
    def resource_from_relative_deploy_path(self, relative_deploy_path):
        """
        Gets the content resource whose deploy path maps to
        the given relative path. If no match is found it returns None.
        """
        if relative_deploy_path in self.resource_deploy_map:
            return self.resource_deploy_map[relative_deploy_path]
        return self.resource_from_relative_path(relative_deploy_path)

    def add_node(self, a_folder):
        """
        Adds a new node to this folder's hierarchy.
        Also adds it to the hashtable of path to node associations
        for quick lookup.
        """
        folder = Folder(a_folder)
        node = self.node_from_path(folder)
        if node:
            logger.debug("Node exists at [%s]" % node.relative_path)
            return node

        if not folder.is_descendant_of(self.source_folder):
            raise HydeException("The given folder [%s] does not"
                                " belong to this hierarchy [%s]" %
                                (folder, self.source_folder))

        p_folder = folder
        parent = None
        hierarchy = []
        while not parent:
            hierarchy.append(p_folder)
            p_folder = p_folder.parent
            parent = self.node_from_path(p_folder)

        hierarchy.reverse()
        node = parent if parent else self
        for h_folder in hierarchy:
            node = node.add_child_node(h_folder)
            self.node_map[unicode(h_folder)] = node
            logger.debug("Added node [%s] to [%s]" % (
                            node.relative_path, self.source_folder))

        return node

    def add_resource(self, a_file):
        """
        Adds a file to the parent node.  Also adds to to the
        hashtable of path to resource associations for quick lookup.
        """

        afile = File(a_file)

        resource = self.resource_from_path(afile)
        if resource:
            logger.debug("Resource exists at [%s]" % resource.relative_path)
            return resource

        if not afile.is_descendant_of(self.source_folder):
            raise HydeException("The given file [%s] does not reside"
                                " in this hierarchy [%s]" %
                                (afile, self.source_folder))

        node = self.node_from_path(afile.parent)

        if not node:
            node = self.add_node(afile.parent)
        resource = node.add_child_resource(afile)
        self.resource_map[unicode(afile)] = resource
        relative_path = resource.relative_path
        resource.simple_copy = any(fnmatch.fnmatch(relative_path, pattern)
                                        for pattern
                                        in self.site.config.simple_copy)

        logger.debug("Added resource [%s] to [%s]" %
                    (resource.relative_path, self.source_folder))
        return resource

    def load(self):
        """
        Walks the `source_folder` and loads the sitemap.
        Creates nodes and resources, reads metadata and injects attributes.
        This is the model for hyde.
        """

        if not self.source_folder.exists:
            raise HydeException("The given source folder [%s]"
                                " does not exist" % self.source_folder)

        with self.source_folder.walker as walker:

            def dont_ignore(name):
                for pattern in self.site.config.ignore:
                    if fnmatch.fnmatch(name, pattern):
                        return False
                return True

            @walker.folder_visitor
            def visit_folder(folder):
                if dont_ignore(folder.name):
                    self.add_node(folder)
                else:
                    logger.debug("Ignoring node: %s" % folder.name)
                    return False

            @walker.file_visitor
            def visit_file(afile):
                if dont_ignore(afile.name):
                    self.add_resource(afile)


def _encode_path(base, path, safe):
    base = base.strip().replace(os.sep, '/').encode('utf-8')
    path = path.strip().replace(os.sep, '/').encode('utf-8')
    path = quote(path, safe) if safe is not None else quote(path)
    return base.rstrip('/') + '/' + path.lstrip('/')

class Site(object):
    """
    Represents the site to be generated.
    """

    def __init__(self, sitepath=None, config=None):
        super(Site, self).__init__()
        self.sitepath = Folder(Folder(sitepath).fully_expanded_path)
        # Add sitepath to the list of module search paths so that
        # local plugins can be included.
        sys.path.insert(0, self.sitepath.fully_expanded_path)

        self.config = config if config else Config(self.sitepath)
        self.content = RootNode(self.config.content_root_path, self)
        self.plugins = []
        self.context = {}

    def refresh_config(self):
        """
        Refreshes config data if one or more config files have
        changed. Note that this does not refresh the meta data.
        """
        if self.config.needs_refresh():
            logger.debug("Refreshing config data")
            self.config = Config(self.sitepath,
                        self.config.config_file,
                        self.config.config_dict)

    def reload_if_needed(self):
        """
        Reloads if the site has not been loaded before or if the
        configuration has changed since the last load.
        """
        if not len(self.content.child_nodes):
            self.load()

    def load(self):
        """
        Walks the content and media folders to load up the sitemap.
        """
        self.content.load()

    def _safe_chars(self, safe=None):
        if safe is not None:
            return safe
        elif self.config.encode_safe is not None:
            return self.config.encode_safe
        else:
            return None

    def content_url(self, path, safe=None):
        """
        Returns the content url by appending the base url from the config
        with the given path. The return value is url encoded.
        """
        return _encode_path(self.config.base_url, path, self._safe_chars(safe))


    def media_url(self, path, safe=None):
        """
        Returns the media url by appending the media base url from the config
        with the given path. The return value is url encoded.
        """
        return _encode_path(self.config.media_url, path, self._safe_chars(safe))

    def full_url(self, path, safe=None):
        """
        Determines if the given path is media or content based on the
        configuration and returns the appropriate url. The return value
        is url encoded.
        """
        if urlparse.urlparse(path)[:2] != ("",""):
            return path

        if self.is_media(path):
            relative_path = File(path).get_relative_path(
                                Folder(self.config.media_root))
            return self.media_url(relative_path, safe)
        else:
            return self.content_url(path, safe)

    def is_media(self, path):
        """
        Given the relative path, determines if it is content or media.
        """
        folder = self.content.source.child_folder(path)
        return folder.is_descendant_of(self.config.media_root_path)
########NEW FILE########
__FILENAME__ = template
# -*- coding: utf-8 -*-
# pylint: disable-msg=W0104,E0602,W0613,R0201
"""
Abstract classes and utilities for template engines
"""
from hyde.exceptions import HydeException

import abc

from commando.util import getLoggerWithNullHandler


class HtmlWrap(object):
    """
    A wrapper class for raw html.

    Provides pyquery interface if available.
    Otherwise raw html access.
    """

    def __init__(self, html):
        super(HtmlWrap, self).__init__()
        self.raw = html
        try:
            from pyquery import PyQuery
        except:
            PyQuery = False
        if PyQuery:
            self.q = PyQuery(html)

    def __unicode__(self):
        return self.raw

    def __call__(self, selector=None):
        if not self.q:
            return self.raw
        return self.q(selector).html()

class Template(object):
    """
    Interface for hyde template engines. To use a different template engine,
    the following interface must be implemented.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, sitepath):
        self.sitepath = sitepath
        self.logger = getLoggerWithNullHandler(self.__class__.__name__)

    @abc.abstractmethod
    def configure(self, site, engine):

        """
        The site object should contain a config attribute. The config object
        is a simple YAML object with required settings. The template
        implementations are responsible for transforming this object to match
        the `settings` required for the template engines.

        The engine is an informal protocol to provide access to some
        hyde internals.

        The preprocessor attribute must contain the function that trigger the
        hyde plugins to preprocess the template after load.

        A context_for_path attribute must contain the function that returns
        the context object that is populated with the appropriate variables
        for the given path.
        """
        return

    def clear_caches(self):
        """
        Clear all caches to prepare for regeneration
        """
        return

    def get_dependencies(self, text):
        """
        Finds the dependencies based on the included
        files.
        """
        return None

    @abc.abstractmethod
    def render_resource(self, resource, context):
        """
        This function must load the file represented by the resource
        object and return the rendered text.
        """
        return ''

    @abc.abstractmethod
    def render(self, text, context):
        """
        Given the text, and the context, this function must return the
        rendered string.
        """

        return ''

    @abc.abstractproperty
    def exception_class(self):
        return HydeException

    @abc.abstractproperty
    def patterns(self):
        """
        Patterns for matching selected template statements.
        """
        return {}

    @abc.abstractmethod
    def get_include_statement(self, path_to_include):
        """
        Returns an include statement for the current template,
        given the path to include.
        """
        return '{%% include \'%s\' %%}' % path_to_include

    @abc.abstractmethod
    def get_extends_statement(self, path_to_extend):
        """
        Returns an extends statement for the current template,
        given the path to extend.
        """
        return '{%% extends \'%s\' %%}' % path_to_extend

    @abc.abstractmethod
    def get_open_tag(self, tag, params):
        """
        Returns an open tag statement.
        """
        return '{%% %s %s %%}' % (tag, params)

    @abc.abstractmethod
    def get_close_tag(self, tag, params):
        """
        Returns an open tag statement.
        """
        return '{%% end%s %%}' % tag

    @abc.abstractmethod
    def get_content_url_statement(self, url):
        """
        Returns the content url statement.
        """
        return '/' + url

    @abc.abstractmethod
    def get_media_url_statement(self, url):
        """
        Returns the media url statement.
        """
        return '/media/' + url

    @staticmethod
    def find_template(site):
        """
        Reads the configuration to find the appropriate template.
        """
        # TODO: Find the appropriate template environment
        from hyde.ext.templates.jinja import Jinja2Template
        template = Jinja2Template(site.sitepath)
        return template

########NEW FILE########
__FILENAME__ = test_auto_extend
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site


from fswrap import File
from nose.tools import nottest
from pyquery import PyQuery

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestAutoExtend(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    @nottest
    def assert_extended(self, s, txt, templ):
        content = (templ.strip() % txt).strip()
        bd = File(TEST_SITE.child('content/auto_extend.html'))
        bd.write(content)
        gen = Generator(s)
        gen.generate_resource_at_path(bd.path)
        res = s.content.resource_from_path(bd.path)
        target = File(s.config.deploy_root_path.child(res.relative_deploy_path))
        assert target.exists
        text = target.read_all()
        q = PyQuery(text)
        assert q('title').text().strip() == txt.strip()

    def test_can_auto_extend(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin',
                            'hyde.ext.plugins.meta.AutoExtendPlugin',
                            'hyde.ext.plugins.text.BlockdownPlugin']
        txt ="This template tests to make sure blocks can be replaced with markdownish syntax."
        templ = """
---
extends: base.html
---
=====title========
%s
====/title========"""
        self.assert_extended(s, txt, templ)



    def test_can_auto_extend_with_default_blocks(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin',
                            'hyde.ext.plugins.meta.AutoExtendPlugin',
                            'hyde.ext.plugins.text.BlockdownPlugin']
        txt ="This template tests to make sure blocks can be replaced with markdownish syntax."
        templ = """
---
extends: base.html
default_block: title
---
%s
"""
        self.assert_extended(s, txt, templ)

########NEW FILE########
__FILENAME__ = test_blockdown
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File
from pyquery import PyQuery

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestBlockdown(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_can_parse_blockdown(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.text.BlockdownPlugin']
        txt ="This template tests to make sure blocks can be replaced with markdownish syntax."
        templ = """
{%% extends "base.html" %%}
=====title========
%s
====/title========"""

        content = (templ.strip() % txt).strip()
        bd = File(TEST_SITE.child('content/blockdown.html'))
        bd.write(content)
        gen = Generator(s)
        gen.generate_resource_at_path(bd.path)
        res = s.content.resource_from_path(bd.path)
        target = File(s.config.deploy_root_path.child(res.relative_deploy_path))
        assert target.exists
        text = target.read_all()
        q = PyQuery(text)
        assert q('title').text().strip() == txt.strip()

########NEW FILE########
__FILENAME__ = test_combine
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File, Folder

COMBINE_SOURCE = File(__file__).parent.child_folder('combine')
TEST_SITE = File(__file__).parent.parent.child_folder('_test')

class CombineTester(object):
    def _test_combine(self, content):
        s = Site(TEST_SITE)
        s.config.plugins = [
            'hyde.ext.plugins.meta.MetaPlugin',
            'hyde.ext.plugins.structure.CombinePlugin']
        source = TEST_SITE.child('content/media/js/script.js')
        target = File(Folder(s.config.deploy_root_path).child('media/js/script.js'))
        File(source).write(content)

        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        text = target.read_all()
        return text, s

class TestCombine(CombineTester):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        TEST_SITE.child_folder('content/media/js').make()
        COMBINE_SOURCE.copy_contents_to(TEST_SITE.child('content/media/js'))

    def tearDown(self):
        TEST_SITE.delete()

    def test_combine_top(self):
        text, _ = self._test_combine("""
---
combine:
   files: script.*.js
   where: top
---

Last line""")
        assert text == """var a = 1 + 2;
var b = a + 3;
var c = a + 5;
Last line"""
        return

    def test_combine_bottom(self):
        text, _ = self._test_combine("""
---
combine:
   files: script.*.js
   where: bottom
---

First line
""")
        expected = """First line
var a = 1 + 2;
var b = a + 3;
var c = a + 5;
"""

        assert text.strip() == expected.strip()
        return

    def test_combine_bottom_unsorted(self):
        text, _ = self._test_combine("""
---
combine:
   sort: false
   files:
        - script.3.js
        - script.1.js
        - script.2.js
   where: bottom
---

First line
""")
        expected = """First line
var c = a + 5;
var a = 1 + 2;
var b = a + 3;
"""

        assert text.strip() == expected.strip()
        return

    def test_combine_remove(self):
        _, s = self._test_combine("""
---
combine:
   files: script.*.js
   remove: yes
---

First line""")
        for i in range(1,4):
            assert not File(Folder(s.config.deploy_root_path).
                            child('media/js/script.%d.js' % i)).exists


class TestCombinePaths(CombineTester):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        TEST_SITE.child_folder('content/media/js').make()
        JS = TEST_SITE.child_folder('content/scripts').make()
        S1 = JS.child_folder('s1').make()
        S2 = JS.child_folder('s2').make()
        S3 = JS.child_folder('s3').make()
        File(COMBINE_SOURCE.child('script.1.js')).copy_to(S1)
        File(COMBINE_SOURCE.child('script.2.js')).copy_to(S2)
        File(COMBINE_SOURCE.child('script.3.js')).copy_to(S3)

    def tearDown(self):
        TEST_SITE.delete()

    def test_combine_top(self):
        text, _ = self._test_combine("""
---
combine:
   root: scripts
   recurse: true
   files: script.*.js
   where: top
---

Last line""")
        assert text == """var a = 1 + 2;
var b = a + 3;
var c = a + 5;
Last line"""
        return

########NEW FILE########
__FILENAME__ = test_depends
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestDepends(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        TEST_SITE.parent.child_folder(
                    'templates/jinja2').copy_contents_to(
                        TEST_SITE.child_folder('content'))

    def tearDown(self):
        TEST_SITE.delete()

    def test_depends(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin',
                            'hyde.ext.plugins.depends.DependsPlugin']
        text = """
===
depends: index.html
===

"""
        inc = File(TEST_SITE.child('content/inc.md'))
        inc.write(text)
        gen = Generator(s)
        gen.load_site_if_needed()
        gen.load_template_if_needed()
        def dateformat(x):
            return x.strftime('%Y-%m-%d')
        gen.template.env.filters['dateformat'] = dateformat
        gen.generate_resource_at_path(inc.name)
        res = s.content.resource_from_relative_path(inc.name)
        assert len(res.depends) == 1
        assert 'index.html' in res.depends
        deps = list(gen.get_dependencies(res))
        assert len(deps) == 3

        assert 'helpers.html' in deps
        assert 'layout.html' in deps
        assert 'index.html' in deps
########NEW FILE########
__FILENAME__ = test_drafts
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""

from hyde.generator import Generator
from hyde.site import Site
from hyde.model import Config

from fswrap import File

TEST_SITE = File(__file__).parent.parent.child_folder('_test')

DRAFT_POST = """

---
is_draft: true
---

A draft post.

"""

class TestDrafts(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        draft = TEST_SITE.child_file('content/blog/2013/may/draft-post.html')
        draft.parent.make()
        draft.write(DRAFT_POST)

    def tearDown(self):
        TEST_SITE.delete()

    def test_drafts_are_skipped_in_production(self):
        s = Site(TEST_SITE)
        cfg = """
        mode: production
        plugins:
            - hyde.ext.plugins.meta.MetaPlugin
            - hyde.ext.plugins.blog.DraftsPlugin
        """
        import yaml
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        gen = Generator(s)
        gen.generate_all()
        assert not s.config.deploy_root_path.child_file(
                    'blog/2013/may/draft-post.html').exists

    def test_drafts_are_published_in_development(self):
        s = Site(TEST_SITE)
        cfg = """
        mode: development
        plugins:
            - hyde.ext.plugins.meta.MetaPlugin
            - hyde.ext.plugins.blog.DraftsPlugin
        """
        import yaml
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        gen = Generator(s)
        gen.generate_all()
        assert s.config.deploy_root_path.child_file(
                    'blog/2013/may/draft-post.html').exists



########NEW FILE########
__FILENAME__ = test_flattener
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""

from hyde.generator import Generator
from hyde.site import Site
from hyde.model import Config

from fswrap import File

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestFlattner(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_can_flatten(self):
        s = Site(TEST_SITE)
        cfg = """
        plugins:
            - hyde.ext.plugins.structure.FlattenerPlugin
        flattener:
            items:
                -
                    source: blog
                    target: ''
        """
        import yaml
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        gen = Generator(s)
        gen.generate_all()

        assert not s.config.deploy_root_path.child_folder('blog').exists
        assert File(s.config.deploy_root_path.child('merry-christmas.html')).exists

    def test_flattener_fixes_nodes(self):
        s = Site(TEST_SITE)
        cfg = """
        plugins:
            - hyde.ext.plugins.structure.FlattenerPlugin
        flattener:
            items:
                -
                    source: blog
                    target: ''
        """
        import yaml
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        gen = Generator(s)
        gen.generate_all()
        blog_node = s.content.node_from_relative_path('blog')

        assert blog_node
        assert blog_node.url == '/'



########NEW FILE########
__FILENAME__ = test_grouper
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.ext.plugins.meta import GrouperPlugin, MetaPlugin, SorterPlugin
from hyde.generator import Generator
from hyde.site import Site
from hyde.model import Config, Expando

from fswrap import File
from hyde.tests.util import assert_html_equals
import yaml

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestGrouperSingleLevel(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                  'sites/test_grouper').copy_contents_to(TEST_SITE)

        self.s = Site(TEST_SITE)
        cfg = """
        nodemeta: meta.yaml
        plugins:
          - hyde.ext.plugins.meta.MetaPlugin
          - hyde.ext.plugins.meta.SorterPlugin
          - hyde.ext.plugins.meta.GrouperPlugin
        sorter:
          kind:
              attr:
                  - source_file.kind
              filters:
                  is_processable: True
        grouper:
          section:
              description: Sections in the site
              sorter: kind
              groups:
                  -
                      name: start
                      description: Getting Started
                  -
                      name: plugins
                      description: Plugins

        """
        self.s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        self.s.load()
        MetaPlugin(self.s).begin_site()
        SorterPlugin(self.s).begin_site()
        GrouperPlugin(self.s).begin_site()

        self.all = ['installation.html', 'overview.html', 'templating.html', 'plugins.html', 'tags.html']
        self.start = ['installation.html', 'overview.html', 'templating.html']
        self.plugins = ['plugins.html', 'tags.html']
        self.section = self.all

    def tearDown(self):
        TEST_SITE.delete()

    def test_site_grouper_groups(self):

        groups = dict([(g.name, g) for g in self.s.grouper['section'].groups])
        assert len(groups) == 2
        assert 'start' in groups
        assert 'plugins' in groups

    def test_site_grouper_walk_groups(self):

        groups = dict([(g.name, g) for g in self.s.grouper['section'].walk_groups()])
        assert len(groups) == 3
        assert 'section' in groups
        assert 'start' in groups
        assert 'plugins' in groups

    def test_walk_section_groups(self):

        assert hasattr(self.s.content, 'walk_section_groups')
        groups = dict([(grouper.group.name, grouper) for grouper in self.s.content.walk_section_groups()])
        assert len(groups) == 3
        assert 'section' in groups
        assert 'start' in groups
        assert 'plugins' in groups
        for name in ['start', 'plugins']:
            res = [resource.name for resource in groups[name].resources]
            assert res == getattr(self, name)

    def test_walk_start_groups(self):

        assert hasattr(self.s.content, 'walk_start_groups')
        groups = dict([(g.name, g) for g, resources in self.s.content.walk_start_groups()])
        assert len(groups) == 1
        assert 'start' in groups


    def test_walk_plugins_groups(self):

        assert hasattr(self.s.content, 'walk_plugins_groups')
        groups = dict([(g.name, g) for g, resources in self.s.content.walk_plugins_groups()])
        assert len(groups) == 1
        assert 'plugins' in groups

    def test_walk_section_resources(self):

        assert hasattr(self.s.content, 'walk_resources_grouped_by_section')

        resources = [resource.name for resource in self.s.content.walk_resources_grouped_by_section()]
        assert resources == self.all


    def test_walk_start_resources(self):

        assert hasattr(self.s.content, 'walk_resources_grouped_by_start')

        start_resources = [resource.name for resource in self.s.content.walk_resources_grouped_by_start()]
        assert start_resources == self.start

    def test_walk_plugins_resources(self):

        assert hasattr(self.s.content, 'walk_resources_grouped_by_plugins')

        plugin_resources = [resource.name for resource in self.s.content.walk_resources_grouped_by_plugins()]
        assert plugin_resources == self.plugins

    def test_resource_group(self):

        groups = dict([(g.name, g) for g in self.s.grouper['section'].groups])

        for name, group in groups.items():
            pages = getattr(self, name)
            for page in pages:
                res = self.s.content.resource_from_relative_path('blog/' + page)
                assert hasattr(res, 'section_group')
                res_group = getattr(res, 'section_group')
                assert res_group == group

    def test_resource_belongs_to(self):

        groups = dict([(g.name, g) for g in self.s.grouper['section'].groups])

        for name, group in groups.items():
            pages = getattr(self, name)
            for page in pages:
                res = self.s.content.resource_from_relative_path('blog/' + page)
                res_groups = getattr(res, 'walk_%s_groups' % name)()
                assert group in res_groups

    def test_prev_next(self):

        resources = []
        for page in self.all:
            resources.append(self.s.content.resource_from_relative_path('blog/' + page))

        index = 0
        for res in resources:
            if index < 4:
                assert res.next_in_section.name == self.all[index + 1]
            else:
                assert not res.next_in_section
            index += 1

        index = 0
        for res in resources:
            if index:
                assert res.prev_in_section.name == self.all[index - 1]
            else:
                assert not res.prev_in_section
            index += 1

    def test_nav_with_grouper(self):

        text ="""
{% for group, resources in site.content.walk_section_groups() %}
<ul>
    <li>
        <h2>{{ group.name|title }}</h2>
        <h3>{{ group.description }}</h3>
        <ul class="links">
            {% for resource in resources %}
            <li>{{resource.name}}</li>
            {% endfor %}
        </ul>
    </li>
</ul>
{% endfor %}

"""
        expected = """
<ul>
    <li>
        <h2>Section</h2>
        <h3>Sections in the site</h3>
        <ul class="links"></ul>
    </li>
</ul>
<ul>
    <li>
        <h2>Start</h2>
        <h3>Getting Started</h3>
        <ul class="links">
            <li>installation.html</li>
            <li>overview.html</li>
            <li>templating.html</li>
        </ul>
    </li>
</ul>
<ul>
    <li>
        <h2>Plugins</h2>
        <h3>Plugins</h3>
        <ul class="links">
            <li>plugins.html</li>
            <li>tags.html</li>
        </ul>
    </li>
</ul>

"""

        gen = Generator(self.s)
        gen.load_site_if_needed()
        gen.load_template_if_needed()
        out = gen.template.render(text, {'site':self.s})
        assert_html_equals(out, expected)

    def test_nav_with_grouper_sorted(self):

        cfg = """
        nodemeta: meta.yaml
        plugins:
          - hyde.ext.plugins.meta.MetaPlugin
          - hyde.ext.plugins.meta.SorterPlugin
          - hyde.ext.plugins.meta.GrouperPlugin
        sorter:
          kind:
              attr:
                  - source_file.kind
              filters:
                  is_processable: True
        grouper:
          section:
              description: Sections in the site
              sorter: kind
              groups:
                  -
                      name: start
                      description: Getting Started
                  -
                      name: awesome
                      description: Awesome
                  -
                      name: plugins
                      description: Plugins

        """
        self.s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        self.s.load()
        MetaPlugin(self.s).begin_site()
        SorterPlugin(self.s).begin_site()
        GrouperPlugin(self.s).begin_site()

        text ="""
{% set sorted = site.grouper['section'].groups|sort(attribute='name') %}
{% for group in sorted %}
<ul>
    <li>
        <h2>{{ group.name|title }}</h2>
        <h3>{{ group.description }}</h3>
        <ul class="links">
            {% for resource in group.walk_resources_in_node(site.content) %}
            <li>{{resource.name}}</li>
            {% endfor %}
        </ul>
    </li>
</ul>
{% endfor %}

"""
        expected = """
<ul>
    <li>
        <h2>Awesome</h2>
        <h3>Awesome</h3>
        <ul class="links">
        </ul>
    </li>
</ul>
<ul>
    <li>
        <h2>Plugins</h2>
        <h3>Plugins</h3>
        <ul class="links">
            <li>plugins.html</li>
            <li>tags.html</li>
        </ul>
    </li>
</ul>
<ul>
    <li>
        <h2>Start</h2>
        <h3>Getting Started</h3>
        <ul class="links">
            <li>installation.html</li>
            <li>overview.html</li>
            <li>templating.html</li>
        </ul>
    </li>
</ul>


"""
        self.s.config.grouper.section.groups.append(Expando({"name": "awesome", "description": "Aweesoome"}));
        gen = Generator(self.s)
        gen.load_site_if_needed()
        gen.load_template_if_needed()
        out = gen.template.render(text, {'site':self.s})
        assert_html_equals(out, expected)

########NEW FILE########
__FILENAME__ = test_images
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`

Requires PIL
"""
from hyde.generator import Generator
from hyde.site import Site
from hyde.ext.plugins.images import thumb_scale_size


from fswrap import File
import yaml

TEST_SITE = File(__file__).parent.parent.child_folder('_test')
IMAGE_SOURCE = File(__file__).parent.child_folder('images')

PORTRAIT_IMAGE = "portrait.jpg"
PORTRAIT_SIZE = (90, 120)
LANDSCAPE_IMAGE = "landscape.jpg"
LANDSCAPE_SIZE = (120, 90)

IMAGES = [PORTRAIT_IMAGE, LANDSCAPE_IMAGE]
SIZES = [PORTRAIT_SIZE, LANDSCAPE_SIZE]

# PIL requirement
try:
    from PIL import Image
except ImportError:
    # No pillow
    import Image

class TestImageSizer(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        IMAGES = TEST_SITE.child_folder('content/media/img')
        IMAGES.make()
        IMAGE_SOURCE.copy_contents_to(IMAGES)
        self.site = Site(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def _generic_test_image(self, text):
        self.site.config.mode = "production"
        self.site.config.plugins = ['hyde.ext.plugins.images.ImageSizerPlugin']
        tlink = File(self.site.content.source_folder.child('timg.html'))
        tlink.write(text)
        gen = Generator(self.site)
        gen.generate_all()
        f = File(self.site.config.deploy_root_path.child(tlink.name))
        assert f.exists
        html = f.read_all()
        assert html
        return html

    def test_size_image(self):
        text = u"""
<img src="/media/img/%s">
""" % PORTRAIT_IMAGE
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] in html

    def test_size_image_relative(self):
        text = u"""
<img src="media/img/%s">
""" % PORTRAIT_IMAGE
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] in html

    def test_size_image_no_resize(self):
        text = u"""
<img src="/media/img/%s" width="2000" height="150">
""" % PORTRAIT_IMAGE
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] not in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] not in html

    def test_size_image_size_proportional(self):
        text = u"""
<img src="/media/img/%s" width="%d">
""" % (PORTRAIT_IMAGE,  PORTRAIT_SIZE[0]*2)
        html = self._generic_test_image(text)
        assert ' width="%d"' % (PORTRAIT_SIZE[0]*2) in html
        assert ' height="%d"' % (PORTRAIT_SIZE[1]*2) in html

    def test_size_image_not_exists(self):
        text = u"""
<img src="/media/img/hyde-logo-no.png">
"""
        self._generic_test_image(text)

    def test_size_image_multiline(self):
        text = u"""
     <img src="/media/img/%s">
""" % PORTRAIT_IMAGE
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] in html

    def test_size_multiple_images(self):
        text = u"""
<img src="/media/img/%s">
<img src="/media/img/%s">Hello <img src="/media/img/%s">
<img src="/media/img/%s">Bye
""" % ((PORTRAIT_IMAGE,)*4)
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] in html
        assert 'Hello ' in html
        assert 'Bye' in html
        assert len([f for f in html.split("<img")
                    if ' width=' in f]) == 4
        assert len([f for f in html.split("<img")
                    if ' height=' in f]) == 4

    def test_size_malformed1(self):
        text = u"""
<img src="/media/img/%s>
""" % PORTRAIT_IMAGE
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] in html

    def test_size_malformed2(self):
        text = u"""
<img src="/media/img/%s alt="hello">
""" % PORTRAIT_IMAGE
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] in html

    def test_outside_media_url(self):
        self.site.config.media_url = "http://media.example.com/"
        text = u"""
<img src="http://media.example.com/img/%s" alt="hello">
""" % PORTRAIT_IMAGE
        html = self._generic_test_image(text)
        assert ' width="%d"' % PORTRAIT_SIZE[0] in html
        assert ' height="%d"' % PORTRAIT_SIZE[1] in html

class TestImageThumbSize(object):

    def test_width_only(self):
        ow, oh = 100, 200
        nw, nh = thumb_scale_size(ow, oh, 50, None)
        assert nw == 50
        assert nh == 100

    def test_width_only_nonintegral(self):
        ow, oh = 100, 205
        nw, nh = thumb_scale_size(ow, oh, 50, None)
        assert nw == 50
        assert nh == 103

    def test_height_only(self):
        ow, oh = 100, 200
        nw, nh = thumb_scale_size(ow, oh, None, 100)
        assert nw == 50
        assert nh == 100

    def test_height_only_nonintegral(self):
        ow, oh = 105, 200
        nw, nh = thumb_scale_size(ow, oh, None, 100)
        assert nw == 53
        assert nh == 100

    def test_height_and_width_portrait(self):
        ow, oh = 100, 200
        nw, nh = thumb_scale_size(ow, oh, 50, 50)
        assert nw == 50
        assert nh == 100

    def test_height_and_width_landscape(self):
        ow, oh = 200, 100
        nw, nh = thumb_scale_size(ow, oh, 50, 50)
        assert nw == 100
        assert nh == 50

class TestImageThumbnails(object):
    # TODO: add tests for cropping? (not easy currently)

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        IMAGES = TEST_SITE.child_folder('content/media/img')
        IMAGES.make()
        IMAGE_SOURCE.copy_contents_to(IMAGES)
        self.image_folder = IMAGES
        self.site = Site(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def _generate_site_with_meta(self, meta):
        self.site.config.mode = "production"
        self.site.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin', 'hyde.ext.plugins.images.ImageThumbnailsPlugin']

        mlink = File(self.image_folder.child('meta.yaml'))
        meta_text = yaml.dump(meta, default_flow_style=False)
        mlink.write(meta_text)
        gen = Generator(self.site)
        gen.generate_all()

    def _test_generic_thumbnails(self, meta):
        self._generate_site_with_meta(meta)
        thumb_meta = meta.get('thumbnails', [])
        for th in thumb_meta:
            prefix = th.get('prefix')
            if prefix is None:
                continue

            for fn in [PORTRAIT_IMAGE, LANDSCAPE_IMAGE]:
                f = File(self._deployed_image(prefix, fn))
                assert f.exists

    def _deployed_image(self, prefix, filename):
        return self.site.config.deploy_root_path.child('media/img/%s%s'%(prefix,filename))

    def test_width(self):
        prefix='thumb_'
        meta = dict(thumbnails=[dict(width=50, prefix=prefix, include=['*.jpg'])])
        self._test_generic_thumbnails(meta)
        for fn in IMAGES:
            im = Image.open(self._deployed_image(prefix, fn))
            assert im.size[0] == 50

    def test_height(self):
        prefix='thumb_'
        meta = dict(thumbnails=[dict(height=50, prefix=prefix, include=['*.jpg'])])
        self._test_generic_thumbnails(meta)
        for fn in IMAGES:
            im = Image.open(self._deployed_image(prefix, fn))
            assert im.size[1] == 50

    def test_width_and_height(self):
        prefix='thumb_'
        meta = dict(thumbnails=[dict(width=50, height=50, prefix=prefix, include=['*.jpg'])])
        self._test_generic_thumbnails(meta)
        for fn in IMAGES:
            im = Image.open(self._deployed_image(prefix, fn))
            assert im.size[0] == 50
            assert im.size[1] == 50

    def test_larger(self):
        prefix='thumb_'
        meta = dict(thumbnails=[dict(larger=50, prefix=prefix, include=['*.jpg'])])
        self._test_generic_thumbnails(meta)

        im = Image.open(self._deployed_image(prefix, PORTRAIT_IMAGE))
        assert im.size[1] == 50

        im = Image.open(self._deployed_image(prefix, LANDSCAPE_IMAGE))
        assert im.size[0] == 50

    def test_smaller(self):
        prefix='thumb_'
        meta = dict(thumbnails=[dict(smaller=50, prefix=prefix, include=['*.jpg'])])
        self._test_generic_thumbnails(meta)

        im = Image.open(self._deployed_image(prefix, PORTRAIT_IMAGE))
        assert im.size[0] == 50

        im = Image.open(self._deployed_image(prefix, LANDSCAPE_IMAGE))
        assert im.size[1] == 50

    def test_larger_and_smaller(self):
        prefix='thumb_'
        meta = dict(thumbnails=[dict(larger=100, smaller=50, prefix=prefix, include=['*.jpg'])])
        self._test_generic_thumbnails(meta)

        im = Image.open(self._deployed_image(prefix, PORTRAIT_IMAGE))
        assert im.size[0] == 50
        assert im.size[1] == 100

        im = Image.open(self._deployed_image(prefix, LANDSCAPE_IMAGE))
        assert im.size[0] == 100
        assert im.size[1] == 50

########NEW FILE########
__FILENAME__ = test_less
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File, Folder

LESS_SOURCE = File(__file__).parent.child_folder('less')
TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestLess(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        LESS_SOURCE.copy_contents_to(TEST_SITE.child('content/media/css'))
        File(TEST_SITE.child('content/media/css/site.css')).delete()


    def tearDown(self):
        TEST_SITE.delete()

    def test_can_execute_less(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.css.LessCSSPlugin']
        source = TEST_SITE.child('content/media/css/site.less')
        target = File(Folder(s.config.deploy_root_path).child('media/css/site.css'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        text = target.read_all()
        expected_text = File(LESS_SOURCE.child('expected-site.css')).read_all()

        assert text == expected_text
        return

########NEW FILE########
__FILENAME__ = test_markings
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File
from pyquery import PyQuery

TEST_SITE = File(__file__).parent.parent.child_folder('_test')

def assert_valid_conversion(html):
    assert html
    q = PyQuery(html)
    assert "is_processable" not in html
    assert q("h1")
    assert "This is a" in q("h1").text()
    assert "heading" in q("h1").text()
    assert q(".amp").length == 1
    assert "mark" not in html
    assert "reference" not in html
    assert '.' not in q.text()
    assert '/' not in q.text()

class TestMarkings(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()



    def test_mark(self):
        text = u"""
===
is_processable: False
===
{% filter markdown|typogrify %}
§§ heading
This is a heading
=================
§§ /heading

§§ content
Hyde & Jinja
§§ /

{% endfilter %}
"""

        text2 = """
{% refer to "inc.md" as inc %}
{% filter markdown|typogrify %}
{{ inc.heading }}
{{ inc.content }}
{% endfilter %}
"""
        site = Site(TEST_SITE)
        site.config.plugins = [
            'hyde.ext.plugins.meta.MetaPlugin',
            'hyde.ext.plugins.text.MarkingsPlugin']
        inc = File(TEST_SITE.child('content/inc.md'))
        inc.write(text)
        site.load()
        gen = Generator(site)
        gen.load_template_if_needed()

        template = gen.template
        html = template.render(text2, {}).strip()
        assert_valid_conversion(html)

    def test_reference(self):
        text = u"""
===
is_processable: False
===
{% filter markdown|typogrify %}
§§ heading
This is a heading
=================
§§ /heading

§§ content
Hyde & Jinja
§§ /

{% endfilter %}
"""

        text2 = u"""
※ inc.md as inc
{% filter markdown|typogrify %}
{{ inc.heading }}
{{ inc.content }}
{% endfilter %}
"""
        site = Site(TEST_SITE)
        site.config.plugins = [
            'hyde.ext.plugins.meta.MetaPlugin',
            'hyde.ext.plugins.text.MarkingsPlugin',
            'hyde.ext.plugins.text.ReferencePlugin']
        inc = File(site.content.source_folder.child('inc.md'))
        inc.write(text.strip())
        src = File(site.content.source_folder.child('src.html'))
        src.write(text2.strip())
        gen = Generator(site)
        gen.generate_all()
        f = File(site.config.deploy_root_path.child(src.name))
        assert f.exists
        html = f.read_all()
        assert_valid_conversion(html)

########NEW FILE########
__FILENAME__ = test_meta
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File, Folder
from pyquery import PyQuery
import yaml


TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestMeta(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_can_set_standard_attributes(self):
        text = """
---
is_processable: False
---
{% extends "base.html" %}
"""
        about2 = File(TEST_SITE.child('content/about2.html'))
        about2.write(text)
        s = Site(TEST_SITE)
        s.load()
        res = s.content.resource_from_path(about2.path)
        assert res.is_processable

        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin']
        gen = Generator(s)
        gen.generate_all()
        assert not res.meta.is_processable
        assert not res.is_processable

    def test_ignores_pattern_in_content(self):
        text = """
{% markdown %}

Heading 1
===

Heading 2
===

{% endmarkdown %}
"""
        about2 = File(TEST_SITE.child('content/about2.html'))
        about2.write(text)
        s = Site(TEST_SITE)
        s.load()
        res = s.content.resource_from_path(about2.path)
        assert res.is_processable

        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin']
        gen = Generator(s)
        gen.generate_all()
        target = File(Folder(s.config.deploy_root_path).child('about2.html'))
        text = target.read_all()
        q = PyQuery(text)
        assert q("h1").length == 2
        assert q("h1:nth-child(1)").text().strip() == "Heading 1"
        assert q("h1:nth-child(2)").text().strip() == "Heading 2"

    def test_can_load_front_matter(self):
        d = {'title': 'A nice title',
            'author': 'Lakshmi Vyas',
            'twitter': 'lakshmivyas'}
        text = """
---
title: %(title)s
author: %(author)s
twitter: %(twitter)s
---
{%% extends "base.html" %%}

{%% block main %%}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    <span class="title">{{resource.meta.title}}</span>
    <span class="author">{{resource.meta.author}}</span>
    <span class="twitter">{{resource.meta.twitter}}</span>
{%% endblock %%}
"""
        about2 = File(TEST_SITE.child('content/about2.html'))
        about2.write(text % d)
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin']
        gen = Generator(s)
        gen.generate_all()
        res = s.content.resource_from_path(about2.path)

        assert hasattr(res, 'meta')
        assert hasattr(res.meta, 'title')
        assert hasattr(res.meta, 'author')
        assert hasattr(res.meta, 'twitter')
        assert res.meta.title == "A nice title"
        assert res.meta.author == "Lakshmi Vyas"
        assert res.meta.twitter == "lakshmivyas"
        target = File(Folder(s.config.deploy_root_path).child('about2.html'))
        text = target.read_all()
        q = PyQuery(text)
        for k, v in d.items():
            assert v in q("span." + k).text()

    def test_can_load_from_node_meta(self):
        d = {'title': 'A nice title',
            'author': 'Lakshmi Vyas',
            'twitter': 'lakshmivyas'}
        text = """
===
title: Even nicer title
===
{%% extends "base.html" %%}

{%% block main %%}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    <span class="title">{{resource.meta.title}}</span>
    <span class="author">{{resource.meta.author}}</span>
    <span class="twitter">{{resource.meta.twitter}}</span>
{%% endblock %%}
"""
        about2 = File(TEST_SITE.child('content/about2.html'))
        about2.write(text % d)
        meta = File(TEST_SITE.child('content/meta.yaml'))
        meta.write(yaml.dump(d))
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin']
        gen = Generator(s)
        gen.generate_all()
        res = s.content.resource_from_path(about2.path)
        assert hasattr(res, 'meta')
        assert hasattr(res.meta, 'title')
        assert hasattr(res.meta, 'author')
        assert hasattr(res.meta, 'twitter')
        assert res.meta.title == "Even nicer title"
        assert res.meta.author == "Lakshmi Vyas"
        assert res.meta.twitter == "lakshmivyas"
        target = File(Folder(s.config.deploy_root_path).child('about2.html'))
        text = target.read_all()
        q = PyQuery(text)
        for k, v in d.items():
            if not k == 'title':
                assert v in q("span." + k).text()
        assert q("span.title").text() == "Even nicer title"

    def test_can_load_from_site_meta(self):
        d = {'title': 'A nice title',
            'author': 'Lakshmi Vyas'}
        text = """
---
title: Even nicer title
---
{%% extends "base.html" %%}

{%% block main %%}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    <span class="title">{{resource.meta.title}}</span>
    <span class="author">{{resource.meta.author}}</span>
    <span class="twitter">{{resource.meta.twitter}}</span>
{%% endblock %%}
"""
        about2 = File(TEST_SITE.child('content/about2.html'))
        about2.write(text % d)
        meta = File(TEST_SITE.child('content/nodemeta.yaml'))
        meta.write(yaml.dump(d))
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin']
        s.config.meta = {
            'author': 'Lakshmi',
            'twitter': 'lakshmivyas'
        }
        gen = Generator(s)
        gen.generate_all()
        res = s.content.resource_from_path(about2.path)
        assert hasattr(res, 'meta')
        assert hasattr(res.meta, 'title')
        assert hasattr(res.meta, 'author')
        assert hasattr(res.meta, 'twitter')
        assert res.meta.title == "Even nicer title"
        assert res.meta.author == "Lakshmi Vyas"
        assert res.meta.twitter == "lakshmivyas"
        target = File(Folder(s.config.deploy_root_path).child('about2.html'))
        text = target.read_all()
        q = PyQuery(text)
        for k, v in d.items():
            if not k == 'title':
                assert v in q("span." + k).text()
        assert q("span.title").text() == "Even nicer title"


    def test_multiple_levels(self):

        page_d = {'title': 'An even nicer title'}

        blog_d = {'author': 'Laks'}

        content_d  = {'title': 'A nice title',
                      'author': 'Lakshmi Vyas'}

        site_d = {'author': 'Lakshmi',
                  'twitter': 'lakshmivyas',
                  'nodemeta': 'meta.yaml'}
        text = """
---
title: %(title)s
---
{%% extends "base.html" %%}

{%% block main %%}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    <span class="title">{{resource.meta.title}}</span>
    <span class="author">{{resource.meta.author}}</span>
    <span class="twitter">{{resource.meta.twitter}}</span>
{%% endblock %%}
"""
        about2 = File(TEST_SITE.child('content/blog/about2.html'))
        about2.write(text % page_d)
        content_meta = File(TEST_SITE.child('content/nodemeta.yaml'))
        content_meta.write(yaml.dump(content_d))
        content_meta = File(TEST_SITE.child('content/blog/meta.yaml'))
        content_meta.write(yaml.dump(blog_d))
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin']
        s.config.meta = site_d
        gen = Generator(s)
        gen.generate_all()
        expected = {}

        expected.update(site_d)
        expected.update(content_d)
        expected.update(blog_d)
        expected.update(page_d)

        res = s.content.resource_from_path(about2.path)
        assert hasattr(res, 'meta')
        for k, v in expected.items():
            assert hasattr(res.meta, k)
            assert getattr(res.meta, k) == v
        target = File(Folder(s.config.deploy_root_path).child('blog/about2.html'))
        text = target.read_all()
        q = PyQuery(text)
        for k, v in expected.items():
            if k != 'nodemeta':
                assert v in q("span." + k).text()

########NEW FILE########
__FILENAME__ = test_optipng
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.model import Expando
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File, Folder

OPTIPNG_SOURCE = File(__file__).parent.child_folder('optipng')
TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestOptipng(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        IMAGES = TEST_SITE.child_folder('content/media/images')
        IMAGES.make()
        OPTIPNG_SOURCE.copy_contents_to(IMAGES)


    def tearDown(self):
        TEST_SITE.delete()

    def test_can_execute_optipng(self):
        s = Site(TEST_SITE)
        s.config.mode = "production"
        s.config.plugins = ['hyde.ext.plugins.images.OptiPNGPlugin']
        s.config.optipng = Expando(dict(args=dict(quiet="")))
        source =File(TEST_SITE.child('content/media/images/hyde-lt-b.png'))
        target = File(Folder(s.config.deploy_root_path).child('media/images/hyde-lt-b.png'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)
        assert target.exists
        assert target.size < source.size

########NEW FILE########
__FILENAME__ = test_paginator
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from textwrap import dedent

from hyde.generator import Generator
from hyde.site import Site

from fswrap import File

TEST_SITE = File(__file__).parent.parent.child_folder('_test')

class TestPaginator(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                  'sites/test_paginator').copy_contents_to(TEST_SITE)
        self.s = Site(TEST_SITE)
        self.deploy = TEST_SITE.child_folder('deploy')

        self.gen = Generator(self.s)
        self.gen.load_site_if_needed()
        self.gen.load_template_if_needed()
        self.gen.generate_all()


    def tearDown(self):
        TEST_SITE.delete()


    def test_pages_of_one(self):
        pages = ['pages_of_one.txt', 'page2/pages_of_one.txt',
                    'page3/pages_of_one.txt', 'page4/pages_of_one.txt']
        files = [File(self.deploy.child(p)) for p in pages]
        for f in files:
            assert f.exists

        page5 = File(self.deploy.child('page5/pages_of_one.txt'))
        assert not page5.exists


    def test_pages_of_one_content(self):
        expected_page1_content = dedent('''\
            Another Sad Post

            /page2/pages_of_one.txt''')
        expected_page2_content = dedent('''\
            A Happy Post
            /pages_of_one.txt
            /page3/pages_of_one.txt''')
        expected_page3_content = dedent('''\
            An Angry Post
            /page2/pages_of_one.txt
            /page4/pages_of_one.txt''')
        expected_page4_content = dedent('''\
            A Sad Post
            /page3/pages_of_one.txt
            ''')

        page1 = self.deploy.child('pages_of_one.txt')
        content = File(page1).read_all()
        assert expected_page1_content == content

        page2 = self.deploy.child('page2/pages_of_one.txt')
        content = File(page2).read_all()
        assert expected_page2_content == content

        page3 = self.deploy.child('page3/pages_of_one.txt')
        content = File(page3).read_all()
        assert expected_page3_content == content

        page4 = self.deploy.child('page4/pages_of_one.txt')
        content = File(page4).read_all()
        assert expected_page4_content == content


    def test_pages_of_ten(self):
        page1 = self.deploy.child('pages_of_ten.txt')
        page2 = self.deploy.child('page2/pages_of_ten.txt')

        assert File(page1).exists
        assert not File(page2).exists


    def test_pages_of_ten_depends(self):
        depends = self.gen.deps['pages_of_ten.txt']

        assert depends
        assert len(depends) == 4
        assert 'blog/sad-post.html' in depends
        assert 'blog/another-sad-post.html' in depends
        assert 'blog/angry-post.html' in depends
        assert 'blog/happy-post.html' in depends


    def test_pages_of_ten_content(self):
        expected_content = dedent('''\
            Another Sad Post
            A Happy Post
            An Angry Post
            A Sad Post
            ''')

        page = self.deploy.child('pages_of_ten.txt')
        content = File(page).read_all()
        assert expected_content == content


    def test_pages_of_one_depends(self):
        depends = self.gen.deps['pages_of_one.txt']

        assert depends
        assert len(depends) == 4
        assert 'blog/sad-post.html' in depends
        assert 'blog/another-sad-post.html' in depends
        assert 'blog/angry-post.html' in depends
        assert 'blog/happy-post.html' in depends


    def test_custom_file_pattern(self):
        page1 = self.deploy.child('custom_file_pattern.txt')
        page2 = self.deploy.child('custom_file_pattern-2.txt')

        assert File(page1).exists
        assert File(page2).exists

########NEW FILE########
__FILENAME__ = test_requirejs
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File, Folder

RJS_SOURCE = File(__file__).parent.child_folder('requirejs')
TEST_SITE = File(__file__).parent.parent.child_folder('_test')

class TestRequireJS(object):
    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder('sites/test_jinja').copy_contents_to(TEST_SITE)
        RJS_SOURCE.copy_contents_to(TEST_SITE.child('content/media/js'))
        File(TEST_SITE.child('content/media/js/app.js')).delete()

    def tearDown(self):
        TEST_SITE.delete()

    def test_can_execute_rjs(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.js.RequireJSPlugin']
        source = TEST_SITE.child('content/media/js/rjs.conf')
        target = File(Folder(s.config.deploy_root_path).child('media/js/app.js'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        text = target.read_all()
        expected_text = File(RJS_SOURCE.child('app.js')).read_all()

        assert text == expected_text
        return

########NEW FILE########
__FILENAME__ = test_scss
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site
from hyde.tests.util import assert_no_diff

from fswrap import File, Folder

SCSS_SOURCE = File(__file__).parent.child_folder('scss')
TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestSassyCSS(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        SCSS_SOURCE.copy_contents_to(TEST_SITE.child('content/media/css'))
        File(TEST_SITE.child('content/media/css/site.css')).delete()


    def tearDown(self):
        TEST_SITE.delete()


    def test_scss(self):
        s = Site(TEST_SITE)
        s.config.mode = 'prod'
        s.config.plugins = ['hyde.ext.plugins.css.SassyCSSPlugin']
        source = TEST_SITE.child('content/media/css/site.scss')
        target = File(Folder(s.config.deploy_root_path).child('media/css/site.css'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        text = target.read_all()
        expected_text = File(SCSS_SOURCE.child('expected-site.css')).read_all()
        assert_no_diff(expected_text, text)


########NEW FILE########
__FILENAME__ = test_sorter
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.ext.plugins.meta import MetaPlugin, SorterPlugin
from hyde.generator import Generator
from hyde.site import Site
from hyde.model import Config, Expando

from fswrap import File, Folder
import yaml


TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestSorter(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_walk_resources_sorted(self):
        s = Site(TEST_SITE)
        s.load()
        s.config.plugins = ['hyde.ext.meta.SorterPlugin']
        s.config.sorter = Expando(dict(kind=dict(attr=['source_file.kind', 'name'])))

        SorterPlugin(s).begin_site()

        assert hasattr(s.content, 'walk_resources_sorted_by_kind')
        expected = ["404.html",
                    "about.html",
                    "apple-touch-icon.png",
                    "merry-christmas.html",
                    "crossdomain.xml",
                    "favicon.ico",
                    "robots.txt",
                    "site.css"
                    ]

        pages = [page.name for page in
                s.content.walk_resources_sorted_by_kind()]

        assert pages == sorted(expected, key=lambda f: (File(f).kind, f))

    def test_walk_resources_sorted_reverse(self):
        s = Site(TEST_SITE)
        s.load()
        s.config.plugins = ['hyde.ext.meta.SorterPlugin']
        s.config.sorter = Expando(dict(kind=dict(attr=['source_file.kind', 'name'], reverse=True)))

        SorterPlugin(s).begin_site()

        assert hasattr(s.content, 'walk_resources_sorted_by_kind')
        expected = ["404.html",
                    "about.html",
                    "apple-touch-icon.png",
                    "merry-christmas.html",
                    "crossdomain.xml",
                    "favicon.ico",
                    "robots.txt",
                    "site.css"
                    ]

        pages = [page.name for page in
                s.content.walk_resources_sorted_by_kind()]


        assert pages == sorted(expected, key=lambda f: (File(f).kind, f), reverse=True)

    def test_walk_resources_sorted_with_filters(self):
        s = Site(TEST_SITE)
        cfg = """
        plugins:
            - hyde.ext.meta.SorterPlugin
        sorter:
            kind2:
                filters:
                    source_file.kind: html
        """
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        SorterPlugin(s).begin_site()

        assert hasattr(s.content, 'walk_resources_sorted_by_kind2')
        expected = ["404.html",
                    "about.html",
                    "merry-christmas.html"
                    ]

        pages = [page.name for page in s.content.walk_resources_sorted_by_kind2()]

        assert pages == sorted(expected)

    def test_walk_resources_sorted_with_multiple_attributes(self):
        s = Site(TEST_SITE)
        cfg = """
        plugins:
            - hyde.ext.meta.SorterPlugin
        sorter:
            multi:
                attr:
                    - source_file.kind
                    - node.name
                    - name

        """
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        SorterPlugin(s).begin_site()

        assert hasattr(s.content, 'walk_resources_sorted_by_multi')
        expected = ["content/404.html",
                    "content/about.html",
                    "content/apple-touch-icon.png",
                    "content/blog/2010/december/merry-christmas.html",
                    "content/crossdomain.xml",
                    "content/favicon.ico",
                    "content/robots.txt",
                    "content/site.css"
                    ]

        pages = [page.name for page in s.content.walk_resources_sorted_by_multi()]

        expected_sorted = [File(page).name
                                for page in
                                    sorted(expected,
                                        key=lambda p: tuple(
                                            [File(p).kind,
                                            File(p).parent.name, p]))]
        assert pages == expected_sorted

    def test_walk_resources_sorted_no_default_is_processable(self):
        s = Site(TEST_SITE)
        cfg = """
        plugins:
            - hyde.ext.meta.SorterPlugin
        sorter:
            kind2:
                filters:
                    source_file.kind: html
                attr:
                    - name
        """
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        p_404 = s.content.resource_from_relative_path('404.html')
        p_404.is_processable = False
        SorterPlugin(s).begin_site()

        assert hasattr(s.content, 'walk_resources_sorted_by_kind2')
        expected = ["404.html", "about.html", "merry-christmas.html"]

        pages = [page.name for page in s.content.walk_resources_sorted_by_kind2()]

        assert pages == sorted(expected)

    def test_prev_next(self):
        s = Site(TEST_SITE)
        cfg = """
        plugins:
            - hyde.ext.meta.SorterPlugin
        sorter:
            kind2:
                filters:
                    source_file.kind: html
                attr:
                    - name
        """
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        SorterPlugin(s).begin_site()

        p_404 = s.content.resource_from_relative_path('404.html')
        p_about = s.content.resource_from_relative_path('about.html')
        p_mc = s.content.resource_from_relative_path(
                            'blog/2010/december/merry-christmas.html')

        assert hasattr(p_404, 'prev_by_kind2')
        assert not p_404.prev_by_kind2
        assert hasattr(p_404, 'next_by_kind2')
        assert p_404.next_by_kind2 == p_about

        assert hasattr(p_about, 'prev_by_kind2')
        assert p_about.prev_by_kind2 == p_404
        assert hasattr(p_about, 'next_by_kind2')
        assert p_about.next_by_kind2 == p_mc

        assert hasattr(p_mc, 'prev_by_kind2')
        assert p_mc.prev_by_kind2 == p_about
        assert hasattr(p_mc, 'next_by_kind2')
        assert not p_mc.next_by_kind2

    def test_prev_next_looped(self):
        s = Site(TEST_SITE)
        cfg = """
        plugins:
            - hyde.ext.meta.SorterPlugin
        sorter:
            kind2:
                circular: true
                filters:
                    source_file.kind: html
                attr:
                    - name
        """
        s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
        s.load()
        SorterPlugin(s).begin_site()

        p_404 = s.content.resource_from_relative_path('404.html')
        p_about = s.content.resource_from_relative_path('about.html')
        p_mc = s.content.resource_from_relative_path(
                            'blog/2010/december/merry-christmas.html')

        assert hasattr(p_404, 'prev_by_kind2')
        assert p_404.prev_by_kind2 == p_mc
        assert hasattr(p_404, 'next_by_kind2')
        assert p_404.next_by_kind2 == p_about

        assert hasattr(p_about, 'prev_by_kind2')
        assert p_about.prev_by_kind2 == p_404
        assert hasattr(p_about, 'next_by_kind2')
        assert p_about.next_by_kind2 == p_mc

        assert hasattr(p_mc, 'prev_by_kind2')
        assert p_mc.prev_by_kind2 == p_about
        assert hasattr(p_mc, 'next_by_kind2')
        assert p_mc.next_by_kind2 == p_404

    def test_prev_next_reversed(self):
          s = Site(TEST_SITE)
          cfg = """
          plugins:
              - hyde.ext.meta.SorterPlugin
          sorter:
              folder_name:
                  attr:
                    - node.name
                  reverse: True
                  filters:
                      source_file.kind: html
          """
          s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
          s.load()
          SorterPlugin(s).begin_site()

          p_404 = s.content.resource_from_relative_path('404.html')
          p_about = s.content.resource_from_relative_path('about.html')
          p_mc = s.content.resource_from_relative_path(
                              'blog/2010/december/merry-christmas.html')

          assert hasattr(p_mc, 'prev_by_folder_name')
          assert not p_mc.prev_by_folder_name
          assert hasattr(p_mc, 'next_by_folder_name')
          assert p_mc.next_by_folder_name == p_404

          assert hasattr(p_404, 'prev_by_folder_name')
          assert p_404.prev_by_folder_name == p_mc
          assert hasattr(p_404, 'next_by_folder_name')
          assert p_404.next_by_folder_name == p_about

          assert hasattr(p_about, 'prev_by_folder_name')
          assert p_about.prev_by_folder_name == p_404
          assert hasattr(p_about, 'next_by_folder_name')
          assert not p_about.next_by_folder_name

    def test_walk_resources_sorted_using_generator(self):
           s = Site(TEST_SITE)
           cfg = """
           meta:
               time: !!timestamp 2010-10-23
               title: NahNahNah
           plugins:
               - hyde.ext.plugins.meta.MetaPlugin
               - hyde.ext.plugins.meta.SorterPlugin
           sorter:
               time:
                   attr: meta.time
                   filters:
                       source_file.kind: html
           """
           s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
           text = """
   ---
    time: !!timestamp 2010-12-31
    title: YayYayYay
   ---
   {% extends "base.html" %}

   {% block main %}
       {% set latest = site.content.walk_resources_sorted_by_time()|reverse|first %}
       <span class="latest">{{ latest.meta.title }}</span>
   {% endblock %}
   """

           about2 = File(TEST_SITE.child('content/about2.html'))
           about2.write(text)
           gen = Generator(s)
           gen.generate_all()

           from pyquery import PyQuery
           target = File(Folder(s.config.deploy_root_path).child('about2.html'))
           text = target.read_all()
           q = PyQuery(text)

           assert q('span.latest').text() == 'YayYayYay'

class TestSorterMeta(object):

   def setUp(self):
       TEST_SITE.make()
       TEST_SITE.parent.child_folder(
                   'sites/test_sorter').copy_contents_to(TEST_SITE)

   def tearDown(self):
       TEST_SITE.delete()

   def test_attribute_checker_no_meta(self):
       s = Site(TEST_SITE)
       s.load()
       from hyde.ext.plugins.meta import attributes_checker
       for r in s.content.walk_resources():
           assert not attributes_checker(r, ['meta.index'])

   def test_attribute_checker_with_meta(self):
       s = Site(TEST_SITE)
       s.load()
       MetaPlugin(s).begin_site()
       from hyde.ext.plugins.meta import attributes_checker
       have_index = ["angry-post.html",
                   "another-sad-post.html",
                   "happy-post.html"]
       for r in s.content.walk_resources():
           expected = r.name in have_index
           assert attributes_checker(r, ['meta.index']) == expected


   def test_walk_resources_sorted_by_index(self):
       s = Site(TEST_SITE)
       s.load()
       config = {
        "index": {
            "attr": ['meta.index', 'name']
        }
       }
       s.config.sorter = Expando(config)
       MetaPlugin(s).begin_site()
       SorterPlugin(s).begin_site()

       assert hasattr(s.content, 'walk_resources_sorted_by_index')
       expected = ["angry-post.html",
                   "another-sad-post.html",
                   "happy-post.html"]

       pages = [page.name for page in
               s.content.walk_resources_sorted_by_index()]

       assert pages == sorted(expected, key=lambda f: (File(f).kind, f))

########NEW FILE########
__FILENAME__ = test_stylus
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.model import Expando
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File, Folder

STYLUS_SOURCE = File(__file__).parent.child_folder('stylus')
TEST_SITE = File(__file__).parent.parent.child_folder('_test')

class TestStylus(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        STYLUS_SOURCE.copy_contents_to(TEST_SITE.child('content/media/css'))
        File(TEST_SITE.child('content/media/css/site.css')).delete()


    def tearDown(self):
        TEST_SITE.delete()

    def test_can_execute_stylus(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.css.StylusPlugin']
        paths = ['/usr/local/share/npm/bin/stylus']
        for path in paths:
            if File(path).exists:
                s.config.stylus = Expando(dict(app=path))
        source = TEST_SITE.child('content/media/css/site.styl')
        target = File(Folder(s.config.deploy_root_path).child('media/css/site.css'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        text = target.read_all()
        expected_text = File(STYLUS_SOURCE.child('expected-site.css')).read_all()
        assert text.strip() == expected_text.strip()

    def test_can_compress_with_stylus(self):
        s = Site(TEST_SITE)
        s.config.mode = "production"
        s.config.plugins = ['hyde.ext.plugins.css.StylusPlugin']
        paths = ['/usr/local/share/npm/bin/stylus']
        for path in paths:
            if File(path).exists:
                s.config.stylus = Expando(dict(app=path))
        source = TEST_SITE.child('content/media/css/site.styl')
        target = File(Folder(s.config.deploy_root_path).child('media/css/site.css'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        text = target.read_all()
        expected_text = File(STYLUS_SOURCE.child('expected-site-compressed.css')).read_all()
        assert text.strip() == expected_text.strip()

########NEW FILE########
__FILENAME__ = test_syntext
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File
from pyquery import PyQuery

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestSyntext(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()



    def test_syntext(self):
        text = u"""
~~~~~~~~css~~~~~~~
.body{
    background-color: white;
}
~~~~~~~~~~~~~~~~~~
"""
        site = Site(TEST_SITE)
        site.config.plugins = [
            'hyde.ext.plugins.meta.MetaPlugin',
            'hyde.ext.plugins.text.SyntextPlugin']
        syn = File(site.content.source_folder.child('syn.html'))
        syn.write(text)
        gen = Generator(site)
        gen.generate_all()
        f = File(site.config.deploy_root_path.child(syn.name))
        assert f.exists
        html = f.read_all()
        assert html
        q = PyQuery(html)
        assert q('figure.code').length == 1

########NEW FILE########
__FILENAME__ = test_tagger
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File

TEST_SITE = File(__file__).parent.parent.child_folder('_test')

class TestTagger(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                  'sites/test_tagger').copy_contents_to(TEST_SITE)
        self.s = Site(TEST_SITE)
        self.deploy = TEST_SITE.child_folder('deploy')


    def tearDown(self):
        TEST_SITE.delete()

    def test_tagger_walker(self):
        gen = Generator(self.s)
        gen.load_site_if_needed()
        gen.generate_all()

        assert hasattr(self.s, 'tagger')
        assert hasattr(self.s.tagger, 'tags')
        assert self.s.tagger.tags
        tags = self.s.tagger.tags.to_dict()

        assert len(tags) == 6

        for tag in ['sad', 'happy', 'angry', 'thoughts', 'events']:
            assert tag in tags

        sad_posts = [post.name for post in tags['sad']['resources']]
        assert len(sad_posts) == 2
        assert "sad-post.html" in sad_posts
        assert "another-sad-post.html" in sad_posts
        sad_posts == [post.name for post in
                        self.s.content.walk_resources_tagged_with('sad')]


        happy_posts = [post.name for post in
                        self.s.content.walk_resources_tagged_with('happy')]
        assert len(happy_posts) == 1
        assert "happy-post.html" in happy_posts

        angry_posts = [post.name for post in
                        self.s.content.walk_resources_tagged_with('angry')]
        assert len(angry_posts) == 1
        assert "angry-post.html" in angry_posts

        sad_thought_posts = [post.name for post in
                        self.s.content.walk_resources_tagged_with('sad+thoughts')]
        assert len(sad_thought_posts) == 1
        assert "sad-post.html" in sad_thought_posts

    def test_tagger_archives_generated(self):
        gen = Generator(self.s)
        gen.load_site_if_needed()
        gen.load_template_if_needed()
        gen.generate_all()
        tags_folder = self.deploy.child_folder('blog/tags')

        assert tags_folder.exists
        tags = ['sad', 'happy', 'angry', 'thoughts', 'events']

        archives = (File(tags_folder.child("%s.html" % tag)) for tag in tags)

        for archive in archives:
            assert archive.exists

        from pyquery import PyQuery

        q = PyQuery(File(tags_folder.child('sad.html')).read_all())
        assert q

        assert q('li').length == 2
        assert q('li:nth-child(1) a').attr('href') == '/blog/another-sad-post.html'
        assert q('li:nth-child(2) a').attr('href') == '/blog/sad-post.html'

        q = PyQuery(File(tags_folder.child('happy.html')).read_all())
        assert q

        assert q('li').length == 1
        assert q('li a:first-child').attr('href') == '/blog/happy-post.html'

        q = PyQuery(File(tags_folder.child('angry.html')).read_all())
        assert q

        assert q('li').length == 1
        assert q('li a:first-child').attr('href') == '/blog/angry-post.html'

        q = PyQuery(File(tags_folder.child('thoughts.html')).read_all())
        assert q

        assert q('li').length == 3
        assert q('li:nth-child(1) a').attr('href') == '/blog/happy-post.html'
        assert q('li:nth-child(2) a').attr('href') == '/blog/angry-post.html'
        assert q('li:nth-child(3) a').attr('href') == '/blog/sad-post.html'

        q = PyQuery(File(tags_folder.child('events.html')).read_all())
        assert q

        assert q('li').length == 1
        assert q('li a:first-child').attr('href') == '/blog/another-sad-post.html'

    def test_tagger_metadata(self):
        conf = {
            "tagger":{
                "tags": {
                    "sad" : {
                        "emotions": ["Dissappointed", "Lost"]
                    },
                    "angry": {
                        "emotions": ["Irritated", "Annoyed", "Disgusted"]
                    }
                }
            }
        }
        s = Site(TEST_SITE)
        s.config.update(conf)
        gen = Generator(s)
        gen.load_site_if_needed()
        gen.generate_all()

        assert hasattr(s, 'tagger')
        assert hasattr(s.tagger, 'tags')
        assert s.tagger.tags
        tags = s.tagger.tags
        sad_tag = tags.sad
        assert hasattr(sad_tag, "emotions")

        assert sad_tag.emotions == s.config.tagger.tags.sad.emotions

        assert hasattr(tags, "angry")
        angry_tag = tags.angry
        assert angry_tag
        assert hasattr(angry_tag, "emotions")
        assert angry_tag.emotions == s.config.tagger.tags.angry.emotions

        for tagname in ['happy', 'thoughts', 'events']:
            tag = getattr(tags, tagname)
            assert tag
            assert not hasattr(tag, "emotions")

    def test_tagger_sorted(self):
        conf = {
           "tagger":{
               "sorter": "time",
               "archives": {
                    "blog": {
                        "template": "emotions.j2",
                        "source": "blog",
                        "target": "blog/tags",
                        "extension": "html",
                        "meta": {
                            "author": "Tagger Plugin"
                        }
                    }
               },
               "tags": {
                   "sad" : {
                       "emotions": ["Dissappointed", "Lost"]
                   },
                   "angry": {
                       "emotions": ["Irritated", "Annoyed", "Disgusted"]
                   }
               }
           }
        }

        text = """
<div id="author">{{ resource.meta.author }}</div>
<h1>Posts tagged: {{ tag }} in {{ node.name|title }}</h1>
Emotions:
<ul>
{% for emotion in tag.emotions %}
<li class="emotion">
{{ emotion }}
</li>
{% endfor %}
<ul>
{% for resource in walker() -%}
<li>
<a href="{{ content_url(resource.url) }}">{{ resource.meta.title }}</a>
</li>
{%- endfor %}
</ul>
"""
        template = File(TEST_SITE.child('layout/emotions.j2'))
        template.write(text)
        s = Site(TEST_SITE)
        s.config.update(conf)
        gen = Generator(s)
        gen.load_site_if_needed()
        gen.generate_all()

        tags_folder = self.deploy.child_folder('blog/tags')
        assert tags_folder.exists
        tags = ['sad', 'happy', 'angry', 'thoughts', 'events']
        archives = dict((tag, File(tags_folder.child("%s.html" % tag))) for tag in tags)

        for tag, archive in archives.items():
            assert archive.exists

        from pyquery import PyQuery

        q = PyQuery(archives['sad'].read_all())
        assert len(q("li.emotion")) == 2
        assert q("#author").text() == "Tagger Plugin"

        q = PyQuery(archives['angry'].read_all())
        assert len(q("li.emotion")) == 3

        for tag, archive in archives.items():
            if tag not in ["sad", "angry"]:
                q = PyQuery(archives[tag].read_all())
                assert not len(q("li.emotion"))

########NEW FILE########
__FILENAME__ = test_textlinks
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.site import Site
from urllib import quote

from fswrap import File

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestTextlinks(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()



    def test_textlinks(self):
        d = {
            'objects': 'template/variables',
            'plugins': 'plugins/metadata',
            'sorter': 'plugins/sorter'
        }
        text = u"""
{%% markdown %%}
[[!!img/hyde-logo.png]]
*   [Rich object model][hyde objects] and
    [overridable hierarchical metadata]([[ %(plugins)s ]]) thats available for use in
    templates.
*   Configurable [sorting][], filtering and grouping support.

[hyde objects]: [[ %(objects)s ]]
[sorting]: [[%(sorter)s]]
{%% endmarkdown %%}
"""
        site = Site(TEST_SITE)
        site.config.plugins = ['hyde.ext.plugins.text.TextlinksPlugin']
        site.config.base_url = 'http://example.com/'
        site.config.media_url = '/media'
        tlink = File(site.content.source_folder.child('tlink.html'))
        tlink.write(text % d)
        print tlink.read_all()
        gen = Generator(site)
        gen.generate_all()
        f = File(site.config.deploy_root_path.child(tlink.name))
        assert f.exists
        html = f.read_all()
        assert html
        for name, path in d.items():

            assert site.config.base_url +  quote(path) in html
        assert '/media/img/hyde-logo.png' in html

########NEW FILE########
__FILENAME__ = test_uglify
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.model import Expando
from hyde.generator import Generator
from hyde.site import Site

from fswrap import File, Folder
from hyde.tests.util import assert_no_diff

UGLIFY_SOURCE = File(__file__).parent.child_folder('uglify')
TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestUglify(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)
        JS = TEST_SITE.child_folder('content/media/js')
        JS.make()
        UGLIFY_SOURCE.copy_contents_to(JS)


    def tearDown(self):
        TEST_SITE.delete()

    def test_can_uglify(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.js.UglifyPlugin']
        s.config.mode = "production"
        source = TEST_SITE.child('content/media/js/jquery.js')
        target = File(Folder(s.config.deploy_root_path).child('media/js/jquery.js'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        expected = UGLIFY_SOURCE.child_file('expected-jquery.js').read_all()
        # TODO: Very fragile. Better comparison needed.
        text = target.read_all()
        assert_no_diff(expected, text)

    def test_uglify_with_extra_options(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.js.UglifyPlugin']
        s.config.mode = "production"
        s.config.uglify = Expando(dict(args={"comments":"/http\:\/\/jquery.org\/license/"}))
        source = TEST_SITE.child('content/media/js/jquery.js')
        target = File(Folder(s.config.deploy_root_path).child('media/js/jquery.js'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        expected = UGLIFY_SOURCE.child_file('expected-jquery-nc.js').read_all()
        # TODO: Very fragile. Better comparison needed.
        text = target.read_all()
        assert_no_diff(expected, text)

    def test_no_uglify_in_dev_mode(self):
        s = Site(TEST_SITE)
        s.config.plugins = ['hyde.ext.plugins.js.UglifyPlugin']
        s.config.mode = "dev"
        source = TEST_SITE.child('content/media/js/jquery.js')
        target = File(Folder(s.config.deploy_root_path).child('media/js/jquery.js'))
        gen = Generator(s)
        gen.generate_resource_at_path(source)

        assert target.exists
        expected = UGLIFY_SOURCE.child_file('jquery.js').read_all()
        # TODO: Very fragile. Better comparison needed.
        text = target.read_all()
        assert_no_diff(expected, text)



########NEW FILE########
__FILENAME__ = test_urlcleaner
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.generator import Generator
from hyde.model import Config
from hyde.site import Site

from fswrap import File, Folder
import yaml

TEST_SITE = File(__file__).parent.parent.child_folder('_test')


class TestUrlCleaner(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder(
                    'sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_url_cleaner(self):
           s = Site(TEST_SITE)
           cfg = """
           plugins:
                - hyde.ext.plugins.urls.UrlCleanerPlugin
           urlcleaner:
                index_file_names:
                    - about.html
                strip_extensions:
                    - html
                append_slash: true
           """
           s.config = Config(TEST_SITE, config_dict=yaml.load(cfg))
           text = """
   {% extends "base.html" %}

   {% block main %}
   <a id="index" href="{{ content_url('about.html') }}"></a>
   <a id="blog" href="{{ content_url('blog/2010/december/merry-christmas.html') }}"></a>
   {% endblock %}
   """

           about2 = File(TEST_SITE.child('content/test.html'))
           about2.write(text)
           gen = Generator(s)
           gen.generate_all()

           from pyquery import PyQuery
           target = File(Folder(s.config.deploy_root_path).child('test.html'))
           text = target.read_all()
           q = PyQuery(text)
           assert q('a#index').attr("href") == '/'
           assert q('a#blog').attr("href") == '/blog/2010/december/merry-christmas'
########NEW FILE########
__FILENAME__ = banner
from hyde.plugin import Plugin


class BannerPlugin(Plugin):
	"""
	Adds a comment banner to all generated html files
	"""

	def text_resource_complete(self, resource, text):
		banner = """
<!--
This file was produced with infinite love, care & sweat.
Please dont copy. If you have to, please drop me a note.
-->
"""
		if resource.source.kind == "html":
			text = banner + text
		return text
########NEW FILE########
__FILENAME__ = test_generate
 # -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""

from hyde.generator import Generator
from hyde.model import Config
from hyde.site import Site

from pyquery import PyQuery

from fswrap import File, Folder

TEST_SITE = File(__file__).parent.child_folder('_test')

class TestGenerator(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder('sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_generate_resource_from_path(self):
        site = Site(TEST_SITE)
        site.load()
        gen = Generator(site)
        gen.generate_resource_at_path(TEST_SITE.child('content/about.html'))
        about = File(Folder(site.config.deploy_root_path).child('about.html'))
        assert about.exists
        text = about.read_all()
        q = PyQuery(text)
        assert about.name in q("div#main").text()

    def test_generate_resource_from_path_with_is_processable_false(self):
        site = Site(TEST_SITE)
        site.load()
        resource = site.content.resource_from_path(TEST_SITE.child('content/about.html'))
        resource.is_processable = False
        gen = Generator(site)
        gen.generate_resource_at_path(TEST_SITE.child('content/about.html'))
        about = File(Folder(site.config.deploy_root_path).child('about.html'))
        assert not about.exists

    def test_generate_resource_from_path_with_uses_template_false(self):
        site = Site(TEST_SITE)
        site.load()
        resource = site.content.resource_from_path(TEST_SITE.child('content/about.html'))
        resource.uses_template = False
        gen = Generator(site)
        gen.generate_resource_at_path(TEST_SITE.child('content/about.html'))
        about = File(Folder(site.config.deploy_root_path).child('about.html'))
        assert about.exists
        text = about.read_all()
        expected = resource.source_file.read_all()
        assert text == expected

    def test_generate_resource_from_path_with_deploy_override(self):
        site = Site(TEST_SITE)
        site.load()
        resource = site.content.resource_from_path(TEST_SITE.child('content/about.html'))
        resource.relative_deploy_path = 'about/index.html'
        gen = Generator(site)
        gen.generate_resource_at_path(TEST_SITE.child('content/about.html'))
        about = File(Folder(site.config.deploy_root_path).child('about/index.html'))
        assert about.exists
        text = about.read_all()
        q = PyQuery(text)
        assert resource.name in q("div#main").text()

    def test_has_resource_changed(self):
        site = Site(TEST_SITE)
        site.load()
        resource = site.content.resource_from_path(TEST_SITE.child('content/about.html'))
        gen = Generator(site)
        gen.generate_all()
        import time
        time.sleep(1)
        assert not gen.has_resource_changed(resource)
        text = resource.source_file.read_all()
        resource.source_file.write(text)
        assert gen.has_resource_changed(resource)
        gen.generate_all()
        assert not gen.has_resource_changed(resource)
        time.sleep(1)
        l = File(TEST_SITE.child('layout/root.html'))
        l.write(l.read_all())
        assert gen.has_resource_changed(resource)

    def test_context(self):
        site = Site(TEST_SITE, Config(TEST_SITE, config_dict={
            "context": {
                "data": {
                    "abc": "def"
                }
            }
        }))
        text = """
{% extends "base.html" %}

{% block main %}
    abc = {{ abc }}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    {{resource.name}}
{% endblock %}
"""
        site.load()
        resource = site.content.resource_from_path(TEST_SITE.child('content/about.html'))
        gen = Generator(site)
        resource.source_file.write(text)
        gen.generate_all()
        target = File(site.config.deploy_root_path.child(resource.name))
        assert "abc = def" in target.read_all()

    def test_context_providers(self):
        site = Site(TEST_SITE, Config(TEST_SITE, config_dict={
            "context": {
                "data": {
                    "abc": "def"
                },
                "providers": {
                    "nav": "nav.yaml"
                }
            }
        }))
        nav = """
- home
- articles
- projects
"""
        text = """
{% extends "base.html" %}

{% block main %}
    {{nav}}
    {% for item in nav %}
    {{item}}
    {% endfor %}
    abc = {{ abc }}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    {{resource.name}}
{% endblock %}
"""
        File(TEST_SITE.child('nav.yaml')).write(nav)
        site.load()
        resource = site.content.resource_from_path(TEST_SITE.child('content/about.html'))
        gen = Generator(site)
        resource.source_file.write(text)
        gen.generate_all()
        target = File(site.config.deploy_root_path.child(resource.name))
        out = target.read_all()
        assert "abc = def" in out
        assert "home" in out
        assert "articles" in out
        assert "projects" in out

    def test_context_providers_no_data(self):
        site = Site(TEST_SITE, Config(TEST_SITE, config_dict={
            "context": {
                "providers": {
                    "nav": "nav.yaml"
                }
            }
        }))
        nav = """
main:
    - home
    - articles
    - projects
"""
        text = """
{% extends "base.html" %}

{% block main %}
    {{nav}}
    {% for item in nav.main %}
    {{item}}
    {% endfor %}
    abc = {{ abc }}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    {{resource.name}}
{% endblock %}
"""
        File(TEST_SITE.child('nav.yaml')).write(nav)
        site.load()
        resource = site.content.resource_from_path(TEST_SITE.child('content/about.html'))
        gen = Generator(site)
        resource.source_file.write(text)
        gen.generate_all()
        target = File(site.config.deploy_root_path.child(resource.name))
        out = target.read_all()
        assert "home" in out
        assert "articles" in out
        assert "projects" in out

    def test_context_providers_equivalence(self):
        import yaml
        events = """
    2011:
        -
            title: "one event"
            location: "a city"
        -
            title: "one event"
            location: "a city"

    2010:
        -
            title: "one event"
            location: "a city"
        -
            title: "one event"
            location: "a city"
"""
        events_dict = yaml.load(events)
        config_dict = dict(context=dict(
            data=dict(events1=events_dict),
            providers=dict(events2="events.yaml")
        ))
        text = """
{%% extends "base.html" %%}

{%% block main %%}
    <ul>
    {%% for year, eventlist in %s %%}
        <li>
            <h1>{{ year }}</h1>
            <ul>
                {%% for event in eventlist %%}
                <li>{{ event.title }}-{{ event.location }}</li>
                {%% endfor %%}
            </ul>
        </li>
    {%% endfor %%}
    </ul>
{%% endblock %%}
"""

        File(TEST_SITE.child('events.yaml')).write(events)
        f1 = File(TEST_SITE.child('content/text1.html'))
        f2 = File(TEST_SITE.child('content/text2.html'))
        f1.write(text % "events1")
        f2.write(text % "events2")
        site = Site(TEST_SITE, Config(TEST_SITE, config_dict=config_dict))
        site.load()
        gen = Generator(site)
        gen.generate_all()
        left = File(site.config.deploy_root_path.child(f1.name)).read_all()
        right = File(site.config.deploy_root_path.child(f2.name)).read_all()
        assert left == right


########NEW FILE########
__FILENAME__ = test_initialize
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""


from hyde.engine import Engine
from hyde.exceptions import HydeException
from hyde.layout import Layout

from fswrap import File, Folder
from nose.tools import raises, with_setup, nottest

TEST_SITE = File(__file__).parent.child_folder('_test')
TEST_SITE_AT_USER = Folder('~/_test')

@nottest
def create_test_site():
    TEST_SITE.make()

@nottest
def delete_test_site():
    TEST_SITE.delete()

@nottest
def create_test_site_at_user():
    TEST_SITE_AT_USER.make()

@nottest
def delete_test_site_at_user():
    TEST_SITE_AT_USER.delete()

@raises(HydeException)
@with_setup(create_test_site, delete_test_site)
def test_ensure_exception_when_site_yaml_exists():
    e = Engine(raise_exceptions=True)
    File(TEST_SITE.child('site.yaml')).write("Hey")
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create']))

@raises(HydeException)
@with_setup(create_test_site, delete_test_site)
def test_ensure_exception_when_content_folder_exists():
    e = Engine(raise_exceptions=True)
    TEST_SITE.child_folder('content').make()
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create']))

@raises(HydeException)
@with_setup(create_test_site, delete_test_site)
def test_ensure_exception_when_layout_folder_exists():
    e = Engine(raise_exceptions=True)
    TEST_SITE.child_folder('layout').make()
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create']))

@with_setup(create_test_site, delete_test_site)
def test_ensure_no_exception_when_empty_site_exists():
    e = Engine(raise_exceptions=True)
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create']))
    verify_site_contents(TEST_SITE, Layout.find_layout())

@with_setup(create_test_site, delete_test_site)
def test_ensure_no_exception_when_forced():
    e = Engine(raise_exceptions=True)
    TEST_SITE.child_folder('layout').make()
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create', '-f']))
    verify_site_contents(TEST_SITE, Layout.find_layout())
    TEST_SITE.delete()
    TEST_SITE.child_folder('content').make()
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create', '-f']))
    verify_site_contents(TEST_SITE, Layout.find_layout())
    TEST_SITE.delete()
    TEST_SITE.make()
    File(TEST_SITE.child('site.yaml')).write("Hey")
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create', '-f']))
    verify_site_contents(TEST_SITE, Layout.find_layout())

@with_setup(create_test_site, delete_test_site)
def test_ensure_no_exception_when_sitepath_does_not_exist():
    e = Engine(raise_exceptions=True)
    TEST_SITE.delete()
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create', '-f']))
    verify_site_contents(TEST_SITE, Layout.find_layout())

@with_setup(create_test_site_at_user, delete_test_site_at_user)
def test_ensure_can_create_site_at_user():
    e = Engine(raise_exceptions=True)
    TEST_SITE_AT_USER.delete()
    e.run(e.parse(['-s', unicode(TEST_SITE_AT_USER), 'create', '-f']))
    verify_site_contents(TEST_SITE_AT_USER, Layout.find_layout())

@nottest
def verify_site_contents(site, layout):
    assert site.exists
    assert site.child_folder('layout').exists
    assert File(site.child('info.yaml')).exists

    expected = map(lambda f: f.get_relative_path(layout), layout.walker.walk_all())
    actual = map(lambda f: f.get_relative_path(site), site.walker.walk_all())
    assert actual
    assert expected

    expected.sort()
    actual.sort()
    assert actual == expected

@raises(HydeException)
@with_setup(create_test_site, delete_test_site)
def test_ensure_exception_when_layout_is_invalid():
    e = Engine(raise_exceptions=True)
    e.run(e.parse(['-s', unicode(TEST_SITE), 'create', '-l', 'junk']))


########NEW FILE########
__FILENAME__ = test_jinja2template
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`

Some code borrowed from rwbench.py from the jinja2 examples
"""
from datetime import datetime
from random import choice, randrange

from hyde.ext.templates.jinja import Jinja2Template
from hyde.site import Site
from hyde.generator import Generator
from hyde.model import Config

from fswrap import File
from jinja2.utils import generate_lorem_ipsum
from nose.tools import nottest
from pyquery import PyQuery

import yaml

ROOT = File(__file__).parent
JINJA2 = ROOT.child_folder('templates/jinja2')

class Article(object):

    def __init__(self, id):
        self.id = id
        self.href = '/article/%d' % self.id
        self.title = generate_lorem_ipsum(1, False, 5, 10)
        self.user = choice(users)
        self.body = generate_lorem_ipsum()
        self.pub_date = datetime.utcfromtimestamp(
                            randrange(10 ** 9, 2 * 10 ** 9))
        self.published = True

def dateformat(x):
    return x.strftime('%Y-%m-%d')

class User(object):

    def __init__(self, username):
        self.href = '/user/%s' % username
        self.username = username


users = map(User, [u'John Doe', u'Jane Doe', u'Peter Somewhat'])
articles = map(Article, range(20))
navigation = [
    ('index',           'Index'),
    ('about',           'About'),
    ('foo?bar=1',       'Foo with Bar'),
    ('foo?bar=2&s=x',   'Foo with X'),
    ('blah',            'Blub Blah'),
    ('hehe',            'Haha'),
] * 5

context = dict(users=users, articles=articles, page_navigation=navigation)

def test_render():
    """
    Uses pyquery to test the html structure for validity
    """
    t = Jinja2Template(JINJA2.path)
    t.configure(None)
    t.env.filters['dateformat'] = dateformat
    source = File(JINJA2.child('index.html')).read_all()

    html = t.render(source, context)
    actual = PyQuery(html)
    assert actual(".navigation li").length == 30
    assert actual("div.article").length == 20
    assert actual("div.article h2").length == 20
    assert actual("div.article h2 a").length == 20
    assert actual("div.article p.meta").length == 20
    assert actual("div.article div.text").length == 20

def test_typogrify():
    source = """
    {%filter typogrify%}
    One & two
    {%endfilter%}
    """
    t = Jinja2Template(JINJA2.path)
    t.configure(None)
    t.env.filters['dateformat'] = dateformat
    html = t.render(source, {}).strip()
    assert html == u'One <span class="amp">&amp;</span>&nbsp;two'

def test_spaceless():
    source = """
    {%spaceless%}
    <html>
        <body>
            <ul>
                <li>
                    One
                </li>
                <li>
                    Two
                </li>
                <li>
                    Three
                </li>
            </ul>
        </body>
    </html>
    {%endspaceless%}
    """
    t = Jinja2Template(JINJA2.path)
    t.configure(None)
    t.env.filters['dateformat'] = dateformat
    html = t.render(source, {}).strip()
    expected = u"""
<html><body><ul><li>
                    One
                </li><li>
                    Two
                </li><li>
                    Three
                </li></ul></body></html>
"""
    assert html.strip() == expected.strip()

def test_asciidoc():
    source = """
    {%asciidoc%}
    == Heading 2 ==

    * test1
    * test2
    * test3
    {%endasciidoc%}
    """
    t = Jinja2Template(JINJA2.path)
    t.configure(None)
    html = t.render(source, {}).strip()

    assert html
    q = PyQuery(html)
    assert q
    assert q("li").length == 3
    assert q("li:nth-child(1)").text().strip() == "test1"
    assert q("li:nth-child(2)").text().strip() == "test2"
    assert q("li:nth-child(3)").text().strip() == "test3"

def test_markdown():
    source = """
    {%markdown%}
    ### Heading 3
    {%endmarkdown%}
    """
    t = Jinja2Template(JINJA2.path)
    t.configure(None)
    html = t.render(source, {}).strip()
    assert html == u'<h3>Heading 3</h3>'

def test_restructuredtext():
    source = """
{% restructuredtext %}
Hello
=====
{% endrestructuredtext %}
    """
    t = Jinja2Template(JINJA2.path)
    t.configure(None)
    html = t.render(source, {}).strip()
    assert html == u"""<div class="document" id="hello">
<h1 class="title">Hello</h1>
</div>""", html

def test_restructuredtext_with_sourcecode():
    source = """
{% restructuredtext %}
Code
====
.. sourcecode:: python

    def add(a, b):
        return a + b

See `Example`_

.. _Example: example.html

{% endrestructuredtext %}
"""

    expected = """
<div class="document" id="code">
<h1 class="title">Code</h1>
<div class="highlight"><pre><span class="k">def</span> <span class="nf">add</span><span class="p">(</span><span class="n">a</span><span class="p">,</span> <span class="n">b</span><span class="p">):</span>
    <span class="k">return</span> <span class="n">a</span> <span class="o">+</span> <span class="n">b</span>
</pre></div>
<p>See <a class="reference external" href="example.html">Example</a></p>
</div>
"""
    t = Jinja2Template(JINJA2.path)
    s = Site(JINJA2.path)
    c = Config(JINJA2.path, config_dict=dict(
                    restructuredtext=dict(highlight_source=True)))
    s.config = c
    t.configure(s)
    html = t.render(source, {}).strip()
    assert html.strip() == expected.strip()

def test_markdown_with_extensions():
    source = """
    {%markdown%}
    ### Heading 3

    {%endmarkdown%}
    """
    t = Jinja2Template(JINJA2.path)
    s = Site(JINJA2.path)
    c = Config(JINJA2.path, config_dict=dict(markdown=dict(extensions=['headerid'])))
    s.config = c
    t.configure(s)
    t.env.filters['dateformat'] = dateformat
    html = t.render(source, {}).strip()
    assert html == u'<h3 id="heading-3">Heading 3</h3>'

def test_markdown_with_sourcecode():
    source = """
{%markdown%}
# Code

    :::python
    def add(a, b):
        return a + b

See [Example][]
[Example]: example.html

{%endmarkdown%}
"""

    expected = """
    <h1>Code</h1>
<div class="codehilite"><pre><span class="k">def</span> <span class="nf">add</span><span class="p">(</span><span class="n">a</span><span class="p">,</span> <span class="n">b</span><span class="p">):</span>
    <span class="k">return</span> <span class="n">a</span> <span class="o">+</span> <span class="n">b</span>
</pre></div>


<p>See <a href="example.html">Example</a></p>
    """
    t = Jinja2Template(JINJA2.path)
    s = Site(JINJA2.path)
    c = Config(JINJA2.path, config_dict=dict(
                    markdown=dict(extensions=['codehilite'])))
    s.config = c
    t.configure(s)
    html = t.render(source, {}).strip()
    assert html.strip() == expected.strip()


def test_line_statements():
    source = """
    $$$ markdown
    ### Heading 3

    $$$ endmarkdown
    """
    t = Jinja2Template(JINJA2.path)
    s = Site(JINJA2.path)
    c = Config(JINJA2.path, config_dict=dict(markdown=dict(extensions=['headerid'])))
    s.config = c
    t.configure(s)
    t.env.filters['dateformat'] = dateformat
    html = t.render(source, {}).strip()
    assert html == u'<h3 id="heading-3">Heading 3</h3>'

def test_line_statements_with_config():
    source = """
    %% markdown
    ### Heading 3

    %% endmarkdown
    """
    config = """
    markdown:
        extensions:
            - headerid
    jinja2:
        line_statement_prefix: '%%'

    """
    t = Jinja2Template(JINJA2.path)
    s = Site(JINJA2.path)
    s.config = Config(JINJA2.path, config_dict=yaml.load(config))
    t.configure(s)
    t.env.filters['dateformat'] = dateformat
    html = t.render(source, {}).strip()
    assert html == u'<h3 id="heading-3">Heading 3</h3>'


TEST_SITE = File(__file__).parent.child_folder('_test')

@nottest
def assert_markdown_typogrify_processed_well(include_text, includer_text):
    site = Site(TEST_SITE)
    site.config.plugins = ['hyde.ext.plugins.meta.MetaPlugin']
    inc = File(TEST_SITE.child('content/inc.md'))
    inc.write(include_text)
    site.load()
    gen = Generator(site)
    gen.load_template_if_needed()
    template = gen.template
    html = template.render(includer_text, {}).strip()
    assert html
    q = PyQuery(html)
    assert "is_processable" not in html
    assert "This is a" in q("h1").text()
    assert "heading" in q("h1").text()
    assert q(".amp").length == 1
    return html

class TestJinjaTemplate(object):

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder('sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_depends(self):
        t = Jinja2Template(JINJA2.path)
        t.configure(None)
        t.env.filters['dateformat'] = dateformat
        deps = list(t.get_dependencies('index.html'))
        assert len(deps) == 2

        assert 'helpers.html' in deps
        assert 'layout.html' in deps

    def test_depends_multi_level(self):
        site = Site(TEST_SITE)
        JINJA2.copy_contents_to(site.content.source)
        inc = File(TEST_SITE.child('content/inc.md'))
        inc.write("{% extends 'index.html' %}")
        site.load()
        gen = Generator(site)
        gen.load_template_if_needed()
        t = gen.template
        deps = list(t.get_dependencies('inc.md'))

        assert len(deps) == 3

        assert 'helpers.html' in deps
        assert 'layout.html' in deps
        assert 'index.html' in deps

    def test_line_statements_with_blocks(self):
        site = Site(TEST_SITE)
        JINJA2.copy_contents_to(site.content.source)
        text = """
        {% extends 'index.html' %}
        $$$ block body
        <div id="article">Heya</div>
        $$$ endblock
        """
        site.load()
        gen = Generator(site)
        gen.load_template_if_needed()
        template = gen.template
        template.env.filters['dateformat'] = dateformat
        html = template.render(text, {}).strip()

        assert html
        q = PyQuery(html)
        article = q("#article")
        assert article.length == 1
        assert article.text() == "Heya"


    def test_depends_with_reference_tag(self):
        site = Site(TEST_SITE)
        JINJA2.copy_contents_to(site.content.source)
        inc = File(TEST_SITE.child('content/inc.md'))
        inc.write("{% refer to 'index.html' as index%}")
        site.load()
        gen = Generator(site)
        gen.load_template_if_needed()
        t = gen.template
        deps = list(t.get_dependencies('inc.md'))

        assert len(deps) == 3

        assert 'helpers.html' in deps
        assert 'layout.html' in deps
        assert 'index.html' in deps

    def test_cant_find_depends_with_reference_tag_var(self):
        site = Site(TEST_SITE)
        JINJA2.copy_contents_to(site.content.source)
        inc = File(TEST_SITE.child('content/inc.md'))
        inc.write("{% set ind = 'index.html' %}{% refer to ind as index %}")
        site.load()
        gen = Generator(site)
        gen.load_template_if_needed()
        t = gen.template
        deps = list(t.get_dependencies('inc.md'))

        assert len(deps) == 1

        assert not deps[0]


    def test_can_include_templates_with_processing(self):
        text = """
===
is_processable: False
===

{% filter typogrify %}{% markdown %}
This is a heading
=================

Hyde & Jinja.

{% endmarkdown %}{% endfilter %}
"""


        text2 = """{% include "inc.md"  %}"""
        assert_markdown_typogrify_processed_well(text, text2)


    def test_includetext(self):
        text = """
===
is_processable: False
===

This is a heading
=================

Hyde & Jinja.

"""

        text2 = """{% includetext "inc.md"  %}"""
        assert_markdown_typogrify_processed_well(text, text2)

    def test_reference_is_noop(self):
        text = """
===
is_processable: False
===

{% mark heading %}
This is a heading
=================
{% endmark %}
{% reference content %}
Hyde & Jinja.
{% endreference %}

"""

        text2 = """{% includetext "inc.md"  %}"""
        html = assert_markdown_typogrify_processed_well(text, text2)
        assert "mark" not in html
        assert "reference" not in html

    def test_reference_is_not_callable(self):
        text = """
===
is_processable: False
===

{% mark heading %}
This is a heading
=================
{% endmark %}
{% reference content %}
Hyde & Jinja.
{% endreference %}

{% mark repeated %}
<span class="junk">Junk</span>
{% endmark %}

{{ self.repeated() }}
{{ self.repeated }}

"""

        text2 = """{% includetext "inc.md"  %}"""
        html = assert_markdown_typogrify_processed_well(text, text2)
        assert "mark" not in html
        assert "reference" not in html
        q = PyQuery(html)
        assert q("span.junk").length == 1

    def test_refer(self):
        text = """
===
is_processable: False
===
{% filter markdown|typogrify %}
{% mark heading %}
This is a heading
=================
{% endmark %}
{% reference content %}
Hyde & Jinja.
{% endreference %}
{% endfilter %}
"""

        text2 = """
{% refer to "inc.md" as inc %}
{% filter markdown|typogrify %}
{{ inc.heading }}
{{ inc.content }}
{% endfilter %}
"""
        html = assert_markdown_typogrify_processed_well(text, text2)
        assert "mark" not in html
        assert "reference" not in html

    def test_refer_with_full_html(self):
        text = """
===
is_processable: False
===
<div class="fulltext">
{% filter markdown|typogrify %}
{% mark heading %}
This is a heading
=================
{% endmark %}
{% reference content %}
Hyde & Jinja.
{% endreference %}
{% endfilter %}
</div>
"""

        text2 = """
{% refer to "inc.md" as inc %}
{{ inc.html('.fulltext') }}
"""
        html = assert_markdown_typogrify_processed_well(text, text2)
        assert "mark" not in html
        assert "reference" not in html

    def test_two_level_refer_with_var(self):
        text = """
===
is_processable: False
===
<div class="fulltext">
{% filter markdown|typogrify %}
{% mark heading %}
This is a heading
=================
{% endmark %}
{% reference content %}
Hyde & Jinja.
{% endreference %}
{% endfilter %}
</div>
"""

        text2 = """
{% set super = 'super.md' %}
{% refer to super as sup %}
<div class="justhead">
{% mark child %}
{{ sup.heading }}
{% endmark %}
{% mark cont %}
{{ sup.content }}
{% endmark %}
</div>
"""
        text3 = """
{% set incu = 'inc.md' %}
{% refer to incu as inc %}
{% filter markdown|typogrify %}
{{ inc.child }}
{{ inc.cont }}
{% endfilter %}
"""

        superinc = File(TEST_SITE.child('content/super.md'))
        superinc.write(text)

        html = assert_markdown_typogrify_processed_well(text2, text3)
        assert "mark" not in html
        assert "reference" not in html


    def test_refer_with_var(self):
        text = """
===
is_processable: False
===
<div class="fulltext">
{% filter markdown|typogrify %}
{% mark heading %}
This is a heading
=================
{% endmark %}
{% reference content %}
Hyde & Jinja.
{% endreference %}
{% endfilter %}
</div>
"""

        text2 = """
{% set incu = 'inc.md' %}
{% refer to incu as inc %}
{{ inc.html('.fulltext') }}
"""
        html = assert_markdown_typogrify_processed_well(text, text2)
        assert "mark" not in html
        assert "reference" not in html


    def test_yaml_tag(self):

        text = """
{% yaml test %}
one:
    - A
    - B
    - C
two:
    - D
    - E
    - F
{% endyaml %}
{% for section, values in test.items() %}
<ul class="{{ section }}">
    {% for value in values %}
    <li>{{ value }}</li>
    {% endfor %}
</ul>
{% endfor %}
"""
        t = Jinja2Template(JINJA2.path)
        t.configure(None)
        t.env.filters['dateformat'] = dateformat
        html = t.render(text, {}).strip()
        actual = PyQuery(html)
        assert actual("ul").length == 2
        assert actual("ul.one").length == 1
        assert actual("ul.two").length == 1

        assert actual("li").length == 6

        assert actual("ul.one li").length == 3
        assert actual("ul.two li").length == 3

        ones = [item.text for item in actual("ul.one li")]
        assert ones == ["A", "B", "C"]

        twos = [item.text for item in actual("ul.two li")]
        assert twos == ["D", "E", "F"]

    def test_top_filter(self):

        text = """
{% yaml test %}
item_list:
    - A
    - B
    - C
    - D
    - E
    - F
{% endyaml %}
<ul class="top">
{% for value in test.item_list|top(3) %}
    <li>{{ value }}</li>
{% endfor %}
</ul>
<ul class="mid">
{% for value in test.item_list|islice(3, 6) %}
    <li>{{ value }}</li>
{% endfor %}
</ul>
"""
        t = Jinja2Template(JINJA2.path)
        t.configure(None)
        t.env.filters['dateformat'] = dateformat
        html = t.render(text, {}).strip()
        actual = PyQuery(html)
        assert actual("ul").length == 2
        assert actual("li").length == 6
        items = [item.text for item in actual("ul.top li")]
        assert items == ["A", "B", "C"]
        items = [item.text for item in actual("ul.mid li")]
        assert items == ["D", "E", "F"]

    def test_raw_tag(self):
        expected = """
<div class="template secondary">
<aside class="secondary">
  <ul>
    {{#sections}}
      <li><a href="#{{id}}">{{textContent}}</a></li>
    {{/sections}}
  </ul>
</aside>
"""
        text = "{%% raw %%}%s{%% endraw %%}" % expected
        t = Jinja2Template(JINJA2.path)
        t.configure(None)
        html = t.render(text, {}).strip()
        assert html.strip() == expected.strip()

    def test_raw_tag_with_markdown_typogrify(self):
        expected = """
<div class="template secondary">
<aside class="secondary">
  <ul>
    {{#sections}}
      <li><a href="#{{id}}">{{textContent}}</a></li>
    {{/sections}}
  </ul>
</aside>
"""
        text = "{%% filter markdown|typogrify %%}{%% raw %%}%s{%% endraw %%}{%% endfilter %%}" % expected
        t = Jinja2Template(JINJA2.path)
        t.configure(None)
        html = t.render(text, {}).strip()
        assert html.strip() == expected.strip()

    def test_urlencode_filter(self):
        text= u"""
<a href="{{ 'фотография.jpg'|urlencode }}">фотография</a>
<a href="{{ 'http://localhost:8080/"abc.jpg'|urlencode }}">quoted</a>
"""
        expected = u"""
<a href="%D1%84%D0%BE%D1%82%D0%BE%D0%B3%D1%80%D0%B0%D1%84%D0%B8%D1%8F.jpg">фотография</a>
<a href="http%3A//localhost%3A8080/%22abc.jpg">quoted</a>
"""
        t = Jinja2Template(JINJA2.path)
        t.configure(None)
        html = t.render(text, {}).strip()
        assert html.strip() == expected.strip()

    def test_urldecode_filter(self):
        text= u"""
<a href="{{ 'фотография.jpg'|urlencode }}">{{ "%D1%84%D0%BE%D1%82%D0%BE%D0%B3%D1%80%D0%B0%D1%84%D0%B8%D1%8F.jpg"|urldecode }}</a>
"""
        expected = u"""
<a href="%D1%84%D0%BE%D1%82%D0%BE%D0%B3%D1%80%D0%B0%D1%84%D0%B8%D1%8F.jpg">фотография.jpg</a>
"""
        t = Jinja2Template(JINJA2.path)
        t.configure(None)
        html = t.render(text, {}).strip()
        assert html.strip() == expected.strip()
########NEW FILE########
__FILENAME__ = test_layout
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
import os

from hyde.layout import Layout, HYDE_DATA, LAYOUTS

from fswrap import File
from nose.tools import nottest, with_setup

DATA_ROOT = File(__file__).parent.child_folder('data')
LAYOUT_ROOT = DATA_ROOT.child_folder(LAYOUTS)

@nottest
def setup_data():
    DATA_ROOT.make()

@nottest
def cleanup_data():
    DATA_ROOT.delete()

def test_find_layout_from_package_dir():
    f = Layout.find_layout()
    assert f.name == 'basic'
    assert f.child_folder('layout').exists

@with_setup(setup_data, cleanup_data)
def test_find_layout_from_env_var():
    f = Layout.find_layout()
    LAYOUT_ROOT.make()
    f.copy_to(LAYOUT_ROOT)
    os.environ[HYDE_DATA] = unicode(DATA_ROOT)
    f = Layout.find_layout()
    assert f.parent == LAYOUT_ROOT
    assert f.name == 'basic'
    assert f.child_folder('layout').exists
    del os.environ[HYDE_DATA]

########NEW FILE########
__FILENAME__ = test_model
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
from hyde.model import Config, Expando

from fswrap import File, Folder

def test_expando_one_level():
    d = {"a": 123, "b": "abc"}
    x = Expando(d)
    assert x.a == d['a']
    assert x.b == d['b']

def test_expando_two_levels():
    d = {"a": 123, "b": {"c": 456}}
    x = Expando(d)
    assert x.a == d['a']
    assert x.b.c == d['b']['c']

def test_expando_three_levels():
    d = {"a": 123, "b": {"c": 456, "d": {"e": "abc"}}}
    x = Expando(d)
    assert x.a == d['a']
    assert x.b.c == d['b']['c']
    assert x.b.d.e == d['b']['d']['e']

def test_expando_update():
    d1 = {"a": 123, "b": "abc"}
    x = Expando(d1)
    assert x.a == d1['a']
    assert x.b == d1['b']
    d = {"b": {"c": 456, "d": {"e": "abc"}}, "f": "lmn"}
    x.update(d)
    assert  x.a == d1['a']
    assert x.b.c == d['b']['c']
    assert x.b.d.e == d['b']['d']['e']
    assert x.f == d["f"]
    d2 = {"a": 789, "f": "opq"}
    y = Expando(d2)
    x.update(y)
    assert x.a == 789
    assert x.f == "opq"

def test_expando_to_dict():
    d = {"a": 123, "b": {"c": 456, "d": {"e": "abc"}}}
    x = Expando(d)
    assert d == x.to_dict()

def test_expando_to_dict_with_update():
    d1 = {"a": 123, "b": "abc"}
    x = Expando(d1)
    d = {"b": {"c": 456, "d": {"e": "abc"}}, "f": "lmn"}
    x.update(d)
    expected = {}
    expected.update(d1)
    expected.update(d)
    assert expected == x.to_dict()
    d2 = {"a": 789, "f": "opq"}
    y = Expando(d2)
    x.update(y)
    expected.update(d2)
    assert expected == x.to_dict()

TEST_SITE = File(__file__).parent.child_folder('_test')

import yaml
class TestConfig(object):

    @classmethod
    def setup_class(cls):
        cls.conf1 = """
        mode: development
        content_root: stuff # Relative path from site root
        media_root: media # Relative path from site root
        media_url: /media
        widgets:
        plugins:
        aggregators:
        """

        cls.conf2 = """
        mode: development
        deploy_root: ~/deploy_site
        content_root: site/stuff # Relative path from site root
        media_root: mmm # Relative path from site root
        media_url: /media
        widgets:
        plugins:
        aggregators:
        """

    def setUp(self):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder('sites/test_jinja').copy_contents_to(TEST_SITE)

    def tearDown(self):
        TEST_SITE.delete()

    def test_default_configuration(self):
        c = Config(sitepath=TEST_SITE, config_dict={})
        for root in ['content', 'layout']:
            name = root + '_root'
            path = name + '_path'
            assert hasattr(c, name)
            assert getattr(c, name) == root
            assert hasattr(c, path)
            assert getattr(c, path) == TEST_SITE.child_folder(root)
        assert c.media_root_path == c.content_root_path.child_folder('media')
        assert hasattr(c, 'plugins')
        assert len(c.plugins) == 0
        assert hasattr(c, 'ignore')
        assert c.ignore == ["*~", "*.bak", ".hg", ".git", ".svn"]
        assert c.deploy_root_path == TEST_SITE.child_folder('deploy')
        assert c.not_found == '404.html'
        assert c.meta.nodemeta == 'meta.yaml'

    def test_conf1(self):
        c = Config(sitepath=TEST_SITE, config_dict=yaml.load(self.conf1))
        assert c.content_root_path == TEST_SITE.child_folder('stuff')

    def test_conf2(self):
        c = Config(sitepath=TEST_SITE, config_dict=yaml.load(self.conf2))
        assert c.content_root_path == TEST_SITE.child_folder('site/stuff')
        assert c.media_root_path == c.content_root_path.child_folder('mmm')
        assert c.media_url == TEST_SITE.child_folder('/media')
        assert c.deploy_root_path == Folder('~/deploy_site')

    def test_read_from_file_by_default(self):
        File(TEST_SITE.child('site.yaml')).write(self.conf2)
        c = Config(sitepath=TEST_SITE)
        assert c.content_root_path == TEST_SITE.child_folder('site/stuff')
        assert c.media_root_path == c.content_root_path.child_folder('mmm')
        assert c.media_url == TEST_SITE.child_folder('/media')
        assert c.deploy_root_path == Folder('~/deploy_site')

    def test_read_from_specified_file(self):
        File(TEST_SITE.child('another.yaml')).write(self.conf2)
        c = Config(sitepath=TEST_SITE, config_file='another.yaml')
        assert c.content_root_path == TEST_SITE.child_folder('site/stuff')
        assert c.media_root_path == c.content_root_path.child_folder('mmm')
        assert c.media_url == TEST_SITE.child_folder('/media')
        assert c.deploy_root_path == Folder('~/deploy_site')

    def test_extends(self):
        another = """
        extends: site.yaml
        mode: production
        media_root: xxx
        """
        File(TEST_SITE.child('site.yaml')).write(self.conf2)
        File(TEST_SITE.child('another.yaml')).write(another)
        c = Config(sitepath=TEST_SITE, config_file='another.yaml')
        assert c.mode == 'production'
        assert c.content_root_path == TEST_SITE.child_folder('site/stuff')
        assert c.media_root_path == c.content_root_path.child_folder('xxx')
        assert c.media_url == TEST_SITE.child_folder('/media')
        assert c.deploy_root_path == Folder('~/deploy_site')

########NEW FILE########
__FILENAME__ = test_plugin
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""

from hyde.generator import Generator
from hyde.plugin import Plugin
from hyde.site import Site
from hyde.model import Expando

from mock import patch, Mock

from fswrap import File, Folder

TEST_SITE = File(__file__).parent.child_folder('_test')

class PluginLoaderStub(Plugin):
    pass

class NoReturnPlugin(Plugin):

    def begin_text_resource(self, resource, text):
        print "NoReturnPlugin"
        return None

class ConstantReturnPlugin(Plugin):

    def begin_text_resource(self, resource, text):
        print "ConstantReturnPlugin"
        return "Jam"


class TestPlugins(object):

    @classmethod
    def setup_class(cls):
        TEST_SITE.make()
        TEST_SITE.parent.child_folder('sites/test_jinja').copy_contents_to(TEST_SITE)
        folders = []
        text_files = []
        binary_files = []

        with TEST_SITE.child_folder('content').walker as walker:
            @walker.folder_visitor
            def visit_folder(folder):
                folders.append(folder.path)

            @walker.file_visitor
            def visit_file(afile):
                if not afile.is_text:
                    binary_files.append(afile.path)
                else:
                    text_files.append(afile.path)

        cls.content_nodes = sorted(folders)
        cls.content_text_resources = sorted(text_files)
        cls.content_binary_resources = sorted(binary_files)


    @classmethod
    def teardown_class(cls):
        TEST_SITE.delete()

    def setUp(self):
         self.site = Site(TEST_SITE)
         self.site.config.plugins = ['hyde.tests.test_plugin.PluginLoaderStub']

    def test_can_load_plugin_modules(self):
        assert not len(self.site.plugins)
        Plugin.load_all(self.site)

        assert len(self.site.plugins) == 1
        assert self.site.plugins[0].__class__.__name__ == 'PluginLoaderStub'


    def test_generator_loads_plugins(self):
        gen = Generator(self.site)
        assert len(self.site.plugins) == 1

    def test_generator_template_registered_called(self):
        with patch.object(PluginLoaderStub, 'template_loaded') as template_loaded_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert template_loaded_stub.call_count == 1

    def test_generator_template_begin_generation_called(self):
        with patch.object(PluginLoaderStub, 'begin_generation') as begin_generation_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert begin_generation_stub.call_count == 1

    def test_generator_template_begin_generation_called_for_single_resource(self):
        with patch.object(PluginLoaderStub, 'begin_generation') as begin_generation_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder.child('about.html')
            gen.generate_resource_at_path(path)

            assert begin_generation_stub.call_count == 1

    def test_generator_template_begin_generation_called_for_single_node(self):
        with patch.object(PluginLoaderStub, 'begin_generation') as begin_generation_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder
            gen.generate_node_at_path(path)
            assert begin_generation_stub.call_count == 1


    def test_generator_template_generation_complete_called(self):
        with patch.object(PluginLoaderStub, 'generation_complete') as generation_complete_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert generation_complete_stub.call_count == 1

    def test_generator_template_generation_complete_called_for_single_resource(self):
        with patch.object(PluginLoaderStub, 'generation_complete') as generation_complete_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder.child('about.html')
            gen.generate_resource_at_path(path)

            assert generation_complete_stub.call_count == 1

    def test_generator_template_generation_complete_called_for_single_node(self):
        with patch.object(PluginLoaderStub, 'generation_complete') as generation_complete_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder
            gen.generate_node_at_path(path)
            assert generation_complete_stub.call_count == 1

    def test_generator_template_begin_site_called(self):
        with patch.object(PluginLoaderStub, 'begin_site') as begin_site_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert begin_site_stub.call_count == 1

    def test_generator_template_begin_site_called_for_single_resource(self):
        with patch.object(PluginLoaderStub, 'begin_site') as begin_site_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder.child('about.html')
            gen.generate_resource_at_path(path)
            assert begin_site_stub.call_count == 1

    def test_generator_template_begin_site_not_called_for_single_resource_second_time(self):
        with patch.object(PluginLoaderStub, 'begin_site') as begin_site_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert begin_site_stub.call_count == 1
            path = self.site.content.source_folder.child('about.html')
            gen.generate_resource_at_path(path)
            assert begin_site_stub.call_count == 1

    def test_generator_template_begin_site_called_for_single_node(self):
        with patch.object(PluginLoaderStub, 'begin_site') as begin_site_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder
            gen.generate_node_at_path(path)

            assert begin_site_stub.call_count == 1

    def test_generator_template_begin_site_not_called_for_single_node_second_time(self):
        with patch.object(PluginLoaderStub, 'begin_site') as begin_site_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert begin_site_stub.call_count == 1
            path = self.site.content.source_folder
            gen.generate_node_at_path(path)

            assert begin_site_stub.call_count == 1

    def test_generator_template_site_complete_called(self):
        with patch.object(PluginLoaderStub, 'site_complete') as site_complete_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert site_complete_stub.call_count == 1


    def test_generator_template_site_complete_called_for_single_resource(self):

        with patch.object(PluginLoaderStub, 'site_complete') as site_complete_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder.child('about.html')
            gen.generate_resource_at_path(path)

            assert site_complete_stub.call_count == 1

    def test_generator_template_site_complete_not_called_for_single_resource_second_time(self):

        with patch.object(PluginLoaderStub, 'site_complete') as site_complete_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert site_complete_stub.call_count == 1
            path = self.site.content.source_folder.child('about.html')
            gen.generate_resource_at_path(path)

            assert site_complete_stub.call_count == 1

    def test_generator_template_site_complete_called_for_single_node(self):

        with patch.object(PluginLoaderStub, 'site_complete') as site_complete_stub:
            gen = Generator(self.site)
            path = self.site.content.source_folder
            gen.generate_node_at_path(path)

            assert site_complete_stub.call_count == 1

    def test_generator_template_site_complete_not_called_for_single_node_second_time(self):

        with patch.object(PluginLoaderStub, 'site_complete') as site_complete_stub:
            gen = Generator(self.site)
            gen.generate_all()
            path = self.site.content.source_folder
            gen.generate_node_at_path(path)

            assert site_complete_stub.call_count == 1

    def test_generator_template_begin_node_called(self):

        with patch.object(PluginLoaderStub, 'begin_node') as begin_node_stub:
            gen = Generator(self.site)
            gen.generate_all()

            assert begin_node_stub.call_count == len(self.content_nodes)
            called_with_nodes = sorted([arg[0][0].path for arg in begin_node_stub.call_args_list])
            assert called_with_nodes == self.content_nodes

    def test_generator_template_begin_node_called_for_single_resource(self):

        with patch.object(PluginLoaderStub, 'begin_node') as begin_node_stub:
            gen = Generator(self.site)
            gen.generate_resource_at_path(self.site.content.source_folder.child('about.html'))
            assert begin_node_stub.call_count == len(self.content_nodes)


    def test_generator_template_begin_node_not_called_for_single_resource_second_time(self):

        with patch.object(PluginLoaderStub, 'begin_node') as begin_node_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert begin_node_stub.call_count == len(self.content_nodes)
            gen.generate_resource_at_path(self.site.content.source_folder.child('about.html'))
            assert begin_node_stub.call_count == len(self.content_nodes) # No extra calls


    def test_generator_template_node_complete_called(self):

        with patch.object(PluginLoaderStub, 'node_complete') as node_complete_stub:
            gen = Generator(self.site)
            gen.generate_all()

            assert node_complete_stub.call_count == len(self.content_nodes)
            called_with_nodes = sorted([arg[0][0].path for arg in node_complete_stub.call_args_list])
            assert called_with_nodes == self.content_nodes

    def test_generator_template_node_complete_called_for_single_resource(self):

        with patch.object(PluginLoaderStub, 'node_complete') as node_complete_stub:
            gen = Generator(self.site)
            gen.generate_resource_at_path(self.site.content.source_folder.child('about.html'))
            assert node_complete_stub.call_count == len(self.content_nodes)

    def test_generator_template_node_complete_not_called_for_single_resource_second_time(self):

        with patch.object(PluginLoaderStub, 'node_complete') as node_complete_stub:
            gen = Generator(self.site)
            gen.generate_all()
            assert node_complete_stub.call_count == len(self.content_nodes)
            gen.generate_resource_at_path(self.site.content.source_folder.child('about.html'))
            assert node_complete_stub.call_count == len(self.content_nodes) # No extra calls

    def test_generator_template_begin_text_resource_called(self):

        with patch.object(PluginLoaderStub, 'begin_text_resource') as begin_text_resource_stub:
            begin_text_resource_stub.reset_mock()
            begin_text_resource_stub.return_value = ''
            gen = Generator(self.site)
            gen.generate_all()

            called_with_resources = sorted([arg[0][0].path for arg in begin_text_resource_stub.call_args_list])
            assert set(called_with_resources) == set(self.content_text_resources)

    def test_generator_template_begin_text_resource_called_for_single_resource(self):

        with patch.object(PluginLoaderStub, 'begin_text_resource') as begin_text_resource_stub:
            begin_text_resource_stub.return_value = ''
            gen = Generator(self.site)
            gen.generate_all()
            begin_text_resource_stub.reset_mock()
            path = self.site.content.source_folder.child('about.html')
            gen = Generator(self.site)
            gen.generate_resource_at_path(path, incremental=True)

            called_with_resources = sorted([arg[0][0].path for arg in begin_text_resource_stub.call_args_list])
            assert begin_text_resource_stub.call_count == 1
            assert called_with_resources[0] == path

    def test_generator_template_begin_binary_resource_called(self):

        with patch.object(PluginLoaderStub, 'begin_binary_resource') as begin_binary_resource_stub:
            gen = Generator(self.site)
            gen.generate_all()

            called_with_resources = sorted([arg[0][0].path for arg in begin_binary_resource_stub.call_args_list])
            assert begin_binary_resource_stub.call_count == len(self.content_binary_resources)
            assert called_with_resources == self.content_binary_resources

    def test_generator_template_begin_binary_resource_called_for_single_resource(self):

        with patch.object(PluginLoaderStub, 'begin_binary_resource') as begin_binary_resource_stub:
            gen = Generator(self.site)
            gen.generate_all()
            begin_binary_resource_stub.reset_mock()
            path = self.site.content.source_folder.child('favicon.ico')
            gen.generate_resource_at_path(path)

            called_with_resources = sorted([arg[0][0].path for arg in begin_binary_resource_stub.call_args_list])
            assert begin_binary_resource_stub.call_count == 1
            assert called_with_resources[0] == path

    def test_plugin_chaining(self):
         self.site.config.plugins = [
            'hyde.tests.test_plugin.ConstantReturnPlugin',
            'hyde.tests.test_plugin.NoReturnPlugin'
         ]
         path = self.site.content.source_folder.child('about.html')
         gen = Generator(self.site)
         gen.generate_resource_at_path(path)
         about = File(Folder(
                    self.site.config.deploy_root_path).child('about.html'))
         assert about.read_all() == "Jam"

    def test_plugin_filters_begin_text_resource(self):
        def empty_return(self, resource, text=''):
            return text
        with patch.object(ConstantReturnPlugin, 'begin_text_resource', new=Mock(wraps=empty_return)) as mock1:
            with patch.object(NoReturnPlugin, 'begin_text_resource', new=Mock(wraps=empty_return)) as mock2:
                self.site.config.plugins = [
                    'hyde.tests.test_plugin.ConstantReturnPlugin',
                    'hyde.tests.test_plugin.NoReturnPlugin'
                 ]
                self.site.config.constantreturn = Expando(dict(include_file_pattern="*.css"))
                self.site.config.noreturn = Expando(dict(include_file_pattern=["*.html", "*.txt"]))
                gen = Generator(self.site)
                gen.generate_all()
                mock1_args = sorted(set([arg[0][0].name for arg in mock1.call_args_list]))
                mock2_args = sorted(set([arg[0][0].name for arg in mock2.call_args_list]))
                assert len(mock1_args) == 1
                assert len(mock2_args) == 4
                assert mock1_args == ["site.css"]
                assert mock2_args == ["404.html", "about.html", "merry-christmas.html", "robots.txt"]

    def test_plugin_node_filters_begin_text_resource(self):
        def empty_return(*args, **kwargs):
            return None
        with patch.object(ConstantReturnPlugin, 'begin_text_resource', new=Mock(wraps=empty_return)) as mock1:
            with patch.object(NoReturnPlugin, 'begin_text_resource', new=Mock(wraps=empty_return)) as mock2:
                self.site.config.plugins = [
                    'hyde.tests.test_plugin.ConstantReturnPlugin',
                    'hyde.tests.test_plugin.NoReturnPlugin'
                 ]
                self.site.config.constantreturn = Expando(dict(include_paths="media"))
                self.site.config.noreturn = Expando(dict(include_file_pattern="*.html", include_paths=["blog"]))
                gen = Generator(self.site)
                gen.generate_all()
                mock1_args = sorted(set([arg[0][0].name for arg in mock1.call_args_list]))
                mock2_args = sorted(set([arg[0][0].name for arg in mock2.call_args_list]))
                assert len(mock1_args) == 1
                assert len(mock2_args) == 1
                assert mock1_args == ["site.css"]
                assert mock2_args == ["merry-christmas.html"]
########NEW FILE########
__FILENAME__ = test_simple_copy
# -*- coding: utf-8 -*-
"""
Tests the simple copy feature.

In order to mark some files to simply be copied to the
destination without any processing what so ever add this
to the config (site.yaml for example):
simple_copy:
    - media/css/*.css
    - media/js/*.js
    - **/*.js

Matching is done with `fnmatch` module. So any `glob` that fnmatch
can process is a valid pattern.

Use nose
`$ pip install nose`
`$ nosetests`
"""
import yaml

from hyde.model import Config
from hyde.site import Site
from hyde.generator import Generator

from fswrap import File
from nose.tools import nottest


TEST_SITE_ROOT = File(__file__).parent.child_folder('sites/test_jinja')

class TestSimpleCopy(object):
    @classmethod
    def setup_class(cls):
        cls.SITE_PATH =  File(__file__).parent.child_folder('sites/test_jinja_with_config')
        cls.SITE_PATH.make()
        TEST_SITE_ROOT.copy_contents_to(cls.SITE_PATH)

    @classmethod
    def teardown_class(cls):
        cls.SITE_PATH.delete()

    @nottest
    def setup_config(self, passthru):
        self.config_file = File(self.SITE_PATH.child('site.yaml'))
        with open(self.config_file.path) as config:
            conf = yaml.load(config)
            conf['simple_copy'] = passthru
            self.config = Config(sitepath=self.SITE_PATH, config_dict=conf)

    def test_simple_copy_basic(self):
        self.setup_config([
            'about.html'
        ])
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        res = s.content.resource_from_relative_path('about.html')
        assert res
        assert res.simple_copy

    def test_simple_copy_directory(self):
        self.setup_config([
            '**/*.html'
        ])
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        res = s.content.resource_from_relative_path('about.html')
        assert res
        assert not res.simple_copy
        res = s.content.resource_from_relative_path('blog/2010/december/merry-christmas.html')
        assert res
        assert res.simple_copy

    def test_simple_copy_multiple(self):
        self.setup_config([
            '**/*.html',
            'media/css/*.css'
        ])
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        res = s.content.resource_from_relative_path('about.html')
        assert res
        assert not res.simple_copy
        res = s.content.resource_from_relative_path('blog/2010/december/merry-christmas.html')
        assert res
        assert res.simple_copy
        res = s.content.resource_from_relative_path('media/css/site.css')
        assert res
        assert res.simple_copy

    def test_generator(self):
        self.setup_config([
            '**/*.html',
            'media/css/*.css'
        ])
        s = Site(self.SITE_PATH, self.config)
        g = Generator(s)
        g.generate_all()
        source = s.content.resource_from_relative_path('blog/2010/december/merry-christmas.html')
        target = File(s.config.deploy_root_path.child(source.relative_deploy_path))
        left = source.source_file.read_all()
        right = target.read_all()
        assert left == right

    def test_plugins(self):

        text = """
---
title: Hey
author: Me
twitter: @me
---
{%% extends "base.html" %%}

{%% block main %%}
    Hi!

    I am a test template to make sure jinja2 generation works well with hyde.
    <span class="title">{{resource.meta.title}}</span>
    <span class="author">{{resource.meta.author}}</span>
    <span class="twitter">{{resource.meta.twitter}}</span>
{%% endblock %%}
"""
        index = File(self.SITE_PATH.child('content/blog/index.html'))
        index.write(text)
        self.setup_config([
            '**/*.html',
            'media/css/*.css'
        ])
        conf = {'plugins': ['hyde.ext.plugins.meta.MetaPlugin']}
        conf.update(self.config.to_dict())
        s = Site(self.SITE_PATH, Config(sitepath=self.SITE_PATH, config_dict=conf))
        g = Generator(s)
        g.generate_all()
        source = s.content.resource_from_relative_path('blog/index.html')
        target = File(s.config.deploy_root_path.child(source.relative_deploy_path))
        left = source.source_file.read_all()
        right = target.read_all()
        assert left == right
########NEW FILE########
__FILENAME__ = test_site
# -*- coding: utf-8 -*-
"""
Use nose
`$ pip install nose`
`$ nosetests`
"""
import yaml
from urllib import quote

from hyde.model import Config
from hyde.site import Node, RootNode, Site

from fswrap import File, Folder

TEST_SITE_ROOT = File(__file__).parent.child_folder('sites/test_jinja')

def test_node_site():
    s = Site(TEST_SITE_ROOT)
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    assert r.site == s
    n = Node(r.source_folder.child_folder('blog'), r)
    assert n.site == s

def test_node_root():
    s = Site(TEST_SITE_ROOT)
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    assert r.root == r
    n = Node(r.source_folder.child_folder('blog'), r)
    assert n.root == r

def test_node_parent():
    s = Site(TEST_SITE_ROOT)
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    c = r.add_node(TEST_SITE_ROOT.child_folder('content/blog/2010/december'))
    assert c.parent == r.node_from_relative_path('blog/2010')

def test_node_module():
    s = Site(TEST_SITE_ROOT)
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    assert not r.module
    n = r.add_node(TEST_SITE_ROOT.child_folder('content/blog'))
    assert n.module == n
    c = r.add_node(TEST_SITE_ROOT.child_folder('content/blog/2010/december'))
    assert c.module == n

def test_node_url():
    s = Site(TEST_SITE_ROOT)
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    assert not r.module
    n = r.add_node(TEST_SITE_ROOT.child_folder('content/blog'))
    assert n.url == '/' + n.relative_path
    assert n.url == '/blog'
    c = r.add_node(TEST_SITE_ROOT.child_folder('content/blog/2010/december'))
    assert c.url == '/' + c.relative_path
    assert c.url == '/blog/2010/december'

def test_node_full_url():
    s = Site(TEST_SITE_ROOT)
    s.config.base_url = 'http://localhost'
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    assert not r.module
    n = r.add_node(TEST_SITE_ROOT.child_folder('content/blog'))
    assert n.full_url == 'http://localhost/blog'
    c = r.add_node(TEST_SITE_ROOT.child_folder('content/blog/2010/december'))
    assert c.full_url == 'http://localhost/blog/2010/december'

def test_node_full_url_quoted():
    s = Site(TEST_SITE_ROOT)
    s.config.base_url = 'http://localhost'
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    assert not r.module
    n = r.add_node(TEST_SITE_ROOT.child_folder('content/blo~g'))
    assert n.full_url == 'http://localhost/' + quote('blo~g')
    c = r.add_node(TEST_SITE_ROOT.child_folder('content/blo~g/2010/december'))
    assert c.full_url == 'http://localhost/' + quote('blo~g/2010/december')

def test_node_relative_path():
    s = Site(TEST_SITE_ROOT)
    r = RootNode(TEST_SITE_ROOT.child_folder('content'), s)
    assert not r.module
    n = r.add_node(TEST_SITE_ROOT.child_folder('content/blog'))
    assert n.relative_path == 'blog'
    c = r.add_node(TEST_SITE_ROOT.child_folder('content/blog/2010/december'))
    assert c.relative_path == 'blog/2010/december'

def test_load():
    s = Site(TEST_SITE_ROOT)
    s.load()
    path = 'blog/2010/december'
    node = s.content.node_from_relative_path(path)
    assert node
    assert Folder(node.relative_path) == Folder(path)
    path += '/merry-christmas.html'
    resource = s.content.resource_from_relative_path(path)
    assert resource
    assert resource.relative_path == path
    assert not s.content.resource_from_relative_path('/happy-festivus.html')

def test_walk_resources():
    s = Site(TEST_SITE_ROOT)
    s.load()
    pages = [page.name for page in s.content.walk_resources()]
    expected = ["404.html",
                "about.html",
                "apple-touch-icon.png",
                "merry-christmas.html",
                "crossdomain.xml",
                "favicon.ico",
                "robots.txt",
                "site.css"
                ]
    pages.sort()
    expected.sort()
    assert pages == expected

def test_contains_resource():
    s = Site(TEST_SITE_ROOT)
    s.load()
    path = 'blog/2010/december'
    node = s.content.node_from_relative_path(path)
    assert node.contains_resource('merry-christmas.html')

def test_get_resource():
    s = Site(TEST_SITE_ROOT)
    s.load()
    path = 'blog/2010/december'
    node = s.content.node_from_relative_path(path)
    resource = node.get_resource('merry-christmas.html')
    assert resource == s.content.resource_from_relative_path(Folder(path).child('merry-christmas.html'))

def test_resource_slug():
    s = Site(TEST_SITE_ROOT)
    s.load()
    path = 'blog/2010/december'
    node = s.content.node_from_relative_path(path)
    resource = node.get_resource('merry-christmas.html')
    assert resource.slug == 'merry-christmas'


def test_get_resource_from_relative_deploy_path():
    s = Site(TEST_SITE_ROOT)
    s.load()
    path = 'blog/2010/december'
    node = s.content.node_from_relative_path(path)
    resource = node.get_resource('merry-christmas.html')
    assert resource == s.content.resource_from_relative_deploy_path(Folder(path).child('merry-christmas.html'))
    resource.relative_deploy_path = Folder(path).child('merry-christmas.php')
    assert resource == s.content.resource_from_relative_deploy_path(Folder(path).child('merry-christmas.php'))

def test_is_processable_default_true():
    s = Site(TEST_SITE_ROOT)
    s.load()
    for page in s.content.walk_resources():
        assert page.is_processable

def test_relative_deploy_path():
    s = Site(TEST_SITE_ROOT)
    s.load()
    for page in s.content.walk_resources():
        assert page.relative_deploy_path == Folder(page.relative_path)
        assert page.url == '/' + page.relative_deploy_path

def test_relative_deploy_path_override():
    s = Site(TEST_SITE_ROOT)
    s.load()
    res = s.content.resource_from_relative_path('blog/2010/december/merry-christmas.html')
    res.relative_deploy_path = 'blog/2010/december/happy-holidays.html'
    for page in s.content.walk_resources():
        if res.source_file == page.source_file:
            assert page.relative_deploy_path == 'blog/2010/december/happy-holidays.html'
        else:
            assert page.relative_deploy_path == Folder(page.relative_path)

class TestSiteWithConfig(object):

    @classmethod
    def setup_class(cls):
        cls.SITE_PATH =  File(__file__).parent.child_folder('sites/test_jinja_with_config')
        cls.SITE_PATH.make()
        TEST_SITE_ROOT.copy_contents_to(cls.SITE_PATH)
        cls.config_file = File(cls.SITE_PATH.child('alternate.yaml'))
        with open(cls.config_file.path) as config:
            cls.config = Config(sitepath=cls.SITE_PATH, config_dict=yaml.load(config))
        cls.SITE_PATH.child_folder('content').rename_to(cls.config.content_root)

    @classmethod
    def teardown_class(cls):
        cls.SITE_PATH.delete()

    def test_load_with_config(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = 'blog/2010/december'
        node = s.content.node_from_relative_path(path)
        assert node
        assert Folder(node.relative_path) == Folder(path)
        path += '/merry-christmas.html'
        resource = s.content.resource_from_relative_path(path)
        assert resource
        assert resource.relative_path == path
        assert not s.content.resource_from_relative_path('/happy-festivus.html')

    def test_content_url(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = 'blog/2010/december'
        assert s.content_url(path) == "/" + path

    def test_content_url_encoding(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = '".jpg'
        assert s.content_url(path) == "/" + quote(path)

    def test_content_url_encoding_safe(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = '".jpg/abc'
        print s.content_url(path, "")
        print "/"  + quote(path, "")
        assert s.content_url(path, "") == "/" + quote(path, "")

    def test_media_url(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = 'css/site.css'
        assert s.media_url(path) == "/media/" + path

    def test_is_media(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        assert s.is_media('media/css/site.css')

        s.config.media_root = 'monkey'
        assert not s.is_media('media/css/site.css')
        assert s.is_media('monkey/css/site.css')

    def test_full_url_for_content(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = 'blog/2010/december'
        assert s.full_url(path) == "/" + path

    def test_full_url_for_media(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = 'media/css/site.css'
        assert s.is_media(path)
        full_url = s.full_url(path)
        assert full_url == "/" + path

    def test_media_url_from_resource(self):
        s = Site(self.SITE_PATH, config=self.config)
        s.load()
        path = 'css/site.css'
        resource = s.content.resource_from_relative_path(
                        Folder("media").child(path))
        assert resource
        assert resource.full_url == "/media/" + path

    def test_config_ignore(self):
        c = Config(self.SITE_PATH, config_dict=self.config.to_dict())
        s = Site(self.SITE_PATH, config=c)
        s.load()
        path = 'apple-touch-icon.png'
        resource = s.content.resource_from_relative_path(path)
        assert resource
        assert resource.full_url ==  "/" + path
        s = Site(self.SITE_PATH, config=c)
        s.config.ignore.append('*.png')
        resource = s.content.resource_from_relative_path(path)
        assert not resource

    def test_config_ignore_nodes(self):
        c = Config(self.SITE_PATH, config_dict=self.config.to_dict())
        git = self.SITE_PATH.child_folder('.git')
        git.make()
        s = Site(self.SITE_PATH, config=c)
        s.load()
        git_node = s.content.node_from_relative_path('.git')
        assert not git_node
        blog_node = s.content.node_from_relative_path('blog')
        assert blog_node
        assert blog_node.full_url ==  "/blog"
        s = Site(self.SITE_PATH, config=c)
        s.config.ignore.append('blog')
        blog_node = s.content.node_from_relative_path('blog')
        assert not blog_node
        git_node = s.content.node_from_relative_path('.git')
        assert not git_node
########NEW FILE########
__FILENAME__ = util
import re
import difflib

def strip_spaces_between_tags(value):
    """
    Stolen from `django.util.html`
    Returns the given HTML with spaces between tags removed.
    """
    return re.sub(r'>\s+<', '><', unicode(value))

def assert_no_diff(expected, out):
    diff = [l for l in difflib.unified_diff(expected.splitlines(True),
                                                out.splitlines(True),
                                                n=3)]
    assert not diff, ''.join(diff)


def assert_html_equals(expected, actual, sanitize=None):
    expected = strip_spaces_between_tags(expected.strip())
    actual = strip_spaces_between_tags(actual.strip())
    if sanitize:
        expected = sanitize(expected)
        actual = sanitize(actual)
    assert expected == actual

def trap_exit_fail(f):
    def test_wrapper(*args):
        try:
            f(*args)
        except SystemExit:
            assert False
    test_wrapper.__name__ = f.__name__
    return test_wrapper

def trap_exit_pass(f):
    def test_wrapper(*args):
        try:
            f(*args)
        except SystemExit:
            pass
    test_wrapper.__name__ = f.__name__
    return test_wrapper
########NEW FILE########
__FILENAME__ = util
"""
Module for python 2.6 compatibility.
"""
import os
from functools import partial
from itertools import izip, tee


def make_method(method_name, method_):
    def method__(*args, **kwargs):
        return method_(*args, **kwargs)
    method__.__name__ = method_name
    return method__


def add_property(obj, method_name, method_, *args, **kwargs):
    m = make_method(method_name, partial(method_, *args, **kwargs))
    setattr(obj, method_name, property(m))


def add_method(obj, method_name, method_, *args, **kwargs):
    m = make_method(method_name, partial(method_, *args, **kwargs))
    setattr(obj, method_name, m)


def pairwalk(iterable):
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)


def first_match(predicate, iterable):
    """
    Gets the first element matched by the predicate
    in the iterable.
    """
    for item in iterable:
        if predicate(item):
            return item
    return None


def discover_executable(name, sitepath):
    """
    Finds an executable in the given sitepath or in the
    path list provided by the PATH environment variable.
    """

    # Check if an executable can be found in the site path first.
    # If not check the os $PATH for its presence.

    paths = [unicode(sitepath)] + os.environ['PATH'].split(os.pathsep)
    for path in paths:
        full_name = os.path.join(path, name)
        if os.path.exists(full_name):
            return full_name
    return None
########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-
"""
Handles hyde version.
"""
__version__ = '0.8.8'

########NEW FILE########
