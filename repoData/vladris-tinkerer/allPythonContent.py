__FILENAME__ = build
'''
    Build utility for Tinkerer blog
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Builds the blog with all themes and either generates the theme previews or
    opens each theme in the browser.

    :copyright: Copyright 2011-2013 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import argparse
import os
import shutil
import sys
from tinkerer import cmdline



DEFAULT_THEME = "flat"

OTHER_THEMES = ["modern5", "minimal5", "responsive", "dark"]



def update_conf(theme):
    '''
    Updates conf.py with the given theme
    '''
    CONF = "conf.py"

    lines = open(CONF).readlines()
    lines = ["html_theme = '%s'\n" % (theme, ) if "html_theme =" in line
                else line for line in lines]
    open(CONF, "w").writelines(lines)



def update_index(theme):
    '''
    Updates index_<THEME>.hml files to point to the correct static dir
    '''
    index = os.path.join("blog", "html", "index_%s.html" % (theme,))

    text = open(index, encoding="utf-8").read()
    text = text.replace("_static", "_static_%s" % (theme, ))

    open(index, "w").write(text)



def move_theme(theme):
    '''
    Moves the build output of the given theme
    '''
    src = os.path.join("blog", "html")
    dest = os.path.join("themes", theme)

    print("Moving %s to %s" % (src, dest))
    shutil.move(src, dest)



def open_all():
    '''
    Opens all themes in browser
    '''
    for theme in OTHER_THEMES:
        os.startfile(os.path.join("themes", theme, "index.html"))
    os.startfile("index.html")



def copy_previews():
    '''
    Copies themes to preview directory for Tinkerer website
    '''
    for theme in OTHER_THEMES:
        shutil.move(
            os.path.join("themes", theme, "index.html"), 
            os.path.join("blog", "html", "index_%s.html" % (theme, )))
        shutil.move(
            os.path.join("themes", theme, "_static"),
            os.path.join("blog", "html", "_static_%s" % (theme, )))
        update_index(theme)       



def parse(argv):
    '''
    Parses command line arguments
    '''
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-o", "--open", action="store_true", 
        help="open all themes in browser")
    group.add_argument("-p", "--preview", action="store_true",
        help="generates previews for all themes")

    return parser.parse_args(argv)



def build_all_themes():
    '''
    Builds all themes
    '''
    # remove previous theme build output if any
    shutil.rmtree("themes", True)

    for theme in OTHER_THEMES:
        print("Building theme %s" % (theme,))
        update_conf(theme)
        cmdline.build()
        move_theme(theme)

    update_conf(DEFAULT_THEME)
    cmdline.build()



command = parse(sys.argv[1:])

if command.open:
    build_all_themes()
    open_all()   
elif command.preview:
    build_all_themes()
    copy_previews()

########NEW FILE########
__FILENAME__ = conf
import tinkerer
import tinkerer.paths        

project = 'Tinkerer'                   
tagline = 'Blogging for Pythonistas'                  
description = 'Tinkerer is a Python blogging engine/static website generator powered by Sphinx'
author = 'Vlad Riscutia'
copyright = '2011-2013, ' + author         
website = 'http://tinkerer.me/'                              

disqus_shortname = 'tinkerer'                                   
html_favicon = 'tinkerer.ico'           
html_theme = 'flat'
rss_service = 'http://feeds.feedburner.com/tinkerer'

extensions = ['tinkerer.ext.blog', 'tinkerer.ext.disqus', 'hidemail'] 
templates_path = ['_templates']
html_static_path = ['_static', tinkerer.paths.static]
html_theme_path = [tinkerer.paths.themes]                 
exclude_patterns = ["drafts/*", "_templates/*"]

doc_sidebar = ['reference.html', 'searchbox.html']

html_sidebars = {
    '**': ['recent.html', 
           'get_tinkerer.html', 
           'searchbox.html', 
           'sphinx.html', 
           'get_involved.html',
           'themes.html'],
    'doc/command_line': doc_sidebar,
    'doc/deploying': doc_sidebar,
    'doc/extensions': doc_sidebar,
    'doc/internals': doc_sidebar,
    'doc/more_tinkering': doc_sidebar,
    'doc/theming': doc_sidebar,
    'doc/tinkering': doc_sidebar,
    'pages/documentation': doc_sidebar,
}

source_suffix = tinkerer.source_suffix
master_doc = tinkerer.master_doc
version = tinkerer.__version__
release = tinkerer.__version__
html_title = project
html_use_index = False
html_show_sourcelink = False
html_add_permalinks = None


########NEW FILE########
__FILENAME__ = hidemail
'''
    hidemail
    ~~~~~~~~

    Email obfuscation role
    
    The obfuscation code was taken from
    
        http://pypi.python.org/pypi/bud.nospam
        
    Email obfuscation role for Sphinx:
    
        http://pypi.python.org/pypi/sphinxcontrib-email

    :copyright: Copyright 2011 by Kevin Teague
    :copyright: Copyright 2012 by Christian Jann
    :license: BSD license
'''
from docutils import nodes
import re
from tinkerer.ext.uistr import UIStr

try:
    maketrans = ''.maketrans
except AttributeError:
    # fallback for Python 2
    from string import maketrans


rot_13_trans = maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
)


def rot_13_encrypt(line):
    """Rotate 13 encryption.

    """
    line = line.translate(rot_13_trans)
    line = re.sub('(?=[\\"])', r'\\', line)
    line = re.sub('\n', r'\n', line)
    line = re.sub('@', r'\\100', line)
    line = re.sub('\.', r'\\056', line)
    line = re.sub('/', r'\\057', line)
    return line


def js_obfuscated_text(text):
    """
    ROT 13 encryption with embedded in Javascript code to decrypt
    in the browser.
    """
    return """<noscript>(%s)</noscript>
              <script type="text/javascript">
              <!--
                  document.write("%s".replace(/[a-zA-Z]/g,
                  function(c){
                    return String.fromCharCode(
                    (c<="Z"?90:122)>=(c=c.charCodeAt(0)+13)?c:c-26);}));
              -->
              </script>""" % (UIStr.MAIL_HIDDEN_BY_JAVASCRIPT, rot_13_encrypt(text))


def js_obfuscated_mailto(email, displayname=None):
    """
    ROT 13 encryption within an Anchor tag w/ a mailto: attribute
    """
    if not displayname:
        displayname = email
    return js_obfuscated_text("""<a href="mailto:%s">%s</a>""" % (
        email, displayname
    ))


def email_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Role to obfuscate e-mail addresses.
    """
    try:
        # needed in Python 2
        text = text.decode("utf-8").encode("utf-8")
    except AttributeError:
        pass
    
    # Handle addresses of the form "Name <name@domain.org>"
    if '<' in text and '>' in text:
        name, email = text.split('<')
        email = email.split('>')[0]
    elif '(' in text and ')' in text:
        name, email = text.split('(')
        email = email.split(')')[0]
    else:
        name = text
        email = name

    obfuscated = js_obfuscated_mailto(email, displayname=name)
    node = nodes.raw('', obfuscated, format="html")
    return [node], []


def setup(app):
    app.add_role('email', email_role)
   

########NEW FILE########
__FILENAME__ = cmdline
'''
    Tinkerer command line
    ~~~~~~~~~~~~~~~~~~~~~

    Automates the following blog operations:

    setup - to create a new blog
    build - to clean build blog
    post - to create a new post
    page - to create a new page

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import argparse
from datetime import datetime
import os
import shutil
import sphinx
import tinkerer
from tinkerer import draft, output, page, paths, post, writer


def setup():
    '''
    Sets up a new blog in the current directory.
    '''
    # it is a new blog if conf.py doesn't already exist
    new_blog = writer.setup_blog()

    output.filename.info("conf.py")
    if new_blog:
        output.write.info("Your new blog is almost ready!")
        output.write.info("You just need to edit a couple of lines in %s" %
                          (os.path.relpath(paths.conf_file), ))
    else:
        output.write.info("Done")


def build():
    '''
    Runs a clean Sphinx build of the blog.
    '''
    # clean build directory
    if os.path.exists(paths.blog):
        shutil.rmtree(paths.blog)

    flags = ["sphinx-build"]
    # silence Sphinx if in quiet mode
    if output.quiet:
        flags.append("-q")
    flags += ["-d", paths.doctree, "-b", "html", paths.root, paths.html]

    # build always prints "index.html"
    output.filename.info("index.html")

    # copy some extra files to the output directory
    if os.path.exists("_copy"):
        shutil.copytree("_copy/", paths.html)

    return sphinx.main(flags)


def create_post(title, date, template):
    '''
    Creates a new post with the given title or makes an existing file a post.
    '''
    move = os.path.exists(title)

    if move:
        new_post = post.move(title, date)
    else:
        new_post = post.create(title, date, template)

    output.filename.info(new_post.path)
    if move:
        output.write.info("Draft moved to post '%s'" % new_post.path)
    else:
        output.write.info("New post created as '%s'" % new_post.path)


def create_page(title, template):
    '''
    Creates a new page with the given title or makes an existing file a page.
    '''
    move = os.path.exists(title)

    if move:
        new_page = page.move(title)
    else:
        new_page = page.create(title, template)

    output.filename.info(new_page.path)
    if move:
        output.write.info("Draft moved to page '%s'" % new_page.path)
    else:
        output.write.info("New page created as '%s'" % new_page.path)


def create_draft(title, template):
    '''
    Creates a new draft with the given title or makes an existing file a draft.
    '''
    move = os.path.exists(title)

    if move:
        new_draft = draft.move(title)
    else:
        new_draft = draft.create(title, template)

    output.filename.info(new_draft)
    if move:
        output.write.info("File moved to draft '%s'" % new_draft)
    else:
        output.write.info("New draft created as '%s'" % new_draft)


def preview_draft(draft_file):
    '''
    Rebuilds the blog, including the given draft.
    '''
    if not os.path.exists(draft_file):
        raise Exception("Draft named '%s' does not exist" % draft_file)

    # promote draft
    preview_post = post.move(draft_file)

    try:
        # rebuild
        result = build()
    finally:
        # demote post back to draft
        draft.move(preview_post.path)

    return result


def main(argv=None):
    '''
    Parses command line and executes required action.
    '''
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--setup", action="store_true",
                       help="setup a new blog")
    group.add_argument("-b", "--build", action="store_true", help="build blog")
    group.add_argument(
        "-p", "--post", nargs=1,
        help="create a new post with the title POST (if a file named POST "
        "exists, it is moved to a new post instead)")
    group.add_argument(
        "--page", nargs=1,
        help="create a new page with the title PAGE (if a file named PAGE "
        "exists, it is moved to a new page instead)")
    group.add_argument(
        "-d", "--draft", nargs=1,
        help="creates a new draft with the title DRAFT (if a file named DRAFT "
        "exists, it is moved to a new draft instead)")
    group.add_argument(
        "--preview", nargs=1,
        help="rebuilds the blog, including the draft PREVIEW, without "
        "permanently promoting the draft to a post")
    group.add_argument(
        "-v", "--version", action="store_true",
        help="display version information")

    parser.add_argument(
        '-t', '--template', action='store', default=None,
        help="specify a body template, defaults to page or post",
    )
    parser.add_argument(
        "--date", nargs=1,
        help="optionally specify a date as 'YYYY/mm/dd' for the post, "
        "useful when migrating blogs; can only be used together with "
        "-p/--post")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-q", "--quiet", action="store_true", help="quiet mode")
    group.add_argument(
        "-f", "--filename", action="store_true",
        help="output filename only - useful to pipe Tinkerer commands")

    command = parser.parse_args(argv)

    output.init(command.quiet, command.filename)

    # tinkerer should be run from the blog root unless in setup mode or -v
    if (not command.setup and not command.version
            and not os.path.exists(paths.conf_file)):
        output.write.error("Tinkerer must be run from your blog root "
                           "(directory containing 'conf.py')")
        return -1

    post_date = None
    if command.date:
        # --date only works with --post
        if not command.post:
            output.write.error("Can only use --date with -p/--post.")
            return -1

        try:
            post_date = datetime.strptime(command.date[0], "%Y/%m/%d")
        except:
            output.write.error(
                "Invalid post date: format should be YYYY/mm/dd"
            )
            return -1

    if command.template:
        if not os.path.exists(os.path.join(paths.templates, command.template)):
            output.write.error(
                "The specified template does not exist. "
                " Make sure the template is placed inside the _templates"
                " subdirectory of your blog.")
            return -1

    if command.setup:
        setup()
    elif command.build:
        return build()
    elif command.post:
        create_post(command.post[0], post_date, command.template)
    elif command.page:
        create_page(command.page[0], command.template)
    elif command.draft:
        create_draft(command.draft[0], command.template)
    elif command.preview:
        preview_draft(command.preview[0])
    elif command.version:
        output.write.info("Tinkerer version %s" % tinkerer.__version__)
    else:
        parser.print_help()

    return 0

