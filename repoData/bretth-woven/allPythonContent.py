__FILENAME__ = woven-admin
#!/usr/bin/env python
import sys, os
from distutils.core import run_setup
from random import choice
import re
import optparse

from django.core.management import execute_from_command_line, call_command
from django.core.management.base import CommandError, _make_writeable
from django.utils.importlib import import_module

from fabric.contrib.console import confirm, prompt
from fabric.api import settings
from fabric.state import env
from fabric.main import find_fabfile

import woven

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(woven.__file__))
                                ,'templates','distribution_template')

def copy_helper(app_or_project, name, directory, dist, template_dir, noadmin):
    """
    
    Replacement for django copy_helper
    Copies a Django project layout template into the specified distribution directory

    """

    import shutil
    if not re.search(r'^[_a-zA-Z]\w*$', name): # If it's not a valid directory name.
        # Provide a smart error message, depending on the error.
        if not re.search(r'^[_a-zA-Z]', name):
            message = 'make sure the name begins with a letter or underscore'
        else:
            message = 'use only numbers, letters and underscores'
        raise CommandError("%r is not a valid project name. Please %s." % (name, message))
    top_dir = os.path.join(directory, dist)
    try:
        os.mkdir(top_dir)
    except OSError, e:
        raise CommandError(e)
        
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir)+1:].replace('project_name', name)
        if relative_dir:
            os.mkdir(os.path.join(top_dir, relative_dir))
        for subdir in subdirs[:]:
            if subdir.startswith('.'):
                subdirs.remove(subdir)
        for f in files:
            if not f.endswith('.py'):
                # Ignore .pyc, .pyo, .py.class etc, as they cause various
                # breakages.
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(top_dir, relative_dir, f.replace('project_name', name))
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            if noadmin:
                fp_new.write(fp_old.read().replace('{{ project_name }}', name))
            else:
                fp_new.write(fp_old.read().replace('{{ project_name }}', name).replace('## ',''))
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write(style.NOTICE("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new))


def start_distribution(project_name, template_dir, dist, noadmin):
    """
    Custom startproject command to override django default
    """

    directory = os.getcwd()

    # Check that the project_name cannot be imported.
    try:
        import_module(project_name)
    except ImportError:
        pass
    else:
        raise CommandError("%r conflicts with the name of an existing Python module and cannot be used as a project name. Please try another name." % project_name)
    #woven override
    copy_helper('project', project_name, directory, dist, template_dir, noadmin)
    
    #Create a random SECRET_KEY hash, and put it in the main settings.
    main_settings_file = os.path.join(directory, dist, project_name, 'settings.py')
    settings_contents = open(main_settings_file, 'r').read()
    fp = open(main_settings_file, 'w')
    secret_key = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    settings_contents = re.sub(r"(?<=SECRET_KEY = ')'", secret_key + "'", settings_contents)
    fp.write(settings_contents)
    fp.close()
    
    #import settings and create start directories
    sys.path.append(os.path.join(directory, dist))

    s = import_module('.'.join([project_name,'settings']))
    sys.path.pop()
    if s.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3':
        if s.DATABASES['default']['NAME'] and not os.path.exists(s.DATABASES['default']['NAME']):
            os.mkdir(os.path.dirname(s.DATABASES['default']['NAME']))
    if s.STATIC_ROOT and os.path.isabs(s.STATIC_ROOT) and not os.path.exists(s.STATIC_ROOT):
        os.mkdir(s.STATIC_ROOT)
    if s.MEDIA_ROOT and os.path.isabs(s.MEDIA_ROOT) and not os.path.exists(s.MEDIA_ROOT):
        os.mkdir(s.MEDIA_ROOT)
    if s.TEMPLATE_DIRS:
        for t in s.TEMPLATE_DIRS:
            if not os.path.exists(t) and os.path.sep in t:
                os.mkdir(t)
    

if __name__ == "__main__":
    #Inject woven into the settings only if it is a woven command
    settings_mod = None
    inject = False
    startproject = False
    orig_cwd = os.getcwd()

    for arg in sys.argv:
        if '--settings' in arg:
            settings_mod = arg.split('=')[1].strip()
        elif arg in ['activate','deploy','startsites','setupnode','node','bundle','patch', 'validate']:
            inject = True
        elif arg == 'startproject':
            #call woven startproject in place of django startproject
            startproject = True
            inject = True
            parser = optparse.OptionParser(usage="usage: %prog startproject [project_name] [username@domain] [options]\n\n"
                "project_name is the name of your django project\n"                               
                "username@domain is an optional email address to setup a superuser")
            parser.add_option('-t', '--template-dir', dest='src_dir',
                        help='project template directory to use',
                        default=TEMPLATE_DIR)
            parser.add_option('-d','--dist', dest='dist_name',
                        help="alternative distribution name",
                        default='')
            parser.add_option('--noadmin',
                    action='store_true',
                    default=False,
                    help="admin disabled",
                    ),
            parser.add_option('--nosyncdb',
                    action='store_true',
                    default=False,
                    help="Does not syncdb",
                    )
            options, args = parser.parse_args()
            if len(args) not in (2, 3, 4):
                parser.print_help()
                sys.exit(1)
            if not options.dist_name:
                dist = args[1]
            else:
                dist = options.dist_name
            project_name = args[1]
            try:
                email = args[2]
            except IndexError:
                email = ''

            start_distribution(project_name,options.src_dir, dist, noadmin = options.noadmin)

    #get the name of the settings from setup.py if DJANGO_SETTINGS_MODULE is not set
    if not os.environ.get('DJANGO_SETTINGS_MODULE') and not settings_mod:
        if startproject:
            os.chdir(os.path.join(orig_cwd,dist))
        elif not 'setup.py' in os.listdir(os.getcwd()):
            #switch the working directory to the distribution root where setup.py is
            with settings(fabfile='setup.py'):
                env.setup_path = find_fabfile()
            if not env.setup_path:
                print 'Error: You must have a setup.py file in the current or a parent folder'
                sys.exit(1)
            local_working_dir = os.path.split(env.setup_path)[0]
            os.chdir(local_working_dir)
        
        woven_admin = sys.argv[0]
        setup = run_setup('setup.py',stop_after="init")
        settings_mod = '.'.join([setup.packages[0],'settings'])
        os.environ['DJANGO_SETTINGS_MODULE'] =  settings_mod
        sys.argv.remove('setup.py')
        sys.argv.insert(0, woven_admin)


    if inject:
        if settings_mod:
            os.environ['DJANGO_SETTINGS_MODULE'] = settings_mod

        from django.conf import settings
        settings.INSTALLED_APPS += ('woven',)
        
        #switch to the settings module directory
        proj = settings_mod.split('.')[0]
        proj_mod = import_module(proj)
        if not proj_mod:
            sys.exit(0)
        moddir = os.path.dirname(proj_mod.__file__)
        os.chdir(moddir)

    
    if startproject:
        if not options.nosyncdb:
            call_command('syncdb',interactive=False)
            if 'django.contrib.auth' in settings.INSTALLED_APPS:
                if '@' in email:
                    u = email.split('@')[0]
                else:
                    u = project_name
                    email = '%s@example.com'% project_name
                print "\nA superuser will be created with '%s' as username and password"% u
                print "Alternatively you can run the standard createsuperuser command separately"
                csuper = confirm('Would you like to create a superuser now?',default=True)
                if csuper:
                    from django.contrib.auth.models import User
                    
                    User.objects.create_superuser(username=u, email=email, password=u)
                    print "\nA default superuser was created:"
                    print "Username:", u
                    print "Password:", u
                    print "Email:", email
                    print "Change your password with 'woven-admin.py changepassword %s'"% u
                else:
                    print "\nNo superuser created. "
                    print "Run 'woven-admin.py createsuperuser' to create one"
        
    #run command as per django-admin.py
    else:
        #switch back to the original directory just in case some command needs it
        os.chdir(orig_cwd)
        execute_from_command_line()


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Woven documentation build configuration file, created by
# sphinx-quickstart on Sat Jun 19 13:59:33 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('../'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.todo']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Woven'
copyright = u'2010, Brett Haydon'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
from woven import get_version
version = get_version()
# The full version, including alpha/beta/rc tags.
release = get_version()

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'sphinxdoc'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Wovendoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Woven.tex', u'Woven Documentation',
   u'Brett Haydon', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = dec
"""
Tests the decorators.py module
"""

from fabric.api import settings, sudo

from woven.decorators import run_once_per_node, run_once_per_version

H = '192.168.188.10'
HS = 'root@192.168.188.10:22'
R = 'root'

def teardown():
    with settings(host_string=HS,user=R,password=R,project_fullname='example-0.2'):
        sudo('rm -rf /var/local/woven')

def test_dec_run_once_per_node():
    teardown()
    
    @run_once_per_node
    def test_func():
        return 'some'
    
    with settings(host=H, host_string=HS,user=R,password=R,project_fullname='example-0.1'):
        assert test_func() == 'some'
        r = test_func()
        assert not r
    with settings(host=H,host_string=HS,user=R,password=R,project_fullname='example-0.2'):
        assert test_func()
    
    teardown()

def test_dec_run_once_per_version():
    teardown()
    
    @run_once_per_version
    def test_func():
        return 'some'
    
    with settings(host=H,host_string=HS,user=R,password=R,project_fullname='example-0.1'):
        assert test_func() == 'some'
    with settings(host=H,host_string=HS,user=R,password=R,project_fullname='example-0.2'):
        r=test_func()
        assert r
        #run a second time
        assert not test_func()
        
    teardown()
    
########NEW FILE########
__FILENAME__ = dep
from fabric.contrib.files import exists
from fabric.api import sudo, settings

from woven.deployment import _backup_file, _restore_file

H = '192.168.188.10'
HS = 'root@192.168.188.10:22'
R = 'root'

def test_dep_backup_file():
    with settings(hosts=[H],host_string=HS,user=R,password=R):
        sudo('rm -rf /var/local/woven-backup')
        _backup_file('/etc/ssh/sshd_config')
        assert exists('/var/local/woven-backup/etc/ssh/sshd_config')
        sudo('rm -rf /var/local/woven-backup')
        
        
    



########NEW FILE########
__FILENAME__ = env

from fabric.api import *
from fabric.state import env

from woven.environment import _root_domain, _parse_project_version
from woven.environment import set_env, server_state, set_server_state
from woven.environment import version_state, set_version_state
H = '192.168.188.10'
HS = 'root@192.168.188.10:22'
R = 'root'

def setup():
    sudo('rm -rf /var/local/woven')

def teardown():
    sudo('rm -rf /var/local/woven')
    
def test_env_set_env():
    print "TEST SET ENV"
    set_env()

def test_env_server_state():
    with settings(host_string=HS,user=R,password=R):
        setup()
        env.project_fullname = 'example_project-0.1'
        sudo('rm -rf /var/local/woven')
        #test
        set_server_state('example',delete=True)
        set_server_state('example')
        assert server_state('example')
        set_server_state('example',object=['something'])
        state = server_state('example')
        assert state == ['something']
        set_server_state('example',delete=True)
        state = server_state('example')
        assert not state

        teardown()

def test_env_version_state():
    with settings(host_string=HS,user=R,password=R):
        setup()
        env.project_fullname = 'example_project-0.1'
        sudo('rm -rf /var/local/woven')
        #test
        set_version_state('example',delete=True)
        set_version_state('example')
        assert version_state('example')
        set_version_state('example',object=['something'])
        state = version_state('example')
        assert state == ['something']
        state = version_state('example', prefix=True)
        assert state
        
        set_version_state('example',delete=True)
        state = version_state('example')
        assert not state
        teardown()
    
        
def test_env_parse_project_version():
    v = _parse_project_version('0.1')
    env.project_version = ''
    assert v == '0.1'
    v = _parse_project_version('0.1.0.1')
    env.project_version = ''
    assert v == '0.1'
    v = _parse_project_version('0.1 alpha')
    env.project_version = ''
    assert v =='0.1-alpha'
    v = _parse_project_version('0.1a 1234')
    env.project_version = ''
    assert v == '0.1a'
    v = _parse_project_version('0.1-alpha')
    env.project_version = ''
    assert v == '0.1-alpha'
    v = _parse_project_version('0.1 rc1 1234')
    env.project_version = ''
    assert v == '0.1-rc1'
    v = _parse_project_version('0.1.0rc1')
    env.project_version = ''
    assert v == '0.1.0rc1'
    v = _parse_project_version('0.1.1 rc2')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = _parse_project_version('0.1.1.rc2.1234')
    env.project_version = ''
    assert v == '0.1.1.rc2'
    v = _parse_project_version('0.1.1-rc2.1234')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = _parse_project_version('0.1.1-rc2-1234')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = _parse_project_version('0.1.1 rc2 1234')
    assert v ==  '0.1.1-rc2'
    v = _parse_project_version('d.og')
    assert v == 'd.og'
    v = _parse_project_version('dog')
    assert v == 'dog'

def test_env_root_domain():
    with settings(hosts=[H],host_string=HS,user=R,password=R):
        #In the event of noinput, the domain will default to example.com
        domain = _root_domain()
        print domain
        assert domain == 'example.com'
########NEW FILE########
__FILENAME__ = fabfile
#!/usr/bin/env python
"""
Test runner for woven.

Unit Tests don't appear to work with Fabric so all tests are run as fabfiles.
In absence of a better alternative the tests are split into separate files
with a specific naming strategy to make sure they run in groups.

``fab test`` will run all tests

To run individual tests:

``fab test_[test name]``

Tests are prefixed with an abbreviated name of the module they are testing so
that they run in groups, then alpha order.

Test functions defined in this file should be less than 10 characters in length.

"""
import os, string, sys

from django.utils import importlib
from fabric.state import commands, env
from woven.environment import set_env

#import tests
from env import test_env_set_env, test_env_server_state, test_env_parse_project_version, test_env_root_domain
from env import test_env_version_state

#from ubu import test_ubu_disable_root, test_ubu_change_ssh_port, test_ubu_port_is_open
#from ubu import test_ubu_setup_ufw, test_ubu_post_install_package, test_ubu_post_setupnode

from web import test_web_site_users
from lin import test_lin_add_repositories, test_lin_uninstall_packages
from lin import test_lin_setup_ufw_rules, test_lin_disable_root
from dec import test_dec_run_once_per_node, test_dec_run_once_per_version
from dep import test_dep_backup_file

#Set the environ for Django
settings_module = os.environ['DJANGO_SETTINGS_MODULE'] = 'example_project.setting'

env.INTERACTIVE = False
#Normally you would run fab or manage.py under the setup.py path
#since we are testing outside the normal working directory we need to pass it in
setup_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],'simplest_example')
sys.path.insert(0,setup_dir)

env.verbosity = 2
#Most high level api functions require set_env to set the necessary woven environment
set_env(setup_dir=setup_dir)

def _run_tests(key=''):
    #Get a list of functions from fabric
    tests = commands.keys()
    for t in tests:
        if key:
            test_prefix = 'test_'+key+'_'
        else:
            test_prefix = 'test_'        
        if test_prefix in t and len(t)>10:
            print string.upper(t)
            commands[t]()    
            print string.upper(t), 'COMPLETE'
def test():
    """
    Run all tests (in alpha order)
    """
    _run_tests()
            
def test_env():
    """
    Run all environment tests
    """
    _run_tests('env')

def test_lin():
    """
    Run all linux tests
    """
    _run_tests('lin')
    
def test_vir():
    """
    Run all virtualenv tests
    """
    _run_tests('vir')
    
def test_web():
    """
    Run all virtualenv tests
    """
    _run_tests('web')
    
def test_dec():
    """
    Run all decorator tests
    """
    _run_tests('dec')
    
def test_dep():
    """
    Run all deployment tests
    """
    _run_tests('dep')

    



########NEW FILE########
__FILENAME__ = lin
  
