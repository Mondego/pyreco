__FILENAME__ = wsgi
import os
from klaus import make_app

if 'KLAUS_HTDIGEST_FILE' in os.environ:
    with open(os.environ['KLAUS_HTDIGEST_FILE']) as file:
        application = make_app(
            os.environ['KLAUS_REPOS'].split(),
            os.environ['KLAUS_SITE_NAME'],
            os.environ.get('KLAUS_USE_SMARTHTTP'),
            file,
        )
else:
    application = make_app(
        os.environ['KLAUS_REPOS'].split(),
        os.environ['KLAUS_SITE_NAME'],
        os.environ.get('KLAUS_USE_SMARTHTTP'),
        None,
    )

########NEW FILE########
__FILENAME__ = wsgi_autoreload
import os
import time
import threading
from klaus import make_app


# Shared state between poller and application wrapper
class _:
    #: the real WSGI app
    inner_app = None
    should_reload = True


def poll_for_changes(interval, dir):
    """
    Polls `dir` for changes every `interval` seconds and sets `should_reload`
    accordingly.
    """
    old_contents = os.listdir(dir)
    while 1:
        time.sleep(interval)
        if _.should_reload:
            # klaus application has not seen our change yet
            continue
        new_contents = os.listdir(dir)
        if new_contents != old_contents:
            # Directory contents changed => should_reload
            new_contents = old_contents
            _.should_reload = True


def make_autoreloading_app(repos_root, *args, **kwargs):
    def app(environ, start_response):
        if _.should_reload:
            # Refresh inner application with new repo list
            print "Reloading repository list..."
            _.inner_app = make_app(
                [os.path.join(repos_root, x) for x in os.listdir(repos_root)],
                *args, **kwargs
            )
            _.should_reload = False
        return _.inner_app(environ, start_response)

    # Background thread that polls the directory for changes
    poller_thread = threading.Thread(target=(lambda: poll_for_changes(10, repos_root)))
    poller_thread.daemon = True
    poller_thread.start()

    return app


if 'KLAUS_HTDIGEST_FILE' in os.environ:
    with open(os.environ['KLAUS_HTDIGEST_FILE']) as file:
        application = make_app(
            os.environ['KLAUS_REPOS'].split(),
            os.environ['KLAUS_SITE_NAME'],
            os.environ.get('KLAUS_USE_SMARTHTTP'),
            file,
        )
else:
    application = make_autoreloading_app(
        os.environ['KLAUS_REPOS'].split(),
        os.environ['KLAUS_SITE_NAME'],
        os.environ.get('KLAUS_USE_SMARTHTTP'),
        None,
    )

########NEW FILE########
__FILENAME__ = diff
# -*- coding: utf-8 -*-
"""
    lodgeit.lib.diff
    ~~~~~~~~~~~~~~~~

    Render a nice diff between two things.

    :copyright: 2007 by Armin Ronacher.
    :license: BSD
"""
import re
from cgi import escape


def prepare_udiff(udiff, **kwargs):
    """Prepare an udiff for a template."""
    return DiffRenderer(udiff).prepare(**kwargs)