########NEW FILE########
__FILENAME__ = draft
'''
    draft
    ~~~~~

    Handles creating drafts.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENCE file
'''
import os
import re
import shutil
import tinkerer
from tinkerer import master, paths, utils, writer


def create(title, template=None):
    '''
    Creates a new post draft.
    '''
    name = utils.name_from_title(title)
    template = template or paths.post_template

    path = os.path.join(
        utils.get_path(paths.root, "drafts"),
        name + tinkerer.source_suffix,
    )

    if os.path.exists(path):
        raise Exception("Draft '%s' already exists at '%s" %
                        (title, path))

    writer.render(template, path,
                  {"title":      title,
                   "content":    "",
                   "author":     "default",
                   "categories": "none",
                   "tags":       "none"})

    return path


def move(path):
    '''
    Demotes given file to draft.
    '''
    # get dirname and filename
    dirname, filename = os.path.split(path)

    # get docname without extension
    docname = os.path.splitext(filename)[0]

    draft = os.path.join(utils.get_path(paths.root, "drafts"), filename)

    # move file
    shutil.move(path, draft)

    # check if file is a post or a page
    if os.path.basename(dirname) == "pages":
        docname = "pages/" + docname
    else:
        match = re.match(r".*(?P<y>\d{4}).(?P<m>\d{2}).(?P<d>\d{2})$", dirname)
        if not match:
            return draft
        g = match.group
        docname = "/".join([g("y"), g("m"), g("d"), docname])

    # remove file from TOC
    master.remove_doc(docname)

    return draft

########NEW FILE########
__FILENAME__ = aggregator
'''
    aggregator
    ~~~~~~~~~~

    Aggregates multiple posts into single pages.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import copy
from tinkerer.ext.uistr import UIStr


def make_aggregated_pages(app):
    '''
    Generates aggregated pages.
    '''
    env = app.builder.env
    posts_per_page = app.config.posts_per_page

    # get post groups
    groups = [env.blog_posts[i:i+posts_per_page]
              for i in range(0, len(env.blog_posts), posts_per_page)]

    # for each group
    for i, posts in enumerate(groups):
        # initialize context
        context = {
            "prev": {},
            "next": {},
            "posts": []
        }

        # add posts to context
        for post in posts:
            # deepcopy metadata for each post
            metadata = copy.deepcopy(env.blog_metadata[post])
            context["posts"].append(metadata)

        # handle navigation
        if i == 0:
            # first page doesn't have prev link and its title is "Home"
            pagename = "index"
            context["prev"] = None
            context["title"] = UIStr.HOME
        else:
            # following pages prev-link to previous page (titled as "Newer")
            pagename = "page%d" % (i + 1)
            context["prev"]["title"] = UIStr.NEWER
            context["prev"]["link"] = (
                "index.html" if i == 1 else "page%d.html" % i
            )
            context["title"] = UIStr.PAGE_FMT % (i + 1)

        if i == len(groups) - 1:
            # last page doesn't have next link
            context["next"] = None
        else:
            # other pages next-link to following page (titled as "Older")
            context["next"]["title"] = UIStr.OLDER
            context["next"]["link"] = "page%d.html" % (i + 2)

        context["archive_title"] = UIStr.BLOG_ARCHIVE

        yield (pagename, context, "aggregated.html")

########NEW FILE########
__FILENAME__ = author
'''
    author
    ~~~~~~

    Post author extension.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
from sphinx.util.compat import Directive


class AuthorDirective(Directive):
    '''
    Author directive. The directive is not rendered, just stored in the
    metadata and passed to the templating engine.
    '''
    required_arguments = 0
    optional_arguments = 100
    has_content = False

    def run(self):
        '''
        Called when parsing the document.
        '''
        env = self.state.document.settings.env

        # store author in metadata
        author = " ".join(self.arguments)
        if author == "default":
            author = env.config.author
        env.blog_metadata[env.docname].author = author

        return []

########NEW FILE########
__FILENAME__ = blog
'''
    blog
    ~~~~

    Master blog extension.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
from tinkerer.ext import (aggregator, author, filing, html5, metadata, patch,
                          readmore, rss, uistr)
import gettext


def initialize(app):
    '''
    Initializes extension after environment is initialized.
    '''
    # ensure website config value ends with "/"
    if not app.config.website[-1] == "/":
        app.config.website += "/"

    # initialize other components
    metadata.initialize(app)
    filing.initialize(app)

    # localization
    languages = [app.config.language] if app.config.language else None

    locale_dir = ""
    try:
        from pkg_resources import resource_filename
    except ImportError:
        resource_filename = None

    if resource_filename is not None:
        try:
            locale_dir = resource_filename(__name__, "/locale")
        except NotImplementedError:
            # resource_filename doesn't work with non-egg zip files
            pass

    app.t = gettext.translation(
        "tinkerer",
        locale_dir,
        languages=languages,
        fallback=True)
    app.t.install()

    # initialize localized strings
    uistr.UIStr(app)


def source_read(app, docname, source):
    '''
    Processes document after source is read.
    '''
    metadata.get_metadata(app, docname)


def env_updated(app, env):
    '''
    Processes data after environment is updated (all docs are read).
    '''
    metadata.process_metadata(app, env)


def html_page_context(app, pagename, templatename, context, doctree):
    '''
    Passes data to templating engine.
    '''
    metadata.add_metadata(app, pagename, context)
    rss.add_rss(app, context)


def collect_additional_pages(app):
    '''
    Generates additional pages.
    '''
    for name, context, template in rss.generate_feed(app):
        yield (name, context, template)

    for name, context, template in filing.make_tag_pages(app):
        yield (name, context, template)

    for name, context, template in filing.make_category_pages(app):
        yield (name, context, template)

    for name, context, template in aggregator.make_aggregated_pages(app):
        yield (name, context, template)

    for name, context, template in filing.make_archive(app):
        yield (name, context, template)


def html_collect_pages(app):
    '''
    Collect html pages and emit event
    '''
    for name, context, template in collect_additional_pages(app):
        # emit event
        app.emit("html-collected-context", name, template, context)
        yield (name, context, template)


def html_collected_context(app, name, template, context):
    '''
    Patches HTML in aggregated pages
    '''
    if template == "aggregated.html":
        patch.patch_aggregated_metadata(context)


def setup(app):
    '''
    Sets up the extension.
    '''
    # new config values
    app.add_config_value("tagline", "My blog", True)
    app.add_config_value("description", "My blog", True)
    app.add_config_value("author", "Winston Smith", True)
    app.add_config_value("rss_service", None, True)
    app.add_config_value("rss_generate_full_posts", False, True)
    app.add_config_value("website", "http://127.0.0.1/blog/html/", True)
    app.add_config_value("posts_per_page", 10, True)
    # added here for consistency, slug_word_separator is used by Tinkerer
    # command line and not really needed by the Sphinx environment
    app.add_config_value("slug_word_separator", "_", True)
    app.add_config_value("rss_max_items", 0, True)

    # new directives
    app.add_directive("author", author.AuthorDirective)
    app.add_directive("comments", metadata.CommentsDirective)
    app.add_directive("tags",
                      filing.create_filing_directive("tags"))
    app.add_directive("categories",
                      filing.create_filing_directive("categories"))
    app.add_directive("more", readmore.InsertReadMoreLink)

    # create a new Sphinx event which gets called when we generate aggregated
    # pages
    app._events["html-collected-context"] = "pagename, templatename, context"

    # event handlers
    app.connect("builder-inited", initialize)
    app.connect("source-read", source_read)
    app.connect("env-updated", env_updated)
    app.connect("html-page-context", html_page_context)
    app.connect("html-collect-pages", html_collect_pages)
    app.connect("html-collected-context", html_collected_context)

    # monkey-patch Sphinx html translator to emit proper HTML5
    html5.patch_translator()

########NEW FILE########
__FILENAME__ = disqus
'''
    disqus
    ~~~~~~

    Handler for `comments` directive using Disqus.
    Disqus shortname must be provided in `conf.py` as `disqus_shortname`.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''

# flake8: noqa

'''
Disqus JS script file.
'''
DISQUS_SCRIPT = "_static/disqus.js"


def create_thread(disqus_shortname, identifier):
    '''
    Returns JS code to create a new Disqus thread.
    '''
    return str(
'<div id="disqus_thread"></div>'
'<script type="text/javascript">'
'    var disqus_shortname = "%s";'
'    var disqus_identifier = "%s";'
'    disqus_thread();'
'</script>'
'<noscript>Please enable JavaScript to view the '
'   <a href=\"http://disqus.com/?ref_noscript\">comments powered by Disqus.</a>'
'</noscript>' % (disqus_shortname, identifier))


def enable_count(disqus_shortname):
    '''
    Returns JS code required to enable comment counting on a page.
    '''
    return str(
'<script type="text/javascript">'
'    var disqus_shortname = "%s";'
'    disqus_count();'
'</script>' 
            % disqus_shortname)



def get_count(link, identifier):
    '''
    Returns HTML required by Disqus to retrieve comment count.
    '''
    return str('<a href="%s#disqus_thread" data-disqus-identifier="%s">%s</a>' % 
            (link, identifier, "Leave a comment"))



def add_disqus_block(app, pagename, templatename, context, doctree):
    '''
    Adds Disqus to page.
    '''
    # return if no shortname was provided
    if not app.config.disqus_shortname:
        return

    env = app.builder.env

    # append disqus.js if not already in context
    if DISQUS_SCRIPT not in context["script_files"]:
        context["script_files"].append(DISQUS_SCRIPT)

    # if page is blog post and has comments
    if pagename in env.blog_metadata and env.blog_metadata[pagename].comments:
        context["comments"] = create_thread(app.config.disqus_shortname, pagename)

        # store code required to retrieve comment count for this post in metadata
        env.blog_metadata[pagename].comment_count = get_count(
                "%s%s.html" % (app.config.website,
                                env.blog_metadata[pagename].link),
                pagename)

    # just enable comment counting on the page
    else:
        context["comment_enabler"] = enable_count(app.config.disqus_shortname)



def setup(app):
    '''
    Sets up Disqus comment handler.
    '''
    # disqus_shortname contains shortname provided to Disqus
    app.add_config_value("disqus_shortname", None, True)

    # connect event
    app.connect("html-page-context", add_disqus_block)


