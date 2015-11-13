__FILENAME__ = pybuild
#!/usr/bin/env python
# coding:utf-8

import sys, os, re
import distutils.core, py2exe
import optparse
import shutil
import zipfile

manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1"
manifestVersion="1.0">
<assemblyIdentity
    version="0.64.1.0"
    processorArchitecture="x86"
    name="Controls"
    type="win32"
/>
<description>Test Program</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.VC90.CRT"
            version="9.0.30729.4918"
            processorArchitecture="X86"
            publicKeyToken="1fc8b3b9a1e18e3b"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''

RT_MANIFEST = 24

class Py2exe(py2exe.build_exe.py2exe):
    """A py2exe which archive *.py files to zip"""
    def make_lib_archive(self, zip_filename, base_dir, files,
                         verbose=0, dry_run=0):
        from distutils.dir_util import mkpath
        if not self.skip_archive:
            # Like distutils "make_archive", but we can specify the files
            # to include, and the compression to use - default is
            # ZIP_STORED to keep the runtime performance up.  Also, we
            # don't append '.zip' to the filename.
            mkpath(os.path.dirname(zip_filename), dry_run=dry_run)

            if self.compressed:
                compression = zipfile.ZIP_DEFLATED
            else:
                compression = zipfile.ZIP_STORED

            if not dry_run:
                z = zipfile.ZipFile(zip_filename, "w",
                                    compression=compression)
                for f in files:
                    try:
                        z.write((os.path.join(x, f[:-1]) for x in sys.path if os.path.isfile(os.path.join(x, f[:-1]))).next(), f[:-1])
                    except:
                        z.write(os.path.join(base_dir, f), f)
                z.close()

            return zip_filename
        else:
            # Don't really produce an archive, just copy the files.
            from distutils.file_util import copy_file

            destFolder = os.path.dirname(zip_filename)

            for f in files:
                d = os.path.dirname(f)
                if d:
                    mkpath(os.path.join(destFolder, d), verbose=verbose, dry_run=dry_run)
                copy_file(
                          os.path.join(base_dir, f),
                          os.path.join(destFolder, f),
                          preserve_mode=0,
                          verbose=verbose,
                          dry_run=dry_run
                         )
            return '.'


def optparse_options_to_dist_options(filename, options):
    basename = os.path.splitext(os.path.basename(filename))[0]

    mode = 'windows' if options.windowed else 'console'
    mode_options = {'script'          : filename,
                    'description'     : options.description or 'https://github.com/goagent/pybuild',
                    'version'         : options.version or '1.0.0.0',
                    'name'            : options.name or basename,
                    'company_name'    : options.company or 'goagent.org',
                    'copyright'       : options.copyright or 'GPL License',
                    'icon_resources'  : [(1, options.icon)] if options.icon else [],
                    'other_resources' : [(RT_MANIFEST, 1, manifest_template % dict(prog=basename))] if mode == 'windows' else [],
                    }

    py2exe_options = {'dist_dir'     : 'dist',
                      'compressed'   : 1,
                      'optimize'     : 1,
                      'dll_excludes' : ['w9xpopen.exe', 'MSVCP90.dll', 'mswsock.dll', 'powrprof.dll'],
                      'ascii'        : options.ascii or False,
                      'bundle_files' : options.bundle or 1,
                      'excludes'     : options.excludes.split(',') or [],
                     }

    zipfile = options.zipfile

    return { mode      :  [mode_options],
            'zipfile'  :  zipfile,
            'options'  :  {'py2exe' : py2exe_options},
            'cmdclass' :  {'py2exe' : Py2exe},
            }

def finalize(windows=None, console=None, service=None, com_server=None, ctypes_com_server=None, zipfile=None, options=None, cmdclass=None):
    shutil.rmtree('build')
    mode = [x for x in (windows, console, service, com_server, ctypes_com_server) if x is not None][0][0]
    py2exe_options = options['py2exe']
    basename = os.path.splitext(os.path.basename(mode['script']))[0]
    if py2exe_options['bundle_files'] == 1:
        dist_files = ['%s.exe' % basename]
        if zipfile is not None:
            dist_files += [zipfile]
        dist_dir = py2exe_options.get('dist_dir', 'dist')
        for filename in dist_files:
            shutil.move(os.path.join(dist_dir, filename), filename)
        shutil.rmtree(dist_dir)

