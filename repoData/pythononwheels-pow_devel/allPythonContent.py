__FILENAME__ = generate_app
#!python
#  pow app generator
#  Generates the PoW Application.
#  options are:
#   see: python generate_app.py --help


from optparse import OptionParser
import sqlite3, sys, os, datetime
import string
import shutil

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./stubs/lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./stubs/models/powmodels" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./scripts" )))
for p in sys.path:
    print p
    

import powlib
import generate_model
    
def main():
    """ 
        Executes the render methods to generate a conroller and basic 
        tests according to the given options 
    """
    parser = OptionParser()
    #mode = MODE_CREATE
    parser.add_option("-n", "--name",  action="store", type="string", dest="name", 
        help="set the app name", default ="None")
    parser.add_option("-d", "--directory",  action="store", type="string", dest="directory", 
        help="app base dir", default ="./")
    parser.add_option("-f", "--force",  action="store_true",  dest="force", 
        help="forces overrides of existing app", default="False")

    (options, args) = parser.parse_args()
    #print options, args
    if options.name == "None":
        if len(args) > 0:
            # if no option flag (like -n) is given, it is assumed that 
            # the first argument is the appname. (representing -n arg1)
            options.name = args[0]
        else:
            parser.error("You must at least specify an appname by giving -n <name>.")
    
    appdir = options.directory
    appname = options.name
    force = options.force
    start = None
    end = None
    start = datetime.datetime.now()

    gen_app(appname, appdir, force)

    end = datetime.datetime.now()
    duration = None
    duration = end - start
    print " -- generated_app in("+ str(duration) +")"

def render_db_config( appname, appbase ):
    """ Creates the db.cfg file for this application and puts it in appname/config/db.cfg"""
    
    infile = open("./stubs/config/db.py")
    instr = infile.read()
    infile.close()
    instr = instr.replace("please_rename_the_development_db", appname + "_devel")
    instr = instr.replace("please_rename_the_test_db", appname + "_test")
    instr = instr.replace("please_rename_the_production_db", appname + "_prod")
    ofile = open( os.path.normpath(appbase + "/config/db.py"), "w" )
    ofile.write(instr)
    ofile.close()
 

    
def gen_app(appname, appdir, force=False):
    """ Generates the complete App Filesystem Structure for Non-GAE Apps.
        Filesystem action like file and dir creation, copy fiels etc. NO DB action in this function 
    """
    
    appname = str(appname)
    appname = str.strip(appname)
    appname = str.lower(appname)
    print " -- generating app:", appname

    powlib.check_create_dir(appdir + appname)
    appbase = os.path.abspath(os.path.normpath(appdir +"/"+ appname + "/"))
    #print appbase
    # defines the subdirts to be created. Form { dir : subdirs }
    subdirs = [ {"config" : [] },  
                        {"db" : [] },
                        {"lib" : [] },
                        {"migrations" : [] },
                        {"models" : ["basemodels"] },
                        {"controllers" : [] },
                        {"public" : ["img", "img/bs", "ico", "css", "css/bs", "js", "js/bs", "doc"] },
                        {"stubs" : ["partials"] },
                        {"views" : ["layouts"] },
                        {"tests" : ["models", "controllers", "integration", "fixtures"] },
                        {"ext" : ["auth", "validate"] }                        
                        ]
    for elem in subdirs:
        for key in elem:
            subdir = os.path.join(appbase,str(key))
            powlib.check_create_dir( subdir)
            for subs in elem[key]:
                powlib.check_create_dir( os.path.join(subdir,str(subs)))
    
    #
    # copy the files in subdirs. Form ( from, to )
    #
    deep_copy_list = [  ("stubs/config", "config"),  
                        ("stubs/lib", "lib"), 
                        ("stubs", "stubs"),
                        ("stubs/migrations","migrations"),
                        ("stubs/partials","stubs/partials"),
                        ("stubs/public/doc","/public/doc"),
                        ("stubs/public/ico","/public/ico"),
                        ("stubs/public/img","/public/img"),
                        ("stubs/public/img/bs","/public/img/bs"),
                        ("stubs/public/css","/public/css"),
                        ("stubs/public/css/bs","/public/css/bs"),
                        ("stubs/public/js", "public/js"),
                        ("stubs/public/js/bs", "public/js/bs"),
                        ("stubs/lib", "lib"), 
                        ("stubs/controllers", "controllers"),
                        ("stubs/views", "views"),
                        ("stubs/views/layouts", "views/layouts"),
                        ("stubs/ext/auth", "ext/auth"),
                        ("stubs/ext/validate", "ext/validate"),
                        ]
                        
    print " -- copying files ..."
    exclude_patterns = [".pyc", ".pyo", ".DS_STORE"]
    exclude_files = [ "db.cfg" ]
    for source_dir, dest_dir in deep_copy_list:
        for source_file in os.listdir(source_dir):
            fname, fext = os.path.splitext(source_file)
            if not fext in exclude_patterns and not source_file in exclude_files:
                powlib.check_copy_file(
                    os.path.join(source_dir,source_file),
                    os.path.join(appbase+"/"+dest_dir,source_file)
                )
            else:
                print " excluded:.EXCL", source_file
                continue
                
    #
    # copy the generator files
    #
    powlib.check_copy_file("scripts/generate_model.py", appbase)
    powlib.check_copy_file("scripts/do_migrate.py", appbase)
    powlib.check_copy_file("scripts/generate_controller.py", appbase)
    powlib.check_copy_file("scripts/generate_migration.py", appbase)
    powlib.check_copy_file("scripts/generate_scaffold.py", appbase)
    powlib.check_copy_file("scripts/generate_mvc.py", appbase)
    powlib.check_copy_file("scripts/simple_server.py", appbase)
    powlib.check_copy_file("pow_router.wsgi", appbase)
    powlib.check_copy_file("scripts/pow_console.py", appbase)
    powlib.check_copy_file("scripts/runtests.py", appbase)
        
    powlib.replace_string_in_file(
        os.path.join(appbase + "/" + "simple_server.py"),
        "#POWAPPNAME",
        appname
    )
    
    powlib.replace_string_in_file(
        os.path.join(appbase + "/" + "pow_router.wsgi"),
        "#POWAPPNAME",
        appname
    )
    
    #
    # copy the initial db's
    #
    appdb = "stubs/db/app_db_including_app_versions_small.db"
    powlib.check_copy_file(appdb, os.path.normpath(appbase + "/db/" + appname + "_prod.db") )
    powlib.check_copy_file(appdb, os.path.normpath(appbase + "/db/" + appname + "_test.db") )
    powlib.check_copy_file(appdb, os.path.normpath(appbase + "/db/" + appname + "_devel.db") )
    #powlib.check_copy_file("stubs/db/empty_app.db", os.path.normpath(appbase + "/db/app.db") )
    
    #
    # initiate the db.cfg file
    #
    render_db_config(appname, appbase)
    
    generate_model.render_model("App", False, "System class containing the App Base Informations", appname)
    generate_model.render_model("Version", False, "System class containing the Versions", appname)
    return
    
    
if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = 00003_post
#
#
# This file was autogenerated by python_on_wheels.
# But YOU CAN EDIT THIS FILE SAFELY
# It will not be overwritten by python_on_wheels
# unless you force it with the -f or --force option
# 
# 2012-09-07

from sqlalchemy import *
from sqlalchemy.schema import CreateTable
from sqlalchemy import event, DDL

import sys
import os

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))

import powlib
from PowTable import PowTable
from BaseMigration import BaseMigration

class Migration(BaseMigration):
    table_name="posts"
    table = None
        
    def up(self):
        """ up method will be executed when running do_migrate -d up"""
          
        self.table = PowTable(self.table_name, self.__metadata__,
            # here is where you define your table (Format see example below)
            # the columns below are just examples.
            # Remember that PoW automatically adds an id and a timestamp column (ID,TIMESTAMP)
            Column('title', String(50)),
            Column('content', Text),
            Column('image', Binary)
            
            #Column('user_id', Integer, ForeignKey('users.id'))
        )
        self.create_table()
        #print CreateTable(self.table)
        
    def down(self):
        """ down method will be executed when running do_migrate -d down"""
        self.drop_table()
########NEW FILE########
__FILENAME__ = BlogPostController
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 
# date created: 	2012-07-22
import sys
import os
from mako.template import Template
from mako.lookup import TemplateLookup
import datetime

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../controllers" )) )

import powlib
import PowObject
import BaseController
import Post

class PostController(BaseController.BaseController):
    def __init__(self):
        self.modelname = "Post"
        BaseController.BaseController.__init__(self)
    
    def list( self, powdict ):
        res = self.model.find_all()
        return self.render(model=self.model, powdict=powdict, list=res)
    
    def blog( self, powdict ):
        res = self.model.find_all()
        return self.render(model=self.model, powdict=powdict, list=res)
    
    def show( self,powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
        
    def new( self, powdict ):
        self.model.__init__()
        dict = powdict["REQ_PARAMETERS"]
        for key in dict:
            statement = "self.model.%s=dict['%s']" % (key,key)
            exec(statement)
        self.model.create()
        return self.render(model=self.model, powdict=powdict)
    
    def create( self, powdict):
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def edit( self, powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
    
    def update( self, powdict ):
        self.model.__init__()
        #print powdict["REQ_PARAMETERS"]
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        #print self.model
        dict = powdict["REQ_PARAMETERS"]
        if dict.has_key("title"):
            self.model.set("title", dict["title"])
        if dict.has_key("content"):
            self.model.set("content", dict["content"])
        if dict.has_key("image"):
            data = dict["image"].file.read()
            ofiledir = os.path.normpath("./public/img/blog/")
            ofilename = os.path.join(ofiledir, dict["image"].filename)
            ofile = open( ofilename , "wb")
            ofile.write(data)
            ofile.close()
            self.model.set("image", dict["image"].filename )

        self.model.update()
        return self.render(model=self.model, powdict=powdict)
    
    def delete( self, powdict ):
        self.model.__init__()
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        self.model.delete(self.model.get_id())
        return self.render(model=self.model, powdict=powdict)

########NEW FILE########
__FILENAME__ = generate_blog
#
# automates the (few) manual steps needed to
# setup a base weblog environment for PoW.
#
# khz (July/2012)
#


import generate_migration
import generate_model
import generate_scaffold
import generate_controller
import sys,os, os.path
import do_migrate

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))

import powlib

def generate_all_for( model ):
    generate_model.render_model(model, True, model + " Model")
    generate_controller.render_controller(model, True)
    generate_scaffold.scaffold(model, True)    
    generate_migration.render_migration(model, model, model + " Migration")
    return


if __name__ == "__main__":
    generate_all_for( "post" )
    #do_migrate.do_migrate(-1, "up")
    
    #do_migrate.do_migrate(-1, "up")
    print " -----------------------------------------------------------"
    print " .. everything has been created, you need to migrate up 2 times"
    print " .. this is not done automatically, since you might want to change the" 
    print " .. tables first."
    print " => see: ./migrations/ folder"
    sys.exit(0)
########NEW FILE########
__FILENAME__ = populate_posts
#
# read bram stoker dracula and make a blog post
# from every chapters first 200 words
#
import sys, string

sys.path.append("../models/")

import Post

if __name__=="__main__":
    f = open("../public/doc/dracula.txt","r")
    counter = 0
    found = False
    postlist = []
    l = [l for l in f.readlines() if l.strip()]
    #print l
    skip = 0
    for line in l:
        counter += 1
        if line.lower().find("chapter") != -1 and skip <= counter:
            print line
            p = Post.Post()
            p.title = l[counter]
            p.content = ""
            content = l[counter+1:counter+20]
            #print content
            for elem in content:
                elem = elem.replace("\n","<br>")
                elem = elem.replace("\r\n","<br>")
                p.content += elem
                #print elem
            skip = counter+3
            p.create()
            print p
    sys.exit(0)
########NEW FILE########
__FILENAME__ = do_migrate
#!python
# do_migrate
# execute db migrations and jobs.
# also modify migrations (erase, set version etc)
#
#

import os
from optparse import OptionParser
import sqlite3
import sqlalchemy
import sys
import datetime

from sqlalchemy.orm import mapper

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))  # lint:ok
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models" )))  # lint:ok
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./controllers" )))  # lint:ok
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./migrations" )))  # lint:ok

import powlib
import App
import PowTable

# setting the right defaults
MODE_CREATE = 1
MODE_REMOVE = 0


def main():
    parser = OptionParser()
    mode = MODE_CREATE

    parser.add_option("-d", "--direction",
                      action="store",
                      type="string",
                      dest="direction",
                      help="migrate up or down",
                      default="None")
    parser.add_option("-v", "--version",
                      action="store",
                      type="string",
                      dest="version",
                      help="migrates to version ver",
                      default="None")
    parser.add_option("-e", "--erase",
                      action="store_true",
                      dest="erase",
                      help="erases version ver",
                      default="False")
    parser.add_option("-i", "--info",
                      action="store_true",
                      dest="info",
                      help="shows migration information",
                      default="False")
    parser.add_option("-j", "--job",
                      action="store",
                      type="string", dest="job",
                      help="executes a migration job",
                      default="None")
    parser.add_option("-m", "--method",
                      action="store", type="string",
                      dest="method",
                      help="execute the given method. Only in with -j",
                      default="None")
    parser.add_option("-s", "--set-currentversion",
                      action="store",
                      type="string",
                      dest="set_curr_version",
                      help="sets cuurentversion to given version ver",
                      default="None")

    (options, args) = parser.parse_args()
    #print options
    if options.info is True:
        show_info()
        return

    if options.version == "None":
        ver = None
    else:
        ver = int(options.version)

    start = None
    end = None
    start = datetime.datetime.now()

    if options.erase is True:
        do_erase()
    elif options.set_curr_version != "None":
        set_currentversion(options.set_curr_version)
    elif options.job != "None":
        if options.direction == "None" and options.method == "None":
            print "You must at least give a direction -d up",
            print "OR -d down OR a method with -m"
            return
        else:
            do_job(options, options.job, options.method)
    else:
        if options.direction == "None" and ver == -1:
            print "You must at least give a direction -d up OR -d down"
            return
        else:
            do_migrate(ver, options.direction)

    end = datetime.datetime.now()
    duration = None
    duration = end - start
    print "migrated in(" + str(duration) + ")"


def do_job(options, filename, method):
    print "migrating"
    #print options
    # get rid of trailing directories
    h, t = os.path.split(filename)
    # get rid of file extensions
    filename, ext = os.path.splitext(t)
    #print filename
    # load the class
    mig = powlib.load_class(filename, "Migration")
    # execute the given method
    if method != "None":
        eval("mig." + str(method) + "()")
    elif options.direction == "up":
        mig.up()
    elif options.direction == "down":
        mig.down()
    else:
        raise StandardError("Migration Direction is neither <up> nor <down>.")
    return


def do_migrate(goalversion, direction):
    #powlib.load_module("App")
    print "..migrating "
    app = powlib.load_class("App", "App")
    app_versions = powlib.load_class("Version", "Version")
    sess = app.pbo.getSession()
    app = sess.query(App.App).first()
    #print app
    #print "name: " + app.name
    #print "path: " + app.path
    print " -- currentversion: " + str(app.currentversion)
    #print "maxversion: " + str(app.maxversion)

    currentversion = int(app.currentversion)
    maxversion = int(app.maxversion)

    times = 1
    if goalversion is None:
        # -d up or down was given
        if direction == "down" and currentversion == 2:
            #then the App or versions table would be migrated down
            # which will break the environment.
            print " -- Error: you are attemting to migrate down the ",
            print " sytem tables .. bailing out"
            return
    elif goalversion > maxversion:
        print " -- Error: version would become greater than",
        print " Maxversion.. bailing out"
        return
    else:
        print " -- migrating to version:" + str(goalversion)
        # setting number of times to run
        if goalversion < currentversion:
            direction = "down"
            times = currentversion - goalversion
        elif goalversion >= currentversion:
            direction = "up"
            times = goalversion - currentversion
        else:
            times = 0
        print " -- Running " + str(times) + " times: "
    sess.add(app)

    if goalversion and (goalversion < 2):
        #then the App or versions table would be migrated down
        # which will break the environment.
        print " -- Error: you are attemting to migrate down the",
        print " sytem tables .. bailing out"
        return

    for run in range(0, times):
        #
        # migrate up
        if direction == "up":
            if currentversion > maxversion:
                print " -- Error: version would become greater than ",
                print "Maxversion.. bailing out"
                return
            currentversion += 1
            ver = app_versions.find_by("version", currentversion)
            #filename = os.path.normpath ( powlib.version_to_string(currentversion) +"_" + "migration"  )  # lint:ok
            filename = ver.filename
            mig = powlib.load_class(filename, "Migration")
            mig.up()
            print '{0:18} ==> {1:5} ==> {2:30}'.format(
                        " -- Migration run #", str(run + 1).zfill(3), filename
                        )
        #
        # migrate down
        #
        elif direction == "down":
            if currentversion <= 2:
                print " -- Error: version would become less than 2 ",
                print " which would affect System tables .. bailing out"
                return

            #filename = os.path.normpath ( powlib.version_to_string(currentversion) +"_" + "migration"  )  # lint:ok
            ver = app_versions.find_by("version", currentversion)
            filename = ver.filename
            mig = powlib.load_class(filename, "Migration")
            mig.down()
            currentversion -= 1
            print '{0:18} ==> {1:5} ==> {2:20}'.format(" -- Migration run",  str(run+1).zfill(5), filename)  # lint:ok
        else:
            raise StandardError("Direction must be either up or down")

    print " -- setting currentversion to: " + str(currentversion)
    app.currentversion = currentversion
    #sess.dirty
    sess.commit()
    return


def drop_table(tablename, **kwargs):
    model = PowTable.PowTable()
    modelname = powlib.table_to_model(tablename)
    model = powlib.load_class(modelname, modelname)
    #print type(model)
    #powlib.print_sorted(dir(model))
    if not "checkfirst" in kwargs:
        kwargs["checkfirst"] = "False"
        print " -- set checkfirst=", kwargs["checkfirst"]
    model.__table__.drop(**kwargs)
    print " -- dropped table: ", tablename
    return

def set_currentversion(ver):

    print "migrating "
    app = powlib.load_class("App", "App")
    app_versions = powlib.load_class("Version", "Version")
    sess = app.pbo.getSession()
    app = sess.query(App.App).first()
    #print app
    #print "name: " + app.name
    #print "path: " + app.path
    print " -- currentversion: " + str(app.currentversion)
    print " -- setting currentversion to: " + str(ver)
    #print "maxversion: " + str(app.maxversion)
    goalversion = int(ver)
    if goalversion >= 0 and goalversion <= app.maxversion:
        app.currentversion = ver
    else:
        print " -- ERROR: new currentversion <=0 or >= maxversion"
        return
    sess.commit()
    return