import os

from fabric.api import *
from fabric.contrib.files import uncomment, exists, comment, contains, append, sed
from fabric.state import connections, env
from fabric.network import join_host_strings, normalize

from woven.linux import disable_root, change_ssh_port, port_is_open, setup_ufw
from woven.linux import setup_ufw_rules
from woven.linux import uninstall_packages
from woven.linux import add_repositories

from woven.environment import server_state, set_server_state

H = '192.168.188.10'
HS = 'woven@192.168.188.10:10022'
R = 'woven'


def test_lin_add_repositories():
    add_repositories()
#Step 1 in Server setup process

def teardown_disable_root():
    local('rm -rf .woven')
    with settings(host_string='woven@192.168.188.10:22',user='woven',password='woven'):
        run('echo %s:%s > /tmp/root_user.txt'% ('root','root'))
        sudo('chpasswd < /tmp/root_user.txt')
        sudo('rm -rf /tmp/root_user.txt')
        print "Closing connection %s"% env.host_string
        #print connections
        connections[env.host_string].close()
        try:
            connections['woven@example.com:22'].close()
        except: pass
        original_username = 'woven'
        (olduser,host,port) = normalize(env.host_string)
        host_string=join_host_strings('root',host,'22')
        with settings(host_string=host_string,  password='root'):
            sudo('deluser --remove-home '+original_username)
   

def test_lin_disable_root():

    #automate
    env.DISABLE_ROOT = True
    env.INTERACTIVE = False
    env.HOST_PASSWORD = 'woven'
    env.ROOT_PASSWORD = 'root'
    
    #test
    with settings(host_string='woven@192.168.188.10:22',user='woven',password='woven'):
        disable_root()
        assert exists('/home/woven')
    
        #cleanup - re-enable root
        #teardown_disable_root()
    
def test_lin_change_ssh_port():

    #automate
    env.ROOT_PASSWORD = 'root'
    
    #setup
    host_state_dir = os.path.join(os.getcwd(),'.woven')
    host_state_path = os.path.join(host_state_dir,'example.com')
    if not os.path.exists(host_state_dir):
        os.mkdir(host_state_dir)
    open(host_state_path,'w').close()
    #test
    print "test_change_ssh_port"
    with settings(user='root',password=env.ROOT_PASSWORD):
        change_ssh_port()
    print "test logging in on the new port"
    
    with settings(host_string='root@192.168.188.10:10022',user='root',password=env.ROOT_PASSWORD):
        try:
            run('echo')
        except:
            print "\nTEST: change_ssh_port FAILED"
            return
        print 'CHANGE PASSED'
    with settings(user='root',password=env.ROOT_PASSWORD):
        result = change_ssh_port()
        print result
        assert result  
    #teardown
    with settings(host_string='root@192.168.188.10:10022', user='root',password=env.ROOT_PASSWORD):
        sed('/etc/ssh/sshd_config','Port 10022','Port 22',use_sudo=True)
        sudo('/etc/init.d/ssh restart')
    local('rm -rf .woven')
    return

def test_lin_port_is_open():
    with settings(host_string='root@192.168.188.10:22', user='root',password=env.ROOT_PASSWORD):
        result = port_is_open()
        assert result
        
        sudo("echo 'Debian vers \n \l'> /etc/issue.new")
        sudo('cp -f /etc/issue /tmp/issue.bak')
        sudo('mv -f /etc/issue.new /etc/issue')
        
        result = port_is_open()
        
        sudo ('cp -f /tmp/issue.bak /etc/issue')


#def test_lin_post_install_package():
#    env.installed_packages = ['postgresql','somepackage']
#    post_install_packages()
    
#def test_lin_post_setupnode():
#    post_setupnode()

def test_lin_setup_ufw_rules():
    #first define some rules that was in the settings
    UFW_RULES = ['allow from 127.0.0.1 to any app apache2', 'allow 5432/tcp']

    with settings(packages=p,UFW_RULES=UFW_RULES, host_string=HS,user=R,password=R):
        setup_ufw_rules()
        
        
def test_lin_setup_ufw():
    with settings(host_string='root@192.168.188.10', user='root',password='root'):

        #tests
        env.HOST_SSH_PORT = '22'
        setup_ufw()
        r = sudo('ufw status').strip()
        assert 'woven' in r
        assert 'ALLOW' in r
        
        with settings(warn_only=True):

            sudo('ufw disable')
            sudo('rm -f /etc/ufw/applications.d/woven')
            sudo('rm -f /etc/ufw/applications.d/woven_project')
            apt_get_purge('ufw')
            set_server_state('ufw_installed',delete=True)
        
        #test change port
        print "CHANGE PORT to add 10022"
        env.HOST_SSH_PORT='22,10022'
        setup_ufw()
        r = sudo('ufw status verbose')
        assert '22,10022' in r
        assert '80,443' in r
        
        #test add an allow
        env.UFW_RULES = ['allow 5432/tcp']
        setup_ufw()
        r = sudo('ufw status verbose')
        assert '5432' in r
        
        #teardown
        sudo('ufw disable')
        sudo('rm -f /etc/ufw/applications.d/woven')
        apt_get_purge('ufw')
        set_server_state('ufw_installed',delete=True)

def test_lin_uninstall_packages():
    uninstall_packages()
    

########NEW FILE########
__FILENAME__ = vir

from fabric.state import env

    




########NEW FILE########
__FILENAME__ = web
from fabric.api import *

from woven.webservers import _site_users
from woven.linux import add_user

def test_web_site_users():
    with settings(host_string='root@192.168.188.10:22', user='root',password='root'):
        sudo('userdel site_1')
        users = _site_users()
        assert not users
        #now add a user
        add_user(username='site_1',group='www-data',site_user=True)
        users = _site_users()
        assert users[0] == 'site_1'
        
########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python
"""
The full public woven api
"""
from fabric.state import env

from woven.decorators import run_once_per_node, run_once_per_version

from woven.deployment import deploy_files, mkdirs
from woven.deployment import upload_template

from woven.environment import check_settings, deployment_root, set_env, patch_project
from woven.environment import get_project_version, server_state, set_server_state
from woven.environment import set_version_state, version_state, get_packages
from woven.environment import post_install_package, post_exec_hook

from woven.project import deploy_static, deploy_media, deploy_project, deploy_db, deploy_templates

from woven.linux import add_user, install_package, port_is_open, skip_disable_root
from woven.linux import install_packages, uninstall_packages
from woven.linux import upgrade_packages, setup_ufw, setup_ufw_rules, disable_root
from woven.linux import add_repositories, restrict_ssh, upload_ssh_key
from woven.linux import change_ssh_port, set_timezone, lsb_release, upload_etc

from woven.virtualenv import activate, active_version
from woven.virtualenv import mkvirtualenv, rmvirtualenv, pip_install_requirements


from woven.webservers import deploy_wsgi, deploy_webconf, start_webserver, stop_webserver, reload_webservers
from woven.webservers import webserver_list

def deploy(overwrite=False):
    """
    deploy a versioned project on the host
    """
    check_settings()
    if overwrite:
        rmvirtualenv()
    deploy_funcs = [deploy_project,deploy_templates, deploy_static, deploy_media,  deploy_webconf, deploy_wsgi]
    if not patch_project() or overwrite:
        deploy_funcs = [deploy_db,mkvirtualenv,pip_install_requirements] + deploy_funcs
    for func in deploy_funcs: func()


def setupnode(overwrite=False):
    """
    Install a baseline host. Can be run multiple times

    """
    if not port_is_open():
        if not skip_disable_root():
            disable_root()
        port_changed = change_ssh_port()
    #avoid trying to take shortcuts if setupnode did not finish 
    #on previous execution
    if server_state('setupnode-incomplete'):
        env.overwrite=True
    else: set_server_state('setupnode-incomplete')
    upload_ssh_key()
    restrict_ssh()
    add_repositories()
    upgrade_packages()
    setup_ufw()
    uninstall_packages()
    install_packages()

    upload_etc()
    post_install_package()
    setup_ufw_rules()
    set_timezone()
    set_server_state('setupnode-incomplete',delete=True)
    #stop and start webservers - and reload nginx
    for s in webserver_list():
        stop_webserver(s)
        start_webserver(s)



########NEW FILE########
__FILENAME__ = decorators
from functools import wraps

from fabric.api import env
from woven.environment import server_state, set_server_state
from woven.environment import version_state, set_version_state

def run_once_per_node(func):
    """
    Decorator preventing wrapped function from running more than
    once per host (not just interpreter session).

    Using env.patch = True will allow the wrapped function to be run
    if it has been previously executed, but not otherwise
    
    Stores the result of a function as server state
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        if not hasattr(env,'patch'): env.patch = False
        state = version_state(func.__name__)
        if not env.patch and state:
            verbose = " ".join([env.host,func.__name__,"completed. Skipping..."])
        elif env.patch and not state:
            verbose = " ".join([env.host,func.__name__,"not previously completed. Skipping..."])
        else:
            results = func(*args, **kwargs)
            verbose =''
            if results: set_version_state(func.__name__,object=results)
            else: set_version_state(func.__name__)
            return results
        if env.verbosity and verbose: print verbose
        return             
          
    return decorated

def run_once_per_version(func):
    """
    Decorator preventing wrapped function from running more than
    once per host and env.project_fullname (not just interpreter session).

    Using env.patch = True will allow the function to be run
    
    Stores the result of a function as server state
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        if not hasattr(env,'patch'): env.patch = False
        state = version_state(func.__name__)
        if not env.patch and state:
            verbose = " ".join([env.host,func.__name__,"completed. Skipping..."])
        elif env.patch and not state:
            verbose = " ".join([env.host,func.__name__,"not previously completed. Skipping..."])
        else:
            results = func(*args, **kwargs)
            verbose =''
            if results: set_version_state(func.__name__,object=results)
            else: set_version_state(func.__name__)
            return results
        if env.verbosity and verbose: print verbose
        return             
          
    return decorated
########NEW FILE########
__FILENAME__ = deploy
from fabric.state import env
from fabric.api import sudo, settings

def post_install_postgresql():
    """
    example default hook for installing postgresql
    """
    from django.conf import settings as s
    with settings(warn_only=True):
        sudo('/etc/init.d/postgresql-8.4 restart')
        sudo("""psql template1 -c "ALTER USER postgres with encrypted password '%s';" """% env.password, user='postgres')
        sudo("psql -f /usr/share/postgresql/8.4/contrib/adminpack.sql", user='postgres')
        if s.DATABASES['default']['ENGINE']=='django.db.backends.postgresql_psycopg2':
            sudo("""psql template1 -c "CREATE ROLE %s LOGIN with encrypted password '%s';" """% (s.DATABASES['default']['USER'],s.DATABASES['default']['PASSWORD']), user='postgres')
            sudo('createdb -T template0 -O %s %s'% (s.DATABASES['default']['USER'],s.DATABASES['default']['NAME']), user='postgres')

        print "* setup postgres user password with your '%s' password"% env.user
        print "* imported the adminpack"
        print "Post install setup of Postgresql complete!"

        
                
    
########NEW FILE########
__FILENAME__ = deployment
#!/usr/bin/env python
from functools import wraps
from glob import glob
from hashlib import sha1
import os, shutil, sys, tempfile

from django.template.loader import render_to_string

from fabric.state import env
from fabric.operations import run, sudo, put
from fabric.context_managers import cd, settings, hide
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project

def _backup_file(path):
    """
    Backup a file but never overwrite an existing backup file
    """
    backup_base = '/var/local/woven-backup'
    backup_path = ''.join([backup_base,path])
    if not exists(backup_path):
        directory = ''.join([backup_base,os.path.split(path)[0]])
        sudo('mkdir -p %s'% directory)
        sudo('cp %s %s'% (path,backup_path))

def _restore_file(path, delete_backup=True):
    """
    Restore a file if it exists and remove the backup
    """
    backup_base = '/var/local/woven-backup'
    backup_path = ''.join([backup_base,path])
    if exists(backup_path):
        if delete_backup:
            sudo('mv -f %s %s'% (backup_path,path))
        else:
            sudo('cp -f %s %s'% (backup_path,path))


def _get_local_files(local_dir, pattern=''):
    """
    Returns a dictionary with directories as keys, and filenames as values
    for filenames matching the glob ``pattern`` under the ``local_dir``
    ``pattern can contain the Boolean OR | to evaluated multiple patterns into
    a combined set. 
    """
    local_files = {}
    
    if pattern:
        cwd = os.getcwd()
        os.chdir(local_dir)
        patterns = pattern.split('|')
        local_list = set([])
        for p in patterns: local_list = local_list | set(glob(p))
        for path in local_list:
            dir, file = os.path.split(path)
            if os.path.isfile(path):
                local_files[dir] = local_files.get(dir,[])+[file]
            elif os.path.isdir(path):
                local_files[file] = local_files.get(dir,[])
        os.chdir(cwd)
    return local_files

def _stage_local_files(local_dir, local_files={}):
    """
    Either ``local_files`` and/or ``context`` should be supplied.
    
    Will stage a ``local_files`` dictionary of path:filename pairs where path
    is relative to ``local_dir`` into a local tmp staging directory.
    
    Returns a path to the temporary local staging directory

    """
    staging_dir = os.path.join(tempfile.mkdtemp(),os.path.basename(local_dir))
    os.mkdir(staging_dir)
    for root, dirs, files in os.walk(local_dir):
        relative_tree = root.replace(local_dir,'')
        if relative_tree:
            relative_tree = relative_tree[1:]
        if local_files:
            files = local_files.get(relative_tree,[])
        for file in files:
            if relative_tree:
                filepath = os.path.join(relative_tree,file)
                if not os.path.exists(os.path.join(staging_dir,relative_tree)):
                    os.mkdir(os.path.join(staging_dir,relative_tree))
            else: filepath = file
            shutil.copy2(os.path.join(root,file),os.path.join(staging_dir,filepath))
    return staging_dir

def deploy_files(local_dir, remote_dir, pattern = '',rsync_exclude=['*.pyc','.*'], use_sudo=False):
    """
    Generic deploy function for cases where one or more files are being deployed to a host.
    Wraps around ``rsync_project`` and stages files locally and/or remotely
    for network efficiency.
    
    ``local_dir`` is the directory that will be deployed.
   
    ``remote_dir`` is the directory the files will be deployed to.
    Directories will be created if necessary.
    
    Note: Unlike other ways of deploying files, all files under local_dir will be
    deployed into remote_dir. This is the equivalent to cp -R local_dir/* remote_dir.

    ``pattern`` finds all the pathnames matching a specified glob pattern relative
    to the local_dir according to the rules used by the Unix shell.
    ``pattern`` enhances the basic functionality by allowing the python | to include
    multiple patterns. eg '*.txt|Django*'
     
    ``rsync_exclude`` as per ``rsync_project``
    
    Returns a list of directories and files created on the host.
    
    """
    #normalise paths
    if local_dir[-1] == os.sep: local_dir = local_dir[:-1]
    if remote_dir[-1] == '/': remote_dir = remote_dir[:-1]
    created_list = []
    staging_dir = local_dir
    
    #resolve pattern into a dir:filename dict
    local_files = _get_local_files(local_dir,pattern)
    #If we are only copying specific files or rendering templates we need to stage locally
    if local_files: staging_dir = _stage_local_files(local_dir, local_files)
    remote_staging_dir = '/home/%s/.staging'% env.user
    if not exists(remote_staging_dir):
        run(' '.join(['mkdir -pv',remote_staging_dir])).split('\n')
        created_list = [remote_staging_dir]
    
    #upload into remote staging
    rsync_project(local_dir=staging_dir,remote_dir=remote_staging_dir,exclude=rsync_exclude,delete=True)

    #create the final destination
    created_dir_list = mkdirs(remote_dir, use_sudo)
    
    if not os.listdir(staging_dir): return created_list

    func = use_sudo and sudo or run
    #cp recursively -R from the staging to the destination and keep a list
    remote_base_path = '/'.join([remote_staging_dir,os.path.basename(local_dir),'*'])
    copy_file_list = func(' '.join(['cp -Ruv',remote_base_path,remote_dir])).split('\n')
    if copy_file_list[0]: created_list += [file.split(' ')[2][1:-1] for file in copy_file_list if file]

    #cleanup any tmp staging dir
    if staging_dir <> local_dir:
        shutil.rmtree(staging_dir,ignore_errors=True)
    
    return created_list

