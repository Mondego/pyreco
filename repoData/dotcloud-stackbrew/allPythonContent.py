__FILENAME__ = app
import sys
import json

import flask

sys.path.append('./lib')

import brew
import db
import periodic
import utils

app = flask.Flask('stackbrew')
config = None
with open('./config.json') as config_file:
    config = json.load(config_file)
data = db.DbManager(config['db_url'], debug=config['debug'])


@app.route('/')
def home():
    return utils.resp(app, 'stackbrew')


@app.route('/summary')
@app.route('/status')
def latest_summary():
    result = data.latest_status()
    return utils.resp(app, result)


@app.route('/summary/<int:id>')
def get_summary(id):
    result = data.get_summary(id)
    return utils.resp(app, result)


@app.route('/success/<repo_name>')
def latest_success(repo_name):
    tag = flask.request.args.get('tag', None)
    result = data.get_latest_successful(repo_name, tag)
    return utils.resp(app, result)


if config['debug']:
    @app.route('/build/force', methods=['POST'])
    def force_build():
        build_task()


def build_task():
    summary = brew.build_library(
        config['library_repo'], namespace='stackbrew',
        debug=config['debug'], push=config['push'], prefill=False,
        repos_folder=config['repos_folder'], logger=app.logger
    )
    data.insert_summary(summary)


try:
    periodic.init_task(build_task, config['build_interval'],
                       logger=app.logger)
    app.logger.info('Periodic build task initiated.')
except RuntimeError:
    app.logger.warning('Periodic build task already locked.')

app.run(
    host=config.get('host', '127.0.0.1'),
    port=config.get('port', 5000),
    debug=config['debug']
)

########NEW FILE########
__FILENAME__ = brew
import hashlib
import logging
import os
import random
from shutil import rmtree
import string

import docker

import git
from summary import Summary

DEFAULT_REPOSITORY = 'git://github.com/shin-/brew'
DEFAULT_BRANCH = 'master'

client = docker.Client(timeout=10000)
processed = {}
processed_folders = []


def build_library(repository=None, branch=None, namespace=None, push=False,
                  debug=False, prefill=True, registry=None, targetlist=None,
                  repos_folder=None, logger=None):
    ''' Entrypoint method build_library.
        repository:     Repository containing a library/ folder. Can be a
                        local path or git repository
        branch:         If repository is a git repository, checkout this branch
                        (default: DEFAULT_BRANCH)
        namespace:      Created repositories will use the following namespace.
                        (default: no namespace)
        push:           If set to true, push images to the repository
        debug:          Enables debug logging if set to True
        prefill:        Retrieve images from public repository before building.
                        Serves to prefill the builder cache.
        registry:       URL to the private registry where results should be
                        pushed. (only if push=True)
        targetlist:     String indicating which library files are targeted by
                        this build. Entries should be comma-separated. Default
                        is all files.
        repos_folder:   Fixed location where cloned repositories should be
                        stored. Default is None, meaning folders are temporary
                        and cleaned up after the build finishes.
        logger:         Logger instance to use. Default is None, in which case
                        build_library will create its own logger.
    '''
    dst_folder = None
    summary = Summary()
    if logger is None:
        logger = logging.getLogger(__name__)
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                            level='INFO')

    if repository is None:
        repository = DEFAULT_REPOSITORY
    if branch is None:
        branch = DEFAULT_BRANCH
    if debug:
        logger.setLevel('DEBUG')
    if targetlist is not None:
        targetlist = targetlist.split(',')

    if not repository.startswith(('https://', 'git://')):
        logger.info('Repository provided assumed to be a local path')
        dst_folder = repository

    try:
        client.version()
    except Exception as e:
        logger.error('Could not reach the docker daemon. Please make sure it '
                     'is running.')
        logger.warning('Also make sure you have access to the docker UNIX '
                       'socket (use sudo)')
        return

    if not dst_folder:
        logger.info('Cloning docker repo from {0}, branch: {1}'.format(
            repository, branch))
        try:
            rep, dst_folder = git.clone_branch(repository, branch)
        except Exception as e:
            logger.exception(e)
            logger.error('Source repository could not be fetched. Check '
                         'that the address is correct and the branch exists.')
            return
    try:
        dirlist = os.listdir(os.path.join(dst_folder, 'library'))
    except OSError as e:
        logger.error('The path provided ({0}) could not be found or didn\'t'
                     'contain a library/ folder.'.format(dst_folder))
        return
    for buildfile in dirlist:
        if buildfile == 'MAINTAINERS':
            continue
        if (targetlist and buildfile not in targetlist):
            continue
        f = open(os.path.join(dst_folder, 'library', buildfile))
        linecnt = 0
        for line in f:
            linecnt += 1
            if not line or line.strip() == '':
                continue
            elif line.lstrip().startswith('#'):  # # It's a comment!
                continue
            logger.debug('{0} ---> {1}'.format(buildfile, line))
            try:
                tag, url, ref, dfile = parse_line(line, logger)
                if prefill:
                    logger.debug('Pulling {0} from official repository (cache '
                                 'fill)'.format(buildfile))
                    try:
                        client.pull(buildfile)
                    except:
                        # Image is not on official repository, ignore prefill
                        pass

                img, commit = build_repo(url, ref, buildfile, dfile, tag,
                                         namespace, push, registry,
                                         repos_folder, logger)
                summary.add_success(buildfile, (linecnt, line), img, commit)
            except Exception as e:
                logger.exception(e)
                summary.add_exception(buildfile, (linecnt, line), e)

        f.close()
    cleanup(dst_folder, dst_folder != repository, repos_folder is None)
    summary.print_summary(logger)
    return summary


