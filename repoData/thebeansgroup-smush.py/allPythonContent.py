__FILENAME__ = animated_gif
from optimiser.optimiser import Optimiser

class OptimiseAnimatedGIF(Optimiser):
    """
    Optimises animated gifs with Gifsicle - http://www.lcdf.org/gifsicle/
    """

    def __init__(self, **kwargs):
        super(OptimiseAnimatedGIF, self).__init__(**kwargs)

        # the command to execute this optimiser
        self.commands = ('gifsicle -O2 "__INPUT__" --output "__OUTPUT__"',)

        # format as returned by 'identify'
        self.format = "GIFGIF"

########NEW FILE########
__FILENAME__ = gif
import os.path
import shutil
from optimiser.optimiser import Optimiser
from animated_gif import OptimiseAnimatedGIF
import logging

class OptimiseGIF(Optimiser):
    """
    Optimises gifs. If they aren't animated, it converts them to pngs with ImageMagick before
    optimising them as for pngs.

    Animated gifs get optimised according to the commands in OptimiseAnimatedGIF
    """


    def __init__(self, **kwargs):
        super(OptimiseGIF, self).__init__(**kwargs)

        # the command to execute this optimiser
        if kwargs.get('quiet') == True:
            pngcrush = 'pngcrush -rem alla -brute -reduce -q "__INPUT__" "__OUTPUT__"'
        else:
            pngcrush = 'pngcrush -rem alla -brute -reduce "__INPUT__" "__OUTPUT__"'
        self.commands = ('convert "__INPUT__" png:"__OUTPUT__"',
            'pngnq -n 256 -o "__OUTPUT__" "__INPUT__"',
            pngcrush)

        # variable so we can easily determine whether a gif is animated or not
        self.animated_gif_optimiser = OptimiseAnimatedGIF()

        self.converted_to_png = False
        self.is_animated = False

        # format as returned by 'identify'
        self.format = "GIF"


    def set_input(self, input):
        super(OptimiseGIF, self).set_input(input)
        self.converted_to_png = False
        self.is_animated = False


    def _is_animated(self, input):
        """
        Tests an image to see whether it's an animated gif
        """
        return self.animated_gif_optimiser._is_acceptable_image(input)


    def _keep_smallest_file(self, input, output):
        """
        Compares the sizes of two files, and discards the larger one
        """
        input_size = os.path.getsize(input)
        output_size = os.path.getsize(output)
        
        # if the image was optimised (output is smaller than input), overwrite the input file with the output
        # file.
        if (output_size < input_size):
            try:
                shutil.copyfile(output, input)
                self.files_optimised += 1
                self.bytes_saved += (input_size - output_size)
            except IOError:
                logging.error("Unable to copy %s to %s: %s" % (output, input, IOError))
                sys.exit(1)

            if self.iterations == 1 and not self.is_animated:
                self.converted_to_png = True
            
        # delete the output file
        os.unlink(output)


    def _get_command(self):
        """
        Returns the next command to apply
        """

        command = False

        # for the first iteration, return the first command
        if self.iterations == 0:
            # if the GIF is animated, optimise it
            if self._is_animated(self.input):
                command = self.animated_gif_optimiser.commands[0]
                self.is_animated = True
            else:             # otherwise convert it to PNG
                command = self.commands[0]

        # execute the png optimisations if the gif was converted to a png
        elif self.converted_to_png and self.iterations < len(self.commands):
            command = self.commands[self.iterations]

        self.iterations += 1

        return command

    def _list_only(self, input, output):
        """
        Always keeps input, but still compares the sizes of two files
        """
        input_size = os.path.getsize(input)
        output_size = os.path.getsize(output)

        if (output_size > 0 and output_size < input_size):
            self.files_optimised += 1
            self.bytes_saved += (input_size - output_size)
            self.array_optimised_file.append(input)
            if self.iterations == 1 and not self.is_animated:
                self.convert_to_png = True
        
        # delete the output file
        os.unlink(output)