class DiffRenderer(object):
    """Give it a unified diff and it renders you a beautiful
    html diff :-)
    """
    _chunk_re = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')

    def __init__(self, udiff):
        """:param udiff:   a text in udiff format"""
        self.lines = [escape(line) for line in udiff.splitlines()]

    def _extract_rev(self, line1, line2):
        def _extract(line):
            parts = line.split(None, 1)
            if parts[0].startswith(('a/', 'b/')):
                parts[0] = parts[0][2:]
            return parts[0], (len(parts) == 2 and parts[1] or None)
        try:
            if line1.startswith('--- ') and line2.startswith('+++ '):
                return _extract(line1[4:]), _extract(line2[4:])
        except (ValueError, IndexError):
            pass
        return (None, None), (None, None)

    def _highlight_line(self, line, next):
        """Highlight inline changes in both lines."""
        start = 0
        limit = min(len(line['line']), len(next['line']))
        while start < limit and line['line'][start] == next['line'][start]:
            start += 1
        end = -1
        limit -= start
        while -end <= limit and line['line'][end] == next['line'][end]:
            end -= 1
        end += 1
        if start or end:
            def do(l):
                last = end + len(l['line'])
                if l['action'] == 'add':
                    tag = 'ins'
                else:
                    tag = 'del'
                l['line'] = u'%s<%s>%s</%s>%s' % (
                    l['line'][:start],
                    tag,
                    l['line'][start:last],
                    tag,
                    l['line'][last:]
                )
            do(line)
            do(next)

    def prepare(self, want_header=True):
        """Parse the diff an return data for the template."""
        in_header = True
        header = []
        lineiter = iter(self.lines)
        files = []
        try:
            line = lineiter.next()
            while 1:
                # continue until we found the old file
                if not line.startswith('--- '):
                    if in_header:
                        header.append(line)
                    line = lineiter.next()
                    continue

                if header and all(x.strip() for x in header):
                    if want_header:
                        files.append({'is_header': True, 'lines': header})
                    header = []

                in_header = False
                chunks = []
                old, new = self._extract_rev(line, lineiter.next())
                adds, dels = 0, 0
                files.append({
                    'is_header':        False,
                    'old_filename':     old[0],
                    'old_revision':     old[1],
                    'new_filename':     new[0],
                    'new_revision':     new[1],
                    'additions':        adds,
                    'deletions':        dels,
                    'chunks':           chunks
                })

                line = lineiter.next()
                while line:
                    match = self._chunk_re.match(line)
                    if not match:
                        in_header = True
                        break

                    lines = []
                    chunks.append(lines)

                    old_line, old_end, new_line, new_end = \
                        [int(x or 1) for x in match.groups()]
                    old_line -= 1
                    new_line -= 1
                    old_end += old_line
                    new_end += new_line
                    line = lineiter.next()

                    while old_line < old_end or new_line < new_end:
                        if line:
                            command, line = line[0], line[1:]
                        else:
                            command = ' '
                        affects_old = affects_new = False

                        if command == '+':
                            affects_new = True
                            action = 'add'
                            adds += 1
                        elif command == '-':
                            affects_old = True
                            action = 'del'
                            dels += 1
                        else:
                            affects_old = affects_new = True
                            action = 'unmod'

                        old_line += affects_old
                        new_line += affects_new
                        lines.append({
                            'old_lineno':   affects_old and old_line or u'',
                            'new_lineno':   affects_new and new_line or u'',
                            'action':       action,
                            'line':         line
                        })
                        # Make sure to store the stats before a
                        # StopIteration is raised
                        files[-1]['additions'] = adds
                        files[-1]['deletions'] = dels
                        line = lineiter.next()

        except StopIteration:
            pass

        # highlight inline changes
        for file in files:
            if file['is_header']:
                continue
            for chunk in file['chunks']:
                lineiter = iter(chunk)
                try:
                    while True:
                        line = lineiter.next()
                        if line['action'] != 'unmod':
                            nextline = lineiter.next()
                            if nextline['action'] == 'unmod' or \
                               nextline['action'] == line['action']:
                                continue
                            self._highlight_line(line, nextline)
                except StopIteration:
                    pass

        return files

########NEW FILE########
__FILENAME__ = markup
import os

LANGUAGES = []


def get_renderer(filename):
    _, ext = os.path.splitext(filename)
    for extensions, renderer in LANGUAGES:
        if ext in extensions:
            return renderer


def can_render(filename):
    return get_renderer(filename) is not None


def render(filename, content=None):
    if content is None:
        content = open(filename).read()

    return get_renderer(filename)(content)


def _load_markdown():
    try:
        import markdown
    except ImportError:
        return

    def render_markdown(content):
        return markdown.markdown(content, extensions=['toc', 'extra'])

    LANGUAGES.append((['.md', '.mkdn', '.markdown'], render_markdown))


