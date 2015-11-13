__FILENAME__ = collabmap
#!/usr/bin/env python

import sys
import getpass
import itertools
import github

def printHeader(users):
    print """<html>
<head>
  <style type="text/css">
    tr.odd * {
      background: #bbf
    }
  </style>
</head>
<body>
<table>"""
    print "<thead><tr>"
    print "<th>Repo</th>"
    for u in users:
        print "  <th>%s</th>" % u
    print "<th>Repo</th>"
    print "</tr></thead>"

def printRepo(repo, allusers, repo_users, rowstylegen):

    print '<tr class="%s">' % rowstylegen.next()
    print "  <td><b>%s</b></td>" % repo

    for u in allusers:
        style = {True: 'user', False: 'notuser'}[u in repo_users]
        state = {True: u, False: '-'}[u in repo_users]
        print '  <td class="%s">%s</td>' % (style, state)

    print "  <td><b>%s</b></td>" % repo
    print "</th>"

def printFooter():
    print """
</table>
</body>
</html>"""

def usage():
    sys.stderr.write("Usage:  %s githubuser githubtoken > map.html\n"
                     % sys.argv[0])
    sys.exit(64)

if __name__ == '__main__':

    try:
        gh = github.GitHub(sys.argv[1], sys.argv[2])
    except IndexError:
        usage()

    rh = gh.repos.collaborators_all()

    allusers = set()
    for v in rh.itervalues():
        allusers.update(set(v))

    au = sorted(list(allusers))

    printHeader(au)

    rowstylegen = itertools.cycle(['odd', 'even'])

    print "<tbody>"
    for r in sorted(rh.keys()):
        printRepo(r, au, rh[r], rowstylegen)
    print "</tbody>"

    printFooter()

########NEW FILE########
__FILENAME__ = ghsearch
#!/usr/bin/env python
#
# Copyright (c) 2005-2008  Dustin Sallings <dustin@spy.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# <http://www.opensource.org/licenses/mit-license.php>
"""
Search script.
"""

import sys

import github

def usage():
    """display the usage and exit"""
    print "Usage:  %s keyword [keyword...]" % (sys.argv[0])
    sys.exit(1)

def mk_url(repo):
    return "http://github.com/%s/%s" % (repo.username, repo.name)

if __name__ == '__main__':
    g = github.GitHub()
    if len(sys.argv) < 2:
        usage()
    res = g.repos.search(' '.join(sys.argv[1:]))

    for repo in res:
        try:
            print "Found %s at %s" % (repo.name, mk_url(repo))
        except AttributeError:
            print "Bug: Couldn't format %s" % repo.__dict__

########NEW FILE########
__FILENAME__ = github
#!/usr/bin/env python
#
# Copyright (c) 2005-2008  Dustin Sallings <dustin@spy.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# <http://www.opensource.org/licenses/mit-license.php>
"""
Interface to github's API (v2).

Basic usage:

g = GitHub()

for r in g.user.search('dustin'):
    print r.name

See the GitHub docs or README.markdown for more usage.

Copyright (c) 2007  Dustin Sallings <dustin@spy.net>
"""

import sys
import xml
import xml.dom.minidom

try: import simplejson as json
except ImportError: import json

from urllib import urlencode

import hclient

def _string_parser(x):
    """Extract the data from the first child of the input."""
    return x.firstChild.data

_types = {
    'string': _string_parser,
    'integer': lambda x: int(_string_parser(x)),
    'float': lambda x: float(_string_parser(x)),
    'datetime': _string_parser,
    'boolean': lambda x: _string_parser(x) == 'true'
}

def _parse(el):
    """Generic response parser."""

    type = 'string'
    if el.attributes and 'type' in list(el.attributes.keys()):
        type = el.attributes['type'].value
    elif el.localName in _types:
        type = el.localName
    elif len(el.childNodes) > 1:
        # This is a container, find the child type
        type = None
        ch = el.firstChild
        while ch and not type:
            if ch.localName == 'type':
                type = ch.firstChild.data
            ch = ch.nextSibling

    if not type:
        raise Exception("Can't parse %s, known: %s"
                        % (el.toxml(), repr(list(_types.keys()))))

    return _types[type](el)

def parses(t):
    """Parser for a specific type in the github response."""
    def f(orig):
        orig.parses = t
        return orig
    return f

def with_temporary_mappings(m):
    """Allow temporary localized altering of type mappings."""
    def f(orig):
        def every(self, *args):
            global _types
            o = _types.copy()
            for k,v in list(m.items()):
                if v:
                    _types[k] = v
                else:
                    del _types[k]
            try:
                return orig(self, *args)
            finally:
                _types = o
        return every
    return f

@parses('array')
def _parseArray(el):
    rv = []
    ch = el.firstChild
    while ch:
        if ch.nodeType != xml.dom.Node.TEXT_NODE and ch.firstChild:
            rv.append(_parse(ch))
        ch=ch.nextSibling
    return rv

class BaseResponse(object):
    """Base class for XML Response Handling."""

    def __init__(self, el):
        ch = el.firstChild
        while ch:
            if ch.nodeType != xml.dom.Node.TEXT_NODE and ch.firstChild:
                ln = ch.localName.replace('-', '_')
                self.__dict__[ln] = _parse(ch)
            ch=ch.nextSibling

    def __repr__(self):
        return "<<%s>>" % str(self.__class__)

class User(BaseResponse):
    """A github user."""

    parses = 'user'

    def __repr__(self):
        return "<<User %s>>" % self.name

class Plan(BaseResponse):
    """A github plan."""

    parses = 'plan'

    def __repr__(self):
        return "<<Plan %s>>" % self.name

class Repository(BaseResponse):
    """A repository."""

    parses = 'repository'

    @property
    def owner_name(self):
        if hasattr(self, 'owner'):
            return self.owner
        else:
            return self.username

    def __repr__(self):
        return "<<Repository %s/%s>>" % (self.owner_name, self.name)

class PublicKey(BaseResponse):
    """A public key."""

    parses = 'public-key'
    title = 'untitled'

    def __repr__(self):
        return "<<Public key %s>>" % self.title

class Commit(BaseResponse):
    """A commit."""

    parses = 'commit'

    def __repr__(self):
        return "<<Commit: %s>>" % self.id

class Parent(Commit):
    """A commit parent."""

    parses = 'parent'

class Author(User):
    """A commit author."""

    parses = 'author'

class Committer(User):
    """A commit committer."""

    parses = 'committer'

class Issue(BaseResponse):
    """An issue within the issue tracker."""

    parses = 'issue'

    def __repr__(self):
        return "<<Issue #%d>>" % self.number

class IssueComment(BaseResponse):
    """ An issue comment within the issue tracker."""

    parses = 'comment'

    def __repr__(self):
        return "<<Comment #%s>>" % self.body