########NEW FILE########
__FILENAME__ = jpg
import os.path
from optimiser.optimiser import Optimiser
import logging

class OptimiseJPG(Optimiser):
    """
    Optimises jpegs with jpegtran (part of libjpeg)
    """


    def __init__(self, **kwargs):
        super(OptimiseJPG, self).__init__(**kwargs)

        strip_jpg_meta = kwargs.pop('strip_jpg_meta')

        # the command to execute this optimiser
        if strip_jpg_meta:
            self.commands = ('jpegtran -outfile "__OUTPUT__" -optimise -copy none "__INPUT__"',
                'jpegtran -outfile "__OUTPUT__" -optimise -progressive "__INPUT__"')
        else:
            self.commands = ('jpegtran -outfile "__OUTPUT__" -optimise -copy all "__INPUT__"',
                'jpegtran -outfile "__OUTPUT__" -optimise -progressive -copy all "__INPUT__"')

        # format as returned by 'identify'
        self.format = "JPEG"


    def _get_command(self):
        """
        Returns the next command to apply
        """
        # for the first iteration, return the first command
        if self.iterations == 0:
            self.iterations += 1
            return self.commands[0]
        elif self.iterations == 1:
            self.iterations += 1
                        
            # for the next one, only return the second command if file size > 10kb
            if os.path.getsize(self.input) > 10000:
                if self.quiet == False:
                    logging.warning("File is > 10kb - will be converted to progressive")
                return self.commands[1]

        return False

########NEW FILE########
__FILENAME__ = png
import os.path
from optimiser.optimiser import Optimiser

class OptimisePNG(Optimiser):
    """
    Optimises pngs. Uses pngnq (http://pngnq.sourceforge.net/) to quantise them, then uses pngcrush
    (http://pmt.sourceforge.net/pngcrush/) to crush them.
    """


    def __init__(self, **kwargs):
        super(OptimisePNG, self).__init__(**kwargs)

        if kwargs.get('quiet') == True:
            pngcrush = 'pngcrush -rem alla -brute -reduce -q "__INPUT__" "__OUTPUT__"'
        else:
            pngcrush = 'pngcrush -rem alla -brute -reduce "__INPUT__" "__OUTPUT__"'

        # the command to execute this optimiser
        self.commands = ('pngnq -n 256 -o "__OUTPUT__" "__INPUT__"', pngcrush)

        # format as returned by 'identify'
        self.format = "PNG"


#    def _get_output_file_name(self):
#        """
#        Returns the input file name with Optimiser.output_suffix inserted before the extension
#        """
#        (basename, extension) = os.path.splitext(self.input)
#
#        if extension.lower() == '.png':
#            return basename + Optimiser.output_suffix
#
#        return self.input + Optimiser.output_suffix

########NEW FILE########
__FILENAME__ = optimiser
import os.path
import os
import shlex
import subprocess
import sys
import shutil
import logging
import tempfile
from scratch import Scratch