def _load_restructured_text():
    try:
        from docutils.core import publish_parts
        from docutils.writers.html4css1 import Writer
    except ImportError:
        return

    def render_rest(content):
        # start by h2 and ignore invalid directives and so on
        # (most likely from Sphinx)
        settings = {'initial_header_level': 2, 'report_level': 'quiet'}
        return publish_parts(content,
                             writer=Writer(),
                             settings_overrides=settings).get('html_body')

    LANGUAGES.append((['.rst', '.rest'], render_rest))


for loader in [_load_markdown, _load_restructured_text]:
    loader()

########NEW FILE########
__FILENAME__ = repo
import os
import cStringIO

import dulwich, dulwich.patch

from klaus.utils import check_output, force_unicode
from klaus.diff import prepare_udiff


class FancyRepo(dulwich.repo.Repo):
    # TODO: factor out stuff into dulwich
    @property
    def name(self):
        # 1. /x/y.git -> /x/y  and  /x/y/.git/ -> /x/y//
        # 2. /x/y/ -> /x/y
        # 3. /x/y -> y
        return self.path.replace(".git", "").rstrip(os.sep).split(os.sep)[-1]

    def get_last_updated_at(self):
        refs = [self[ref_hash] for ref_hash in self.get_refs().itervalues()]
        refs.sort(key=lambda obj:getattr(obj, 'commit_time', None),
                  reverse=True)
        if refs:
            return refs[0].commit_time
        return None

    def get_description(self):
        """
        Like Dulwich's `get_description`, but returns None if the file contains
        Git's default text "Unnamed repository[...]"
        """
        description = super(FancyRepo, self).get_description()
        if description:
            if not description.startswith("Unnamed repository;"):
                return force_unicode(description)

    def get_commit(self, rev):
        rev = str(rev)  # https://github.com/jelmer/dulwich/issues/144
        for prefix in ['refs/heads/', 'refs/tags/', '']:
            key = prefix + rev
            try:
                obj = self[key]
                if isinstance(obj, dulwich.objects.Tag):
                    obj = self[obj.object[1]]
                return obj
            except KeyError:
                pass
        raise KeyError(rev)

    def get_default_branch(self):
        """
        Tries to guess the default repo branch name.
        """
        for candidate in ['master', 'trunk', 'default', 'gh-pages']:
            try:
                self.get_commit(candidate)
                return candidate
            except KeyError:
                pass
        try:
            return self.get_branch_names()[0]
        except IndexError:
            return None

    def get_sorted_ref_names(self, prefix, exclude=None):
        refs = self.refs.as_dict(prefix)
        if exclude:
            refs.pop(prefix + exclude, None)

        def get_commit_time(refname):
            obj = self[refs[refname]]
            if isinstance(obj, dulwich.objects.Tag):
                return obj.tag_time
            return obj.commit_time

        return sorted(refs.iterkeys(), key=get_commit_time, reverse=True)

    def get_branch_names(self, exclude=None):
        """ Returns a sorted list of branch names. """
        return self.get_sorted_ref_names('refs/heads', exclude)

    def get_tag_names(self):
        """ Returns a sorted list of tag names. """
        return self.get_sorted_ref_names('refs/tags')

    def history(self, commit, path=None, max_commits=None, skip=0):
        """
        Returns a list of all commits that infected `path`, starting at branch
        or commit `commit`. `skip` can be used for pagination, `max_commits`
        to limit the number of commits returned.

        Similar to `git log [branch/commit] [--skip skip] [-n max_commits]`.
        """
        # XXX The pure-Python/dulwich code is very slow compared to `git log`
        #     at the time of this writing (mid-2012).
        #     For instance, `git log .tx` in the Django root directory takes
        #     about 0.15s on my machine whereas the history() method needs 5s.
        #     Therefore we use `git log` here until dulwich gets faster.
        #     For the pure-Python implementation, see the 'purepy-hist' branch.

        cmd = ['git', 'log', '--format=%H']
        if skip:
            cmd.append('--skip=%d' % skip)
        if max_commits:
            cmd.append('--max-count=%d' % max_commits)
        cmd.append(commit)
        if path:
            cmd.extend(['--', path])

        sha1_sums = check_output(cmd, cwd=os.path.abspath(self.path))
        return [self[sha1] for sha1 in sha1_sums.strip().split('\n')]

    def get_blob_or_tree(self, commit, path):
        """ Returns the Git tree or blob object for `path` at `commit`. """
        tree_or_blob = self[commit.tree]  # Still a tree here but may turn into
                                          # a blob somewhere in the loop.
        for part in path.strip('/').split('/'):
            if part:
                if isinstance(tree_or_blob, dulwich.objects.Blob):
                    # Blobs don't have sub-files/folders.
                    raise KeyError
                tree_or_blob = self[tree_or_blob[part][1]]
        return tree_or_blob

    def commit_diff(self, commit):
        from klaus.utils import guess_is_binary, force_unicode

        if commit.parents:
            parent_tree = self[commit.parents[0]].tree
        else:
            parent_tree = None

        summary = {'nfiles': 0, 'nadditions':  0, 'ndeletions':  0}
        file_changes = []  # the changes in detail

        dulwich_changes = self.object_store.tree_changes(parent_tree, commit.tree)
        for (oldpath, newpath), (oldmode, newmode), (oldsha, newsha) in dulwich_changes:
            summary['nfiles'] += 1

            try:
                # Check for binary files -- can't show diffs for these
                if newsha and guess_is_binary(self[newsha]) or \
                   oldsha and guess_is_binary(self[oldsha]):
                    file_changes.append({
                        'is_binary': True,
                        'old_filename': oldpath or '/dev/null',
                        'new_filename': newpath or '/dev/null',
                        'chunks': None
                    })
                    continue
            except KeyError:
                # newsha/oldsha are probably related to submodules.
                # Dulwich will handle that.
                pass

            stringio = cStringIO.StringIO()
            dulwich.patch.write_object_diff(stringio, self.object_store,
                                            (oldpath, oldmode, oldsha),
                                            (newpath, newmode, newsha))
            files = prepare_udiff(force_unicode(stringio.getvalue()),
                                  want_header=False)
            if not files:
                # the diff module doesn't handle deletions/additions
                # of empty files correctly.
                file_changes.append({
                    'old_filename': oldpath or '/dev/null',
                    'new_filename': newpath or '/dev/null',
                    'chunks': [],
                    'additions': 0,
                    'deletions': 0,
                })
            else:
                change = files[0]
                summary['nadditions'] += change['additions']
                summary['ndeletions'] += change['deletions']
                file_changes.append(change)

        return summary, file_changes

