__FILENAME__ = errorcodes
#!/usr/bin/env python
"""Scans MongoDB source tree for potential error codes and creates multiple outputs"""

generateCSV = 'no'
generateRST = 'no'
generateJSON = 'no'
debug = False
save_to_mongo = False

import os
import sys
import re
import ConfigParser

try: 
	import pymongo
	pymongo_flag = True
except:
	sys.stderr.write("pymongo unavailable, continuing\n")
	pymongo_flag = False

config_file = 'errorcodes.conf'

config = ConfigParser.SafeConfigParser()
config_flag = False
config_files = [ config_file, 'bin/{}'.format(config_file)]
try:
	config.read(config_files)
	config_flag = True
except:
	sys.exit("Could not read config file, exiting\n")

if config_flag == True:
	sourceroot = config.get('errorcodes','source')
	resultsRoot = config.get('errorcodes', 'outputDir')
	errorsTitle = config.get('errorcodes', 'Title')
	if (config.has_option('errorcodes','Format')):
		errorsFormat = config.get('errorcodes', 'Format')
	if (config.has_option('errorcodes','generateCSV')):
		generateCSV = config.get('errorcodes','generateCSV')
	if (config.has_option('errorcodes','generateJSON')):
		generateJSON = config.get('errorcodes','generateJSON')
	if (config.has_option('errorcodes','generateRST')):
		generateRST = config.get('errorcodes', 'generateRST')
	if (config.has_option('mongodb', 'persistence')):
		if (config.get('mongodb','persistence') == 'insert'):
			save_to_mongo = True
		elif (config.get('mongodb','persistence') == 'update'):
			sys.exit("Fatal, updating not supported")
else:
	sys.exit("No configuration data present, exiting\n")
	
if save_to_mongo == True:
#	why candygram? because there's only so many times you can use mongo and
#	database before going mad.  Alt: cf. Blazing Saddles
	fields = ['database','collection','user','password','port']
	for field in fields:
		if config.has_option('mongodb',field):
			candygram[field]  = config.get('mongodb',field)
	if candygram['database'] == '':
		sys.exit("Fatal: you told me to save to a database but did not configure one.");
	if candygram['collection'] == '':
		sys.exit("Fatal: you told me to save to a database but did not configure a collection.");

default_domain = "\n\n.. default-domain:: mongodb\n\n"

sys.path.append(sourceroot+"/buildscripts")

# we only need to scan the mongo source tree not 3rd party
product_source = sourceroot + '/src/mongo'

# get mongodb/buildscripts/utils.py 
import utils


assertNames = [ "uassert" , "massert", "fassert", "fassertFailed" ]

severityTexts = dict({
		'fassert':'Abort', 
		'fasserted' : 'Abort',
		'fassertFailed': 'Abort',
		'massert':'Info', 
		'masserted': 'Info',
		'msgasserted': 'Info',
		'wassert':'Warning',
		'wasserted': 'Warning',
		})

exceptionTexts = dict({
	'uassert': 'UserException',
	'uasserted': 'UserException',
	'UserException' : 'UserException',
	'dbexception': 'DBException',
	'DBException': 'DBException',
	'DBexception': 'DBException',
	'MsgException': 'MsgException',
	'MSGException': 'MsgException',
	'MsgAssertionException': 'MsgAssertionException',
	})
	
# codes is legacy errocodes.py
codes = []
# messages is our real structure
messages = {}

def assignErrorCodes():
    cur = 10000
    for root in assertNames:
        for x in utils.getAllSourceFiles():
            print( x )
            didAnything = False
            fixed = ""
            for line in open( x ):
                s = line.partition( root + "(" )
                if s[1] == "" or line.startswith( "#define " + root):
                    fixed += line
                    continue
                fixed += s[0] + root + "( " + str( cur ) + " , " + s[2]
                cur = cur + 1
                didAnything = True
            if didAnything:
                out = open( x , 'w' )
                out.write( fixed )
                out.close()


