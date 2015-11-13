__FILENAME__ = cl
#! /usr/bin/python
# -*- coding: utf-8 -*-

from core import *
from utils import dump
from functools import partial
import watch
import config

import sys
import optparse

import logging
# we're running as a command line script, re-enable logging
logging.disable(logging.NOTSET)
FORMAT = '%(asctime)-15s %(levelname)-12s %(message)s'

def version():
    '''print version of Imagy'''
    print imagy.__version__

parser = optparse.OptionParser('Optimize images')
true_flag = partial(parser.add_option, action="store_true", default=False)

true_flag('-c', '--clear', help=clear.__doc__)
true_flag('-l', '--list', help=list_files.__doc__)
true_flag('-r', '--revert', help=revert.__doc__)
true_flag('-f', '--files', help=do_files.__doc__)
true_flag('-q', '--quiet', help='suppress output')
true_flag('-m', '--memorystore', help='maintain file paths in memory')
true_flag('-v', '--version', help=version.__doc__)
true_flag('-n', '--run', help='Run the daemon even though another option has been specified')

true_flag('--deloriginals', help=delete_originals.__doc__)
true_flag('--debug', help='set logging to DEBUG')
true_flag('--no-init', dest='no_init', help='do not check directories for not yet optimized files')
true_flag('--no-watch', dest='no_watch', help='do not watch directories for changes')

parser.add_option('-d', '--dir', action="store", default=STORE_PATH, dest="store_path", help='the directory '
                  'within which internal storage resides')
#debug
true_flag('--dump', help=dump.__doc__)
opts, args = parser.parse_args(sys.argv[1:])

def _main(opts, args):
    level = logging.DEBUG if opts.debug else logging.INFO
    logging.basicConfig(format=FORMAT, level=level)

    if opts.quiet:
        logging.disable(logging.CRITICAL)

    logging.info('Imagy started')
    logging.debug(map(str, (args, opts)))

    if not opts.memorystore:
        store_path = opts.store_path
        if store_path is None:
            store_path = imagy_at_home = path('~').expanduser().joinpath(IMAGY_DIR_NAME)
            snippet = (' and backup files' if config.KEEP_ORIGINALS else '')
            msg = 'Using %s to store configuration%s, you can modify this path in config.py under STORE_PATH'
            logging.info(msg, imagy_at_home, snippet)
        store.load(store_path)

    args = [path(arg) for arg in args or FILE_PATTERNS if arg]
    run_daemon = opts.run

    if opts.clear: clear()
    elif opts.dump: dump(store)
    elif opts.revert: revert()
    elif opts.list: list_files()
    elif opts.files: do_files(*args)
    elif opts.deloriginals: delete_originals()
    elif opts.version: version()
    else: run_daemon = True

    if run_daemon:
        # if nothing specified so far, just run `smart mode` i.e. initialize the
        # directories and then run the daemon afterwards
        if not opts.no_init:
            initialize(*args)
        if not opts.no_watch:
            watch.watcher.run(*args)

def main():
    try:
        _main(opts, args)
    finally:
        try:
            store.save()
        except Exception, e:
            logging.error('unable to save %s', e)
        else:
            logging.debug('saved to %s', store.dir)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = config
IMAGY_DIR_NAME = '.imagy'

OPTIMIZE_ON_CREATE = True
OPTIMIZE_ON_CHANGE = True

FILE_PATTERNS = (
#    '/srv/images/*',
#    '/home/me/awesome/',
    )

# If set to False, Imagy will delete originals after deletion
KEEP_ORIGINALS = True

# this is inserted before the file extension, if the path already exists, append
# a 0 to the identifier and keep iterating until a free path is found
ORIGINAL_IDENTIFIER = '-original'

#image extensions to be picked up by imagy
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif',)

STRIP_JPG_META = True

# the location where imagy stores its internals, if this is `None` at startup,
# imagy will ask where it should store

STORE_PATH = None

TRIAL_RUN = False

########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-

# all config values are constant & uppercase
from config import *

from utils import make_path, same_file, MARK
from store import store
from libsmush import optimize_with_touch
import watch
from path import path
import logging
logging.disable(logging.CRITICAL)

def revert():
    '''Move stored originals back to their initial location'''
    # sort to get as many un-marked paths that require no user input,
    # until prompting for further instruction (storedat.values() are either None or MARK)
    logging.info('reverting %s files', len(store.originals))
    for pth, storedat in sorted(store.originals.items(), key=lambda (k, v):store.storedat[v]):
        move = True
        if store.storedat[storedat] == MARK:
            # the stored original has been modified, wat do?
            resp = raw_input('%s has been modified, move back to %s? [y]es/[N]o/[a]bort ' %
                             (storedat, pth)).lower()[:1]
            if resp == 'a':
                break
            if resp != 'y':
                # we still want to go down and remove the file from store so we don't ask for it
                # upon repeated invocation
                move = False
        if move:
            logging.info('moving %s back to %s', storedat, pth)
            path(storedat).move(pth)
        clear_record(pth, storedat)