def mkdirs(remote_dir, use_sudo=False):
    """
    Wrapper around mkdir -pv
    
    Returns a list of directories created
    """
    func = use_sudo and sudo or run
    result = func(' '.join(['mkdir -pv',remote_dir])).split('\n')
    #extract dir list from ["mkdir: created directory `example.com/some/dir'"]
    if result[0]: result = [dir.split(' ')[3][1:-1] for dir in result if dir]
    return result

def upload_template(filename,  destination,  context={},  use_sudo=False, backup=True, modified_only=False):
    """
    Render and upload a template text file to a remote host using the Django
    template api. 

    ``filename`` should be the Django template name.
    
    ``context`` is the Django template dictionary context to use.

    The resulting rendered file will be uploaded to the remote file path
    ``destination`` (which should include the desired remote filename.) If the
    destination file already exists, it will be renamed with a ``.bak``
    extension.

    By default, the file will be copied to ``destination`` as the logged-in
    user; specify ``use_sudo=True`` to use `sudo` instead.
    """
    #Replaces the default fabric.contrib.files.upload_template
    basename = os.path.basename(filename)
    text = render_to_string(filename,context)

    func = use_sudo and sudo or run
    
    #check hashed template on server first
    if modified_only:
        hashfile_dir, hashfile = os.path.split(destination)
        hashfile_dir = ''.join(['/var/local/woven-backup',hashfile_dir])
        hashfile = '%s.hashfile'% hashfile
        hashfile_path = os.path.join(hashfile_dir, hashfile)
        hashed = sha1(text).hexdigest()
        if hashfile:
            if not exists(hashfile_dir): sudo('mkdir -p %s'% hashfile_dir)
            sudo('touch %s'% hashfile_path) #store the hash near the template
            previous_hashed = sudo('cat %s'% hashfile_path).strip()
            if previous_hashed == hashed:
                return False
            else: sudo('echo %s > %s'% (hashed, hashfile_path))

    temp_destination = '/tmp/' + basename

    # This temporary file should not be automatically deleted on close, as we
    # need it there to upload it (Windows locks the file for reading while open).
    tempfile_fd, tempfile_name = tempfile.mkstemp()
    output = open(tempfile_name, "w+b")
    
    output.write(text)
    output.close()
        
    # Upload the file.
    put(tempfile_name, temp_destination)
    os.close(tempfile_fd)
    os.remove(tempfile_name)

    
    # Back up any original file (need to do figure out ultimate destination)
    if backup:
        to_backup = destination
        with settings(hide('everything'), warn_only=True):
            # Is destination a directory?
            if func('test -f %s' % to_backup).failed:
                # If so, tack on the filename to get "real" destination
                to_backup = destination + '/' + basename
        if exists(to_backup):
            _backup_file(to_backup)
    # Actually move uploaded template to destination
    func("mv %s %s" % (temp_destination, destination))
    return True
########NEW FILE########
__FILENAME__ = environment
#!/usr/bin/env python
import json, os, string, sys, tempfile
from contextlib import nested
from distutils.core import run_setup

from django.utils.importlib import import_module

from fabric.context_managers import settings as fab_settings
from fabric.context_managers import _setenv, cd
from fabric.contrib.files import exists, comment, sed, append
from fabric.decorators import runs_once, hosts
from fabric.main import find_fabfile
from fabric.network import normalize
from fabric.operations import local, run, sudo, prompt, get, put
from fabric.state import _AttributeDict, env, output
from fabric.version import get_version
        

woven_env = _AttributeDict({
'HOSTS':[], #optional - a list of host strings to setup on as per Fabric
'ROLEDEFS':{}, #optional as per fabric. eg {'staging':['woven@example.com']}
'HOST_SSH_PORT':10022, #optional - the ssh port to be setup
'HOST_USER':'', #optional - can be used in place of defining it elsewhere (ie host_string)
'HOST_PASSWORD':'',#optional
'SSH_KEY_FILENAME':'',#optional - as per fabric, a path to a key to use in place your local .ssh key 

#The first setup task is usually disabling the default root account and changing the ssh port.
'ROOT_USER':'root', #optional - mostly the default administrative account is root
'DISABLE_ROOT': False, #optional - disable the default administrative account
'ROOT_PASSWORD':'', #optional - blank by default
'DEFAULT_SSH_PORT':22, #optional - The default ssh port, prior to woven changing it. Defaults to 22
'DISABLE_SSH_PASSWORD': False, #optional - setting this to true will disable password login and use ssh keys only.
'ENABLE_UFW':True, #optional - If some alternative firewall is already pre-installed
#optional - the default firewall rules (note ssh is always allowed)
'UFW_RULES':['allow 80,443/tcp'], 
'ROLE_UFW_RULES':{},
    
#The default packages that are setup. It is NOT recommended you change these:
'HOST_BASE_PACKAGES':[
        'ufw', #firewall
        'subversion','git-core','mercurial','bzr', #version control
        'gcc','build-essential', 'python-dev', 'python-setuptools', #build
        'apache2','libapache2-mod-wsgi','nginx', #webservers
        'python-imaging', #pil
        'python-psycopg2','python-mysqldb','python-pysqlite2'], #default database drivers

'HOST_EXTRA_PACKAGES':[], #optional - additional packages as required

'ROLE_PACKAGES':{},#define ROLEDEFS packages instead of using HOST_BASE_PACKAGES + HOST_EXTRA_PACKAGES

#Apache list of modules to disable for performance and memory efficiency
#This list gets disabled
'APACHE_DISABLE_MODULES':['alias','auth_basic','authn_file','authz_default','authz_groupfile',
                          'authz_user','autoindex','cgid','dir',
                          'setenvif','status'], 
#Specify a linux base backend to use. Not yet implemented
#'LINUX_BASE':'debian',

#define a list of repositories/sources to search for packages
'LINUX_PACKAGE_REPOSITORIES':[], # eg ppa:bchesneau/gunicorn
    
#Virtualenv/Pip
'DEPLOYMENT_ROOT':'',
'PROJECT_APPS_PATH':'',#a relative path from the project package directory for any local apps
'PIP_REQUIREMENTS':[], #a list of pip requirement and or pybundle files to use for installation

#Application media
'STATIC_URL':'', #optional
'STATIC_ROOT':'', #optional

#Database migrations
'MANUAL_MIGRATION':False, #optional Manage database migrations manually

})

def _parse_project_version(version=''):
    """
    Returns the significant part of the version excluding the build
       
    The final forms returned can be
    
    major.minor
    major.minor stage (spaces will be replaced with '-')
    major.minor.stage
    major.minor-stage
    major.minorstage (eg 1.0rc1)
    major.minor.maintenance
    major.minor.maintenance-stage
    major.minor.maintenancestage
    
    Anything beyond the maintenance or stage whichever is last is ignored 
    """
    
    def mm_version(vers):
        stage = ''
        stage_sep = ''
        finalvers = ''
        if not vers.isdigit():
            for num,char in enumerate(vers):
                if char.isdigit():
                    finalvers += str(char)
                elif char.isalpha():
                    stage = vers[num:]
                    break
                elif char in [' ','-']: #sep
                    #We will strip spaces to avoid needing to 'quote' paths
                    stage_sep = '-'
                    stage = vers[num+1:]
                    break
        else:
            finalvers = vers
        #remove any final build numbers
        if ' ' in stage:
            stage = stage.split(' ')[0]
        elif '-' in stage:
            stage = stage.split('-')[0]
        return (finalvers,stage,stage_sep)
        
    v = version.split('.')
    if len(v)==1: return v[0]
    major = v[0]
    minor = v[1]
    maint = ''
    stage = ''
    if len(v)>2 and v[2]<>'0': #(1.0.0 == 1.0)
        maint = v[2]
    if len(v)>3 and v[3][0].isalpha():
        stage = v[3]
        project_version = '.'.join([major,minor,maint,stage])
    else:
        #Detect stage in minor
        minor,stage_minor,stage_minor_sep = mm_version(minor)
        if maint: #may be maint = ''
            maint, stage_maint, stage_maint_sep = mm_version(maint)
        else:
            stage_maint = ''; stage_maint_sep = ''
        if stage_minor:
            stage = stage_minor
            stage_sep = stage_minor_sep
        elif stage_maint:
            stage = stage_maint
            stage_sep = stage_maint_sep
        finalvers = [major,minor]
        if maint: finalvers.append(maint)
        finalvers = '.'.join(finalvers)
        if stage:
            finalvers = stage_sep.join([finalvers,stage])
        project_version = finalvers
   
    return project_version

def _root_domain():
    """
    Deduce the root domain name - usually a 'naked' domain.
    
    This only needs to be done prior to the first deployment
    """

    if not hasattr(env,'root_domain'):
        cwd = os.getcwd().split(os.sep)
        domain = ''
        #if the first env.host has a domain name then we'll use that
        #since there are no top level domains that have numbers in them we can test env.host

        username, host, port = normalize(env.hosts[0])
        if host[-1] in string.ascii_letters:
            domain_parts = env.host.split('.')
            length = len(domain_parts)
            if length==2:
                #assumes .com .net etc so we want the full hostname for the domain
                domain = host
            elif length==3 and len(domain_parts[-1])==2:
                #assume country tld so we want the full hostname for domain
                domain = host
            elif length >=3:
                #assume the first part is the hostname of the machine
                domain = '.'.join(domain[1:])
        #we'll just pick the first directory in the path which has a period.
        else:
            for d in cwd:
                if '.' in d: 
                    domain = d
        if not domain and env.INTERACTIVE:
            domain = prompt('Enter the root domain for this project ',default='example.com')
        else:
            domain = 'example.com'
        env.root_domain = domain
    return env.root_domain

def check_settings():
    """
    Validate the users settings conf prior to deploy
    """
    valid=True
    if not get_version() >= '1.0':
        print "FABRIC ERROR: Woven is only compatible with Fabric < 1.0"
        valid = False
    if not env.MEDIA_ROOT or not env.MEDIA_URL:
        print "MEDIA ERROR: You must define a MEDIA_ROOT & MEDIA_URL in your settings.py"
        print "even if plan to deploy your media separately to your project"
        valid = False
    if not env.TEMPLATE_DIRS:
        print "TEMPLATES_DIRS ERROR: You must define a TEMPLATES_DIRS in your settings.py"
        valid=False
    if env.DEFAULT_DATABASE_ENGINE in ['django.db.backends.','django.db.backends.dummy']:
        print "DATABASE SETTINGS ERROR: The default database engine has not been defined in your settings.py file"
        print "At a minimum you must define an sqlite3 database for woven to deploy,"
        print "or define a database backend is managed outside of woven."    
        valid=False
    if not valid: sys.exit(1)

def disable_virtualenvwrapper():
    """
    Hack to workaround an issue with virtualenvwrapper logging caused by Fabric sudo
    
    Can also add --noprofile to env.shell
    """
    profile_path = '/'.join([deployment_root(),'.profile'])

    sed(profile_path,'source /usr/local/bin/virtualenvwrapper.sh','')

def enable_virtualenvwrapper():
    profile_path = '/'.join([deployment_root(),'.profile'])
    append(profile_path, 'source /usr/local/bin/virtualenvwrapper.sh')
    

def deployment_root():
    """
    deployment root varies per host based on the user
    
    It can be overridden by the DEPLOYMENT_ROOT setting

    """
    if not env.DEPLOYMENT_ROOT: return '/'.join(['/home',env.user])
    else: return env.DEPLOYMENT_ROOT

def get_project_version():
    return env.project_version