def readErrorCodes():   
    """Open each source file in sourceroot and scan for potential error messages."""
    sys.stderr.write("Analyzing source tree: {}\n".format(sourceroot))
    quick = [ "assert" , "Exception"]

    ps = [ re.compile( "(([wum]asser(t|ted))) *\(( *)(\d+) *,\s*(\"\S[^\"]+\S\")\s*,?.*" ) ,
           re.compile( "(([wum]asser(t|ted))) *\(( *)(\d+) *,\s*([\S\s+<\(\)\"]+) *,?.*" ) ,
           re.compile( '((msgasser(t|ted))) *\(( *)(\d+) *, *(\"\S[^,^\"]+\S\") *,?' ) ,
           re.compile( '((msgasser(t|ted)NoTrace)) *\(( *)(\d+) *, *(\"\S[^,^\"]+\S\") *,?' ) ,
           re.compile( "((fasser(t|ted))) *\(( *)(\d+)()" ) ,  
           re.compile( "((DB|User|Msg|MsgAssertion)Exceptio(n))\(( *)(\d+) *,? *(\S+.+\S) *,?" ),
           re.compile( "((fassertFailed)()) *\(( *)(\d+)()" ),
           re.compile( "(([wum]asser(t|ted)))\s*\(([^\d]*)(\d+)\s*,?()"),
           re.compile( "((msgasser(t|ted)))\s*\(([^\d]*)(\d+)\s*,?()"),
           re.compile( "((msgasser(t|ted)NoTrace))\s*\(([^\d]*)(\d+)\s*,?()"),
           
           ]

    bad = [ re.compile( "\sassert *\(" ) ]
    arr=[]
    for x in utils.getAllSourceFiles(arr,product_source):
    	if (debug == True):
			sys.stderr.write("Analyzing: {}\n".format(x))
        needReplace = [False]
        lines = []
        lastCodes = [0]
        lineNum = 1
        
        stripChars = " " + "\n"
        sourcerootOffset = len(sourceroot)

        
        for line in open( x ):

            found = False
            for zz in quick:
                if line.find( zz ) >= 0:
                    found = True
                    break

            if found:
                
                for p in ps:               

                    def repl( m ):
                        m = m.groups()
                        severity = m[0]
                        start = m[0]
                        spaces = m[3]
                        code = m[4]
                        message = m[5]
                        codes.append( ( x , lineNum , line , code, message, severity ) )
                        if x.startswith(sourceroot):
							fn = x[sourcerootOffset+1:].rpartition("/2")[2]

                        msgDICT = {
							'id': code, 
							'parsed':message, 
							'message':message,
							'assert':severity,
							'severity': returnSeverityText(severity),
							'uresp':'',
							'sysresp':'', 
							'linenum':lineNum, 
							'file':fn,
							'src': line.strip(stripChars),
							'altered': 0
							}
                        messages[int(code)] = msgDICT

                        return start + "(" + spaces + code

                    line = re.sub( p, repl, line )
            
            lineNum = lineNum + 1

def returnSeverityText(s):
	if not s:
		return ""
	elif s in severityTexts:
		result = severityTexts[s]
	elif s in exceptionTexts:
		result = exceptionTexts[s]
	else:
		result = s
	return result


def getNextCode( lastCodes = [0] ):
    highest = [max(lastCodes)]
    def check( fileName , lineNum , line , code ):
        code = int( code )
        if code > highest[0]:
            highest[0] = code
    readErrorCodes( check )
    return highest[0] + 1

def checkErrorCodes():
    seen = {}
    errors = []
    def checkDups( fileName , lineNum , line , code ):
        if code in seen:
            print( "DUPLICATE IDS" )
            print( "%s:%d:%s %s" % ( fileName , lineNum , line.strip() , code ) )
            print( "%s:%d:%s %s" % seen[code] )
            errors.append( seen[code] )
        seen[code] = ( fileName , lineNum , line , code )
    readErrorCodes( checkDups,False )
    return len( errors ) == 0 

def getBestMessage( err , start ):
    #print(err + "\n")
    err = err.partition( start )[2]
    if not err:
        return ""
    err = err.partition( "\"" )[2]
    if not err:
        return ""
    err = err.rpartition( "\"" )[0]
    if not err:
        return ""
    return err
    