def do_erase():
    app = powlib.load_class("App", "App")
    app_version = powlib.load_class("Version", "Version")
    sess = app.pbo.getSession()
    app = sess.query(App.App).first()
    print " -- erasing migration version:", str(app.maxversion)

    sess.add(app)

    maxversion = int(app.maxversion)
    currversion = int(app.currentversion)
    #
    # only delete a migration file if it is not in use
    #(so the current mig is not baed on it)
    #
    if maxversion == currversion:
        print "cannot delete the currently active migration version. ",
        print " Migrate down first"
        return
    # get the version-info from app.db.version
    ver = app_version.find_by("version", maxversion)
    #sess.add(ver)

    filename = ver.filename + ".py"
    filename_pyc = filename + "c"

    print "attempting to delete version: " + str(maxversion) + "->" + filename
    if os.path.isfile(os.path.normpath("./migrations/" + filename)):
        os.remove(os.path.normpath("./migrations/" + filename))
        print " -- deleted: ", filename
    if os.path.isfile(os.path.normpath("./migrations/" + filename_pyc)):
        os.remove(os.path.normpath("./migrations/" + filename_pyc))
        print " -- deleted: ", filename_pyc

    #  delete the app.db.version entry
    ver.delete()

    maxversion -= 1
    print "setting new currentversion to: " + str(currversion)
    app.maxversion = maxversion
    print "setting new maxversion to: " + str(maxversion)
    #sess.dirty
    sess.commit()


def show_info():
    app = powlib.load_class("App", "App")
    app_versions = powlib.load_class("Version", "Version")
    sess = app.pbo.getSession()
    app = sess.query(App.App).first()
    print "showing migration information for"
    #print " -- Appname: " + app.name
    print " -- currentversion is : " + str(app.currentversion)
    print " -- max version is : " + str(app.maxversion)


def getTimes(migv, goalv):
    if migv < goalv:
        pass


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = generate_app
#!python
#  pow app generator
#  Generates the PoW Application.
#  options are:
#   see: python generate_app.py --help


from optparse import OptionParser
import sqlite3, sys, os, datetime
import string
import shutil

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./stubs/lib" )))  # lint:ok
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./stubs/models/powmodels" )))  # lint:ok
#for p in sys.path:
#    print p


import powlib
import generate_model


def main():
    """ Executes the render methods to generate a conroller and basic
        tests according to the given options """
    parser = OptionParser()
    #mode = MODE_CREATE
    parser.add_option("-n", "--name",
                      action="store",
                      type="string",
                      dest="name",
                      help="set the app name",
                      default="None")
    parser.add_option("-d", "--directory",
                      action="store",
                      type="string",
                      dest="directory",
                      help="app base dir",
                      default="./")
    parser.add_option("-f", "--force",
                      action="store_true",
                      dest="force",
                      help="forces overrides of existing app",
                      default="False")

    (options, args) = parser.parse_args()
    #print options, args
    if options.name == "None":
        if len(args) > 0:
            # if no option flag (like -n) is given, it is assumed that
            # the first argument is the appname. (representing -n arg1)
            options.name = args[0]
        else:
            parser.error(
                "You must at least specify an appname by giving -n <name>."
                )

    appdir = options.directory
    appname = options.name
    force = options.force
    start = None
    end = None
    start = datetime.datetime.now()

    gen_app(appname, appdir, force)

    end = datetime.datetime.now()
    duration = None
    duration = end - start
    print " -- generated_app in(" + str(duration) + ")"


def render_db_config(appname, appbase):
    """ Creates the db.cfg file for this application
        and puts it in appname/config/db.cfg"""

    infile = open("./stubs/config/db.py")
    instr = infile.read()
    infile.close()
    instr = instr.replace("please_rename_the_development_db", appname + "_devel")  # lint:ok
    instr = instr.replace("please_rename_the_test_db", appname + "_test")
    instr = instr.replace("please_rename_the_production_db", appname + "_prod")
    ofile = open(os.path.normpath(appbase + "/config/db.py"), "w")
    ofile.write(instr)
    ofile.close()


def gen_app(appname, appdir, force=False):
    """ Generates the complete App Filesystem Structure for Non-GAE Apps.
        Filesystem action like file and dir creation, copy fiels etc.
        NO DB action in this function """

    appname = str(appname)
    appname = str.strip(appname)
    appname = str.lower(appname)
    print " -- generating app:", appname

    powlib.check_create_dir(appdir + appname)
    appbase = os.path.abspath(os.path.normpath(appdir + "/" + appname + "/"))
    #print appbase
    # defines the subdirts to be created. Form { dir : subdirs }
    subdirs = [
                {"config": []},
                {"db": []},
                {"lib": []},
                {"migrations": []},
                {"models": ["basemodels"]},
                {"controllers": []},
                {"public": ["img",
                            "img/bs",
                            "ico",
                            "css",
                            "css/bs",
                            "js",
                            "js/bs",
                            "doc"]},
                {"stubs": ["partials"]},
                {"views": ["layouts"]},
                {"tests": ["models",
                           "controllers",
                           "integration",
                           "fixtures"]},
                {"ext": ["auth", "validate"]}
              ]
    for elem in subdirs:
        for key in elem:
            subdir = os.path.join(appbase, str(key))
            powlib.check_create_dir(subdir)
            for subs in elem[key]:
                powlib.check_create_dir(os.path.join(subdir, str(subs)))

    #
    # copy the files in subdirs. Form ( from, to )
    #
    deep_copy_list = [("stubs/config", "config"),
                       ("stubs/lib", "lib"),
                       ("stubs", "stubs"),
                       ("stubs/migrations", "migrations"),
                       ("stubs/partials", "stubs/partials"),
                       ("stubs/public/doc", "/public/doc"),
                       ("stubs/public/ico", "/public/ico"),
                       ("stubs/public/img", "/public/img"),
                       ("stubs/public/img/bs", "/public/img/bs"),
                       ("stubs/public/css", "/public/css"),
                       ("stubs/public/css/bs", "/public/css/bs"),
                       ("stubs/public/js", "public/js"),
                       ("stubs/public/js/bs", "public/js/bs"),
                       ("stubs/lib", "lib"),
                       ("stubs/controllers", "controllers"),
                       ("stubs/views", "views"),
                       ("stubs/views/layouts", "views/layouts"),
                       ("stubs/ext/auth", "ext/auth"),
                       ("stubs/ext/validate", "ext/validate"),
                       ]

    print " -- copying files ..."
    exclude_patterns = [".pyc", ".pyo", ".DS_STORE"]
    exclude_files = ["db.cfg"]
    for source_dir, dest_dir in deep_copy_list:
        for source_file in os.listdir(source_dir):
            fname, fext = os.path.splitext(source_file)
            if not fext in exclude_patterns and not source_file in exclude_files:  # lint:ok
                powlib.check_copy_file(
                    os.path.join(source_dir, source_file),
                    os.path.join(appbase + "/" + dest_dir,source_file)
                )
            else:
                print " excluded:.EXCL", source_file
                continue

    #
    # copy the generator files
    #
    powlib.check_copy_file("scripts/generate_model.py", appbase)
    powlib.check_copy_file("scripts/do_migrate.py", appbase)
    powlib.check_copy_file("scripts/generate_controller.py", appbase)
    powlib.check_copy_file("scripts/generate_migration.py", appbase)
    powlib.check_copy_file("scripts/generate_scaffold.py", appbase)
    powlib.check_copy_file("scripts/simple_server.py", appbase)
    powlib.check_copy_file("scripts/pow_router.wsgi", appbase)
    powlib.check_copy_file("pow_console.py", appbase)
    powlib.check_copy_file("runtests.py", appbase)

    powlib.replace_string_in_file(
        os.path.join(appbase + "/" + "simple_server.py"),
        "#POWAPPNAME",
        appname
    )

    powlib.replace_string_in_file(
        os.path.join(appbase + "/" + "pow_router.wsgi"),
        "#POWAPPNAME",
        appname
    )

    #
    # copy the initial db's
    #
    appdb = "stubs/db/app_db_including_app_versions_small.db"
    app_db_path = appbase + "/db/" + appname
    powlib.check_copy_file(appdb, os.path.normpath(app_db_path + "_prod.db"))
    powlib.check_copy_file(appdb, os.path.normpath(app_db_path + "_test.db"))
    powlib.check_copy_file(appdb, os.path.normpath(app_db_path + "_devel.db"))
    #powlib.check_copy_file("stubs/db/empty_app.db", os.path.normpath(appbase + "/db/app.db") )  # lint:ok

    #
    # initiate the db.cfg file
    #
    render_db_config(appname, appbase)

    generate_model.render_model(
        "App",
        False,
        "System class containing the App Base Informations",
        appname)
    generate_model.render_model(
        "Version",
        False,
        "System class containing the Versions",
        appname)
    return


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = generate_controller
#!python
#  pow controller generator.
#
# options are: 
#   see: python generate_controller.py --help

import os
from optparse import OptionParser
import sqlite3
import sys
import string
import datetime
from sqlalchemy.orm import mapper
from sqlalchemy import *

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models/powmodels" )))
import powlib
import PowObject

# setting the right defaults
MODE_CREATE = 1
MODE_REMOVE = 0
PARTS_DIR = powlib.PARTS_DIR
CONTROLLER_TEST_DIR = "/tests/controllers/"


def main():
    """ 
        Executes the render methods to generate a conroller and basic 
        tests according to the given options
    """
    parser = OptionParser()
    mode= MODE_CREATE
    parser.add_option("-n", "--name",  action="store", type="string", 
                        dest="name", 
                        help="creates migration with name = <name>", 
                        default ="None")
    parser.add_option("-m", "--model",  
                        action="store", 
                        type="string", 
                        dest="model", 
                        help="defines the model for this migration.", 
                        default ="None")
    parser.add_option("-f", "--force",  
                        action="store_true",  
                        dest="force", 
                        help="forces overrides of existing files",
                        default=False)
    
    controller_name = "None"
    controller_model = "None"
    start = None
    end = None
    start = datetime.datetime.now()
    
    (options, args) = parser.parse_args()
    #print options        
    if options.model == "None":
        if len(args) > 0:
            # if no option flag (like -m) is given, it is assumed that 
            # the first argument is the model. (representing -m arg1)
            options.model = args[0]
        else:
            parser.error("You must at least specify an controllername by giving -n <name>.")
            
    controller_name = options.model
    render_controller(controller_name, options.force)

    end = datetime.datetime.now()
    duration = None
    duration = end - start 
    print "generated_controller in("+ str(duration) +")"
    print
    return
    
def render_controller( name="NO_NAME_GIVEN", force=False, prefix_path="./"):
    """ generates a controller according to the given options
        @param name: name prefix of the Controller fullname NameController
        @param force: if true: forces overwrtiting existing controllers"""
    
    print "generate_controller: ", name 
    # add the auto generated warning to the outputfile
    infile = open (os.path.normpath(PARTS_DIR + "controller_stub.part"), "r")
    ostr = infile.read()
    infile.close()
    
    #pluralname = powlib.plural(model)
    ostr = ostr.replace( "#DATE", str(datetime.date.today()) )  
    modelname = string.capitalize( name ) 
    ostr = ostr.replace("#MODELNAME", modelname)
    ostr = ostr.replace("#CONTROLLERNAME", modelname)
    classname = modelname + "Controller"
    filename = os.path.normpath ( 
        os.path.join( prefix_path + "./controllers/",  classname + ".py" ) )
    
    if os.path.isfile( os.path.normpath(filename) ):
        if not force:
            print " --", filename,
            print " already exists... (Not overwritten. Use -f to force ovewride)"
        else:
            ofile = open(  filename , "w+") 
            print  " -- created controller " + filename
            ofile.write( ostr )
            ofile.close()
    else:
        ofile = open(  filename , "w+") 
        print  " -- created controller " + filename
        ofile.write( ostr )
        ofile.close()
    #
    # check if BaseController exist and repair if necessary
    if not os.path.isfile(os.path.normpath( "./controllers/BaseController.py")):
        # copy the BaseClass
        powlib.check_copy_file(
            os.path.normpath( "./stubs/controllers/BaseController.py"), 
            os.path.normpath( "./controllers/") )
    
    render_test_stub( name, classname )
    return
    
    
def render_test_stub (controllername, classname, prefix_path ="./" ):
    """ renders the basic testcase for a PoW Controller """
    #print "rendering Testcase for:", classname, " ", " ", modelname
    print " -- generating TestCase...",
    infile = open( os.path.normpath( PARTS_DIR +  "test_controller_stub.part"), "r")
    instr = infile.read()
    infile.close()
    test_name = "Test" + classname + ".py"
    
    ofile = open( 
        os.path.normpath(
            os.path.join(prefix_path + CONTROLLER_TEST_DIR, test_name ) ), "w")
    
    instr = instr.replace("#CLASSNAME", "Test" + classname  )
    instr = instr.replace( "#DATE", str(datetime.date.today()) )  
    ofile.write(instr)
    
    ofile.close()
    print  " %s...(created)" % (prefix_path + CONTROLLER_TEST_DIR + test_name)
    return


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = generate_migration
#!python
#  pow migration generator.
#
# options are: 
#   see: python generate_migration.py --help


import os, datetime, time
from optparse import OptionParser
import sqlite3
import sys
import datetime
from sqlalchemy.orm import mapper
from sqlalchemy import *
import string

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models" )))

import powlib
import App

# setting the right defaults
MODE_CREATE = 1
MODE_REMOVE = 0
PARTS_DIR = powlib.PARTS_DIR

    
def main():
    """ Executes the render methods to generate a migration according to the given options """
    parser = OptionParser()
    mode= MODE_CREATE
    parser.add_option( "-m", "--model",  
                       action="store", 
                       type="string", 
                       dest="model", 
                       help="defines the model for this migration.", 
                       default ="None")
    parser.add_option( "-c", "--comment",  
                       action="store", 
                       type="string", 
                       dest="comment", 
                       help="defines a comment for this migration.", 
                       default ="No Comment")
    parser.add_option( "-j", "--job",  
                       action="store", 
                       type="string", 
                       dest="job", 
                       help="creates migration job, e.g for backups, restores etc.",
                       default="None")
    parser.add_option( "-d", "--column-definitions",  
                       action="store", 
                       type="string", dest="col_defs", 
                       help="column definitions.Form: d- 'NAME TYPE opt, NAME2 TYPE2 opt2' Name, type, options (all SQLAlchemy style).",
                       default="None")
    parser.add_option( "-t", "--table",  
                       action="store", 
                       type="string", 
                       dest="table", 
                       help="set table for migration_job",
                       default="None")
    #
    # column definition format: NAME TYPE opt1 opt2 optn, NAME2 TYPE2 opt1 opt2 optn ....
    # 
    
    start = None
    end = None 
    start = datetime.datetime.now()

    (options, args) = parser.parse_args()
    #print options
    #TODO: reorg and optimize the section below. more structure.
    #
    if options.model == "None" and options.job == "None":
        # no model- or job flag given
        if len(args) == 0:
            parser.error("You must at least specify an migration name by giving -n <name>.")
            return
            # if no option flag (like -m) is given, it is assumed 
            #that the first argument is the model. (representing -m arg1)
        else:
            options.model = args[0]
            
    if options.model.startswith("rel_") and ( options.model.count("_") == 2 ):
        # if the name is of the form: rel_name1_name2 it is assumed that you want to
        # generate a relation between name1 and name2. So the mig is especially customized for that.
        print "assuming you want to create a relation migration..."
        
        render_relation_migration(options.model)
        end = datetime.datetime.now()
        duration = None
        duration = end - start 

        print "generated_migration in("+ str(duration) +")"
        return        
            
    else:
        # we got a model or job.
        if options.job != "None":
            render_migration_job(options.job, options.table)
        else:
            render_migration(options.model,options.comment, options.col_defs)
    
    end = datetime.datetime.now()
    duration = None
    duration = end - start 
    
    print "generated_migration in("+ str(duration) +")"
    print
    return

def transform_col_defs( ostr, col_defs ):
    """
        Get the list of given column definitions of the form:
        
            NAME TYPE opt1 opt2 optn, NAME2 TYPE2 opt1 opt2 optn ....
        And transform them to a valid SQLAlchemy Column definition for a migration.
        Form:
            Column('firstname', String(150), Options)
        
    """
    
    cols = ""
    clist = str(col_defs).split(",")
    print clist
    counter = 0
    for elem in clist:
        counter += 1
        elem = elem.strip()
        elem = elem.split(" ")
        if len(elem) == 2:
            cols += "Column('%s', %s)" % (elem[0], elem[1]) 
        elif len(elem) == 3:
            cols += "Column('%s', %s, %s)" % (elem[0], elem[1], elem[2])
        else:
            print "Error. Wrong number of arguments. You must give name, type (and optionally column options)"
        if counter < len(clist):
            cols += "," + os.linesep + powlib.tab*3

    ostr = ostr.replace("Column('example_column', String(50))", cols)
    
    return ostr


def render_relation_migration(name, PARTS_DIR = powlib.PARTS_DIR, prefix_dir = "./"):
    """
    renders a migration for a relational link between tables / models
    Typical examples are A.has_many(B) and B.belongs_to(A)
    these are then added to the newly genrated migration file.
    
    @params name    =>  name of the migration. Must be rel_modelA_modelB
    @param PARTS_DIR:   A relative path to the stubs/partials dir from the executing script.
    @param prefix_dir:  A prefix path to be added to migrations making prefix_dir/migrations the target dir
    """

    splittxt = string.split(name, "_")
    model1 = splittxt[1]
    model2 = splittxt[2]
    
    print " -- generate_migration: relation migration for models: " + model1 +  " & " + model2
    print " -- following the naming convention rel_model1_model2"
    print " -- you gave:", name
    
    # add the auto generated (but can be safely edited) warning to the outputfile
    infile = open (os.path.normpath(PARTS_DIR + "/db_relation_migration_stub.part"), "r")
    ostr = infile.read()
    infile.close()
    
    # add a creation date
    ostr = ostr.replace( "#DATE", str(datetime.date.today() ))
    # add model1 import
    ostr = ostr.replace( "#IMPORT_MODEL1", "import " + model1)
    # add model2 import
    ostr = ostr.replace( "#IMPORT_MODEL2", "import " + model2)
    
    # add the example migration for this models
    ostr = ostr.replace( "#MODEL1", model1)
    ostr = ostr.replace( "#MODEL2_has_many", powlib.pluralize(model2))
    ostr = ostr.replace( "#MODEL2", model2)
    
    filename = write_migration( name, 
                                "relation between %s and %s" % (model1, model2),
                                prefix_dir,
                                ostr
                                )
    print  " -- created file:" + str(os.path.normpath(os.path.join(prefix_dir,filename)))
    return
    

def write_migration(name, comment, prefix_dir="./", ostr=""):
    """
    Writes a new migration.
    It generates a new version, constructs the correct filename and path
    Updates the App and Version tables and writes ostr to the new filen.
    @param name:    Name of the new migration. 
    @param ostr:    Content that will be written to the new migration.
    """
    version = get_new_version()
    print "version: %s" % (version)
    verstring = powlib.version_to_string(version)
    # will be saved in the versions table and used to load the module by do_migrate
    modulename = verstring +"_" + name 
    filename = modulename + ".py"
    
    #update the app table with the new version
    update_app_and_version(version, modulename, version, comment )
    
    ofile = open(  os.path.normpath(os.path.join(prefix_dir + "/migrations/", filename)) , "w+") 
    ofile.write(ostr)
    ofile.close()
    print "written %s " % (filename)
    return filename
    
def get_new_version():
    """
    Constructs the new version by queriing the App Table for maxversion
    """
    app = powlib.load_class( "App", "App")
    
    sess = app.pbo.getSession()
    app = sess.query(App.App).first()
    
    version = app.maxversion
    version += 1
    return version
    
