__FILENAME__ = nginx_conf
# -*- coding: utf-8 -*-

""" 根据站点的配置文件，生成nginx的配置 

- input: /var/sites/contents/sites/_config.yaml
- output: /etc/nginx/sites-enabled/zcms.conf:

"""

import os
import yaml

nginx_conf = """server{
    listen 80;
    location  /  {
        proxy_set_header        HOST $http_host;

        rewrite ^/themes/(.*) /themes/$1 break;

        proxy_pass     http://127.0.0.1:8000;
        proxy_redirect off;
    }
}

%s
"""

if __name__ == '__main__':
    sites_config = []
    for site_name in os.listdir('/var/sites/contents/'):
        config = file('/var/sites/contents/%s/_config.yaml' % site_name, 'r')
        site_config = yaml.load(config)
        if site_config['domain_name']:
            sites_config.append("""server{
                listen 80;
                server_name %s;
                location  /  {
                proxy_set_header        HOST $http_host;
                rewrite ^/themes/(.*) /themes/$1 break;
                proxy_set_header        X-ZCMS-VHM true;

                rewrite ^/(.*) /%s/$1 break;

                proxy_pass     http://127.0.0.1:8000;
                proxy_redirect off;
                }
                }""" % (site_config['domain_name'], site_name))

    open('/etc/nginx/sites-enabled/zcms.conf', 'w').write(nginx_conf % '\n'.join(sites_config))

########NEW FILE########
__FILENAME__ = blog_views
# -*- encoding: utf-8 -*-

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import render

#from z3c.batching.batch import Batch

from models import Page 
from webhelpers import paginate
from utils import getDisplayTime, zcms_template
from datetime import datetime

def blog_view(context, request, size=5):
    current_page = request.params.get('page', '0')
    # XXX hack, 很奇怪会附加一个/
    if current_page.endswith('/'):
        current_page = current_page[:-1]
    current_page = int(current_page)
    page_url = paginate.PageURL_WebOb(request)
    blog_subpaths = context.get_recent_file_subpaths()
    blog_page = paginate.Page(blog_subpaths, current_page, items_per_page=size, url=page_url)

    posts = []
    for subpath in blog_page:
        obj = context.get_obj_by_subpath(subpath)
        if obj is not None:
            raw_html = obj.render_html(request)
            converted_html = raw_html.replace(
                'src="img/',
                'src="%s/../img/' % obj.url(request)
            )
            dc = obj.metadata
            created = dc.get('modified', dc.get('created', datetime.now()))
            posts.append({
                'title':obj.title,
                'description':dc.get('description', ''),
                'url':subpath,
                'created':getDisplayTime(created),
                'creator':dc.get('creator', ''),
                'body':converted_html,
            })

    batch = blog_page.pager()
    return render(
        'templates/bloglist.pt',
        dict(
            result = posts,
            batch = batch,
        )
    )


@view_config(context=Page, name="blogpost.html")
@zcms_template
def blog_post_view(context, request):
    """ 单独一篇博客 """
    obj = context
    dc = obj.metadata

    result = {}
    result['url'] = obj.__name__
    result['title'] = obj.title
    result['description'] = dc.get('description', '')
    result['created'] = dc.get('modified', dc.get('created', datetime.now()))
    result['creator'] = dc.get('creator', '')

    pachs = request.url.split('/')
    img_url =  '/'.join(pachs[0:len(pachs)-2]) + '/img/'
    result['body'] = obj.render_html(request).replace('src="img/', 'src="%s' % img_url)

    idcomments_acct = request.registry.settings.get('idcomments_acct', '')

    title = context.title
    description = dc.get('description', '')
    return render(
        'templates/blogpost_main.pt',
        dict(
            result = result,
            post_created = getDisplayTime(result['created']),
            idcomments_acct = idcomments_acct,
        )
    )


########NEW FILE########
__FILENAME__ = blogs
# -*- coding: utf-8 -*-

# 博客列表指令

"""
目的：动态的生成博客列表html
使用方法::

    .. blogs:: asdfasdfasd
       :size: 5

参考： 
http://docutils.sourceforge.net/docs/howto/rst-directives.html

"""
"""
navtree_directive.arguments = (0, 1, 0) 
     three args: required_arguments,optional_arguments,final_argument_whitespace
     .. navtree:: no required_arguments
     :root_depth: one optional_arguments
"""
from docutils import nodes
from docutils.parsers.rst import directives
from zcms.blog_views import blog_view

def blogs_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    context = state.document.settings.context
    request = state.document.settings.request

    parsed = blog_view(context.__parent__, request, options.get('size', 5))
    return [nodes.raw('', parsed, format='html')]