def genErrorOutput():
    """Sort and iterate through codes printing out error codes and messages in RST format."""
    sys.stderr.write("Generating RST files\n");
    separatefiles = False
    if errorsFormat == 'single':
        errorsrst = resultsRoot + "/errors.txt"
        if os.path.exists(errorsrst ):
            i = open(errorsrst , "r" ) 
        out = open( errorsrst , 'wb' )
        sys.stderr.write("Generating single file: {}\n".format(errorsrst))
        titleLen = len(errorsTitle)
        out.write(":orphan:\n")
        out.write("=" * titleLen + "\n")
        out.write(errorsTitle + "\n")
        out.write("=" * titleLen + "\n")
        out.write(default_domain);
    elif errorsFormat == 'separate':
        separatefiles = True
    else:
        raise Exception("Unknown output format: {}".format(errorsFormat))
    
    prev = ""
    seen = {}
    
    sourcerootOffset = len(sourceroot)
    stripChars = " " + "\n"
    
#    codes.sort( key=lambda x: x[0]+"-"+x[3] )
    codes.sort( key=lambda x: int(x[3]) )
    for f,l,line,num,message,severity in codes:
        if num in seen:
            continue
        seen[num] = True

        if f.startswith(sourceroot):
            f = f[sourcerootOffset+1:]
        fn = f.rpartition("/")[2]
        url = ":source:`" + f + "#L" + str(l) + "`"
        
        if separatefiles:
           outputFile = "{}/{:d}.txt".format(resultsRoot,int(num))
           out = open(outputFile, 'wb')
           out.write(default_domain)
           sys.stderr.write("Generating file: {}\n".format(outputFile))
           
        out.write(".. line: {}\n\n".format(line.strip(stripChars)))
        out.write(".. error:: {}\n\n".format(num))
        if message != '':
           out.write("   :message: {}\n".format(message.strip(stripChars)))
        else:
           message = getBestMessage(line,str(num)).strip(stripChars)
           if message != '':
              out.write("   :message: {}\n".format(message))
        if severity:
           if severity in severityTexts:
              out.write("   :severity: {}\n".format(severityTexts[severity]))
           elif severity in exceptionTexts:
              out.write("   :throws: {}\n".format(exceptionTexts[severity]))
           else:
              out.write("   :severity: {}\n".format(severity))
        
        out.write("   :module: {}\n".format(url) )
        if separatefiles:
           out.write("\n")
           out.close()

    if separatefiles==False:    
        out.write( "\n" )
        out.close()
    
def genErrorOutputCSV():
	"""Parse through codes array and generate a csv file."""
	errorsCSV = "{}/errors.csv".format(resultsRoot)
	sys.stderr.write("Writing to {}\n".format(errorsCSV))
	if os.path.exists(errorsCSV):
		i=open(errorsCSV,"r");
	
	out = open(errorsCSV, 'wb')
	out.write('"Error","Text","Module","Line","Message","Severity"' + "\n")
	
	prev = ""
	seen = {}
	
	stripChars = " " + "\n" + '"'

	
	codes.sort( key=lambda x: int(x[3]) )
	for f,l,line,num,message,severity in codes:
		if num in seen:
			continue
		seen[num] = True
		
		if f.startswith( "./"):
			f=f[2:]
			fn = f.rpartition("/")[2]
		
		out.write('"{}","{}","{}","{}","{}","{}"'.format(num, getBestMessage(line , str(num)).strip(stripChars),f,l,message.strip(stripChars),severity))
		
		out.write("\n")
	
	out.close()
	
def writeToMongo():
	"""Pipe the messages array into mongodb"""
	sys.stderr.write("Saving to db.messages.errors, will not check for duplicates!")
	from  pymongo import Connection
	connection = Connection()
	db = connection['messages']
	errorcodes = db['errors']
#	errorcodes.insert(messages)
	for errCode in messages.keys():
		sys.stderr.write('Inserting code: {}\n'.format(errCode))
		result = errorcodes.insert(messages[errCode])
		sys.stderr.write('Result: {}\n'.format(result))
#	for k in messages:
#		print("{}\t{}".format(k,messages[k]))
#		errorcodes.insert(k,messages[k])
		
	#for key in messages.keys()
#		val= 'foo'
#		print("key({})\tvalue({})\n".format(key,val))
	