def update_app_and_version(maxversion, filename, version, comment=""):
    """
    update the app table with the new version
    update the version table with:
        filename, version and comment (if any).
    """
    app = powlib.load_class( "App", "App")
    app_versions = powlib.load_class( "Version", "Version")
    app = app.find_first()
    app.maxversion = str(maxversion)
    app.update()
    app_versions.filename = str(filename)
    app_versions.version = str(version)
    app_versions.comment = str(comment)
    app_versions.update()
    return 
    
def render_migration( modelname="NO_MODEL_GIVEN", comment="", col_defs = "", PARTS_DIR = powlib.PARTS_DIR, prefix_dir = "./"):
    """
    Renders a database migration file.
    @param model:       Modelname for this migration (typically defining the model's base table)
    @param comment:     a Comment for this migration
    @param col_defs:    pre defined column definitions of the form NAME TYPE OPTIONS, NAME1 TYPE1 OPTIONS1, ...
    @param PARTS_DIR:   A relative path to the stubs/partials dir from the executing script.
    @param prefix_dir:  A prefix path to be added to migrations making prefix_dir/migrations the target dir
    """
    
    # add the auto generated (but can be safely edited) warning to the outputfile
    infile = open (os.path.normpath(PARTS_DIR + "/db_migration_stub.part"), "r")
    ostr = infile.read()
    infile.close()

    # Replace the TAGGED Placeholders with the actual values
    ostr = ostr.replace( "#DATE", str(datetime.date.today() ))
    pluralname = powlib.plural(modelname)
    ostr = ostr.replace("#TABLENAME", pluralname)
    
    #
    # Add / Replace the column definitions with the given ones by -d (if there were any)
    # 
    if col_defs != "None":
        ostr = transform_col_defs( ostr, col_defs )

    # generate the new version
    #version = get_new_version()
    #verstring = powlib.version_to_string(version)

    print "generate_migration for model: " + modelname

    # really write the migration now
    write_migration(modelname, comment, prefix_dir, ostr)

    return


def render_migration_job(filename, tablename):
        """create a 'job' or task that has to be done on the database.
        typical examples are backup/restore scripts for dbs or tables or loading data into a table.
        These migrations are not part of the migration versioning system.
        They can be executed with python migrate.py -f <migrationname>
        You can set the table by adding the -t <tablename> option
        """
        print " -- creating migration job:"
        infile = open(os.path.normpath( PARTS_DIR + "migration_job.part"), "r")
        instr = infile.read()
        infile.close()
        instr = instr.replace("#JOBNAME", filename+ "_migration.py")
        if tablename != "None":
            instr = instr.replace("#TABLENAME", tablename)
        ofile = open(os.path.normpath( "./migrations/" + filename + "_migration.py"), "w")
        ofile.write(instr)
        ofile.close()
        #powlib.check_copy_file(os.path.normpath( PARTS_DIR + "migration_job.part"), "./migrations/" + filename + "_migration.py")
        return
        

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = generate_model
#!python
#  pow model generator.
#
# options are: 
#    see python generate_model.py --help

from optparse import OptionParser
import sqlite3, sys, os, datetime
import string

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models/powmodels" )))
import powlib


# setting the right defaults
MODE_CREATE = 1
MODE_REMOVE = 0
PARTS_DIR = powlib.PARTS_DIR
MODEL_TEST_DIR = "/tests/models/" 
pow_newline = powlib.linesep
pow_tab= powlib.tab

def main():
    """ Executes the render methods to generate a model, 
    basemodel and basic tests according to the given options """
    
    parser = OptionParser()
    mode= MODE_CREATE
    parser.add_option( "-n", "--name",  
                       action="store", 
                       type="string", 
                       dest="name", 
                       help="creates model named model-name", 
                       default ="None")
    parser.add_option( "-a", "--attributes",  
                       action="store",
                       type="string",
                       dest="actions",
                       help="defines the attributes included in the model.",
                       default ="None")
    parser.add_option( "-f", "--force",
                       action="store_true",
                       dest="force",
                       help="forces overrides of existing files",
                       default="False")
    parser.add_option( "-c", "--comment",
                       action="store",
                       type="string",
                       dest="comment",
                       help="defines a comment for this model.",
                       default ="No Comment")
    parser.add_option( "-p", "--path",
                       action="store",
                       type="string",
                       dest="path",
                       help="sets the model output psth.",
                       default ="./")
    
    (options, args) = parser.parse_args()
    #print options
    if options.name == "None":
       if len(args) > 0:
           # if no option flag (like -n) is given, it is assumed that the 
           # first argument is the model name. (representing -n arg1)
           options.name = args[0]
       else:
           parser.error("You must at least specify an appname by giving -n <name>.")

    #model_dir = os.path.normpath("./models/")
    model_dir = os.path.normpath(options.path)
    modelname = options.name
    start = None
    end = None
    start = datetime.datetime.now()
    
    render_model(modelname, options.force, options.comment, model_dir)
    
    end = datetime.datetime.now()
    duration = None
    duration = end - start 
    print "generated_model in("+ str(duration) +")"
    print ""
    return

    
def render_model(modelname = "NO_MODELNAME_GIVEN", 
                 force = False, 
                 comment="", 
                 prefix_path="./", 
                 properties=None, 
                 parts_dir= powlib.PARTS_DIR ):
    """
    Renders the generated Model Class in prefix_path/models.
    Renders the according BaseModel in prefix_path/models/basemodels.
    Renders a basic test in tests dierctory.
    Uses the stubs from stubs/partials.
    """
    print "generate_model: " + modelname
    # new model filename
    classname = string.capitalize(modelname)  
    baseclassname = "Base" + classname
    filename = classname + ".py"
    filename = os.path.normpath( prefix_path+ "/models/" + filename)
    if os.path.isfile( os.path.normpath( filename ) ) and force != True:
        print filename + " (exists)...(Use -f to force override)"
    else:
        infile = None
        infile = open (os.path.normpath( parts_dir +  "model_stub.part"), "r")
        ostr = ""
        ostr = ostr + infile.read()
        infile.close()
        
        ostr = ostr.replace("#DATE", str(datetime.date.today()) )
        ostr = ostr.replace("#MODELCLASS", classname)
        
        ostr = ostr.replace("#BASECLASS", baseclassname)
        ostr = ostr.replace( "#MODELTABLE",  powlib.plural(string.lower(modelname))  ) 
        
        # write the output file to disk
        ofile = open( filename , "w+") 
        print " --", filename + " (created)"
        ofile.write( ostr )
        ofile.close()
    
    ### generate BaseModel if neccessary
    filename = "Base" + classname + ".py"
    if os.path.isfile( os.path.normpath( filename ) ) and force != True:
        print filename + " (exists)...(Use -f to force override)"
    else:
        infile = None
        ### generate the BaseClass
        infile = open (os.path.normpath( PARTS_DIR +  "basemodel_stub.part"), "r")
        ostr = infile.read()
        infile.close()
        # Add Class declaration and Table relation for sqlalchemy
        ostr = ostr.replace( "#BASECLASSNAME",  baseclassname )
        ostr = ostr.replace( "#MODELTABLE",  powlib.plural(string.lower(modelname))  ) 
         
        ### adding the properties list
        # TODO: Needs to be tested. 
        if properties == None:
            ostr = ostr.replace("#PROPERTIES_LIST",  "[]")
        else:
            ostr = ostr.replace("#PROPERTIES_LIST",  properties )
            
        ostr = ostr.replace("#MODELNAME" , string.capitalize(modelname) )        
            
        filename = os.path.normpath( prefix_path + "/models/basemodels/" + filename)
    
        ofile = open(  filename , "w+") 
        print  " --", filename + " (created)"
        ofile.write( ostr )
        ofile.close()
        
    # render a basic testcase 
    render_test_stub(modelname, classname, prefix_path, PARTS_DIR)
    return 

def reset_model(modelname):
    """ overwrites the generated Model, BaseModel and 
    Test with empty / newly generated versions."""
    
    return render_model(modelname, True, "", properties=None, nomig=True)
    
def render_test_stub (modelname, classname, prefix_path = "", PARTS_DIR = powlib.PARTS_DIR ):
    """ renders the basic testcase for a PoW Model """
    #print "rendering Testcase for:", classname, " ", " ", modelname
    print " -- generating TestCase...",
    infile = open( os.path.normpath( PARTS_DIR +  "test_model_stub.part"), "r")
    test_name = "Test" + classname + ".py"
    ofile = open( os.path.normpath(prefix_path + MODEL_TEST_DIR + test_name ), "w")
    instr = infile.read()
    instr = instr.replace("#CLASSNAME", "Test" +  classname )
    ofile.write(instr)
    infile.close()
    ofile.close()
    print  " %s...(created)" % (prefix_path + MODEL_TEST_DIR + test_name)
    
    return


    
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = generate_mvc

#!python
#  pow migration generator.
#
# options are:
#   see: python generate_migration.py --help


import os
import datetime
import time
from optparse import OptionParser
import sys
import string

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(__file__), "./lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(__file__), "./models" )))

import powlib
import generate_migration
import generate_model
import generate_scaffold
import generate_controller
import powlib

# setting the right defaults
MODE_CREATE = 1
MODE_REMOVE = 0
PARTS_DIR = powlib.PARTS_DIR


def main():
    """ Executes the render methods to generate a model, controller,
    migration and the views according to the given options """
    parser = OptionParser()
    mode= MODE_CREATE
    parser.add_option("-m", "--model",
                      action="store",
                      type="string",
                      dest="model",
                      help="defines the model for this migration.",
                      default ="None")

    parser.add_option("-c", "--comment",
                      action="store",
                      type="string",
                      dest="comment",
                      help="defines a comment for this migration.",
                      default ="No Comment")

    parser.add_option("-d", "--column-definitions",
                      action="store",
                      type="string", dest="col_defs",
                      help="""column definitions.Form: d- 'NAME TYPE opt, NAME2 TYPE2 opt2'
                              Name, type, options (all SQLAlchemy style).""",
                      default="None")

    parser.add_option("-f", "--force",
                        action="store_true",
                        dest="force",
                        help="forces overrides of existing files",
                        default=False)
    #
    # column definition format: NAME TYPE opt1 opt2 optn, NAME2 TYPE2 opt1 opt2 optn
    #
    start = datetime.datetime.now()


    (options, args) = parser.parse_args()

    #if no model given and no parameter at all, then quit with error
    if options.model == "None" and len(args) < 1:
        parser.error("You must at least specify an migration name by giving -n <name>.")
        return
    else:
        # if no model given but a parameter, than assume that the first parameter
        # is the model
        if options.model == "None":
            options.model = args[0]

        print "generate_mvc for model:", options.model
        # generate the model
        generate_model.render_model(modelname = options.model,
                                    force = options.force,
                                    comment = options.comment
                                    )
        print
        # generate the Controller
        generate_controller.render_controller( name = options.model,
                                               force = options.force
                                              )

        print
        # generate the views
        generate_scaffold.scaffold(modelname = options.model,
                                   force = options.force,
                                   actions = ["list", "show","create", "edit", "message"]
                                   )

        print
        # generate the migration
        # ooptions_col_defs has to be a comma separated list of column names and SQLAlchemy DB types:
        # example: lastname String(100), email String(100)
        col_defs = options.col_defs

        generate_migration.render_migration( modelname = options.model,
                                             comment = options.comment,
                                             col_defs = options.col_defs
                                             )
        print


    end = datetime.datetime.now()
    duration = end - start
    print "generated_mvc in("+ str(duration) +")"
    print
    return

if __name__ == "__main__":
    main()
    sys.exit(0)

########NEW FILE########
__FILENAME__ = generate_scaffold
#!python
#  pow scaffold generator.
#
#  options are: 
#    no option or -create         means create
#    -remove             removes 

import email
import string
import os
from optparse import OptionParser
import sqlite3
import sys
import datetime
from sqlalchemy.orm import mapper
from sqlalchemy import *


sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models/powmodels" )))
import powlib


# setting the right defaults
MODE_CREATE = 1
MODE_REMOVE = 0
PARTS_DIR = powlib.PARTS_DIR

def main():
    """ Executes the render methods to generate scaffold views for a model 
    according to the given options """
    
    parser = OptionParser()
    mode = MODE_CREATE    
    parser.add_option(  "-m", "--model",  
                        action="store", 
                        type="string", 
                        dest="model", 
                        help="defines the model for this migration.", 
                        default ="None")
    parser.add_option(  "-f", "--force",  
                        action="store_true",  
                        dest="force", 
                        help="forces overrides of existing files",
                        default=False)
    parser.add_option(  "-t", "--template",  
                        action="store",  
                        type="string",    
                        dest="template", 
                        help="forces a special mako template for these views",
                        default="/${context.get('template')}")

    start = None
    end = None
    start = datetime.datetime.now()
    
    (options, args) = parser.parse_args()
    print options
    if options.model == "None":
        if len(args) > 0:
            # if no option flag (like -n) is given, it is 
            # assumed that the first argument is the model name. (representing -n arg1)
            options.model = args[0]
        else:
            parser.error("You must at least specify an appname by giving -n <name>.")
    
    scaffold(options.model, options.force, options.template)
    end = datetime.datetime.now()
    duration = None
    duration = end - start 
    print "generated_scaffold in("+ str(duration) +")"
    print
    return
    
def scaffold(   modelname="NO_MODELNAME_GIVEN", 
                force=False,
                template = "/${context.get('template')}",
                actions = ["list", "show","create", "edit", "message"], 
                PARTS_DIR = powlib.PARTS_DIR, 
                prefix_dir = "./" ):
    """
        Generates the scaffold view for a given model.
        @param modelname:  the name of the model for which the views are scaffolded
        @param force:      if set, existing files will be overwritten (default=False)
        @param actions:    list of actions for which the views will be scaffoded
        @param PARTS_DIR:  relative path of the stubs/partial directory. (default=stubs/partials)
        @param prefix_dir: prefix_path for the generated views. /(default=./ which results in ./views) 
    """
     
    print "generate_scaffold for model: " + str(modelname)
    
    for act in actions:
       
        # Add the _stub part0 content to the newly generated file. 
        infile = open (os.path.normpath( PARTS_DIR +  "scaffold_stub_part0.tmpl"), "r")
        ostr = infile.read()
        infile.close() 
        
        # add a creation date
        ostr = ostr.replace("#DATE", str(datetime.date.today()) )    
        
        #set the template
        ostr = ostr.replace("#TEMPLATE", template )  
       
        
        # Add the _stub part1 content to the newly generated file. 
        infile = open (os.path.normpath( PARTS_DIR +  "scaffold_" + act +"_stub_part1.tmpl"), "r")
        ostr = ostr + infile.read()
        infile.close()
        filename = string.capitalize(modelname)  + "_" + act +".tmpl"
        filename = os.path.normpath( 
                            os.path.join(prefix_dir + "/views/", filename) ) 
                                    
        #TODO: optimize the double else part .
        if os.path.isfile( os.path.normpath(filename) ):
            if not force:
                print filename + " already exists..."
            else:
                ofile = open(  filename , "w+") 
                print  " -- created scaffold " + filename
                ofile.write( ostr )
                ofile.close()
        else:
            ofile = open(  filename , "w+") 
            print  " -- created scaffold " + filename
            ofile.write( ostr )
            ofile.close()
            
    return
    

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = md_test
#
# what:     a short markdown to html test for PoW
# web:      www.pythononwheels.org
# email:    khz@pythononwheels.org
# who:      11to1.org sparetime development from 11pm to 1am ;)
#
#
import markdown

if __name__ == "__main__":
    infile = open("github.md", "r")
    text = infile.read()
    infile.close()
    html = markdown.markdown(text)
    of = open("github.html","w")
    of.write(html)
    of.close()
    
########NEW FILE########
__FILENAME__ = pow_console
#!python
## Thx to:
##  http://code.activestate.com/recipes/355319/ (r1)
## eased my life. Console and the  recipe above ;)
import code
import sys,os, string, pdb
try:
    import pyreadline as readline
except ImportError:
    try:
        import readline
    except ImportError:
        print "pow_console needs readline or pyreadline. Please install readline(linux) or pyreadline(wivdows) via"
        print "pip install (py)readline."

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))

class FileCacher:
    "Cache the stdout text so we can analyze it before returning it"
    def __init__(self): self.reset()
    def reset(self): self.out = []
    def write(self,line): self.out.append(line)
    def flush(self):
        output = '\n'.join(self.out)
        self.reset()
        return output

class Shell(code.InteractiveConsole):
    "Wrapper around Python that can filter input/output to the shell"
    def __init__(self):
        self.stdout = sys.stdout
        self.cache = FileCacher()
        code.InteractiveConsole.__init__(self)
        # importing the pow modules as well as 
        # current Models, Controllers for this project
        importdirs = ["models/basemodels", "models", "controllers" ]
        include_ext_list = [".py"]
        for adir in importdirs:
            sys.path.append(os.path.abspath(adir))
            
        for path in importdirs:
            importlist = []
            for elem in os.listdir(os.path.normpath(path)):
                fname, fext = os.path.splitext(elem)
                if fext in include_ext_list and not fname.startswith("__"):
                    statement = "from "+ str(fname)+ " import " + str(fname)
                    print "executing statement: ", statement
                    #exec statement
                    self.push(statement)
        return
    
    def get_output(self): sys.stdout = self.cache
    def return_output(self): sys.stdout = self.stdout

    def push(self,line):
        self.get_output()
        # you can filter input here by doing something like
        #print "hey, this is the input: ", line
        # line = filter(line)
        newline = line
        code.InteractiveConsole.push(self,newline)
        self.return_output()
        output = self.cache.flush()
        # you can filter the output here by doing something like
        # output = filter(output)
        if output != "":
            print output # or do something else with it
        return 

if __name__ == '__main__':
    sh = Shell()
    
    pow_banner = "pow console v0.1 " + os.linesep
    pow_banner += "Using python " + str(sys.version)[:6] + os.linesep
    pow_banner += "type help to get more info and help on special pow_console commands"
     
    sh.interact(pow_banner)
## end of http://code.activestate.com/recipes/355319/ }}}

########NEW FILE########
__FILENAME__ = runtests
#!python
#
# Runs the generated Tests.
# All fail by defualt. You need to implement them
# to make them pass.
#
#

import nose
import sys
import os
import os.path


def runmodels():
    print " -- running model tests"
    testdir = os.path.normpath('./tests/models/')
    configfile = os.path.join(os.path.normpath('./config/'), "nose.cfg")
    argv = [configfile, testdir]
    nose.run(argv=argv)
    return

def runcontrollers():
    print " -- running controller tests"
    testdir = os.path.normpath('./tests/controllers/')
    configfile = os.path.join(os.path.normpath('./config/'), "nose.cfg")
    argv = [configfile, testdir]
    nose.run(argv=argv)
    return

def runall():
    runmodels()
    runcontrollers()
    testdir = os.path.normpath('./tests/others/')
    configfile = os.path.join(os.path.normpath('./config/'), "nose.cfg")
    argv = [configfile, testdir]
    nose.run(argv=argv)
    return

if __name__ == "__main__":
    #print len(sys.argv), "  ", sys.argv
    if len(sys.argv) == 1 or sys.argv[1] == "all":
        print " -- running all tests"
        runall()
    elif sys.argv[1] == "models":
        runmodels()
    elif sys.argv[1] == "controllers":
        runcontrollers()
    else:
        print "Usage: runtests < all OR models OR controllers >"
        sys.exit(0)
    sys.exit(0)

