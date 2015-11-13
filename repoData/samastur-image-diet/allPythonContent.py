__FILENAME__ = diet
import logging
from os.path import isfile
from subprocess import call, PIPE
from imghdr import what as determinetype
import image_diet.settings as settings

logger = logging.getLogger('image_diet')


def squeeze_jpeg():
    ''' Prefer jpegtran to jpegoptim since it makes smaller images
    and can create progressive jpegs (smaller and faster to load)'''
    if not settings.DIET_JPEGTRAN and not settings.DIET_JPEGOPTIM:  # Can't do anything
        return ""
    if not settings.DIET_JPEGTRAN:
        return u"jpegoptim -f --strip-all '%(file)s'"
    return (u"jpegtran -copy none -progressive -optimize -outfile '%(file)s'.diet '%(file)s' "
            "&& mv '%(file)s.diet' '%(file)s'")


def squeeze_gif():
    '''Gifsicle only optimizes animations.

    Eventually add support to change gifs to png8.'''
    return (u"gifsicle -O2 '%(file)s' > '%(file)s'.diet "
            "&& mv '%(file)s.diet' '%(file)s'") if settings.DIET_GIFSICLE else ""


def squeeze_png():
    commands = []
    if settings.DIET_OPTIPNG:
        commands.append(u"optipng -force -o7 '%(file)s'")
    if settings.DIET_ADVPNG:
        commands.append(u"advpng -z4 '%(file)s'")
    if settings.DIET_PNGCRUSH:
        commands.append(
            (u"pngcrush -rem gAMA -rem alla -rem cHRM -rem iCCP -rem sRGB "
             u"-rem time '%(file)s' '%(file)s.diet' "
             u"&& mv '%(file)s.diet' '%(file)s'")
        )
    return " && ".join(commands)


def squeeze(path):
    '''Returns path of optimized image or None if something went wrong.'''
    if not isfile(path):
        logger.error("'%s' does not point to a file." % path)
        return None

    if settings.DIET_DEBUG:  # Create a copy of original file for debugging purposes
        call("cp '%(file)s' '%(file)s'.orig" % {'file': path},
             shell=True, stdout=PIPE)

    filetype = determinetype(path)

    squeeze_cmd = ""
    if filetype == "jpeg":
        squeeze_cmd = squeeze_jpeg()
    elif filetype == "gif":
        squeeze_cmd = squeeze_gif()
    elif filetype == "png":
        squeeze_cmd = squeeze_png()

    if squeeze_cmd:
        try:
            retcode = call(squeeze_cmd % {'file': path},
                           shell=True, stdout=PIPE)
        except:
            logger.error('Squeezing failed with parameters:')
            logger.error(squeeze_cmd[filetype] % {'file': path})
            logger.exception()
            return None

        if retcode != 0:
            # Failed.
            logger.error(
                ('Squeezing failed. '
                 'Likely because you are missing one of required utilities.'))
            return None
    return path

########NEW FILE########
__FILENAME__ = check_diet_tools
from subprocess import call, PIPE
from django.core.management.base import BaseCommand
import image_diet.settings as settings


class Command(BaseCommand):
    help = ("Check which external image diet tools are "
            "available and suggest settings.py configuration.")

    def handle(self, *args, **options):
        tools = (
            'jpegoptim',
            'jpegtran',
            'gifsicle',
            'optipng',
            'advpng',
            'pngcrush',
        )
        not_found = []
        for tool in tools:
            setting_name = "DIET_" + tool.upper()
            if getattr(settings, setting_name):
                retcode = call("which %s" % tool, shell=True, stdout=PIPE)
                if retcode == 0:
                    self.stdout.write('Found: %s\n' % tool)
                else:
                    self.stdout.write('MISSING: %s\n' % tool)
                    not_found.append(tool)
            else:  # Tool turned off
                self.stdout.write('Disabled: %s\n' % tool)
        if len(not_found):
            off_settings = ["DIET_%s = False" % tool.upper() for tool
                            in not_found]
            self.stdout.write("\n")
            self.stdout.write("You can disable missing tools by adding following lines to your settings.py: \n")
            self.stdout.write("\n".join(off_settings))
            self.stdout.write("\n")

########NEW FILE########
__FILENAME__ = diet_images
import os
from os.path import join
from django.core.management.base import BaseCommand
from image_diet.diet import squeeze


class Command(BaseCommand):
    args = '<dir1> [<dir2>...]'
    help = "Scan directories and subdirectories for images and compress them."

    def handle(self, *args, **options):
        for dirname in args:
            for (root, dirs, files) in os.walk(dirname):
                for filename in files:
                    filepath = join(root, filename)
                    squeeze(filepath)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

DIET_DEBUG = getattr(settings, 'DIET_DEBUG', False)

DIET_JPEGOPTIM = getattr(settings, 'DIET_JPEGOPTIM', True)
DIET_JPEGTRAN = getattr(settings, 'DIET_JPEGTRAN', True)
DIET_GIFSICLE = getattr(settings, 'DIET_GIFSICLE', True)
DIET_OPTIPNG = getattr(settings, 'DIET_OPTIPNG', True)
DIET_ADVPNG = getattr(settings, 'DIET_ADVPNG', True)
DIET_PNGCRUSH = getattr(settings, 'DIET_PNGCRUSH', True)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import receiver
from diet import squeeze

