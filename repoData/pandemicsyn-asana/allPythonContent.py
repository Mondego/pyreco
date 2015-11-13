__FILENAME__ = asana
#!/usr/bin/env python

import requests
import time

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

try:
    import simplejson as json
except ImportError:
    import json

from pprint import pprint


class AsanaException(Exception):
    """Wrap api specific errors"""
    pass


class AsanaAPI(object):
    """Basic wrapper for the Asana api. For further information on the API
    itself see: http://developer.asana.com/documentation/
    """

    def __init__(self, apikey, debug=False):
        self.debug = debug
        self.asana_url = "https://app.asana.com/api"
        self.api_version = "1.0"
        self.aurl = "/".join([self.asana_url, self.api_version])
        self.apikey = apikey
        self.bauth = self.get_basic_auth()

    def get_basic_auth(self):
        """Get basic auth creds
        :returns: the basic auth string
        """
        s = self.apikey + ":"
        return s.encode("base64").rstrip()

    def handle_exception(self, r):
        """ Handle exceptions

        :param r: request object
        :param api_target: API URI path for requests
        :param data: payload
        :returns: 1 if exception was 429 (rate limit exceeded), otherwise, -1
        """
        if self.debug:
            print "-> Got: %s" % r.status_code
            print "-> %s" % r.text
        if (r.status_code == 429):
            self._handle_rate_limit(r)
            return 1
        else:
            raise AsanaException('Received non 2xx or 404 status code on call')

    def _handle_rate_limit(self, r):
        """ Sleep for length of retry time

        :param r: request object
        """
        retry_time = int(r.headers['Retry-After'])
        assert(retry_time > 0)
        if self.debug:
            print("-> Sleeping for %i seconds" % retry_time)
        time.sleep(retry_time)

    def _asana(self, api_target):
        """Peform a GET request

        :param api_target: API URI path for request
        """
        # TODO: Refactor to use requests.get params
        target = "/".join([self.aurl, quote(api_target, safe="/&=?")])
        if self.debug:
            print "-> Calling: %s" % target
        r = requests.get(target, auth=(self.apikey, ""))
        if self._ok_status(r.status_code) and r.status_code is not 404:
            if r.headers['content-type'].split(';')[0] == 'application/json':
                if hasattr(r, 'text'):
                    return json.loads(r.text)['data']
                elif hasattr(r, 'content'):
                    return json.loads(r.content)['data']
                else:
                    raise AsanaException('Unknown format in response from api')
            else:
                raise AsanaException(
                    'Did not receive json from api: %s' % str(r))
        else:
            if (self.handle_exception(r) > 0):
                return self._asana(api_target)

    def _asana_delete(self, api_target):
        """Peform a DELETE request

        :param api_target: API URI path for request
        """
        target = "/".join([self.aurl, quote(api_target, safe="/&=?")])
        if self.debug:
            print "-> Calling: %s" % target
        r = requests.delete(target, auth=(self.apikey, ""))
        if self._ok_status(r.status_code) and r.status_code is not 404:
            if r.headers['content-type'].split(';')[0] == 'application/json':
                if hasattr(r, 'text'):
                    return json.loads(r.text)['data']
                elif hasattr(r, 'content'):
                    return json.loads(r.content)['data']
                else:
                    raise AsanaException('Unknown format in response from api')
            else:
                raise AsanaException(
                    'Did not receive json from api: %s' % str(r))
        else:
            if (self.handle_exception(r) > 0):
                return self._asana_delete(api_target)

    def _asana_post(self, api_target, data=None, files=None):
        """Peform a POST request

        :param api_target: API URI path for request
        :param data: POST payload
        :param files: Optional file to upload
        """
        target = "/".join([self.aurl, api_target])
        if self.debug:
            print "-> Posting to: %s" % target
            if data:
                print "-> Post payload:"
                pprint(data)
            if files:
                print "-> Posting file:"
                pprint(files)
        r = requests.post(
            target, auth=(self.apikey, ""), data=data, files=files)
        if self._ok_status(r.status_code) and r.status_code is not 404:
            if r.headers['content-type'].split(';')[0] == 'application/json':
                if hasattr(r, 'text'):
                    return json.loads(r.text)['data']
                elif hasattr(r, 'content'):
                    return json.loads(r.content)['data']
                else:
                    raise AsanaException('Unknown format in response from api')
            else:
                raise AsanaException(
                    'Did not receive json from api: %s' % str(r))
        else:
            if (self.handle_exception(r) > 0):
                return self._asana_post(api_target, data)

    def _asana_put(self, api_target, data):
        """Peform a PUT request

        :param api_target: API URI path for request
        :param data: PUT payload
        """
        target = "/".join([self.aurl, api_target])
        if self.debug:
            print "-> PUTting to: %s" % target
            print "-> PUT payload:"
            pprint(data)
        r = requests.put(target, auth=(self.apikey, ""), data=data)
        if self._ok_status(r.status_code) and r.status_code is not 404:
            if r.headers['content-type'].split(';')[0] == 'application/json':
                if hasattr(r, 'text'):
                    return json.loads(r.text)['data']
                elif hasattr(r, 'content'):
                    return json.loads(r.content)['data']
                else:
                    raise AsanaException('Unknown format in response from api')
            else:
                raise AsanaException(
                    'Did not receive json from api: %s' % str(r))
        else:
            if (self.handle_exception(r) > 0):
                return self._asana_put(api_target, data)

    @classmethod
    def _ok_status(cls, status_code):
        """Check whether status_code is a ok status i.e. 2xx or 404"""
        status_code = int(status_code)
        if status_code / 200 is 1:
            return True
        elif status_code / 400 is 1:
            if status_code is 404:
                return True
            else:
                return False
        elif status_code is 500:
            return False

    def user_info(self, user_id="me"):
        """Obtain user info on yourself or other users.

        :param user_id: target user or self (default)
        """
        return self._asana('users/%s' % user_id)

    def list_users(self, workspace=None, filters=None):
        """List users

        :param workspace: list users in given workspace
        :param filters: Optional [] of filters you want to apply to listing
        """
        if workspace:
            return self._asana('workspaces/%s/users' % workspace)
        else:
            if filters:
                fkeys = [x.strip().lower() for x in filters]
                fields = ",".join(fkeys)
                return self._asana('users?opt_fields=%s' % fields)
            else:
                return self._asana('users')

    def list_tasks(self, workspace, assignee, include_archived=False,
                   completed_since=None, modified_since=None):
        """List tasks

        :param workspace: workspace id
        :param assignee: assignee
        :param include_archived: true to include archived tasks
        """
        # Sanitise our include_archived variable
        if include_archived:
            include_archived = "true"
        else:
            include_archived = "false"
        target = "tasks?workspace=%d&assignee=%s&include_archived=%s" % (
            workspace, assignee, include_archived)

        if completed_since:
            target += '&completed_since=%s' % completed_since
        if modified_since:
            target += '&modified_since=%s' % modified_since

        return self._asana(target)

    def get_task(self, task_id):
        """Get a task

        :param task_id: id# of task"""
        return self._asana("tasks/%d" % task_id)

    def get_subtasks(self, task_id):
        """Get subtasks associated with a given task

        :param task_id: id# of task"""
        return self._asana("tasks/%d/subtasks" % task_id)

    def list_projects(self, workspace=None, include_archived=True):
        """"List projects in a workspace

        :param workspace: workspace whos projects you want to list
        :param include_archived: defaults True, set to False to exclude """
        if include_archived:
            include_archived = "true"
        else:
            include_archived = "false"
        target = "projects?archived=%s" % (include_archived)
        if workspace:
            target = "workspaces/%d/" % (workspace) + target

        return self._asana(target)

    def get_project(self, project_id):
        """Get project

        :param project_id: id# of project
        """
        return self._asana('projects/%d' % project_id)

    def get_project_tasks(self, project_id, include_archived=False):
        """Get project tasks

        :param project_id: id# of project
        :param include_archived: true to include archived tasks
        """
        # Sanitise our include_archived variable
        if include_archived:
            include_archived = "true"
        else:
            include_archived = "false"
        return self._asana('projects/%d/tasks?include_archived=%s' % (
            project_id, include_archived))

    def list_stories(self, task_id):
        """List stories for task

        :param task_id: id# of task
        """
        return self._asana('tasks/%d/stories' % task_id)

    def get_story(self, story_id):
        """Get story

        :param story_id: id# of story
        """
        return self._asana('stories/%d' % story_id)

    def list_workspaces(self):
        """List workspaces"""
        return self._asana('workspaces')

    def organization_teams(self, org_id):
        """Show all `teams <http://developer.asana.com/documentation/#teams>`
        you're member of in an
        `organization <https://asana.com/guide/workspaces/organizations>`.

        :param org_id organization id#
        """
        return self._asana('organizations/%d/teams' % org_id)

    def create_task(self, name, workspace, assignee=None, assignee_status=None,
                    completed=False, due_on=None, followers=None, notes=None,
                    projects=None):
        """Create a new task

        :param name: Name of task
        :param workspace: Workspace for task
        :param assignee: Optional assignee for task
        :param assignee_status: status
        :param completed: Whether this task is completed (defaults to False)
        :param due_on: Optional due date for task
        :param followers: Optional followers for task
        :param notes: Optional notes to add to task
        :param projects: Array of projects this task is associated with.
        """
        payload = {'name': name, 'workspace': workspace}
        if assignee:
            payload['assignee'] = assignee
        if assignee_status in ['inbox', 'later', 'today', 'upcoming']:
            payload['assignee_status'] = assignee_status
        if completed:
            payload['completed'] = 'true'
        if due_on:
            try:
                time.strptime(due_on, '%Y-%m-%d')
                payload['due_on'] = due_on
            except ValueError:
                raise AsanaException('Bad task due date: %s' % due_on)
        if followers:
            for pos, person in enumerate(followers):
                payload['followers[%d]' % pos] = person
        if projects:
            for pos, project in enumerate(projects):
                payload['projects[%d]' % pos] = project
        if notes:
            payload['notes'] = notes

        return self._asana_post('tasks', payload)

    def update_task(self, task, name=None, assignee=None, assignee_status=None,
                    completed=False, due_on=None, notes=None):
        """Update an existing task

        :param task: task to update
        :param name: Update task name
        :param assignee: Update assignee
        :param assignee_status: Update status
        :param completed: Update whether the task is completed
        :param due_on: Update due date
        :param notes: Update notes
        """
        payload = {}
        if name:
            payload['name'] = name
        if assignee:
            payload['assignee'] = assignee
        if assignee_status:
            payload['assignee_status'] = assignee_status
        if completed:
            payload['completed'] = completed
        if due_on:
            try:
                time.strptime(due_on, '%Y-%m-%d')
                payload['due_on'] = due_on
            except ValueError:
                raise AsanaException('Bad task due date: %s' % due_on)
        if notes:
            payload['notes'] = notes

        return self._asana_put('tasks/%s' % task, payload)

    def task_attachments(self, task_id):
        """Showing all attachments on a task.

        :param task_id: id# of a task
        """
        return self._asana('tasks/%d/attachments' % task_id)

    def get_attachment(self, attachment_id):
        """This method returns the full record for a single attachment.

        :param attachment_id: id# of an attachment
        """
        return self._asana('attachments/%d' % attachment_id)

    def upload_attachment(self, task_id, file_name, stream):
        """This method uploads an attachment to a task.

        :param task_id: id# of an a task
        :param file_name: attachment's file name
        :param stream: open file handle
        """
        return self._asana_post(
            'tasks/%d/attachments' % task_id,
            files={'file': (file_name, stream)}
        )

    def add_parent(self, task_id, parent_id):
        """Set the parent for an existing task.

        :param task_id: id# of a task
        :param parent_id: id# of a parent task
        """
        return self._asana_post('tasks/%s/setParent' % task_id,
                                {'parent': parent_id})

    def create_subtask(self, parent_id, name, completed=False, assignee=None,
                       notes=None, followers=None, assignee_status=None,
                       due_on=None):
        """Creates a task and sets it's parent.
        There is one noticeable distinction between
        creating task and assigning it a parent and
        creating a subtask. Latter doesn't get reflected
        in the project task list. Only in the parent task description.
        So using this method you can avoid polluting task list with subtasks.

        :param parent_id: id# of a task that subtask will be assigned to
        :param name: subtask name
        :param assignee: Optional user id# of subtask assignee
        :param notes: Optional subtask description
        :param followers: Optional followers for subtask
        :param assignee_status: Optional status for assignee
        :param due_on: Due date in format YYYY-MM-DD"""
        payload = {'name': name}
        if assignee:
            payload['assignee'] = assignee
        if followers:
            for pos, person in enumerate(followers):
                payload['followers[%d]' % pos] = person
        if notes:
            payload['notes'] = notes
        if completed:
            payload['completed'] = 'true'
        if assignee_status in ['inbox', 'later', 'today', 'upcoming']:
            payload['assignee_status'] = assignee_status
        if due_on:
            try:
                time.strptime(due_on, '%Y-%m-%d')
                payload['due_on'] = due_on
            except ValueError:
                raise AsanaException('Bad task due date: %s' % due_on)
        return self._asana_post('tasks/%s/subtasks' % parent_id, payload)

    def create_project(self, name, workspace, team=None,
                       notes=None, archived=False):
        """Create a new project

        :param name: Name of project
        :param workspace: Workspace for task
        :param team: Optional id/name of the team this project is shared with
        :param notes: Optional notes to add
        :param archived: Whether or not project is archived (defaults to False)
        """
        payload = {'name': name, 'workspace': workspace, 'team': team}
        if notes:
            payload['notes'] = notes
        if archived:
            payload['archived'] = 'true'
        return self._asana_post('projects', payload)

    def update_project(self, project_id, name=None, notes=None,
                       archived=False):
        """Update project

        :param project_id: id# of project
        :param name: Update name
        :param notes: Update notes
        :param archived: Update archive status
        """
        payload = {}
        if name:
            payload['name'] = name
        if notes:
            payload['notes'] = notes
        if archived:
            payload['archived'] = 'true'
        return self._asana_put('projects/%s' % project_id, payload)

    def delete_project(self, project_id):
        """Delete project

        :param project_id: id# of project
        """
        return self._asana_delete('projects/%s' % project_id)

    def update_workspace(self, workspace_id, name):
        """Update workspace

        :param workspace_id: id# of workspace
        :param name: Update name
        """
        payload = {'name': name}
        return self._asana_put('workspaces/%s' % workspace_id, payload)

    def add_project_task(self, task_id, project_id):
        """Add project task

        :param task_id: id# of task
        :param project_id: id# of project
        """
        return self._asana_post('tasks/%d/addProject' % task_id,
                                {'project': project_id})

    def rm_project_task(self, task_id, project_id):
        """Remove a project from task

        :param task_id: id# of task
        :param project_id: id# of project
        """
        return self._asana_post('tasks/%d/removeProject' % task_id,
                                {'project': project_id})

    def add_story(self, task_id, text):
        """Add a story to task

        :param task_id: id# of task
        :param text: story contents
        """
        return self._asana_post('tasks/%d/stories' % task_id, {'text': text})

    def add_tag_task(self, task_id, tag_id):
        """Tag a task

        :param task_id: id# of task
        :param tag_id: id# of tag to add
        """
        return self._asana_post('tasks/%d/addTag' % task_id, {'tag': tag_id})

    def rm_tag_task(self, task_id, tag_id):
        """Remove a tag from a task.

        :param task_id: id# of task
        :param tag_id: id# of tag to remove
        """
        return self._asana_post('tasks/%d/removeTag' %
                                task_id, {'tag': tag_id})

    def get_task_tags(self, task_id):
        """List tags that are associated with a task.

        :param task_id: id# of task
        """
        return self._asana('tasks/%d/tags' % task_id)

    def get_tags(self, workspace):
        """Get available tags for workspace

        :param workspace: id# of workspace
        """
        return self._asana('workspaces/%d/tags' % workspace)

    def get_tag_tasks(self, tag_id):
        """Get tasks for a tag

        :param tag_id: id# of task
        """
        return self._asana('tags/%d/tasks' % tag_id)

    def create_tag(self, tag, workspace):
        """Create tag

        :param tag_name: name of the tag to be created
        :param workspace: id# of workspace in which tag is to be created
        """
        payload = {'name': tag, 'workspace': workspace}

        return self._asana_post('tags', payload)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# asana documentation build configuration file, created by
# sphinx-quickstart on Fri Sep  7 00:35:58 2012.
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
#sys.path.insert(0, os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'asana'
copyright = u'2012, Florian Hines'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0'
# The full version, including alpha/beta/rc tags.
release = '0.0.2'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'asanadoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'asana.tex', u'asana Documentation',
   u'Florian Hines', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'asana', u'asana Documentation',
     [u'Florian Hines'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'asana', u'asana Documentation',
   u'Florian Hines', 'asana', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