class Label(BaseResponse):
    """A Label within the issue tracker."""
    parses = 'label'

    def __repr__(self):
        return "<<Label $%s>>" % self.name

class Tree(BaseResponse):
    """A Tree object."""

    # Parsing is scoped to objects...
    def __repr__(self):
        return "<<Tree: %s>>" % self.name

class Blob(BaseResponse):
    """A Blob object."""

    # Parsing is scoped to objects...
    def __repr__(self):
        return "<<Blob: %s>>" % self.name

class Modification(BaseResponse):
    """A modification object."""

    # Parsing is scoped to usage
    def __repr__(self):
        return "<<Modification of %s>>" % self.filename

class Network(BaseResponse):
    """A network entry."""

    parses = 'network'

    def __repr__(self):
        return "<<Network of %s/%s>>" % (self.owner, self.name)

class Organization(BaseResponse):
    """An organization."""

    parses = 'organization'

    def __repr__(self):
        return "<<Organization %s>>" % getattr(self, 'name', self.login)

# Load the known types.
for __t in (t for t in list(globals().values()) if hasattr(t, 'parses')):
    _types[__t.parses] = __t

class BaseEndpoint(object):

    BASE_URL = 'https://github.com/api/v2/xml/'

    def __init__(self, user, token, fetcher):
        self.user = user
        self.token = token
        self.fetcher = fetcher

    def _raw_fetch(self, path, base=None, data=None, httpAuth=False, method=None):
        if not base:
            base = self.BASE_URL
        p = base + path
        args = ''
        if self.user and self.token and not httpAuth:
            params = '&'.join(['login=' + hclient.quote(self.user),
                               'token=' + hclient.quote(self.token)])
            if '?' in path:
                p += '&' + params
            else:
                p += '?' + params

        if httpAuth:
            return self.fetcher(p, data,
                                username=self.user, password=self.token,
                                method=method)
        else:
            return self.fetcher(p, data)

    def _fetch(self, path, parselang = False):
        rawfetch = self._raw_fetch(path).read()
        # Hack since Github languages API gives malformed XML
        if parselang:
            rawfetch = rawfetch.replace('#', 'sharp')
            rawfetch = rawfetch.replace('-', '')
            rawfetch = rawfetch.replace('+', 'p')
            rawfetch = rawfetch.replace(' Lisp', 'Lisp')
            rawfetch = rawfetch.replace('Visual Basic', 'VisualBasic')
            rawfetch = rawfetch.replace('Pure Data', 'PureData')
            rawfetch = rawfetch.replace('Max/MSP', 'MaxMSP')
        return xml.dom.minidom.parseString(rawfetch)

    def _jfetch(self, path, httpAuth=True):
        return json.load(self._raw_fetch(path, 'https://api.github.com/',
                                         httpAuth=httpAuth))

    def _jpost(self, path, data, httpAuth=True):
        return json.load(self._raw_fetch(path, 'https://api.github.com/',
                                         data=data,
                                         httpAuth=httpAuth))

    def _post(self, path, **kwargs):
        p = {'login': self.user, 'token': self.token}
        p.update(kwargs)
        return self.fetcher(self.BASE_URL + path, urlencode(p)).read()

    def _put(self, path, **kwargs):
        p = {'login': self.user, 'token': self.token}
        p.update(kwargs)
        # Setting PUT with urllib2: http://stackoverflow.com/questions/111945
        import urllib2
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(self.BASE_URL + path, data=hclient.urlencode(p))
        request.get_method = lambda: 'PUT'
        return opener.open(request).read()

    def _parsed(self, path):
        doc = self._fetch(path)
        return _parse(doc.documentElement)

    def _posted(self,path,**kwargs):
        stuff = self._post(path,**kwargs)
        doc = xml.dom.minidom.parseString(stuff)
        return _parse(doc.documentElement)

class UserEndpoint(BaseEndpoint):

    def search(self, query):
        """Search for a user."""
        return self._parsed('user/search/' + query)

    def show(self, username):
        """Get the info for a user."""
        return self._parsed('user/show/' + username)

    def keys(self):
        """Get the public keys for a user."""
        return self._parsed('user/keys')

    def removeKey(self, keyId):
        """Remove the key with the given ID (as retrieved from keys)"""
        self._post('user/key/remove', id=keyId)

    def addKey(self, name, key):
        """Add an ssh key."""
        self._post('user/key/add', name=name, key=key)