########NEW FILE########
__FILENAME__ = utils
# encoding: utf-8
import os
import re
import time
import datetime
import mimetypes
import locale
try:
    import chardet
except ImportError:
    chardet = None

from pygments import highlight
from pygments.lexers import get_lexer_for_filename, guess_lexer, ClassNotFound, TextLexer
from pygments.formatters import HtmlFormatter

from humanize import naturaltime

from klaus import markup


class SubUri(object):
    """
    WSGI middleware that tweaks the WSGI environ so that it's possible to serve
    the wrapped app (klaus) under a sub-URL and/or to use a different HTTP
    scheme (http:// vs. https://) for proxy communication.

    This is done by making your proxy pass appropriate HTTP_X_SCRIPT_NAME and
    HTTP_X_SCHEME headers.

    For instance if you have klaus mounted under /git/ and your site uses SSL
    (but your proxy doesn't), make it pass ::

        X-Script-Name = '/git'
        X-Scheme = 'https'

    Snippet stolen from http://flask.pocoo.org/snippets/35/
    """
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name.rstrip('/')

        if script_name and environ['PATH_INFO'].startswith(script_name):
            # strip `script_name` from PATH_INFO
            environ['PATH_INFO'] = environ['PATH_INFO'][len(script_name):]

        if 'HTTP_X_SCHEME' in environ:
            environ['wsgi.url_scheme'] = environ['HTTP_X_SCHEME']

        return self.app(environ, start_response)