def clear_record(pth, storedat):
    '''remove the file from internal storage'''
    del store.originals[pth]
    del store.storedat[storedat]

def clear():
    '''Clear out all internal records - this makes --revert unreliable'''
    cleared = len(store.originals)
    store.clear()
    store.save()
    logging.info('cleared %s file names from internal store', cleared)

def handle_evented_file(pth):
    '''handles a file after an event has been received for it'''
    if not store.wants(pth):
        return
    if pth in store.storedat:
        if not store.storedat[pth]:
            # only warn on first modification
            logging.warning('%s, a stored original has been modified - will ask what to do at --revert', pth)
            store.storedat[pth] = MARK
    else:
        return handle_file(pth)

def handle_file(pth):
    '''Optimizes an image and stores an original if KEEP_ORIGINALS is set'''
    logging.info('Optimizing file %s', pth)
    if KEEP_ORIGINALS:
        if pth in store.originals:
            # we have previously optimized this file and know where to store it
            storedat = store_original(pth, store.originals[pth])
        else:
            storedat = store_original(pth)
    # the original gets briefly added to ignore so watchdog doesnt pick it up
    ignore_file(pth)
    optimize_with_touch(pth)
    if KEEP_ORIGINALS:
        # only keep the file if we actually optimized it
        if same_file(storedat, pth):
            storedat.remove()
        else:
            store_original_location(pth, storedat)

def initialize(*dirs):
    '''Run through the specified directories, optimizing all images'''
    logging.info('looking for not yet optimized files')
    files = (p for dir in dirs for p in dir.walkfiles())
    do_files(*files)

def do_files(*files):
    '''Optimize all given files'''
    touched_files = set(pth for kv in store.originals.items() for pth in kv)
    for file in files:
        pth = path(file).abspath()
        if pth in touched_files:
            logging.info('ignoring %s', pth)
        else:
            handle_file(pth)

def list_files():
    '''list all files in internal store'''
    logging.info('optimized files:')
    i = 0
    for i, (pth, storedat) in enumerate(store.originals.iteritems()):
        print pth, '->', storedat
        i += 1
    logging.info('%s files', i)

def store_original(pth, storedat=None):
    '''Store a copy of the original and return the copy's location'''
    if not storedat:
        # get an unused file name to store the original
        storedat = find_storage_space(pth)
    logging.debug('pushing original to %s', storedat)
    ignore_file(storedat)
    pth.copy(storedat)
    # check if the copy was successful
    if not same_file(pth, storedat):
        raise AttributeError('copy seems to differ from original')
    return storedat

def store_original_location(pth, storedat):
    '''store the original path so we can revert it later'''
    store.originals[pth] = storedat
    store.storedat[storedat] = None

def find_storage_space(pth, identifier=ORIGINAL_IDENTIFIER):
    '''Find a new path with the identifier'''
    name, ext = pth.splitext()
    return make_path(name + identifier + ext, sep='').abspath()

def ignore_file(pth, store=store):
    '''before touching a file we tell store how many events it should ignore for it'''
    if not watch.watcher.running:
        return
    # if the file exists watchdog sends `modify` if not it also sends `create` beforehand
    n = 1 if pth.exists() else 2
    store.ignore(pth, n)

def correct_ext(pth, exts=set(IMAGE_EXTENSIONS)):
    return pth.splitext()[1] in exts

def delete_originals():
    '''Delete all originals, useful if you want to switch KEEP_ORIGINALS to False'''
    for pth, storedat in store.originals.items():
        logging.debug('removing %s', storedat)
        # using remove_p as it doesnt raise an Exception if the path doesnt exist
        storedat.remove_p()
        clear_record(pth, storedat)

########NEW FILE########
__FILENAME__ = libsmush
'''
A wrapper around the smush.py library

the library itself has been modifed to make it work with the binaries included in most package managers (to custom patches + recompiling
'''

from config import STRIP_JPG_META
from utils import file_sig

from smush import Smush
from path import path

smusher = Smush(strip_jpg_meta=STRIP_JPG_META, list_only=False, quiet=True, identify_mime=True)
optimize_image = smusher.smush

