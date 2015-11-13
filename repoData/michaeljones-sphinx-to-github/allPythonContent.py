__FILENAME__ = sphinxtogithub
#! /usr/bin/env python
 
from optparse import OptionParser

import os
import sys
import shutil
import codecs


class DirHelper(object):

    def __init__(self, is_dir, list_dir, walk, rmtree):

        self.is_dir = is_dir
        self.list_dir = list_dir
        self.walk = walk
        self.rmtree = rmtree

class FileSystemHelper(object):

    def __init__(self, open_, path_join, move, exists):

        self.open_ = open_
        self.path_join = path_join
        self.move = move
        self.exists = exists

class Replacer(object):
    "Encapsulates a simple text replace"

    def __init__(self, from_, to):

        self.from_ = from_
        self.to = to

    def process(self, text):

        return text.replace( self.from_, self.to )

class FileHandler(object):
    "Applies a series of replacements the contents of a file inplace"

    def __init__(self, name, replacers, opener):

        self.name = name
        self.replacers = replacers
        self.opener = opener

    def process(self):

        text = self.opener(self.name, "r").read()

        for replacer in self.replacers:
            text = replacer.process( text )

        self.opener(self.name, "w").write(text)

class Remover(object):

    def __init__(self, exists, remove):
        self.exists = exists
        self.remove = remove

    def __call__(self, name):

        if self.exists(name):
            self.remove(name)

class ForceRename(object):

    def __init__(self, renamer, remove):

        self.renamer = renamer
        self.remove = remove

    def __call__(self, from_, to):

        self.remove(to)
        self.renamer(from_, to)

class VerboseRename(object):

    def __init__(self, renamer, stream):

        self.renamer = renamer
        self.stream = stream

    def __call__(self, from_, to):

        self.stream.write(
                "Renaming directory '%s' -> '%s'\n"
                    % (os.path.basename(from_), os.path.basename(to))
                )

        self.renamer(from_, to)


class DirectoryHandler(object):
    "Encapsulates renaming a directory by removing its first character"

    def __init__(self, name, root, renamer):

        self.name = name
        self.new_name = name[1:]
        self.root = root + os.sep
        self.renamer = renamer

    def path(self):

        return os.path.join(self.root, self.name)

    def relative_path(self, directory, filename):

        path = directory.replace(self.root, "", 1)
        return os.path.join(path, filename)

    def new_relative_path(self, directory, filename):

        path = self.relative_path(directory, filename)
        return path.replace(self.name, self.new_name, 1)

    def process(self):

        from_ = os.path.join(self.root, self.name)
        to = os.path.join(self.root, self.new_name)
        self.renamer(from_, to)


class HandlerFactory(object):

    def create_file_handler(self, name, replacers, opener):

        return FileHandler(name, replacers, opener)

    def create_dir_handler(self, name, root, renamer):

        return DirectoryHandler(name, root, renamer)


class OperationsFactory(object):

    def create_force_rename(self, renamer, remover):

        return ForceRename(renamer, remover)

    def create_verbose_rename(self, renamer, stream):

        return VerboseRename(renamer, stream)

    def create_replacer(self, from_, to):

        return Replacer(from_, to)

    def create_remover(self, exists, remove):

        return Remover(exists, remove)


class Layout(object):
    """
    Applies a set of operations which result in the layout
    of a directory changing
    """

    def __init__(self, directory_handlers, file_handlers):

        self.directory_handlers = directory_handlers
        self.file_handlers = file_handlers

    def process(self):

        for handler in self.file_handlers:
            handler.process()

        for handler in self.directory_handlers:
            handler.process()


class NullLayout(object):
    """
    Layout class that does nothing when asked to process
    """
    def process(self):
        pass