class Optimiser(object):
    """
    Super-class for optimisers
    """

    input_placeholder = "__INPUT__"
    output_placeholder = "__OUTPUT__"

    # string to place between the basename and extension of output images
    output_suffix = "-opt.smush"


    def __init__(self, **kwargs):
        # the number of times the _get_command iterator has been run
        self.iterations = 0
        self.files_scanned = 0
        self.files_optimised = 0
        self.bytes_saved = 0
        self.list_only = kwargs.get('list_only')
        self.array_optimised_file = []
        self.quiet = kwargs.get('quiet')
        self.stdout = Scratch()
        self.stderr = Scratch()

    def __del__(self):
        self.stdout.destruct()
        self.stderr.destruct()

    def set_input(self, input):
        self.iterations = 0
        self.input = input


    def _get_command(self):
        """
        Returns the next command to apply
        """
        command = False
        
        if self.iterations < len(self.commands):
            command = self.commands[self.iterations]
            self.iterations += 1

        return command


    def _get_output_file_name(self):
        """
        Returns the input file name with Optimiser.output_suffix inserted before the extension
        """
        temp = tempfile.mkstemp(suffix=Optimiser.output_suffix)
        try:
            output_file_name = temp[1]
            os.unlink(output_file_name)
            return output_file_name
        finally:
            os.close(temp[0])


    def __replace_placeholders(self, command, input, output):
        """
        Replaces the input and output placeholders in a string with actual parameter values
        """
        return command.replace(Optimiser.input_placeholder, input).replace(Optimiser.output_placeholder, output)


    def _keep_smallest_file(self, input, output):
        """
        Compares the sizes of two files, and discards the larger one
        """
        input_size = os.path.getsize(input)
        output_size = os.path.getsize(output)

        # if the image was optimised (output is smaller than input), overwrite the input file with the output
        # file.
        if (output_size > 0 and output_size < input_size):
            try:
                shutil.copyfile(output, input)
                self.files_optimised += 1
                self.bytes_saved += (input_size - output_size)
            except IOError:
                logging.error("Unable to copy %s to %s: %s" % (output, input, IOError))
                sys.exit(1)
        
        # delete the output file
        os.unlink(output)
        

    def _is_acceptable_image(self, input):
        """
        Returns whether the input image can be used by a particular optimiser.

        All optimisers are expected to define a variable called 'format' containing the file format
        as returned by 'identify -format %m'
        """
        test_command = 'identify -format %%m "%s"' % input
        args = shlex.split(test_command)

        try:
            retcode = subprocess.call(args, stdout=self.stdout.opened, stderr=self.stderr.opened)
        except OSError:
            logging.error("Error executing command %s. Error was %s" % (test_command, OSError))
            sys.exit(1)
        except:
            # most likely no file matched
            if self.quiet == False:
                logging.warning("Cannot identify file.")
            return False
        if retcode != 0:
            if self.quiet == False:
                logging.warning("Cannot identify file.")
            return False
        output = self.stdout.read().strip()
        return output.startswith(self.format)


    def optimise(self):
        """
        Calls the 'optimise_image' method on the object. Tests the 'optimised' file size. If the
        generated file is larger than the original file, discard it, otherwise discard the input file.
        """
        # make sure the input image is acceptable for this optimiser
        if not self._is_acceptable_image(self.input):
            logging.warning("%s is not a valid image for this optimiser" % (self.input))
            return

        self.files_scanned += 1

        while True:
            command = self._get_command()

            if not command:
                break

            output_file_name = self._get_output_file_name()
            command = self.__replace_placeholders(command, self.input, output_file_name)
            logging.info("Executing %s" % (command))
            args = shlex.split(command)
            
            try:
                retcode = subprocess.call(args, stdout=self.stdout.opened, stderr=self.stderr.opened)
            except OSError:
                logging.error("Error executing command %s. Error was %s" % (command, OSError))
                sys.exit(1)

            if retcode != 0:
                # gifsicle seems to fail by the file size?
                os.unlink(output_file_name)
            else :
                if self.list_only == False:
                    # compare file sizes if the command executed successfully
                    self._keep_smallest_file(self.input, output_file_name)
                else:
                    self._list_only(self.input, output_file_name)


    def _list_only(self, input, output):
        """
        Always keeps input, but still compares the sizes of two files
        """
        input_size = os.path.getsize(input)
        output_size = os.path.getsize(output)

        if (output_size > 0 and output_size < input_size):
            self.files_optimised += 1
            self.bytes_saved += (input_size - output_size)
            self.array_optimised_file.append(input)
        
        # delete the output file
        os.unlink(output)

########NEW FILE########
__FILENAME__ = scratch
import os, sys, tempfile