class RepositoryEndpoint(BaseEndpoint):

    def forUser(self, username, page=1):
        """Get the repositories for the given user."""
        return self._parsed('repos/show/' + username + "/?page=" + str(page))

    def branches(self, user, repo):
        """List the branches for a repo."""
        doc = self._fetch("repos/show/" + user + "/" + repo + "/branches")
        rv = {}
        for c in doc.documentElement.childNodes:
            if c.nodeType != xml.dom.Node.TEXT_NODE:
                rv[c.localName] = str(c.firstChild.data)
        return rv

    def languages(self, user, repo):
        """List the languages for a repo."""
        doc = self._fetch("repos/show/" + user + "/" + repo + "/languages", True)
        rv = {}
        for c in doc.documentElement.childNodes:
            if c.nodeType != xml.dom.Node.TEXT_NODE:
                rv[c.localName] = str(c.firstChild.data)
        return rv

    def tags(self, user, repo):
        """List the tags for a repo."""
        doc = self._fetch("repos/show/" + user + "/" + repo + "/tags")
        rv = {}
        for c in doc.documentElement.childNodes:
            if c.nodeType != xml.dom.Node.TEXT_NODE:
                rv[c.localName] = str(c.firstChild.data)
        return rv

    def search(self, term, **args):
        """Search for repositories.

        Accept arguments to filter the search:
        - start_page => specifies the page of the results to show
        - language   => limits the search to a programming language """

        path = 'repos/search/' + hclient.quote_plus(term)
        params = "&".join(["%s=%s" % (k, v) for k,v in list(args.items())])
        if params:
            path += '?%s' % params
        return self._parsed(path)

    def show(self, user, repo):
        """Lookup an individual repository."""
        return self._parsed('/'.join(['repos', 'show', user, repo]))

    def set(self, user, repo, **args):
        """Set repository parameters.

        Repository parameters include the following:

         - description
         - homepage
         - has_wiki
         - has_issues
         - has_downloads"""

        prepared_args = {}
        for k,v in list(args.items()):
            prepared_args['values[' + k + ']'] = v
        return self._post('/'.join(['repos', 'show', user, repo]),
                          **prepared_args)

    def watch(self, user, repo):
        """Watch a repository."""
        self._post('repos/watch/' + user + '/' + repo)

    def unwatch(self, user, repo):
        """Stop watching a repository."""
        self._post('repos/unwatch/' + user + '/' + repo)

    def watched(self, user):
        """Get watched repositories of a user."""
        return self._parsed('repos/watched/' + user)

    def network(self, user, repo):
        """Get the network for a given repo."""
        return self._parsed('repos/show/' + user + '/' + repo + '/network')

    def setVisible(self, repo, public=True):
        """Set the visibility of the given repository (owned by the current user)."""
        if public:
            path = 'repos/set/public/' + repo
        else:
            path = 'repos/set/private/' + repo
        self._post(path)

    def create(self, name, description='', homepage='', public=1):
        """Create a new repository."""
        self._post('repos/create', name=name, description=description,
                   homepage=homepage, public=str(public))

    def delete(self, repo):
        """Delete a repository."""
        self._post('repos/delete/' + repo)

    def fork(self, user, repo):
        """Fork a user's repo."""
        self._post('repos/fork/' + user + '/' + repo)

    def watchers(self, user, repo):
        """Find all of the watchers of one of your repositories."""
        return self._parsed('repos/show/%s/%s/watchers' % (user, repo))

    def collaborators(self, user, repo):
        """Find all of the collaborators of one of your repositories."""
        return self._parsed('repos/show/%s/%s/collaborators' % (user, repo))

    def addCollaborator(self, repo, username):
        """Add a collaborator to one of your repositories."""
        self._post('repos/collaborators/' + repo + '/add/' + username)

    def removeCollaborator(self, repo, username):
        """Remove a collaborator from one of your repositories."""
        self._post('repos/collaborators/' + repo + '/remove/' + username)

    def collaborators_all(self):
        """Find all of the collaborators of every of your repositories.

        Returns a dictionary with reponame as key and a list of collaborators as value."""
        ret = {}
        for reponame in (rp.name for rp in self.forUser(self.user)):
            ret[reponame] = self.collaborators(self.user, reponame)
        return ret

    def addCollaborator_all(self, username):
        """Add a collaborator to all of your repositories."""
        for reponame in (rp.name for rp in self.forUser(self.user)):
            self.addCollaborator(reponame, username)

    def removeCollaborator_all(self, username):
        """Remove a collaborator from all of your repositories."""
        for reponame in (rp.name for rp in self.forUser(self.user)):
            self.removeCollaborator(reponame, username)

    def deployKeys(self, repo):
        """List the deploy keys for the given repository.

        The repository must be owned by the current user."""
        return self._parsed('repos/keys/' + repo)

    def addDeployKey(self, repo, title, key):
        """Add a deploy key to a repository."""
        self._post('repos/key/' + repo + '/add', title=title, key=key)

    def removeDeployKey(self, repo, keyId):
        """Remove a deploy key."""
        self._post('repos/key/' + repo + '/remove', id=keyId)

    def discoverHooks(self):
        """Get the known hook types supported by github.

        returns a dict of name -> info.  (see info['schema'] for config params)
        """
        hooks = self._jfetch('hooks', httpAuth=False)
        return dict((h['name'], h) for h in hooks)

    def listHooks(self, user, repo):
        """List hooks configured for a repo."""
        # /repos/:user/:repo/hooks
        return self._jfetch('/'.join(['repos', user, repo, 'hooks']))

    def getHook(self, user, repo, hookid):
        """Get a specific hook by ID."""
        return self._jfetch('/'.join(['repos', user, repo, 'hooks',
                                      str(hookid)]))

    def createHook(self, user, repo, name, config,
                   events=["push"], active=True):
        """Create a hook on the given repo.

        For more info, see the docs:
             http://developer.github.com/v3/repos/hooks/
        """

        doc = json.dumps({'name': name,
                          'active': active,
                          'config': config,
                          'events': events})

        return self._jpost('/'.join(['repos', user, repo, 'hooks']), doc)

    def testHook(self, user, repo, hookid):
        """Test a specific hook by ID."""
        return self._raw_fetch('/'.join(['repos', user, repo, 'hooks',
                                     str(hookid), 'test']),
                               base='https://api.github.com/',
                               data='', httpAuth=True).read()

    def deleteHook(self, user, repo, hookid):
        """Remove a specified hook."""
        return self._raw_fetch('/'.join(['repos', user, repo, 'hooks',
                                         str(hookid)]),
                               base='https://api.github.com/',
                               data='', httpAuth=True, method='DELETE').read()


class CommitEndpoint(BaseEndpoint):

    def forBranch(self, user, repo, branch='master', page=1):
        """Get the commits for the given branch."""
        return self._parsed('/'.join(['commits', 'list', user, repo, branch])+ "?page=" + str(page))

    def forFile(self, user, repo, path, branch='master'):
        """Get the commits for the given file within the given branch."""
        return self._parsed('/'.join(['commits', 'list', user, repo, branch, path]))

    @with_temporary_mappings({'removed': _parseArray,
                              'added': _parseArray,
                              'modified': Modification,
                              'diff': _string_parser,
                              'filename': _string_parser})
    def show(self, user, repo, sha):
        """Get an individual commit."""
        c = self._parsed('/'.join(['commits', 'show', user, repo, sha]))
        # Some fixup due to weird XML structure
        if hasattr(c, 'removed'):
            c.removed = [i[0] for i in c.removed]
        if hasattr(c, 'added'):
            c.added = [i[0] for i in c.added]
        return c

class IssuesEndpoint(BaseEndpoint):

    @with_temporary_mappings({'user': None})
    def search(self, user, repo, state, search_term):
        """Search the issues for the given repo for the given state and search term."""
        return self._parsed('/'.join(['issues', 'search', user, repo, state,
                                      hclient.quote_plus(search_term)]))

    @with_temporary_mappings({'user': None})
    def list(self, user, repo, state='open'):
        """Get the list of issues for the given repo in the given state."""
        return self._parsed('/'.join(['issues', 'list', user, repo, state]))

    @with_temporary_mappings({'user': None})
    def comments(self, user, repo, issue_id):
        return self._parsed('/'.join(['issues', 'comments', user, repo, str(issue_id)]))

    def add_comment(self, user, repo, issue_id, comment):
        """Add a comment to an issue."""
        return self._post('/'.join(['issues', 'comment', user,
                                    repo, str(issue_id)]),
                          comment=comment)

    @with_temporary_mappings({'user': None})
    def show(self, user, repo, issue_id):
        """Show an individual issue."""
        return self._parsed('/'.join(['issues', 'show', user, repo, str(issue_id)]))

    def add_label(self, user, repo, issue_id, label):
        """Add a label to an issue."""
        self._post('issues/label/add/' + user + '/'
                       + repo + '/' + label + '/' + str(issue_id))

    def remove_label(self, user, repo, issue_id, label):
        """Remove a label from an issue."""
        self._post('issues/label/remove/' + user + '/'
                   + repo + '/' + label + '/' + str(issue_id))

    def close(self, user, repo, issue_id):
        """Close an issue."""
        self._post('/'.join(['issues', 'close', user, repo, str(issue_id)]))

    def reopen(self, user, repo, issue_id):
        """Reopen an issue."""
        self._post('/'.join(['issues', 'reopen', user, repo, str(issue_id)]))

    def new(self, user, repo, title, body=''):
        """Create a new issue."""
        return self._posted('/'.join(['issues', 'open', user, repo]),
                            title=title, body=body)

    def edit(self, user, repo, issue_id, title, body):
        """Create a new issue."""
        self._post('/'.join(['issues', 'edit', user, repo, str(issue_id)]),
                   title=title, body=body)