blogs_directive.arguments = (0, 1, 0) 
blogs_directive.has_content = 1
blogs_directive.content = 1  
blogs_directive.options = {'size': int}

directives.register_directive('blogs', blogs_directive)


########NEW FILE########
__FILENAME__ = codeblock
# -*- coding: utf-8 -*-

# 一组补丁集合

"""
    The Pygments reStructuredText directive
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This fragment is a Docutils_ 0.4 directive that renders source code
    (to HTML only, currently) via Pygments.

    To use it, adjust the options below and copy the code into a module
    that you import on initialization.  The code then automatically
    registers a ``sourcecode`` directive that you can use instead of
    normal code blocks like this::

        .. sourcecode:: python

            My code goes here.

    If you want to have different code styles, e.g. one with line numbers
    and one without, add formatters with their names in the VARIANTS dict
    below.  You can invoke them instead of the DEFAULT one by using a
    directive option::

        .. sourcecode:: python
            :linenos:

            My code goes here.

    Look at the `directive documentation`_ to get all the gory details.

    .. _Docutils: http://docutils.sf.net/
    .. _directive documentation:
       http://docutils.sourceforge.net/docs/howto/rst-directives.html

    :copyright: Copyright 2006-2009 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Options
# ~~~~~~~

# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False

from pygments.formatters import HtmlFormatter

# The default formatter
DEFAULT = HtmlFormatter(noclasses=INLINESTYLES)

# Add name -> formatter pairs for every variant you want to use
VARIANTS = {
    # 'linenos': HtmlFormatter(noclasses=INLINESTYLES, linenos=True),
}


from docutils import nodes
from docutils.parsers.rst import directives

from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer

def pygments_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    try:
        lexer = get_lexer_by_name(arguments[0])
    except ValueError:
        # no lexer found - use the text one instead of an exception
        lexer = TextLexer()
    # take an arbitrary option if more than one is given
    formatter = options and VARIANTS[options.keys()[0]] or DEFAULT
    parsed = highlight(u'\n'.join(content), lexer, formatter)
    return [nodes.raw('', parsed, format='html')]

pygments_directive.arguments = (1, 0, 1)
pygments_directive.content = 1
pygments_directive.options = dict([(key, directives.flag) for key in VARIANTS])

directives.register_directive('code-block', pygments_directive)

########NEW FILE########
__FILENAME__ = navtree
# -*- coding: utf-8 -*-

# 导航树指令

"""
目的：动态的生成导航树html
使用方法::

    .. navtree:: asdfasdfasd
       :root_depth: 1
       :class: nav nav-pills nav-stacked

参考： 
http://docutils.sourceforge.net/docs/howto/rst-directives.html

"""
"""
navtree_directive.arguments = (0, 1, 0) 
     three args: required_arguments,optional_arguments,final_argument_whitespace
     .. navtree:: no required_arguments
     :root_depth: one optional_arguments
"""
from docutils import nodes
from docutils.parsers.rst import directives
from string import Template
from zcms.models import Folder, File, Image

nav_root_template = Template(r""" <ul class="${ul_class}"> ${nav_items} </ul> """)

nav_item_template = Template(r"""
<li class="${class_str}"> <a href="${node_url}"> ${node_title} </a> </li>""")

def navtree_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    context = state.document.settings.context
    request = state.document.settings.request

    parsed = nav_tree(context, request, options.get('root_depth', 1), options.get('class', 'nav nav-list'))
    return [nodes.raw('', parsed, format='html')]

navtree_directive.arguments = (0, 1, 0)
navtree_directive.has_content = 1
navtree_directive.content = 1 
navtree_directive.options = {'root_depth': int, 'class':str}

directives.register_directive('navtree', navtree_directive)

# 生成navtree
def nav_tree(context, request, root_depth, klass):
    """render navtree structure, root_depth from root"""
    # get the root accoding to root_depth
    if isinstance(context, Folder):
        parents = [context]
    else:
        parents = []
    current = context.__parent__
    while current.__parent__:
        parents.insert(0, current)
        current = current.__parent__

    # 超界
    if len(parents) < root_depth + 1:
        return ''

    root = parents[root_depth]
    nodes = []
    parent_paths = [obj.vpath for obj in parents]
    for obj in root.values(True, True):
        is_active = obj.vpath in parent_paths or obj.vpath == context.vpath
        nodes.append(
           nav_item_template.substitute(
               class_str = 'active' if is_active else '',
               node_url = obj.url(request),
               node_title = obj.title,
           ))

    nav_items = ''.join(nodes)
    return nav_root_template.substitute(ul_class=klass, nav_items=nav_items)


########NEW FILE########
__FILENAME__ = news
# -*- coding: utf-8 -*-

# 博客列表指令

"""
目的：动态的生成新闻面板
使用方法::

    .. news:: 
       :path: /edoprojects.com/blogs
       :size: 5