########NEW FILE########
__FILENAME__ = simple_server
#!python
#
# simple_server is a simple wsgi server for testing purposes only.
# Gives you the opportunity to develop on your local machine 
# without any complex Webserver / module configuration at first.
#
# DO NOT USE THIS for production. !!!!
# 


from wsgiref.simple_server import make_server
import logging
import string
import os.path
import sys
import os
import re
from pprint import pformat
from beaker.middleware import SessionMiddleware
#from cgi import parse_qs, escape
import cgi

import traceback, StringIO
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./config" )))
import urllib
import pow
import powlib
from powlib import _log
import pow_web_lib
from webob import Request, Response


def powapp_simple_server(environ, start_response):
    
    #print show_environ_cli(environ)
    output = []
    powdict =  {}    
    real_action = None
    
    req = Request(environ)
    req.charset = pow.global_conf["DEFAULT_ENCODING"]
    #print "webob: req.params", req.params
    #print "webob: req.body", req.body
    
    
    #print dir(req.params)
    #
    # relevant parameters have to be defined here
    # (Same as for apache the declarations in the httpd.conf file
    #
    # redirect static media from the meta link static to the real source dir
    # advantage is: you can alway refer safely to /static/<something> inside your css o .tmpl
    # files and the real source can be anywhere. sometimes the real static source differs from
    # prod-webserver A to prod-webserver B. with this litte tirck you can leave your links unchanged.
    # for apache the redirection is done in http.conf
    alias_dict ={    
        "/static/css/"             :    "./public/css/",
        "/static/stylesheets/"     :    "./public/css/",
        "/static/scripts/"         :     "./public/js/",
        "/static/js/"               :     "./public/js/",
        "/static/documents/"     :     "./public/doc/",
        "/static/doc/"           :     "./public/doc/",
        "/static/ico/"           :     "./public/ico/",
        "/static/img/"           :     "./public/img/"
        
        }
    environ["SCRIPT_FILENAME"] = __file__
    powdict["POW_APP_NAME"] = "atest"
    powdict["POW_APP_URL"] = "www.pythononwheels.org"
    powdict["POW_APP_DIR"] = environ.get("pow.wsgi_dir")
    powdict["ERROR_INFO"] = "NONE"
    
    # Get the session object from the environ
    session = environ['beaker.session']
    #TO_DO: set the right status in the end, according to the situatio instead of setting it hard-coded here
    status = '200 OK'
    response_headers = [
        #('Content-type', 'text/html; charset=utf-8')
        ('Content-type', 'text/html')
        ]

    
    if not session.has_key('user.id'):
        session['user.id'] = 0
    
    #session.save()
    
    powdict["SESSION"] = session
    #print "-- request info:"
    #print "-- webob: req.content_type: ", req.content_type
    if pow.logging["LOG_LEVEL"] == "DEBUG":
        print "-- webob: ", req.method
    
    powdict["REQ_CONTENT_TYPE"] = req.content_type
    powdict["REQ_PARAMETERS"] = req.params
    powdict["REQ_BODY"] = req.body
    
    
      
    plist = req.params
    
    #if plist.has_key("image"):
    #    print "Image found: ", plist['image'].filename
    #    ofile = file(plist['image'].filename, "wb")
    #    infile = plist['image'].file
    #    ofile.write( infile.read() )
    #   #ofile.write( plist["image"].value )
    #    ofile.close()
    #
    # handling static files
    #
    pinfo = environ.get("PATH_INFO")
    pinfo_before = pinfo
    ostr = ""
    #
    # check for static links and replace them when found.
    #
    found_static = False
    for elem in alias_dict:
        if string.find(pinfo,  elem) != -1:
            found_static = True
            pinfo = string.replace(pinfo,elem, alias_dict[elem])
    
    environ["PATH_INFO"] = pinfo
    
    if found_static == True:
        non_binary = [".css", ".html",".js",".tmpl"]
        ctype = "UNINITIALIZED"
        ftype = os.path.splitext(pinfo)[1]
        
        if string.lower(ftype) in non_binary:
            infile = open (os.path.normpath(pinfo), "r")
        else:
            infile = open (os.path.normpath(pinfo), "rb")
        ostr = infile.read()
        infile.close()
        #print "file type is: ", ftype, " -> ", ctype
        if string.lower(ftype) == ".gif":
            ctype = "image/gif"
        elif string.lower(ftype) == ".jpg" or string.lower(ftype) ==".jpeg":
            ctype= "image/jpeg"
        elif string.lower(ftype) == ".css":
            ctype = "text/css"
        elif string.lower(ftype) == ".png":
            ctype = "image/png"
        elif string.lower(ftype) ==".js":
            ctype= "application/x-javascript"
        else:
            ctype = "text/html"
        #_log( "file type is: %s responding with type-> %s , %s" %(ftype,ctype,pinfo), "DEBUG") 
        response_headers = [
            ('Content-type', ctype )
        ]
        start_response(status, response_headers)
        return [ostr]
        
    _log( "-- Dynamic REQUEST --------------------------------------------------------- ", "INFO")
    _log( "Parameters = %s " % (powdict["REQ_PARAMETERS"]), "DEBUG")
    _log( "Request: %s " % (environ["REQUEST_METHOD"]) , "DEBUG" ) 
    _log( "Query String: %s" % ( environ["QUERY_STRING"]) , "DEBUG" ) 
    _log( "PATH_INFO before: %s " % (pinfo_before), "DEBUG")
    _log( "PATH_INFO after: %s " % (pinfo) , "DEBUG" )
        
    if not session.has_key('counter'):
        session['counter'] = 0
    else:
        session['counter'] += 1

    powdict["SCRIPT_FILENAME"] = environ.get("SCRIPT_FILENAME")
    powdict["SCRIPT_DIR"] = os.path.dirname(environ.get("SCRIPT_FILENAME"))
    powdict["SCRIPT_VIEWS_DIR"] = os.path.abspath(os.path.join(os.path.dirname(environ.get("SCRIPT_FILENAME")) + "/views/"))
    # PATH_INFO contains the path beginning from the app-root url.     # first part is the controller,      # second part is the action
    powdict["PATH_INFO"] = environ.get("PATH_INFO")
    #print os.path.split(powdict["PATH_INFO"])
    powdict["ENVIRON"] = pow_web_lib.show_environ( environ )
    powdict["DOCUMENT_ROOT"] = environ.get("DOCUMENT_ROOT")
    powdict["FLASHTEXT"] = ""
    powdict["FLASHTYPE"] ="error"
    #output.append( show_environ( output, environ ) )
    
    #
    # get controller and action
    #
    
    pathdict = pow_web_lib.get_controller_and_action(environ["PATH_INFO"])
    #(controller,action) = os.path.split(pathinfo)
    _log ("(controller,action) -> %s" % (pathdict), "INFO" )
    controller = powdict["CONTROLLER"] = pathdict["controller"]
    action = powdict["ACTION"] = pathdict["action"]
    powdict["PATHDICT"]=pathdict

    #TO_DO: include the real, mod re based routing instead of seting it hard to user/list here.
    if controller == "":
        defroute = pow.routes["default"]
        #defroute = powlib.readconfig("pow.cfg","routes","default")
        _log("pow_web_lib.get_controller_and_action: %s" %(pow_web_lib.get_controller_and_action(defroute)), "INFO")
        pathdict = pow_web_lib.get_controller_and_action(defroute)
        #(controller,action) = os.path.split(pathinfo)
        _log ("(controller,action) -> %s" % (pathdict), "INFO" )
        controller = powdict["CONTROLLER"] = pathdict["controller"]
        action = powdict["ACTION"] = pathdict["action"]
        powdict["PATHDICT"]=pathdict

        _log( "Using the DEFAULT_ROUTE: ", "INFO" )
        _log ("(controller,action) -> %s" % (pathdict), "INFO" )
    # get rid of the first / in front of the controller. string[1:] returns the string from char1 to len(string)
    controller = string.capitalize(controller) + "Controller"
    
    #
    # route the request
    #
    #print "Loading Class:", controller
    aclass = powlib.load_class(controller,controller)
    #print "setting Action: ", action
    aclass.setCurrentAction(action)
    #output.append(action + "<br>")
    # checking if action is locked 
    if aclass.is_locked(action):
        # locked, so set the action to the given redirection and execute that instead.
        # TODO: Could be aditionally coupled with a flashtext.
        _log( "Action: %s is locked." % (action), "INFO")
        cont, action = aclass.get_redirection_if_locked(action)
        if  cont != None and cont != "None" and cont != "":
            controller = string.capitalize(cont) + "Controller"
            aclass = powlib.load_class(controller,controller)
        aclass.setCurrentAction(action)
        _log( " -- Redirecting to: %s" % (action), "INFO")
    #
    # Now really execute the action
    #
    if hasattr( aclass, action ):
        real_action = eval("aclass." + action)  
        output.append(real_action(powdict).encode(pow.global_conf["DEFAULT_ENCODING"]))
    else:
        msg = "ERROR: No such class or action  %s.%s " % (controller, action)  
        output.append(msg)
    #
    # error handling wsgi see: http://www.python.org/dev/peps/pep-0333/#error-handling
    #
    start_response(status, response_headers)
    return output
        
session_opts = {
    'session.type': 'file',
    'session.data_dir': './session_data',
    'session.cookie_expires': True,
    'session.auto': True
}

#application= SessionMiddleware(powapp, key='mysession', secret='randomsecret')
#application = SessionMiddleware(powapp, session_opts)
 

if __name__ == "__main__":
    #
    # setup logging
    #
    
    logging.basicConfig( format=pow.logging["FORMAT"],
                         filename=pow.logging["LOGFILE"], 
                         filemode=pow.logging["LOGFILE_MODE"], 
                         level=getattr( logging, pow.logging["LOG_LEVEL"]) )
        
    application = pow_web_lib.Middleware(SessionMiddleware(powapp_simple_server, session_opts))
    port = pow.global_conf["PORT"]
    httpd = make_server('', int(port), application )
    print "Serving HTTP on port %s..." % (port)
    
    # Respond to requests until process is killed
    httpd.serve_forever()

    # Alternative: serve one request, then exit
    #httpd.handle_request()

########NEW FILE########
__FILENAME__ = 100posts
# -*- coding: utf-8 -*-
#
# create 100 Post entries
#

import sys, string

sys.path.append("../models/")

import Post

if __name__=="__main__":
    p = Post.Post()
    for elem in range(1,10):
        p.title = u"This is new post number %s" % (str(elem))
        p.content = u"""
        Das Blog [blɔg] (auch: der Blog) oder auch Web-Log [ˈwɛb.lɔg], engl. [ˈwɛblɒg], 
        Wortkreuzung aus engl. World Wide Web und Log für Logbuch, ist ein auf einer Website 
        geführtes und damit – meist öffentlich – einsehbares Tagebuch oder Journal, in 
        dem mindestens eine Person, der Web-Logger, kurz Blogger, Aufzeichnungen führt, 
        Sachverhalte protokolliert oder Gedanken niederschreibt.

        Häufig ist ein Blog „endlos“, d. h. eine lange, abwärts chronologisch sortierte 
        Liste von Einträgen, die in bestimmten Abständen umbrochen wird. 
        Der Herausgeber oder Blogger steht, anders als etwa bei Netzzeitungen, als 
        wesentlicher Autor über dem Inhalt, und häufig sind die Beiträge aus der 
        Ich-Perspektive geschrieben. Das Blog bildet ein für Autor und Leser einfach 
        zu handhabendes Medium zur Darstellung von Aspekten des eigenen Lebens und von 
        Meinungen zu spezifischen Themen. Meist sind aber auch 
        Kommentare oder Diskussionen der Leser über einen Artikel zulässig
        """
        p.content = p.content.replace("\n","<br>")
        p.create()
        print " -- created post number: ", str(elem)
########NEW FILE########
__FILENAME__ = AppTest
#
# testscript for class App.App
#

import App
x = App.App()
sess = x.pao.getSession()

app = sess.query(App.App).filter_by(name='manuell').first()
#
# print the result
#
print app
print "name: " + app.name
print "path: " + app.path
print "currentversion: " + str(app.currentversion)
print "migrationversion: " + str(app.migrationversion)

#
# add a new user
#
a = App.App()
a.name = "test"
a.path = "test"
a.currentversion = 99
a.migrationversion = 99

sess.add(a)
sess.commit()






########NEW FILE########
__FILENAME__ = AppController
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 

# date created:     2011-06-21

import sys
import os


sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../../stubs/lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../../stubs/models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../../stubs/models/powmodels" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../../stubs/controllers" )) )

import powlib
from powlib import mixin, uc
from BaseController import BaseController
import datetime

from auth import AuthController 


class AppController(object):
    
    def __init__(self):
        # it is needed to set a Modelname before calling the BaseControllers init
        #self.modelname = "App"
        #BaseController.__init__(self)
        
        #AuthController.login_required = { "welcome" : "admin" }
        self.login_required = { "welcome" : "admin" }
        # example of locked actions and the redirections.
        self.locked_actions = {}
        AuthController.protect(self)
    
    def ajax( self, powdict ):
        print "AJAX-Request"
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S")
        ret_str = uc("""<div class="alert alert-success">
                <button type="button" class="close" data-dismiss="alert">&times;</button>
                <strong>Yeah! AJAX with python rocks totally now:</strong>&nbsp %s &nbsp; %s 
              </div>""" % (now, powdict["REQ_BODY"] ))
        
        
        return ret_str 
        
    
    def welcome( self, powdict ):
        #example of setting a special_template for an action not following the Controller_action.tmpl convention
        #return self.render(special_tmpl="hero.tmpl",model=self.model, powdict=powdict)
        print "welcome"
        
    def thanks( self ):
        print "Das ist die thanks action"
        
    def howto_start( self,powdict ):
        return self.render(model=self.model, powdict=powdict)
    
class B(object):   
    def __init__(self):
        print "init"
        self.an_attribute = "hallo"
    
    def a_method(self):
        print "a method" 

    
if __name__ == "__main__":
    a = AppController()
    AuthController.protect(a)
    a.thanks()
    a.welcome("admin")
    b = B()
    print b.__dict__.items() 
    for k,v in b.__dict__.iteritems():
        print k,v
    
########NEW FILE########
__FILENAME__ = auth
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 

# date created:     2011-06-21

import sys
import os
from mako.template import Template
from mako.lookup import TemplateLookup
import datetime

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models/powmodels" )))


import powlib
import BaseController
import datetime


class AuthController(BaseController.BaseController):
    
    def __init__(self):
        self.modelname = "User"
        BaseController.BaseController.__init__(self)
        self.login_required = {}
    
    @staticmethod
    def protect(cls):
        print "in protect", cls
        print cls.__dict__.items()
        for k, v in cls.__dict__.items():
            print "k"
            if not k.startswith("__") and isinstance(v, type(AuthController.protect)):
                print "wrap", k
                setattr(cls, k, mkwrapper(v))

    def mkwrapper(f):
        def wrapper(*args, **kwargs):
            print "pruefe ", f.__name__
            result = f(*args, **kwargs)
            print "fertig mit gepruefter funktion:", f.__name__
            return result
        return wrapper
    
    
    def authenticate(self):
        print "AuthController.authenticate()"
        return
        
    def register(self, powdict):
        """ registers a User """
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def unregister(self, powdict):
        """ unregisters a User """
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def test_render(self, powdict):
        self.model.__init__()
        return self.render_message("Test", "success", powdict=powdict)
    
    def login( self, powdict):
        """ shows the Auth_login.tmpl template form """
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def do_login( self, powdict ):
        """ The real login action """
        user = User.User()
        session = powdict["SESSION"]
        if powdict["REQ_PARAMETERS"].has_key("loginname") and powdict["REQ_PARAMETERS"].has_key("password"):
            try:
                user = user.find_by("loginname",powdict["REQ_PARAMETERS"]["loginname"])
                if user.password == powdict["REQ_PARAMETERS"]["password"]:
                    #login ok
                    session["user.id"] = user.id
                    session["user.loginname"] = user.loginname
                    session.save()
                    powdict["FLASHTEXT"] = "You successfully logged in, %s " % (user.loginname)
                    powdict["FLASHTYPE"] = "success"
                    return self.redirect("welcome",powdict=powdict)
                else:
                    powdict["FLASHTEXT"] = "Error logging you in, %s " % (user.loginname)
                    powdict["FLASHTYPE"] = "error"
                    return self.redirect("login",powdict=powdict)
            except:
                powdict["FLASHTEXT"] = "Error logging you in " 
                powdict["FLASHTYPE"] = "error"
                return self.redirect("login", powdict=powdict)
        else:
            powdict["FLASHTEXT"] = "Error logging you in. You have to fill in username and password. " 
            powdict["FLASHTYPE"] = "error"
            return self.redirect("login", powdict=powdict)
        return
    
    def logout( self, powdict):
        """logs a user out """
        session = powdict["SESSION"]
        session["user.id"] = 0
        session.save()
        powdict["FLASHTEXT"] = "You successfully logged out. " 
        powdict["FLASHTYPE"] = "success"
        return self.redirect("login", powdict=powdict)
    
    def access_granted(self,**kwargs):
        """ 
            returns true if access is ok, meaning that:
            no login required or login required AND user already lgged in.
        """
        powdict = kwargs.get("powdict",None)
        session = powdict["SESSION"]
        is_logged_in = False
        if self.current_action in self.login_required:
            # login required, so check if user is logged in. 
            try:
                if session["user.id"] != 0:
                    return True
            except KeyError:
                    return False
       
        else:
            # no login required
            return True
        # by default return False
        return False
    

########NEW FILE########
__FILENAME__ = orig_shorttest
class Foo:
    def __init__(self, x):
        self.x = x
       
    def bar(self, y):
        return self.x + y

def wrap(cls):
    for k, v in cls.__dict__.items():
        print "key,value:", k,v
        print "type v", type(v)
        print "type(wrap)", type(wrap)
        if not k.startswith("__") and isinstance(v, type(wrap)):
            print "wrap", k
            setattr(cls, k, mkwrapper(v))

def mkwrapper(f):
    def wrapper(*args, **kwargs):
        print "vor ", f.__name__
        result = f(*args, **kwargs)
        print "nach", f.__name__
        return result
    return wrapper

foo = Foo(3)
wrap(Foo)
print foo.bar(4)
########NEW FILE########
__FILENAME__ = shorttest
class Foo:
    def __init__(self, x):
        self.x = x
        
    def bar(self, y):
        return self.x + y

def wrap(cls):
    print cls, type(cls)
    for k, v in cls.__dict__.items():
        print k
        if not k.startswith("__") and isinstance(v, type(wrap)):
            print "wrap", k
            setattr(cls, k, mkwrapper(v))
    
def mkwrapper(f):
    def wrapper(*args, **kwargs):
        print "vor ", f.__name__
        result = f(*args, **kwargs)
        print "nach", f.__name__
        return result
    return wrapper
    