########NEW FILE########
__FILENAME__ = filing
'''
    filing
    ~~~~~~

    Handles post filing by date, caregories and tags.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
from sphinx.util.compat import Directive
from tinkerer import utils
from tinkerer.ext.uistr import UIStr


def create_filing_directive(name):
    class FilingDirective(Directive):
        '''
        Filing directive used to groups posts. The directive is not rendered,
        just stored in the metadata and passed to the templating engine.
        '''
        required_arguments = 0
        optional_arguments = 100
        has_content = False

        def run(self):
            '''
            Called when parsing the document.
            '''
            env = self.state.document.settings.env

            for item in " ".join(self.arguments).split(","):
                item = item.strip()
                if item == "none":
                    continue

                if not item:
                    env.warn(env.docname,
                             "Empty string in '%s' directive" % (name,))
                    continue

                if item not in env.filing[name]:
                    env.filing[name][item] = []
                env.filing[name][item].append(env.docname)
                env.blog_metadata[env.docname].filing[name].append(
                    (utils.name_from_title(item), item))

            return []

    return FilingDirective


def initialize(app):
    '''
    Initializes tags and categories.
    '''
    app.builder.env.filing = {"tags": dict(), "categories": dict()}


def make_archive_page(env, title, pagename, post_filter=None):
    '''
    Generates archive page with given title by applying the given filter to
    all posts and aggregating results by year.
    '''
    context = {"title": title}
    context["years"] = dict()

    for post in filter(post_filter, env.blog_posts):
        year = env.blog_metadata[post].date.year
        if year not in context["years"]:
            context["years"][year] = []
        context["years"][year].append(env.blog_metadata[post])

    return (pagename, context, "archive.html")


def make_archive(app):
    '''
    Generates blog archive including all posts.
    '''
    yield make_archive_page(
        app.builder.env,
        UIStr.BLOG_ARCHIVE,
        "archive")


def make_tag_pages(app):
    '''
    Generates archive pages for each tag.
    '''
    env = app.builder.env
    for tag in env.filing["tags"]:
        yield make_archive_page(
            env,
            UIStr.TAGGED_WITH_FMT % tag,
            "tags/" + utils.name_from_title(tag),
            lambda post: post in env.filing["tags"][tag])


def make_category_pages(app):
    '''
    Generates archive pages for each category.
    '''
    env = app.builder.env
    for category in env.filing["categories"]:
        yield make_archive_page(
            env,
            UIStr.FILED_UNDER_FMT % category,
            "categories/" + utils.name_from_title(category),
            lambda post: post in env.filing["categories"][category])

########NEW FILE########
__FILENAME__ = html5
"""
    html5
    ~~~~~

    Monkey-patch Sphinx HTML translator to emit HTML5.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file.
"""
from sphinx.writers.html import HTMLTranslator


def visit_desc_addname(self, node):
    '''
    Similar to Sphinx but using a <span> node instead of <tt>.
    '''
    self.body.append(self.starttag(node, 'span', '', CLASS='descclassname'))


def depart_desc_addname(self, node):
    '''
    Similar to Sphinx but using a <span> node instead of <tt>.
    '''
    self.body.append('</span>')


def visit_desc_name(self, node):
    '''
    Similar to Sphinx but using a <span> node instead of <tt>.
    '''
    self.body.append(self.starttag(node, 'span', '', CLASS='descname'))


def depart_desc_name(self, node):
    '''
    Similar to Sphinx but using a <span> node instead of <tt>.
    '''
    self.body.append('</span>')


def visit_literal(self, node):
    '''
    Similar to Sphinx but using a <span> node instead of <tt>.
    '''
    self.body.append(self.starttag(node, 'span', '',
                                   CLASS='docutils literal'))
    self.protect_literal_text += 1


def depart_literal(self, node):
    '''
    Similar to Sphinx but using a <span> node instead of <tt>.
    '''
    self.protect_literal_text -= 1
    self.body.append('</span>')


def patch_translator():
    '''
    Monkey-patch Sphinx translator to emit proper HTML5.
    '''
    HTMLTranslator.visit_desc_addname = visit_desc_addname
    HTMLTranslator.depart_desc_addname = depart_desc_addname
    HTMLTranslator.visit_desc_name = visit_desc_name
    HTMLTranslator.depart_desc_name = depart_desc_name
    HTMLTranslator.visit_literal = visit_literal
    HTMLTranslator.depart_literal = depart_literal

########NEW FILE########
__FILENAME__ = metadata
'''
    metadata
    ~~~~~~~~

    Blog metadata extension. The extension extracts and computes metadata
    associated with blog posts/pages and stores it in the environment.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import re
import datetime
from functools import partial
from sphinx.util.compat import Directive
from babel.core import Locale
from babel.dates import format_date
import tinkerer
from tinkerer.ext.uistr import UIStr
from tinkerer.utils import name_from_title


def initialize(app):
    '''
    Initializes metadata in environment.
    '''
    app.builder.env.blog_metadata = dict()


class Metadata:
    '''
    Metadata associated with each post/page.
    '''
    num = 1

    def __init__(self):
        '''
        Initializes metadata with default values.
        '''
        self.is_post = False
        self.is_page = False
        self.title = None
        self.link = None
        self.date = None
        self.formatted_date = None
        self.formatted_date_short = None
        self.body = None
        self.author = None
        self.filing = {"tags": [], "categories": []}
        self.comments, self.comment_count = False, False
        self.num = Metadata.num
        Metadata.num += 1


class CommentsDirective(Directive):
    '''
    Comments directive. The directive is not rendered by this extension, only
    added to the metadata, so plug-in comment handlers can be used.
    '''
    required_arguments = 0
    optional_arguments = 0
    has_content = False

    def run(self):
        '''
        Called when parsing the document.
        '''
        env = self.state.document.settings.env

        # mark page as having comments
        env.blog_metadata[env.docname].comments = True

        return []


def get_metadata(app, docname):
    '''
    Extracts metadata from a document.
    '''
    env = app.builder.env
    language = app.config.language
    locale = Locale.parse(language) if language else Locale('en', 'US')
    format_ui_date = partial(
        format_date, format=UIStr.TIMESTAMP_FMT, locale=locale)
    format_short_ui_short = partial(
        format_date, format=UIStr.TIMESTAMP_FMT_SHORT, locale=locale)

    env.blog_metadata[docname] = Metadata()
    metadata = env.blog_metadata[docname]

    # if it's a page
    if docname.startswith("pages/"):
        metadata.is_page = True
        return

    # posts are identified by ($YEAR)/($MONTH)/($DAY) paths
    match = re.match(r"\d{4}/\d{2}/\d{2}/", docname)

    # if not post return
    if not match:
        return

    metadata.is_post = True
    metadata.link = docname
    metadata.date = datetime.datetime.strptime(match.group(), "%Y/%m/%d/")

    # we format date here instead of inside template due to localization issues
    # and Python2 vs Python3 incompatibility
    metadata.formatted_date = format_ui_date(metadata.date)
    metadata.formatted_date_short = format_short_ui_short(metadata.date)


def process_metadata(app, env):
    '''
    Processes metadata after all sources are read - the function determines
    post and page ordering, stores doc titles and adds "Home" link to page
    list.
    '''
    # get ordered lists of posts and pages
    env.blog_posts, env.blog_pages = [], []
    relations = env.collect_relations()

    # start from root
    doc = tinkerer.master_doc

    # while not last doc
    while relations[doc][2]:
        doc = relations[doc][2]

        # if this is a post or a page (has metadata)
        if doc in env.blog_metadata:
            # set title
            env.blog_metadata[doc].title = env.titles[doc].astext()

            # ignore if parent is not master (eg. nested pages)
            if relations[doc][0] == tinkerer.master_doc:
                if env.blog_metadata[doc].is_post:
                    env.blog_posts.append(doc)
                elif env.blog_metadata[doc].is_page:
                    env.blog_pages.append(doc)

    env.blog_page_list = [("index", UIStr.HOME)] + \
                         [(page, env.titles[page].astext())
                          for page in env.blog_pages]


def add_metadata(app, pagename, context):
    '''
    Passes metadata to the templating engine.
    '''
    env = app.builder.env

    # page data
    context['website'] = app.config.website

    # blog tagline and pages
    context["tagline"] = app.config.tagline
    context["description"] = app.config.description
    context["pages"] = env.blog_page_list

    # set translation context variables
    context["text_recent_posts"] = UIStr.RECENT_POSTS
    context["text_posted_by"] = UIStr.POSTED_BY
    context["text_blog_archive"] = UIStr.BLOG_ARCHIVE
    context["text_filed_under"] = UIStr.FILED_UNDER
    context["text_tags"] = UIStr.TAGS
    context["text_tags_cloud"] = UIStr.TAGS_CLOUD
    context["text_categories"] = UIStr.CATEGORIES

    # recent posts
    context["recent"] = [(post, env.titles[post].astext()) for post
                         in env.blog_posts[:20]]
    # tags & categories
    tags = dict((t, 0) for t in env.filing["tags"])
    taglinks = dict((t, name_from_title(t)) for t in env.filing["tags"])
    categories = dict((c, 0) for c in env.filing["categories"])
    catlinks = dict([(c, name_from_title(c))
                     for c in env.filing["categories"]])
    for post in env.blog_posts:
        p = env.blog_metadata[post]
        for tag in p.filing["tags"]:
            tags[tag[1]] += 1
        for cat in p.filing["categories"]:
            categories[cat[1]] += 1
    context["tags"] = tags
    context["taglinks"] = taglinks
    context["categories"] = categories
    context["catlinks"] = catlinks

    # if there is metadata for the page, it is not an auto-generated one
    if pagename in env.blog_metadata:
        context["metadata"] = env.blog_metadata[pagename]

        # if this is a post
        if pagename in env.blog_posts:
            # save body
            env.blog_metadata[pagename].body = context["body"]

            # no prev link if first post, no next link for last post
            if pagename == env.blog_posts[0]:
                context["prev"] = None
            if pagename == env.blog_posts[-1]:
                context["next"] = None
        # if this is not documententation
        elif not (pagename.startswith("doc/") or pagename.startswith("docs/")):
            # no rellinks for non-posts/docs
            context["prev"], context["next"] = None, None

    # otherwise provide default metadata
    else:
        context["metadata"] = Metadata()

########NEW FILE########
__FILENAME__ = patch
'''
    patch
    ~~~~~

    Handles HTML link patching for images and cross-references. Sphinx
    generates these links as relative paths - aggregated pages and RSS
    feed require these to be patched.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
from os import path

import pyquery

from tinkerer.ext.uistr import UIStr


def patch_aggregated_metadata(context):
    """
    Patches context in aggregated pages
    """
    for metadata in context["posts"]:
        metadata.body = patch_links(
            metadata.body,
            metadata.link[:11],  # first 11 characters is path (YYYY/MM/DD/)
            metadata.link[11:],  # following characters represent filename
            True)      # hyperlink title to post
        metadata.body = strip_xml_declaration(metadata.body)


def patch_links(body, docpath, docname=None, link_title=False,
                replace_read_more_link=True):
    '''
    Parses the document body and calls patch_node from the document root
    to fix hyperlinks. Also hyperlinks document title. Returns resulting
    XML as string.
    '''
    doc = pyquery.PyQuery(body)
    patch_node(doc, docpath, docname)

    body = doc.html()
    if docname and replace_read_more_link:
        body = make_read_more_link(body, docpath, docname)

    if link_title:
        return hyperlink_title(body, docpath, docname)
    else:
        return body


def hyperlink_title(body, docpath, docname):
    """
    Hyperlink titles by embedding appropriate a tag inside
    h1 tags (which should only be post titles).
    """
    body = body.replace("<h1>", '<h1><a href="%s.html">' %
                        (docpath + docname), 1)
    body = body.replace("</h1>", "</a></h1>", 1)
    return body


def make_read_more_link(body, docpath, docname):
    """
    Create "read more" link if marker exists.
    """
    doc = pyquery.PyQuery(body)
    link_p = ('<p class="readmorewrapper"><a class="readmore" '
              'href="%s.html#more">%s</a></p>' %
              (docpath + docname, UIStr.READ_MORE))
    doc('div#more').replaceWith(link_p)
    doc('p.readmorewrapper').next_all().remove()
    return doc.html()


def collapse_path(path_url):
    '''
    Normalize relative path and patch protocol prefix
    and Windows path separator
    '''
    return path.normpath(path_url).replace("\\", "/").replace(":/", "://")


def patch_node(node, docpath, docname=None):
    for img in node.find('img'):
        src = img.get('src', '')
        if src.startswith(".."):
            src = docpath + src
        src = collapse_path(src)
        img.set('src', src)

    for anchor in node.find('a'):
        ref = anchor.get('href')
        # skip anchor links <a name="anchor1"></a>, <a name="more"/>
        if ref is not None:
            # patch links only - either starting with "../" or having
            # "internal" class
            is_relative = ref.startswith("../")

            classes = anchor.get('class')
            is_internal = classes and "internal" in classes

            if is_relative or is_internal:
                ref = docpath + ref

            # html anchor with missing post.html
            # e.g. href="2012/08/23/#the-cross-compiler"
            # now href="2012/08/23/a_post.html#the-cross-compiler"
            ref = ref.replace("/#", "/%s.html#" % docname)

            # normalize urls so "2012/08/23/../../../_static/" becomes
            # "_static/" - we can use normpath for this, just make sure
            # to revert change on protocol prefix as normpath deduplicates
            # // (http:// becomes http:/)
            ref = collapse_path(ref)
            anchor.set('href', ref)


def strip_xml_declaration(body):
    """
    Remove XML declaration from document body.
    """
    return body.replace('<?xml version="1.0" ?>', '')

########NEW FILE########
__FILENAME__ = readmore
'''
    readmore
    ~~~~~~~~

    Read more directive.

    :copyright: Copyright 2012 by Christian Jann
    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