def main():
    parser = optparse.OptionParser(usage='usage: %prog [options] filename')
    parser.add_option("-w", "--windowed", dest="windowed", action="store_true", default=False, help="Use the Windows subsystem executable.")
    parser.add_option("-a", "--ascii",    dest="ascii",    action="store_true", default=False, help="do not include encodings.")
    parser.add_option("-b", "--bundle",   dest="bundle",   type="int",    metavar="LEVEL",  help="produce a bundle_files deployment.")
    parser.add_option("-v", "--version",  dest="version",  type="string", metavar="number", help="add version number to the executable.")
    parser.add_option("-d", "--description",  dest="description",  type="string", help="add description to the executable.")
    parser.add_option("-C", "--copyright",  dest="copyright",  type="string", help="add copyright to the executable.")
    parser.add_option("-n", "--name",     dest="name",     type="string", help="add name string to the executable.")
    parser.add_option("-c", "--company",  dest="company",  type="string", help="add company string to the executable.")
    parser.add_option("-i", "--icon"   ,  dest="icon",     type="string", metavar="file.ico", help="add file.ico to the executable's resources.")
    parser.add_option("-z", "--zipfile",  dest="zipfile",  type="string", metavar="file.zip", help="add file.zip to the extra resources.")
    parser.add_option("-x", "--excludes", dest="excludes", type="string", default='', help="py2exe excludes packages.")

    options, args = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        sys.exit(0)
    else:
        print options, args

    filename = args[0]
    dist_options = optparse_options_to_dist_options(filename, options)
    print dist_options

    sys.argv[1:] = ['py2exe', '-q']
    distutils.core.setup(**dist_options)
    finalize(**dist_options)

    if sys.version_info[:2] > (2, 5):
        print "you need vc2008redist['Microsoft.VC90.CRT.manifest', 'msvcr90.dll']"

if __name__ == '__main__':
    main()
########NEW FILE########
__FILENAME__ = python27
#!/usr/bin/env python
# inspired from https://raw.github.com/schmir/bbfreeze/master/bbfreeze/py.py

import sys
import os
sys.path.append(os.path.dirname(getattr(sys,'executable',sys.argv[0])) or '.')
try:
    import zipextimporter
    zipextimporter.install()
except:
    pass

def parse_options(args, spec):
    needarg = dict()
    for x in spec.split():
        if x.endswith('='):
            needarg[x[:-1]] = True
        else:
            needarg[x] = False
    options = []
    newargs = []
    i = 0
    while i < len(args):
        a, v = (args[i].split('=', 1) + [None])[:2]
        if a in needarg:
            if v is None and needarg[a]:
                i += 1
                try:
                    v = args[i]
                except IndexError:
                    raise Exception('option %s needs an argument' % (a, ))
            options.append((a, v))
            if a in ('-c', '-m'):
                break
        else:
            break
        i += 1
    newargs.extend(args[i:])
    return options, newargs

options, args = parse_options(sys.argv[1:], '-u -h -B -V -x -c= -m=')
options = dict(options)
sys.argv = args or ['']

main = __import__('__main__')

if '-B' in options or os.getenv('PYTHONDONTWRITEBYTECODE'):
    sys.dont_write_bytecode = True
if '-u' in options or os.getenv('PYTHONUNBUFFERED'):
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

if '-h' in options:
    print """
usage: python [option] ... [-c cmd | file] [arg] ...
Options and arguments (and corresponding environment variables):
-B     : don't write .py[co] files on import; also PYTHONDONTWRITEBYTECODE=x
-c cmd : program passed in as string (terminates option list)
-h     : print this help message and exit
-u     : unbuffered binary stdout and stderr; also PYTHONUNBUFFERED=x
         see man page for details on internal buffering relating to '-u'
-V     : print the Python version number and exit (also --version)
-x     : skip first line of source, allowing use of non-Unix forms of #!cmd
file   : program read from script file
arg ...: arguments passed to program in sys.argv[1:]
    """.strip()
elif '-V' in options:
    sys.stdout.write('python %s\n' % sys.version.split()[0])
elif options.get('-m') is not None:
    get_loader = getattr(__import__('imp'), 'get_loader', None) or getattr(__import__('pkgutil'), 'get_loader')
    codeobj = get_loader(options['-m']).get_code(options['-m'])
    main.__dict__ ['__file__'] = codeobj.co_filename
    exec codeobj in main.__dict__
elif options.get('-c') is not None:
    exec options.get('-c') in main.__dict__
elif sys.argv[0]:
    if sys.argv[0].endswith('.zip'):
        import zipimport
        importer = zipimport.zipimporter(sys.argv[0])
        sys.path.insert(0, sys.argv[0])
        main.__dict__['__file__'] = os.path.join(os.path.abspath(sys.argv[0]), '__main__.py')
        exec importer.get_code('__main__') in main.__dict__
    else:
        codeobj = None
        with open(sys.argv[0], 'rb') as fp:
            if '-x' in options:
                fp.readline()
            content = fp.read()
            main.__dict__['__file__'] = os.path.abspath(sys.argv[0])
            if content.startswith('\x03\xf3\r\n'):
                codeobj = __import__('marshal').loads(content[8:])
            else:
                codeobj = compile(content, filename=sys.argv[0], mode='exec')
        if codeobj:
            exec codeobj in main.__dict__
else:
    import code
    cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
    code.interact(banner='Python %s on %s\n%s' % (sys.version, sys.platform, cprt))

########NEW FILE########