class Scratch (object):
    def __init__ (self):
        tup = tempfile.mkstemp()
        self._path = tup[1]
        self._file = os.fdopen(tup[0])        
        self._file.close()

    def __del__ (self):
        if self._path != None:
            self.destruct()

    def destruct (self):
        self.close()
        os.unlink(self._path)
        self._path = None
        self._file = None

    def close (self):
        if self._file.closed == False:
            self._file.flush()
            self._file.close()

    def read (self):
        if self._file.closed == True:
            self._reopen()
        self._file.seek(0)
        return self._file.read()

    def _reopen (self):
        self._file = open(self._path, 'w+')

    def getopened (self):
        self.close()
        self._reopen()
        return self._file
    opened = property(getopened, NotImplemented, NotImplemented, "opened file - read only")

    def getfile (self):
        return self._file
    file = property(getfile, NotImplemented, NotImplemented, "file - read only")

########NEW FILE########
__FILENAME__ = smush
#!/usr/bin/env python

import sys, os, os.path, getopt, time, shlex, subprocess, logging
from subprocess import CalledProcessError
from optimiser.formats.png import OptimisePNG
from optimiser.formats.jpg import OptimiseJPG
from optimiser.formats.gif import OptimiseGIF
from optimiser.formats.animated_gif import OptimiseAnimatedGIF
from scratch import Scratch

__author__     = 'al, Takashi Mizohata'
__credit__     = ['al', 'Takashi Mizohata']
__maintainer__ = 'Takashi Mizohata'

# there should be an option to keep or strip meta data (e.g. exif data) from jpegs