if __name__ == "__main__":
	readErrorCodes()
	if (generateRST == 'yes'):
		genErrorOutput()
	else:
		sys.stderr.write("Not generating RST files\n");
	if (generateCSV == 'yes'):
		genErrorOutputCSV()
	else:
		sys.stderr.write("Not generating CSV file\n");
	if (generateJSON== 'yes'):
		import json
		outputFile = "{}/errorcodes.json".format(resultsRoot)
		out = open(outputFile, 'wb')
		sys.stderr.write("Generating JSON file: {}\n".format(outputFile))
		out.write(json.dumps(messages))
		out.close()
	else:
		sys.stderr.write("Not generating JSON file\n");

	if save_to_mongo == True:
		writeToMongo()
	else:
		sys.stderr.write("Not inserting/updating to Mongo\n");		
########NEW FILE########
__FILENAME__ = bootstrap
import os
import subprocess
import argparse
import yaml
import sys

project_root = os.path.abspath(os.path.dirname(__file__))

master_conf = os.path.join(project_root, 'config', 'build_conf.yaml')

with open(master_conf, 'r') as f:
    conf = yaml.safe_load(f)

repo = 'git://github.com/{0}.git'.format(conf['git']['remote']['tools'])

buildsystem = conf['paths']['buildsystem']

sys.path.append(os.path.join(buildsystem, 'bin'))

def bootstrap_init():
    if os.path.exists(buildsystem):
        import bootstrap_helper

        cmd = []
        cmd.append(['git', 'reset', '--quiet', '--hard', bootstrap_helper.reset_ref])
        cmd.append(['git', 'pull', '--quiet', 'origin', 'master'])

        for c in cmd:
            subprocess.call(c, cwd=buildsystem)

        print('[bootstrap]: updated git repository.')