from docutils import nodes
from sphinx.util.compat import Directive


class InsertReadMoreLink(Directive):
    '''
    Sphinx extension for inserting a "Read more..." link.
    '''

    has_content = True
    required_arguments = 0

    def run(self):
        return [nodes.raw("", '<div id="more"> </div>', format="html")]

########NEW FILE########
__FILENAME__ = rss
'''
    rss
    ~~~

    RSS feed generator for blog.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import email.utils
import time

import pyquery

from tinkerer.ext import patch


def remove_header_link(body):
    """Remove any headerlink class anchor tags from the body.
    """
    doc = pyquery.PyQuery(body)
    doc.remove('a.headerlink')
    body = doc.html()
    return body


def add_rss(app, context):
    '''
    Adds RSS service link to page context.
    '''
    context["rss_service"] = app.config.rss_service


def generate_feed(app):
    '''
    Generates RSS feed.
    '''
    env = app.builder.env

    # don't do anything if no posts are available
    if not env.blog_posts:
        return

    posts = env.blog_posts
    if app.config.rss_max_items > 0:
        posts = posts[:app.config.rss_max_items]

    context = make_feed_context(app, None, posts)
    yield ("rss", context, "rss.html")


def make_feed_context(app, feed_name, posts):
    env = app.builder.env
    context = dict()

    # feed items
    context["items"] = []
    for post in posts:
        link = "%s%s.html" % (app.config.website, post)

        timestamp = email.utils.formatdate(
            time.mktime(env.blog_metadata[post].date.timetuple()),
            localtime=True)

        categories = [category[1] for category in
                      env.blog_metadata[post].filing["categories"]]

        description = patch.strip_xml_declaration(
            patch.patch_links(
                env.blog_metadata[post].body,
                # first 11 characters of post is the path (YYYY/MM/DD/)
                app.config.website + post[:11],
                # following characters represent filename
                post[11:],
                replace_read_more_link=not app.config.rss_generate_full_posts,
            ),
        )
        description = remove_header_link(description)

        context["items"].append({
            "title": env.titles[post].astext(),
            "link": link,
            "description": description,
            "categories": categories,
            "pubDate": timestamp
        })

    # feed metadata
    if feed_name:
        context["title"] = "%s - %s" % (app.config.project, feed_name)
    else:
        context["title"] = app.config.project
    context["link"] = app.config.website
    context["tagline"] = app.config.tagline
    context["language"] = "en-us"

    # feed pubDate is equal to latest post pubDate
    if context['items']:
        context["pubDate"] = context["items"][0]["pubDate"]

    return context

########NEW FILE########
__FILENAME__ = uistr
'''
    uistr
    ~~~~~

    Centralizes UI strings for easier localization and handling unicode
    support.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
try:
    # Python 3
    import builtins as __builtin__
except:
    # Python 2
    import __builtin__


# check whether unicode builtin exists, otherwise strings are unicode by
# default so it can be stubbed
if "unicode" not in __builtin__.__dict__:
    def unicode(ret, ignore):
        return ret


class UIStr:
    # initialize localized strings
    def __init__(self, app):
        _ = app.t.gettext

        UIStr.HOME = unicode(_("Home"), "utf-8")
        UIStr.RECENT_POSTS = unicode(_("Recent Posts"), "utf-8")
        UIStr.POSTED_BY = unicode(_("Posted by"), "utf-8")
        UIStr.BLOG_ARCHIVE = unicode(_("Blog Archive"), "utf-8")
        UIStr.FILED_UNDER = unicode(_("Filed under"), "utf-8")
        UIStr.TAGS = unicode(_("Tags"), "utf-8")
        UIStr.TAGS_CLOUD = unicode(_("Tags Cloud"), "utf-8")
        UIStr.CATEGORIES = unicode(_("Categories"), "utf-8")
        UIStr.TIMESTAMP_FMT = unicode(_('MMMM dd, yyyy'), "utf-8")
        UIStr.TIMESTAMP_FMT_SHORT = unicode(_('MMM dd'), "utf-8")
        UIStr.TAGGED_WITH_FMT = unicode(
            _('Posts tagged with <span class="title_tag">%s</span>'), "utf-8")
        UIStr.FILED_UNDER_FMT = unicode(
            _('Filed under <span class="title_category">%s</span>'), "utf-8")
        UIStr.NEWER = unicode(_("Newer"), "utf-8")
        UIStr.OLDER = unicode(_("Older"), "utf-8")
        UIStr.PAGE_FMT = unicode(_("Page %d"), "utf-8")
        UIStr.READ_MORE = unicode(_("Read more..."), "utf-8")
        UIStr.MAIL_HIDDEN_BY_JAVASCRIPT = unicode(
            _("Javascript must be enabled to see this e-mail address"),
            "utf-8")

########NEW FILE########
__FILENAME__ = master
'''
    master
    ~~~~~~

    Handles updating the master document.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
from tinkerer import paths


def read_master():
    '''
    Reads master file into a list.
    '''
    with open(paths.master_file, "r") as f:
        return f.readlines()


def write_master(lines):
    '''
    Overwrites master file with given lines.
    '''
    with open(paths.master_file, "w") as f:
        f.writelines(lines)


def prepend_doc(docname):
    '''
    Inserts document at the top of the TOC.
    '''
    lines = read_master()

    # find maxdepth directive
    line_no = 0
    for line_no, line in enumerate(lines):
        if "maxdepth" in line:
            break

    # insert docname after it with 3 space alignment
    lines.insert(line_no + 2, "   %s\n" % docname)

    write_master(lines)


def append_doc(docname):
    '''
    Appends document at the end of the TOC.
    '''
    lines = read_master()

    # find second blank line after maxdepth directive
    blank, line_no = 0, 0
    for line_no, line in enumerate(read_master()):
        if blank == 3:
            break
        if "maxdepth" in line:
            blank = 1
        if blank and line == "\n":
            blank += 1

    lines.insert(line_no, "   %s\n" % docname)

    write_master(lines)


def exists_doc(docname):
    '''
    Return true if document in TOC.
    '''
    return ("   %s\n" % docname) in read_master()


def remove_doc(docname):
    '''
    Removes document from the TOC.
    '''
    # rewrite file filtering line containing docname
    write_master(filter(
        lambda line: line != "   %s\n" % docname,
        read_master())
    )

########NEW FILE########
__FILENAME__ = output
'''
    Tinkerer output
    ~~~~~~~~~~~~~~~

    Handles writing output

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import logging
import sys


# output writer
write = logging.getLogger("write")


# used in "filename only" mode
filename = logging.getLogger("filename")


# global quiet is used to pass -q to Sphinx build
quiet = False


def init(quiet_mode, filename_only):
    """
    Initialize output based on quiet/filename-only flags
    """
    global quiet

    # global quiet is used to pass -q to Sphinx build so it should be set when
    # either in quiet mode or filename-only mode
    quiet = quiet_mode or filename_only

    # always handle write as it also output all errors
    write.addHandler(logging.StreamHandler())

    if filename_only:
        # in filename-only mode, also handle filename and suppress other
        # messages below ERROR level
        filename.addHandler(logging.StreamHandler(sys.stdout))
        write.setLevel(logging.ERROR)
        filename.setLevel(logging.INFO)
    elif quiet:
        # in quiet mode, only display ERROR and above
        write.setLevel(logging.ERROR)
    else:
        # otherwise display INFO
        write.setLevel(logging.INFO)

########NEW FILE########
__FILENAME__ = page
'''
    page
    ~~~~

    Handles creating new pages and inserting them in the master document.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import os
import shutil
import tinkerer
from tinkerer import master, paths, utils, writer


class Page():
    '''
    The class provides methods to create a new page and insert it into the
    master document.
    '''
    def __init__(self, title=None, path=None):
        '''
        Determines page filename based on title or given path and creates the
        path to the page if it doesn't already exist.
        '''
        self.title = title

        # get name from path if specified, otherwise from title
        if path:
            self.name = utils.name_from_path(path)
        else:
            self.name = utils.name_from_title(title)

        # create page directory if it doesn't exist and get page path
        self.path = os.path.join(
            utils.get_path(paths.root, "pages"),
            self.name) + tinkerer.source_suffix

        # docname as it should appear in TOC
        self.docname = "pages/" + self.name

    def write(self, content="", template=None):
        '''
        Writes the page template.
        '''
        template = template or paths.page_template
        writer.render(template, self.path,
                      {"title": self.title,
                       "content": content})


def create(title, template=None):
    '''
    Creates a new page given its title.
    '''
    page = Page(title, path=None)
    if os.path.exists(page.path):
        raise Exception("Page '%s' already exists at '%s" %
                        (title, page.path))
    page.write(template=template)
    if not master.exists_doc(page.docname):
        master.append_doc(page.docname)
    return page


def move(path, date=None):
    '''
    Moves a page given its path.
    '''
    page = Page(title=None, path=path)
    if os.path.exists(page.path):
        raise Exception("Page '%s' already exists" %
                        (page.path, ))
    shutil.move(path, page.path)
    if not master.exists_doc(page.docname):
        master.append_doc(page.docname)
    return page

########NEW FILE########
__FILENAME__ = paths
'''
    paths
    ~~~~~

    Tinkerer path information.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import os
import tinkerer
import sys


# package path
__package_path = os.path.abspath(os.path.dirname(__file__))


# absolute path to assets
__internal_templates_abs_path = os.path.join(__package_path, "__templates")
templates = os.path.join(os.path.abspath("."), "_templates")
themes = os.path.join(__package_path, "themes")
static = os.path.join(__package_path, "static")


# template names
post_template = "post.rst"
page_template = "page.rst"


# add "./exts" path to os search path so Sphinx can pick up any extensions
# from there
sys.path.append(os.path.abspath("./_exts"))


def set_paths(root_path="."):
    '''
    Computes required relative paths based on given root path.
    '''
    global root, blog, doctree, html, master_file, index_file, conf_file
    root = os.path.abspath(root_path)
    blog = os.path.join(root, "blog")
    doctree = os.path.join(blog, "doctrees")
    html = os.path.join(blog, "html")
    master_file = os.path.join(root,
                               tinkerer.master_doc + tinkerer.source_suffix)
    index_file = os.path.join(root, "index.html")
    conf_file = os.path.join(root, "conf.py")

    # relative path to assets required by conf.py
    global themes, templates, static


# compute paths on import
set_paths()

########NEW FILE########
__FILENAME__ = post
'''
    post
    ~~~~

    Handles creating new posts and inserting them in the master document.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENCE file
'''
import os
import shutil
import tinkerer
from tinkerer import master, paths, utils, writer


class Post():
    '''
    The class provides methods to create a new post and insert it into the
    master document.
    '''

    def __init__(self, title=None, path=None, date=None):
        '''
        Initializes a new post and creates path to it if it doesn't already
        exist.
        '''
        self.title = title

        # get year, month and day from date
        self.year, self.month, self.day = utils.split_date(date)

        # get name from path if specified, otherwise from title
        if path:
            self.name = utils.name_from_path(path)
        else:
            self.name = utils.name_from_title(title)

        # create post directory if it doesn't exist and get post path
        self.path = os.path.join(
            utils.get_path(
                paths.root,
                self.year,
                self.month,
                self.day),
            self.name) + tinkerer.source_suffix

        # docname as it should appear in TOC
        self.docname = "/".join([self.year, self.month, self.day, self.name])

    def write(self, content="", author="default",
              categories="none", tags="none",
              template=None):
        '''
        Writes the post template with given arguments.
        '''
        template = template or paths.post_template
        writer.render(template, self.path,
                      {"title":      self.title,
                       "content":    content,
                       "author":     author,
                       "categories": categories,
                       "tags":       tags})