class Protector(object):
    def __init__(self):
        self.to_protect = {}

    def pre(self): 
        print 'pre'
    
    def post(self): 
        print 'post'
    
    def wrap_old(self,cls):
        print type(self.wrap_old)
        print type(self.__class__.wrap_old)
        print cls.__dict__.items()
        for k, v in cls.__dict__.items():
            print "key, value:", k,v
            if not k.startswith("__") and isinstance(v, type(self.__class__.wrap_old)):
                print "wrap", k
                setattr(cls, k, mkwrapper(v))
                
    def wrap(self, instance):
        #print self.__dict__
        #print dir(self.__class__.__dict__)
        print instance.__class__.__dict__.items()
        for k, v in instance.__class__.__dict__.items():
            print k,v
            if not k.startswith("__"):
                func = getattr(instance, k)
                print "callable",callable(func)
                if callable(func):
                    print "wrap", k
                    setattr(instance.__class__, k, mkwrapper(v))
    
    def wrap_class(self, cls):
        #print self.__dict__
        #print dir(self.__class__.__dict__)
        print cls.__dict__.items()
        for k, v in cls.__dict__.items():
            print "key, value:", k,v
            if not k.startswith("__"):
                func = getattr(cls, k)
                print "callable",callable(func)
                if callable(func):
                    print "wrap", k
                    setattr(cls, k, mkwrapper(v))
    
    def mkwrapper(f):
        def wrapper(*args, **kwargs):
            print "vor ", f.__name__
            result = f(*args, **kwargs)
            print "nach", f.__name__
            return result
        return wrapper



if __name__ == "__main__":
    
    foo = Foo(3)
    p = Protector()
    #p.wrap(foo)
    p.wrap_class(Foo)
    #p.wrap_old(Foo)
    print foo.bar(4)
    print "----------------------"
    # 
    #wrap(Foo)
    #print foo.bar(4)
########NEW FILE########
__FILENAME__ = shorttest2
#
# mostly taken from: http://www.semicomplete.com/blog/geekery/python-method-call-wrapper.html
#
class Filter(object):
    @staticmethod
    def wrapmethod(func, premethod=None, postmethod=None):
      def w(function, *args, **kwds):
        if premethod:
          premethod(*args, **kwds)
        function(*args, **kwds)
        if postmethod:
          postmethod(*args, **kwds)
      return lambda *x,**k: w(func,*x,**k)




def pre(self, *args, **kwds):
  print "hello: %s, %s" % (args, kwds)

def post(self, *args, **kwds):
  print "world: %s, %s" % (args, kwds)

class C(object):
    @staticmethod
    def pre(self, *args, **kwds):
        print "hello C: %s, %s" % (args, kwds)
    @staticmethod
    def post(self, *args, **kwds):
        print "world C: %s, %s" % (args, kwds)
    
  
class X(object):
    def Foo(self, *args, **kwds):
        try:
            print kwds['somearg']
        except: 
            print "No 'somearg' argument given"
    Foo = Filter.wrapmethod(Foo, C.pre)

x = X()

x.Foo(42, bar=33)
x.Foo(somearg="Hello there")

########NEW FILE########
__FILENAME__ = shorttest3
class Wrapper(object):
    def __init__(self, obj):
        self.obj = obj
        
    def __getattr__(self, name):
        func = getattr(self.__dict__['obj'], name)
        if callable(func):
            def my_wrapper(*args, **kwargs):
                print "entering"
                ret = func(*args, **kwargs)
                print "exiting"
                return ret
            return my_wrapper
        else:
            return func
    

## for example on a string:
s = 'abc'
w = Wrapper(s)
print w.isdigit()
########NEW FILE########
__FILENAME__ = test_for_forum
class Foo:
    def __init__(self, x):
        self.x = x
        
    def bar(self, y):
        return self.x + y

    
class Protector(object):
    def __init__(self):
        self.to_protect = {}

    def pre(self): 
        print 'pre'
    
    def post(self): 
        print 'post'
    
    def wrap(self,cls):
        print cls.__dict__.items()
        for k, v in cls.__dict__.items():
            print "key, value:", k,v
            print "type self(wrap):", type(self.wrap)
            print "type(v):", type(v)
            if not k.startswith("__") and isinstance(v, type(self.wrap)):
                print "wrap", k
                setattr(cls, k, mkwrapper(v))
    
    def mkwrapper(f):
        def wrapper(*args, **kwargs):
            print "vor ", f.__name__
            result = f(*args, **kwargs)
            print "nach", f.__name__
            return result
        return wrapper



if __name__ == "__main__":
    
    foo = Foo(3)
    p = Protector()
    p.wrap(Foo)
    print foo.bar(4)
    
########NEW FILE########
__FILENAME__ = PostController
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 
# date created: 	2012-07-22
import sys
import os
from mako.template import Template
from mako.lookup import TemplateLookup
import datetime

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../controllers" )) )

import powlib, pow_web_lib
import PowObject
import BaseController
import Post

class PostController(BaseController.BaseController):
    def __init__(self):
        self.modelname = "Post"
        BaseController.BaseController.__init__(self)
        self.login_required = []
        
    def list( self, powdict ):
        res = self.model.find_all()
        return self.render(model=self.model, powdict=powdict, list=res)
    
    def blog( self, powdict ):
        res = self.model.find_all()
        return self.render(model=self.model, powdict=powdict, list=res)
    
    def show( self,powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
        
    def new( self, powdict ):
        self.model.__init__()
        dict = powdict["REQ_PARAMETERS"]
        if dict.has_key("title"):
            self.model.set("title", dict["title"])
        if dict.has_key("content"):
            self.model.set("content", dict["content"])
            
        ofiledir  = os.path.normpath("./public/img/blog/")
        if pow_web_lib.get_form_image_data( "image", dict, ofiledir):
            # if form contains file data AND file could be written, update model
            self.model.set("image", dict["image"].filename )   
        else:
            # dont update model
            self.model.set("image","")     
        self.model.create()
        return self.render(model=self.model, powdict=powdict)
    
    def create( self, powdict):
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def edit( self, powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
    
    def update( self, powdict ):
        self.model.__init__()
        #print powdict["REQ_PARAMETERS"]
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        #print self.model
        dict = powdict["REQ_PARAMETERS"]
        if dict.has_key("title"):
            self.model.set("title", dict["title"])
        if dict.has_key("content"):
            self.model.set("content", dict["content"])
        #print dir(powdict["REQ_BODY"])  
        
        ofiledir  = os.path.normpath("./public/img/blog/")
        if pow_web_lib.get_form_image_data( "image", dict, ofiledir):
            # if form contains file data AND file could be written, update model
            self.model.set("image", dict["image"].filename )   
            self.model.update()
        else:
            # dont update model
            pass
        
        return self.render(model=self.model, powdict=powdict)
    
    def delete( self, powdict ):
        self.model.__init__()
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        self.model.delete(self.model.get_id())
        return self.render(model=self.model, powdict=powdict)

########NEW FILE########
__FILENAME__ = PostControllerWithoutLogin
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 
# date created: 	2012-07-22
import sys
import os
from mako.template import Template
from mako.lookup import TemplateLookup
import datetime

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../controllers" )) )

import powlib, pow_web_lib
import PowObject
import BaseController
import Post

class PostController(BaseController.BaseController):
    def __init__(self):
        self.modelname = "Post"
        BaseController.BaseController.__init__(self)
        self.login_required = []
        
    def list( self, powdict ):
        res = self.model.find_all()
        return self.render(model=self.model, powdict=powdict, list=res)
    
    def blog( self, powdict ):
        res = self.model.find_all()
        return self.render(model=self.model, powdict=powdict, list=res)
    
    def show( self,powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
        
    def new( self, powdict ):
        self.model.__init__()
        dict = powdict["REQ_PARAMETERS"]
        if dict.has_key("title"):
            self.model.set("title", dict["title"])
        if dict.has_key("content"):
            self.model.set("content", dict["content"])
            
        ofiledir  = os.path.normpath("./public/img/blog/")
        if pow_web_lib.get_form_image_data( "image", dict, ofiledir):
            # if form contains file data AND file could be written, update model
            self.model.set("image", dict["image"].filename )   
        else:
            # dont update model
            self.model.set("image","")     
        self.model.create()
        return self.render(model=self.model, powdict=powdict)
    
    def create( self, powdict):
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def edit( self, powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
    
    def update( self, powdict ):
        self.model.__init__()
        #print powdict["REQ_PARAMETERS"]
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        #print self.model
        dict = powdict["REQ_PARAMETERS"]
        if dict.has_key("title"):
            self.model.set("title", dict["title"])
        if dict.has_key("content"):
            self.model.set("content", dict["content"])
        #print dir(powdict["REQ_BODY"])  
        
        ofiledir  = os.path.normpath("./public/img/blog/")
        if pow_web_lib.get_form_image_data( "image", dict, ofiledir):
            # if form contains file data AND file could be written, update model
            self.model.set("image", dict["image"].filename )     
        else:
            # dont update model
            pass
        self.model.update()
        return self.render(model=self.model, powdict=powdict)
    
    def delete( self, powdict ):
        self.model.__init__()
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        self.model.delete(self.model.get_id())
        return self.render(model=self.model, powdict=powdict)

########NEW FILE########
__FILENAME__ = replace_tabs_by_spaces
import sys,os,os.path
import string
     
if __name__ == "__main__":

    
    for (path, dirs, files) in os.walk("../"):
        print path
        for file in files:
            if "git" in path or "scripts" in path:
                #print "skipping: ", path
                pass
            else:
                filename, extension = os.path.splitext(file)
                #print filename, "  ", extension
                if extension ==".py":
                    print "process", path + file
                    infile = os.path.join(path, file)
                    f = open(infile,"r")
                    out = ""
                    for line in f.readlines():
                        out += line.replace("\t", "    ")
                    f.close()
                    os.remove(infile)
                    outfile = open(infile, "w")
                    outfile.write(out)
                    outfile.close()
            
    sys.exit(0)
########NEW FILE########
__FILENAME__ = space_tabs
#
# kill all those ugly tabs ( \t ) and replace it with 4-spaces
#
#


import sys
import os
import os.path

exclude_dirs = [".git"]
if __name__ == "__main__":
    path = "./"
    i = 0
    for (path, dirs, files) in os.walk(path):
        for elem in exclude_dirs:
            #print "comparing:", path , " with:", elem, "result:", path.find(elem)
            if path.find(elem) < 0:
                print "path: ", path
                print "dirs: ",dirs
                print "files: ",files
                for item in files:
                    (name, ext) = os.path.splitext(item)
                    print "%-20s ==> %10s" % (name, ext)
                print "----"
            else:
                print "excluding: ", path 
        
        i += 1
        if i >= 3:
            break
########NEW FILE########
__FILENAME__ = test
import generate_migration
import sys,os

inl = "firstname String(50), lastname String(50), email String(100)"
inf = open(os.path.normpath("./stubs/partials/db_migration_stub2_part2.py"))
instr = inf.read()
print generate_migration.transform_col_defs(instr, inl)
########NEW FILE########
__FILENAME__ = test_dispatch
#
#
# test method dispatching for olugins using getattr
#

class Validate(object):
    
    def __init__(self):
        pass
    
    def presence_of(self, model_attribute):
        print "validating the presence of an attribute: ", model_attribute
        return


class Model(object, Validate):
    
    
    def __init__(self):
        self.firstname = "None"
        self.lastname = "None"
    
    
    def set_firstname(self, name):
        self.firstname = name
        return

    def set_lastname(self, name):
        self.lastname = name
        return


if __name__ == "__main__":
    print "start test"
########NEW FILE########
__FILENAME__ = test_filter
#
# test the pre_/post_filter functionality
#


import AppController
import ApplicationController

if __name__ == "__main__":
    app = AppController.AppController()
    app.pre_filter("authenticate","only", ["thanks"])
    app.pre_filter("authenticate","any")
    app.thanks()
    
    
########NEW FILE########
__FILENAME__ = test_getattribute
class A(object):
    def __init__(self):
        self.__dict__['x'] = 5
        self.adict = {}
        

    def __getattribute__(self, name):
        if name != '__dict__':
            print '__getattribute__', name
        return object.__getattribute__(self, name)

    def __getattr__(self, name):
        if name != '__dict__':
            print '__getattr__', name
        return 7

    def __setattr__(self, name, value):
        print '__setattr__', name, value
        return object.__setattr__(self, name, value)

    def func(self, x):
        return x+1
    
class B(object):
    
    def __inti__(self):
        super(B, self).__init__()
    def meths(self):
        return [method for method in dir(self) if callable(getattr(self, method))]
    def a(self):
        return
    def b(self):
        return
    
if __name__ == '__main__':
    a = A()
    a.y = 6
    print a.x
    print a.y
    print a.z
    print a.func(2)
    print a.adict
    print "B"
    b = B()
    b.meths()
########NEW FILE########
__FILENAME__ = test_github_json
#
##
#
# test github api access
#
#

import json
import requests
import sys


class User(object):
    
    def __init__(self, name = "", password = ""):
        self.name = name
        self.password = password
    
    
def github.get_milestone_info(user, repo, milestone):
    r = requests.get('https://api.github.com/repos/%s/%s/milestones/%s' % (user,repo, milestone), auth=(user, pwd))
    #print json.dumps(r.json, sort_keys=True, indent=4)
    return r.json
    
def get_commit_info( user, repo, branch):
    r = requests.get('https://api.github.com/repos/%s/%s/commits/%s' % (user,repo, branch), auth=(user, pwd))
    return r.json
    
if __name__ == "__main__":
    #user = raw_input("github user to check:")
    #pwd = raw_input("github password for %s:" % (user) )
    #repo = raw_input("github repo to check:")
    #branch = raw_input("branch for %s repo to check:" % (repo))
    user = User()
    user.name = "pythononwheels"
    user.password = "h0dde!1"
    repo = "pow_devel" 
    branch = "beta1_auth_and_relate"
    
    
    
    #ostr = ""
    #for di in r.json:
    #    ostr += "date: " + di["commit"]["author"]["date"] + "\n"
    #    ostr += "author name: "+ di["commit"]["author"]["name"] +  "\n"
    #    ostr += "author email: " + di["commit"]["author"]["email"] + "\n"
    #    ostr += "commit message: " + di["commit"]["message"] + "\n"
    #    ostr += "commit url: " + di["commit"]["url"] + "\n"
    #    print di
    #of = open("out.txt", "w")
    #of.write(ostr)
    #of.close()   
    sys.exit()
# test github api access
#
#

import json
import requests
import sys

if __name__ == "__main__":
    #user = raw_input("github user to check:")
    #pwd = raw_input("github password for %s:" % (user) )
    #repo = raw_input("github repo to check:")
    #branch = raw_input("branch for %s repo to check:" % (repo))
     
    user = "pythononwheels"
    pwd = "h0dde!1"
    repo = "pow_devel" 
    branch = "beta1_auth_and_relate"
    #r = requests.get('https://api.github.com/user/repos' , auth=(user, pwd))
    #print json.dumps(r.json, sort_keys=True, indent=4)
    
    r = requests.get('https://api.github.com/repos/%s/%s/commits/%s' % (user,repo, branch), auth=(user, pwd))
    print json.dumps(r.json, sort_keys=True, indent=4)
    #ostr = ""
    #for di in r.json:
    #    ostr += "date: " + di["commit"]["author"]["date"] + "\n"
    #    ostr += "author name: "+ di["commit"]["author"]["name"] +  "\n"
    #    ostr += "author email: " + di["commit"]["author"]["email"] + "\n"
    #    ostr += "commit message: " + di["commit"]["message"] + "\n"
    #    ostr += "commit url: " + di["commit"]["url"] + "\n"
    #    print di
    #of = open("out.txt", "w")
    #of.write(ostr)
    #of.close()   
    sys.exit()
########NEW FILE########
__FILENAME__ = test_inspect
from optparse import OptionParser

class B(object):
    
    def __init__(self):
        super(B, self).__init__()
    def meths(self):
        import inspect
        alist =  inspect.getmembers(self, predicate=inspect.ismethod)
        for elem in alist:
            print elem[0]
      

    def a(self):
        print "I am a"
        
    def b(self):
        print "I am b"
    
if __name__ == '__main__':
    
    print "B"
    b = B()
    b.meths()
########NEW FILE########
__FILENAME__ = unicode_test
﻿# unicode test for BasePost
# 
import sys, os

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./models/basemodels" )))


import BasePost
import Post

if __name__ == "__main__":
    b = BasePost.BasePost()
    
    s_title = "Hällo"
    unicode_title = s_title.decode("utf-8")
    print s_title, type(s_title)
    print unicode_title, type(unicode_title)
    b.title = unicode_title
    b.utitle = unicode_title
    b.strtitle = unicode_title
    #print b.title, type(b.title)
    b.create()
    
########NEW FILE########
__FILENAME__ = db
#
# Author:       khz
# Date created: 16/08/2012
# purpose:      database configuration 
# Changes:
# 16/08/2012    initially created
#
development = {
    "dialect"   :   "sqlite",
    "driver"    :   "",
    "database"  :   "please_rename_the_development_db",
    "host"      :   "localhost",
    "port"      :   "0",
    "parameters":   "",
    "username"  :   "",
    "password"  :   ""

}

test = {
    "dialect"   :   "sqlite",
    "driver"    :   "",
    "database"  :   "please_rename_the_test_db",
    "host"      :   "localhost",
    "port"      :   "0",
    "parameters":   "",
    "username"  :   "",
    "password"  :   ""

}

production = {
    "dialect"   :   "sqlite",
    "driver"    :   "",
    "database"  :   "please_rename_the_production_db",
    "host"      :   "localhost",
    "port"      :   "0",
    "parameters":   "",
    "username"  :   "",
    "password"  :   ""

}

########NEW FILE########
__FILENAME__ = ext
#
# configuration file for PythonOnWheels extensions
# all extensions shall by convention be placed in
# appname/ext dir. Any specific subdir might be chosen 
# but needs to be configured here.
# You can take the pow_auth and validation extensions as example.
#
#

# list of available extensions.
# Format: ( "ext_name", enabled? ), where enabled can be True or False
extensions = [ 
    ("auth", True),
    ("validate", False)
]

# extension specific dictionary for extension configuration.
# dir is the directory inside appname/ext where pow will look for the module.
# module specifies the main extension module to load.
auth = {
    "dir" : "auth",
    "module" : "auth",
    "models_dir" : "models",
    "controllers_dir" : "controllers",
    "views_dir" : "views"
}

validate = {
    "dir" : "validate",
    "module" : "Validate"
}
########NEW FILE########
__FILENAME__ = pow
#
# project_name = python on wheels
# author = khz
# author_email = khz@pythononwheels.org
# short_description = python rapid web app generator framework
# homepage_base_url = http://www.pythononwheels.org
#
# New style main config file for PythonOnWheels.
# Uses python data structures (dict, list etc) instead of ini-style
# way better handling ;)
# Date: July 2012
# 

global_conf = { 
    "ENV"               :   "development",
    "DEFAULT_TEMPLATE"  :   "hero.tmpl",
    "DEFAULT_ENCODING"  :   "utf-8",
    "PORT"              :   "8080",
    "MAX_FILE_UPLOAD"   :   "100000",
    "STD_BINARY_PATH"   :   "/static/img/",
    "DEFAULT_IMAGE_NAME":   "image",
    "DEFAULT_VIDEO_NAME":   "video",
    "DEFAULT_AUDIO_NAME":   "audio",
    "DEFAULT_TEXT_NAME" :   "text"
}

routes = {
     "default"  :   "/app/welcome" 
}

logging = {
      # turn POW logging on OR off
      "TURN"                    :   "off",
      "LOGFILE"                 :   "log.txt",
      "LOGFILE_MODE"            :   "w",
      # log_level = DEBUG or INFO
      "LOG_LEVEL"               :   "DEBUG",
      # see: http://docs.python.org/howto/logging.html#logging-basic-tutorial
      "FORMAT"                  :   "%(asctime)s %(message)s",
      # turn SQLAlchemy logging on OR off
      "SQLALCHEMY_LOGGING"      :   "False"
}
########NEW FILE########
__FILENAME__ = AppController
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 

# date created:     2011-06-21

import sys
import os


sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models/powmodels" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../controllers" )) )

import powlib
from powlib import mixin, uc
from BaseController import BaseController
import datetime

#import AuthController 

#@mixin(AuthController.AuthController)
class AppController(BaseController):
    
    def __init__(self):
        # it is needed to set a Modelname before calling the BaseControllers init
        self.modelname = "App"
        BaseController.__init__(self)
        
        self.login_required = []
        # example of locked actions and the redirections.
        self.locked_actions = {}
    
    def ajax( self, powdict ):
        print "AJAX-Request"
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S")
        ret_str = uc("""<div class="alert alert-success">
                <button type="button" class="close" data-dismiss="alert">&times;</button>
                <strong>Yeah! AJAX with python rocks totally now:</strong>&nbsp %s &nbsp; %s 
              </div>""" % (now, powdict["REQ_BODY"] ))
        return ret_str 
        
    
    def welcome( self,powdict ):
        #example of setting a special_template for an action not following the Controller_action.tmpl convention
        #return self.render(special_tmpl="hero.tmpl",model=self.model, powdict=powdict)
        return self.render(model=self.model, powdict=powdict)
        
    def thanks( self ):
        print "Das ist die thanks action"
        
    def howto_start( self,powdict ):
        return self.render(model=self.model, powdict=powdict)
    
    
        
    

########NEW FILE########
__FILENAME__ = BaseController
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 

# date created:     2011-04-27


import sys
import os
from mako.template import Template
from mako.lookup import TemplateLookup


sys.path.append(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )) )
sys.path.append(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )) )
sys.path.append(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../config" )) )
import pow
import powlib
import PowObject

class BaseController(object):
    #model = None
    #session = None
    #modelname = "None"
    #current_action = "list"
    moddir="/../views/mako_modules"
    #mylookup = None
    
    
    def __init__(self):
        # put the actions that require a login into login_required list.
        self.login_required = []
        # put the actions you implemented but do not want to be callable via web request 
        # into the locked_actions dictionary. Format: "actionname" : "redirect_to" }
        # simple_server and pow_router will not call locked actions but redirect to the given value, instead
        self.locked_actions = {}
        self.current_action = "NOT_DEFINED"
        # Format: { filter: ( selector, [list of actions] ) } 
        self.pre_filter_dict = {}
        
        self.mylookup = TemplateLookup(directories=[os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../views/")),
                    os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../views/layouts/")),
                    os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../views/stylesheets/"))
                    ] )
        # example how to instanciate the model:
        if self.modelname == None or self.modelname == "None":
            self.model = None
            self.session = None
        else:
            self.model = powlib.load_class(self.modelname, self.modelname)
            self.session = self.model.pbo.getSession()
       
        
    
    #def __getattribute__(self, key):
    #   return super(BaseController, self).__getattribute__(key)
    #def __getattribute__(self,name):
    #    # check if pre_filter needs to be applied
    #    if name != '__dict__':
    #        #print '__getattribute__', name
    #        if name in self.__dict__["pre_filter_dict"].keys():
    #            print "filter found"
    #        else:
    #            print "no filter found",  self.__dict__["pre_filter_dict"].keys()
    #            
    #    ret = BaseController.__getattribute__(self,name)
    #    
    #    return ret
    def pre_filter(self, filter, selector ,action_list = []):
        
        """
        set a pre_filter operation for controller actions.
        @param filter:             Name of the filter to be executed before the action (Module.Class.Method) 
                                  if there are no dots self.filter is assumed
        @param selector:           One of: any, except,only
        @param action_list:        If selector is except OR only, this defines the actions in scope.
        """
        # check if filter already set.
        if not self.pre_filter_dict.has_key(filter):
            # check if selector correct
            if selector in ["any", "except", "only"]:
                # set the filter
                if selector == "any":
                    import inspect
                    alist =  inspect.getmembers(self, predicate=inspect.ismethod)
                    for elem in alist:
                        print elem[0]
                elif selector == "only":
                    for func in action_list:
                        if self.pre_filter_dict.has_key(func):
                            self.pre_filter_dict[func].append(filter)
                        else:
                            self.pre_filter_dict[func] = [filter]
                elif selector == "except":
                    pass
                print "Added pre_filter: ", self.pre_filter_dict
                return True
            else:
                raise NameError("selector must be one of: only, except or any. You gave %s" % (str(selector)))
                return False
        return False 
       
    def get_locked_actions(self):
        """ returns the dictionary of locked actions. 
        Locked actions will not be executed by simple_server nor pow_router"""
        return self.locked_actions
    
    def is_locked(self, action):
        """ returns the the True, if the given action is locked. 
        Locked actions will not be executed by simple_server nor pow_router"""
        if self.locked_actions.has_key(action):
            return self.locked_actions[action]
        else:
            return False
        # should never be reached
        return False

    def get_redirection_if_locked(self, action): 
        """returns the redirection, if the given action is locked. None otherwise. 
        Locked actions will not be executed by simple_server nor pow_router"""
        if self.is_locked(action):
            
            return ( self.locked_actions[action].split("/")[0], 
                     self.locked_actions[action].split("/")[1] )
        else:
            return "None"
        # should never be reached
        return "None"
            
    def render(self, **kwargs):
        """
            Renders a template:
            
            Mandatory Parameters:
            powdict    =    The powdict containing all the HTTP:Request Parameters, Body etc.
            
            Optional Parameters:
            special_tmpl     =     a speciaol template to use. By default Controller_current_action.tmpl is chosen 
        """
        powdict = kwargs["powdict"]
        kwargs["powdict"] = powdict
        kwargs["template"] = pow.global_conf["DEFAULT_TEMPLATE"] 

        special_tmpl = None
        if kwargs.has_key("special_tmpl"):
            special_tmpl = kwargs["special_tmpl"]
            del kwargs["special_tmpl"]

        if self.current_action not in self.locked_actions:
            if self.access_granted(**kwargs) == True:
                first_part = os.path.join( os.path.dirname(os.path.abspath(__file__)),"../views/")
                if special_tmpl == None:
                    fname =  self.modelname + "_" + self.current_action +".tmpl"
                else:
                    fname =  special_tmpl
                mytemplate = self.mylookup.get_template(fname)
                #mytemplate = Template(filename=fname, lookup=self.mylookup)
                return mytemplate.render(**kwargs)
            else:
                #self.setCurrentAction("login")
                kwargs["powdict"]["FLASHTEXT"] = "You need to be logged in to access method: %s" % (str(self.current_action))
                kwargs["powdict"]["FLASHTYPE"] = "error"
                #fname = os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../views/App_login.tmpl"))
                fname = "App_login.tmpl"
                #mytemplate = Template(filename=fname, lookup=self.mylookup)
                mytemplate = self.mylookup.get_template(fname)
                return mytemplate.render(**kwargs)
        else:
            kwargs["ERROR_INFO"] = "The action you have called (", self.current_action, "is locked from outside access."
            return self.error(**kwargs)
            
    
    def redirect(self, action, **kwargs):
        """ sets the given action and executes it so that all prerequisites are correct """
        self.setCurrentAction(action)
        return eval("self." + action + "(**kwargs)")
    
    def re_route(self, controller, action,**kwargs):
        """ Loads another Controller and calls the given action"""
        kwargs["template"] = pow.global_conf["DEFAULT_TEMPLATE"] 
        controller = None
        controller = powlib.load_class( string.capitalize(controller),string.capitalize(controller))
        if controller != None:
            if hasattr( aclass, action ):
                controller.setCurrentAction(action)
                real_action = eval("controller." + action)
                return real_action(kwargs["powdict"])
            else:
                return render_message("Error, no such action: %s, for controller: %s" % (action, controller), "error", **kwargs)
        else:
            return render_message("Error, no such controller: %s" % (controller), "error", **kwargs)
        return render_message("Error, this should never be reached" % (controller), "error", **kwargs)
    
    def render_message(self, message, type, **kwargs ):
        """Renders the given message using the given type (one of error || success || info || warning)
            as flashmessage, using the error.tmpl. This special tmpl displays the given message alone, embedded
            in the default context.template
            
            Mandatory Parameters:
            message = the flashmessagr
            type    = the type of the message (different css styles)
            powdict = powdict
            Optional:
            tmpl    = a special .tmpl file to use. 
            """
        
        # set the context template.        
        kwargs["template"] = pow.global_conf["DEFAULT_TEMPLATE"] 
        # by default call the error.tmpl. You can give another template using tmpl="template_name.tmpl".

        if kwargs.has_key("tmpl"):
            tmpl = kwargs["tmpl"]
        else:
            tmpl = "error.tmpl"
        # ste the flash messages 
        kwargs["powdict"]["FLASHTEXT"] = message
        kwargs["powdict"]["FLASHTYPE"] = type
        
        mytemplate = self.mylookup.get_template(tmpl)
        return mytemplate.render(**kwargs)
    
    
    def access_granted(self,**kwargs):
        """ 
            returns true if access is ok, meaning that:
            no login required or login required AND user already lgged in.
        """
        powdict = kwargs.get("powdict",None)
        session = powdict["SESSION"]
        is_logged_in = False
        if self.current_action in self.login_required:
            # login required, so check if user is logged in. 
            try:
                if session["user.id"] != 0:
                    return True
            except KeyError:
                    return False
       
        else:
            # no login required
            return True
        # by default return False
        return False
    
        
    def setCurrentAction(self, action ):
        """ sets the cuurent action of this controller to action"""
        self.current_action = action
        
########NEW FILE########
__FILENAME__ = AuthController
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 

# date created:     2011-06-21

import sys
import os
from mako.template import Template
from mako.lookup import TemplateLookup
import datetime

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models/powmodels" )))


import powlib
import BaseController
import datetime


class AuthController(BaseController.BaseController):
    
    def __init__(self):
        self.modelname = "User"
        BaseController.BaseController.__init__(self)
        self.login_required = []
        self.locked_actions = {}
    
    def authenticate(self):
        print "AuthController.authenticate()"
        return
        
    def register(self, powdict):
        """ registers a User """
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def unregister(self, powdict):
        """ unregisters a User """
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def test_render(self, powdict):
        self.model.__init__()
        return self.render_message("Test", "success", powdict=powdict)
    
    def login( self, powdict):
        """ shows the Auth_login.tmpl template form """
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def do_login( self, powdict ):
        """ The real login action """
        user = User.User()
        session = powdict["SESSION"]
        if powdict["REQ_PARAMETERS"].has_key("loginname") and powdict["REQ_PARAMETERS"].has_key("password"):
            try:
                user = user.find_by("loginname",powdict["REQ_PARAMETERS"]["loginname"])
                if user.password == powdict["REQ_PARAMETERS"]["password"]:
                    #login ok
                    session["user.id"] = user.id
                    session["user.loginname"] = user.loginname
                    session.save()
                    powdict["FLASHTEXT"] = "You successfully logged in, %s " % (user.loginname)
                    powdict["FLASHTYPE"] = "success"
                    return self.redirect("welcome",powdict=powdict)
                else:
                    powdict["FLASHTEXT"] = "Error logging you in, %s " % (user.loginname)
                    powdict["FLASHTYPE"] = "error"
                    return self.redirect("login",powdict=powdict)
            except:
                powdict["FLASHTEXT"] = "Error logging you in " 
                powdict["FLASHTYPE"] = "error"
                return self.redirect("login", powdict=powdict)
        else:
            powdict["FLASHTEXT"] = "Error logging you in. You have to fill in username and password. " 
            powdict["FLASHTYPE"] = "error"
            return self.redirect("login", powdict=powdict)
        return
    
    def logout( self, powdict):
        """logs a user out """
        session = powdict["SESSION"]
        session["user.id"] = 0
        session.save()
        powdict["FLASHTEXT"] = "You successfully logged out. " 
        powdict["FLASHTYPE"] = "success"
        return self.redirect("login", powdict=powdict)
    
    def access_granted(self,**kwargs):
        """ 
            returns true if access is ok, meaning that:
            no login required or login required AND user already lgged in.
        """
        powdict = kwargs.get("powdict",None)
        session = powdict["SESSION"]
        is_logged_in = False
        if self.current_action in self.login_required:
            # login required, so check if user is logged in. 
            try:
                if session["user.id"] != 0:
                    return True
            except KeyError:
                    return False
       
        else:
            # no login required
            return True
        # by default return False
        return False
    

########NEW FILE########
__FILENAME__ = cleanup
#
# Standard setup script to enable this plugin in PoW
#
import sys
import os
import os.path

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../modules" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../" )))