def set_env(settings=None, setup_dir=''):
    """
    Used in management commands or at the module level of a fabfile to
    integrate woven project django.conf settings into fabric, and set the local current
    working directory to the distribution root (where setup.py lives).
    
    ``settings`` is your django settings module to pass in
    if you want to call this from a fabric script.
    
    ``setup_dir`` is an optional path to the directory containing setup.py
    This would be used in instances where setup.py was not above the cwd
    
    This function is used to set the environment for all hosts
   
    """

    #switch the working directory to the distribution root where setup.py is
    if hasattr(env, 'setup_path') and env.setup_path:
        setup_path = env.setup_path
    else:
        with fab_settings(fabfile='setup.py'):
            if setup_dir:
                setup_path = os.path.join(setup_dir,'setup.py')
            else:
                setup_path = find_fabfile()
            if not setup_path:
                print 'Error: You must have a setup.py file in the current or a parent folder'
                sys.exit(1)
        
    local_working_dir = os.path.split(setup_path)[0]
    os.chdir(local_working_dir)
    
    setup = run_setup('setup.py',stop_after="init")

    if setup.get_name() == 'UNKNOWN' or setup.get_version()=='0.0.0' or not setup.packages:
        print "ERROR: You must define a minimum of name, version and packages in your setup.py"
        sys.exit(1)
    
    #project env variables for deployment
    env.project_name = setup.get_name() #project_name()
    env.project_full_version = setup.get_version()#local('python setup.py --version').rstrip()
    env.project_version = _parse_project_version(env.project_full_version)
    env.project_fullname = '-'.join([env.project_name,env.project_version])
    env.project_package_name = setup.packages[0]
    env.patch = False

    #django settings are passed in by the command
    #We'll assume that if the settings aren't passed in we're running from a fabfile
    if not settings:
        sys.path.insert(0,local_working_dir)
        
        #import global settings
        project_settings = import_module(env.project_name+'.settings')
    else:

        project_settings = settings
    #If sqlite is used we can manage the database on first deployment
    env.DEFAULT_DATABASE_ENGINE = project_settings.DATABASES['default']['ENGINE']
    env.DEFAULT_DATABASE_NAME = project_settings.DATABASES['default']['NAME']
    
    #overwrite with main sitesettings module
    #just for MEDIA_URL, ADMIN_MEDIA_PREFIX, and STATIC_URL
    #if this settings file exists
    try:
        site_settings = import_module('.'.join([env.project_name,'sitesettings.settings']))
        project_settings.MEDIA_URL = site_settings.MEDIA_URL
        project_settings.ADMIN_MEDIA_PREFIX = site_settings.ADMIN_MEDIA_PREFIX
        project_settings.DATABASES = site_settings.DATABASES 
        if hasattr(site_settings,'STATIC_URL'):
            project_settings.STATIC_URL = site_settings.STATIC_URL
        else:
            project_settings.STATIC_URL = project_settings.ADMIN_MEDIA_PREFIX
    except ImportError:
        pass

    #update woven_env from project_settings    
    local_settings = dir(project_settings)
    #only get settings that woven uses
    for setting in local_settings:
        if setting.isupper() and hasattr(woven_env,setting):
            s = getattr(project_settings,setting,'')
            woven_env[setting] = s
    
    #upate the fabric env with all the woven settings
    env.update(woven_env)
    
    #set any user/password defaults if they are not supplied
    #Fabric would get the user from the options by default as the system user
    #We will overwrite that
    if woven_env.HOST_USER:
        env.user = woven_env.HOST_USER
    env.password = woven_env.HOST_PASSWORD
    
    #set the hosts if they aren't already
    if not env.hosts: env.hosts = woven_env.HOSTS
    if not env.roledefs: env.roledefs = woven_env.ROLEDEFS
    
    #reverse_lookup hosts to roles
    role_lookup  = {}
    for role in env.roles:
        r_hosts = env.roledefs[role]
        for host in r_hosts:
            #since port is not handled by fabric.main.normalize we'll do it ourselves
            role_lookup['%s:%s'% (host,str(woven_env.HOST_SSH_PORT))]=role
    #now add any hosts that aren't already defined in roles
    for host in env.hosts:
        host_string = '%s:%s'% (host,str(woven_env.HOST_SSH_PORT))
        if host_string not in role_lookup.keys():
            role_lookup[host_string] = ''
    env.role_lookup = role_lookup
    env.hosts = role_lookup.keys()
    
    #remove any unneeded db adaptors - except sqlite
    remove_backends = ['postgresql_psycopg2', 'mysql']
    for db in project_settings.DATABASES:
        engine = project_settings.DATABASES[db]['ENGINE'].split('.')[-1]
        if engine in remove_backends: remove_backends.remove(engine)
    for backend in remove_backends:
        if backend == 'postgresql_psycopg2': rm = 'python-psycopg2'
        elif backend == 'mysql': rm = 'python-mysqldb'
        env.HOST_BASE_PACKAGES.remove(rm)

    #packages can be just the base + extra packages
    #or role dependent we need to just map out the packages to hosts and roles here
    packages = {}
    all_packages = set([])
    for role in env.roles:
        packages[role]=env.ROLE_PACKAGES.get(role,[])
        if not packages[role]:
            packages[role] = env.HOST_BASE_PACKAGES + env.HOST_EXTRA_PACKAGES
        all_packages = set(packages[role]) | all_packages

    #no role
    packages[''] = env.HOST_BASE_PACKAGES + env.HOST_EXTRA_PACKAGES
    all_packages = set(packages['']) | all_packages

    #conveniently add gunicorn ppa
    if 'gunicorn' in all_packages:
        if 'ppa:bchesneau/gunicorn' not in env.LINUX_PACKAGE_REPOSITORIES:
            env.LINUX_PACKAGE_REPOSITORIES.append('ppa:bchesneau/gunicorn')    

    env.packages = packages
    
    #sanity check for unwanted combinations in the empty role
    u = set(packages[''])
    wsgi = u & set(['gunicorn','uwsgi'])
    if wsgi and 'apache2' in u:
        u = u - set(['apache2','libapache2-mod-wsgi'])

    #Used to detect certain apps eg South, static_builder
    env.INSTALLED_APPS = project_settings.INSTALLED_APPS

    env.packages[''] = list(u)
   
    #per host
    env.installed_packages = {} 
    env.uninstalled_packages = {}
    
    #UFW firewall rules
    firewall_rules = {}
    for role in env.roles:
        firewall_rules[role]= env.ROLE_UFW_RULES.get(role,[])
    firewall_rules['']=env.UFW_RULES
    env.firewall_rules = firewall_rules
    
    #Now update the env with any settings that are not defined by woven but may
    #be used by woven or fabric
    env.MEDIA_ROOT = project_settings.MEDIA_ROOT
    env.MEDIA_URL = project_settings.MEDIA_URL
    try:
        env.ADMIN_MEDIA_PREFIX = project_settings.ADMIN_MEDIA_PREFIX
    except AttributeError:
        env.ADMIN_MEDIA_PREFIX = ''
    if not env.STATIC_URL:
        env.STATIC_URL = project_settings.ADMIN_MEDIA_PREFIX
    env.TEMPLATE_DIRS = project_settings.TEMPLATE_DIRS
    
    #Set the server /etc/timezone
    env.TIME_ZONE = project_settings.TIME_ZONE
    #Used to detect certain apps eg South, static_builder
    env.INSTALLED_APPS = project_settings.INSTALLED_APPS
    
    #SSH key
    if not hasattr(env,'key_filename') and not env.key_filename and env.SSH_KEY_FILENAME:
        env.key_filename = env.SSH_KEY_FILENAME
    elif not hasattr(env,'key_filename'):
        env.key_filename = None
        
    #noinput
    if not hasattr(env,'INTERACTIVE'):
        env.INTERACTIVE = True
    if not hasattr(env,'verbosity'):
        env.verbosity = 1
    
    #overwrite existing settings
    if not hasattr(env,'overwrite'):
        env.overwrite=False
    
    #South integration defaults
    env.nomigration = False
    env.manualmigration = False
    env.migration = ''
    
    env.root_disabled = False
    
    #Sites
    env.sites = {}
    env.shell = '/bin/bash --noprofile -l -c'
    #output.debug = True

def get_packages():
    """
    per host list of packages
    """
    packages = env.packages[env.role_lookup[env.host_string]]
    return packages
    
def patch_project():
    return env.patch

def post_install_package():
    """
    Run any functions post install a matching package.
    Hook functions are in the form post_install_[package name] and are
    defined in a deploy.py file
    
    Will be executed post install_packages and upload_etc
    """

    module_name = '.'.join([env.project_package_name,'deploy'])
    funcs_run = []
    try:
        imported = import_module(module_name)
        funcs = vars(imported)
        for f in env.installed_packages[env.host]:
            func = funcs.get(''.join(['post_install_',f.replace('.','_').replace('-','_')]))
            if func:
                func()
                funcs_run.append(func)
    except ImportError:
        pass
    
    #run per app
    for app in env.INSTALLED_APPS:
        if app == 'woven': continue
        module_name = '.'.join([app,'deploy'])
        try:
            imported = import_module(module_name)
            funcs = vars(imported)
            for f in env.installed_packages[env.host]:
                func = funcs.get(''.join(['post_install_',f.replace('.','_').replace('-','_')]))
                if func and func not in funcs_run:
                    func()
                    funcs_run.append(func)
        except ImportError:
            pass
    #run woven last
    import woven.deploy
    funcs = vars(woven.deploy)
    for f in env.installed_packages[env.host]:
        func = funcs.get(''.join(['post_install_',f.replace('.','_').replace('-','_')]))
        if func and func not in funcs_run: func()
    

def post_exec_hook(hook):
    """
    Runs a hook function defined in a deploy.py file
    """
    #post_setupnode hook
    module_name = '.'.join([env.project_package_name,'deploy'])
    funcs_run = []
    try:
        imported = import_module(module_name)
        func = vars(imported).get(hook)
        if func:
            func()
            funcs_run.append(func)
    except ImportError:
        return

   #run per app
    for app in env.INSTALLED_APPS:
        if app == 'woven': continue
        module_name = '.'.join([app,'deploy'])
        try:
            imported = import_module(module_name)
            func = vars(imported).get(hook)
            if func and func not in funcs_run:
                func()
                funcs_run.append(func)
        except ImportError:
            pass
    import woven.deploy
    func = vars(woven.deploy).get(hook)
    if func and func not in funcs_run: func()

def project_version(full_version):
    """
    project_version context manager
    """

    project_full_version=full_version
    v = _parse_project_version(full_version)
    name = project_name()
    project_fullname = '-'.join([name,v])

    return _setenv(project_full_version=project_full_version, project_version=v,project_name=name,project_fullname=project_fullname)

class State(str):
    """
    State class     
    It may be used to store stdout stderr etc.

    """
    def __init__(self,name,object=None):
        self.name = name
        self.object = object
        self.failed = False
        self.stderr = ''
        self.stdout = ''
    def __repr__(self):
        return str(self.name)
    def __str__(self):
        return str(self.name)
    def __bool__(self):
        return not self.failed
    def __len__(self):
        if self.failed: return 0
        else: return 1
    def __eq__(self, other):
        return self.name == other
    def __cmp__(self,other):
        return self.name == other
    def __ne__(self,other):
        return str(self.name) <> other

def set_server_state(name,object=None,delete=False):
    """
    Sets a simple 'state' on the server by creating a file
    with the desired state's name and storing ``content`` as json strings if supplied
    
    returns the filename used to store state   
    """
    with fab_settings(project_fullname=''):
        return set_version_state(name,object,delete)


def set_version_state(name,object=None,delete=False):
    """
    Sets a simple 'state' on the server by creating a file
    with the desired state's name + version and storing ``content`` as json strings if supplied
    
    returns the filename used to store state   
    """
    if env.project_fullname: state_name = '-'.join([env.project_fullname,name])
    else: state_name = name
    with fab_settings(warn_only=True):
        #Test for os state
        if not exists('/var/local/woven', use_sudo=True):
            sudo('mkdir /var/local/woven')
    if not delete:
        sudo('touch /var/local/woven/%s'% state_name)
        if object <> None:
            fd, file_path = tempfile.mkstemp()
            f = os.fdopen(fd,'w')
            f.write(json.dumps(object))
            f.close()
            put(file_path,'/tmp/%s'% state_name)
            os.remove(file_path)
            sudo('cp /tmp/%s /var/local/woven/%s'% (state_name,state_name))
    else:
        sudo('rm -f /var/local/woven/%s'% state_name)
    return state_name
    

def server_state(name, no_content=False):
    """
    If the server state exists return parsed json as a python object or True 
    prefix=True returns True if any files exist with ls [prefix]*
    """
    with fab_settings(project_fullname=''):
        return version_state(name, no_content=no_content)


def version_state(name, prefix=False, no_content=False):
    """
    If the server state exists return parsed json as a python object or True 
    prefix=True returns True if any files exist with ls [prefix]*
    """
    if env.project_fullname: full_name = '-'.join([env.project_fullname,name])
    else: full_name = name
    current_state = False
    state = State(full_name)
    state_path = '/var/local/woven/%s'% full_name
    if not prefix and not no_content and exists(state_path):
        content = int(sudo('ls -s %s'% state_path).split()[0]) #get size
        if content:
            fd, file_path = tempfile.mkstemp()
            os.close(fd)
            get(state_path,file_path)
            with open(file_path, "r") as f:
                content = f.read()
                object = json.loads(content)
                current_state = object
        else:
            current_state = True
    elif not prefix and no_content and exists(state_path):
        current_state = True
    elif prefix:
        with fab_settings(warn_only=True): #find any version
            current_state = sudo('ls /var/local/woven/*%s'% name)
        if not current_state.failed:current_state = True
      
    return current_state
   

########NEW FILE########
__FILENAME__ = linux
"""
Replaces the ubuntu.py module with more generic linux functions.
"""
#To implement different backends we'll either
#split out functions into function and _backend_functions
#or if the difference is marginal just use if statements
import os, socket, sys
import getpass

from django.utils import importlib

from fabric.state import  _AttributeDict, env, connections
from fabric.context_managers import settings, hide
from fabric.operations import prompt, run, sudo, get, put
from fabric.contrib.files import comment, uncomment, contains, exists, append, sed
from fabric.contrib.console import confirm
from fabric.network import join_host_strings, normalize

from woven.deployment import _backup_file, _restore_file, deploy_files, upload_template
from woven.environment import server_state, set_server_state, get_packages

def _get_template_files(template_dir):
    etc_dir = os.path.join(template_dir,'woven','etc')
    templates = []
    for root, dirs, files in os.walk(etc_dir):
        if files:
            for f in files:
                if f[0] <> '.':
                    new_root = root.replace(template_dir,'')
                    templates.append(os.path.join(new_root,f))

    return set(templates)

def add_repositories():
    """
    Adds additional sources as defined in LINUX_PACKAGE_REPOSITORIES.

    """
    if not env.overwrite and env.LINUX_PACKAGE_REPOSITORIES == server_state('linux_package_repositories'): return
    if env.verbosity:
        print env.host, "UNCOMMENTING SOURCES in /etc/apt/sources.list and adding PPAs"
    if contains(filename='/etc/apt/sources.list',text='#(.?)deb(.*)http:(.*)universe'):

        _backup_file('/etc/apt/sources.list')
        uncomment('/etc/apt/sources.list','#(.?)deb(.*)http:(.*)universe',use_sudo=True)
    install_package('python-software-properties')
    for p in env.LINUX_PACKAGE_REPOSITORIES:
        sudo('add-apt-repository %s'% p)
        if env.verbosity:
            print 'added source', p
    set_server_state('linux_package_repositories',env.LINUX_PACKAGE_REPOSITORIES)

def add_user(username='',password='',group='', site_user=False):
    """
    Adds the username
    """
    if group: group = '-g %s'% group
    if not site_user:
        run('echo %s:%s > /tmp/users.txt'% (username,password))
    if not site_user:
        sudo('useradd -m -s /bin/bash %s %s'% (group,username))
        sudo('chpasswd < /tmp/users.txt')
        sudo('rm -rf /tmp/users.txt')
    else:
        sudo('useradd -M -d /var/www -s /bin/bash %s'% username)
        sudo('usermod -a -G www-data %s'% username)    

def change_ssh_port():
    """
    For security woven changes the default ssh port.
    
    """
    host = normalize(env.host_string)[1]

    after = env.port
    before = str(env.DEFAULT_SSH_PORT)
    

    host_string=join_host_strings(env.user,host,before)
    with settings(host_string=host_string, user=env.user):
        if env.verbosity:
            print env.host, "CHANGING SSH PORT TO: "+str(after)
        sed('/etc/ssh/sshd_config','Port '+ str(before),'Port '+str(after),use_sudo=True)
        if env.verbosity:
            print env.host, "RESTARTING SSH on",after

        sudo('/etc/init.d/ssh restart')
        return True

def disable_root():
    """
    Disables root and creates a new sudo user as specified by HOST_USER in your
    settings or your host_string
    
    The normal pattern for hosting is to get a root account which is then disabled.
    
    returns True on success
    """
    
    def enter_password():
        password1 = getpass.getpass(prompt='Enter the password for %s:'% sudo_user)
        password2 = getpass.getpass(prompt='Re-enter the password:')
        if password1 <> password2:
            print env.host, 'The password was not the same'
            enter_password()
        return password1

    (olduser,host,port) = normalize(env.host_string)
 
    if env.verbosity and not (env.HOST_USER or env.ROLEDEFS):
    
        print "\nWOVEN will now walk through setting up your node (host).\n"

        if env.INTERACTIVE:
            root_user = prompt("\nWhat is the default administrator account for your node?", default=env.ROOT_USER)
        else: root_user = env.ROOT_USER
        if env.user <> 'root': sudo_user = env.user
        else: sudo_user = ''
        if env.INTERACTIVE:
            sudo_user = prompt("What is the new or existing account you wish to use to setup and deploy to your node?", default=sudo_user)
           
    else:
        root_user = env.ROOT_USER
        sudo_user = env.user
        

    original_password = env.get('HOST_PASSWORD','')
    
    host_string=join_host_strings(root_user,host,str(env.DEFAULT_SSH_PORT))
    with settings(host_string=host_string, key_filename=env.key_filename, password=env.ROOT_PASSWORD):
        if not contains('/etc/group','sudo',use_sudo=True):
            sudo('groupadd sudo')

        home_path = '/home/%s'% sudo_user
        if not exists(home_path):
            if env.verbosity:
                print env.host, 'CREATING A NEW ACCOUNT WITH SUDO PRIVILEGE: %s'% sudo_user
            if not original_password:

                original_password = enter_password()
            
            add_user(username=sudo_user, password=original_password,group='sudo')

        #Add existing user to sudo group
        else:
            sudo('adduser %s sudo'% sudo_user)
        #adm group used by Ubuntu logs
        sudo('usermod -a -G adm %s'% sudo_user)
        #add user to /etc/sudoers
        if not exists('/etc/sudoers.wovenbak',use_sudo=True):
            sudo('cp -f /etc/sudoers /etc/sudoers.wovenbak')
        sudo('cp -f /etc/sudoers /tmp/sudoers.tmp')
        append('/tmp/sudoers.tmp', "# Members of the sudo group may gain root privileges", use_sudo=True)
        append('/tmp/sudoers.tmp', "%sudo ALL=(ALL) NOPASSWD:ALL",  use_sudo=True)
        sudo('visudo -c -f /tmp/sudoers.tmp')
        sudo('cp -f /tmp/sudoers.tmp /etc/sudoers')
        sudo('rm -rf /tmp/sudoers.tmp')
        if env.key_filename:
            sudo('mkdir -p /home/%s/.ssh'% sudo_user)
            sudo('cp -f ~/.ssh/authorized_keys /home/%s/.ssh/authorized_keys'% sudo_user)
            sudo('chown -R %s:sudo /home/%s/.ssh'% (sudo_user,sudo_user))
            
    env.password = original_password

    #finally disable root
    host_string=join_host_strings(sudo_user,host,str(env.DEFAULT_SSH_PORT))
    with settings(host_string=host_string):
        if sudo_user <> root_user and root_user == 'root':
            if env.INTERACTIVE:
                d_root = confirm("Disable the root account", default=True)
            else: d_root = env.DISABLE_ROOT
            if d_root:
                if env.verbosity:
                    print env.host, 'DISABLING ROOT'
                sudo("usermod -L %s"% 'root')

    return True