参考： 
http://docutils.sourceforge.net/docs/howto/rst-directives.html

"""
"""
navtree_directive.arguments = (0, 1, 0) 
     three args: required_arguments,optional_arguments,final_argument_whitespace
     .. navtree:: no required_arguments
     :root_depth: one optional_arguments
"""
from docutils import nodes
from docutils.parsers.rst import directives
from zcms.utils import getDisplayTime
from datetime import datetime

def news_directive(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine):
    context = state.document.settings.context
    request = state.document.settings.request

    parsed = render_news(context, request, options['path'], options.get('size', 5), options.get('class', ''))
    return [nodes.raw('', parsed, format='html')]

news_directive.arguments = (0, 1, 0) 
news_directive.has_content = 1
news_directive.content = 1  
news_directive.options = {'size': int, 'path': str, 'class':str}

directives.register_directive('news', news_directive)

def render_news(context, request, path, size=5, klass='nav nav-list'):
    site = context.get_site()
    container = site.get_obj_by_subpath(path)
    container_url = container.url(request)
    title = container.title

    posts = []
    blog_subpaths = container.get_recent_file_subpaths()

    for subpath in blog_subpaths[:size]:
        obj = container.get_obj_by_subpath(subpath)
        if obj is None: continue

        dc = obj.metadata
        url = obj.url(request)
        if url.endswith('/'): url = url[:-1]
        created = dc.get('modified', dc.get('created', datetime.now()))
        posts.append("""<li><a href="%s">%s</a><span>%s</span></li>""" % \
              (url, obj.title, getDisplayTime(created)))

    return '<ul class="%s">%s</ul>' % (klass, ''.join(posts))

########NEW FILE########
__FILENAME__ = frs
# -*- encoding:utf-8 -*-
""" vfs = virtual file system; a virtual posix like file system
"""

import os, shutil
import posixpath
from types import UnicodeType
import yaml
import time
import sys
import fnmatch

FS_CHARSET = sys.getfilesystemencoding()

def ucopytree(ossrc, osdst, symlinks=False):
    # ucopy2 dosn't work with unicode filename yet
    if type(osdst) is UnicodeType and \
            not os.path.supports_unicode_filenames:
        ossrc = ossrc.encode(FS_CHARSET)
        osdst = osdst.encode(FS_CHARSET)
    shutil.copytree(ossrc, osdst, symlinks)

def umove(ossrc, osdst):
    # umove dosn't work with unicode filename yet
    if type(osdst) is UnicodeType and \
           not os.path.supports_unicode_filenames:
        ossrc = ossrc.encode(FS_CHARSET)
        osdst = osdst.encode(FS_CHARSET)
    shutil.move(ossrc, osdst)

class FRS:

    def __init__(self, cache_root='/tmp'):
        self._top_paths = {}
        self.cache_root = cache_root

    def mount(self, name, path):
        """ XXX only support mount top dirs only now

        mount filesystem path to vfs
        """
        if not os.path.exists(path):
            raise OSError('no mount path: '+ path)
        if name.startswith('/'):
            name = name[1:]
        self._top_paths[name] = path

    def setCacheRoot(self, path):
        """ where to push caches """
        self.cache_root = path

    def vpath(self, ospath):
        """ transform ospath to vpath """
        for root, path in self._top_paths.items():
            if ospath.startswith(path + '/'):
                return '/%s%s' % (root, ospath[len(path):])

    def cache_path(self, vpath):
        """ get os path of cache folder for vpath """
        return os.path.join(self.cache_root, 
                            *vpath.split('/') )

    def ospath(self, vPath):
        """ transform to a real os path """
        if not vPath.startswith('/'):
            raise OSError(vPath)
        parts = vPath.split('/')
        toppath = self._top_paths[parts[1]]
        return os.path.join(toppath, *parts[2:])

    def exists(self, vPath):
        try:
            path = self.ospath(vPath)
        except OSError:
            return False
        return os.path.exists(path)

    def joinpath(self, *arg):
        return posixpath.join(*arg)

    def basename(self, path):
        return posixpath.basename(path)

    def splitext(self, name):
        return os.path.splitext(name)

    def stat(self, vPath):
        return os.stat(self.ospath(vPath))

    def dirname(self, path):
        return posixpath.dirname(path)

    def ismount(self, vPath):
        """ return if vPath is a mount folder
        """
        return vPath[1:] in self.listdir('/')

    def isdir(self, vPath):
        return os.path.isdir(self.ospath(vPath))

    def isfile(self, vPath):
        return os.path.isfile(self.ospath(vPath))

    def atime(self, vPath):
        return os.path.getatime( self.ospath(vPath) )

    def mtime(self, vPath):
        return os.path.getmtime( self.ospath(vPath) )

    def ctime(self, vPath):
        return os.path.getctime( self.ospath(vPath) )

    def getsize(self, vPath):
        return os.path.getsize( self.ospath(vPath) )

    def listdir(self, vPath, pattern=None):
        if vPath == '/':
             return self._top_paths.keys()
        names = os.listdir(self.ospath(vPath))
        if pattern is not None:
            names = fnmatch.filter(names, pattern)
        return names

    def dirs(self, vPath, pattern=None):
        names = [ name for name in self.listdir(vPath, pattern)\
	                  if self.isdir(self.joinpath(vPath, name))]
        return names

    def files(self, vPath, pattern=None):
        names = [ name for name in self.listdir(vPath, pattern)\
	                  if self.isfile(self.joinpath(vPath, name))]
        return names

    def open(self, vPath, mode='r'):
        return file(self.ospath(vPath), mode)

    def move(self, vPath1, vPath2):
        # can't remove mount folder
        if self.ismount(vPath1):
            raise Exception("can't remove mount folder %s" % vPath1)
        if self.ismount(vPath2):
            raise Exception("can't move to mount folder %s" % vPath2)

        umove(self.ospath(vPath1), self.ospath(vPath2) )
        #notify(AssetMoved(self, vPath1, vPath2))

    def mkdir(self, vPath, mode=0777):
        os.mkdir(self.ospath(vPath), mode)

    def makedirs(self, vPath, mode=0777):
        os.makedirs(self.ospath(vPath), mode)

    def getNewName(self, path, name):
        while self.exists(self.joinpath(path, name)):
            name = 'copy_of_' + name
        return name

    def remove(self, vPath):
        """ remove a file path"""
        os.remove(self.ospath(vPath) )
        #notify(AssetRemoved(self, vpath))

    def copyfile(self, vSrc, vDst):
        shutil.copyfile(self.ospath(vSrc), self.ospath(vDst))

    def copytree(self, vSrc, vDst):
        # copy2 don't work well with encoding
        # in fact it is os.utime don't work well
        ossrc = self.ospath(vSrc)
        osdst = self.ospath(vDst)
        ucopytree(ossrc, osdst, symlinks=False)

    def rmtree(self, vPath, ignore_errors=False, onerror=None):
        # can't remove mount folder
        if self.ismount(vPath):
            raise Exception("can't remove mount folder %s" % vPath)

        shutil.rmtree(self.ospath(vPath), ignore_errors, onerror)

    def touch(self, vpath):
        fd = os.open(self.ospath(vpath), os.O_WRONLY | os.O_CREAT, 0666)
        os.close(fd)

    def walk(self, top, topdown=True, onerror=None):
        if top == '/':
            mount_dirs = self._top_paths.keys()
            yield '/', mount_dirs,[]
            for name in mount_dirs:
                for item in self.walk('/' + name, topdown, onerror):
                    yield item
        else:
            top_ospath = os.path.normpath(self.ospath(top))
            top_ospath_len = len(top_ospath)
            for dirpath, dirnames, filenames in os.walk(top_ospath,topdown,onerror):

                if dirnames or filenames:
                    dir_sub_path = dirpath[top_ospath_len+1:].replace(os.path.sep,  '/')
                    if dir_sub_path:
                        yield self.joinpath(top, dirpath[top_ospath_len+1:].replace(os.path.sep,  '/')), dirnames, filenames
                    else:
                        yield top, dirnames, filenames

    # asset management

    def removeAsset(self, path):
        if self.exists(path):
            if self.isfile(path):
                self.remove(path)
            else:
                self.rmtree(path)

        os.remove(self.cache_path(path))

    def moveAsset(self, src, dst):
        """ rename or move a file or folder
        """
        if not self.exists( self.dirname(dst) ):
            self.makedirs( self.dirname(dst) )
        self.move(src, dst)

        cache_src = self.cache_path(src)
        if not os.path.exists(cache_src):
            return 

        cache_dst = self.cache_path(dst)
        if not os.path.exists( os.path.dirname(cache_dst) ):
            os.makedirs( os.path.dirname(cache_dst) )
        shutil.move(cache_src, cache_dst)

    def copyAsset(self, src, dst, **kw):
        """ copy folder / file 

        don't keep stat
        """
        if self.isfile(src):
            self.copyfile(src, dst)
        else:
            # copy folder
            if not self.exists(dst):
                self.makedirs(dst)
            for name in self.listdir(src):
                self.copyAsset(self.joinpath(src, name), self.joinpath(dst, name), copycache=0)

        # copy cache
        cache_src = self.cache_path(src)
        if not os.path.exists(cache_src):
            return

        cache_dst = self.cache_path(dst)
        cache_dst_parent = os.path.dirname(cache_dst)
        if not os.path.exists( cache_dst_parent ):
            os.makedirs(cache_dst_parent )
        if not os.path.exists(cache_dst):
            ucopytree(cache_src, cache_dst)


########NEW FILE########
__FILENAME__ = models
# -*- encoding: utf-8 -*-

__docformat__ = 'restructuredtext'
import yaml
import time
from datetime import datetime
import tempfile
import os.path
import stat
import posixpath
from pyramid.threadlocal import get_current_registry
import markdown
import fnmatch
from utils import rst2html

def get_sub_time_paths(folder, root_vpath):
    """ 迭代查找整个子目录，找出所有的子文档的路径 """

    result = []
    for obj in folder.values(True, False):
        dc = obj.metadata
        if isinstance(obj, Folder):
            result.extend(get_sub_time_paths(obj, root_vpath))
        elif isinstance(obj, Page):
            result.append((
                dc.get('modified', 
                dc.get('created', datetime.now())),
                obj.vpath.replace(root_vpath + '/', ''),
            ))
    return result

class FRSAsset(object):

    __parent__ = None
    __name__ = ''

    def __init__(self, frs, vpath=u'/'):
        self.frs = frs
        self.vpath = vpath
        self._md = None

    @property
    def ospath(self):
        return self.frs.ospath(self.vpath)

    def url(self, request):
        """ 得到对象的URL，如果不是文件夹，去除之后的/ """
        if isinstance(self, Folder):
            return request.resource_url(self) 
        else:
            return request.resource_url(self)[:-1]

    @property
    def title(self):
        title = self.metadata.get('title', '')
	if title: return title
	return self.__name__.split('.', 1)[0].replace('-', ' ')

    def get_site(self):
        """ 得到所属的站点 """
        context = self
        while context.vpath.find('/', 1) != -1:
            context = context.__parent__
        return context

    def _get_slot_info(self, name):
        # 往上找左右列
        if self.__name__ == '':
             return '', ''
        source_path = str(self.ospath)
        if isinstance(self, Folder):
            rst_path = os.path.join(source_path, '_' + name + '.rst')
        else:
            rst_path = os.path.join(os.path.dirname(source_path), '_' + name + '_' + self.__name__)

        if os.path.exists(rst_path):
            col = open(rst_path).read()
            return col, rst_path

        if self.__parent__ is None:
            return '', source_path
        return self.__parent__._get_slot_info(name)

    def render_slots(self, name, request):
        """ name can be: left, right, upper """
        rst_content, rst_path = self._get_slot_info(name)
        if rst_content != '':
            return rst2html(rst_content, rst_path, self, request)
        else:
            return ''

class Folder(FRSAsset):

    @property
    def metadata(self):
        metadatapath = self.frs.joinpath(self.vpath, '_config.yaml')
        try:
            return yaml.load(self.frs.open(metadatapath))
        except KeyError:
            return {}
        except IOError:
            return {}

    def _filter(self, key):
        """Subclasses may overwrite this method.

        Filter possible assets.
        """
        return (not key.startswith('.'))

    def _get(self, key):
        if not self._filter(key):
            raise KeyError(key)

        try:
            path = self.frs.joinpath(self.vpath, key)
            st = self.frs.stat(path)
        except OSError:
            raise KeyError(key)

        if stat.S_ISDIR(st.st_mode):
            obj = Folder(self.frs, path)
        elif stat.S_ISREG(st.st_mode):
            ext = posixpath.splitext(path)[1].lower()
            if ext in ['.gif', '.bmp', '.jpg', '.jpeg', '.png']:
                obj = Image(self.frs, path)
            elif ext in ['.html', '.htm', '.rst', '.md']:
                obj = Page(self.frs, path)
            else:
                obj = File(self.frs, path)
        else:
            raise KeyError(key)

        obj.__parent__ = self
        obj.__name__ = key
        return obj

    def keys(self, do_filter=False, do_sort=False):
        if self.vpath is None:
            return []

        keys = sorted([
            unicode(key) for key in self.frs.listdir(self.vpath)
            if self._filter(key)
        ])

        if not do_filter and not do_sort:
            return keys

        metadata = self.metadata

        if do_filter:
            hidden_keys = metadata.get('exclude', [])
	    hidden_keys.extend(['_*'])
            for key in hidden_keys:
                for _key in fnmatch.filter(keys, key):
                    keys.remove(_key)

        if do_sort:
            sorted_keys = metadata.get('order', [])
            if sorted_keys:
                sorted_keys.reverse()
                for key in sorted_keys:
                    try:
                        keys.remove(key)
                        keys.insert(0, key)
                    except ValueError:
                        # wrong key in config file
                        pass
        return keys

    def get(self, key, default=None):
        try:
            return self._get(key)
        except KeyError:
            return default

    def values(self, do_filter=False, do_sort=False):
        return [self._get(key) for key in self.keys(do_filter, do_sort)]

    def items(self, do_filter=False, do_sort=False):
        return [(key, self._get(key)) for key in self.keys(do_filter, do_sort)]

 
    def get_recent_file_subpaths(self):
        # 1. 检查是否存在有效的缓存，如果有，直接返回sub_vpath清单
        # ['asdfa/aa.doc', 'asdf.rst']
        #today_str = datetime.date.today().strftime('%Y-%m-%d')
        timenow = [t for t in time.localtime(time.time())[:5]]
        str_timenow = '-'.join(
            [str(t) for t in time.localtime(time.time())[:5]])

        tmp_dir = tempfile.gettempdir()
        cache_name = 'zcmscache' + '-'.join(self.vpath.split('/'))
        cache_path = os.path.join(tmp_dir, cache_name) + '.txt'
        sub_vpaths = []
        cache_is_recent = False
        minutes_lag = 720  # 默认半天

        def lag_minutes(time_now, txt_time):
            tn, tt = time_now[:], txt_time[:]
            to_expend = [0, 0, 75, 0]
            for t in to_expend:
                tn.append(t)
                tt.append(t)
            t1 = time.mktime(tn)
            t2 = time.mktime(tt)
            lag = (t1 - t2) / 60
            return lag

        # try the cache first
        is_debug = get_current_registry().settings.get('pyramid.debug_templates', False)
        if not is_debug and os.path.exists(cache_path):
            rf = file(cache_path, 'r')
            txt_date = rf.readline().rstrip()
            if txt_date != '':
                txt_time = [int(n) for n in txt_date.split('-')]
                if lag_minutes(timenow, txt_time) < minutes_lag:
                    cache_is_recent = True
                    sub_vpaths = [rl.rstrip() for rl in rf.readlines()]
            rf.close()

        # 2. 否则重新查找出来，并更新缓存
        if not cache_is_recent:
            wf = file(cache_path, 'w')
            to_write = str_timenow + '\n'

            sub_time_vpaths = get_sub_time_paths(self, self.vpath)

            def mycmp(x, y):
                if x[0] == '' or y[0] == '':
                    return -1
                return cmp(y[0], x[0])

            # todo
            sub_time_vpaths.sort(mycmp)
            sub_vpaths = [vpath[1] for vpath in sub_time_vpaths]

            for vpath in sub_vpaths:
                to_write += vpath + '\n'
            wf.write(to_write)
            wf.close()
        return sub_vpaths

    def get_obj_by_subpath(self, sub_vpath):
        """ 根据vpath，找到对象 """
        cur = self
        for name in sub_vpath.split('/'):
            if not name:
                pass
            cur = cur.get(name)
        return cur

    def __getitem__(self, key):
        """ traverse """
        return self._get(key)

    def __contains__(self, key):
        return key in self.keys()

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self.keys())


class File(FRSAsset):

    def _get_data(self):
        if self.vpath is None:
            return ''
        else:
            return self.frs.open(self.vpath, 'rb').read()

    def _set_data(self, value):
        if self.vpath is None:
            raise NotImplementedError('Choose first a valid path.')
        else:
            self.frs.open(self.vpath, 'wb').write(value)

    data = property(_get_data, _set_data)

    @property
    def metadata(self):
        return {'title':self.__name__.split('.', 1)[0].replace('-', ' ')}

    @property
    def contentType(self):
        if self.vpath.endswith('html'):
            return 'text/html'
        elif self.vpath.endswith('rst'):
            return 'text/rst'
        elif self.vpath.endswith('md'):
            return 'text/markdown'
        else:
            return 'text/plain'

class Image(File): pass
   
class Page(File):

    @property
    def metadata(self):
        if self._md is None:
            f = self.frs.open(self.vpath, 'rb')
            row = f.readline().strip()
            # support utf8
            if row not in ['---', '\xef\xbb\xbf---']: 
                self._md = {}
                return self._md

            lines = []
            row = f.readline()
	    while row:
                if row.startswith('---'): break
                lines.append(row)
                row = f.readline()
            else:
                self._md = {}
                return self._md

            self._md = yaml.load(''.join(lines))
        return self._md

    def get_body(self):
        f = self.frs.open(self.vpath, 'rb')
        row = f.readline().strip()
        # windows会自动增加utf8的标识字
        if row[0:3] == '\xef\xbb\xbf':
            row = row[3:]
        if row == '---': 
            lines = []
            row = f.readline()
            while row and not row.startswith('---'): 
                row = f.readline()
            row = ''
        return row + '\n' + f.read()

    def render_html(self, request):
        data = self.get_body()

        lstrip_data = data.lstrip()
        if self.__name__.endswith('.rst'):
            # 判断文件内容是否为html
            if lstrip_data and lstrip_data[0] == '<':
                return data

            # 不显示的标题区域，标题在zpt里面独立处理了
            ospath = self.ospath
            return rst2html(data, str(ospath), self, request)
        elif self.__name__.endswith('.md'):
            return ''.join(markdown.Markdown().convert(data.decode('utf8')))

        return data


########NEW FILE########
__FILENAME__ = utils
# -*- encoding: utf-8 -*-

from datetime import datetime
from docutils.core import publish_parts
from docutils.writers.html4css1 import Writer
import urllib2
import os
import chardet
from string import Template
from pyramid.response import Response
from pyramid.threadlocal import get_current_registry
import rst2html5

_templates_cache = {}
EMPTY_THEME = u"""
     <html>
       <head>
          <title>$title - $site_title</title>
          <meta name="Description" content="$site_description"/>
       </head>
       <body>
          <ul>$nav</ul>
          <div>$upper</div>
          <table>
            <tr>
               <td>$left</td>
               <td>$content</td>
               <td>$right</td>
            </tr>
          </table>
       </body>
     </html>