class Smush():
    def __init__(self, **kwargs):
        self.optimisers = {
            'PNG': OptimisePNG(**kwargs),
            'JPEG': OptimiseJPG(**kwargs),
            'GIF': OptimiseGIF(**kwargs),
            'GIFGIF': OptimiseAnimatedGIF(**kwargs)
        }

        self.__files_scanned = 0
        self.__start_time = time.time()
        self.exclude = {}
        for dir in kwargs.get('exclude'):
            if len(dir) == 0:
                continue
            self.exclude[dir] = True
        self.quiet = kwargs.get('quiet')
        self.identify_mime = kwargs.get('identify_mime')

        # setup tempfile for stdout and stderr
        self.stdout = Scratch()
        self.stderr = Scratch()

    def __del__(self):
        self.stdout.destruct()
        self.stderr.destruct()

    def __smush(self, file):
        """
        Optimises a file
        """
        key = self.__get_image_format(file)

        if key in self.optimisers:
            logging.info('optimising file %s' % (file))
            self.__files_scanned += 1
            self.optimisers[key].set_input(file)
            self.optimisers[key].optimise()


    def process(self, dir, recursive):
        """
        Iterates through the input directory optimising files
        """
        if recursive:
            self.__walk(dir, self.__smush)
        else:
            if os.path.isdir(dir):
                dir = os.path.abspath(dir)
                for file in os.listdir(dir):
                    if self.__checkExclude(file):
                        continue
                        
                    if self.identify_mime:
                        import mimetypes
                        (type,encoding) = mimetypes.guess_type(file)
                        if type and (type[:5] != "image"):
                            continue

                    self.__smush(os.path.join(dir, file))
            elif os.path.isfile(dir):
                self.__smush(dir)


    def __walk(self, dir, callback):
        """ Walks a directory, and executes a callback on each file """
        dir = os.path.abspath(dir)
        logging.info('walking %s' % (dir))
        for file in os.listdir(dir):
            if self.__checkExclude(file):
                continue
            
            if self.identify_mime:
                import mimetypes
                (type,encoding) = mimetypes.guess_type(file)        
                if type and (type[:5] != "image"):
                    continue

            nfile = os.path.join(dir, file)
            callback(nfile)
            if os.path.isdir(nfile):
                self.__walk(nfile, callback)


    def __get_image_format(self, input):
        """
        Returns the image format for a file.
        """
        test_command = 'identify -format %%m "%s"' % input
        args = shlex.split(test_command)

        try:
            retcode = subprocess.call(args, stdout=self.stdout.opened, stderr=self.stderr.opened)
            if retcode != 0:
                if self.quiet == False:
                    logging.warning(self.stderr.read().strip())
                return False

        except OSError:
            logging.error('Error executing command %s. Error was %s' % (test_command, OSError))
            sys.exit(1)
        except:
            # most likely no file matched
            if self.quiet == False:
                logging.warning('Cannot identify file.')
            return False

        return self.stdout.read().strip()[:6]


    def stats(self):
        output = []
        output.append('\n%d files scanned:' % (self.__files_scanned))
        arr = []

        for key, optimiser in self.optimisers.iteritems():
            # divide optimiser.files_optimised by 2 for each optimiser since each optimised file
            # gets counted twice
            output.append('    %d %ss optimised out of %d scanned. Saved %dkb' % (
                    optimiser.files_optimised // 2,
                    key, 
                    optimiser.files_scanned, 
                    optimiser.bytes_saved / 1024))
            arr.extend(optimiser.array_optimised_file)

        if (len(arr) != 0):
            output.append('Modified files:')
            for filename in arr:
                output.append('    %s' % filename)
        output.append('Total time taken: %.2f seconds' % (time.time() - self.__start_time))
        return {'output': "\n".join(output), 'modified': arr}


    def __checkExclude(self, file):
        if file in self.exclude:
            logging.info('%s is excluded.' % (file))
            return True
        return False


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hrqs', ['help', 'recursive', 'quiet', 'strip-meta', 'exclude=', 'list-only' ,'identify-mime'])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    if len(args) == 0:
        usage()
        sys.exit()

    recursive = False
    quiet = False
    strip_jpg_meta = False
    exclude = ['.bzr', '.git', '.hg', '.svn']
    list_only = False
    identify_mime = False

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit()
        elif opt in ('-r', '--recursive'):
            recursive = True
        elif opt in ('-q', '--quiet'):
            quiet = True
        elif opt in ('-s', '--strip-meta'):
            strip_jpg_meta = True
        elif opt in ('--identify-mime'):
            identify_mime = True
        elif opt in ('--exclude'):
            exclude.extend(arg.strip().split(','))
        elif opt in ('--list-only'):
            list_only = True
            # quiet = True
        else:
            # unsupported option given
            usage()
            sys.exit(2)

    if quiet == True:
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')

    smush = Smush(strip_jpg_meta=strip_jpg_meta, exclude=exclude, list_only=list_only, quiet=quiet, identify_mime=identify_mime)

    for arg in args:
        try:
            smush.process(arg, recursive)
            logging.info('\nSmushing Finished')
        except KeyboardInterrupt:
            logging.info('\nSmushing aborted')

    result = smush.stats()
    if list_only and len(result['modified']) > 0:
        logging.error(result['output'])
        sys.exit(1)
    print result['output']
    sys.exit(0)

def usage():
    print """Losslessly optimises image files - this saves bandwidth when displaying them
on the web.

  Usage: """ + sys.argv[0] + """ [options] FILES...

    FILES can be a space-separated list of files or directories to optimise

  **WARNING**: Existing images files  will be OVERWRITTEN with optimised
               versions.

  Options are any of:
  -h, --help         Display this help message and exit
  -r, --recursive    Recurse through given directories optimising images
  -q, --quiet        Don't display optimisation statistics at the end
  -s, --strip-meta   Strip all meta-data from JPEGs
  --exclude=EXCLUDES comma separated value for excluding files
  --identify-mime    Fast identify image files via mimetype
  --list-only        Perform a trial run with no changes made
"""

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_smush
#!/usr/bin/env python

import unittest
import os, os.path, sys, shutil, time, subprocess
sys.path.insert(0, os.path.abspath('./smush'))
from smush import Smush