def install_package(package):
    """
    apt-get install [package]
    """
    #install silent and answer yes by default -qqy
    sudo('apt-get install -qqy %s'% package, pty=True)
    
def install_packages():
    """
    Install a set of baseline packages and configure where necessary
    """

    if env.verbosity:
        print env.host, "INSTALLING & CONFIGURING NODE PACKAGES:"
    #Get a list of installed packages
    p = run("dpkg -l | awk '/ii/ {print $2}'").split('\n')
    
    #Remove apparmor - TODO we may enable this later
    if env.overwrite or not server_state('apparmor-disabled') and 'apparmor' in p:
        with settings(warn_only=True):
            sudo('/etc/init.d/apparmor stop')
            sudo('update-rc.d -f apparmor remove')
            set_server_state('apparmor-disabled')

    #The principle we will use is to only install configurations and packages
    #if they do not already exist (ie not manually installed or other method)
    env.installed_packages[env.host] = []
    role = env.role_lookup[env.host_string]
    packages = get_packages()
    for package in packages:
        if not package in p:
            install_package(package)
            if env.verbosity:
                print ' * installed',package
            env.installed_packages[env.host].append(package)
    if env.overwrite or env.installed_packages[env.host]: #always store the latest complete list
        set_server_state('packages_installed', packages)
        env.installed_packages[env.host] = packages

    if env.overwrite and 'apache2' in env.installed_packages[env.host]: 
            #some sensible defaults -might move to putting this config in a template
            sudo("rm -f /etc/apache2/sites-enabled/000-default")
            sed('/etc/apache2/apache2.conf',before='KeepAlive On',after='KeepAlive Off',use_sudo=True, backup='')
            sed('/etc/apache2/apache2.conf',before='StartServers          2', after='StartServers          1', use_sudo=True, backup='')
            sed('/etc/apache2/apache2.conf',before='MaxClients          150', after='MaxClients          100', use_sudo=True, backup='')
            for module in env.APACHE_DISABLE_MODULES:
                sudo('rm -f /etc/apache2/mods-enabled/%s*'% module)
    #Install base python packages
    #We'll use easy_install at this stage since it doesn't download if the package
    #is current whereas pip always downloads.
    #Once both these packages mature we'll move to using the standard Ubuntu packages
    if (env.overwrite or not server_state('pip-venv-wrapper-installed')) and 'python-setuptools' in packages:
        sudo("easy_install virtualenv")
        sudo("easy_install pip")
        sudo("easy_install virtualenvwrapper")
        if env.verbosity:
            print " * easy installed pip, virtualenv, virtualenvwrapper"
        set_server_state('pip-venv-wrapper-installed')
    if not contains("/home/%s/.profile"% env.user,"source /usr/local/bin/virtualenvwrapper.sh"):
        append("/home/%s/.profile"% env.user, "export WORKON_HOME=$HOME/env")
        append("/home/%s/.profile"% env.user, "source /usr/local/bin/virtualenvwrapper.sh")

    #cleanup after easy_install
    sudo("rm -rf build")

def lsb_release():
    """
    Get the linux distribution information and return in an attribute dict
    
    The following attributes should be available:
    base, distributor_id, description, release, codename
    
    For example Ubuntu Lucid would return
    base = debian
    distributor_id = Ubuntu
    description = Ubuntu 10.04.x LTS
    release = 10.04
    codename = lucid
    
    """
    
    output = run('lsb_release -a').split('\n')
    release = _AttributeDict({})
    for line in output:
        try:
            key, value = line.split(':')
        except ValueError:
            continue
        release[key.strip().replace(' ','_').lower()]=value.strip()
   
    if exists('/etc/debian_version'): release.base = 'debian'
    elif exists('/etc/redhat-release'): release.base = 'redhat'
    else: release.base = 'unknown'
    return release
    
def port_is_open():
    """
    Determine if the default port and user is open for business.
    """
    with settings(hide('aborts'), warn_only=True ):
        try:
            if env.verbosity:
                print "Testing node for previous installation on port %s:"% env.port
            distribution = lsb_release()
        except KeyboardInterrupt:
            if env.verbosity:
                print >> sys.stderr, "\nStopped."
            sys.exit(1)
        except: #No way to catch the failing connection without catchall? 
            return False
        if distribution.distributor_id <> 'Ubuntu':
            print env.host, 'WARNING: Woven has only been tested on Ubuntu >= 10.04. It may not work as expected on',distribution.description
    return True

def restrict_ssh(rollback=False):
    """
    Set some sensible restrictions in Ubuntu /etc/ssh/sshd_config and restart sshd
    UseDNS no #prevents dns spoofing sshd defaults to yes
    X11Forwarding no # defaults to no
    AuthorizedKeysFile  %h/.ssh/authorized_keys

    uncomments PasswordAuthentication no and restarts sshd
    """

    if not rollback:
        if server_state('ssh_restricted'):
            return False

        sshd_config = '/etc/ssh/sshd_config'
        if env.verbosity:
            print env.host, "RESTRICTING SSH with "+sshd_config
        filename = 'sshd_config'
        if not exists('/home/%s/.ssh/authorized_keys'% env.user): #do not pass go do not collect $200
            print env.host, 'You need to upload_ssh_key first.'
            return False
        _backup_file(sshd_config)
        context = {"HOST_SSH_PORT": env.HOST_SSH_PORT}
        
        upload_template('woven/ssh/sshd_config','/etc/ssh/sshd_config',context=context,use_sudo=True)
        # Restart sshd
        sudo('/etc/init.d/ssh restart')
        
        # The user can modify the sshd_config file directly but we save
        proceed = True
        if not env.key_filename and (env.DISABLE_SSH_PASSWORD or env.INTERACTIVE) and contains('/etc/ssh/sshd_config','#PasswordAuthentication no',use_sudo=True):
            print "WARNING: You may want to test your node ssh login at this point ssh %s@%s -p%s"% (env.user, env.host, env.port)
            c_text = 'Would you like to disable password login and use only ssh key authentication'
            proceed = confirm(c_text,default=False)
    
        if not env.INTERACTIVE or proceed or env.DISABLE_SSH_PASSWORD:
            #uncomments PasswordAuthentication no and restarts
            uncomment(sshd_config,'#(\s?)PasswordAuthentication(\s*)no',use_sudo=True)
            sudo('/etc/init.d/ssh restart')
        set_server_state('ssh_restricted')
        return True
    else: #Full rollback
        _restore_file('/etc/ssh/sshd_config')
        if server_state('ssh_port_changed'):
            sed('/etc/ssh/sshd_config','Port '+ str(env.DEFAULT_SSH_PORT),'Port '+str(env.HOST_SSH_PORT),use_sudo=True)
            sudo('/etc/init.d/ssh restart')
        sudo('/etc/init.d/ssh restart')
        set_server_state('ssh_restricted', delete=True)
        return True

def set_timezone(rollback=False):
    """
    Set the time zone on the server using Django settings.TIME_ZONE
    """
    if not rollback:
        if contains(filename='/etc/timezone', text=env.TIME_ZONE, use_sudo=True):
            return False
        if env.verbosity:
            print env.host, "CHANGING TIMEZONE /etc/timezone to "+env.TIME_ZONE
        _backup_file('/etc/timezone')
        sudo('echo %s > /tmp/timezone'% env.TIME_ZONE)
        sudo('cp -f /tmp/timezone /etc/timezone')
        sudo('dpkg-reconfigure --frontend noninteractive tzdata')
    else:
        _restore_fie('/etc/timezone')
        sudo('dpkg-reconfigure --frontend noninteractive tzdata')
    return True

def setup_ufw():
    """
    Setup basic ufw rules just for ssh login
    """
    if not env.ENABLE_UFW: return
   
    ufw_state = server_state('ufw_installed')
    if ufw_state and not env.overwrite or ufw_state == str(env.HOST_SSH_PORT): return
    #check for actual package
    ufw = run("dpkg -l | grep 'ufw' | awk '{print $2}'").strip()
    if not ufw:
        if env.verbosity:
            print env.host, "INSTALLING & ENABLING FIREWALL ufw"
        install_package('ufw')

    if env.verbosity:
        print env.host, "CONFIGURING FIREWALL ufw"
    #upload basic woven (ssh) ufw app config
    upload_template('/'.join(['woven','ufw.txt']),
        '/etc/ufw/applications.d/woven',
        {'HOST_SSH_PORT':env.HOST_SSH_PORT},
        use_sudo=True,
        backup=False)
    sudo('chown root:root /etc/ufw/applications.d/woven')
    with settings(warn_only=True):
        if not ufw_state:
            sudo('ufw allow woven')
        else:
            sudo('ufw app update woven')
    _backup_file('/etc/ufw/ufw.conf')
        
    #enable ufw
    sed('/etc/ufw/ufw.conf','ENABLED=no','ENABLED=yes',use_sudo=True, backup='')
    with settings(warn_only=True):
        output = sudo('ufw reload')
        if env.verbosity:
            print output
            
    set_server_state('ufw_installed',str(env.HOST_SSH_PORT))
    return

def setup_ufw_rules():
    """
    Setup ufw app rules from application templates and settings UFW_RULES

    """
    
    #current rules
    current_rules = server_state('ufw_rules')
    if current_rules: current_rules = set(current_rules)
    else: current_rules = set([])
    role = env.role_lookup[env.host_string]
    firewall_rules = set(env.firewall_rules[role])
    if not env.overwrite and firewall_rules == current_rules: return
    if env.verbosity:
        print 'CONFIGURING FIREWALL'
    
    delete_rules = current_rules - firewall_rules
    for rule in delete_rules:
        with settings(warn_only=True):
            if env.verbosity:
                print 'ufw delete', rule
            sudo('ufw delete %s'% rule)
    new_rules = firewall_rules - current_rules        
    for rule in new_rules:
        with settings(warn_only=True):
            if env.verbosity:
                print 'ufw', rule
            sudo('ufw %s'% rule)
    set_server_state('ufw_rules',list(firewall_rules))

        
    output = sudo('ufw reload')
    if env.verbosity:
        print output

    

def skip_disable_root():
    return env.root_disabled

def uninstall_package(package):
    """
    apt-get autoremove --purge
    """
    sudo('apt-get autoremove --purge -qqy %s'% package, pty=True)

def uninstall_packages():
    """
    Uninstall unwanted packages
    """
    p = server_state('packages_installed')
    if p: installed = set(p)
    else: return
    env.uninstalled_packages[env.host] = []
    #first uninstall any that have been taken off the list
    packages = set(get_packages())
    uninstall = installed - packages
    if uninstall and env.verbosity:
        print env.host,'UNINSTALLING HOST PACKAGES'
    for p in uninstall:
        if env.verbosity:
            print ' - uninstalling',p
        uninstall_package(p)
        env.uninstalled_packages[env.host].append(p)
    set_server_state('packages_installed',get_packages())
    return

def upgrade_packages():
    """
    apt-get update and apt-get upgrade
    """
    if env.verbosity:
        print env.host, "apt-get UPDATING and UPGRADING SERVER PACKAGES"
        print " * running apt-get update "
    sudo('apt-get -qqy update')
    if env.verbosity:
        print " * running apt-get upgrade"
        print " NOTE: apt-get upgrade has been known in rare cases to require user input."
        print "If apt-get upgrade does not complete within 15 minutes"
        print "see troubleshooting docs *before* aborting the process to avoid package management corruption."
    sudo('apt-get -qqy upgrade')

def upload_etc():
    """
    Upload and render all templates in the woven/etc directory to the respective directories on the nodes
    
    Only configuration for installed packages will be uploaded where that package creates it's own subdirectory
    in /etc/ ie /etc/apache2.
    
    For configuration that falls in some other non package directories ie init.d, logrotate.d etc
    it is intended that this function only replace existing configuration files. To ensure we don't upload 
    etc files that are intended to accompany a particular package.
    """
    role = env.role_lookup[env.host_string]
    packages = env.packages[role]
    #determine the templatedir
    if env.verbosity:
        print "UPLOAD ETC configuration templates"
    if not hasattr(env, 'project_template_dir'):
        #the normal pattern would mean the shortest path is the main one.
        #its probably the last listed
        length = 1000
        env.project_template_dir = ''
        for dir in env.TEMPLATE_DIRS:
            if dir:
                len_dir = len(dir)
                if len_dir < length:
                    length = len_dir
                    env.project_template_dir = dir

    template_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],'templates','')
    default_templates = _get_template_files(template_dir)
    if env.project_template_dir: user_templates = _get_template_files(os.path.join(env.project_template_dir,''))
    else: user_templates = set([])
    etc_templates = user_templates | default_templates

    context = {'host_ip':socket.gethostbyname(env.host)}
    if env.overwrite or env.installed_packages[env.host]: mod_only = False
    else: mod_only = True
    for t in etc_templates:
        dest = t.replace('woven','',1)
        directory,filename = os.path.split(dest)
        package_name = filename.split('.')[0]
        if directory in ['/etc','/etc/init.d','/etc/init','/etc/logrotate.d','/etc/rsyslog.d']:
            #must be replacing an existing file
            if not exists(dest) and package_name not in packages: continue
        elif directory == '/etc/ufw/applications.d':
            #must be a package name
            if filename not in packages: continue
        elif not exists(directory, use_sudo=True): continue
        uploaded = upload_template(t,dest,context=context,use_sudo=True, modified_only=mod_only)
            
        if uploaded:
            sudo(' '.join(["chown root:root",dest]))
            if 'init.d' in dest: sudo(' '.join(["chmod ugo+rx",dest]))
            else: sudo(' '.join(["chmod ugo+r",dest]))
            if env.verbosity:
                print " * uploaded",dest

def upload_ssh_key(rollback=False):
    """
    Upload your ssh key for passwordless logins
    """
    auth_keys = '/home/%s/.ssh/authorized_keys'% env.user
    if not rollback:
        local_user = getpass.getuser()
        host = socket.gethostname()
        u = '@'.join([local_user,host])
        u = 'ssh-key-uploaded-%s'% u
        if not env.overwrite and server_state(u): return
        if not exists('.ssh'):
            run('mkdir .ssh')
           
        #determine local .ssh dir
        home = os.path.expanduser('~')
        ssh_key = None
        upload_key = True
        ssh_dsa = os.path.join(home,'.ssh/id_dsa.pub')
        ssh_rsa =  os.path.join(home,'.ssh/id_rsa.pub')
        if env.key_filename and env.INTERACTIVE:
                upload_key = confirm('Would you like to upload your personal key in addition to %s'% str(env.key_filename), default=True)
        if upload_key:  
            if os.path.exists(ssh_dsa):
                ssh_key = ssh_dsa
            elif os.path.exists(ssh_rsa):
                ssh_key = ssh_rsa
    
        if ssh_key:
            ssh_file = open(ssh_key,'r').read()
            
            if exists(auth_keys):
                _backup_file(auth_keys)
            if env.verbosity:
                print env.host, "UPLOADING SSH KEY"
            append(auth_keys,ssh_file) #append prevents uploading twice
            set_server_state(u)
        return
    else:
        if exists(auth_keys+'.wovenbak'):
            _restore_file('/home/%s/.ssh/authorized_keys'% env.user)
        else: #no pre-existing keys remove the .ssh directory
            sudo('rm -rf /home/%s/.ssh')
        return    

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
import sys

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.color import no_style