def optimize_with_touch(pth, smusher=smusher):
    '''
    dirty, but we need to guarantee that the file gets touched to make sure watchdog fires an event
    when the file gets optimized
    '''
    pth = path(pth).abspath()
    sig = file_sig(pth)
    optimize_image(pth)
    if file_sig(pth) == sig:
        # not modified, force it ourselves
        pth.touch()

########NEW FILE########
__FILENAME__ = animated_gif
from ..optimiser import Optimiser

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
from ..optimiser import Optimiser
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
from ..optimiser import Optimiser
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
from ..optimiser import Optimiser

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
        self.commands = (# pngnq seems to degrade visual quality, disable for now
                         #'pngnq -n 256 "__INPUT__"',
                         pngcrush,
                         )

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
import os
import shlex
import subprocess
import sys
import shutil
import logging
import tempfile
from ..scratch import Scratch

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
        pass
        #self.stdout.destruct()
        #self.stderr.destruct()

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
            #logging.info("Executing %s" % (command))
            args = shlex.split(command)

            pngnq = command.startswith('pngnq')
            if pngnq:
                # work around pngnq's __retarded__ output options
                di = tempfile.mkdtemp()
                args[1:1] = ['-d', di]

                # if there's -o stuff, remove it
                if '-o' in args:
                    oi = args.index('-o')
                    args[oi:oi+2] = []
                
            try:
                retcode = subprocess.call(args, stdout=self.stdout.opened, stderr=self.stderr.opened)
            except OSError:
                logging.error("Error executing command %s. Error was %s" % (command, OSError))
                sys.exit(1)

            if pngnq:
                output_file_name = os.path.join(di, os.listdir(di)[0])
            
            if retcode != 0:
                # gifsicle seems to fail by the file size?
                os.unlink(output_file_name)
            else:
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
        pass
        #if self._path != None:
        #    self.destruct()

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
        for dir in kwargs.get('exclude', []):
            if len(dir) == 0:
                continue
            self.exclude[dir] = True
        self.quiet = kwargs.get('quiet')
        self.identify_mime = kwargs.get('identify_mime')

        # setup tempfile for stdout and stderr
        self.stdout = Scratch()
        self.stderr = Scratch()

    def __del__(self):
        pass
        #self.stdout.destruct()
        #self.stderr.destruct()

    def smush(self, file):
        """
        Optimises a file
        """
        key = self.__get_image_format(file)

        if key in self.optimisers:
            #logging.info('optimising file %s' % (file))
            self.__files_scanned += 1
            self.optimisers[key].set_input(file)
            self.optimisers[key].optimise()
            
    __smush = smush

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
__FILENAME__ = store
from path import path
import logging
from collections import defaultdict, namedtuple
try:
    import simplejson as json
except ImportError:
    import json

SubStore = namedtuple('SubStore', 'name init filename mapping')
'''
init is a function to initialize and re-vivify the individual substore
mapping is a tuple consisting of the respective key, value data types in order to load
from JSON
'''

class Store(object):
    '''
    Keeps track of optimized files, backups and potentially persists them to disk
    the actual attributes get created dynamically with get/setattr
    '''
    STORES = (
        # used if we modify a file and don't want watchdog to pick it up
        SubStore('ignored', lambda *args:defaultdict(int, *args), 'ignored.json', (path, None)),

        # used to restore original files in case of --revert
        SubStore('originals', dict, 'originals.json', (path, path)),

        # maintained to quickly check if a stored original has been modified
        # if we mark it and ask what to do upon --revert
        SubStore('storedat', dict, 'storedat.json', (path, str)),
        )

    def __init__(self, dir=None):
        self.filepaths = {}
        self.clear()
        self.dir = dir
        if dir is not None:
            self.load(dir)

    def clear(self):
        '''initialize data stores to emptiness'''
        for substore in self.STORES:
            setattr(self, substore.name, substore.init())

    def load(self, dir):
        '''tries to load files from the dir,
        if the directory or a file doesn't exist, do nothing'''
        dir = self.dir = path(dir)
        if not dir.exists():
            return
        for substore in self.STORES:
            name = substore.name
            filepath = dir.joinpath(substore.filename)
            self.filepaths[name] = filepath
            try:
                with open(filepath) as f:
                    loaded = json.load(f)
                k_type, v_type = substore.mapping
                value = substore.init((k_type(k), v_type(v)) for k, v in loaded.iteritems())
                setattr(self, name, value)
            except:
                msg = "couldn't load %s from %s"
                if not filepath.exists():
                    msg += ', no such file'
                logging.debug(msg, name, filepath, exc_info=True)
            else:
                logging.debug('successfully loaded %s from %s', name, filepath)

    def save(self):
        '''save to disk, creates directory if necessary'''
        dir = self.dir
        if dir is None:
            return
        if not dir.exists():
            dir.makedirs_p()
        for substore in self.STORES:
            with open(self.filepaths[substore.name], 'w') as f:
                json.dump(getattr(self, substore.name), f)

    def ignore(self, item, n=1):
        '''increment the counter inside ignored,
        which causes events to that path to be ignored n times'''
        self.ignored[item] += n

    def wants(self, pth):
        '''
        Returns if the pth is supposed to be optimized
        to work around watchdog picking up modified file paths at an indeterminate point
        in time, we maintain a counter of how many times to ignore it
        e.g. if we create a new file in a directory that watchdog is watching we can expect
        to receive 2 events, file_created and file_modified and increase its counter to 2
        '''
        counter = self.ignored[pth]
        if counter < 0:
            # ignore indefinitely
            return False
        elif counter > 0:
            self.ignored[pth] -= 1
            return False
        # 0 default case
        return True