class KlausFormatter(HtmlFormatter):
    def __init__(self):
        HtmlFormatter.__init__(self, linenos='table', lineanchors='L',
                               anchorlinenos=True)

    def _format_lines(self, tokensource):
        for tag, line in HtmlFormatter._format_lines(self, tokensource):
            if tag == 1:
                # sourcecode line
                line = '<span class=line>%s</span>' % line
            yield tag, line


def pygmentize(code, filename=None, render_markup=True):
    """
    Renders code using Pygments, markup (markdown, rst, ...) using the
    corresponding renderer, if available.
    """
    if render_markup and markup.can_render(filename):
        return markup.render(filename, code)

    try:
        lexer = get_lexer_for_filename(filename, code)
    except ClassNotFound:
        try:
            lexer = guess_lexer(code)
        except ClassNotFound:
            lexer = TextLexer()
    return highlight(code, lexer, KlausFormatter())


def timesince(when, now=time.time):
    """ Returns the difference between `when` and `now` in human readable form. """
    return naturaltime(now() - when)


def formattimestamp(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%b %d, %Y - %H:%M:%S')


def guess_is_binary(dulwich_blob):
    return any('\0' in chunk for chunk in dulwich_blob.chunked)


def guess_is_image(filename):
    mime, _ = mimetypes.guess_type(filename)
    if mime is None:
        return False
    return mime.startswith('image/')


def force_unicode(s):
    """ Does all kind of magic to turn `s` into unicode """
    # It's already unicode, don't do anything:
    if isinstance(s, unicode):
        return s

    # Try some default encodings:
    try:
        return s.decode('utf-8')
    except UnicodeDecodeError as exc:
        pass
    try:
        return s.decode(locale.getpreferredencoding())
    except UnicodeDecodeError:
        pass

    if chardet is not None:
        # Try chardet, if available
        encoding = chardet.detect(s)['encoding']
        if encoding is not None:
            return s.decode(encoding)

    raise exc  # Give up.


def extract_author_name(email):
    """
    Extracts the name from an email address...
    >>> extract_author_name("John <john@example.com>")
    "John"

    ... or returns the address if none is given.
    >>> extract_author_name("noname@example.com")
    "noname@example.com"
    """
    match = re.match('^(.*?)<.*?>$', email)
    if match:
        return match.group(1).strip()
    return email


def shorten_sha1(sha1):
    if re.match('[a-z\d]{20,40}', sha1):
        sha1 = sha1[:10]
    return sha1


def parent_directory(path):
    return os.path.split(path)[0]


def subpaths(path):
    """
    Yields a `(last part, subpath)` tuple for all possible sub-paths of `path`.

    >>> list(subpaths("foo/bar/spam"))
    [('foo', 'foo'), ('bar', 'foo/bar'), ('spam', 'foo/bar/spam')]
    """
    seen = []
    for part in path.split('/'):
        seen.append(part)
        yield part, '/'.join(seen)


def shorten_message(msg):
    return msg.split('\n')[0]


try:
    from subprocess import check_output
except ImportError:
    # Python < 2.7 fallback, stolen from the 2.7 stdlib
    def check_output(*popenargs, **kwargs):
        from subprocess import Popen, PIPE, CalledProcessError
        if 'stdout' in kwargs:
            raise ValueError('stdout argument not allowed, it will be overridden.')
        process = Popen(stdout=PIPE, *popenargs, **kwargs)
        output, _ = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise CalledProcessError(retcode, cmd, output=output)
        return output


def guess_git_revision():
    git_dir = os.path.join(os.path.dirname(__file__), '..', '.git')
    if os.path.exists(git_dir):
        return check_output(
            ['git', 'log', '--format=%h', '-n', '1'],
            cwd=git_dir
        ).strip()

########NEW FILE########
__FILENAME__ = views
import os
import stat

from flask import request, render_template, current_app
from flask.views import View

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotFound

from dulwich.objects import Blob

from klaus import markup
from klaus.utils import parent_directory, subpaths, pygmentize, \
                        force_unicode, guess_is_binary, guess_is_image


def repo_list():
    """Shows a list of all repos and can be sorted by last update. """
    if 'by-last-update' in request.args:
        sort_key = lambda repo: repo.get_last_updated_at()
        reverse = True
    else:
        sort_key = lambda repo: repo.name
        reverse = False
    repos = sorted(current_app.repos, key=sort_key, reverse=reverse)
    return render_template('repo_list.html', repos=repos)

def robots_txt():
    """Serves the robots.txt file to manage the indexing of the site by search enginges"""
    return current_app.send_static_file('robots.txt')

class BaseRepoView(View):
    """
    Base for all views with a repo context.

    The arguments `repo`, `rev`, `path` (see `dispatch_request`) define the
    repository, branch/commit and directory/file context, respectively --
    that is, they specify what (and in what state) is being displayed in all the
    derived views.

    For example: The 'history' view is the `git log` equivalent, i.e. if `path`
    is "/foo/bar", only commits related to "/foo/bar" are displayed, and if
    `rev` is "master", the history of the "master" branch is displayed.
    """
    def __init__(self, view_name, template_name=None):
        self.view_name = view_name
        self.template_name = template_name
        self.context = {}

    def dispatch_request(self, repo, rev=None, path=''):
        self.make_template_context(repo, rev, path.strip('/'))
        return self.get_response()

    def get_response(self):
        return render_template(self.template_name, **self.context)

    def make_template_context(self, repo, rev, path):
        try:
            repo = current_app.repo_map[repo]
        except KeyError:
            raise NotFound("No such repository %r" % repo)

        if rev is None:
            rev = repo.get_default_branch()
            if rev is None:
                raise NotFound("Empty repository")
        try:
            commit = repo.get_commit(rev)
        except KeyError:
            raise NotFound("No such commit %r" % rev)

        try:
            blob_or_tree = repo.get_blob_or_tree(commit, path)
        except KeyError:
            raise NotFound("File not found")

        self.context = {
            'view': self.view_name,
            'repo': repo,
            'rev': rev,
            'commit': commit,
            'branches': repo.get_branch_names(exclude=rev),
            'tags': repo.get_tag_names(),
            'path': path,
            'blob_or_tree': blob_or_tree,
            'subpaths': list(subpaths(path)) if path else None,
        }


class TreeViewMixin(object):
    """
    Implements the logic required for displaying the current directory in the sidebar
    """
    def make_template_context(self, *args):
        super(TreeViewMixin, self).make_template_context(*args)
        self.context['root_tree'] = self.listdir()

    def listdir(self):
        """
        Returns a list of directories and files in the current path of the
        selected commit
        """
        root_directory = self.get_root_directory()
        root_tree = self.context['repo'].get_blob_or_tree(
            self.context['commit'],
            root_directory
        )

        dirs, files = [], []
        for entry in root_tree.iteritems():
            name, entry = entry.path, entry.in_path(root_directory)
            if entry.mode & stat.S_IFDIR:
                dirs.append((name.lower(), name, entry.path))
            else:
                files.append((name.lower(), name, entry.path))
        files.sort()
        dirs.sort()

        if root_directory:
            dirs.insert(0, (None, '..', parent_directory(root_directory)))

        return {'dirs' : dirs, 'files' : files}

    def get_root_directory(self):
        root_directory = self.context['path']
        if isinstance(self.context['blob_or_tree'], Blob):
            # 'path' is a file (not folder) name
            root_directory = parent_directory(root_directory)
        return root_directory


class HistoryView(TreeViewMixin, BaseRepoView):
    """ Show commits of a branch + path, just like `git log`. With pagination. """
    def make_template_context(self, *args):
        super(HistoryView, self).make_template_context(*args)

        try:
            page = int(request.args.get('page'))
        except (TypeError, ValueError):
            page = 0

        self.context['page'] = page

        if page:
            history_length = 30
            skip = (self.context['page']-1) * 30 + 10
            if page > 7:
                self.context['previous_pages'] = [0, 1, 2, None] + range(page)[-3:]
            else:
                self.context['previous_pages'] = xrange(page)
        else:
            history_length = 10
            skip = 0

        history = self.context['repo'].history(
            self.context['rev'],
            self.context['path'],
            history_length + 1,
            skip
        )
        if len(history) == history_length + 1:
            # At least one more commit for next page left
            more_commits = True
            # We don't want show the additional commit on this page
            history.pop()
        else:
            more_commits = False

        self.context.update({
            'history': history,
            'more_commits': more_commits,
        })


class BlobViewMixin(object):
    def make_template_context(self, *args):
        super(BlobViewMixin, self).make_template_context(*args)
        self.context['filename'] = os.path.basename(self.context['path'])


class BlobView(BlobViewMixin, TreeViewMixin, BaseRepoView):
    """ Shows a file rendered using ``pygmentize`` """
    def make_template_context(self, *args):
        super(BlobView, self).make_template_context(*args)

        if not isinstance(self.context['blob_or_tree'], Blob):
            raise NotFound("Not a blob")

        binary = guess_is_binary(self.context['blob_or_tree'])
        too_large = sum(map(len, self.context['blob_or_tree'].chunked)) > 100*1024

        if binary:
            self.context.update({
                'is_markup': False,
                'is_binary': True,
                'is_image': False,
            })
            if guess_is_image(self.context['filename']):
                self.context.update({
                    'is_image': True,
                })
        elif too_large:
            self.context.update({
                'too_large': True,
                'is_markup': False,
                'is_binary': False,
            })
        else:
            render_markup = 'markup' not in request.args
            rendered_code = pygmentize(
                force_unicode(self.context['blob_or_tree'].data),
                self.context['filename'],
                render_markup
            )
            self.context.update({
                'too_large': False,
                'is_markup': markup.can_render(self.context['filename']),
                'render_markup': render_markup,
                'rendered_code': rendered_code,
                'is_binary': False,
            })


class RawView(BlobViewMixin, BaseRepoView):
    """
    Shows a single file in raw for (as if it were a normal filesystem file
    served through a static file server)
    """
    def get_response(self):
        return Response(self.context['blob_or_tree'].chunked)


#                                     TODO v
history = HistoryView.as_view('history', 'history', 'history.html')
commit = BaseRepoView.as_view('commit', 'commit', 'view_commit.html')
blob = BlobView.as_view('blob', 'blob', 'view_blob.html')
raw = RawView.as_view('raw', 'raw')

########NEW FILE########
__FILENAME__ = dumbtest
""" Very dumb testing tool: Ensures all sites respond with HTTP 2xx/3xx """
import sys
import re
import time
import httplib
from collections import defaultdict
import atexit

def view_from_url(url):
    try:
        return url.split('/')[2]
    except IndexError:
        return url

AHREF_RE = re.compile('href="([\w/][^"]+)"')

seen = set()
errors = defaultdict(set)
durations = defaultdict(list)

def main():
    urls = {'/'}
    while urls:
        try:
            http_conn.close()
        except NameError:
            pass
        http_conn = httplib.HTTPConnection('localhost', 8080)
        url = urls.pop()
        if url in seen:
            continue
        seen.add(url)
        if url.startswith('http'):
            continue
        if '-v' in sys.argv:
            print 'Requesting %r...' % url
        start = time.time()
        http_conn.request('GET', url)
        response = http_conn.getresponse()
        durations[view_from_url(url)].append(time.time() - start)
        status = str(response.status)
        if status[0] == '3':
            urls.add(response.getheader('Location'))
        elif status[0] == '2':
            if not '/raw/' in url:
                html = response.read()
                html = re.sub('<pre>.*?</pre>', '', html)
                urls.update(AHREF_RE.findall(html))
        else:
            if '--failfast' in sys.argv:
                print url, status
                exit(1)
            errors[status].add(url)

def print_stats():
    import pprint
    print len(seen)
    pprint.pprint(dict(errors))
    print {url: sum(times)/len(times) for url, times in durations.iteritems()}
atexit.register(print_stats)

main()

########NEW FILE########