from fabric import state 
from fabric.network import normalize
from fabric.context_managers import hide,show

from woven.environment import set_env

class WovenCommand(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Do NOT prompt for input (except password entry if required)'),
        make_option('-r', '--reject-unknown-hosts',
            action='store_true',
            default=False,
            help="reject unknown hosts"
        ),
    
        make_option('-D', '--disable-known-hosts',
            action='store_true',
            default=False,
            help="do not load user known_hosts file"
        ),
        make_option('-i',
            action='append',
            dest='key_filename',
            default=None,
            help="path to SSH private key file."
        ),
        
        make_option('-u', '--user',
            default=state._get_system_username(),
            help="username to use when connecting to remote hosts"
        ),
    
        make_option('-p', '--password',
            default=None,
            help="password for use with authentication and/or sudo"
        ),
    
        make_option('--setup',
            help='The /path/to/dir containing the setup.py module. The command will execute from this directory. Only required if you are not executing the command from below the setup.py directory',
        ),
        
    )
    help = ""
    args = "host1 [host2 ...] or user@host1 ..."
    requires_model_validation = False

  
    def handle_host(self, *args, **options):
        """
        This will be executed per host - override in subclass
        """
    def parse_host_args(self, *args):
        """
        Returns a comma separated string of hosts
        """
        return ','.join(args)
        
    def handle(self, *args, **options):
        """
        Initializes the fabric environment
        """
        self.style = no_style()
        #manage.py execution specific variables
        #verbosity 0 = No output at all, 1 = woven output only, 2 = Fabric outputlevel = everything except debug
        state.env.verbosity = int(options.get('verbosity', 1))

        #show_traceback = options.get('traceback', False)
        state.env.INTERACTIVE = options.get('interactive')
        
        #Fabric options
        #Django passes in a dictionary instead of the optparse options objects
        for option in options:
            state.env[option] = options[option]
       
        #args will be tuple. We convert it to a comma separated string for fabric
        all_role_hosts = []

        if args:
            #subclasses can implement parse_host_args to strip out subcommands
            comma_hosts = self.parse_host_args(*args)
            normalized_host_list = comma_hosts.split(',')
            for r in normalized_host_list:
                #define a list of hosts for given roles
                if hasattr(settings,'ROLEDEFS') and settings.ROLEDEFS.get(r): 
                    all_role_hosts+=settings.ROLEDEFS[r]
                    state.env['roles'] = state.env['roles'] + [r]
                #simple single host 
                else: 
                    all_role_hosts.append(r)
            
        #if no args are given we'll use either a 'default' roledef/role_node
        #or as last resort we'll use a simple HOSTS list
        elif hasattr(settings, 'ROLEDEFS') and settings.ROLEDEFS.get('default'):
            all_role_hosts = settings.ROLEDEFS['default']
            state.env['roles'] = ['default']
        elif hasattr(settings,'HOSTS') and settings.HOSTS:
            all_role_hosts = settings.HOSTS
        else:
            print "Error: You must include a host or role in the command line or set HOSTS or ROLEDEFS in your settings file"
            sys.exit(1)
        state.env['hosts'] = all_role_hosts
                    
        #This next section is taken pretty much verbatim from fabric.main
        #so we follow an almost identical but more limited execution strategy
        
        #We now need to load django project woven settings into env
        #This is the equivalent to module level execution of the fabfile.py.
        #If we were using a fabfile.py then we would include set_env()

        if int(state.env.verbosity) < 2:
            with hide('warnings', 'running', 'stdout', 'stderr'):
                set_env(settings,state.env.setup)
        else: set_env(settings,state.env.setup)
        
        #Back to the standard execution strategy
        # Set host list (also copy to env)
        state.env.all_hosts = hosts = state.env.hosts
        # If hosts found, execute the function on each host in turn
        for host in hosts:
            # Preserve user
            prev_user = state.env.user
            # Split host string and apply to env dict
            #TODO - This section is replaced by network.interpret_host_string in Fabric 1.0
            username, hostname, port = normalize(host)
            state.env.host_string = host
            state.env.host = hostname
            state.env.user = username
            state.env.port = port

            # Actually run command
            if int(state.env.verbosity) < 2:
                with hide('warnings', 'running', 'stdout', 'stderr'):
                    self.handle_host(*args, **options)
            else:
                self.handle_host(*args, **options)
            # Put old user back
            state.env.user = prev_user

########NEW FILE########
__FILENAME__ = activate
#!/usr/bin/env python
from optparse import make_option

from fabric.state import env

from woven.environment import project_version
from woven.virtualenv import activate
from woven.management.base import WovenCommand

class Command(WovenCommand):
    """
    Active a project version
    
    e.g. python manage.py activate 0.1
    """

    help = "Activate a version of your project"
    requires_model_validation = False
    args = "version user@ipaddress [host2...]"
    
    def parse_host_args(self, *args):
        """
        Returns a comma separated string of hosts
        """
        return ','.join(args[1:])
    
    def handle_host(self,*args, **options):
        vers = args[0]
        env.nomigration = True
        with project_version(vers):        
            activate()

        return
########NEW FILE########
__FILENAME__ = bundle
#!/usr/bin/env python
from optparse import make_option
from glob import glob
import os

from django.core.management.base import BaseCommand
from django.core.management.color import no_style

from fabric import state
from fabric.operations import local
from fabric.context_managers import hide

from woven.environment import set_env

class Command(BaseCommand):
    """
    Pip bundle your requirements into .pybundles for efficient deployment
    
    python manage.py bundle
    """    
    help = "Pip bundle your requirements into .pybundles for efficient deployment"
    args = ""
    requires_model_validation = False
    
    def handle(self, *args, **options):
        
        self.style = no_style()
        #manage.py execution specific variables
        #verbosity 0 = No output at all, 1 = woven output only, 2 = Fabric outputlevel = everything except debug
        state.env.verbosity = int(options.get('verbosity', 1))

        #show_traceback = options.get('traceback', False)
        set_env.no_domain = True
        state.env.INTERACTIVE = options.get('interactive')
        if int(state.env.verbosity) < 2:
            with hide('warnings', 'running', 'stdout', 'stderr'):
                set_env()
        else:
            set_env()
        if not state.env.PIP_REQUIREMENTS: req_files = glob('req*')
        else: req_files = state.env.PIP_REQUIREMENTS
        dist_dir = os.path.join(os.getcwd(),'dist')
        if not os.path.exists(dist_dir):
            os.mkdir(dist_dir)
        for r in req_files:
            bundle = ''.join([r.split('.')[0],'.zip'])
            command = 'pip bundle -r %s %s/%s'% (r,dist_dir,bundle)
            if state.env.verbosity: print command
            if int(state.env.verbosity) < 2:
                with hide('warnings', 'running', 'stdout', 'stderr'):
                    local(command)
            else:
                local(command)
        
        
########NEW FILE########
__FILENAME__ = deploy
#!/usr/bin/env python
from optparse import make_option

from fabric.context_managers import settings

from woven.api import deploy
from woven.virtualenv import activate
from woven.management.base import WovenCommand


class Command(WovenCommand):
    """
    Deploy your project to a host and activate
    
    Basic Usage:
    ``python manage.py deploy [user]@[hoststring]``
    
    Examples:
    ``python manage.py deploy woven@192.168.188.10``
    ``python manage.py deploy woven@host.example.com``
    
    For just the current user
    ``python manage.py deploy host.example.com``
    
    """
    option_list = WovenCommand.option_list + (
        make_option('-m', '--migration',
            default='', #use south default run all migrations
            help="Specify a specific migration to run"
        ),
        make_option('--fake',
            action='store_true',
            default=False,
            help="Fake the south migration. Useful when converting an app"
        ),        
        make_option('--nomigration',
            action='store_true',
            default=False,
            help="Do not run any migration"
        ),
        make_option('--manualmigration',
            action='store_true',
            default=False,
            help="Manage the database migration manually"
        ),
        make_option('--overwrite',
            action='store_true',
            default=False,
            help="Overwrite an existing installation"
        ),
        
    )
    help = "Deploy the current version of your project"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        self.validate()
        deploy(overwrite=options.get('overwrite'))
        
        with settings(nomigration = options.get('nomigration'),
                      migration = options.get('migration'),
                      manualmigration = options.get('manualmigration')):
            activate()


########NEW FILE########
__FILENAME__ = node
#!/usr/bin/env python
"""
Node command to execute arbitrary commands on a host.
"""
from optparse import make_option
from fabric.state import env
from fabric.context_managers import cd
from fabric.operations import run

from woven.management.base import WovenCommand

class Command(WovenCommand):
    """
    Run a management command on a host
    
    Basic Usage:
    ``python manage.py node [user]@[hoststring] --options="[option ...]"``

    """
    option_list = WovenCommand.option_list + (
        make_option('--options',
            help='Store all the management command options in a string. ie --options="--[opt]=[value] ..."'),
    )
    help = """Execute a management command on one or more hosts"""\
    """ Must not require user input"""
    requires_model_validation = False
    
    args = "command user@ipaddress ..."
    
    def parse_host_args(self, *args):
        """
        Splits out the management command and returns a comma separated list of host_strings
        """
        #This overrides the base command
        return ','.join(args[1:])
        
    def handle_host(self,*args, **options):
        opts = options.get('options')
        command = args[0]
        path = '/home/%s/%s/env/%s/project/%s/'% (env.user,root_domain(),env.project_fullname,env.project_name)
        pythonpath = '/home/%s/%s/env/%s/bin/python'% (env.user,env.root_domain,env.project_fullname)
        with cd(path):     
            result = run(' '.join([pythonpath,'manage.py',command,opts]))
        if env.verbosity:
            print result
 
########NEW FILE########
__FILENAME__ = patch
#!/usr/bin/env python
from optparse import make_option

from fabric.context_managers import settings

from woven.api import deploy, activate
from woven.api import deploy_project, deploy_templates, deploy_static, deploy_media
from woven.api import deploy_wsgi, deploy_webconf

from woven.management.base import WovenCommand

class Command(WovenCommand):
    """
    Patch the current version of your project on hosts and restart webservices
    Includes project, web configuration, media, and wsgi but does not pip install
    
    Basic Usage:
    ``python manage.py patch [user]@[hoststring]``
    
    Examples:
    ``python manage.py patch woven@192.168.188.10``
    ``python manage.py patch woven@host.example.com``
    
    For just the current user
    ``python manage.py patch host.example.com``
    
    """

    help = "Patch all parts of the current version of your project, or patch part of the project"
    args = "[project|templates|static|media|wsgi|webconf] [user@hoststring ...]"
    requires_model_validation = False

    def parse_host_args(self, *args):
        """
        Splits out the patch subcommand and returns a comma separated list of host_strings
        """
        self.subcommand = None
        new_args = args
        try:
            sub = args[0]
            if sub in ['project','templates','static','media','wsgi','webconf']:
                self.subcommand = args[0]
                new_args = args[1:]
        except IndexError:
            pass
        
        return ','.join(new_args)
    
    def handle_host(self,*args, **options):
        with settings(patch=True):
            if not self.subcommand:
                deploy()
                activate()
            else:
                eval(''.join(['deploy_',self.subcommand,'()']))
                activate()



########NEW FILE########
__FILENAME__ = startsites
#!/usr/bin/env python
from optparse import make_option
import os

from fabric import state
from fabric.decorators import runs_once
from fabric.context_managers import settings
from fabric.operations import sudo
from fabric.contrib.files import exists

from woven.management.base import WovenCommand
from woven.webservers import _get_django_sites, deploy_wsgi, deploy_webconf, domain_sites, reload_webservers
from woven.project import deploy_sitesettings

class Command(WovenCommand):
    """
    Create sitesetting files for new django.contrib.sites.
    
    In django site creation is through the production database. The startsite command
    creates the sitesetting files for each of the new sites, and deploys them.
    
    Basic Usage:
    ``python manage.py startsite [hoststring|role]``
    
    """
    help = "Create a sitesetting file for new django sites"
    requires_model_validation = False

    def handle_host(self,*args, **options):
        with settings(patch=True):
            deploy_wsgi()
            deploy_webconf()
        
        activate_sites = [''.join([d.name.replace('.','_'),'-',state.env.project_version,'.conf']) for d in domain_sites()]
        site_paths = ['/etc/apache2','/etc/nginx']
        
        #activate new sites
        for path in site_paths:
            for site in activate_sites:
                if not exists('/'.join([path,'sites-enabled',site])):
                    sudo("chmod 644 %s" % '/'.join([path,'sites-available',site]))
                    sudo("ln -s %s/sites-available/%s %s/sites-enabled/%s"% (path,site,path,site))
                    if state.env.verbosity:
                        print " * enabled", "%s/sites-enabled/%s"% (path,site)
        reload_webservers()
        
     


########NEW FILE########
__FILENAME__ = project
#!/usr/bin/env python
"""
Anything related to deploying your project modules, media, and data
"""
import os, shutil, sys

from django.template.loader import render_to_string

from fabric.state import env
from fabric.operations import local, run, put, sudo
from fabric.decorators import runs_once
from fabric.contrib.files import exists
from fabric.contrib.console import confirm
#Required for a bug in 0.9
from fabric.version import get_version

from woven.decorators import run_once_per_version
from woven.deployment import deploy_files
from woven.environment import deployment_root, _root_domain

@runs_once
def _make_local_sitesettings(overwrite=False):
    local_settings_dir = os.path.join(os.getcwd(),env.project_package_name,'sitesettings')
    if not os.path.exists(local_settings_dir) or overwrite:
        if overwrite:
            shutil.rmtree(local_settings_dir,ignore_errors=True)
        os.mkdir(local_settings_dir)
        f = open(os.path.join(local_settings_dir,'__init__.py'),"w")
        f.close()

    settings_file_path = os.path.join(local_settings_dir,'settings.py')
    if not os.path.exists(settings_file_path):
        root_domain = _root_domain()    
        u_domain = root_domain.replace('.','_')
        output = render_to_string('woven/sitesettings.txt',
                {"deployment_root":deployment_root(),
                "site_id":"1",
                "project_name": env.project_name,
                "project_fullname": env.project_fullname,
                "project_package_name": env.project_package_name,
                "u_domain":u_domain,
                "domain":root_domain,
                "user":env,
                "MEDIA_URL":env.MEDIA_URL,
                "STATIC_URL":env.STATIC_URL}
            )
                    
        f = open(settings_file_path,"w+")
        f.writelines(output)
        f.close()
        if env.verbosity:
            print "Created local sitesettings folder and default settings file"
        #copy manage.py into that directory
        manage_path = os.path.join(os.getcwd(),env.project_package_name,'manage.py')
        dest_manage_path = os.path.join(os.getcwd(),env.project_package_name,'sitesettings','manage.py')
        shutil.copy(manage_path, dest_manage_path)

    return