store = Store()


########NEW FILE########
__FILENAME__ = context
import sys, os
sys.path.insert(0, os.path.abspath('../..'))

import imagy
reload(imagy)

########NEW FILE########
__FILENAME__ = imgtest
from __future__ import division
from path import path
from subprocess import Popen, call
import unittest
from operator import eq
from tempfile import mkdtemp
import time
from collections import OrderedDict

QUIET = 1

class ImagyTestCase(unittest.TestCase):
    # use ordereddict so we can selectively only test against a couple of files
    # and also specify which ones come first in `copy_images_over` (since the
    # jpg is the fastest to optimize)
    image_files = OrderedDict([
        ('jpg', 'jpg.jpg'),
        ('gifgif', 'gifgif.gif'),
        ('png', 'png.png'),
        ('gif', 'gif.gif'),
        ])
    imagy = ['imagy']
    if QUIET:
        imagy += ['-q']
    imagy_mem = imagy + ['-m']

    def __init__(self, *args, **kwargs):
        super(ImagyTestCase, self).__init__(*args, **kwargs)
        self.root = path(__file__)
        self.image_loc = self.root.parent.joinpath('images')
        self.images = OrderedDict((k, self.image_loc.joinpath(v)) for k,v in
                                   self.image_files.items())

    def setUp(self, *args, **kwargs):
        self.__setup(*args, **kwargs)
        if not self.__setup is self.setup:
            self.setup(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        self.__teardown(*args, **kwargs)
        if not self.__teardown is self.teardown:
            self.teardown(*args, **kwargs)

    def setup(self):
        self.tmp = path(mkdtemp())
        self.proc = None
    __setup = setup

    def teardown(self):
        if self.tmp.exists():
            self.tmp.rmtree()
        if isinstance(self.proc, Popen):
            self.proc.terminate()
    __teardown = teardown

    def img_path(self, img):
        return self.tmp.joinpath(self.image_files[img])

    def wait_until_passes(self, valfun, genfun=eq, classfun='assertEqual', sleep=7, res=0.5):
        '''
        doing system testing with unittest ... why not?!
        wait upto `sleep` seconds for the test to pass,
        checking with a general function until doing a final test
        with the one associated with the respective TestCase
        '''
        classfun = getattr(self, classfun)
        for _ in range(int(sleep/res)):
            if genfun(*valfun()):
                break
            time.sleep(res)
        classfun(*valfun())

    def start(self, *args, **kwargs):
        starter = kwargs.setdefault('starter', Popen)
        args = self.imagy + list(args)
        if not '-f' in args:
            args += [self.tmp]
        self.proc = starter(args)

    def copy_images_over(self, n):
        call(['cp'] + self.images.values()[:n] + [self.tmp])

########NEW FILE########
__FILENAME__ = test_core
# -*- coding: utf-8 -*-

import unittest
from imgtest import ImagyTestCase
from imagy.config import *
from imagy.core import *
from imagy.store import Store

import logging
logging.disable(logging.CRITICAL)

class CoreTestSuite(ImagyTestCase):
    def setup(self):
        self.s = Store()
        self.copy_images_over()

    def check_image(self, img):
        img = self.img_path(img)
        sz = img.size
        optimize_with_touch(img)
        self.assertTrue(sz >= img.size)

    def test_store_original(self):
        img = self.img_path('jpg')
        orig = store_original(img)
        self.assertTrue(same_file(img, orig))
        orig.remove()

    def test_make_path(self):
        self.assertFalse(make_path(__file__).exists())

    def test_clear(self):
        thing = 'thing'
        self.s.originals[thing] = ''
        self.s.clear()
        self.s.save()
        self.assertFalse(thing in self.s.originals)

def main():
    # dynamically add tests for various file formats, SO FN DRY
    for typ in ImagyTestCase.image_files:
        fn = lambda self:self.check_image(typ)
        setattr(CoreTestSuite, 'test_%s' % typ, fn)
    unittest.main()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_system
# -*- coding: utf-8 -*-

import unittest
from imgtest import *
from imagy.config import *
from imagy.core import *
# todo: be less like http://farm3.static.flickr.com/2465/3898431077_b9c5583b12.jpg

import logging
logging.disable(logging.CRITICAL)

ORIGINALS = '*%s*' % ORIGINAL_IDENTIFIER

class SystemTestSuite(ImagyTestCase):
    """Test system's behavior from afar"""

    def test_watch(self):
        self.start('-m')
        # give time for imagy to start
        time.sleep(2)
        self.copy_images_over(1)
        valfun = lambda:(2, len(self.tmp.files()))
        self.wait_until_passes(valfun, sleep=20)

    def test_init_revert(self):
        self.copy_images_over(1)
        self.start('--no-watch', starter=call)
        valfun = lambda:(2, len(self.tmp.files()))
        self.wait_until_passes(valfun)
        self.start('-r', starter=call)
        valfun = lambda:(1, len(self.tmp.files()))
        self.wait_until_passes(valfun)

    def test_del_originals(self):
        self.copy_images_over(1)
        self.start('--no-watch', starter=call)
        valfun = lambda:(2, len(self.tmp.files()))
        self.wait_until_passes(valfun)
        self.start('--deloriginals', starter=call)
        valfun = lambda:(1, len(self.tmp.files()))
        self.wait_until_passes(valfun)

    def test_files_mode(self):
        self.copy_images_over(1)
        self.start('-m', '-f', *self.tmp.files(), starter=call)
        self.assertEqual(2, len(self.tmp.files()))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = utils
from path import path
from tempfile import NamedTemporaryFile
import os
from filecmp import _sig, cmp as same_file

# the mark that is used to identify stored originals that have been modified
MARK = '!'

def make_path(p, sep='_'):
    '''Find a similar, yet unused path'''
    p = path(p)
    name, ext = p.splitext()
    n = 1
    while p.exists():
        p = path('%s%s%s%s' % (name, sep, n, ext))
        n += 1
    return p

def mktemp():
    f = NamedTemporaryFile(delete=False)
    f.close()
    loc = path(f.name).abspath()
    loc.remove()
    return loc

def file_sig(pth):
    '''
    a signature of the file,
    if this remains the same we can be pretty sure that the file hasn't been changed
    '''
    return _sig(os.stat(pth))

def dump(store):
    '''for debugging purposes'''
    from pprint import pprint
    for p in (store.originals, store.storedat, store.ignored):
        pprint(p)

def callable_or_value(obj):
    if callable(obj):
        return obj()
    return obj

########NEW FILE########
__FILENAME__ = watch
from config import *
import core
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import logging
from path import path

running = False

class OptimizationHandler(FileSystemEventHandler):
    '''Subclassing Watchdog to specify our own handling of files'''
    def handle_event(self, event):
        # convert to an abspath as soon as possible, if relative paths enter the system
        # things start to break
        pth = path(event.src_path).abspath()
        if not pth.isdir() and core.correct_ext(pth):
            core.handle_evented_file(pth)

    def on_created(self, event):
        if not OPTIMIZE_ON_CREATE:
            return
        super(OptimizationHandler, self).on_created(event)
        self.handle_event(event)

    def on_modified(self, event):
        if not OPTIMIZE_ON_CHANGE:
            return
        super(OptimizationHandler, self).on_modified(event)
        self.handle_event(event)

class Watcher(object):
    def __init__(self, event_handler_cls, observer_cls=None):
        if observer_cls is None:
            self.observer_cls = Observer
        self.event_handler_cls = event_handler_cls
        self.running = False

    def add(self, *dirs):
        dirs = [path(dir).abspath() for dir in dirs]
        for dir in dirs:
            if dir.isdir():
                self.observer.schedule(self.event_handler, path=dir, recursive=True)
                logging.warning('watching %s', dir)
            else:
                logging.warning('%s is not a directory', dir)

    def run(self, *dirs):
        self.event_handler = self.event_handler_cls()
        self.observer = self.observer_cls()
        self.add(*dirs)
        if not self.observer._watches:
            logging.error('No valid directories specified.')
            return

        self.running = True
        self.observer.start()
        logging.info('waiting for files')
        logging.info('Ctrl-C to quit')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

watcher = Watcher(OptimizationHandler)

########NEW FILE########