def create(title, date=None, template=None):
    '''
    Creates a new post given its title.
    '''
    post = Post(title, path=None, date=date)
    if os.path.exists(post.path):
        raise Exception("Post '%s' already exists at '%s" %
                        (title, post.path))

    post.write(template=template)
    if not master.exists_doc(post.docname):
        master.prepend_doc(post.docname)
    return post


def move(path, date=None):
    '''
    Moves a post given its path.
    '''
    post = Post(title=None, path=path, date=date)
    if os.path.exists(post.path):
        raise Exception("Post '%s' already exists" %
                        (post.path,))
    shutil.move(path, post.path)
    if not master.exists_doc(post.docname):
        master.prepend_doc(post.docname)
    return post

########NEW FILE########
__FILENAME__ = utils
'''
    utils
    ~~~~~

    Tinkerer utility functions.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import imp
import os
import re


UNICODE_ALNUM_PTN = re.compile(r"[\W_]+", re.U)


def name_from_title(title):
    '''
    Returns a doc name from a title by replacing all groups of
    characters which are not alphanumeric or '_' with the word
    separator character.
    '''
    try:
        word_sep = get_conf().slug_word_separator
    except:
        word_sep = "_"

    return UNICODE_ALNUM_PTN.sub(word_sep, title).lower().strip(word_sep)


def name_from_path(path):
    '''
    Returns a doc name from a path by extracting the filename without
    extension.
    '''
    return os.path.splitext(os.path.basename(path))[0]


def get_path(*args):
    '''
    Creates a path if it doesn't already exist.
    '''
    path = os.path.join(*args)
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def split_date(date=None):
    '''
    Splits a date into formatted year, month and day strings. If not date is
    provided, current date is used.
    '''
    if not date:
        date = datetime.datetime.today()

    return "%04d" % date.year, "%02d" % date.month, "%02d" % date.day


def get_conf():
    '''
    Import conf.py from current directory.
    '''
    return imp.load_source("conf", "./conf.py")

########NEW FILE########
__FILENAME__ = writer
'''
    writer
    ~~~~~~

    Internal template writer - handles template rendering and blog setup.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader
import os
import shutil
from tinkerer import paths, utils


# jinja environment
env = Environment(loader=ChoiceLoader([
    # first choice is _templates subdir from blog root
    FileSystemLoader(paths.templates),
    # if template is not there, use tinkerer builtin
    PackageLoader("tinkerer", "__templates")]))


def render(template, destination, context={}, safe=False):
    '''
    Renders the given template at the given destination with the given context.
    '''
    with open(destination, "wb") as dest:
        dest.write(env.get_template(template).render(context).encode("utf8"))


def render_safe(template, destination, context={}):
    '''
    Similar to render but only renders the template if the destination doesn't
    already exist.
    '''
    # if safe is set to True, abort if file already exists
    if os.path.exists(destination):
        return False

    render(template, destination, context)

    return True


def write_master_file():
    '''
    Writes the blog master document.
    '''
    return render_safe("master.rst", paths.master_file)


def write_index_file():
    '''
    Writes the root index.html file.
    '''
    return render_safe("index.html", paths.index_file)


'''
Default Tinkerer extensions.
'''
DEFAULT_EXTENSIONS = [
    "tinkerer.ext.blog",
    "tinkerer.ext.disqus"
]


def write_conf_file(extensions=DEFAULT_EXTENSIONS, theme="flat"):
    '''
    Writes the Sphinx configuration file.
    '''
    return render_safe(
        "conf.py", paths.conf_file,
        {"extensions": ", ".join(["'%s'" % ext for ext in extensions]),
         "theme": theme})


def copy_templates():
    '''
    Copies Tinkerer post and page templates to blog _templates directory.
    '''
    for template in [paths.post_template, paths.page_template]:
        if not os.path.exists(os.path.join(paths.root, "_templates",
                                           template)):
            shutil.copy(
                os.path.join(paths.__internal_templates_abs_path, template),
                os.path.join(paths.root, "_templates")
            )


def setup_blog():
    '''
    Sets up a new blog.
    '''
    utils.get_path(paths.root, "_static")
    utils.get_path(paths.root, "_templates")
    utils.get_path(paths.root, "drafts")
    copy_templates()
    write_master_file()
    write_index_file()
    return write_conf_file()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-

# flake8: noqa

import tinkerer
import tinkerer.paths

# **************************************************************
# TODO: Edit the lines below
# **************************************************************

# Change this to the name of your blog
project = 'My blog'

# Change this to the tagline of your blog
tagline = 'Add intelligent tagline here'

# Change this to the description of your blog
description = 'This is an awesome blog'

# Change this to your name
author = 'Winston Smith'

# Change this to your copyright string
copyright = '1984, ' + author

# Change this to your blog root URL (required for RSS feed)
website = 'http://127.0.0.1/blog/html/'

# **************************************************************
# More tweaks you can do
# **************************************************************

# Add your Disqus shortname to enable comments powered by Disqus
disqus_shortname = None

# Change your favicon (new favicon goes in _static directory)
html_favicon = 'tinkerer.ico'

# Pick another Tinkerer theme or use your own
html_theme = "{{ theme }}"

# Theme-specific options, see docs
html_theme_options = {}

# Link to RSS service like FeedBurner if any, otherwise feed is
# linked directly
rss_service = None

# Generate full posts for RSS feed even when using "read more"
rss_generate_full_posts = False

# Number of blog posts per page
posts_per_page = 10

# Character use to replace non-alphanumeric characters in slug
slug_word_separator = '_'

# **************************************************************
# Edit lines below to further customize Sphinx build
# **************************************************************

# Add other Sphinx extensions here
extensions = [{{ extensions }}]

# Add other template paths here
templates_path = ['_templates']

# Add other static paths here
html_static_path = ['_static', tinkerer.paths.static]

# Add other theme paths here
html_theme_path = ['_themes', tinkerer.paths.themes]

# Add file patterns to exclude from build
exclude_patterns = ["drafts/*", "_templates/*"]

# Add templates to be rendered in sidebar here
html_sidebars = {
    "**": ["recent.html", "searchbox.html"]
}

# **************************************************************
# Do not modify below lines as the values are required by
# Tinkerer to play nice with Sphinx
# **************************************************************

source_suffix = tinkerer.source_suffix
master_doc = tinkerer.master_doc
version = tinkerer.__version__
release = tinkerer.__version__
html_title = project
html_use_index = False
html_show_sourcelink = False
html_add_permalinks = None

########NEW FILE########
__FILENAME__ = test_categories
'''
    Categories Test
    ~~~~~~~~~~~~~~~

    Tests Tinkerer post categoires.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import os
from tinkerer import paths, post
from tinkertest import utils


# test case
class TestCategories(utils.BaseTinkererTest):
    def test_categories(self):
        utils.test = self

        # create some posts with categories

        # missing category for Post1 ("cateogry #1,") should work,
        # just issue a warning
        for new_post in [("Post1", "category #1,"),
                         ("Post2", "category #2"),
                         ("Post12", "category #1, category #2")]:
            post.create(new_post[0], datetime.date(2010, 10, 1)).write(
                categories=new_post[1])

        utils.hook_extension("test_categories")
        self.build()


# test categories through extension
def build_finished(app, exception):
    blog_categories = app.builder.env.filing["categories"]

    # check collected categories
    utils.test.assertEquals(set(["category #1", "category #2"]),
                            set(blog_categories))

    # check categories
    for result in [(set(["2010/10/01/post1", "2010/10/01/post12"]),
                    "category #1"),
                   (set(["2010/10/01/post2", "2010/10/01/post12"]),
                    "category #2")]:
        utils.test.assertEquals(result[0], set(blog_categories[result[1]]))

    # check post metadata
    for result in [([("category__1", "category #1")], "2010/10/01/post1"),
                   ([("category__2", "category #2")], "2010/10/01/post2"),
                   ([("category__1", "category #1"),
                     ("category__2", "category #2")], "2010/10/01/post12")]:
        utils.test.assertEquals(
            result[0],
            app.builder.env.blog_metadata[result[1]].filing["categories"])

    # check category pages were generated
    for page in ["category__1.html", "category__2.html"]:
        utils.test.assertTrue(os.path.exists(os.path.join(paths.html,
                                                          "categories",
                                                          page)))


# extension setup
def setup(app):
    if utils.is_module(app):
        return
    app.connect("build-finished", build_finished)

########NEW FILE########
__FILENAME__ = test_cmdline
'''
    Command Line Test
    ~~~~~~~~~~~~~~~~~

    Tests Tinkerer command line (setup, post, page and build)

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import logging
import os
try:
    # Python 2
    from StringIO import StringIO
except:
    # Python 3
    from io import StringIO
import tinkerer
from tinkerer import cmdline, output, paths, post
from tinkertest import utils


# test tinkerer command line
class TestCmdLine(utils.BaseTinkererTest):
    # these tests cause lots of output, disable logging while they are running
    def setUp(self):
        logging.disable(logging.CRITICAL)
        utils.setup()

    # re-enable logging
    def tearDown(self):
        logging.disable(logging.NOTSET)
        utils.cleanup()

    # test blog setup
    def test_setup(self):
        # blog is setup as part of test setup, tear it down and
        # re-create it via cmdline
        self.tearDown()
        cmdline.main(["--setup", "--quiet"])

        self.assertEqual(
            set(os.listdir(utils.TEST_ROOT)),
            set([
                "_static",
                "_templates",
                "drafts",
                "conf.py",
                "index.html",
                tinkerer.master_doc + ".rst"
            ]))

    # test post from title
    def test_post_from_title(self):
        cmdline.main(["--post", "My Test Post", "--quiet"])

        # this might fail at midnight :P
        year, month, day = tinkerer.utils.split_date()

        file_path = os.path.join(utils.TEST_ROOT, year, month, day,
                                 "my_test_post.rst")

        # assert file exists
        self.assertTrue(os.path.exists(file_path))

    # test post from existing file
    def test_post_from_path(self):
        # create file
        draft_file = os.path.join(utils.TEST_ROOT, "drafts", "draft_post.rst")

        with open(draft_file, "w") as f:
            f.write("Content")

        cmdline.main(["--post", draft_file, "--quiet"])

        # this might also fail at midnight :P
        year, month, day = tinkerer.utils.split_date()

        file_path = os.path.join(utils.TEST_ROOT, year, month, day,
                                 "draft_post.rst")

        # assert file exists and check content
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, "r") as f:
            self.assertEquals("Content", f.read())

    # test post with explicit date
    def test_post_with_date(self):
        cmdline.main(["--post", "Dated Post", "--date", "2011/11/20"])

        file_path = os.path.join(utils.TEST_ROOT, "2011/11/20",
                                 "dated_post.rst")

        # assert file exists
        self.assertTrue(os.path.exists(file_path))

    # test date is only allowed with post argument
    def test_date_only_on_post(self):
        self.assertNotEqual(
            0,
            cmdline.main(["--page", "Test Page", "--date", "2011/11/20"]))

        self.assertNotEqual(
            0,
            cmdline.main(["--draft", "Test Draft", "--date", "2011/11/20"]))

        self.assertNotEqual(
            0,
            cmdline.main(["--build", "--date", "2011/11/20"]))

    # test page from title
    def test_page_from_title(self):
        cmdline.main(["--page", "My Test Page", "--quiet"])

        file_path = os.path.join(utils.TEST_ROOT, "pages", "my_test_page.rst")

        # assert file exsits
        self.assertTrue(os.path.exists(file_path))

    # test page from existing file
    def test_post_from_existing_file(self):
        # create file
        draft_file = os.path.join(utils.TEST_ROOT, "drafts", "draft_page.rst")

        with open(draft_file, "w") as f:
            f.write("Content")

        cmdline.main(["--page", draft_file, "--quiet"])

        file_path = os.path.join(utils.TEST_ROOT, "pages", "draft_page.rst")

        # assert file exists and check content
        self.assertTrue(os.path.exists(file_path))
        with open(file_path, "r") as f:
            self.assertEquals("Content", f.read())

    # test draft
    def test_draft(self):
        cmdline.main(["--draft", "My Draft", "--quiet"])

        file_path = os.path.join(utils.TEST_ROOT, "drafts", "my_draft.rst")

        # assert draft was created
        self.assertTrue(os.path.exists(file_path))

    # test missing template
    def test_missing_template(self):
        # creating a post with a missing template file should fail
        self.assertNotEqual(
            0,
            cmdline.main(["--post", "test", "--template", "missing",
                          "--quiet"])
        )

    # test build
    def test_build(self):
        # create a new post
        post.create("My Post", datetime.date(2010, 10, 1))

        self.build()

        # assert html is produced
        self.assertTrue(os.path.exists(
            os.path.join(utils.TEST_ROOT, "blog", "html", "2010",
                         "10", "01", "my_post.html")))

    # ensure tinkerer only runs from blog root (dir containing conf.py) except
    # when running setup
    def test_root_only(self):
        # remove "conf.py" created by test setup
        os.remove(os.path.join(paths.root, "conf.py"))

        self.assertNotEqual(
            0,
            cmdline.main(["--page", "Test Post", "--quiet"]))

        self.assertNotEqual(
            0,
            cmdline.main(["--post", "Test Page", "--quiet"]))

        self.assertNotEqual(
            0,
            cmdline.main(["--build", "--quiet"]))

        # setup should work fine from anywhere
        self.assertEqual(
            0,
            cmdline.main(["--setup", "--quiet"]))

    def test_filename_only(self):
        # hook up test log handler
        test_stream = StringIO()

        # restore logging for this particular test
        logging.disable(logging.NOTSET)

        output.filename.addHandler(logging.StreamHandler(test_stream))

        # setup new blog with --filename flag
        cmdline.main(["--setup", "--filename"])

        # output should be `conf.py`
        self.assertEquals("conf.py", test_stream.getvalue().strip())