class LayoutFactory(object):
    "Creates a layout object"

    def __init__(self, operations_factory, handler_factory, file_helper, dir_helper, verbose, stream, force):

        self.operations_factory = operations_factory
        self.handler_factory = handler_factory

        self.file_helper = file_helper
        self.dir_helper = dir_helper

        self.verbose = verbose
        self.output_stream = stream
        self.force = force

    def create_layout(self, path):

        contents = self.dir_helper.list_dir(path)

        renamer = self.file_helper.move

        if self.force:
            remove = self.operations_factory.create_remover(self.file_helper.exists, self.dir_helper.rmtree)
            renamer = self.operations_factory.create_force_rename(renamer, remove) 

        if self.verbose:
            renamer = self.operations_factory.create_verbose_rename(renamer, self.output_stream) 

        # Build list of directories to process
        directories = [d for d in contents if self.is_underscore_dir(path, d)]
        underscore_directories = [
                self.handler_factory.create_dir_handler(d, path, renamer)
                    for d in directories
                ]

        if not underscore_directories:
            if self.verbose:
                self.output_stream.write(
                        "No top level directories starting with an underscore "
                        "were found in '%s'\n" % path
                        )
            return NullLayout()

        # Build list of files that are in those directories
        replacers = []
        for handler in underscore_directories:
            for directory, dirs, files in self.dir_helper.walk(handler.path()):
                for f in files:
                    replacers.append(
                            self.operations_factory.create_replacer(
                                handler.relative_path(directory, f),
                                handler.new_relative_path(directory, f)
                                )
                            )

        # Build list of handlers to process all files
        filelist = []
        for root, dirs, files in self.dir_helper.walk(path):
            for f in files:
                if f.endswith(".html"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                replacers,
                                self.file_helper.open_)
                            )
                if f.endswith(".js"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                [self.operations_factory.create_replacer("'_sources/'", "'sources/'")],
                                self.file_helper.open_
                                )
                            )

        return Layout(underscore_directories, filelist)

    def is_underscore_dir(self, path, directory):

        return (self.dir_helper.is_dir(self.file_helper.path_join(path, directory))
            and directory.startswith("_"))



def sphinx_extension(app, exception):
    "Wrapped up as a Sphinx Extension"

    if not app.builder.name in ("html", "dirhtml"):
        return

    if not app.config.sphinx_to_github:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Disabled, doing nothing."
        return

    if exception:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Exception raised in main build, doing nothing."
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            lambda f, mode: codecs.open(f, mode, app.config.sphinx_to_github_encoding),
            os.path.join,
            shutil.move,
            os.path.exists
            )

    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            app.config.sphinx_to_github_verbose,
            sys.stdout,
            force=True
            )

    layout = layout_factory.create_layout(app.outdir)
    layout.process()


def setup(app):
    "Setup function for Sphinx Extension"

    app.add_config_value("sphinx_to_github", True, '')
    app.add_config_value("sphinx_to_github_verbose", True, '')
    app.add_config_value("sphinx_to_github_encoding", 'utf-8', '')

    app.connect("build-finished", sphinx_extension)


def main(args):

    usage = "usage: %prog [options] <html directory>"
    parser = OptionParser(usage=usage)
    parser.add_option("-v","--verbose", action="store_true",
            dest="verbose", default=False, help="Provides verbose output")
    parser.add_option("-e","--encoding", action="store",
            dest="encoding", default="utf-8", help="Encoding for reading and writing files")
    opts, args = parser.parse_args(args)

    try:
        path = args[0]
    except IndexError:
        sys.stderr.write(
                "Error - Expecting path to html directory:"
                "sphinx-to-github <path>\n"
                )
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            lambda f, mode: codecs.open(f, mode, opts.encoding),
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            opts.verbose,
            sys.stdout,
            force=False
            )

    layout = layout_factory.create_layout(path)
    layout.process()
    


if __name__ == "__main__":
    main(sys.argv[1:])




########NEW FILE########
__FILENAME__ = directoryhandler

import unittest
import os

import sphinxtogithub


class MockRenamer(object):

    def __call__(self, from_, to):

        self.from_ = from_
        self.to = to

class TestDirectoryHandler(unittest.TestCase):

    def setUp(self):

        self.directory = "_static"
        self.new_directory = "static"
        self.root = os.path.join("build", "html")
        renamer = MockRenamer()
        self.dir_handler = sphinxtogithub.DirectoryHandler(self.directory, self.root, renamer)

    def tearDown(self):
        
        self.dir_handler = None
    

    def testPath(self):

        self.assertEqual(self.dir_handler.path(), os.path.join(self.root, self.directory))

    def testRelativePath(self):

        dir_name = "css"
        dir_path = os.path.join(self.root, self.directory, dir_name)
        filename = "cssfile.css"

        self.assertEqual(
                self.dir_handler.relative_path(dir_path, filename),
                os.path.join(self.directory, dir_name, filename)
                )

    def testNewRelativePath(self):

        dir_name = "css"
        dir_path = os.path.join(self.root, self.directory, dir_name)
        filename = "cssfile.css"

        self.assertEqual(
                self.dir_handler.new_relative_path(dir_path, filename),
                os.path.join(self.new_directory, dir_name, filename)
                )

    def testProcess(self):

        self.dir_handler.process()

        self.assertEqual(
                self.dir_handler.renamer.to,
                os.path.join(self.root, self.new_directory)
                )

        self.assertEqual(
                self.dir_handler.renamer.from_,
                os.path.join(self.root, self.directory)
                )