def bootstrap_base():
    if not os.path.exists(buildsystem):
        subprocess.call([ 'git', 'clone', repo, buildsystem])
        print('[bootstrap]: created buildsystem directory.')

    import bootstrap_helper

    bootstrap_helper.bootstrap(build_tools_path=buildsystem, conf_path=master_conf)
    print('[bootstrap]: initialized buildsystem.')

    subprocess.call(['make', 'noop', '--silent', '-i'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('op', nargs='?', choices=['clean', 'setup', 'safe'], default='setup')
    ui = parser.parse_args()

    if ui.op == 'clean':
        try:
            import bootstrap_helper
            bootstrap_helper.clean_buildsystem(buildsystem, conf['build']['paths']['output'])
        except ImportError:
            exit('[bootstrap]: Buildsystem not installed.')
    elif ui.op == 'safe':
        bootstrap_base()
    else:
        bootstrap_init()
        bootstrap_base()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# MongoDB documentation build configuration file, created by
# sphinx-quickstart on Mon Oct  3 09:58:40 2011.
#
# This file is execfile()d with the current directory set to its containing dir.

import sys
import os
import datetime

from sphinx.errors import SphinxError

try:
    project_root = os.path.join(os.path.abspath(os.path.dirname(__file__)))
except NameError:
    project_root = os.path.abspath(os.getcwd())

sys.path.append(project_root)

from bootstrap import buildsystem

sys.path.append(os.path.join(project_root, buildsystem, 'sphinxext'))
sys.path.append(os.path.join(project_root, buildsystem, 'bin'))

from utils.config import get_conf
from utils.project import get_versions, get_manual_path
from utils.serialization import ingest_yaml, ingest_yaml_list
from utils.structures import BuildConfiguration
from utils.strings import dot_concat

conf = get_conf()

conf.paths.projectroot = project_root
intersphinx_libs = ingest_yaml_list(os.path.join(conf.paths.builddata, 'intersphinx.yaml'))
sconf = BuildConfiguration(os.path.join(conf.paths.builddata, 'sphinx-local.yaml'))

# -- General configuration ----------------------------------------------------

needs_sphinx = '1.0'

extensions = [
    'sphinx.ext.extlinks',
    'sphinx.ext.todo',
    'mongodb',
    'directives',
    'intermanual',
]

locale_dirs = [ os.path.join(conf.paths.projectroot, conf.paths.locale) ]
gettext_compact = False

templates_path = ['.templates']
exclude_patterns = []

source_suffix = '.txt'

master_doc = sconf.master_doc
language = 'en'
project = sconf.project
copyright = u'2011-{0}'.format(datetime.date.today().year)
version = conf.version.branch
release = conf.version.release

rst_epilog = '\n'.join([
    '.. |branch| replace:: ``{0}``'.format(conf.git.branches.current),
    '.. |copy| unicode:: U+000A9',
    '.. |year| replace:: {0}'.format(datetime.date.today().year),
    '.. |ent-build| replace:: MongoDB Enterprise',
    '.. |hardlink| replace:: {0}/{1}'.format(conf.project.url, conf.git.branches.current)
])

pygments_style = 'sphinx'

extlinks = {
    'issue': ('https://jira.mongodb.org/browse/%s', '' ),
    'wiki': ('http://www.mongodb.org/display/DOCS/%s', ''),
    'api': ('http://api.mongodb.org/%s', ''),
    'source': ('https://github.com/mongodb/mongo/blob/master/%s', ''),
    'docsgithub' : ( 'http://github.com/mongodb/docs/blob/{0}/%s'.format(conf.git.branches.current), ''),
    'hardlink' : ( 'http://docs.mongodb.org/{0}/%s'.format(conf.git.branches.current), ''),
    'manual': ('http://docs.mongodb.org/manual%s', ''),
    'ecosystem': ('http://docs.mongodb.org/ecosystem%s', ''),
    'meta-driver': ('http://docs.mongodb.org/meta-driver/latest%s', ''),
    'mms': ('https://mms.mongodb.com/help%s', ''),
    'mms-hosted': ('https://mms.mongodb.org/help-hosted%s', ''),
    'about': ('http://www.mongodb.org/about%s', '')
}

## add `extlinks` for each published version.
for i in conf.git.branches.published:
    extlinks[i] = ( ''.join([ conf.project.url, '/', i, '%s' ]), '' )

intersphinx_mapping = {}
for i in intersphinx_libs:
    intersphinx_mapping[i['name']] = ( i['url'], os.path.join(conf.paths.projectroot,
                                                              conf.paths.output,
                                                              i['path']))

languages = [
    ("ar", "Arabic"),
    ("cn", "Chinese"),
    ("cs", "Czech"),
    ("de", "German"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("hu", "Hungarian"),
    ("id", "Indonesian"),
    ("it", "Italian"),
    ("jp", "Japanese"),
    ("ko", "Korean"),
    ("lt", "Lithuanian"),
    ("pl", "Polish"),
    ("pt", "Portuguese"),
    ("ro", "Romanian"),
    ("ru", "Russian"),
    ("tr", "Turkish"),
    ("uk", "Ukrainian")
]

# -- Options for HTML output ---------------------------------------------------

html_theme = sconf.theme.name
html_theme_path = [ os.path.join(buildsystem, 'themes') ]
html_title = conf.project.title
htmlhelp_basename = 'MongoDBdoc'

html_logo = sconf.logo
html_static_path = sconf.paths.static

html_copy_source = False
html_use_smartypants = True
html_domain_indices = True
html_use_index = True
html_split_index = False
html_show_sourcelink = False
html_show_sphinx = True
html_show_copyright = True

manual_edition_path = '{0}/{1}/{2}'.format(conf.project.url,
                                           conf.git.branches.current,
                                           sconf.theme.book_path_base)

html_theme_options = {
    'branch': conf.git.branches.current,
    'pdfpath': dot_concat(manual_edition_path, 'pdf'),
    'epubpath': dot_concat(manual_edition_path, 'epub'),
    'manual_path': get_manual_path(conf),
    'translations': languages,
    'language': language,
    'repo_name': sconf.theme.repo,
    'jira_project': sconf.theme.jira,
    'google_analytics': sconf.theme.google_analytics,
    'project': sconf.theme.project,
    'version': version,
    'version_selector': get_versions(conf),
    'stable': conf.version.stable,
    'sitename': sconf.theme.sitename,
    'nav_excluded': sconf.theme.nav_excluded,
}

html_sidebars = sconf.sidebars

# -- Options for LaTeX output --------------------------------------------------

pdfs = []
try:
    if tags.has('latex'):
        pdf_conf_path = os.path.join(conf.paths.builddata, 'pdfs.yaml')
        if os.path.exists(pdf_conf_path):
            pdfs = ingest_yaml_list(pdf_conf_path)
        else:
            raise SphinxError('[WARNING]: skipping pdf builds because of missing {0} file'.format(pdf_conf_path))
except NameError:
    pass

latex_documents = []
for pdf in pdfs:
    _latex_document = ( pdf['source'], pdf['output'], pdf['title'], pdf['author'], pdf['class'])
    latex_documents.append( _latex_document )

latex_preamble_elements = [ r'\DeclareUnicodeCharacter{FF04}{\$}',
                            r'\DeclareUnicodeCharacter{FF0E}{.}',
                            r'\PassOptionsToPackage{hyphens}{url}',
                            r'\usepackage{upquote}',
                            r'\pagestyle{plain}',
                            r'\pagenumbering{arabic}' ]
latex_elements = {
    'preamble': '\n'.join(latex_preamble_elements),
    'pointsize': '10pt',
    'papersize': 'letterpaper'
}

latex_paper_size = 'letter'
latex_use_parts = False
latex_show_pagerefs = True
latex_show_urls = 'footnote'
latex_domain_indices = False
latex_logo = None
latex_appendices = []

# -- Options for manual page output --------------------------------------------

man_page_definitions = []
try:
    if tags.has('man'):
        man_page_conf_path = os.path.join(conf.paths.builddata, 'manpages.yaml')
        if os.path.exists(man_page_conf_path):
            man_page_definitions = ingest_yaml_list(man_page_conf_path)
        else:
            raise SphinxError('[WARNING]: skipping man builds because of missing {0} file'.format(man_page_conf_path))
except NameError:
    pass
man_pages = []
for mp in man_page_definitions:
    man_pages.append((mp['file'], mp['name'], mp['title'], mp['authors'], mp['section']))

# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = conf.project.title
epub_author = u'MongoDB Documentation Project'
epub_publisher = u'MongoDB, Inc.'
epub_copyright = copyright
epub_theme = 'epub_mongodb'
epub_tocdup = True
epub_tocdepth = 3
epub_language = language
epub_scheme = 'url'
epub_identifier = ''.join([conf.project.url, '/', conf.git.branches.current])
epub_exclude_files = []

epub_pre_files = []
epub_post_files = []


# put it into your conf.py
def setup(app):
    # disable versioning for speed
    from sphinx.builders.gettext import I18nBuilder
    I18nBuilder.versioning_method = 'none'

    def doctree_read(app, doctree):
        if not isinstance(app.builder, I18nBuilder):
            return
        from docutils import nodes
        from sphinx.versioning import add_uids
        list(add_uids(doctree, nodes.TextElement))
    app.connect('doctree-read', doctree_read)

########NEW FILE########
__FILENAME__ = bootstrap
import os
import subprocess
import argparse
import yaml
import sys

project_root = os.path.abspath(os.path.dirname(__file__))

master_conf = os.path.join(project_root, 'config', 'build_conf.yaml')

with open(master_conf, 'r') as f:
    conf = yaml.safe_load(f)

repo = 'git://github.com/{0}.git'.format(conf['git']['remote']['tools'])

buildsystem = conf['paths']['buildsystem']

sys.path.append(os.path.join(buildsystem, 'bin'))

def bootstrap_init():
    if os.path.exists(buildsystem):
        import bootstrap_helper

        cmd = []
        cmd.append(['git', 'reset', '--quiet', '--hard', bootstrap_helper.reset_ref])
        cmd.append(['git', 'pull', '--quiet', 'origin', 'master'])

        for c in cmd:
            subprocess.call(c, cwd=buildsystem)

        print('[bootstrap]: updated git repository.')

def bootstrap_base():
    if not os.path.exists(buildsystem):
        subprocess.call([ 'git', 'clone', repo, buildsystem])
        print('[bootstrap]: created buildsystem directory.')

    import bootstrap_helper

    bootstrap_helper.init_fabric(buildsystem, master_conf)
    bootstrap_helper.bootstrap()
    print('[bootstrap]: initialized buildsystem.')

    subprocess.call(['make', 'noop', '--silent', '-i'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('op', nargs='?', choices=['clean', 'setup', 'safe'], default='setup')
    ui = parser.parse_args()

    if ui.op == 'clean':
        try:
            import bootstrap_helper
            bootstrap_helper.clean_buildsystem(buildsystem, conf['build']['paths']['output'])
        except ImportError:
            exit('[bootstrap]: Buildsystem not installed.')
    elif ui.op == 'safe':
        bootstrap_base()
    else:
        bootstrap_init()
        bootstrap_base()

if __name__ == '__main__':
    main()

########NEW FILE########