def parse_line(line, logger):
    df_folder = '.'
    args = line.split(':', 1)
    if len(args) != 2:
        logger.debug("Invalid line: {0}".format(line))
        raise RuntimeError('Incorrect line format, please refer to the docs')

    try:
        repo = args[1].strip().split()
        if len(repo) == 2:
            df_folder = repo[1].strip()
        url, ref = repo[0].strip().rsplit('@', 1)
        return (args[0].strip(), url, ref, df_folder)
    except ValueError:
        logger.debug("Invalid line: {0}".format(line))
        raise RuntimeError('Incorrect line format, please refer to the docs')


def cleanup(libfolder, clean_libfolder=False, clean_repos=True):
    ''' Cleanup method called at the end of build_library.
        libfolder:       Folder containing the library definition.
        clean_libfolder: If set to True, libfolder will be removed.
                         Only if libfolder was temporary
        clean_repos: Remove library repos. Also resets module variables
                     "processed" and "processed_folders" if set to true.
    '''
    global processed_folders
    global processed
    if clean_libfolder:
        rmtree(libfolder, True)
    if clean_repos:
        for d in processed_folders:
            rmtree(d, True)
        processed_folders = []
        processed = {}


def _random_suffix():
    return ''.join([
        random.choice(string.ascii_letters + string.digits) for i in xrange(6)
    ])


def get_repo_hash(repo_url, ref, df_location):
    h = hashlib.md5(repo_url)
    h.update(ref)
    h.update(df_location)
    return h.hexdigest()