class ObjectsEndpoint(BaseEndpoint):

    @with_temporary_mappings({'tree': Tree, 'type': _string_parser})
    def tree(self, user, repo, t):
        """Get the given tree from the given repo."""
        tl = self._parsed('/'.join(['tree', 'show', user, repo, t]))
        return dict([(t.name, t) for t in tl])

    @with_temporary_mappings({'blob': Blob})
    def blob(self, user, repo, t, fn):
        return self._parsed('/'.join(['blob', 'show', user, repo, t, fn]))

    def raw_blob(self, user, repo, sha):
        """Get a raw blob from a repo."""
        path = 'blob/show/%s/%s/%s' % (user, repo, sha)
        return self._raw_fetch(path).read()

class OrganizationsEndpoint(BaseEndpoint):

    def show(self, org):
        """Get the info of an organization."""
        return self._parsed('organizations/' + org)

    def forUser(self, username):
        """Get the organizations for the given user."""
        return self._parsed('user/show/' + username + "/organizations")

    def forMe(self):
        """Get the organizations for an authenticated user."""
        return self._parsed('organizations')

    def set(self, org, **args):
        """Set organization parameters.

        Organization parameters include the following:
         - name
         - email
         - blog
         - company
         - location
         - billing_email"""
        prepared_args = {}
        for k,v in args.items():
            prepared_args['organization[' + k + ']'] = v
        return self._put('/'.join(['organizations', org]),
            **prepared_args)

    def repositories(self):
        """List repositories across all the organizations that an authenticated user can access."""
        return self._parsed("organizations/repositories")

    def owners(self, org):
        """List the owners of an organization."""
        return self._parsed("organizations/" + org + "/owners")

    def publicRepositories(self, org):
        """List the public repositories for an organization."""
        return self._parsed("organizations/" + org + "/public_repositories")

    def publicMembers(self, org):
        """List the public members of an organization."""
        return self._parsed("organizations/" + org + "/public_members")


class TeamsEndpoint(BaseEndpoint):

    def addUserToTeam(self, team_id, username):
        self._post('teams/%s/members' % str(team_id), name=username)

    def addRepoToTeam(self, team_id, user, repo):
        self._post('teams/%s/repositories' % team_id, name="%s/%s" % (user, repo))

class GitHub(object):
    """Interface to github."""

    def __init__(self, user=None, token=None, fetcher=hclient.fetch, base_url=None):
        self.user    = user
        self.token   = token
        self.fetcher = fetcher

        if base_url:
            BaseEndpoint.BASE_URL = base_url

    @property
    def users(self):
        """Get access to the user API."""
        return UserEndpoint(self.user, self.token, self.fetcher)

    @property
    def repos(self):
        """Get access to the user API."""
        return RepositoryEndpoint(self.user, self.token, self.fetcher)

    @property
    def commits(self):
        return CommitEndpoint(self.user, self.token, self.fetcher)

    @property
    def issues(self):
        return IssuesEndpoint(self.user, self.token, self.fetcher)

    @property
    def objects(self):
        return ObjectsEndpoint(self.user, self.token, self.fetcher)

    @property
    def organizations(self):
        return OrganizationsEndpoint(self.user, self.token, self.fetcher)

    @property
    def teams(self):
        return TeamsEndpoint(self.user, self.token, self.fetcher)

########NEW FILE########
__FILENAME__ = githubsync
#!/usr/bin/env python
#
# Copyright (c) 2005-2008  Dustin Sallings <dustin@spy.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# <http://www.opensource.org/licenses/mit-license.php>
"""
Grab all of a user's projects from github.
"""

import os
import sys
import subprocess

import github

def check_for_old_format(path, url):
    p = subprocess.Popen(['git', '--git-dir=' + path, 'config',
        'remote.origin.fetch'], stdout = subprocess.PIPE)
    stdout, stderr = p.communicate()
    if stdout.strip() != '+refs/*:refs/*':
        print "Not properly configured for mirroring, repairing."
        subprocess.call(['git', '--git-dir=' + path, 'remote', 'rm', 'origin'])
        add_mirror(path, url)

def add_mirror(path, url):
    subprocess.call(['git', '--git-dir=' + path, 'remote', 'add', '--mirror',
            'origin', url])

def sync(path, url, repo_name):
    p = os.path.join(path, repo_name) + ".git"
    print "Syncing %s -> %s" % (repo_name, p)
    if not os.path.exists(p):
        subprocess.call(['git', 'clone', '--bare', url, p])
        add_mirror(p, url)
    check_for_old_format(p, url)
    subprocess.call(['git', '--git-dir=' + p, 'fetch', '-f'])

def sync_user_repo(path, repo):
    sync(path, "git://github.com/%s/%s" % (repo.owner, repo.name), repo.name)

def usage():
    sys.stderr.write("Usage:  %s username destination_url\n" % sys.argv[0])
    sys.stderr.write(
        """Ensures you've got the latest stuff for the given user.

Also, if the file $HOME/.github-private exists, it will be read for
additional projects.

Each line must be a simple project name (e.g. py-github), a tab character,
and a git URL.
""")

if __name__ == '__main__':
    try:
        user, path = sys.argv[1:]
    except ValueError:
        usage()
        exit(1)

    privfile = os.path.join(os.getenv("HOME"), ".github-private")
    if os.path.exists(privfile):
        f = open(privfile)
        for line in f:
            name, url = line.strip().split("\t")
            sync(path, url, name)

    gh = github.GitHub()

    for repo in gh.repos.forUser(user):
        sync_user_repo(path, repo)

########NEW FILE########
__FILENAME__ = githubtest
#!/usr/bin/env python
#
# Copyright (c) 2005-2008  Dustin Sallings <dustin@spy.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# <http://www.opensource.org/licenses/mit-license.php>
"""
Defines and runs unittests.
"""

import urllib
import hashlib
import unittest

import StringIO

import github