# import logging
# project_name = 'test_smush'
# logger = logging.getLogger(project_name)
# formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
# logpath = os.path.expanduser('~/Library/Logs/%s.log' % (project_name))
# if os.path.isfile(logpath) == False:
#     open(logpath, 'w').close()
# mylog = logging.FileHandler(logpath)
# mylog.setFormatter(formatter)
# logger.addHandler(mylog)
# logger.setLevel(logging.INFO)

script_path = os.path.join(os.getcwd(), __file__)
script_dir = os.path.dirname(script_path)
materials_dir = os.path.join(script_dir, 'materials')
filename_gif = 'exam_gif_to_png.gif'

class TestSetup(object):
    working_dir = ''
    working_dirname = ''
    working_files = ''

    def setUp(self):
        # logger.info('Setup')
        # logger.info(materials_dir)
        # logger.info(os.listdir(materials_dir))
        self.working_dirname = '%s' % time.time()
        self.working_dir = os.path.join(script_dir, self.working_dirname)
        shutil.copytree(materials_dir, self.working_dir)
        # logger.info(os.listdir(materials_dir))
        # logger.info('DIR: %s' % self.working_dir)
        files = subprocess.check_output(
            ' '.join(['cd', self.working_dir, '&&', 'find', '.', '-type', 'f', '-regex', '".*[^DS_Store]"']),
            shell=True
        )
        self.working_files = str.splitlines(files);
        i = 0
        for each_file in self.working_files:
            self.working_files[i] = each_file[2:]
            i = i + 1

    def tearDown(self):
        # logger.info('teardown')
        if os.path.isdir(self.working_dir) == True:
            shutil.rmtree(self.working_dir)
            self.working_dir = ''

class SmushTestSuite(TestSetup, unittest.TestCase):
    def test_smush_file (self):
        smushing_path = os.path.join(self.working_dir, filename_gif)
        smush = Smush(strip_jpg_meta=False, list_only=False, quiet=True, exclude='.bzr,.git,.hg,.svn,.DS_Store')
        smush.process(smushing_path, False)

        for each_file in self.working_files:
            if each_file == filename_gif:
                src_size = os.path.getsize(os.path.join(materials_dir, each_file))
                dest_size = os.path.getsize(smushing_path)
                self.assertTrue(src_size > dest_size)
            else:
                src_size = os.path.getsize(os.path.join(materials_dir, each_file))
                dest_size = os.path.getsize(os.path.join(self.working_dir, each_file))
                self.assertTrue(src_size == dest_size)
        return True

    def test_smush_dir_not_recursive (self):
        smush = Smush(strip_jpg_meta=False, list_only=False, quiet=True, exclude='.bzr,.git,.hg,.svn,.DS_Store')
        smush.process(self.working_dir, False)

        for each_file in self.working_files:
            if each_file == filename_gif:
                src_size = os.path.getsize(os.path.join(materials_dir, each_file))
                dest_size = os.path.getsize(os.path.join(self.working_dir, each_file))
                self.assertTrue(src_size > dest_size)
            else:
                src_size = os.path.getsize(os.path.join(materials_dir, each_file))
                dest_size = os.path.getsize(os.path.join(self.working_dir, each_file))
                self.assertTrue(src_size == dest_size)
        return True

    def test_smush_dir_recursive (self):
        smush = Smush(strip_jpg_meta=False, list_only=False, quiet=True, exclude='.bzr,.git,.hg,.svn,.DS_Store')
        smush.process(self.working_dir, True)

        for each_file in self.working_files:
            src_size = os.path.getsize(os.path.join(materials_dir, each_file))
            dest_size = os.path.getsize(os.path.join(self.working_dir, each_file))
            self.assertTrue(src_size > dest_size)
        return True

if __name__ == '__main__':
    # logger.info('%s started at %d' % (project_name, time.time()))
    unittest.main()

########NEW FILE########