def testSuite():
    suite = unittest.TestSuite()

    suite.addTest(TestDirectoryHandler("testPath"))
    suite.addTest(TestDirectoryHandler("testRelativePath"))
    suite.addTest(TestDirectoryHandler("testNewRelativePath"))
    suite.addTest(TestDirectoryHandler("testProcess"))

    return suite


########NEW FILE########
__FILENAME__ = filehandler

import unittest

import sphinxtogithub

class MockFileObject(object):

    before = """
    <title>Breathe's documentation &mdash; BreatheExample v0.0.1 documentation</title>
    <link rel="stylesheet" href="_static/default.css" type="text/css" />
    <link rel="stylesheet" href="_static/pygments.css" type="text/css" />
    """

    after = """
    <title>Breathe's documentation &mdash; BreatheExample v0.0.1 documentation</title>
    <link rel="stylesheet" href="static/default.css" type="text/css" />
    <link rel="stylesheet" href="static/pygments.css" type="text/css" />
    """

    def read(self):

        return self.before

    def write(self, text):

        self.written = text

class MockOpener(object):

    def __init__(self):

        self.file_object = MockFileObject()

    def __call__(self, name, readmode="r"):
        
        self.name = name

        return self.file_object



class TestFileHandler(unittest.TestCase):

    def testProcess(self):

        filepath = "filepath"
        
        opener = MockOpener()
        file_handler = sphinxtogithub.FileHandler(filepath, [], opener)

        file_handler.process()

        self.assertEqual(opener.file_object.written, MockFileObject.before)
        self.assertEqual(opener.name, filepath)

    def testProcessWithReplacers(self):

        filepath = "filepath"
        
        replacers = []
        replacers.append(sphinxtogithub.Replacer("_static/default.css", "static/default.css"))
        replacers.append(sphinxtogithub.Replacer("_static/pygments.css", "static/pygments.css"))

        opener = MockOpener()
        file_handler = sphinxtogithub.FileHandler(filepath, replacers, opener)

        file_handler.process()

        self.assertEqual(opener.file_object.written, MockFileObject.after)



def testSuite():
    suite = unittest.TestSuite()

    suite.addTest(TestFileHandler("testProcess"))
    suite.addTest(TestFileHandler("testProcessWithReplacers"))

    return suite


########NEW FILE########
__FILENAME__ = layout

from sphinxtogithub.tests import MockExists, MockRemove

import sphinxtogithub
import unittest

class MockHandler(object):

    def __init__(self):

        self.processed = False

    def process(self):

        self.processed = True



class TestLayout(unittest.TestCase):

    def testProcess(self):

        directory_handlers = []
        file_handlers = []

        for i in range(0, 10):
            directory_handlers.append(MockHandler())
        for i in range(0, 5):
            file_handlers.append(MockHandler())

        layout = sphinxtogithub.Layout(directory_handlers, file_handlers)

        layout.process()

        # Check all handlers are processed by reducing them with "and"
        self.assert_(reduce(lambda x, y: x and y.processed, directory_handlers, True))
        self.assert_(reduce(lambda x, y: x and y.processed, file_handlers, True))


def testSuite():
    suite = unittest.TestSuite()

    suite.addTest(TestLayout("testProcess"))

    return suite


########NEW FILE########
__FILENAME__ = layoutfactory

from sphinxtogithub.tests import MockStream

import sphinxtogithub
import unittest
import os
import shutil

root = "test_path"
dirs = ["dir1", "dir2", "dir_", "d_ir", "_static", "_source"]
files = ["file1.html", "nothtml.txt", "file2.html", "javascript.js"]

def mock_is_dir(path):

    directories = [ os.path.join(root, dir_) for dir_ in dirs ]

    return path in directories

def mock_list_dir(path):

    contents = []
    contents.extend(dirs)
    contents.extend(files)
    return contents

def mock_walk(path):

    yield path, dirs, files

class MockHandlerFactory(object):

    def create_file_handler(self, name, replacers, opener):

        return sphinxtogithub.FileHandler(name, replacers, opener)

    def create_dir_handler(self, name, root, renamer):

        return sphinxtogithub.DirectoryHandler(name, root, renamer)