@run_once_per_version
def deploy_project():
    """
    Deploy to the project directory in the virtualenv
    """
    
    project_root = '/'.join([deployment_root(),'env',env.project_fullname,'project'])
    local_dir = os.getcwd()
    
    if env.verbosity:
        print env.host,"DEPLOYING project", env.project_fullname
    #Exclude a few things that we don't want deployed as part of the project folder
    rsync_exclude = ['local_settings*','*.pyc','*.log','.*','/build','/dist','/media*','/static*','/www','/public','/template*']

    #make site local settings if they don't already exist
    _make_local_sitesettings()
    created = deploy_files(local_dir, project_root, rsync_exclude=rsync_exclude)
    if not env.patch:
        #hook the project into sys.path
        pyvers = run('python -V').split(' ')[1].split('.')[0:2] #Python x.x.x
        sitepackages = ''.join(['lib/python',pyvers[0],'.',pyvers[1],'/site-packages'])
        link_name = '/'.join([deployment_root(),'env',env.project_fullname,sitepackages,env.project_package_name])
        target = '/'.join([project_root,env.project_package_name])
        run(' '.join(['ln -s',target,link_name]))
        
        #make sure manage.py has exec permissions
        managepy = '/'.join([target,'sitesettings','manage.py'])
        if exists(managepy):
            sudo('chmod ugo+x %s'% managepy)
    
    return created

def deploy_sitesettings():
    """
    Deploy to the project directory in the virtualenv
    """
    
    sitesettings = '/'.join([deployment_root(),'env',env.project_fullname,'project',env.project_package_name,'sitesettings'])
    local_dir = os.path.join(os.getcwd(),env.project_package_name,'sitesettings')
 
    created = deploy_files(local_dir, sitesettings)
    if env.verbosity and created:
        print env.host,"DEPLOYING sitesettings"
        for path in created:
            tail = path.split('/')[-1]
            print ' * uploaded',tail

@run_once_per_version
def deploy_templates():
    """
    Deploy any templates from your shortest TEMPLATE_DIRS setting
    """
    
    deployed = None
    if not hasattr(env, 'project_template_dir'):
        #the normal pattern would mean the shortest path is the main one.
        #its probably the last listed
        length = 1000   
        for dir in env.TEMPLATE_DIRS:
            if dir:
                len_dir = len(dir)
                if len_dir < length:
                    length = len_dir
                    env.project_template_dir = dir
    
    if hasattr(env,'project_template_dir'):
        remote_dir = '/'.join([deployment_root(),'env',env.project_fullname,'templates'])
        if env.verbosity:
            print env.host,"DEPLOYING templates", remote_dir
        deployed = deploy_files(env.project_template_dir,remote_dir)
    return deployed
     
@run_once_per_version
def deploy_static():
    """
    Deploy static (application) versioned media
    """
    
    if not env.STATIC_URL or 'http://' in env.STATIC_URL: return
    from django.core.servers.basehttp import AdminMediaHandler
    remote_dir = '/'.join([deployment_root(),'env',env.project_fullname,'static'])
    m_prefix = len(env.MEDIA_URL)
    #if app media is not handled by django-staticfiles we can install admin media by default
    if 'django.contrib.admin' in env.INSTALLED_APPS and not 'django.contrib.staticfiles' in env.INSTALLED_APPS:
        
        if env.MEDIA_URL and env.MEDIA_URL == env.ADMIN_MEDIA_PREFIX[:m_prefix]:
            print "ERROR: Your ADMIN_MEDIA_PREFIX (Application media) must not be on the same path as your MEDIA_URL (User media)"
            sys.exit(1)
        admin = AdminMediaHandler('DummyApp')
        local_dir = admin.base_dir
        remote_dir =  ''.join([remote_dir,env.ADMIN_MEDIA_PREFIX])
    else:
        if env.MEDIA_URL and env.MEDIA_URL == env.STATIC_URL[:m_prefix]:
            print "ERROR: Your STATIC_URL (Application media) must not be on the same path as your MEDIA_URL (User media)"
            sys.exit(1)
        elif env.STATIC_ROOT:
            local_dir = env.STATIC_ROOT
            static_url = env.STATIC_URL[1:]
            if static_url:
                remote_dir = '/'.join([remote_dir,static_url])
        else: return
    if env.verbosity:
        print env.host,"DEPLOYING static",remote_dir
    return deploy_files(local_dir,remote_dir)

@run_once_per_version       
def deploy_media():
    """
    Deploy MEDIA_ROOT unversioned on host
    """
    if not env.MEDIA_URL or not env.MEDIA_ROOT or 'http://' in env.MEDIA_URL: return
    local_dir = env.MEDIA_ROOT
    
    remote_dir = '/'.join([deployment_root(),'public']) 
    media_url = env.MEDIA_URL[1:]
    if media_url:
        remote_dir = '/'.join([remote_dir,media_url])
    if env.verbosity:
        print env.host,"DEPLOYING media",remote_dir    
    deployed = deploy_files(local_dir,remote_dir)
    
    #make writable for www-data for file uploads
    sudo("chown -R www-data:sudo %s" % remote_dir)
    sudo("chmod -R ug+w %s"% remote_dir)
    return deployed

@runs_once
def deploy_db(rollback=False):
    """
    Deploy a sqlite database from development
    """
    if not rollback:

        if env.DEFAULT_DATABASE_ENGINE=='django.db.backends.sqlite3':
            db_dir = '/'.join([deployment_root(),'database'])
            db_name = ''.join([env.project_name,'_','site_1','.db'])
            dest_db_path = '/'.join([db_dir,db_name])
            if exists(dest_db_path): return
            if env.verbosity:
                print env.host,"DEPLOYING DEFAULT SQLITE DATABASE"
            if not env.DEFAULT_DATABASE_NAME:
                print "ERROR: A database name has not been defined in your Django settings file"
                sys.exit(1)

            if env.DEFAULT_DATABASE_NAME[0] not in [os.path.sep,'.']: #relative path
                db_path = os.path.join(os.getcwd(),env.project_package_name,env.DEFAULT_DATABASE_NAME)

            elif env.DEFAULT_DATABASE_NAME[:2] == '..':
                print "ERROR: Use a full expanded path to the database in your Django settings"
                sys.exit(1)
            else:
                db_path = env.DEFAULT_DATABASE_NAME

            if not db_path or not os.path.exists(db_path):
                print "ERROR: the database %s does not exist. \nRun python manage.py syncdb to create your database locally first, or check your settings."% db_path
                sys.exit(1)

            db_name = os.path.split(db_path)[1]  
            run('mkdir -p '+db_dir)
            put(db_path,dest_db_path)
            #directory and file must be writable by webserver
            sudo("chown -R %s:www-data %s"% (env.user,db_dir))
            sudo("chmod -R ug+w %s"% db_dir)
        
        elif env.DEFAULT_DATABASE_ENGINE=='django.db.backends.':
            print "ERROR: The default database engine has not been defined in your Django settings file"
            print "At a minimum you must define an sqlite3 database for woven to deploy, or define a database that is managed outside of woven."
            sys.exit(1)
    elif rollback and env.DEFAULT_DATABASE_ENGINE=='django.db.backends.sqlite3':
        if env.INTERACTIVE:
            delete = confirm('DELETE the database on the host?',default=False)
            if delete:
                run('rm -f '+db_name)
    return

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Woven settings for {{ project_name }} Django 1.3 project.


from os import path
PROJECT_ROOT = path.dirname(path.realpath(__file__))
DISTRIBUTION_ROOT = path.split(PROJECT_ROOT)[0]

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': path.join(DISTRIBUTION_ROOT,'database','default.db') ,                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = DISTRIBUTION_ROOT + '/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = DISTRIBUTION_ROOT + '/static/'

# URL that handles the static files served from STATIC_ROOT.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# A list of locations of additional static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = '{{ project_name }}.urls'