########NEW FILE########
__FILENAME__ = test_disqus
'''
    Disqus Test
    ~~~~~~~~~~~

    Tests Disqus extension

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import os
from tinkerer import post
from tinkerer.ext import disqus
from tinkertest import utils


# test case
class TestDisqus(utils.BaseTinkererTest):
    # test disqus extension
    def test_disqus(self):
        TEST_SHORTNAME = "test_shortname"

        # add disqus_shortname in conf.py
        conf_path = os.path.join(utils.TEST_ROOT, "conf.py")
        conf_text = open(conf_path, "r").read()

        open(conf_path, "w").write(
            conf_text.replace("disqus_shortname = None",
                              'disqus_shortname = "%s"' % TEST_SHORTNAME))

        # create a post
        post.create("post1", datetime.date(2010, 10, 1))
        POST_ID = "2010/10/01/post1"
        POST_LINK = "http://127.0.0.1/blog/html/" + POST_ID + ".html"

        # build blog
        self.build()

        # ensure disqus script is added to html output
        output = os.path.join(utils.TEST_ROOT,
                              "blog", "html", "2010", "10", "01", "post1.html")
        output_html = open(output, "r").read()

        self.assertTrue(
            disqus.create_thread(TEST_SHORTNAME, POST_ID) in output_html)

        output = os.path.join(utils.TEST_ROOT,
                              "blog", "html", "index.html")
        output_html = open(output, "r").read()

        # ensure script to enable comment count is added to aggregated page
        self.assertTrue(
            disqus.enable_count(TEST_SHORTNAME) in output_html)

        # ensure comment count is added to aggregated page
        self.assertTrue(
            disqus.get_count(POST_LINK, POST_ID) in output_html)

########NEW FILE########
__FILENAME__ = test_draft
'''
    Draft Creation Test
    ~~~~~~~~~~~~~~~~~~~

    Tests creating drafts.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import os
from tinkerer import cmdline, draft, master, page, paths, post
from tinkertest import utils

import mock


# test creating drafts
class TestDraft(utils.BaseTinkererTest):
    # test creating draft from title
    def test_create(self):
        # create draft with given title
        new_draft = draft.create("My Draft")

        self.assertEquals(
            os.path.abspath(os.path.join(
                utils.TEST_ROOT,
                "drafts",
                "my_draft.rst")),
            new_draft)

        self.assertTrue(os.path.exists(new_draft))

    # test moving draft from existing files
    def test_move(self):
        # create a post and a page
        new_post = post.create("A post", datetime.datetime(2010, 10, 1))
        new_page = page.create("A page")

        # page and posts should be in master doc (precondition)
        lines = master.read_master()
        self.assertTrue("   %s\n" % new_post.docname in lines)
        self.assertTrue("   %s\n" % new_page.docname in lines)

        new_draft = draft.move(os.path.join(
            utils.TEST_ROOT, "pages", "a_page.rst"))
        self.assertTrue(os.path.exists(new_draft))

        # page should no longer be in TOC
        lines = master.read_master()
        self.assertTrue("   %s\n" % new_post.docname in lines)
        self.assertFalse("   %s\n" % new_page.docname in lines)

        new_draft = draft.move(os.path.join(
            utils.TEST_ROOT, "2010", "10", "01", "a_post.rst"))
        self.assertTrue(os.path.exists(new_draft))

        # post should no longer be in TOC either
        lines = master.read_master()
        self.assertFalse("   %s\n" % new_post.docname in lines)
        self.assertFalse("   %s\n" % new_page.docname in lines)

    # test draft preview
    def test_preview(self):
        # create a post
        new_post = post.create("A post", datetime.datetime(2010, 10, 1))

        # post should be in master doc (precondition)
        lines = master.read_master()
        self.assertTrue("   %s\n" % new_post.docname in lines)

        # create a draft
        new_draft = draft.create("draft")
        self.assertTrue(os.path.exists(new_draft))

        # preview it (build should succeed)
        self.assertEqual(
            0,
            cmdline.main(["--preview", new_draft, "-q"]))

        # draft should not be in TOC
        for line in master.read_master():
            self.assertFalse("draft" in line)

    # test content
    def test_content(self):
        # create draft with no content
        new_draft = draft.create("My Draft")

        # check expected empty post content
        with open(new_draft) as f:
            self.assertEquals(
                f.readlines(),
                ["My Draft\n",
                 "========\n",
                 "\n",
                 "\n",
                 "\n",
                 ".. author:: default\n",
                 ".. categories:: none\n",
                 ".. tags:: none\n",
                 ".. comments::\n"])

    @mock.patch('tinkerer.writer.render')
    def test_create_without_template(self, render):
        draft.create('no-template')
        render.assert_called_once_with(
            paths.post_template,
            mock.ANY,
            mock.ANY,
        )

    @mock.patch('tinkerer.writer.render')
    def test_create_with_template(self, render):
        draft.create('with-template', template='the_template.rst')
        render.assert_called_once_with(
            'the_template.rst',
            mock.ANY,
            mock.ANY,
        )

########NEW FILE########
__FILENAME__ = test_master
'''
    Master Document Update Test
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests updating the master document.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
from tinkerer import master
from tinkertest import utils


# test updating master document
class TestMaster(utils.BaseTinkererTest):
    # head and tail of master doc checked in each test
    MASTER_HEAD = [
        "Sitemap\n",
        "=======\n",
        "\n",
        ".. toctree::\n",
        "   :maxdepth: 1\n",
        "\n"]

    MASTER_TAIL = ["\n"]

    # validate master doc created by setup
    def test_setup(self):
        self.assertEquals(
            TestMaster.MASTER_HEAD + TestMaster.MASTER_TAIL,
            master.read_master())

    # test appending at the end of the TOC
    def test_append(self):
        new_docs = ["somewhere/somedoc", "anotherdoc"]

        master.append_doc(new_docs[0])

        # first doc should be appendend in the correct place
        self.assertEquals(
            TestMaster.MASTER_HEAD +
            ["   %s\n" % new_docs[0]] +
            TestMaster.MASTER_TAIL,
            master.read_master())

        master.append_doc(new_docs[1])

        # second doc should be appended in the correct place
        self.assertEquals(
            TestMaster.MASTER_HEAD +
            ["   %s\n" % new_docs[0], "   %s\n" % new_docs[1]] +
            TestMaster.MASTER_TAIL,
            master.read_master())

    # test prepending at the beginning of the TOC
    def test_prepend(self):
        new_docs = ["somewhere/somedoc", "anotherdoc"]

        # first doc should be prepended in the correct place
        master.prepend_doc(new_docs[0])

        self.assertEquals(
            TestMaster.MASTER_HEAD +
            ["   %s\n" % new_docs[0]] +
            TestMaster.MASTER_TAIL,
            master.read_master())

        master.prepend_doc(new_docs[1])

        # order should be second doc then first doc
        self.assertEquals(
            TestMaster.MASTER_HEAD +
            ["   %s\n" % new_docs[1], "   %s\n" % new_docs[0]] +
            TestMaster.MASTER_TAIL,
            master.read_master())

    # test removing from the TOC
    def test_remove(self):
        # append 4 docs
        new_docs = ["a", "b", "c", "d"]
        for doc in new_docs:
            master.append_doc(doc)

        # remove 3 of them while checking master each time
        for doc_to_remove in ["c", "b", "d"]:
            master.remove_doc(doc_to_remove)
            new_docs.remove(doc_to_remove)

            self.assertEquals(
                TestMaster.MASTER_HEAD +
                ["   %s\n" % doc for doc in new_docs] +
                TestMaster.MASTER_TAIL,
                master.read_master())

########NEW FILE########
__FILENAME__ = test_metadata
'''
    Metadata Test
    ~~~~~~~~~~~~~

    Tests metadata collected by Tinkerer during build.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
from tinkerer import page, post
from tinkertest import utils


# test case
class TestMetadata(utils.BaseTinkererTest):
    def test_metadata(self):
        utils.test = self

        # create some posts
        for i in range(20):
            post.create("Post %d" % i, datetime.date(2010, 10, i + 1)).write(
                content=" ".join("a" * 100))

        # ... and some pages
        for i in range(10):
            page.create("Page %d" % i)

        utils.hook_extension("test_metadata")
        self.build()


# test metadata through extension
def build_finished(app, exception):
    env = app.builder.env

    # check posts were identified as such
    posts = ["2010/10/%02d/post_%d" % (i + 1, i) for i in range(20)]
    utils.test.assertEquals(set(posts), set(env.blog_posts))

    # check pages were identified as such
    pages = ["pages/page_%d" % i for i in range(10)]
    utils.test.assertEquals(set(pages), set(env.blog_pages))

    # body should contain the whole 100 word string
    utils.test.assertTrue(" ".join("a" * 100) in
                          env.blog_metadata[env.blog_posts[0]].body)


# extension setup
def setup(app):
    if utils.is_module(app):
        return
    app.connect("build-finished", build_finished)

########NEW FILE########
__FILENAME__ = test_ordering
'''
    Ordering Test
    ~~~~~~~~~~~~~

    Tests that Tinkerer adds posts and pages in the correct order

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
from tinkertest import utils
import tinkerer
from tinkerer import page, post


# test case
class TestOrdering(utils.BaseTinkererTest):
    def test_ordering(self):
        utils.test = self

        # create some pages and posts
        page.create("First Page")
        post.create("Oldest Post", datetime.date(2010, 10, 1))
        post.create("Newer Post", datetime.date(2010, 10, 1))
        page.create("Another Page")
        post.create("Newest Post", datetime.date(2010, 10, 1))

        utils.hook_extension("test_ordering")
        self.build()


ordering = {
    tinkerer.master_doc: [None, None, "2010/10/01/newest_post"],
    "2010/10/01/newest_post": [tinkerer.master_doc, tinkerer.master_doc,
                               "2010/10/01/newer_post"],
    "2010/10/01/newer_post": [tinkerer.master_doc, "2010/10/01/newest_post",
                              "2010/10/01/oldest_post"],
    "2010/10/01/oldest_post": [tinkerer.master_doc, "2010/10/01/newer_post",
                               "pages/first_page"],
    "pages/first_page": [tinkerer.master_doc, "2010/10/01/oldest_post",
                         "pages/another_page"],
    "pages/another_page": [tinkerer.master_doc, "pages/first_page", None]
}


# test ordering through extension
def build_finished(app, exception):
    env = app.builder.env

    # check post and pages have the correct relations
    relations = env.collect_relations()

    for docname in ordering:
        utils.test.assertEquals(relations[docname], ordering[docname])

    # check metadata ordering is correct
    utils.test.assertEquals(
        ["2010/10/01/newest_post",
         "2010/10/01/newer_post",
         "2010/10/01/oldest_post"],
        env.blog_posts)

    utils.test.assertEquals(
        ["pages/first_page",
         "pages/another_page"],
        env.blog_pages)


# extension setup
def setup(app):
    if utils.is_module(app):
        return
    app.connect("build-finished", build_finished)

########NEW FILE########
__FILENAME__ = test_page
'''
    Page Creation Test
    ~~~~~~~~~~~~~~~~~~

    Tests creating pages.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import os