try:
    from easy_thumbnails.signals import saved_file, thumbnail_created

    @receiver(saved_file)
    def optimize_file(sender, fieldfile, **kwargs):
        squeeze(fieldfile.path)

    @receiver(thumbnail_created)
    def optimize_thumbnail(sender, **kwargs):
        squeeze(sender.path)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = test_commands
import os
from os.path import join, dirname
from shutil import copyfile
from django.test import TestCase
from image_diet.management.commands import diet_images

TEST_DIR = join(dirname(__file__), 'test_files')


class DietCommandTest(TestCase):
    def setUp(self):
        image_path = join(TEST_DIR, 'stockholm.jpg')

        self.nested_dir = join('dir1', 'dir2', 'dir3')
        self.test_root_dir = join(TEST_DIR, 'dir1')

        os.makedirs(join(TEST_DIR, self.nested_dir))

        self.test_image_path = join(TEST_DIR, self.nested_dir, 'stockholm.jpg')
        copyfile(image_path, self.test_image_path)

    def tearDown(self):
        os.remove(self.test_image_path)
        os.chdir(TEST_DIR)
        os.removedirs(self.nested_dir)

    def test_diet_images(self):
        old_size = os.stat(self.test_image_path).st_size
        action = diet_images.Command()
        action.handle(self.test_root_dir)
        new_size = os.stat(self.test_image_path).st_size

        self.assertTrue(new_size < old_size)

########NEW FILE########
__FILENAME__ = test_diet
import os
from os.path import join, dirname
from shutil import copyfile
from subprocess import call, PIPE
from django.test import TestCase
from image_diet import diet

TEST_DIR = join(dirname(__file__), 'test_files')


class DietTest(TestCase):

    def setUp(self):
        image_path = join(TEST_DIR, 'stockholm.jpg')

        self.test_image_path = join(TEST_DIR, 'test_image.jpg')
        copyfile(image_path, self.test_image_path)

    def tearDown(self):
        os.remove(self.test_image_path)

    def have_jpeg_tools(self):
        retcode = call("which jpegoptim || which jpegtran", shell=True,
                       stdout=PIPE)
        return True if retcode is 0 else False

    def test_squeeze_jpeg(self):
        diet.settings.DIET_JPEGOPTIM = False
        diet.settings.DIET_JPEGTRAN = False
        self.assertEqual(diet.squeeze_jpeg(), "")

        diet.settings.DIET_JPEGTRAN = True
        self.assertEqual(
            diet.squeeze_jpeg(),
            (u"jpegtran -copy none -progressive -optimize -outfile '%(file)s'.diet '%(file)s' "
                "&& mv '%(file)s.diet' '%(file)s'")
        )

        diet.settings.DIET_JPEGOPTIM = True
        diet.settings.DIET_JPEGTRAN = False
        self.assertEqual(diet.squeeze_jpeg(), u"jpegoptim -f --strip-all '%(file)s'")

    def test_squeeze_png(self):
        diet.settings.DIET_OPTIPNG = False
        diet.settings.DIET_ADVPNG = False
        diet.settings.DIET_PNGCRUSH = False
        self.assertEqual(diet.squeeze_png(), "")

        diet.settings.DIET_OPTIPNG = True
        diet.settings.DIET_ADVPNG = False
        diet.settings.DIET_PNGCRUSH = False
        self.assertEqual(diet.squeeze_png(), u"optipng -force -o7 '%(file)s'")

        diet.settings.DIET_OPTIPNG = False
        diet.settings.DIET_ADVPNG = True
        diet.settings.DIET_PNGCRUSH = False
        self.assertEqual(diet.squeeze_png(), u"advpng -z4 '%(file)s'")

        diet.settings.DIET_OPTIPNG = False
        diet.settings.DIET_ADVPNG = False
        diet.settings.DIET_PNGCRUSH = True
        self.assertEqual(
            diet.squeeze_png(),
            (u"pngcrush -rem gAMA -rem alla -rem cHRM -rem iCCP -rem sRGB "
             u"-rem time '%(file)s' '%(file)s.diet' "
             u"&& mv '%(file)s.diet' '%(file)s'")
        )

        diet.settings.DIET_OPTIPNG = True
        diet.settings.DIET_ADVPNG = True
        diet.settings.DIET_PNGCRUSH = False
        self.assertEqual(diet.squeeze_png(), u"optipng -force -o7 '%(file)s' && advpng -z4 '%(file)s'")

    def test_squeeze_gif(self):
        diet.settings.DIET_GIFSICLE = True
        self.assertEqual(
            diet.squeeze_gif(),
            (u"gifsicle -O2 b'%(file)s' > '%(file)s'.diet "
                "&& mv '%(file)s.diet' '%(file)s'")
        )

        diet.settings.DIET_GIFSICLE = False
        self.assertEqual(diet.squeeze_gif(), "")

    def test_squeeze(self):
        self.assertEqual(diet.squeeze('/tmp/bla'), None)

        old_size = os.stat(self.test_image_path).st_size

        new_path = diet.squeeze(self.test_image_path)
        new_size = os.stat(new_path).st_size

        if self.have_jpeg_tools():
            self.assertEqual(new_path, self.test_image_path)
            self.assertTrue(new_size < old_size)
        else:
            print "Install jpegtran or jpegoptim to test shrinking"

########NEW FILE########