"""

def getDisplayTime(input_time, show_mode='localdate'):
    """ 人性化的时间显示: (支持时区转换)

    time 是datetime类型，或者timestampe的服点数，
    最后的show_mode是如下:

    - localdate: 直接转换为本地时间显示，到天
    - localdatetime: 直接转换为本地时间显示，到 年月日时分
    - localtime: 直接转换为本地时间显示，到 时分
    - deadline: 期限，和当前时间的比较天数差别，这个时候返回2个值的 ('late', '12天前')
    - humandate: 人可阅读的天，今天、明天、后天、昨天、前天，或者具体年月日 ('today', '今天')
    """
    if not input_time:
        return ''

    today = datetime.now()
    time_date = datetime(input_time.year, input_time.month, input_time.day)
    year, month, day = today.year, today.month, today.day
    today_start = datetime(year, month, day)

    to_date = today_start - time_date

    # 期限任务的期限
    if show_mode == 'localdate':
        return input_time.strftime('%Y-%m-%d')
    elif show_mode == 'localdatetime':
        return input_time.strftime('%Y-%m-%d %H:%M')
    elif show_mode == 'localtime':
        return input_time.strftime('%H:%M')
    elif show_mode == 'deadline':
        if to_date == 0:
            return ('Today', '今天')
        elif to_date < 0:
            if to_date == -1:
                return (None, '明天')
            elif to_date == -2:
                return (None, '后天')
            else:
                return (None, str(int(-to_date))+'天')
        elif to_date > 0:
            if to_date == 1:
                return ('late', '昨天')
            elif to_date == 2:
                return ('late', '前天')
            else:
                return ('late', str(int(to_date))+'天前')
    elif show_mode == 'humandate':
        if to_date == 0:
            return ('Today', '今天')
        elif to_date < 0:
            if to_date == -1:
                return (None, '明天')
            elif to_date == -2:
                return (None, '后天')
            else:
                return (None, input_time.strftime('%Y-%m-%d'))
        elif to_date > 0:
            if to_date == 1:
                return ('late', '昨天')
            elif to_date == 2:
                return ('late', '前天')
            else:
                return ('late', input_time.strftime('%Y-%m-%d'))

def rst2html(rst, path, context, request):
    settings = {
        'halt_level':6,
        'input_encoding':'UTF-8',
        'output_encoding':'UTF-8',
        'initial_header_level':1,
        'file_insertion_enabled':1,
        'raw_enabled':1,
        'writer_name':'html',
        'language_code':'zh_cn',
        'context':context,
        'request':request
    }

    parts = publish_parts(
        rst,
        source_path = path,
        writer=rst2html5.HTML5Writer(),
        settings_overrides = settings
    )
    return parts['body']


def render_sections(site, context, request):
    if context.vpath == '/': return

    html_list = []
    for tab in site.values(True, True):
        class_str = ''
        if context.vpath.startswith(tab.vpath):
            class_str = "active"

        tab_url = tab.url(request)

        html_list.append(
            '<li class="%s"><a href="%s">%s</a></li>'
            % (class_str, tab_url, tab.title)
        )

    return ''.join(html_list)

def zcms_template(func):
    def _func(context, request):
        site = context.get_site()
        if 'X-ZCMS-VHM' in request.headers:
            # 线上运行，多站点支持, support ngix
            path_info = request.environ['PATH_INFO'].split('/', 2)
            if len(path_info) > 2:
                request.environ['HTTP_X_VHM_ROOT'] = '/' + site.__name__
                request.environ['PATH_INFO'] = '/%s' % path_info[2]

        content = func(context, request)
        if type(content) is tuple:  # index page may change context
            context, content = content
        if type(content) is not unicode:
            content = content.decode('utf-8')

        # 根据模版来渲染最终效果
        theme_base = site.metadata.get('theme_base', '')
        kw = {
        'site_title': site.title,
        'site_description': site.metadata.get('description', ''),
        'title': context.title,
        'description': context.metadata.get('description', ''),
        'nav': render_sections(site, context, request),
        'base': context.url(request),
        'content': content,
        'left': context.render_slots('left', request),
        'right': context.render_slots('right', request),
        'upper': context.render_slots('upper', request),
        'theme_base': theme_base,
        }

        theme_default = site.metadata.get('theme', 'default.html')
        theme = context.metadata.get('theme', theme_default)
        if theme_base.startswith('/'):
            theme_base = 'http://127.0.0.1' + theme_base
        template = get_theme_template(theme_base + '/' + theme)
        output = template.substitute(kw).encode('utf8')
        return Response(output, headerlist=[
                ('Content-length', str(len(output))),
                ('Content-type', 'text/html; charset=UTF-8')
	    ])
    return _func

def get_theme_template(theme_url):
    # cache template, TODO refresh cache
    global _templates_cache
    is_debug = get_current_registry().settings.get('pyramid.debug_templates', False)

    if not is_debug and theme_url in _templates_cache:
        return _templates_cache[theme_url]

    if theme_url == '/default.html':
        theme = EMPTY_THEME
    else:
        theme = urllib2.urlopen(theme_url).read()
        text_encoding = chardet.detect(theme)['encoding']
        theme = theme.decode(text_encoding)
    template = Template(theme)
    _templates_cache[theme_url] = template
    return template


########NEW FILE########
__FILENAME__ = views
# -*- encoding: utf-8 -*-

import os
import mimetypes

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render, render_to_response
from pyramid.response import Response

from utils import zcms_template, _templates_cache
from models import Folder, Page, Image, File
import tempfile

@view_config(context=Folder)
@zcms_template
def folder_view(context, request):

    for name in ('index.rst', 'index.md'):
        try:
            index = context[name]
        except KeyError:
            continue
        return index, index.render_html(request)

    items = []
    for obj in context.values(True, True):
        dc = obj.metadata
        if hasattr(obj, '__getitem__'):
            url = obj.__name__ + '/'
        else:
            url = obj.__name__
        items.append({
            'name': obj.__name__,
            'title': dc.get('title', '') or obj.__name__,
            'url': url,
            'description': dc.get('description', '')
        })

    dc = context.metadata

    title = dc.get('title', context.__name__)
    description = dc.get('description', '')

    return render(
        'templates/contents_main.pt',
        dict(
            title=title,
            description=description,
            items=items
        )
    )

@view_config(context=Page)
@zcms_template
def document_view(context, request):
    return context.render_html(request)

@view_config(context=File, name="view.html")
@zcms_template
def file_view(context, request):
    return render(
            'templates/file.pt',
            dict(
                title = context.title,
                description = context.metadata.get('description', ''),
                url = context.__name__
            )
        )

@view_config(context=Image, name="view.html")
@zcms_template
def image_view(context, request):
    dc = context.metadata
    title = dc.get('title', context.__name__)
    description = dc.get('description', '')
    url = context.__name__

    return render(
            'templates/image.pt',
            dict(
                title=title,
                description=description,
                url=url,
            )
        )

@view_config(context=File)
def download_view(context, request):
    response = Response(context.data)
    filename = context.frs.basename(context.vpath)
    mt, encoding = mimetypes.guess_type(filename)
    if isinstance(context, Page):
        response.content_type = 'text/html'         # mt or 'text/plain'
    else:
        response.content_type = mt or 'text/plain'
    return response

@view_config(context=Folder, name="clear_theme_cache")
def clear_theme_cache():
    _templates_cache.clear()

@view_config(context=Folder, name="clear_content_cache")
def clear_content_cache():
    tmp_dir = tempfile.gettempdir() 
    os.system( 'rm -rf %s/zcmscache*' % tmp_dir ) 


########NEW FILE########