import generate_migration
import generate_model
import generate_scaffold
import powlib
import ext

if __name__ == "__main__":
    
    
    if not powlib.check_for_file("./", "exec_once.nfo"):
       print "#########################################################################" 
       print "# ==> plugin has not been setup, yet. Nothing to be done."       
       print "#########################################################################"
       sys.exit()
       
    print "###################################################################"
    print "# cleaning up auth plugin has to be done manually"
    print "# this is not done automatically to prevent "
    print "# deleting migrations occured inbetween aut install and this attemp "
    print "# to delete it."
    print "#"
    print "# 1. migrate down to the migration before the user migration"
    print "# 2. remove the user_migration (using do_migrate -e)"
    print "# 3. remove the file: exec_once.nfo in the ext/auth directory"
    print "##################################################################"
    
########NEW FILE########
__FILENAME__ = config
#
# configuration for the PoW authentication plugin
#
# cut this and add it to the ext.py file in the confid directory.
# TODO: do this automatically in the setup.py of each plugin
#  


auth = {
    "dir" : "auth",
    "module" : "auth",
    "models_dir" : "models",
    "controllers_dir" : "controllers",
    "views_dir" : "views"
}


# also enable the plugin in ext.py by adding:
#    ("auth", True)
# to the extensions list 
########NEW FILE########
__FILENAME__ = UserController
#
#
# DO NOT EDIT THIS FILE.
# This file was autogenerated by python_on_wheels.
# Any manual edits may be overwritten without notification.
#
# 
# date created: 	2012-08-09
import sys
import os
from mako.template import Template
from mako.lookup import TemplateLookup
import datetime
import string

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../controllers" )) )

import powlib
import pow_web_lib
import PowObject
import BaseController
import sqlalchemy.types

import User

class UserController(BaseController.BaseController):
    def __init__(self):
        self.modelname = "User"
        BaseController.BaseController.__init__(self)
        self.login_required = []
        # put the actions you implemented but do not want to be callable via web request 
        # into the locked_actions dictionary. Format: "actionname" : "redirect_to" }
        # simple_server and pow_router will not call locked actions but redirect to the given value, instead
        self.locked_actions = {}
    
    def list( self, powdict ):
        res = self.model.find_all()
        return self.render(model=self.model, powdict=powdict, list=res)
    
    def show( self,powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
        
    def new( self, powdict ):
        self.model.__init__()
        #print powdict["REQ_PARAMETERS"]
        #print self.model
        dict = powdict["REQ_PARAMETERS"]
        for key in dict:
            statement = 'type(self.model.__table__.columns["%s"].type)' % (key)
            curr_type = eval(statement)
            if curr_type == type(sqlalchemy.types.BLOB()) or curr_type == type(sqlalchemy.types.BINARY()):
                ofiledir  = os.path.normpath("./public/img/")
                print "key: ", key
                if pow_web_lib.get_form_binary_data( key, dict, ofiledir):
                    # if form contains file data AND file could be written, update model
                    self.model.set(key, dict[key].filename )   
                else:
                    # dont update model
                    print " ##### ________>>>>>>>   BINARY DATA but couldnt update model"
            else:
                self.model.set(key, dict[key])
        
        self.model.create()
        powdict["FLASHTEXT"] ="Yep, record successfully created."
        powdict["FLASHTYPE"] ="success"
        spectmpl = string.capitalize(self.model.modelname) + "_message.tmpl"
        return self.render(special_tmpl=spectmpl , model=self.model, powdict=powdict)
    
    def create( self, powdict):
        self.model.__init__()
        return self.render(model=self.model, powdict=powdict)
    
    def edit( self, powdict ):
        res = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        return self.render(model=res, powdict=powdict)
    
    def update( self, powdict ):
        self.model.__init__()
        #print powdict["REQ_PARAMETERS"]
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        #print self.model
        dict = powdict["REQ_PARAMETERS"]
        for key in dict:
            statement = 'type(self.model.__table__.columns["%s"].type)' % (key)
            curr_type = eval(statement)
            if curr_type == type(sqlalchemy.types.BLOB()) or curr_type == type(sqlalchemy.types.BINARY()):
                ofiledir  = os.path.normpath("./public/img/")
                print "key: ", key
                if pow_web_lib.get_form_binary_data( key, dict, ofiledir):
                    # if form contains file data AND file could be written, update model
                    self.model.set(key, dict[key].filename )   
                else:
                    # dont update model
                    print " ##### -_______>>>>>>>   BINARY DATA but couldnt update model"
            else:
                self.model.set(key, dict[key])
        self.model.update()
        powdict["FLASHTEXT"] ="Yep, record successfully updated."
        powdict["FLASHTYPE"] ="success"
        
        spectmpl = string.capitalize(self.model.modelname) + "_message.tmpl"
        return self.render(special_tmpl=spectmpl , model=self.model, powdict=powdict)
        
    
    def delete( self, powdict ):
        self.model.__init__()
        self.model = self.model.find_by("id",powdict["REQ_PARAMETERS"]["id"])
        self.model.delete(self.model.get_id())
        powdict["FLASHTEXT"] ="Yep, record successfully deleted."
        powdict["FLASHTYPE"] ="success"
        spectmpl = string.capitalize(self.model.modelname) + "_message.tmpl"
        return self.render(special_tmpl=spectmpl , model=self.model, powdict=powdict)

########NEW FILE########
__FILENAME__ = pow_validate
#
#
# Basic pythononwheels Validation Extension Module 
# Author:   khz@tzi.org
# Date:     July 2012
#
#


import sys,os,os.path
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../../modules" )))


class PowValidate(object):
    
    def __init__(self):
        pass
        

########NEW FILE########
__FILENAME__ = BaseMigration
import os,sys
import time,datetime
from sqlalchemy import Column
from sqlalchemy.orm import mapper
from sqlalchemy import Table

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
import powlib
from PowObject import PowObject

class BaseMigration(PowObject):
    table_name = "None"
    # self.table is set to a PowTable Object in the migration
    table = None
    
    def __init__(self):
        PowObject.__init__(self)

    def create_table(self):
        if self.table != None:
            self.table.create(bind=PowObject.__engine__, checkfirst=True)
        else:
            raise StandardError("Pow ERROR: table was None")
        
    def drop_table(self, model = None):
        try:
            if model == None:
                self.table = Table(self.table_name, PowObject.__metadata__, autoload = True )
            else:
                self.table = model.__table__
            if self.table != None:
                self.table.drop(bind=PowObject.__engine__, checkfirst=True)
        except:
            raise StandardError("Pow ERROR: table does not exist")
########NEW FILE########
__FILENAME__ = PowBaseObject
import sys, datetime, os, getopt, shutil
import ConfigParser,string
import re

from sqlalchemy import MetaData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.normpath("../config/"))
import powlib
import db
import pow