def build_repo(repository, ref, docker_repo, dockerfile_location,
               docker_tag, namespace, push, registry, repos_folder, logger):
    ''' Builds one line of a library file.
        repository:     URL of the git repository that needs to be built
        ref:            Git reference (or commit ID) that needs to be built
        docker_repo:    Name of the docker repository where the image will
                        end up.
        dockerfile_location: Folder containing the Dockerfile
        docker_tag:     Tag for the image in the docker repository.
        namespace:      Namespace for the docker repository.
        push:           If the image should be pushed at the end of the build
        registry:       URL to private registry where image should be pushed
        repos_folder:   Directory where repositories should be cloned
        logger:         Logger instance
    '''
    dst_folder = None
    img_id = None
    commit_id = None
    repo_hash = get_repo_hash(repository, ref, dockerfile_location)
    if repos_folder:
        # Repositories are stored in a fixed location and can be reused
        dst_folder = os.path.join(repos_folder, docker_repo + _random_suffix())
    docker_repo = '{0}/{1}'.format(namespace or 'library', docker_repo)

    if repo_hash in processed.keys():
        logger.info('[cache hit] {0}'.format(repo_hash))
        logger.info('This ref has already been built, reusing image ID')
        img_id = processed[repo_hash]
        if ref.startswith('refs/'):
            commit_id = processed[repository].ref(ref)
        else:
            commit_id = ref
    else:
        # Not already built
        logger.info('[cache miss] {0}'.format(repo_hash))
        rep = None
        logger.info('Cloning {0} (ref: {1})'.format(repository, ref))
        if repository not in processed:  # Repository not cloned yet
            try:
                rep, dst_folder = git.clone(repository, ref, dst_folder)
            except Exception:
                if dst_folder:
                    rmtree(dst_folder)
                ref = 'refs/tags/' + ref
                rep, dst_folder = git.clone(repository, ref, dst_folder)
            processed[repository] = rep
            processed_folders.append(dst_folder)
        else:
            rep = processed[repository]
            if ref in rep.refs:
                # The ref already exists, we just need to checkout
                dst_folder = git.checkout(rep, ref)
            elif 'refs/tags/' + ref in rep.refs:
                ref = 'refs/tags/' + ref
                dst_folder = git.checkout(rep, ref)
            else:  # ref is not present, try pulling it from the remote origin
                try:
                    rep, dst_folder = git.pull(repository, rep, ref)
                except Exception:
                    ref = 'refs/tags/' + ref
                    rep, dst_folder = git.pull(repository, rep, ref)
        dockerfile_location = os.path.join(dst_folder, dockerfile_location)
        if not 'Dockerfile' in os.listdir(dockerfile_location):
            raise RuntimeError('Dockerfile not found in cloned repository')
        commit_id = rep.head()
        logger.info('Building using dockerfile...')
        img_id, logs = client.build(path=dockerfile_location, quiet=True)
        if img_id is None:
            logger.error('Image ID not found. Printing build logs...')
            logger.debug(logs)
            raise RuntimeError('Build failed')

    logger.info('Committing to {0}:{1}'.format(docker_repo,
                docker_tag or 'latest'))
    client.tag(img_id, docker_repo, docker_tag)
    logger.info("Registering as processed: {0}".format(repo_hash))
    processed[repo_hash] = img_id
    if push:
        logger.info('Pushing result to registry {0}'.format(
            registry or "default"))
        push_repo(img_id, docker_repo, registry=registry, logger=logger)
    return img_id, commit_id


def push_repo(img_id, repo, registry=None, docker_tag=None, logger=None):
    ''' Pushes a repository to a registry
        img_id:     Image ID to push
        repo:       Repository name where img_id should be tagged
        registry:   Private registry where image needs to be pushed
        docker_tag: Tag to be applied to the image in docker repo
        logger:     Logger instance
    '''
    exc = None
    if registry is not None:
        repo = '{0}/{1}'.format(registry, repo)
        logger.info('Also tagging {0}'.format(repo))
        client.tag(img_id, repo, docker_tag)
    for i in xrange(4):
        try:
            pushlog = client.push(repo)
            if '"error":"' in pushlog:
                raise RuntimeError('Error while pushing: {0}'.format(pushlog))
        except Exception as e:
            exc = e
            continue
        return
    raise exc

########NEW FILE########
__FILENAME__ = git
import os
import tempfile
import logging

from dulwich import index
from dulwich.client import get_transport_and_path
from dulwich.objects import Tag
from dulwich.repo import Repo

logger = logging.getLogger(__name__)


def clone_branch(repo_url, branch="master", folder=None):
    return clone(repo_url, 'refs/heads/' + branch, folder)