TEMPLATE_DIRS = (
    DISTRIBUTION_ROOT + '/templates/',
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    ## 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    ## 'django.contrib.admindocs',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', '{{ project_name }}.views.home', name='home'),
    # url(r'^{{ project_name }}/', include('{{ project_name }}.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = virtualenv
#!/usr/bin/env python
from glob import glob
import os, sys
import site

from django import get_version
from django.template.loader import render_to_string


from fabric.decorators import runs_once
from fabric.state import env 
from fabric.operations import run, sudo
from fabric.context_managers import cd, settings
from fabric.contrib.files import exists
from fabric.contrib.console import confirm

from woven.decorators import run_once_per_version
from woven.deployment import mkdirs, deploy_files
from woven.environment import deployment_root,set_version_state, version_state, get_packages
from woven.environment import post_exec_hook, State
from woven.webservers import _get_django_sites, _ls_sites, _sitesettings_files, stop_webserver, start_webserver, webserver_list, domain_sites
from fabric.contrib.files import append

def active_version():
    """
    Determine the current active version on the server
    
    Just examine the which environment is symlinked
    """
    
    link = '/'.join([deployment_root(),'env',env.project_name])
    if not exists(link): return None
    active = os.path.split(run('ls -al '+link).split(' -> ')[1])[1]
    return active

def activate():
    """
    Activates the version specified in ``env.project_version`` if it is different
    from the current active version.
    
    An active version is just the version that is symlinked.
    """

    env_path = '/'.join([deployment_root(),'env',env.project_fullname])

    if not exists(env_path):
        print env.host,"ERROR: The version",env.project_version,"does not exist at"
        print env_path
        sys.exit(1)

    active = active_version()
    servers = webserver_list()

    if env.patch or active <> env.project_fullname:
        for s in servers:
            stop_webserver(s)
        
    if not env.patch and active <> env.project_fullname:
        
        if env.verbosity:
            print env.host, "ACTIVATING version", env_path
        
        if not env.nomigration:
            sync_db()
        
        #south migration
        if 'south' in env.INSTALLED_APPS and not env.nomigration and not env.manualmigration:
            migration()
            
        if env.manualmigration or env.MANUAL_MIGRATION: manual_migration()
      
        #activate sites
        activate_sites = [''.join([d.name.replace('.','_'),'-',env.project_version,'.conf']) for d in domain_sites()]
        if 'apache2' in get_packages():
            site_paths = ['/etc/apache2','/etc/nginx']
        else:
            site_paths = ['/etc/nginx']
        
        #disable existing sites
        for path in site_paths:
            for site in _ls_sites('/'.join([path,'sites-enabled'])):
                if site not in activate_sites:
                    sudo("rm %s/sites-enabled/%s"% (path,site))
        
        #activate new sites
        for path in site_paths:
            for site in activate_sites:
                if not exists('/'.join([path,'sites-enabled',site])):
                    sudo("chmod 644 %s" % '/'.join([path,'sites-available',site]))
                    sudo("ln -s %s/sites-available/%s %s/sites-enabled/%s"% (path,site,path,site))
                    if env.verbosity:
                        print " * enabled", "%s/sites-enabled/%s"% (path,site)
        
        #delete existing symlink
        ln_path = '/'.join([deployment_root(),'env',env.project_name])
        run('rm -f '+ln_path)
        #run post deploy hooks
        post_exec_hook('post_deploy')
        #activate
        run('ln -s %s %s'% (env_path,ln_path))

  
        if env.verbosity:
            print env.host,env.project_fullname, "ACTIVATED"
    else:
        if env.verbosity and not env.patch:
            print env.project_fullname,"is the active version"

    if env.patch or active <> env.project_fullname:
        for s in servers:
            start_webserver(s)
        print
    return

@runs_once
def sync_db():
    """
    Runs the django syncdb command
    """
    with cd('/'.join([deployment_root(),'env',env.project_fullname,'project',env.project_package_name,'sitesettings'])):
        venv = '/'.join([deployment_root(),'env',env.project_fullname,'bin','activate'])
        sites = _get_django_sites()
        site_ids = sites.keys()
        site_ids.sort()
        for site in site_ids:
            for settings_file in _sitesettings_files():
                site_settings = '.'.join([env.project_package_name,'sitesettings',settings_file.replace('.py','')])
                if env.verbosity:
                    print " * django-admin.py syncdb --noinput --settings=%s"% site_settings
                output = sudo(' '.join(['source',venv,'&&',"django-admin.py syncdb --noinput --settings=%s"% site_settings]),
                              user='site_%s'% site)
                if env.verbosity:
                    print output

@runs_once
def manual_migration():
    """
    Simple interactive function to pause the deployment.
    A manual migration can be done two different ways:
    Option 1: Enter y to exit the current deployment. When migration is completed run deploy again.
    Option 2: run the migration in a separate shell   
    """
    if env.INTERACTIVITY:
        print "A manual migration can be done two different ways:"
        print "Option 1: Enter y to exit the current deployment. When migration is completed run deploy again."
        print "Option 2: run the migration in a separate shell"
        exit = confirm("Enter y to exit or accept default to complete deployment and activate the new version",default=False)
    else:
        exit = True
    if exit:
        print "Login to your node and run 'workon %s'"% env.project_fullname 
        sys.exit(0)

@runs_once
def migration():
    """
    Integrate with south schema migration
    """

    #activate env        
    with cd('/'.join([deployment_root(),'env',env.project_fullname,'project',env.project_package_name,'sitesettings'])):
        #migrates all or specific env.migration
        venv = '/'.join([deployment_root(),'env',env.project_fullname,'bin','activate'])
        cmdpt1 = ' '.join(['source',venv,'&&'])
        
        sites = _get_django_sites()
        site_ids = sites.keys()
        site_ids.sort()
        for site in site_ids:
            for settings_file in _sitesettings_files():
                site_settings = '.'.join([env.project_package_name,'sitesettings',settings_file.replace('.py','')])
                cmdpt2 = ' '.join(["django-admin.py migrate",env.migration])
                if hasattr(env,"fakemigration"):
                    cmdpt2 = ' '.join([cmdpt2,'--fake'])
                cmdpt2 = ''.join([cmdpt2,'--settings=',site_settings])
                if env.verbosity:
                    print " *", cmdpt2
                output = sudo(' '.join([cmdpt1,cmdpt2]),user='site_%s'% site)
            if env.verbosity:
                print output
    return           

@run_once_per_version
def mkvirtualenv():
    """
    Create the virtualenv project environment
    """
    root = '/'.join([deployment_root(),'env'])
    path = '/'.join([root,env.project_fullname])
    dirs_created = []
    if env.verbosity:
        print env.host,'CREATING VIRTUALENV', path
    if not exists(root): dirs_created += mkdirs(root)
    with cd(root):
        run(' '.join(["virtualenv",env.project_fullname]))
    with cd(path):
        dirs_created += mkdirs('egg_cache')
        sudo('chown -R %s:www-data egg_cache'% env.user)
        sudo('chmod -R g+w egg_cache')
        run(''.join(["echo 'cd ",path,'/','project','/',env.project_package_name,'/sitesettings',"' > bin/postactivate"]))
        sudo('chmod ugo+rwx bin/postactivate')

    #Create a state
    out = State(' '.join([env.host,'virtualenv',path,'created']))
    out.object = dirs_created + ['bin','lib','include']
    out.failed = False
    return out
        
def rmvirtualenv():
    """
    Remove the current or ``env.project_version`` environment and all content in it
    """
    path = '/'.join([deployment_root(),'env',env.project_fullname])
    link = '/'.join([deployment_root(),'env',env.project_name])
    if version_state('mkvirtualenv'):
        sudo(' '.join(['rm -rf',path]))
        sudo(' '.join(['rm -f',link]))
        sudo('rm -f /var/local/woven/%s*'% env.project_fullname)
        set_version_state('mkvirtualenv',delete=True)
      

@run_once_per_version    
def pip_install_requirements():
    """
    Install on current installed virtualenv version from a pip bundle [dist/project name-version].zip or pip ``req.txt``|``requirements.txt``
    or a env.pip_requirements list.
    
    By default it will look for a zip bundle in the dist directory first then a requirements file.

    
    The limitations of installing requirements are that you cannot point directly to packages
    in your local filesystem. In this case you would bundle instead.
    """
    if not version_state('mkvirtualenv'):
        print env.host,'Error: Cannot run pip_install_requirements. A virtualenv is not created for this version. Run mkvirtualenv first'
        return
    if env.verbosity:
        print env.host, 'PIP INSTALLING REQUIREMENTS:'
    
    #Remove any pre-existing pip-log from any previous failed installation
    pip_log_dir = '/'.join(['/home',env.user,'.pip'])
    if exists(pip_log_dir): run('rm -f %s/*.txt'% pip_log_dir)
    
    #determine what req files or bundle files we need to deploy
    if not env.PIP_REQUIREMENTS:
        req_files = {}.fromkeys(glob('req*'))
    else:
        req_files = {}.fromkeys(env.PIP_REQUIREMENTS)
    
    for key in req_files:
        bundle = ''.join([key.split('.')[0],'.zip'])
        if os.path.exists(os.path.join('dist',bundle)):
            req_files[key] = bundle
        
    #determine the django version
    file_patterns =''
    django_version = get_version()
    svn_version = django_version.find('SVN')
    if svn_version > -1:
        django_version = django_version[svn_version+4:]
        django_req = ''.join(['-e svn+http://code.djangoproject.com/svn/django/trunk@',django_version,'#egg=Django'])
    else:
        other_builds = ['alpha','beta','rc']
        for b in other_builds:
            if b in django_version:
                print "ERROR: Unsupported Django version", django_version
                print "Define a DJANGO_REQUIREMENT pointing to the tar.gz for",django_version
                print "and re-deploy, or use the official or SVN release of Django."
                sys.exit(1)
        django_req = ''.join(['Django==',django_version])

    #if no requirements file exists create one
    if not req_files:
        f = open("requirements.txt","w+")
        text = render_to_string('woven/requirements.txt', {'django':django_req})
        f.write(text)
        f.close()
        if env.verbosity:
            print "Created local requirements.txt"
        req_files["requirements.txt"]=''
        
    req_files_list = req_files.keys()
    req_files_list.sort()
    
    #patterns for bundles
    if req_files: file_patterns = '|'.join([file_patterns,'req*.zip'])

    #create a pip cache & src directory
    cache =  '/'.join([deployment_root(),'.pip','cache'])
    src = '/'.join([deployment_root(),'.pip','src'])
    deployed = mkdirs(cache)
    deployed += mkdirs(src)
    #deploy bundles and any local copy of django
    local_dir = os.path.join(os.getcwd(),'dist')
    remote_dir = '/'.join([deployment_root(),'env',env.project_fullname,'dist'])
    if os.path.exists(local_dir):  
        if file_patterns: deployed += deploy_files(local_dir, remote_dir, pattern=file_patterns)
    
    #deploy any requirement files
    deployed +=  deploy_files(os.getcwd(), remote_dir, pattern = 'req*') 
    
    #install in the env
    out = State(' '.join([env.host,'pip install requirements']))
    python_path = '/'.join([deployment_root(),'env',env.project_fullname,'bin','python'])
    with settings(warn_only=True):
        with cd(remote_dir):
            for req in req_files_list:
                bundle = req_files[req]
                if bundle: req=bundle
                if env.verbosity:
                    print ' * installing',req
                if '.zip' in req.lower():
                    install = run('pip install %s -q --environment=%s --log=/home/%s/.pip/%s_pip_log.txt'%
                                  (req, python_path, env.user, req.replace('.','_')))
                  
                else:
                    install = run('pip install -q --environment=%s --src=%s --download-cache=%s --requirement=%s --log=/home/%s/.pip/%s_pip_log.txt'%
                                  (python_path,src,cache,req, env.user,req.replace('.','_')))
                if install.failed:
                    out.failed =True
                    out.stderr += ' '.join([env.host, "ERROR INSTALLING",req,'\n'])
    
    out.object = deployed
              
    if out.failed:
        print out.stderr
        print "Review the pip install logs at %s/.pip and re-deploy"% deployment_root()
        sys.exit(1)
    return out

########NEW FILE########
__FILENAME__ = webservers
#!/usr/bin/env python
import os,socket, sys
import json

from fabric.state import _AttributeDict, env
from fabric.operations import run, sudo
from fabric.context_managers import cd, settings
from fabric.contrib.files import append, contains, exists
from fabric.decorators import runs_once

from woven.decorators import run_once_per_version
from woven.deployment import deploy_files, mkdirs, upload_template
from woven.environment import deployment_root, version_state, _root_domain, get_packages
from woven.linux import add_user

def _activate_sites(path, filenames):
    enabled_sites = _ls_sites(path)            
    for site in enabled_sites:
        if env.verbosity:
            print env.host,'Disabling', site
        if site not in filenames:
            sudo("rm %s/%s"% (path,site))
        
        sudo("chmod 644 %s" % site)
        if not exists('/etc/apache2/sites-enabled'+ filename):
            sudo("ln -s %s%s %s%s"% (self.deploy_root,filename,self.enabled_path,filename))

def _deploy_webconf(remote_dir,template):
    
    if not 'http:' in env.MEDIA_URL: media_url = env.MEDIA_URL
    else: media_url = ''
    if not 'http:' in env.STATIC_URL: static_url = env.STATIC_URL
    else: static_url = ''
    if not static_url: static_url = env.ADMIN_MEDIA_PREFIX
    log_dir = '/'.join([deployment_root(),'log'])
    deployed = []
    users_added = []
    
    domains = domain_sites()
    for d in domains:
        u_domain = d.name.replace('.','_')
        wsgi_filename = d.settings.replace('.py','.wsgi')
        site_user = ''.join(['site_',str(d.site_id)])
        filename = ''.join([remote_dir,'/',u_domain,'-',env.project_version,'.conf'])
        context = {"project_name": env.project_name,
                   "deployment_root":deployment_root(),
                    "u_domain":u_domain,
                    "domain":d.name,
                    "root_domain":env.root_domain,
                    "user":env.user,
                    "site_user":site_user,
                    "SITE_ID":d.site_id,
                    "host_ip":socket.gethostbyname(env.host),
                    "wsgi_filename":wsgi_filename,
                    "MEDIA_URL":media_url,
                    "STATIC_URL":static_url,
                    }

        upload_template('/'.join(['woven',template]),
                        filename,
                        context,
                        use_sudo=True)
        if env.verbosity:
            print " * uploaded", filename
            
        #add site users if necessary
        site_users = _site_users()
        if site_user not in users_added and site_user not in site_users:
            add_user(username=site_user,group='www-data',site_user=True)
            users_added.append(site_user)
            if env.verbosity:
                print " * useradded",site_user

    return deployed

def _site_users():
    """
    Get a list of site_n users
    """
    userlist = sudo("cat /etc/passwd | awk '/site/'").split('\n')
    siteuserlist = [user.split(':')[0] for user in userlist if 'site_' in user]
    return siteuserlist

def _ls_sites(path):
    """
    List only sites in the domain_sites() to ensure we co-exist with other projects
    """
    with cd(path):
        sites = run('ls').split('\n')
        doms =  [d.name for d in domain_sites()]
        dom_sites = []
        for s in sites:
            ds = s.split('-')[0]
            ds = ds.replace('_','.')
            if ds in doms and s not in dom_sites:
                dom_sites.append(s)
    return dom_sites



def _sitesettings_files():
    """
    Get a list of sitesettings files
    
    settings.py can be prefixed with a subdomain and underscore so with example.com site:
    sitesettings/settings.py would be the example.com settings file and
    sitesettings/admin_settings.py would be the admin.example.com settings file
    """
    settings_files = []
    sitesettings_path = os.path.join(env.project_package_name,'sitesettings')
    if os.path.exists(sitesettings_path):
        sitesettings = os.listdir(sitesettings_path)
        for file in sitesettings:
            if file == 'settings.py':
                settings_files.append(file)
            elif len(file)>12 and file[-12:]=='_settings.py': #prefixed settings
                settings_files.append(file)
    return settings_files

def _get_django_sites():
    """
    Get a list of sites as dictionaries {site_id:'domain.name'}

    """
    deployed = version_state('deploy_project')
    if not env.sites and 'django.contrib.sites' in env.INSTALLED_APPS and deployed:
        with cd('/'.join([deployment_root(),'env',env.project_fullname,'project',env.project_package_name,'sitesettings'])):
            venv = '/'.join([deployment_root(),'env',env.project_fullname,'bin','activate'])
            #since this is the first time we run ./manage.py on the server it can be
            #a point of failure for installations
            with settings(warn_only=True):
                output = run(' '.join(['source',venv,'&&',"django-admin.py dumpdata sites --settings=%s.sitesettings.settings"% env.project_package_name]))

                if output.failed:
                    print "ERROR: There was an error running ./manage.py on the node"
                    print "See the troubleshooting docs for hints on how to diagnose deployment issues"
                    if hasattr(output, 'stderr'):
                        print output.stderr
                    sys.exit(1)
            output = output.split('\n')[-1] #ignore any lines prior to the data being dumped
            sites = json.loads(output)
            env.sites = {}
            for s in sites:
                env.sites[s['pk']] = s['fields']['domain']
    return env.sites

def domain_sites():
    """
    Get a list of domains
    
    Each domain is an attribute dict with name, site_id and settings
    """

    if not hasattr(env,'domains'):
        sites = _get_django_sites()
        site_ids = sites.keys()
        site_ids.sort()
        domains = []
        
        for id in site_ids:

            for file in _sitesettings_files():
                domain = _AttributeDict({})

                if file == 'settings.py':
                    domain.name = sites[id]
                else: #prefix indicates subdomain
                    subdomain = file[:-12].replace('_','.')
                    domain.name = ''.join([subdomain,sites[id]])

                domain.settings = file
                domain.site_id = id
                domains.append(domain)
                
        env.domains = domains
        if env.domains: env.root_domain = env.domains[0].name
        else:
            domain.name = _root_domain(); domain.site_id = 1; domain.settings='settings.py'
            env.domains = [domain]
            
    return env.domains

@run_once_per_version
def deploy_webconf():
    """ Deploy nginx and other wsgi server site configurations to the host """
    deployed = []
    log_dir = '/'.join([deployment_root(),'log'])
    #TODO - incorrect - check for actual package to confirm installation
    if webserver_list():
        if env.verbosity:
            print env.host,"DEPLOYING webconf:"
        if not exists(log_dir):
            run('ln -s /var/log log')
        #deploys confs for each domain based on sites app
        if 'apache2' in get_packages():
            deployed += _deploy_webconf('/etc/apache2/sites-available','django-apache-template.txt')
            deployed += _deploy_webconf('/etc/nginx/sites-available','nginx-template.txt')
        elif 'gunicorn' in get_packages():
            deployed += _deploy_webconf('/etc/nginx/sites-available','nginx-gunicorn-template.txt')
        
        if not exists('/var/www/nginx-default'):
            sudo('mkdir /var/www/nginx-default')
        upload_template('woven/maintenance.html','/var/www/nginx-default/maintenance.html',use_sudo=True)
        sudo('chmod ugo+r /var/www/nginx-default/maintenance.html')
    else:
        print env.host,"""WARNING: Apache or Nginx not installed"""
        
    return deployed

@run_once_per_version
def deploy_wsgi():
    """
    deploy python wsgi file(s)
    """ 
    if 'libapache2-mod-wsgi' in get_packages():
        remote_dir = '/'.join([deployment_root(),'env',env.project_fullname,'wsgi'])
        wsgi = 'apache2'
    elif 'gunicorn' in get_packages():
        remote_dir = '/etc/init'
        wsgi = 'gunicorn'
    deployed = []
    
    #ensure project apps path is also added to environment variables as well as wsgi
    if env.PROJECT_APPS_PATH:
        pap = '/'.join([deployment_root(),'env',
                        env.project_name,'project',env.project_package_name,env.PROJECT_APPS_PATH])
        pap = ''.join(['export PYTHONPATH=$PYTHONPATH:',pap])
        postactivate = '/'.join([deployment_root(),'env','postactivate'])
        if not exists(postactivate):
            append('#!/bin/bash', postactivate)
            run('chmod +x %s'% postactivate)
        if not contains('PYTHONPATH',postactivate):
            append(pap,postactivate)
        
    if env.verbosity:
        print env.host,"DEPLOYING wsgi", wsgi, remote_dir

    for file in _sitesettings_files(): 
        deployed += mkdirs(remote_dir)
        with cd(remote_dir):
            settings_module = file.replace('.py','')
            context = {"deployment_root":deployment_root(),
                       "user": env.user,
                       "project_name": env.project_name,
                       "project_package_name": env.project_package_name,
                       "project_apps_path":env.PROJECT_APPS_PATH,
                       "settings": settings_module,
                       }
            if wsgi == 'apache2':
                filename = file.replace('.py','.wsgi')
                upload_template('/'.join(['woven','django-wsgi-template.txt']),
                                filename,
                                context,
                            )
            elif wsgi == 'gunicorn':
                filename = 'gunicorn-%s.conf'% env.project_name
                upload_template('/'.join(['woven','gunicorn.conf']),
                                filename,
                                context,
                                backup=False,
                                use_sudo=True
                            )                
                
            if env.verbosity:
                print " * uploaded", filename
            #finally set the ownership/permissions
            #We'll use the group to allow www-data execute
            if wsgi == 'apache2':
                sudo("chown %s:www-data %s"% (env.user,filename))
                run("chmod ug+xr %s"% filename)
            elif wsgi == 'gunicorn':
                sudo("chown root:root %s"% filename)
                sudo("chmod go+r %s"% filename)
                
    return deployed

def webserver_list():
    """
    list of webserver packages
    """
    p = set(get_packages())
    w = set(['apache2','gunicorn','uwsgi','nginx'])
    installed = p & w
    return list(installed)
    
def reload_webservers():
    """
    Reload apache2 and nginx
    """
    if env.verbosity:
        print env.host, "RELOADING apache2"
    with settings(warn_only=True):
        a = sudo("/etc/init.d/apache2 reload")
        if env.verbosity:
            print '',a        
    if env.verbosity:

        #Reload used to fail on Ubuntu but at least in 10.04 it works
        print env.host,"RELOADING nginx"
    with settings(warn_only=True):
        s = run("/etc/init.d/nginx status")
        if 'running' in s:
            n = sudo("/etc/init.d/nginx reload")
        else:
            n = sudo("/etc/init.d/nginx start")
    if env.verbosity:
        print ' *',n
    return True    

def stop_webserver(server):
    """
    Stop server
    """
    #TODO - distinguish between a warning and a error on apache
    if server == 'apache2':
        with settings(warn_only=True):
            if env.verbosity:
                print env.host,"STOPPING apache2"
            a = sudo("/etc/init.d/apache2 stop")
            if env.verbosity:
                print '',a
    elif server == 'gunicorn':
        with settings(warn_only=True):
            if env.verbosity:
                print env.host,"STOPPING","%s-%s"% (server,env.project_name)
            a = sudo("stop %s-%s"% (server,env.project_name))
            if env.verbosity and a.strip():
                print '',a
    return True

def start_webserver(server):
    """
    Start server
    """
    if server == 'apache2':
        with settings(warn_only=True):
            if env.verbosity:
                print env.host,"STARTING apache2"
            #some issues with pty=True getting apache to start on ec2
            a = sudo("/etc/init.d/apache2 start", pty=False)
            if env.verbosity:
                print '',a
            
        if a.failed:
            print "ERROR: /etc/init.d/apache2 start failed"
            print env.host, a
            sys.exit(1)
    elif server == 'nginx':
        if env.verbosity:
            #Reload used to fail on Ubuntu but at least in 10.04 it works
            print env.host,"RELOADING nginx"
        with settings(warn_only=True):
            s = run("/etc/init.d/nginx status")
            if 'running' in s:
                n = sudo("/etc/init.d/nginx reload")
            else:
                n = sudo("/etc/init.d/nginx start")
        if env.verbosity:
            print ' *',n
    else:
        if env.verbosity:
            print env.host, "STARTING","%s-%s"% (server,env.project_name)
        with settings(warn_only=True):
            n = sudo('start %s-%s'% (server,env.project_name))
            if env.verbosity and n.strip():
                print ' *', n
            
    return True

    
########NEW FILE########