class BaseCase(unittest.TestCase):

    def _gh(self, expUrl, filename):

        def opener(url):
            self.assertEquals(expUrl, url)
            return open(filename)
        return github.GitHub(fetcher=opener)

    def _agh(self, expUrl, u, t, filename):

        def opener(url):
            self.assertEquals(expUrl, url + '?login=' + u + '&token=' + t)
            return open(filename)
        return github.GitHub(fetcher=opener)

    def _ghp(self, expUrl, u, t, **kv):

        def opener(url, data):
            h = {'login': u, 'token': t}
            h.update(kv)
            self.assertEquals(github.BaseEndpoint.BASE_URL + expUrl, url)
            self.assertEquals(sorted(data.split('&')),
                              sorted(urllib.urlencode(h).split('&')))

            return StringIO.StringIO("")

        return github.GitHub(u, t, fetcher=opener)

class UserTest(BaseCase):

    def __loadUserSearch(self):
        return self._gh('https://github.com/api/v2/xml/user/search/dustin',
            'data/user.search.xml').users.search('dustin')

    def __loadUser(self, which, u=None, p=None):
        if u:
            return self._agh('https://github.com/api/v2/xml/user/show/dustin'
                              + '?login=' + u + '&token=' + p,
                              u, p, 'data/' + which).users.show('dustin')

        else:
            return self._gh('https://github.com/api/v2/xml/user/show/dustin',
                             'data/' + which).users.show('dustin')

    def testUserSearch(self):
        """Test the base properties of the user object."""
        u = self.__loadUserSearch()[0]
        self.assertEquals("Dustin Sallings", u.fullname)
        self.assertEquals("dustin", u.name)
        self.assertEquals("dustin@spy.net", u.email)
        self.assertEquals("Santa Clara, CA", u.location)
        self.assertEquals("Ruby", u.language)
        self.assertEquals(35, u.actions)
        self.assertEquals(77, u.repos)
        self.assertEquals(78, u.followers)
        self.assertEquals('user-1779', u.id)
        self.assertAlmostEquals(12.231684, u.score)
        self.assertEquals('user', u.type)
        self.assertEquals('2008-02-29T17:59:09Z', u.created)
        self.assertEquals('2009-03-19T09:15:24.663Z', u.pushed)
        self.assertEquals("<<User dustin>>", repr(u))

    def testUserPublic(self):
        """Test the user show API with no authentication."""
        u = self.__loadUser('user.public.xml')
        self.assertEquals("Dustin Sallings", u.name)
        # self.assertEquals(None, u.company)
        self.assertEquals(10, u.following_count)
        self.assertEquals(21, u.public_gist_count)
        self.assertEquals(81, u.public_repo_count)
        self.assertEquals('http://bleu.west.spy.net/~dustin/', u.blog)
        self.assertEquals(1779, u.id)
        self.assertEquals(82, u.followers_count)
        self.assertEquals('dustin', u.login)
        self.assertEquals('Santa Clara, CA', u.location)
        self.assertEquals('dustin@spy.net', u.email)
        self.assertEquals('2008-02-29T09:59:09-08:00', u.created_at)

    def testUserPrivate(self):
        """Test the user show API with extra info from auth."""
        u = self.__loadUser('user.private.xml', 'dustin', 'blahblah')
        self.assertEquals("Dustin Sallings", u.name)
        # self.assertEquals(None, u.company)
        self.assertEquals(10, u.following_count)
        self.assertEquals(21, u.public_gist_count)
        self.assertEquals(81, u.public_repo_count)
        self.assertEquals('http://bleu.west.spy.net/~dustin/', u.blog)
        self.assertEquals(1779, u.id)
        self.assertEquals(82, u.followers_count)
        self.assertEquals('dustin', u.login)
        self.assertEquals('Santa Clara, CA', u.location)
        self.assertEquals('dustin@spy.net', u.email)
        self.assertEquals('2008-02-29T09:59:09-08:00', u.created_at)

        # Begin private data

        self.assertEquals("micro", u.plan.name)
        self.assertEquals(1, u.plan.collaborators)
        self.assertEquals(614400, u.plan.space)
        self.assertEquals(5, u.plan.private_repos)
        self.assertEquals(155191, u.disk_usage)
        self.assertEquals(6, u.collaborators)
        self.assertEquals(4, u.owned_private_repo_count)
        self.assertEquals(5, u.total_private_repo_count)
        self.assertEquals(0, u.private_gist_count)

    def testKeysList(self):
        """Test key listing."""
        kl = self._agh('https://github.com/api/v2/xml/user/keys?login=dustin&token=blahblah',
                       'dustin', 'blahblah', 'data/keys.xml').users.keys()
        self.assertEquals(7, len(kl))
        k = kl[0]

        self.assertEquals('some key', k.title)
        self.assertEquals(2181, k.id)
        self.assertEquals(549, k.key.find('cdEXwCSjAIFp8iRqh3GOkxGyFSc25qv/MuOBg=='))

    def testRemoveKey(self):
        """Remove a key."""
        self._ghp('user/key/remove',
                  'dustin', 'p', id=828).users.removeKey(828)

    def testAddKey(self):
        """Add a key."""
        self._ghp('user/key/add',
                  'dustin', 'p', name='my key', key='some key').users.addKey(
            'my key', 'some key')