def clone_tag(repo_url, tag, folder=None):
    return clone(repo_url, 'refs/tags/' + tag, folder)


def checkout(rep, ref=None):
    if ref is None:
        ref = 'refs/heads/master'
    elif ref.startswith('refs/tags'):
        ref = rep.ref(ref)
    if isinstance(rep[ref], Tag):
        rep['HEAD'] = rep[ref].object[1]
    else:
        rep['HEAD'] = rep.refs[ref]
    indexfile = rep.index_path()
    tree = rep["HEAD"].tree
    index.build_index_from_tree(rep.path, indexfile, rep.object_store, tree)
    return rep.path


def pull(origin, rep, ref=None):
    clone(origin, ref, None, rep)
    return rep, rep.path


def clone(repo_url, ref=None, folder=None, rep=None):
    if ref is None:
        ref = 'refs/heads/master'
    logger.debug("clone repo_url={0}, ref={1}".format(repo_url, ref))
    if not rep:
        if folder is None:
            folder = tempfile.mkdtemp()
        else:
            os.mkdir(folder)
        logger.debug("folder = {0}".format(folder))
        rep = Repo.init(folder)
    client, relative_path = get_transport_and_path(repo_url)
    logger.debug("client={0}".format(client))

    remote_refs = client.fetch(relative_path, rep)
    for k, v in remote_refs.iteritems():
        try:
            rep.refs.add_if_new(k, v)
        except:
            pass

    if ref.startswith('refs/tags'):
        ref = rep.ref(ref)

    if isinstance(rep[ref], Tag):
        rep['HEAD'] = rep[ref].object[1]
    else:
        rep['HEAD'] = rep[ref]
    indexfile = rep.index_path()
    tree = rep["HEAD"].tree
    index.build_index_from_tree(rep.path, indexfile, rep.object_store, tree)
    logger.debug("done")
    return rep, folder

########NEW FILE########
__FILENAME__ = summary

class SummaryItem(object):
    def __init__(self, data):
        self.line = data.get('line', None)
        self.repository = data.get('repository', None)
        self.commit_id = data.get('commit', None)
        self.exc = data.get('exc', None)
        self.image_id = data.get('id', None)
        self.source = data.get('source', None)
        self.tag = data.get('tag', None)


class Summary(object):
    def __init__(self):
        self._summary = {}
        self._has_exc = False

    def _add_data(self, image, linestr, data):
        linestr = linestr.strip('\n')
        parts = linestr.split(':', 1)
        data.tag = parts[0]
        data.source = parts[1]
        if image not in self._summary:
            self._summary[image] = {linestr: data}
        else:
            self._summary[image][linestr] = data

    def add_exception(self, image, line, exc, commit=None):
        lineno, linestr = line
        self._add_data(image, linestr, SummaryItem({
            'line': lineno,
            'exc': str(exc),
            'repository': image,
            'commit': commit
        }))
        self._has_exc = True

    def add_success(self, image, line, img_id, commit=None):
        lineno, linestr = line
        self._add_data(image, linestr, SummaryItem({
            'line': lineno,
            'id': img_id,
            'repository': image,
            'commit': commit
        }))

    def print_summary(self, logger=None):
        linesep = ''.center(61, '-') + '\n'
        s = 'BREW BUILD SUMMARY\n' + linesep
        success = 'OVERALL SUCCESS: {}\n'.format(not self._has_exc)
        details = linesep
        for image, lines in self._summary.iteritems():
            details = details + '{}\n{}'.format(image, linesep)
            for linestr, data in lines.iteritems():
                details = details + '{0:2} | {1} | {2:50}\n'.format(
                    data.line,
                    'KO' if data.exc else 'OK',
                    data.exc or data.image_id
                )
            details = details + linesep
        if logger is not None:
            logger.info(s + success + details)
        else:
            print s, success, details

    def exit_code(self):
        return 1 if self._has_exc else 0

    def items(self):
        for lines in self._summary.itervalues():
            for item in lines.itervalues():
                yield item