class PowBaseObject(object):
    """ pow base object class"""
    #__engine__= create_engine(powlib.get_db_conn_str("../config/"))
    __engine__= None
    __metadata__ = MetaData(bind = __engine__)
    __session__ = sessionmaker(bind = __engine__)
    
    def __init__(self):
        #env = pow.global_conf["ENV"]
        logging = pow.logging["SQLALCHEMY_LOGGING"]
        if logging == "True":
            PowBaseObject.__engine__= create_engine(powlib.get_db_conn_str(), echo = True)
        else:
            PowBaseObject.__engine__= create_engine(powlib.get_db_conn_str(), echo = False)
        PowBaseObject.__metadata__.bind =  PowBaseObject.__engine__
        PowBaseObject.__session__.configure( bind = PowBaseObject.__engine__ )
        
    def dispatch(self):
        print "object:" + str(self) +  "dispatch() method invoked"
        return
    
    def getMetaData(self):
        return PowBaseObject.__metadata__
    
    def getEngine(self):
        return PowBaseObject.__engine__
    
    def getSession(self):
        return PowBaseObject.__session__()
        
    def getConnection(self):
        return PowBaseObject.__engine__.connect()
        
    def repr(self):
        return "Not implemented in class: PowBaseObject"
########NEW FILE########
__FILENAME__ = powlib
#
# Author:       khz
# Date created: 17/10/2006
# purpose:      POW lib
# Changes:
# 17/10/2006    initially created
#
import sys, datetime, os, getopt, shutil
import ConfigParser,string
import re

from sqlalchemy import MetaData
from sqlalchemy import create_engine

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../models" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../config" )))
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../controllers" )) )
import pow
import db
import logging

hidden_list = ["created", "last_updated", "group", "user", "id", "password"]
linesep = "\n"
newline = linesep
tab = "    "
MAX_SYSOUT = 50
PARTS_DIR = "./stubs/partials/"

def _log(logstr, level="INFO"):
    if pow.logging["LOG_LEVEL"] == level:
        logging.info(logstr)
    else:
        pass
    return
    
#
# (pattern, search, replace) regex english plural rules tuple
# taken from : http://www.daniweb.com/software-development/python/threads/70647
rule_tuple = (
    ('[ml]ouse$', '([ml])ouse$', '\\1ice'),
    ('child$', 'child$', 'children'),
    ('booth$', 'booth$', 'booths'),
    ('foot$', 'foot$', 'feet'),
    ('ooth$', 'ooth$', 'eeth'),
    ('l[eo]af$', 'l([eo])af$', 'l\\1aves'),
    ('sis$', 'sis$', 'ses'),
    ('man$', 'man$', 'men'),
    ('ife$', 'ife$', 'ives'),
    ('eau$', 'eau$', 'eaux'),
    ('lf$', 'lf$', 'lves'),
    ('[sxz]$', '$', 'es'),
    ('[^aeioudgkprt]h$', '$', 'es'),
    ('(qu|[^aeiou])y$', 'y$', 'ies'),
    ('$', '$', 's')
    )


def uc(instr):
    #encoding = readconfig("pow.cfg","global","DEFAULT_ENCODING")
    encoding = pow.global_conf["DEFAULT_ENCODING"]
    return unicode(instr, encoding)
    
def regex_rules(rules=rule_tuple):
    # also to pluralize
    for line in rules:
        pattern, search, replace = line
        yield lambda word: re.search(pattern, word) and re.sub(search, replace, word)

# the following three functions are taken from:
# http://c2.com/cgi/wiki?MixinsForPython 
# will use them to test mixin of plugin functionalities into models and controllers.
# also see comment to mixin function related to the controvery of mixin vs multiple inheritance.
def mixInClass (base, addition):

    """Mixes in place, i.e. the base class is modified.
    Tags the class with a list of names of mixed members.
    """
    assert not hasattr(base, '_mixed_')
    mixed = []
    for item, val in addition.__dict__.items():
        if not hasattr(base, item):
            setattr(base, item, val)
            mixed.append (item)
    base._mixed_ = mixed



def unMixClass (cla):

    """Undoes the effect of a mixin on a class. Removes all attributes that
    were mixed in -- so even if they have been redefined, they will be
    removed.
    """
    for m in cla._mixed_: #_mixed_ must exist, or there was no mixin
        delattr(cla, m)
    del cla._mixed_



def mixedInClass (base, addition):

    """Same as mixInClass, but returns a new class instead of modifying
    the base.
    """
    class newClass: pass
    newClass.__dict__ = base.__dict__.copy()
    mixIn (newClass, addition)
    return newClass
def mixin(*args):
    """Decorator for mixing in mixins ;) 
        I nkow that there is a BIG debate about mixins vs. multiple inheritance.
        I will try both but personally do not like to have many multi inheritances per class.
           IMO looks ugly. if multi inheritances are also stacked it gets quite copmplex to follow.
        taken from: http://stackoverflow.com/questions/4139508/in-python-can-one-implement-mixin-behavior-without-using-inheritance
        Adapted so that methods already in the Class will not be overwritten.
        Could be chamged semantically to overwrite in the future but then will need to 
        make sure that _meth and __methods are still kept original.
    """
    def inner(cls):
        for a,k in ((a,k) for a in args for k,v in vars(a).items() if callable(v)):
            #print a, type(a)
            #print k, type(k)
            if hasattr(cls, k): 
                print 'method name conflict %s' % (str(k))
            else:
                setattr(cls, k, getattr(a, k))
        return cls
    return inner

def replace_string_in_file( absfilename, origstr, repstr):
    # set correct Appname in pow_router.wsgi
    f = open(os.path.join(absfilename), "r")
    instr = f.read()
    instr = instr.replace(origstr, repstr)
    f.close()
    f = open(os.path.join(absfilename), "w")
    f.write(instr)
    f.close()
    return
    
def plural(noun):
    # the final pluralisation method.
    for rule in regex_rules():
        result = rule(noun)
        if result:
            return result

def pluralize(noun):
    return plural(noun)

def singularize(word):
    # taken from:http://codelog.blogial.com/2008/07/27/singular-form-of-a-word-in-python/
    sing_rules = [lambda w: w[-3:] == 'ies' and w[:-3] + 'y',
              lambda w: w[-4:] == 'ives' and w[:-4] + 'ife',
              lambda w: w[-3:] == 'ves' and w[:-3] + 'f',
              lambda w: w[-2:] == 'es' and w[:-2],
              lambda w: w[-1:] == 's' and w[:-1],
              lambda w: w,
              ]
    word = word.strip()
    singleword = [f(word) for f in sing_rules if f(word) is not False][0]
    return singleword

def check_for_dir( path ):
    ret = False
    #print "check_for_dir(" + os.path.normpath(path) + ")"
    if os.path.isdir( os.path.normpath(path) ):
        ret = True
        #print "is a dir"
    else:
        ret = False
        #print "is NOT a dir"
    return ret


def check_create_dir( path ):
    ret = -1
    #print "checking for " + path +"...\t" ,
    if os.path.isdir( os.path.normpath(path) ):
        print" exists" +"...\t",
        ret = -1
    else:
        os.mkdir( os.path.normpath(path) )
        print " created" +"...\t",
        ret = 1
    print os.path.normpath(path)
    return ret

def check_for_file( path, filename ):
    ret = -1
    if os.path.isfile( os.path.normpath(path + filename) ):
        ret = 1
    else:
        ret = -1
    return ret



def check_create_file( path, filename ):
    ret = -1
    #print "checking for " + os.path.normpath(path + filename) + "...\t" ,
    if os.path.isfile( os.path.normpath(path + filename) ):
        print" exists" +"...\t",
        ret = -1
    else:
        file = open(os.path.normpath(path + filename),"w")
        file.close()
        print " created" +"...\t",
        ret = 1
    print os.path.normpath(path + filename)
    return ret


def check_copy_file( src, dest, force=True, details=False):
    ret = -1
    #print "checking copy of :" + os.path.normpath(src) + "..." ,
    #if os.path.isfile(os.path.normpath(src)):
    #    print "exist\t",
    #else:
    #    print "ERROR: non existent"
    #    sys.exit(-1)
    #print "to " + os.path.normpath(dest)  + "..." ,
    #print "check_copy_file"
    #print src
    #print dest
    if os.path.isfile(os.path.normpath(dest +"/" + src )) and force == False:
        ret = -1
        src_path, src_file = os.path.split(src)
        print " exists ...\t", src_file
        return ret
    else:
        if not check_for_dir(src):
            try:
                shutil.copy(src,dest)
                ret = 1
                print " copied" + "...\t", src
            except IOError, (errno, strerror):
                print " I/O error...(%s): %s. File: %s" % (errno, strerror, src)
                ret = -1
                return ret
        else:
            print " skipped...DIR\t", src

    #print src + " to " + os.path.normpath(dest)
    #src_path, src_file = os.path.split(src)
    #dest_path, dest_file = os.path.split(dest)
    #print src_file
    #print " ---> to ", os.path.join(os.path.relpath(dest_path), dest_file)
    return ret


def create_empty_file( path, filename ):
    file = open(os.path.normpath(path) + filename,"w")
    file.close()


def version_to_string( ver ):
    version = None
    ver = abs(ver)
    if ver < 10:
        version = "0000" + str(ver)
    elif (ver >= 10 and ver < 100):
        version = "000" + str(ver)
    elif (ver >= 100 and ver < 1000):
        version = "00" + str(ver)
    elif (ver >= 1000 and ver < 10000):
        version = "0" + str(ver)
    elif (ver >= 10000 and ver < 100000):
        version = str(ver)
    else:
        version = "99999_max_version_number"
    return version


def readconfig(file, section, option, basepath = None):
    config = ConfigParser.ConfigParser()
    path = ""
    if basepath == None:
        if os.path.exists(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../config/") +  file)):
            path = os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../config/") +  file)
        elif os.path.exists(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"./config/") +  file)):
            path = os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"./config/") +  file)
        else:
            path = os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../config/") +  file)
    else:
        if os.path.exists(os.path.abspath(os.path.join( basepath,"./config/") +  file)):
            path = os.path.abspath(os.path.join( basepath,"./config/") +  file)

    config.read(os.path.normpath( path ))
    option = config.get(section, option)
    return option


def read_db_config( file, env ):
    config = ConfigParser.ConfigParser()
    if os.path.exists(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../config/") +  file)):
        config.read(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../config/") +  file))
    elif os.path.exists(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"./config/") +  file)):
        config.read(os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"./config/") +  file))
    else:
        path = os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)),"../config/") +  file)
        config.read(os.path.normpath( path ))

    opts = ["dialect", "driver", "database", "host", "port", "parameters", "username", "password"]

    dic = {}
    for val in opts:
        dic[val] = config.get(env, str(val) )
    return dic



def op(filename):
    # a short name for os.path.normpath(filename)
    return os.path.normpath(filename)

def get_app_dir():
    #appdir = readconfig("pow.cfg","global","APP_DIR")
    appdir = os.path.abspath( os.path.dirname( __file__ ) + "/../" )
    #print appdir
    return appdir


def get_app_db_conn_str():
    #appdir = readconfig("pow.cfg","global","APP_DIR")
    appdir = get_app_dir()
    return "sqlite:///" + os.path.abspath(appdir + "/db//app.db" )


def get_db_conn_str():
    #env = readconfig("pow.cfg","global","ENV")
    env = pow.global_conf["ENV"]
    #appdir = readconfig( "pow.cfg","global","APP_DIR")
    appdir = get_app_dir()
    #print "APP_DIR: " + appdir
    #print "reading db_conn_str for environment: " + env

    #dic = read_db_config( "db.cfg", env )
    #dic = eval("db."+env)
    dic = getattr(db, env)
    # debug printing
    #for key in dic:
    #    print key + " : " + dic[key]
    if dic["dialect"] == "sqlite":
        db_conn_str = "sqlite:///" + op(appdir + "/db//" + dic["database"]  + ".db")

    else:
        #The URL is a string in the form
        #            dialect+driver://user:password@host/dbname[?key=value..],
        #where dialect is a database name such as mysql, oracle, postgresql, etc., and driver the
        #name of a DBAPI, such as psycopg2, pyodbc, cx_oracle, etc. Alternatively, the URL can be an
        # instance of URL.

        # see all ssqlalchemy db options here :
        # http://www.sqlalchemy.org/docs/core/engines.html#database-engine-options
        db_conn_str = dic["dialect"]
        if dic["driver"] != "":
            db_conn_str += "+" + dic["driver"]
        db_conn_str += "://"
        if dic["username"] != "":
            db_conn_str += dic["username"] + ":" + dic["password"]
        if dic["host"] != "":
            db_conn_str += "@" + dic["host"]
        db_conn_str += "/" + dic["database"]
    return db_conn_str


def load_class( module_name, class_name):
    #print "split:" + str(file.split(".")[0])
    aclass = None
    amodule = load_module(module_name)
    if hasattr(amodule, class_name):
        aclass = eval("amodule." + class_name + "()")
    return aclass

def load_module( module_name ):

    amodule = None
    #print "split:" + str(file.split(".")[0])
    amodule = __import__( module_name , globals(), locals(), [], -1)
    return amodule

def load_func( module_name, class_name, func_name ):
    aclass = load_class( module_name, class_name )
    afunc = None
    if hasattr( aclass, func_name ):
        afunc = eval("aclass." + func_name)
    return afunc

def print_object( obj ):
    print obj
    print " object  - callable? "
    print "---------------------------------"
    for attr in dir(obj):
        print attr +" - " + str ( callable(attr) )

def check_iscallable( obj ):
    isok = callable(eval(obj))
    print "is callable <" + str ( obj )+ "> :" + str ( isok )
    return isok

def dh(instr):
    ostr = instr
    ostr = str.replace("<", "|")
    ostr = str.replace(">", "|")
    return ostr

def print_sorted( sequence_type ):
    for elem in sorted(sequence_type):
        print elem
    return

def table_to_model(tablename):
    return str.capitalize(singularize(str.lower(tablename)))

def model_to_table(modelname):
    return pluralize(str.lower(modelname))

########NEW FILE########
__FILENAME__ = PowObject
import sys, datetime, os, getopt, shutil
import ConfigParser,string
import re

from sqlalchemy import MetaData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.normpath("./"))
import powlib


class PowObject(object):
    """ pow base object class"""
    __engine__= None
    __metadata__ = None
    __session__= None
    
    def dump(sql, *multiparams, **params):
        print sql.compile(dialect=engine.dialect)
    
    def __init__(self):
        PowObject.__engine__= create_engine(powlib.get_db_conn_str())
        PowObject.__metadata__ = MetaData()
        PowObject.__metadata__.bind =  PowObject.__engine__
        PowObject.__metadata__.reflect(PowObject.__engine__)
        PowObject.__session__= sessionmaker()
        PowObject.__session__.configure(bind=PowObject.__engine__)
        
    def dispatch(self):
        print "object:" + str(self) +  "dispatch() method invoked"
        return
        
    def getMetaData(self):
        return PowObject.__metadata__
    
    def getEngine(self):
        return PowObject.__engine__
        
    def getSession(self):
        return PowObject.__session__()
        
    def repr(self):
        return "Not implemented in class: PowObject"
########NEW FILE########
__FILENAME__ = PowTable
import os,sys
import time,datetime
import sqlalchemy
from sqlalchemy import Column
from sqlalchemy.orm import mapper
from sqlalchemy import Text, Sequence, Integer
import datetime
import string

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
import powlib
from PowObject import PowObject

class PowTable(sqlalchemy.Table):
    
    def has_many(self, tablename):
        pass
    
    def belongs_to(self, tablename):
        pass
    
    def many_to_many(self, tablename):
        pass
    
    def append_column_to_db(self, column):
        print dir(column)
        estr = "self.c." + column.name + ".create()"
        print estr
        eval( estr )
    
    def alter_column_name(self, colname, newname):
         eval("self.c." + colname + ".alter(name=\"" + newname + "\")")
         
    def create(self, **kwargs):
        col = Column('created', Text, default=datetime.datetime.now())
        self.append_column( col )
        col = Column('last_updated', Text, default=datetime.datetime.now())
        self.append_column( col )
        col = Column('id', Integer, Sequence(self.name+'_id_seq'), primary_key=True)
        self.append_column( col )
        for elem in self.columns:
            elem.name = string.lower(elem.name)
        sqlalchemy.Table.create(self, **kwargs)
        
    def drop(self, **kwargs):
        sqlalchemy.Table.drop(self, **kwargs)
########NEW FILE########
__FILENAME__ = pow_html_helper
#
# POW Helpers for mako and html
# 
import powlib
import sys, os, os.path
import string
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../config" )))
import pow
import sqlalchemy.types
from powlib import _log

def paginate( list, powdict=None, per_page=3 ):
    """ returns a tupel ( t1 , 2 )
        where     t1 = html for a bootstrap paginator 
        and       t2 = list of results sliced so it fits to the current paginator page.
        
        Always shows     FIRST curent_page +1 +2 +3 +4 LAST
        So if current page =3 it will show
                         FIRST 3 4 5 6 7 LAST
        Example: 
                you give a list of 40 Posts and the current page is 3, per_page is 3
                the the paginator will show:  first 3 4 5 6 7 last
                and the returned list contains the entries 10,11,12 since 
                these are the results that should be displayed on page 3
                You have to loop over the returned list yourself in the according view template.
                see demo blog Post_blog.tmpl for an example
    """
    max_paginators = 4
    # se if we come from a page already.
    if powdict["REQ_PARAMETERS"].has_key("page"):
        page = int(powdict["REQ_PARAMETERS"]["page"])
    else:
        page = 1
    #print " -- page: ", str(page)
    ostr = '<div class="pagination"><ul>'
    link = "#"
    # first link
    ostr += '<li><a href="/post/blog?page=1">First</a></li>' 
    if page > 1:
        # Prev Link
        link = "/post/blog?page=%s" % (str(page-1))
        ostr += '<li><a href="%s">&laquo;</a></li>' % (link)           
    else:
        ostr += '<li><a href="#">&laquo;</a></li>'
    # paginators
    print " -- paginator: len(list) > len(list)/per_page : ", str(len(list)), "  >   ", str(len(list)/per_page)
    
    rest = len(list) % per_page
    if rest > 0:
        # if there is a rest while dividing the list / page (INTEGER) then there is one more page
        # with less then per_page entries that must be added. So + 1 in this case
        real_end =  (len(list)/per_page)+1
    else:
        real_end = (len(list)/per_page)
        
    if page <= max_paginators:
        # make forward pagination page, page +1, page+2  ... and so on
        start = 1
        end = page + max_paginators + 1 
    else:
         # make pagination forward and backwards around page: page-2, page-1 page, 
         # page+1, page+2 (for example)
         start = (page - (max_paginators/2))
         end =  (page + (max_paginators/2))+1
         
    for elem in range(start, end):
        link = "/post/blog?page=%s" % (str(elem))
        if elem == page:
            ostr += '<li class="active"><a href="%s">%s</a></li>' % (link,str(elem))
        else:
            ostr += '<li><a href="%s">%s</a></li>' % (link,str(elem))
        if elem >= real_end:
            break
    
    
    # next link
    if page < real_end:
        link = "/post/blog?page=%s" % (str(page+1))
        ostr += '<li><a href="%s">&raquo;</a></li>' % (link)
    else:
        ostr += '<li><a href="#">&raquo;</a></li>'
   
    # Last link
    link = "/post/blog?page=%s" % (str(real_end))
    ostr += '<li><a href="%s">Last (%s)</a></li>' % (link, str(real_end))
    
    #finish
    ostr += "</ul></div>"
    
    if page == 0:
        return (ostr, list[0:per_page*(page+1)])
    else:
        return (ostr, list[(page-1)*per_page:per_page*(page)])
    #return ostr
    