class RepoTest(BaseCase):

    def __loadUserRepos(self):
        return self._gh('https://github.com/api/v2/xml/repos/show/verbal?page=1',
            'data/repos.xml').repos.forUser('verbal')

    def testUserRepoList(self):
        """Get a list of repos for a user."""
        rs = self.__loadUserRepos()
        self.assertEquals(10, len(rs))
        r = rs[0]
        self.assertEquals('A beanstalk client for the twisted network framework.',
                          r.description)
        self.assertEquals(2, r.watchers)
        self.assertEquals(0, r.forks)
        self.assertEquals('beanstalk-client-twisted', r.name)
        self.assertEquals(False, r.private)
        self.assertEquals('http://github.com/verbal/beanstalk-client-twisted',
                          r.url)
        self.assertEquals(True, r.fork)
        self.assertEquals('verbal', r.owner)
        # XXX:  Can't parse empty elements.  :(
        # self.assertEquals('', r.homepage)

    def testRepoSearch(self):
        """Test searching a repository."""
        rl = self._gh('https://github.com/api/v2/xml/repos/search/ruby+testing',
                      'data/repos.search.xml').repos.search('ruby testing')
        self.assertEquals(12, len(rl))

        r = rl[0]
        self.assertEquals('synthesis', r.name)
        self.assertAlmostEquals(0.3234576, r.score, 4)
        self.assertEquals(4656, r.actions)
        self.assertEquals(2048, r.size)
        self.assertEquals('Ruby', r.language)
        self.assertEquals(26, r.followers)
        self.assertEquals('gmalamid', r.username)
        self.assertEquals('repo', r.type)
        self.assertEquals('repo-3555', r.id)
        self.assertEquals(1, r.forks)
        self.assertFalse(r.fork)
        self.assertEquals('Ruby test code analysis tool employing a '
                          '"Synthesized Testing" strategy, aimed to reduce '
                          'the volume of slower, coupled, complex wired tests.',
                          r.description)
        self.assertEquals('2009-01-08T13:45:06Z', r.pushed)
        self.assertEquals('2008-03-11T23:38:04Z', r.created)

    def testBranchList(self):
        """Test branch listing for a repo."""
        bl = self._gh('https://github.com/api/v2/xml/repos/show/schacon/ruby-git/branches',
                      'data/repos.branches.xml').repos.branches('schacon', 'ruby-git')
        self.assertEquals(4, len(bl))
        self.assertEquals('ee90922f3da3f67ef19853a0759c1d09860fe3b3', bl['master'])

    def testLanguageList(self):
        """Test language listing for a repo."""
        bl = self._gh('https://github.com/api/v2/xml/repos/show/schacon/ruby-git/languages',
                      'data/repos.languages.xml').repos.languages('schacon', 'ruby-git')
        self.assertEquals(1, len(bl))
        self.assertEquals('136905', bl['Ruby'])

    def testGetOneRepo(self):
        """Fetch an individual repository."""
        r = self._gh('https://github.com/api/v2/xml/repos/show/schacon/grit',
                     'data/repo.xml').repos.show('schacon', 'grit')

        self.assertEquals('Grit is a Ruby library for extracting information from a '
                          'git repository in an object oriented manner - this fork '
                          'tries to intergrate as much pure-ruby functionality as possible',
                          r.description)
        self.assertEquals(68, r.watchers)
        self.assertEquals(4, r.forks)
        self.assertEquals('grit', r.name)
        self.assertFalse(r.private)
        self.assertEquals('http://github.com/schacon/grit', r.url)
        self.assertTrue(r.fork)
        self.assertEquals('schacon', r.owner)
        self.assertEquals('http://grit.rubyforge.org/', r.homepage)

    def testGetRepoNetwork(self):
        """Test network fetching."""
        nl = self._gh('https://github.com/api/v2/xml/repos/show/dustin/py-github/network',
                      'data/network.xml').repos.network('dustin', 'py-github')
        self.assertEquals(5, len(nl))

        n = nl[0]
        self.assertEquals('Python interface for talking to the github API',
                          n.description)
        self.assertEquals('py-github', n.name)
        self.assertFalse(n.private)
        self.assertEquals('http://github.com/dustin/py-github', n.url)
        self.assertEquals(30, n.watchers)
        self.assertEquals(4, n.forks)
        self.assertFalse(n.fork)
        self.assertEquals('dustin', n.owner)
        self.assertEquals('http://dustin.github.com/2008/12/29/github-sync.html',
                          n.homepage)

    def testSetPublic(self):
        """Test setting a repo visible."""
        self._ghp('repos/set/public/py-github', 'dustin', 'p').repos.setVisible(
            'py-github')

    def testSetPrivate(self):
        """Test setting a repo to private."""
        self._ghp('repos/set/private/py-github', 'dustin', 'p').repos.setVisible(
            'py-github', False)

    def testCreateRepository(self):
        """Test creating a repository."""
        self._ghp('repos/create', 'dustin', 'p',
                  name='testrepo',
                  description='woo',
                  homepage='',
                  public='1').repos.create(
            'testrepo', description='woo')

    def testDeleteRepo(self):
        """Test setting a repo to private."""
        self._ghp('repos/delete/mytest', 'dustin', 'p').repos.delete('mytest')

    def testFork(self):
        """Test forking'"""
        self._ghp('repos/fork/someuser/somerepo', 'dustin', 'p').repos.fork(
            'someuser', 'somerepo')

    def testAddCollaborator(self):
        """Adding a collaborator."""
        self._ghp('repos/collaborators/memcached/add/trondn',
                  'dustin', 'p').repos.addCollaborator('memcached', 'trondn')

    def testRemoveCollaborator(self):
        """Removing a collaborator."""
        self._ghp('repos/collaborators/memcached/remove/trondn',
                  'dustin', 'p').repos.removeCollaborator('memcached', 'trondn')

    def testAddDeployKey(self):
        """Add a deploy key."""
        self._ghp('repos/key/blah/add', 'dustin', 'p',
                  title='title', key='key').repos.addDeployKey('blah', 'title', 'key')

    def testRemoveDeployKey(self):
        """Remove a deploy key."""
        self._ghp('repos/key/blah/remove', 'dustin', 'p',
                  id=5).repos.removeDeployKey('blah', 5)