from tinkerer import page
from tinkerer import paths
import tinkerer
from tinkertest import utils

import mock
from nose.tools import raises


# test creating new page
class TestPage(utils.BaseTinkererTest):
    # test create call
    def test_create(self):
        # create page
        new_page = page.create("My Page")

        self.assertEquals(
            os.path.abspath(os.path.join(
                utils.TEST_ROOT,
                "pages",
                "my_page.rst")),
            new_page.path)

        self.assertTrue(os.path.exists(new_page.path))
        self.assertEquals("pages/my_page", new_page.docname)

    # test moving existing file
    def test_move(self):
        # create a "pre-existing" file
        draft_file = os.path.join(utils.TEST_ROOT, "drafts", "afile.rst")

        with open(draft_file, "w") as f:
            f.write("Content")

        # move file to page
        moved_page = page.move(draft_file)

        self.assertEquals(
            os.path.abspath(os.path.join(
                utils.TEST_ROOT,
                "pages",
                "afile.rst")),
            moved_page.path)

        self.assertTrue(os.path.exists(moved_page.path))
        self.assertFalse(os.path.exists(draft_file))
        self.assertEquals("pages/afile", moved_page.docname)

    # test updating master document
    def test_master_update(self):
        page.create("Page 1")
        page.create("Page 2")

        with open(tinkerer.paths.master_file, "r") as f:
            lines = f.readlines()

            self.assertEquals("   pages/page_1\n", lines[-3])
            self.assertEquals("   pages/page_2\n", lines[-2])

    # test content
    def test_content(self):
        new_page = page.create("My Page")

        # check expected empty page content
        with open(new_page.path) as f:
            self.assertEquals(
                f.readlines(),
                ["My Page\n",
                 "=======\n",
                 "\n"])

    # test that create duplicate page raises exception
    @raises(Exception)
    def test_create_duplicate(self):
        # create initial post
        page.create("Page1")

        # should raise
        page.create("Page1")

    # test that moving page to existing page raises exception
    @raises(Exception)
    def test_move_duplicate(self):
        # create initial page
        page.create("Page1")

        # should raise
        page.move("Page1")

    @mock.patch('tinkerer.writer.render')
    def test_create_without_template(self, render):
        page.create('no-template')
        render.assert_called_once_with(
            paths.page_template,
            mock.ANY,
            mock.ANY,
        )

    @mock.patch('tinkerer.writer.render')
    def test_create_with_template(self, render):
        page.create('with-template', template='the_template.rst')
        render.assert_called_once_with(
            'the_template.rst',
            mock.ANY,
            mock.ANY,
        )

########NEW FILE########
__FILENAME__ = test_patch
'''
    Patch Test
    ~~~~~~~~~~

    Tests link patching on aggreated pages and RSS feed.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import os
from tinkerer import paths, post
from tinkertest import utils
import sys


# test case
class TestPatch(utils.BaseTinkererTest):

    def check_posts(self, filenames, posts, expected):
        # helper function which creates given list of files and posts, runs a
        # build, then ensures expected content exists in each file
        for filename in filenames:
            with open(os.path.join(paths.root, filename), "w") as f:
                f.write("content not important")

        # posts are tuples consisting of post title and content
        # all posts are created on 2010/10/1 as date is not relevant here
        for new_post in posts:
            post.create(new_post[0], datetime.date(2010, 10, 1)).write(
                content=new_post[1]
            )

        # build and check output
        self.build()

        # tests are tuples consisting of file path (as a list) and the list of
        # expected content
        for test in expected:
            with open(os.path.join(paths.html, *test[0]), "r") as f:
                content = f.read()
                for data in test[1]:
                    if data not in content:
                        print(data)
                        print(content)
                    self.assertTrue(data in content)

    def test_patch_a_and_img(self):
        filenames = ["img.png"]
        posts = [
            ("Post1", ":ref:`x`\n`Arch Linux <www.archlinux.org>`_"),
            ("Post2", ".. _x:\n\nX\n-\n.. image:: ../../../img.png")
        ]

        expected = [
            # Sphinx running on Python3 has an achor here, Python2 doesn't
            (["2010", "10", "01", "post1.html"],
             [('href="post2.html#x"' if sys.version_info[0] == 3 else
               'href="post2.html"'),
              'href="www.archlinux.org"']),

            # images get places in _images directory under root
            (["2010", "10", "01", "post2.html"],
             ['src="../../../_images/img.png"']),

            # index.html should have links patched with relative address
            (["index.html"],
             ['href="2010/10/01/post2.html#x"',
              'href="www.archlinux.org"',
              'src="_images/img.png"']),

            # RSS feed should have links patched with absolute address
            (["rss.html"],
             ['href="http://127.0.0.1/blog/html/2010/10/01/post2.html#x"',
              'href="www.archlinux.org"',
              'src="http://127.0.0.1/blog/html/_images/img.png"'])
        ]

        self.check_posts(filenames, posts, expected)

    def test_patch_target(self):
        # tests patching links for images with :target: specified
        filenames = ["img1.png", "img2.png", "img3.png"]

        posts = [
            ("Post1",
             # relative target
             ".. image:: ../../../img1.png\n"
             "   :target: ../../../_images/img1.png\n"
             "\n"
             # absolute target
             ".. image:: ../../../img2.png\n"
             "   :target: /_images/img2.png\n"
             "\n"
             # external target
             ".. image:: ../../../img3.png\n"
             "   :target: www.archlinux.org\n")
        ]

        expected = [
            (["2010", "10", "01", "post1.html"],
             [
                 # nothing should be changed
                 'href="../../../_images/img1.png"',
                 'href="/_images/img2.png"',
                 'href="www.archlinux.org"']),

            (["index.html"],
             [
                # relative target should get patched
                'href="_images/img1.png"',

                # absolute and external targets should be unchanged
                'href="/_images/img2.png"',
                'href="www.archlinux.org"']),
            (["rss.html"],
             [
                # relative and absolute targets should get patched
                'href="http://127.0.0.1/blog/html/_images/img1.png"',

                # absolute target doesn't get patched
                # 'href="http://127.0.0.1/_images/img2.png"',
                'href="www.archlinux.org"'])
        ]

        self.check_posts(filenames, posts, expected)

    def test_patch_bad_link(self):
        # post with an invalid link, which doesn't produce a proper <a> tag
        posts = [
            ("Post1",
             # bad link
             "`http://book.cakephp.org/3.0/en/appendices/3-0-migration-\n"
             "guide.html`_")
        ]

        expected = [
            (["2010", "10", "01", "post1.html"],
             [
                # should be marked as problematic by Sphinx
                '<a href="#id1"><span class="problematic" id="id2">'
                '`http://book.cakephp.org/3.0/en/appendices/3-0-migration-\n'
                'guide.html`_</span></a>'])
        ]

        self.check_posts([], posts, expected)

########NEW FILE########
__FILENAME__ = test_post
'''
    Post Creation Test
    ~~~~~~~~~~~~~~~~~~

    Tests creating posts.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import os

from tinkerer import post
import tinkerer
from tinkerer import paths

from tinkertest import utils

import mock
from nose.tools import raises


# test creating new post
class TestPost(utils.BaseTinkererTest):
    # test create call
    def test_create(self):
        # create post with current date
        new_post = post.create("My Post")

        year, month, day = tinkerer.utils.split_date()
        self.assertEquals(year, new_post.year)
        self.assertEquals(month, new_post.month)
        self.assertEquals(day, new_post.day)

        self.assertEquals(
            os.path.abspath(os.path.join(
                utils.TEST_ROOT,
                year,
                month,
                day,
                "my_post.rst")),
            new_post.path)

        self.assertTrue(os.path.exists(new_post.path))

        # create post with given date
        new_post = post.create("Date Post", datetime.date(2010, 10, 1))
        self.assertEquals("2010", new_post.year)
        self.assertEquals("10", new_post.month)
        self.assertEquals("01", new_post.day)

        self.assertEquals(
            os.path.abspath(os.path.join(
                utils.TEST_ROOT,
                "2010",
                "10",
                "01",
                "date_post.rst")),
            new_post.path)

        self.assertTrue(os.path.exists(new_post.path))
        self.assertEquals("2010/10/01/date_post", new_post.docname)

    def test_create_dashed(self):
        # chdir to test root and create a dummy conf.py to set the
        # slug_word_separator
        cwd = os.getcwd()
        os.chdir(utils.TEST_ROOT)

        with open("conf.py", "w") as f:
            f.write("slug_word_separator = '-'")

        # create post with current date and dash as word separator
        new_post = post.create("My __Second  Post.")

        os.chdir(cwd)

        year, month, day = tinkerer.utils.split_date()
        self.assertEquals(year, new_post.year)
        self.assertEquals(month, new_post.month)
        self.assertEquals(day, new_post.day)

        self.assertEquals(
            os.path.abspath(os.path.join(
                utils.TEST_ROOT,
                year,
                month,
                day,
                "my-second-post.rst")),
            new_post.path)

        self.assertTrue(os.path.exists(new_post.path))

    # test moving existing file to post
    def test_move(self):
        # create a "pre-existing" file
        draft_file = os.path.join(utils.TEST_ROOT, "drafts", "afile.rst")

        with open(draft_file, "w") as f:
            f.write("Content")

        # move file to post
        moved_post = post.move(draft_file, datetime.date(2010, 10, 1))
        self.assertEquals("2010", moved_post.year)
        self.assertEquals("10", moved_post.month)
        self.assertEquals("01", moved_post.day)

        self.assertEquals(
            os.path.abspath(os.path.join(
                utils.TEST_ROOT,
                "2010",
                "10",
                "01",
                "afile.rst")),
            moved_post.path)

        self.assertTrue(os.path.exists(moved_post.path))
        self.assertFalse(os.path.exists(draft_file))
        self.assertEquals("2010/10/01/afile", moved_post.docname)

    # test updating master document
    def test_master_update(self):
        post.create("Post 1", datetime.date(2010, 10, 1))
        post.create("Post 2", datetime.date(2010, 11, 2))

        with open(tinkerer.paths.master_file, "r") as f:
            lines = f.readlines()

            for lineno, line in enumerate(lines):
                if "maxdepth" in line:
                    break

            self.assertEquals("\n", lines[lineno+1])
            self.assertEquals("   2010/11/02/post_2\n", lines[lineno+2])
            self.assertEquals("   2010/10/01/post_1\n", lines[lineno+3])
            self.assertEquals("\n", lines[lineno+4])

    # test content
    def test_content(self):
        # create post with no content
        new_post = post.create("My Post")

        year, month, day = tinkerer.utils.split_date()

        # check expected empty post content
        with open(new_post.path) as f:
            self.assertEquals(
                f.readlines(),
                ["My Post\n",
                 "=======\n",
                 "\n",
                 "\n",
                 "\n",
                 ".. author:: default\n",
                 ".. categories:: none\n",
                 ".. tags:: none\n",
                 ".. comments::\n"])

        # update post
        new_post.write(author="Mr. Py", categories="category 1, category 2",
                       tags="tag 1, tag 2", content="Lorem ipsum")

        with open(new_post.path) as f:
            self.assertEquals(
                f.readlines(),
                ["My Post\n",
                 "=======\n",
                 "\n",
                 "Lorem ipsum\n",
                 "\n",
                 ".. author:: Mr. Py\n",
                 ".. categories:: category 1, category 2\n",
                 ".. tags:: tag 1, tag 2\n",
                 ".. comments::\n"])

    # test that create duplicate post raises exception
    @raises(Exception)
    def test_create_duplicate(self):
        # create initial post
        post.create("Post1")

        # should raise
        post.create("Post1")

    # test that moving post to existing post raises exception
    @raises(Exception)
    def test_move_duplicate(self):
        # create initial post
        post.create("Post1")

        # should raise
        post.move("Post1")

    # test creating post with no template
    @mock.patch("tinkerer.writer.render")
    def test_create_without_template(self, render):
        post.create("no-template")
        render.assert_called_once_with(
            paths.post_template,
            mock.ANY,
            mock.ANY,
        )

    # test creating post with given template
    @mock.patch("tinkerer.writer.render")
    def test_create_with_template(self, render):
        post.create("with-template", template="the_template.rst")
        render.assert_called_once_with(
            "the_template.rst",
            mock.ANY,
            mock.ANY,
        )