def css_include_tag(base, cssfile):
    return css_tag(base,cssfile)

def css_tag(cssfile, base="/static/css/"):
    retstr='<link href="%s%s" rel="stylesheet">' % (base, cssfile)
    return retstr

def std_css_tag():
    retstr="""
    <link href="/static/css/bs/bootstrap.css" rel="stylesheet">
    <link href="/static/css/bs/bootstrap-responsive.css" rel="stylesheet">
    """
    return retstr    

def test_helper():
    """
    Just a test to see in html inline if helpers work.
    """
    return "test_helper() worked"

def get_user_logonname(powdict):
    return "hans"
    
def generate_hidden(model, hidden_list=None):
    ostr = ""
    if hidden_list == None:
        hidden_list = powlib.hidden_list
    for colname in model.getColumns():
        if colname in hidden_list:
            ostr += '<input type="hidden" name="%s" value="%s"/>' % (colname, model.get(colname))
    
    return ostr

def is_logged_on(powdict):
    """
    returns True if a user is logged on.
    This is semantically equivalent to session.user != 0
    Session user is in powdict
    """
    session = powdict["SESSION"]
    if session['user.id'] == 0:
        return False
    else:
        return True    

def smart_list(model, colname = None):
    """
     Generates the right html tags to display the model attribute content in the model.list view
     according to the model.attribute's column type
        Basically:
            default, text and VArchar   =>      plain type=text
            binary and blob             =>      if colname == image     =>      <img
                                                if colname == other     =>      plain text
            integer, Text               =>      plain text
    """
    ostr = ""
    curr_type = type(model.__table__.columns[colname].type)
    if curr_type == type(sqlalchemy.types.BLOB()) or curr_type == type(sqlalchemy.types.BINARY()):
        if string.lower(colname) == pow.global_conf["DEFAULT_IMAGE_NAME"]:
            if model.get(colname) != None and model.get(colname) != "None":
                ostr += '<img src="%s" alt="%s"/>' % ( pow.global_conf["STD_BINARY_PATH"] + model.get(colname),  model.get(colname))
                _log( "smart_list: curr_type: BINARY file is: %s " % (model.get(colname)), "DEBUG")
            else:
                ostr += "None"
    else:
        #_log( "smart_list: curr_type: %s" % (curr_type), "DEBUG" )
        ostr += model.get(colname)
    return ostr
    
def smart_form_input( modelname = None, colname = None, value = "", accept = "", options_dict = None ):
    """
        Generates the right form input for the given model.column type.
        Basically:
            default, text and VArchar   =>      <input type=text>
            binary and blob             =>      <input type=file>
            Text                        =>      <textarea>
            
    """
    
    colname = string.lower(colname)
    input_first = '<label for="%s">%s:</label>' % (colname, colname)
    if modelname == None:
        # No model given, so always generate a standard text type or the given type input html field
        if type == None:
            input_first += "<input type='text' name='%s' value='%s'>" % (colname, value)
        else:
            input_first += "<input type='%s' name='%s' value='%s'>" % (type, colname, value)
    else:
        # model given, so create the right input-type according to the models datatype
        # the field is the same as the given name. So type of model.name determines the input-type
        mod = powlib.load_class(string.capitalize(modelname), string.capitalize(modelname))
        statement = 'type(mod.__table__.columns["%s"].type)' % (colname)
        curr_type = eval(statement)
        print curr_type
        if curr_type == type(sqlalchemy.types.INTEGER()) or curr_type == type(sqlalchemy.types.VARCHAR()):
            input_first += "<input type='text' name='%s' onClick='this.select();' onFocus='this.select();' value='%s'>" % (colname, value)
        elif curr_type == type(sqlalchemy.types.TEXT()):
            input_first += '<textarea name="%s" onClick="this.select();" onFocus="this.select();" class="input-xxlarge" rows="15">%s</textarea>' % (colname, value)
        elif curr_type == type(sqlalchemy.types.BLOB()) or curr_type == type(sqlalchemy.types.BINARY()):
            if string.lower(colname) == pow.global_conf["DEFAULT_IMAGE_NAME"]:
                input_first += '<input name="%s" type="file" size="50" maxlength="%s" accept="image/*">' % (colname, pow.global_conf["MAX_FILE_UPLOAD"])
            elif string.lower(colname) == pow.global_conf["DEFAULT_VIDEO_NAME"]:
                input_first += '<input name="%s" type="file" size="50" maxlength="%s" accept="video/*">' % (colname, pow.global_conf["MAX_FILE_UPLOAD"])
            elif string.lower(colname) == pow.global_conf["DEFAULT_AUDIO_NAME"]:
                input_first += '<input name="%s" type="file" size="50" maxlength="%s" accept="audio/*">' % (colname, pow.global_conf["MAX_FILE_UPLOAD"])
            elif string.lower(colname) == pow.global_conf["DEFAULT_TEXT_NAME"]:
                input_first += '<input name="%s" type="file" size="50" maxlength="%s" accept="text/*">' % (colname, pow.global_conf["MAX_FILE_UPLOAD"])
        else:   
            input_first += "<ERROR in smart_form_input()>"
    
    
    return input_first
    
def create_link(text=None):
    if text == None:
        retstr = '<i class="icon-plus"></i>&nbsp;<a href="./create">create</a>' 
    else:
        retstr = '<i class="icon-plus"></i>&nbsp;<a href="./create">%s</a>' % (text)
    return retstr
    
def delete_link( model, text=None ):
    if text == None:
        retstr = '<i class="icon-remove"></i>&nbsp;<a href="./delete?id=%s">delete</a>' % (model)
    else:
        retstr = '<i class="icon-remove"></i>&nbsp;<a href="./delete?id=%s">%s</a>' % (model,text)
    return retstr

def show_link( model, text=None):
    if text == None:
        retstr ='<i class="icon-eye-open"></i>&nbsp;<a href="./show?id=%s">show</a>' % (model)
    else:
        retstr = '<i class="icon-eye-open"></i>&nbsp;<a href="./show?id=%s">%s</a>' % (model,text)
    return retstr
    
def edit_link(model_id, text=None):
    if text == None:
        retstr = '<i class="icon-edit"></i>&nbsp;<a href="./edit?id=%s">edit</a>' % (model_id)
    else:
        retstr = '<i class="icon-edit"></i>&nbsp;<a href="./edit?id=%s">%s</a>' % (model_id,text)
    return retstr
        
def flash_message(powdict):
    ostr = ""
    if powdict["FLASHTEXT"] != "":
    	ostr += '<div class="alert alert-%s">' % (powdict["FLASHTYPE"])
    	ostr += '%s<button class="close" data-dismiss="alert">x</button></div>' % ( powdict["FLASHTEXT"] )
    return ostr

def add_html_options(options_dict=None):
    ostr = ""
    if options_dict != None:
        for key in options_dict:
            # handle options_dict as dict (had problems with Mako before 0.72 ??)
            ostr += '%s="%s"' % (key, options_dict[key])
            # handle options_dict as list of tupels. So enable this with Mako before 0.72
            #ostr += "%s=\"%s\"" % (key[0],key[1])
    return ostr  

def mail_to(email):
    mailto_first = "<a href=\"mailto:%s\"" % (email)
    mailto_last = ">%s</a>" % (email)
    mailto_first += add_html_options(options_dict)
    mailto = mailto_first + mailto_last
    return mailto


def link_to(link, text, options_dict=None):
    linkto_first = "<a href=\"%s\"" % (link)
    linkto_last = ">%s</a>" % (text)
    linkto = ""
    # Add html-options if there are any
    linkto_first += add_html_options(options_dict)
    linkto = linkto_first + linkto_last
    return linkto

def start_javascript():
    ostr = """
     <script type="text/javascript">
    """
    return ostr

def end_javascript():
    ostr = """
     </script>
    """
    return ostr
def enable_ajax():
    return enable_xml_http_post()
    
def enable_xml_http_post():
    script = """
    <!-- Start AJAX Test, see: http://stackoverflow.com/questions/336866/how-to-implement-a-minimal-server-for-ajax-in-python -->
    
    function xml_http_post(url, data, callback) {
        var req = false;
        try {
            // Firefox, Opera 8.0+, Safari
            req = new XMLHttpRequest();
        }
        catch (e) {
            // Internet Explorer
            try {
                req = new ActiveXObject("Msxml2.XMLHTTP");
            }
            catch (e) {
                try {
                    req = new ActiveXObject("Microsoft.XMLHTTP");
                }
                catch (e) {
                    alert("Your browser does not support AJAX!");
                    return false;
                }
            }
        }
        
        req.open("POST", url, true);
        req.onreadystatechange = function() {
            if (req.readyState == 4) {
                callback(req);
            }
        }
        req.send(data);
    }

    """
    
    return script
########NEW FILE########
__FILENAME__ = pow_web_lib
#
# Date: 24.1.2012
# Author: khz
# module with the shared functions of pow_router and simple_server
#

import sys
import os
sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "./lib" )))
import urllib
import re
import cgi
import string
import sqlalchemy.types
import powlib

#
# session management default values.
#
session_opts = {
    'session.type': 'file',
    'session.data_dir': './sessions',
    'session.cookie_expires': True,
    'session.auto': True
}

def log( instr ):
    print >> environ['wsgi.errors'], instr
    return

def set_text_or_binary_form_data(model, powdict, bin_data_path="/public/img"):
    """
        iterates over all parameters in the current requests and updates
        the according model fields.
        Handles text and binary data coorectly. Text is directly stored in the
        models attribute. For binary data the file is stored in the given path and 
        the link is stored in the model attribute.
        If binary_data is expected depends on the models.attribute type, NOT on the submitted
        data.
        @param model:            the Model
        @param powdict:          the powdict of the current request
        @param bin_data_path:    path where the binary data will be stored.
        @returns:                the updated model. You need to call model.update 
                                 (or model.create) afterwards, yourself to really update the db.
    """ 
    dict = powdict["REQ_PARAMETERS"]
    for key in dict:
        curr_type = model.get_column_type(key)
        if curr_type == type(sqlalchemy.types.BLOB()) or curr_type == type(sqlalchemy.types.BINARY()):
            #ofiledir  = os.path.normpath(bin_data_path)
            #print "key: ", key
            if form_has_binary_data( key, dict, bin_data_path):
                # if form contains file data AND file could be written, update model
                model.set(key, dict[key].filename )   
            else:
                # dont update model
                print " ##### ________>>>>>>>   BINARY DATA but couldnt update model"
        else:
            model.set(key, dict[key])
    return model

def get_form_binary_data( form_fieldname, dict, ofiledir ):
    return form_has_binary_data( form_fieldname, dict, ofiledir )

def form_has_binary_data( form_fieldname, dict, ofiledir ):
    """ safely checks if a given form field has binary data attached to it
        and safes it into the given filename. Often used for html form <input type="file" ...>
    """
    if dict.has_key(form_fieldname):
        try:
            #print dir(dict[form_fieldname])
            #print dict[form_fieldname].__dict__.viewkeys()
            data = dict[form_fieldname].file.read()
            #ofiledir = os.path.normpath("./public/img/blog/")
            ofilename = os.path.join(ofiledir, dict[form_fieldname].filename)
            ofile = open( ofilename , "wb")
            ofile.write(data)
            ofile.close()
            return True
        except AttributeError:
            # no image data
            return False
    return False

def pre_route(path_info):
    # description:
    # Syntax:     r"URL-Pattern"    :    "Redirection-URL"
    # r"^/user/new*" : "/user/list",
    #    => matches any line starting with /user/new and redirecting it to /user/list
    #    r"^/([w]+)/([w]+)*" : "/user/list",
    #     => matches any /action/controller combination not matched by any of the preceeding ones
    #     and redirecting it to /user/list. you can also access the groups (by parantheses) by match.group(1)..
    # other example:
    # r"^/user/do_login*" : "/user/list",
    # r"^/user/new\w*" : "/user/list",

    routes = {
        r"^/([w]+)/([w]+)*" : "/user/list",
        r"." : "/app/welcome"
    }
    #print routes
    match = None
    for pattern in routes:
        match = re.search(pattern, inp)
        if match:
            print "matched: ", pattern, " --> ", routes[pattern]
            break
        p = None
        match = None
    
    
def show_environ( environ ):
    ostr = ""
    ostr +=  "<h1>Sorted Keys an Values in <tt>environ</tt></h1>" 
    
    sorted_keys = environ.keys()
    sorted_keys.sort()
    
    for key in sorted_keys:
        ostr += str(key) + " = " + str(environ.get(key)) + "<br>"
        
    return ostr

def show_environ_cli( environ ):
    ostr = ""
    ostr +=  "Sorted Keys an Values in environ:" 
    
    sorted_keys = environ.keys()
    sorted_keys.sort()
    
    for key in sorted_keys:
        ostr += str(key) + " = " + str(environ.get(key)) + powlib.newline
        
    return ostr

def get_http_get_parameters( environ):
    #
    # parameters are in query sting
    #
    plist = []
    pstr = ""
    pstr = environ.get("QUERY_STRING")
    if pstr != "":
        plist = pstr.split("&")        
    odict = {}
    for elem in plist:
        key,val = string.split(elem,"=")
        odict[key]= val
    return odict

   
def get_http_post_parameters_new( environ ):
    # see: http://www.wsgi.org/en/latest/specifications/handling_post_forms.html?highlight=post
    # form.getvalue('name'):
    assert is_post_request(environ)
    input = environ['wsgi.input']
    post_form = environ.get('wsgi.post_form')
    print "in get_http_post_parameters_new( environ ):"
    if (post_form is not None
        and post_form[0] is input):
        return post_form[2]
    # This must be done to avoid a bug in cgi.FieldStorage
    environ.setdefault('QUERY_STRING', '')
    fs = cgi.FieldStorage(fp=input,
                          environ=environ,
                          keep_blank_values=1)
    return fs




def get_http_post_parameters( environ ):
    instr = None
    plist = None
    odict = {}
    instr= environ['wsgi.input'].read(int(environ['CONTENT_LENGTH']))
    plist = string.split(instr,"&")
    for elem in plist:
        key,val = string.split(elem,"=")
        newval = val.replace("+", " ")
        val = urllib.unquote_plus(val)
        print "in (get_http_post_parameters)    val=",val , "  newval=", newval
        odict[key] = newval
    return odict

def is_post_request( environ ):
    if environ['REQUEST_METHOD'].upper() != 'POST':
        return False
    else:
        return True
        #content_type = environ.get('CONTENT_TYPE', 'application/x-www-form-urlencoded')
        #return (content_type.startswith('application/x-www-form-urlencoded' or content_type.startswith('multipart/form-data')))

def is_get_request( environ ):
    if environ['REQUEST_METHOD'].upper() != 'GET':
        return False
    else:
        return True
    
def get_controller_and_action(pi="/"):
    # converts a path_info: /user/list/1/2/3/4
    # into al list ol = ['4', '3', '2', '1', 'list', 'user']
    # where the controller is always the last element and the action the one before that (len(ol)-1) and len(ol)-2)
    ol = []
    l = []
    l= os.path.split(pi)
    ol.append(l[1])
    while l[0] != "/":
        #print "l[0]:" + l[0]
        #print "l[1]:" + l[1]
        l = os.path.split(l[0])
        ol.append(l[1])
        print ol
    
    pl = []
    nicedict = {}
    nicedict["controller"]=ol[len(ol)-1]
    nicedict["action"]=ol[len(ol)-2]
    for c in range(0,len(ol)-2):
        pl.append(ol[c])
    nicedict["parameters"]=pl
    
    return nicedict

#
# reference: http://pylonsbook.com/en/1.1/the-web-server-gateway-interface-wsgi.html
# also see: http://svn.python.org/projects/python/branches/release25-maint/Lib/cgitb.py
import cgitb
import sys
from StringIO import StringIO

class Middleware(object):
    def __init__(self, app):
        self.app = app

    def format_exception(self, exc_info):
        dummy_file = StringIO()
        # see: ViewClass in cgitb.Hook
        # here: http://wstein.org/home/wstein/www/home/mhansen/moin-1.7.2/src/MoinMoin/support/cgitb.py
        hook = cgitb.Hook(file=dummy_file)
        hook(*exc_info)
        return [dummy_file.getvalue()]

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except:
            exc_info = sys.exc_info()
            start_response(
            '500 Internal Server Error,',
            [('content-type', 'text/html')],
            exc_info 
            )
            return self.format_exception(exc_info)

########NEW FILE########
__FILENAME__ = 00001_app
#
#
# This file was autogenerated by python_on_wheels.
# But YOU CAN EDIT THIS FILE SAFELY
# It will not be overwtitten by python_on_wheels
# unless you force it with the -f or --force option
# 


# date created: 	2012-07-10

from sqlalchemy import *
from sqlalchemy.schema import CreateTable
from sqlalchemy import event, DDL

import sys
import os

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
import powlib
from PowTable import PowTable
from BaseMigration import BaseMigration

class Migration(BaseMigration):
    table_name="apps"
    table = None
        
    def up(self):
            #
            # here is where you define your table (Format see example below)
            # the columns below are just examples.
            # Remember that PoW automatically adds an id and a timestamp column (ID,TIMESTAMP)
        self.table = PowTable(self.table_name, self.__metadata__,
            
            Column('currentversion', Integer ),
            Column('name', String(50)),
            Column('path', String(50)),
            Column('maxversion', Integer )
            
            #Column('user_id', Integer, ForeignKey('users.id'))
        )
        self.create_table()
        #print CreateTable(self.table)
        
    def down(self):
        self.drop_table()
########NEW FILE########
__FILENAME__ = 00002_versions
#
#
# This file was autogenerated by python_on_wheels.
# But YOU CAN EDIT THIS FILE SAFELY
# It will not be overwtitten by python_on_wheels
# unless you force it with the -f or --force option
# 

# date created: 	2012-07-10

from sqlalchemy import *
from sqlalchemy.schema import CreateTable
from sqlalchemy import event, DDL

import sys
import os

sys.path.append( os.path.abspath(os.path.join( os.path.dirname(os.path.abspath(__file__)), "../lib" )))
import powlib
from PowTable import PowTable
from BaseMigration import BaseMigration

class Migration(BaseMigration):
    table_name="versions"
    table = None
        
    def up(self):
            #
            # here is where you define your table (Format see example below)
            # the columns below are just examples.
            # Remember that PoW automatically adds an id and a timestamp column (ID,TIMESTAMP)
        self.table = PowTable(self.table_name, self.__metadata__,
            
            Column('filename', String(60)),
            Column('version', Integer),
            Column('comment', String(200))
            
            #Column('user_id', Integer, ForeignKey('users.id'))
        )
        self.create_table()
        #print CreateTable(self.table)
        
    def down(self):
        self.drop_table()
########NEW FILE########