class CommitTest(BaseCase):

    def testCommitList(self):
        """Test commit list."""
        cl = self._gh('https://github.com/api/v2/xml/commits/list/mojombo/grit/master?page=1',
                      'data/commits.xml').commits.forBranch('mojombo', 'grit')
        self.assertEquals(30, len(cl))

        c = cl[0]
        self.assertEquals("Regenerated gemspec for version 1.1.1", c.message)
        self.assertEquals('4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde', c.id)
        self.assertEquals('94490563ebaf733cbb3de4ad659eb58178c2e574', c.tree)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.committed_date)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.authored_date)
        self.assertEquals('http://github.com/mojombo/grit/commit/4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde',
                          c.url)
        self.assertEquals(1, len(c.parents))
        self.assertEquals('5071bf9fbfb81778c456d62e111440fdc776f76c', c.parents[0].id)
        self.assertEquals('Tom Preston-Werner', c.author.name)
        self.assertEquals('tom@mojombo.com', c.author.email)
        self.assertEquals('Tom Preston-Werner', c.committer.name)
        self.assertEquals('tom@mojombo.com', c.committer.email)

    def testCommitListForFile(self):
        """Test commit list for a file."""
        cl = self._gh('https://github.com/api/v2/xml/commits/list/mojombo/grit/master/grit.gemspec',
                      'data/commits.xml').commits.forFile('mojombo', 'grit', 'grit.gemspec')
        self.assertEquals(30, len(cl))

        c = cl[0]
        self.assertEquals("Regenerated gemspec for version 1.1.1", c.message)
        self.assertEquals('4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde', c.id)
        self.assertEquals('94490563ebaf733cbb3de4ad659eb58178c2e574', c.tree)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.committed_date)
        self.assertEquals('2009-03-31T09:54:51-07:00', c.authored_date)
        self.assertEquals('http://github.com/mojombo/grit/commit/4ac4acab7fd9c7fd4c0e0f4ff5794b0347baecde',
                          c.url)
        self.assertEquals(1, len(c.parents))
        self.assertEquals('5071bf9fbfb81778c456d62e111440fdc776f76c', c.parents[0].id)
        self.assertEquals('Tom Preston-Werner', c.author.name)
        self.assertEquals('tom@mojombo.com', c.author.email)
        self.assertEquals('Tom Preston-Werner', c.committer.name)
        self.assertEquals('tom@mojombo.com', c.committer.email)

    def testIndividualCommit(self):
        """Grab a single commit."""
        h = '4c86fa592fcc7cb685c6e9d8b6aebe8dcbac6b3e'
        c = self._gh('https://github.com/api/v2/xml/commits/show/dustin/memcached/' + h,
                     'data/commit.xml').commits.show('dustin', 'memcached', h)
        self.assertEquals(['internal_tests.c'], c.removed)
        self.assertEquals(set(['cache.c', 'cache.h', 'testapp.c']), set(c.added))
        self.assertEquals('Create a generic cache for objects of same size\n\n'
                          'The suffix pool could be thread-local and use the generic cache',
                          c.message)

        self.assertEquals(6, len(c.modified))
        self.assertEquals('.gitignore', c.modified[0].filename)
        self.assertEquals(140, len(c.modified[0].diff))

        self.assertEquals(['ee0c3d5ae74d0862b4d9990e2ad13bc79f8c34df'],
                          [p.id for p in c.parents])
        self.assertEquals('http://github.com/dustin/memcached/commit/' + h, c.url)
        self.assertEquals('Trond Norbye', c.author.name)
        self.assertEquals('Trond.Norbye@sun.com', c.author.email)
        self.assertEquals(h, c.id)
        self.assertEquals('2009-04-17T16:15:52-07:00', c.committed_date)
        self.assertEquals('2009-03-27T10:30:16-07:00', c.authored_date)
        self.assertEquals('94b644163f6381a9930e2d7c583fae023895b903', c.tree)
        self.assertEquals('Dustin Sallings', c.committer.name)
        self.assertEquals('dustin@spy.net', c.committer.email)

    def testWatchRepo(self):
        """Test watching a repo."""
        self._ghp('repos/watch/dustin/py-github', 'dustin', 'p').repos.watch(
            'dustin', 'py-github')

    def testWatchRepo(self):
        """Test watching a repo."""
        self._ghp('repos/unwatch/dustin/py-github', 'dustin', 'p').repos.unwatch(
            'dustin', 'py-github')

class IssueTest(BaseCase):

    def testListIssues(self):
        """Test listing issues."""
        il = self._gh('https://github.com/api/v2/xml/issues/list/schacon/simplegit/open',
                      'data/issues.list.xml').issues.list('schacon', 'simplegit')
        self.assertEquals(1, len(il))
        i = il[0]

        self.assertEquals('schacon', i.user)
        self.assertEquals('2009-04-17T16:19:02-07:00', i.updated_at)
        self.assertEquals('something', i.body)
        self.assertEquals('new', i.title)
        self.assertEquals(2, i.number)
        self.assertEquals(0, i.votes)
        self.assertEquals(1.0, i.position)
        self.assertEquals('2009-04-17T16:18:50-07:00', i.created_at)
        self.assertEquals('open', i.state)

    def testShowIssue(self):
        """Show an individual issue."""
        i = self._gh('https://github.com/api/v2/xml/issues/show/dustin/py-github/1',
                     'data/issues.show.xml').issues.show('dustin', 'py-github', 1)

        self.assertEquals('dustin', i.user)
        self.assertEquals('2009-04-17T18:37:04-07:00', i.updated_at)
        self.assertEquals('http://develop.github.com/p/general.html', i.body)
        self.assertEquals('Add auth tokens', i.title)
        self.assertEquals(1, i.number)
        self.assertEquals(0, i.votes)
        self.assertEquals(1.0, i.position)
        self.assertEquals('2009-04-17T17:00:58-07:00', i.created_at)
        self.assertEquals('closed', i.state)

    def testAddLabel(self):
        """Adding a label to an issue."""
        self._ghp('issues/label/add/dustin/py-github/todo/33', 'd', 'pw').issues.add_label(
            'dustin', 'py-github', 33, 'todo')

    def testRemoveLabel(self):
        """Removing a label from an issue."""
        self._ghp('issues/label/remove/dustin/py-github/todo/33',
                  'd', 'pw').issues.remove_label(
            'dustin', 'py-github', 33, 'todo')

    def testCloseIssue(self):
        """Closing an issue."""
        self._ghp('issues/close/dustin/py-github/1', 'd', 'pw').issues.close(
            'dustin', 'py-github', 1)

    def testReopenIssue(self):
        """Reopening an issue."""
        self._ghp('issues/reopen/dustin/py-github/1', 'd', 'pw').issues.reopen(
            'dustin', 'py-github', 1)

    def testCreateIssue(self):
        """Creating an issue."""
        self._ghp('issues/open/dustin/py-github', 'd', 'pw',
                  title='test title', body='').issues.new(
            'dustin', 'py-github', title='test title')

    def testEditIssue(self):
        """Editing an existing issue."""
        self._ghp('issues/edit/dustin/py-github/1', 'd', 'pw',
                  title='new title', body='new body').issues.edit(
            'dustin', 'py-github', 1, 'new title', 'new body')

class ObjectTest(BaseCase):

    def testTree(self):
        """Test tree fetching."""
        h = '1ddd3f99f0b96019042239375b3ad4d45796ffba'
        tl = self._gh('https://github.com/api/v2/xml/tree/show/dustin/py-github/' + h,
                      'data/tree.xml').objects.tree('dustin', 'py-github', h)
        self.assertEquals(8, len(tl))
        self.assertEquals('setup.py', tl['setup.py'].name)
        self.assertEquals('6e290379ec58fa00ac9d1c2a78f0819a21397445',
                          tl['setup.py'].sha)
        self.assertEquals('100755', tl['setup.py'].mode)
        self.assertEquals('blob', tl['setup.py'].type)

        self.assertEquals('src', tl['src'].name)
        self.assertEquals('5fb9175803334c82b3fd66f1b69502691b91cf4f',
                          tl['src'].sha)
        self.assertEquals('040000', tl['src'].mode)
        self.assertEquals('tree', tl['src'].type)

    def testBlob(self):
        """Test blob fetching."""
        h = '1ddd3f99f0b96019042239375b3ad4d45796ffba'
        blob = self._gh('https://github.com/api/v2/xml/blob/show/dustin/py-github/'
                        + h + '/setup.py',
                        'data/blob.xml').objects.blob('dustin', 'py-github', h, 'setup.py')
        self.assertEquals('setup.py', blob.name)
        self.assertEquals(1842, blob.size)
        self.assertEquals('6e290379ec58fa00ac9d1c2a78f0819a21397445', blob.sha)
        self.assertEquals('100755', blob.mode)
        self.assertEquals('text/plain', blob.mime_type)
        self.assertEquals(1842, len(blob.data))
        self.assertEquals(1641, blob.data.index('Production/Stable'))

    def testRawBlob(self):
        """Test raw blob fetching."""
        h = '6e290379ec58fa00ac9d1c2a78f0819a21397445'
        blob = self._gh('https://github.com/api/v2/xml/blob/show/dustin/py-github/' + h,
                        'data/setup.py').objects.raw_blob('dustin', 'py-github', h)
        self.assertEquals('e2dc8aea9ae8961f4f5923f9febfdd0a',
                          hashlib.md5(blob).hexdigest())