########NEW FILE########
__FILENAME__ = test_readmore
'''
    ReadMore Directive Test
    ~~~~~~~~~~~~~~~~~~~~~~~

    Tests readmore directive.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import os
from tinkerer import post
from tinkertest import utils


# test readmore directive
class TestReadMore(utils.BaseTinkererTest):
    def test_readmore(self):
        post.create("post1", datetime.date(2010, 10, 1)).write(
            content="Text\n\n.. more::\n\nMore text")

        self.build()

        post_path = os.path.join(
            utils.TEST_ROOT,
            "blog", "html", "2010", "10", "01", "post1.html")
        post_html = open(post_path, "r").read()

        # ensure readmore div is added to post
        self.assertTrue('<div id="more"> </div>' in post_html)

        # ensure readmore is patched in aggregated page
        index_path = os.path.join(
            utils.TEST_ROOT,
            "blog", "html", "index.html")
        index_html = open(index_path, "r").read()

        expected = (
            '<p class="readmorewrapper"><a class="readmore"'
            ' href="2010/10/01/post1.html#more">Read more...</a></p>'
        )
        self.assertTrue(expected in index_html)

########NEW FILE########
__FILENAME__ = test_rss
'''
    RSS Generator Test
    ~~~~~~~~~~~~~~~~~~

    Tests the RSS feed generator.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import email.utils
import os
import time
import xml.dom.minidom

from tinkerer import paths, post
from tinkerer.ext import rss

from tinkertest import utils

import mock


# get expected pubdate based on date
def expected_pubdate(year, month, day):
    return email.utils.formatdate(
        time.mktime(datetime.date(year, month, day).timetuple()),
        localtime=True)


# test case
class TestRSS(utils.BaseTinkererTest):
    def test_rss(self):
        # create some posts
        for new_post in [
                ("Post 1",
                    datetime.date(2010, 10, 1),
                    "Lorem ipsum",
                    "category 1"),
                ("Post 2",
                    datetime.date(2010, 11, 2),
                    "dolor sit",
                    "category 2"),
                ("Post 3",
                    datetime.date(2010, 12, 3),
                    "amet, consectetuer",
                    "category 3")]:
            post.create(new_post[0], new_post[1]).write(
                content=new_post[2],
                categories=new_post[3])

        self.build()

        feed_path = os.path.join(paths.html, "rss.html")

        # check feed was created
        self.assertTrue(os.path.exists(feed_path))

        # check feed content
        parsed = xml.dom.minidom.parse(feed_path)
        rss = parsed.getElementsByTagName("rss")[0]
        channel = rss.getElementsByTagName("channel")
        doc = channel[0]

        # validate XML channel data against expected content
        data = {
            "title": None,
            "link": None,
            "description": None,
            "language": None,
            "pubDate": None
        }

        data = self.get_data(doc, data)

        self.assertEquals("My blog", data["title"])
        self.assertEquals("http://127.0.0.1/blog/html/", data["link"])
        self.assertEquals("Add intelligent tagline here", data["description"])
        self.assertEquals("en-us", data["language"])
        self.assertEquals(expected_pubdate(2010, 12, 3), data["pubDate"])

        # validate XML "item" node content against expected content
        data = {
            "link": None,
            "guid": None,
            "title": None,
            "description": None,
            "category": None,
            "pubDate": None
        }

        for item in [
                {"index": 0,
                 "link": "http://127.0.0.1/blog/html/2010/12/03/post_3.html",
                 "title": "Post 3",
                 "description": "amet, consectetuer",
                 "category": "category 3",
                 "pubDate": expected_pubdate(2010, 12, 3)},

                {"index": 1,
                 "link": "http://127.0.0.1/blog/html/2010/11/02/post_2.html",
                 "title": "Post 2",
                 "description": "dolor sit",
                 "category": "category 2",
                 "pubDate": expected_pubdate(2010, 11, 2)},

                {"index": 2,
                 "link": "http://127.0.0.1/blog/html/2010/10/01/post_1.html",
                 "title": "Post 1",
                 "description": "Lorem ipsum",
                 "category": "category 1",
                 "pubDate": expected_pubdate(2010, 10, 1)}]:

            data = self.get_data(
                doc.getElementsByTagName("item")[item["index"]], data)
            self.assertEquals(item["link"], data["link"])
            self.assertEquals(item["link"], data["guid"])
            self.assertEquals(item["title"], data["title"])
            self.assertTrue(item["description"] in data["description"])
            self.assertTrue(item["category"] in data["category"])
            self.assertEquals(item["pubDate"], data["pubDate"])

    # get a dictionary of the given data in an XML node
    def get_data(self, node, data):
        for child in data.keys():
            data[child] = node.getElementsByTagName(
                child)[0].childNodes[0].nodeValue

        return data

    def test_empty_blog(self):
        # empty blog should not generate rss
        self.build()

        self.assertFalse(os.path.exists(os.path.join(paths.html, "rss.html")))


# Set up a fake app with some "blog posts" -- since we aren't
# going to process the posts, it doesn't matter what type of
# object we use.
class FauxConfig(object):
    rss_max_items = 0
    website = None
    project = 'faux project'
    tagline = 'faux tagline'


class FauxEnv(object):

    def __init__(self, num_posts=5):
        self.blog_posts = [
            'post %d' % i
            for i in range(num_posts)
        ]


class FauxBuilder(object):

    def __init__(self):
        self.env = FauxEnv()


class FauxApp(object):

    def __init__(self):
        self.builder = FauxBuilder()
        self.config = FauxConfig()


class TestRSSItemCount(utils.BaseTinkererTest):

    def setUp(self):
        super(utils.BaseTinkererTest, self).setUp()
        self.app = FauxApp()

    @mock.patch('tinkerer.ext.rss.make_feed_context')
    def test_more_posts_than_max(self, make_feed_context):
        self.app.config.rss_max_items = 1
        # Call the mocked function for creating the feed context and
        # verify the number of items it contains.
        list(rss.generate_feed(self.app))
        make_feed_context.assert_called_once_with(
            self.app,
            None,
            [self.app.builder.env.blog_posts[0]],
        )

    @mock.patch('tinkerer.ext.rss.make_feed_context')
    def test_fewer_posts_than_max(self, make_feed_context):
        self.app.config.rss_max_items = 10
        # Call the mocked function for creating the feed context and
        # verify the number of items it contains.
        list(rss.generate_feed(self.app))
        make_feed_context.assert_called_once_with(
            self.app,
            None,
            self.app.builder.env.blog_posts,
        )

    @mock.patch('tinkerer.ext.rss.make_feed_context')
    def test_same_posts_and_max(self, make_feed_context):
        self.app.config.rss_max_items = len(self.app.builder.env.blog_posts)
        # Call the mocked function for creating the feed context and
        # verify the number of items it contains.
        list(rss.generate_feed(self.app))
        make_feed_context.assert_called_once_with(
            self.app,
            None,
            self.app.builder.env.blog_posts,
        )

    @mock.patch('tinkerer.ext.rss.make_feed_context')
    def test_no_posts(self, make_feed_context):
        make_feed_context.side_effect = AssertionError('should not be called')
        self.app.builder.env.blog_posts = []
        list(rss.generate_feed(self.app))


class TestRSSTitle(utils.BaseTinkererTest):

    def setUp(self):
        super(utils.BaseTinkererTest, self).setUp()
        self.app = FauxApp()

    def test_with_title(self):
        context = rss.make_feed_context(self.app, 'title here', [])
        self.assertTrue('faux project' in context['title'])
        self.assertTrue('title here' in context['title'])

    def test_without_title(self):
        context = rss.make_feed_context(self.app, None, [])
        self.assertEqual('faux project', context['title'])

########NEW FILE########
__FILENAME__ = test_tags
'''
    Tags Test
    ~~~~~~~~~

    Tests Tinkerer post tags.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import datetime
import os
from tinkerer import paths, post
from tinkertest import utils


# test case
class TestTags(utils.BaseTinkererTest):
    def test_tags(self):
        utils.test = self

        # create some tagged posts
        for new_post in [("Post1", "tag #1"),
                         ("Post2", "tag #2"),
                         ("Post12", "tag #1, tag #2")]:
            p = post.create(new_post[0], datetime.date(2010, 10, 1))
            p.write(tags=new_post[1])

        utils.hook_extension("test_tags")
        self.build()


# test tags through extension
def build_finished(app, exception):
    blog_tags = app.builder.env.filing["tags"]

    # check collected tags
    utils.test.assertEquals(set(["tag #1", "tag #2"]), set(blog_tags))

    # check tagged posts
    for result in [(set(["2010/10/01/post1", "2010/10/01/post12"]), "tag #1"),
                   (set(["2010/10/01/post2", "2010/10/01/post12"]), "tag #2")]:
        utils.test.assertEquals(result[0], set(blog_tags[result[1]]))

    # check post metadata
    for result in [([("tag__1", "tag #1")], "2010/10/01/post1"),
                   ([("tag__2", "tag #2")], "2010/10/01/post2"),
                   ([("tag__1", "tag #1"), ("tag__2", "tag #2")],
                    "2010/10/01/post12")]:
        utils.test.assertEquals(
            result[0],
            app.builder.env.blog_metadata[result[1]].filing["tags"])

    # check tag pages were generated
    for page in ["tag__1.html", "tag__2.html"]:
        utils.test.assertTrue(os.path.exists(os.path.join(paths.html, "tags",
                                                          page)))


# extension setup
def setup(app):
    if utils.is_module(app):
        return
    app.connect("build-finished", build_finished)

########NEW FILE########
__FILENAME__ = utils
'''
    Test utilities
    ~~~~~~~~~~~~~~

    Base test case class inherited by all test cases. Utility functions.

    :copyright: Copyright 2011-2014 by Vlad Riscutia and contributors (see
    CONTRIBUTORS file)
    :license: FreeBSD, see LICENSE file
'''
import os
import shutil
import sys
from tinkerer import cmdline, output, paths, writer
import types
import unittest


# test root directory
TEST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "root"))


# stored test instance to assert from extensions while running Sphinx build
test = None


# base tinkerer test case
class BaseTinkererTest(unittest.TestCase):
    # common setup
    def setUp(self):
        output.quiet = True
        setup()

    # invoke build
    def build(self):
        print("")
        self.assertEquals(0, cmdline.build())

    # common teardown - cleanup working directory
    def tearDown(self):
        cleanup()


# hook extension to conf.py
def hook_extension(ext):
    writer.write_conf_file(extensions=["tinkerer.ext.blog", ext])


# setup blog using TEST_ROOT working directory
def setup():
    # create path
    if not os.path.exists(TEST_ROOT):
        os.mkdir(TEST_ROOT)

    paths.set_paths(TEST_ROOT)

    # setup blog
    writer.setup_blog()


# cleanup test directory
def cleanup():
    if os.path.exists(TEST_ROOT):
        shutil.rmtree(TEST_ROOT)


# nose mistakenly calls Sphinx extension setup functions thinking they are
# test setups with a module parameter
def is_module(m):
    return isinstance(m, types.ModuleType)


# used by Sphinx to lookup extensions
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

########NEW FILE########