class TestLayoutFactory(unittest.TestCase):

    def setUp(self):

        verbose = True
        force = False
        stream = MockStream()
        dir_helper = sphinxtogithub.DirHelper(
            mock_is_dir,
            mock_list_dir,
            mock_walk,
            shutil.rmtree
            )

        file_helper = sphinxtogithub.FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )

        operations_factory = sphinxtogithub.OperationsFactory()
        handler_factory = MockHandlerFactory()

        self.layoutfactory = sphinxtogithub.LayoutFactory(
                operations_factory,
                handler_factory,
                file_helper,
                dir_helper,
                verbose,
                stream,
                force
                )

    def tearDown(self):
        
        self.layoutfactory = None

    def testUnderscoreCheck(self):

        func = self.layoutfactory.is_underscore_dir
        self.assert_(func(root, "_static"))
        self.assert_(not func(root, "dir_"))
        self.assert_(not func(root, "d_ir"))
        self.assert_(not func(root, "dir1"))


    def testCreateLayout(self):

        layout = self.layoutfactory.create_layout(root)

        dh = layout.directory_handlers
        self.assertEqual(dh[0].name, "_static")
        self.assertEqual(dh[1].name, "_source")
        self.assertEqual(len(dh), 2)
        
        fh = layout.file_handlers
        self.assertEqual(fh[0].name, os.path.join(root,"file1.html"))
        self.assertEqual(fh[1].name, os.path.join(root,"file2.html"))
        self.assertEqual(fh[2].name, os.path.join(root,"javascript.js"))
        self.assertEqual(len(fh), 3)




def testSuite():
    suite = unittest.TestSuite()

    suite.addTest(TestLayoutFactory("testUnderscoreCheck"))
    suite.addTest(TestLayoutFactory("testCreateLayout"))

    return suite


########NEW FILE########
__FILENAME__ = remover

from sphinxtogithub.tests import MockExists, MockRemove

import sphinxtogithub
import unittest

class TestRemover(unittest.TestCase):

    def testCall(self):

        exists = MockExists()
        remove = MockRemove()
        remover = sphinxtogithub.Remover(exists, remove)

        filepath = "filepath"
        remover(filepath)

        self.assertEqual(filepath, exists.name)
        self.assertEqual(filepath, remove.name)


def testSuite():
    suite = unittest.TestSuite()

    suite.addTest(TestRemover("testCall"))

    return suite


########NEW FILE########
__FILENAME__ = renamer

from sphinxtogithub.tests import MockExists, MockRemove, MockStream

import sphinxtogithub
import unittest
import os



class MockRename(object):

    def __call__(self, from_, to):
        self.from_ = from_
        self.to = to

class TestForceRename(unittest.TestCase):

    def testCall(self):

        rename = MockRename()
        remove = MockRemove()
        renamer = sphinxtogithub.ForceRename(rename, remove)

        from_ = "from"
        to = "to"
        renamer(from_, to)

        self.assertEqual(rename.from_, from_)
        self.assertEqual(rename.to, to)
        self.assertEqual(remove.name, to)


class TestVerboseRename(unittest.TestCase):

    def testCall(self):

        rename = MockRename()
        stream = MockStream()
        renamer = sphinxtogithub.VerboseRename(rename, stream)

        from_ = os.path.join("path", "to", "from")
        to = os.path.join("path", "to", "to")
        renamer(from_, to)

        self.assertEqual(rename.from_, from_)
        self.assertEqual(rename.to, to)
        self.assertEqual(
                stream.msgs[0],
                "Renaming directory '%s' -> '%s'\n" % (os.path.basename(from_), os.path.basename(to))
                )



def testSuite():
    suite = unittest.TestSuite()

    suite.addTest(TestForceRename("testCall"))
    suite.addTest(TestVerboseRename("testCall"))

    return suite


########NEW FILE########
__FILENAME__ = replacer

import unittest

import sphinxtogithub

class TestReplacer(unittest.TestCase):

    before = """
    <title>Breathe's documentation &mdash; BreatheExample v0.0.1 documentation</title>
    <link rel="stylesheet" href="_static/default.css" type="text/css" />
    <link rel="stylesheet" href="_static/pygments.css" type="text/css" />
    """

    after = """
    <title>Breathe's documentation &mdash; BreatheExample v0.0.1 documentation</title>
    <link rel="stylesheet" href="static/default.css" type="text/css" />
    <link rel="stylesheet" href="_static/pygments.css" type="text/css" />
    """

    def testReplace(self):

        replacer = sphinxtogithub.Replacer("_static/default.css", "static/default.css")
        self.assertEqual(replacer.process(self.before), self.after)


def testSuite():

    suite = unittest.TestSuite()

    suite.addTest(TestReplacer("testReplace"))

    return suite



########NEW FILE########