class OrganizationTest(BaseCase):

    def testOrganization(self):
        """Get the details of an organization."""
        o = self._gh('https://github.com/api/v2/xml/organizations/ff0000',
            'data/org.xml').organizations.show('ff0000')
        self.assertEquals('ff0000', o.login)
        self.assertEquals("RED Interactive Agency", o.name)
        self.assertEquals('514663408e310690ce46f6e8efdf5e2d', o.gravatar_id)
        self.assertEquals('Santa Monica, CA', o.location)
        self.assertEquals('http://ff0000.github.com/', o.blog)
        self.assertEquals('Organization', o.type)
        self.assertEquals(0, o.public_gist_count)
        self.assertEquals(0, o.following_count)
        self.assertEquals(21, o.public_repo_count)
        self.assertEquals(283774, o.id)
        self.assertEquals(1, o.followers_count)
        self.assertEquals('2010-05-21T15:42:37-07:00', o.created_at)

    def testUserPublicOrganizationList(self):
        """Get a list of organizations a user is publicly member of."""
        os = self._gh('https://github.com/api/v2/xml/user/show/claudiob/organizations',
            'data/orgs.for_user.public.xml').organizations.forUser('claudiob')
        self.assertEquals(2, len(os))
        o = os[0]
        self.assertEquals('ff0000', o.login)
        self.assertEquals('RED Interactive Agency', o.name)
        self.assertEquals('514663408e310690ce46f6e8efdf5e2d', o.gravatar_id)
        self.assertEquals('Santa Monica, CA', o.location)
        self.assertEquals('http://ff0000.github.com/', o.blog)
        self.assertEquals('Organization', o.type)

    def testUserFullOrganizationList(self):
        """Get a list of organizations a user is member of."""
        u, t = 'claudiob', 'blah blah' # use real token to run the test
        os = self._agh('https://github.com/api/v2/xml/organizations'
            + '?login=' + u + '&token=' + t,
            u, t, 'data/orgs.for_user.xml').organizations.forMe()
        self.assertEquals(3, len(os))
        o = os[0]
        self.assertEquals('lexdir', o.login)

    def testOrganizationPublicRepositories(self):
        """Get a list of public repositories of an organization."""
        rs = self._gh('https://github.com/api/v2/xml/organizations/ff0000/public_repositories',
            'data/org.repos.public.xml').organizations.publicRepositories('ff0000')
        self.assertEquals(7, len(rs))
        r = rs[0]
        self.assertEquals(r.url, 'https://github.com/ff0000/random_instances')
        self.assertEquals(r.pushed_at, '2011-01-21T14:52:20-08:00')
        self.assertEquals(r.has_issues, True)
        self.assertEquals(r.description, 'Retrieve or generate random instances of Django models.')
        self.assertEquals(r.created_at, '2011-01-20T15:05:23-08:00')
        self.assertEquals(r.watchers, 2)
        self.assertEquals(r.forks, 1)
        self.assertEquals(r.fork, False)
        self.assertEquals(r.has_downloads, True)
        self.assertEquals(r.size, 176)
        self.assertEquals(r.private, False)
        self.assertEquals(r.language, 'Python')
        self.assertEquals(r.name, 'random_instances')
        self.assertEquals(r.owner, 'ff0000')
        self.assertEquals(r.has_wiki, True)
        self.assertEquals(r.open_issues, 0)

    def testOrganizationPublicMembers(self):
        """Get a list of public members of an organization."""
        ms = self._gh('https://github.com/api/v2/xml/organizations/ff0000/public_members',
            'data/org.members.public.xml').organizations.publicMembers('ff0000')
        self.assertEquals(4, len(ms))
        m = ms[2]
        self.assertEquals(m.login, 'claudiob')
        self.assertEquals(m.name, 'Claudio B.')
        self.assertEquals(m.blog, 'http://claudiob.github.com')

    def testOrganizationOwners(self):
        """Get a list of owners of an organization."""
        u, t = 'claudiob', 'blah blah' # use real token to run the test
        ms = self._agh('https://github.com/api/v2/xml/organizations/ff0000/owners'
            + '?login=' + u + '&token=' + t,
            u, t, 'data/org.owners.xml').organizations.owners('ff0000')
        self.assertEquals(1, len(ms))
        m = ms[0]
        self.assertEquals(m.login, 'claudiob')
        self.assertEquals(m.name, 'Claudio B.')
        self.assertEquals(m.blog, 'http://claudiob.github.com')

    def testOrganizationRepositories(self):
        """Get a list of repositories across all the organizations that a user can access."""
        u, t = 'claudiob', 'blah blah' # use real token to run the test
        os = self._agh('https://github.com/api/v2/xml/organizations/repositories'
            + '?login=' + u + '&token=' + t,
            u, t, 'data/orgs.repos.xml').organizations.repositories()
        self.assertEquals(1, len(os))
        o = os[0]
        self.assertEquals('vlex', o.owner)
        self.assertEquals('integrity', o.name)




if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = hclient
#!/usr/bin/env python
#
# Copyright (c) 2005-2008  Dustin Sallings <dustin@spy.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# <http://www.opensource.org/licenses/mit-license.php>
"""
Yet another HTTP client abstraction.
"""

import sys
PY3 = sys.version_info[0] == 3

if PY3:
    from urllib.parse import urlencode
    from urllib.parse import quote
    from urllib.parse import quote_plus
    from urllib.request import Request
    from urllib.request import urlopen
    import base64

    def b64encode(s):
        return str(base64.b64encode(bytes(s, 'utf8')), 'utf8')
else:
    import urllib
    from urllib import urlencode
    from urllib import quote
    from urllib import quote_plus
    from urllib2 import Request, urlopen

    from base64 import b64encode

def fetch(url, data=None, username=None, password=None, headers={},
          method=None):
    request = Request(url, data=data, headers=headers)
    if method:
        request.get_method = lambda: method
    if username and password:
        request.add_header('Authorization',
                           'Basic ' + b64encode("%s:%s" % (username,
                                                           password)).strip())
    return urlopen(request)

########NEW FILE########