########NEW FILE########
__FILENAME__ = create_db
import sys

sys.path.append('./lib')

import db

data = db.DbManager(debug=True)
data.generate_tables()

########NEW FILE########
__FILENAME__ = db
import datetime

import sqlalchemy as sql


metadata = sql.MetaData()
summary = sql.Table(
    'summary', metadata,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('result', sql.Boolean),
    sql.Column('build_date', sql.String)
)

summary_item = sql.Table(
    'summary_item', metadata,
    sql.Column('id', sql.Integer, primary_key=True),
    sql.Column('repo_name', sql.String),
    sql.Column('exception', sql.String),
    sql.Column('commit_id', sql.String),
    sql.Column('image_id', sql.String),
    sql.Column('source_desc', sql.String),
    sql.Column('tag', sql.String),
    sql.Column('summary_id', None, sql.ForeignKey('summary.id'))
)


class DbManager(object):
    def __init__(self, db='/opt/stackbrew/data.db', debug=False):
        self._engine = sql.create_engine('sqlite:///' + db, echo=debug)

    def generate_tables(self):
        metadata.create_all(self._engine)

    def insert_summary(self, s):
        c = self._engine.connect()
        summary_id = None
        with c.begin():
            ins = summary.insert().values(
                result=not s.exit_code(),
                build_date=str(datetime.datetime.now()))
            r = c.execute(ins)
            summary_id = r.inserted_primary_key[0]
            for item in s.items():
                ins = summary_item.insert().values(
                    repo_name=item.repository,
                    exception=item.exc,
                    commit_id=item.commit_id,
                    image_id=item.image_id,
                    source_desc=item.source,
                    tag=item.tag,
                    summary_id=summary_id
                )
                c.execute(ins)
        return summary_id

    def latest_status(self):
        c = self._engine.connect()
        s = sql.select([summary]).order_by(summary.c.id.desc()).limit(1)
        res = c.execute(s)
        row = res.fetchone()
        if row is not None:
            return dict(row)
        return None

    def get_summary(self, id):
        c = self._engine.connect()
        s = sql.select([summary_item]).where(summary_item.c.summary_id == id)
        res = c.execute(s)
        return [dict(row) for row in res]

    def get_latest_successful(self, repo, tag=None):
        c = self._engine.connect()
        tag = tag or 'latest'
        s = sql.select([summary_item]).where(
            summary_item.c.repo_name == repo
        ).where(
            summary_item.c.tag == tag
        ).where(
            summary_item.c.image_id is not None
        ).order_by(
            summary_item.c.summary_id.desc()
        ).limit(1)
        res = c.execute(s)
        row = res.fetchone()
        if row is not None:
            return dict(row)
        return None

########NEW FILE########
__FILENAME__ = periodic
import atexit
import os
import threading

lockfiles = []


def init_task(fn, period, lockfile='/opt/stackbrew/brw.lock', logger=None):
    def periodic(logger):
        if logger is not None:
            logger.info('Periodic task started')
        t = threading.Timer(period, periodic, [logger])
        t.daemon = True
        t.start()
        fn()
    if os.path.exists(lockfile):
        raise RuntimeError('Lockfile already present.')
    open(lockfile, 'w').close()
    lockfiles.append(lockfile)
    t = threading.Timer(0, periodic, [logger])
    t.daemon = True
    t.start()


def clear_lockfiles(lockfiles):
    for lock in lockfiles:
        os.remove(lock)


def on_exit(lockfiles):
    clear_lockfiles(lockfiles)

atexit.register(on_exit, lockfiles)

########NEW FILE########
__FILENAME__ = utils
import json


def resp(app, data=None, code=200, headers=None):
    if not headers:
        headers = {}
    if 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data)
    return app.make_response((data, code, headers))

########NEW FILE########
__FILENAME__ = wsgi
#!/usr/bin/env python
import app as application
########NEW FILE########
