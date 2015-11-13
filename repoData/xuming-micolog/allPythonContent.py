__FILENAME__ = admin
# -*- coding: utf-8 -*-
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
import wsgiref.handlers
from django.conf import settings
settings._target = None
from django.utils import simplejson
from django.utils.translation import ugettext as _
import base
from model import *

from app.pingback import autoPingback
from app.trackback import TrackBack
import xmlrpclib
from xmlrpclib import Fault

class Error404(base.BaseRequestHandler):
    #@printinfo
    def get(self,slug=None):
        self.render2('views/admin/404.html')

class setlanguage(base.BaseRequestHandler):
    def get(self):
        lang_code = self.param('language')
        next = self.param('next')
        if (not next) and os.environ.has_key('HTTP_REFERER'):
            next = os.environ['HTTP_REFERER']
        if not next:
            next = '/'
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        from django.utils.translation import check_for_language, activate
        from django.conf import settings
        settings._target = None

        if lang_code and check_for_language(lang_code):
            g_blog.language=lang_code
            activate(g_blog.language)
            g_blog.save()
        self.redirect(next)

##			if hasattr(request, 'session'):
##				request.session['django_language'] = lang_code
##			else:

##			cookiestr='django_language=%s;expires=%s;domain=%s;path=/'%( lang_code,
##					   (datetime.now()+timedelta(days=100)).strftime("%a, %d-%b-%Y %H:%M:%S GMT"),
##					   ''
##					   )
##			self.write(cookiestr)

##          self.response.headers.add_header('Set-Cookie', cookiestr)

def fetch_result(target_uri):
    for RETRY in range(5):
        try:
            response = urlfetch.fetch(target_uri)
            return response
        except urlfetch.DownloadError:
            logging.info('Download Error, Retry %s times'%RETRY)
            continue
        except:
            raise base.PingbackError(16)
    else:
        logging.info('Times Over')
        raise base.PingbackError(16)


class admin_do_action(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.render2('views/admin/error.html',{'message':_('This operate has not defined!')})
        except:
             self.render2('views/admin/error.html',{'message':_('This operate has not defined!')})


    def post(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.render2('views/admin/error.html',{'message':_('This operate has not defined!')})
        except:
             self.render2('views/admin/error.html',{'message':_('This operate has not defined!')})

    @base.requires_admin
    def action_test(self):
        self.write(os.environ)

    @base.requires_admin
    def action_cacheclear(self):
        memcache.flush_all()
        self.write(_('"Cache cleared successful"'))

    @base.requires_admin
    def action_updatecomments(self):
        for entry in Entry.all():
            cnt=entry.comments().count()
            if cnt<>entry.commentcount:
                entry.commentcount=cnt
                entry.put()
        self.write(_('"All comments updated"'))

    @base.requires_admin
    def action_updatecommentno(self):
        for entry in Entry.all():
            entry.update_commentno()
        self.write(_('"All comments number Updates."'))

    @base.requires_admin
    def action_updatelink(self):
        link_format=self.param('linkfmt')

        if link_format:
            link_format=link_format.strip()
            g_blog.link_format=link_format
            g_blog.save()
            for entry in Entry.all():
                vals={'year':entry.date.year,'month':str(entry.date.month).zfill(2),'day':entry.date.day,
                'postname':entry.slug,'post_id':entry.post_id}

                if entry.slug:
                    newlink=link_format%vals
                else:
                    newlink=g_blog.default_link_format%vals

                if entry.link<>newlink:
                    entry.link=newlink
                    entry.put()
            self.write(_('"Link formated succeed"'))
        else:
            self.write(_('"Please input url format."'))

    @base.requires_admin
    def action_init_blog(self,slug=None):

        for com in Comment.all():
            com.delete()

        for entry in Entry.all():
            entry.delete()

        g_blog.entrycount=0
        self.write(_('"Init has succeed."'))

    @base.requires_admin
    def action_update_tags(self,slug=None):
        for tag in Tag.all():
            tag.delete()
        for entry in Entry.all().filter('entrytype =','post'):
            if entry.tags:
                for t in entry.tags:
                    try:
                        Tag.add(t)
                    except:
                        base.traceback.print_exc()

        self.write(_('"All tags for entry have been updated."'))

    @base.requires_admin
    def action_update_archives(self,slug=None):
        for archive in Archive.all():
            archive.delete()
        entries=Entry.all().filter('entrytype =','post')

        archives={}


        for entry in entries:
            my = entry.date.strftime('%B %Y') # September-2008
            sy = entry.date.strftime('%Y') #2008
            sm = entry.date.strftime('%m') #09
            if archives.has_key(my):
                archive=archives[my]
                archive.entrycount+=1
            else:
                archive = Archive(monthyear=my,year=sy,month=sm,entrycount=1)
                archives[my]=archive

        for ar in archives.values():
            ar.put()

        self.write(_('"All entries have been updated."'))


    def action_trackback_ping(self):
        tbUrl=self.param('tbUrl')
        title=self.param('title')
        excerpt=self.param('excerpt')
        url=self.param('url')
        blog_name=self.param('blog_name')
        tb=TrackBack(tbUrl,title,excerpt,url,blog_name)
        tb.ping()

    def action_pingback_ping(self):
        """Try to notify the server behind `target_uri` that `source_uri`
        points to `target_uri`.  If that fails an `PingbackError` is raised.
        """
        source_uri=self.param('source')
        target_uri=self.param('target')
        try:
            #response =urlfetch.fetch(target_uri)
            response=fetch_result(target_uri) #retry up to 5 times
        except:
            raise base.PingbackError(32)

        try:
            pingback_uri = response.headers['X-Pingback']
        except KeyError:
            _pingback_re = re.compile(r'<link rel="pingback" href="([^"]+)" ?/?>(?i)')
            match = _pingback_re.search(response.content)
            if match is None:
                raise base.PingbackError(33)
            pingback_uri =base.urldecode(match.group(1))

        rpc = xmlrpclib.ServerProxy(pingback_uri)
        try:
            return rpc.pingback.ping(source_uri, target_uri)
        except Fault, e:
            raise base.PingbackError(e.faultCode)
        except:
            raise base.PingbackError(32)




class admin_tools(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current="config"

    @base.requires_admin
    def get(self,slug=None):
        self.render2('views/admin/tools.html')


class admin_sitemap(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current="config"

    @base.requires_admin
    def get(self,slug=None):
        self.render2('views/admin/sitemap.html')


    @base.requires_admin
    def post(self):
        str_options= self.param('str_options').split(',')
        for name in str_options:
            value=self.param(name)
            setattr(g_blog,name,value)

        bool_options= self.param('bool_options').split(',')
        for name in bool_options:
            value=self.param(name)=='on'
            setattr(g_blog,name,value)

        int_options= self.param('int_options').split(',')
        for name in int_options:
            try:
                value=int( self.param(name))
                setattr(g_blog,name,value)
            except:
                pass
        float_options= self.param('float_options').split(',')
        for name in float_options:
            try:
                value=float( self.param(name))
                setattr(g_blog,name,value)
            except:
                pass


        g_blog.save()
        self.render2('views/admin/sitemap.html',{})

class admin_import(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current='config'

    @base.requires_admin
    def get(self,slug=None):
        gblog_init()
        self.render2('views/admin/import.html',{'importitems':
            self.blog.plugins.filter('is_import_plugin',True)})

##	def post(self):
##		try:
##			queue=taskqueue.Queue("import")
##			wpfile=self.param('wpfile')
##			#global imt
##			imt=import_wordpress(wpfile)
##			imt.parse()
##			memcache.set("imt",imt)
##
####			import_data=OptionSet.get_or_insert(key_name="import_data")
####			import_data.name="import_data"
####			import_data.bigvalue=pickle.dumps(imt)
####			import_data.put()
##
##			queue.add(taskqueue.Task( url="/admin/import_next"))
##			self.render2('views/admin/import.html',
##						{'postback':True})
##			return
##			memcache.set("import_info",{'count':len(imt.entries),'msg':'Begin import...','index':1})
##			#self.blog.import_info={'count':len(imt.entries),'msg':'Begin import...','index':1}
##			if imt.categories:
##				queue.add(taskqueue.Task( url="/admin/import_next",params={'cats': pickle.dumps(imt.categories),'index':1}))
##
##			return
##			index=0
##			if imt.entries:
##				for entry in imt.entries :
##					try:
##						index=index+1
##						queue.add(taskqueue.Task(url="/admin/import_next",params={'entry':pickle.dumps(entry),'index':index}))
##					except:
##						pass
##
##		except:
##			self.render2('views/admin/import.html',{'error':'import faiure.'})

class admin_setup(base.BaseRequestHandler):
    def __init__(self):
        self.current='config'

    @base.requires_admin
    def get(self,slug=None):
        vals={'themes':ThemeIterator()}
        self.render2('views/admin/setup.html',vals)

    @base.requires_admin
    def post(self):
        old_theme=g_blog.theme_name
        str_options= self.param('str_options').split(',')
        for name in str_options:
            value=self.param(name)
            setattr(g_blog,name,value)

        bool_options= self.param('bool_options').split(',')
        for name in bool_options:
            value=self.param(name)=='on'
            setattr(g_blog,name,value)

        int_options= self.param('int_options').split(',')
        for name in int_options:
            try:
                value=int( self.param(name))
                setattr(g_blog,name,value)
            except:
                pass
        float_options= self.param('float_options').split(',')
        for name in float_options:
            try:
                value=float( self.param(name))
                setattr(g_blog,name,value)
            except:
                pass


        if old_theme !=g_blog.theme_name:
            g_blog.get_theme()


        g_blog.owner=self.login_user
        g_blog.author=g_blog.owner.nickname()
        g_blog.save()
        gblog_init()
        vals={'themes':ThemeIterator()}
        memcache.flush_all()
        self.render2('views/admin/setup.html',vals)

class admin_entry(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current='write'

    @base.requires_admin
    def get(self,slug='post'):
        action=self.param("action")
        entry=None
        cats=Category.all()
        alltags=Tag.all()
        if action and  action=='edit':
                try:
                    key=self.param('key')
                    entry=Entry.get(key)

                except:
                    pass
        else:
            action='add'

        def mapit(cat):
            return {'name':cat.name,'slug':cat.slug,'select':entry and cat.key() in entry.categorie_keys}

        vals={'action':action,'entry':entry,'entrytype':slug,'cats':map(mapit,cats),'alltags':alltags}
        self.render2('views/admin/entry.html',vals)

    @base.requires_admin
    def post(self,slug='post'):
        action=self.param("action")
        title=self.param("post_title")
        content=self.param('content')
        tags=self.param("tags")
        cats=self.request.get_all('cats')
        key=self.param('key')
        if self.param('publish')!='':
            published=True
        elif self.param('unpublish')!='':
            published=False
        else:
            published=self.param('published')=='True'

        allow_comment=self.parambool('allow_comment')
        allow_trackback=self.parambool('allow_trackback')
        entry_slug=self.param('slug')
        entry_parent=self.paramint('entry_parent')
        menu_order=self.paramint('menu_order')
        entry_excerpt=self.param('excerpt').replace('\n','<br />')
        password=self.param('password')
        sticky=self.parambool('sticky')

        is_external_page=self.parambool('is_external_page')
        target=self.param('target')
        external_page_address=self.param('external_page_address')

        def mapit(cat):
            return {'name':cat.name,'slug':cat.slug,'select':cat.slug in cats}

        vals={'action':action,'postback':True,'cats':Category.all(),'entrytype':slug,
              'cats':map(mapit,Category.all()),
              'entry':{ 'title':title,'content':content,'strtags':tags,'key':key,'published':published,
                         'allow_comment':allow_comment,
                         'allow_trackback':allow_trackback,
                        'slug':entry_slug,
                        'entry_parent':entry_parent,
                        'excerpt':entry_excerpt,
                        'menu_order':menu_order,
                        'is_external_page':is_external_page,
                        'target':target,
                        'external_page_address':external_page_address,
                        'password':password,
                        'sticky':sticky}
              }

        if not (title and (content or (is_external_page and external_page_address))):
            vals.update({'result':False, 'msg':_('Please input title and content.')})
            self.render2('views/admin/entry.html',vals)
        else:
            if action=='add':
                entry= Entry(title=title,content=content)
                entry.settags(tags)
                entry.entrytype=slug
                entry.slug=entry_slug.replace(" ","_")
                entry.entry_parent=entry_parent
                entry.menu_order=menu_order
                entry.excerpt=entry_excerpt
                entry.is_external_page=is_external_page
                entry.target=target
                entry.external_page_address=external_page_address
                newcates=[]
                entry.allow_comment=allow_comment
                entry.allow_trackback=allow_trackback
                entry.author=self.author.user
                entry.author_name=self.author.dispname
                entry.password=password
                entry.sticky=sticky
                if cats:

                    for cate in cats:
                        c=Category.all().filter('slug =',cate)
                        if c:
                            newcates.append(c[0].key())
                entry.categorie_keys=newcates;

                entry.save(published)
                if published:
                    smsg=_('Saved ok. <a href="/%(link)s" target="_blank">View it now!</a>')
                else:
                    smsg=_('Saved ok.')

                vals.update({'action':'edit','result':True,'msg':smsg%{'link':str(entry.link)},'entry':entry})
                self.render2('views/admin/entry.html',vals)
                if published and entry.allow_trackback and g_blog.allow_pingback:
                    try:
                        autoPingback(str(entry.fullurl),HTML=content)
                    except:
                        pass
            elif action=='edit':
                try:
                    entry=Entry.get(key)
                    entry.title=title
                    entry.content=content
                    entry.slug=entry_slug.replace(' ','-')
                    entry.entry_parent=entry_parent
                    entry.menu_order=menu_order
                    entry.excerpt=entry_excerpt
                    entry.is_external_page=is_external_page
                    entry.target=target
                    entry.external_page_address=external_page_address
                    entry.settags(tags)
                    entry.author=self.author.user
                    entry.author_name=self.author.dispname
                    entry.password=password
                    entry.sticky=sticky
                    newcates=[]

                    if cats:

                        for cate in cats:
                            c=Category.all().filter('slug =',cate)
                            if c:
                                newcates.append(c[0].key())
                    entry.categorie_keys=newcates;
                    entry.allow_comment=allow_comment
                    entry.allow_trackback=allow_trackback

                    entry.save(published)

                    if published:
                        smsg=_('Saved ok. <a href="/%(link)s" target="_blank">View it now!</a>')
                    else:
                        smsg=_('Saved ok.')
                    vals.update({'result':True,'msg':smsg%{'link':str(base.urlencode( entry.link))},'entry':entry})

                    self.render2('views/admin/entry.html',vals)
                    if published and entry.allow_trackback and g_blog.allow_pingback:
                        try:
                            autoPingback(entry.fullurl,HTML=content)
                        except:
                            pass

                except:
                    vals.update({'result':False,'msg':_('Error:Entry can''t been saved.')})
                    self.render2('views/admin/entry.html',vals)


class admin_entries(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug='post'):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1




        entries=Entry.all().filter('entrytype =',slug).order('-date')
        entries,links=base.Pager(query=entries,items_per_page=15).fetch(page_index)

        self.render2('views/admin/'+slug+'s.html',
         {
           'current':slug+'s',
           'entries':entries,
           'pager':links
          }
        )

    @base.requires_admin
    def post(self,slug='post'):
        try:
            linkcheck= self.request.get_all('checks')
            for id in linkcheck:
                kid=int(id)

                entry=Entry.get_by_id(kid)

                #delete it's comments
                #entry.delete_comments()

                entry.delete()
                g_blog.entrycount-=1
        finally:

            self.redirect('/admin/entries/'+slug)


class admin_categories(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug=None):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1




        cats=Category.allTops()
        entries,pager=base.Pager(query=cats,items_per_page=15).fetch(page_index)

        self.render2('views/admin/categories.html',
         {
           'current':'categories',
           'cats':cats,
           'pager':pager
          }
        )

    @base.requires_admin
    def post(self,slug=None):
        try:
            linkcheck= self.request.get_all('checks')
            for key in linkcheck:

                cat=Category.get(key)
                if cat:
                    cat.delete()
        finally:
            self.redirect('/admin/categories')

class admin_comments(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug=None):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1



        cq=self.param('cq')
        cv=self.param('cv')
        if cq and cv:
            query=Comment.all().filter(cq+' =',cv).order('-date')
        else:
            query=Comment.all().order('-date')
        comments,pager=base.Pager(query=query,items_per_page=15).fetch(page_index)

        self.render2('views/admin/comments.html',
         {
           'current':'comments',
           'comments':comments,
           'pager':pager,
           'cq':cq,
           'cv':cv
          }
        )

    @base.requires_admin
    def post(self,slug=None):
        try:
            linkcheck= self.request.get_all('checks')
            entrykeys=[]
            for key in linkcheck:

                comment=Comment.get(key)
                comment.delit()
                entrykeys.append(comment.entry.key())
            entrykeys=set(entrykeys)
            for key in entrykeys:
                e=Entry.get(key)
                e.update_commentno()
                e.removecache()
            memcache.delete("/feed/comments")
        finally:
            self.redirect(self.request.uri)

class admin_links(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug=None):
        self.render2('views/admin/links.html',
         {
          'current':'links',
          'links':Link.all().filter('linktype =','blogroll')#.order('-createdate')
          }
        )
    @base.requires_admin
    def post(self):
        linkcheck= self.request.get_all('linkcheck')
        for link_id in linkcheck:
            kid=int(link_id)
            link=Link.get_by_id(kid)
            link.delete()
        self.redirect('/admin/links')

class admin_link(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug=None):
        action=self.param("action")
        vals={'current':'links'}
        if action and  action=='edit':
                try:
                    action_id=int(self.param('id'))
                    link=Link.get_by_id(action_id)
                    vals.update({'link':link})
                except:
                    pass
        else:
            action='add'
        vals.update({'action':action})

        self.render2('views/admin/link.html',vals)

    @base.requires_admin
    def post(self):
        action=self.param("action")
        name=self.param("link_name")
        url=self.param("link_url")
        comment = self.param("link_comment")

        vals={'action':action,'postback':True,'current':'links'}
        if not (name and url):
            vals.update({'result':False,'msg':_('Please input name and url.')})
            self.render2('views/admin/link.html',vals)
        else:
            if action=='add':
               link= Link(linktext=name,href=url,linkcomment=comment)
               link.put()
               vals.update({'result':True,'msg':'Saved ok'})
               self.render2('views/admin/link.html',vals)
            elif action=='edit':
                try:
                    action_id=int(self.param('id'))
                    link=Link.get_by_id(action_id)
                    link.linktext=name
                    link.href=url
                    link.linkcomment = comment
                    link.put()
                    #goto link manage page
                    self.redirect('/admin/links')

                except:
                    vals.update({'result':False,'msg':_('Error:Link can''t been saved.')})
                    self.render2('views/admin/link.html',vals)

class admin_category(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current='categories'

    @base.requires_admin
    def get(self,slug=None):
        action=self.param("action")
        key=self.param('key')
        category=None
        if action and  action=='edit':
                try:

                    category=Category.get(key)

                except:
                    pass
        else:
            action='add'
        vals={'action':action,'category':category,'key':key,'categories':[c for c in Category.all() if not category or c.key()!=category.key()]}
        self.render2('views/admin/category.html',vals)

    @base.requires_admin
    def post(self):
        def check(cate):
            parent=cate.parent_cat
            skey=cate.key()
            while parent:
                if parent.key()==skey:
                    return False
                parent=parent.parent_cat
            return True

        action=self.param("action")
        name=self.param("name")
        slug=self.param("slug")
        parentkey=self.param('parentkey')
        key=self.param('key')


        vals={'action':action,'postback':True}

        try:

                if action=='add':
                    cat= Category(name=name,slug=slug)
                    if not (name and slug):
                        raise Exception(_('Please input name and slug.'))
                    if parentkey:
                        cat.parent_cat=Category.get(parentkey)

                    cat.put()
                    self.redirect('/admin/categories')

                    #vals.update({'result':True,'msg':_('Saved ok')})
                    #self.render2('views/admin/category.html',vals)
                elif action=='edit':

                        cat=Category.get(key)
                        cat.name=name
                        cat.slug=slug
                        if not (name and slug):
                            raise Exception(_('Please input name and slug.'))
                        if parentkey:
                            cat.parent_cat=Category.get(parentkey)
                            if not check(cat):
                                raise Exception(_('A circle declaration found.'))
                        else:
                            cat.parent_cat=None
                        cat.put()
                        self.redirect('/admin/categories')

        except Exception ,e :
            if cat.is_saved():
                cates=[c for c in Category.all() if c.key()!=cat.key()]
            else:
                cates= Category.all()

            vals.update({'result':False,'msg':e.message,'category':cat,'key':key,'categories':cates})
            self.render2('views/admin/category.html',vals)

class admin_status(base.BaseRequestHandler):
    @base.requires_admin
    def get(self):
        self.render2('views/admin/status.html',{'cache':memcache.get_stats(),'current':'status','environ':os.environ})
class admin_authors(base.BaseRequestHandler):
    @base.requires_admin
    def get(self):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1




        authors=User.all().filter('isAuthor =',True)
        entries,pager=base.Pager(query=authors,items_per_page=15).fetch(page_index)

        self.render2('views/admin/authors.html',
         {
           'current':'authors',
           'authors':authors,
           'pager':pager
          }
        )


    @base.requires_admin
    def post(self,slug=None):
        try:
            linkcheck= self.request.get_all('checks')
            for key in linkcheck:

                author=User.get(key)
                author.delete()
        finally:
            self.redirect('/admin/authors')

class admin_author(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current='authors'

    @base.requires_admin
    def get(self,slug=None):
        action=self.param("action")
        author=None
        if action and  action=='edit':
                try:
                    key=self.param('key')
                    author=User.get(key)

                except:
                    pass
        else:
            action='add'
        vals={'action':action,'author':author}
        self.render2('views/admin/author.html',vals)

    @base.requires_admin
    def post(self):
        action=self.param("action")
        name=self.param("name")
        slug=self.param("email")

        vals={'action':action,'postback':True}
        if not (name and slug):
            vals.update({'result':False,'msg':_('Please input dispname and email.')})
            self.render2('views/admin/author.html',vals)
        else:
            if action=='add':
               author= User(dispname=name,email=slug	)
               author.user=db.users.User(slug)
               author.put()
               vals.update({'result':True,'msg':'Saved ok'})
               self.render2('views/admin/author.html',vals)
            elif action=='edit':
                try:
                    key=self.param('key')
                    author=User.get(key)
                    author.dispname=name
                    author.email=slug
                    author.user=db.users.User(slug)
                    author.put()
                    if author.isadmin:
                        g_blog.author=name
                    self.redirect('/admin/authors')

                except:
                    vals.update({'result':False,'msg':_('Error:Author can''t been saved.')})
                    self.render2('views/admin/author.html',vals)

class admin_plugins(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current='plugins'

    @base.requires_admin
    def get(self,slug=None):
        vals={'plugins':self.blog.plugins}
        self.render2('views/admin/plugins.html',vals)

    @base.requires_admin
    def post(self):
        action=self.param("action")
        name=self.param("plugin")
        ret=self.param("return")
        self.blog.plugins.activate(name,action=="activate")
        if ret:
            self.redirect(ret)
        else:
            vals={'plugins':self.blog.plugins}
            self.render2('views/admin/plugins.html',vals)

class admin_plugins_action(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current='plugins'

    @base.requires_admin
    def get(self,slug=None):
        plugin=self.blog.plugins.getPluginByName(slug)
        if not plugin :
            self.error(404)
            return
        plugins=self.blog.plugins.filter('active',True)
        if not plugin.active:
            pcontent=_('''<div>Plugin '%(name)s' havn't actived!</div><br><form method="post" action="/admin/plugins?action=activate&amp;plugin=%(iname)s&amp;return=/admin/plugins/%(iname)s"><input type="submit" value="Activate Now"/></form>''')%{'name':plugin.name,'iname':plugin.iname}
            plugins.insert(0,plugin)
        else:
            pcontent=plugin.get(self)


        vals={'plugins':plugins,
              'plugin':plugin,
              'pcontent':pcontent}

        self.render2('views/admin/plugin_action.html',vals)

    @base.requires_admin
    def post(self,slug=None):

        plugin=self.blog.plugins.getPluginByName(slug)
        if not plugin :
            self.error(404)
            return
        plugins=self.blog.plugins.filter('active',True)
        if not plugin.active:
            pcontent=_('''<div>Plugin '%(name)s' havn't actived!</div><br><form method="post" action="/admin/plugins?action=activate&amp;plugin=%(iname)s&amp;return=/admin/plugins/%(iname)s"><input type="submit" value="Activate Now"/></form>''')%{'name':plugin.name,'iname':plugin.iname}
            plugins.insert(0,plugin)
        else:
            pcontent=plugin.post(self)


        vals={'plugins':plugins,
              'plugin':plugin,
              'pcontent':pcontent}

        self.render2('views/admin/plugin_action.html',vals)

class WpHandler(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,tags=None):
        try:
            all=self.param('all')
        except:
            all=False

        if(all):
            entries = Entry.all().order('-date')
            filename='micolog.%s.xml'%datetime.now().strftime('%Y-%m-%d')
        else:
            str_date_begin=self.param('date_begin')
            str_date_end=self.param('date_end')
            try:
                date_begin=datetime.strptime(str_date_begin,"%Y-%m-%d")
                date_end=datetime.strptime(str_date_end,"%Y-%m-%d")
                entries = Entry.all().filter('date >=',date_begin).filter('date <',date_end).order('-date')
                filename='micolog.%s.%s.xml'%(str(str_date_begin),str(str_date_end))
            except:
                self.render2('views/admin/404.html')
                return

        cates=Category.all()
        tags=Tag.all()

        self.response.headers['Content-Type'] = 'binary/octet-stream'#'application/atom+xml'
        self.response.headers['Content-Disposition'] = 'attachment; filename=%s'%filename
        self.render2('views/wordpress.xml',{'entries':entries,'cates':cates,'tags':tags})

class Upload(base.BaseRequestHandler):
    @base.requires_admin
    def post(self):
        name = self.param('filename')
        mtype = self.param('fileext')
        bits = self.param('upfile')
        Media(name = name, mtype = mtype, bits = bits).put()

        self.redirect('/admin/filemanager')

class UploadEx(base.BaseRequestHandler):
    @base.requires_admin
    def get(self):
        extstr=self.param('ext')
        ext=extstr.split('|')
        files=Media.all()
        if extstr!='*':
            files=files.filter('mtype IN',ext)
        self.render2('views/admin/upload.html',{'ext':extstr,'files':files})

    @base.requires_admin
    def post(self):
        ufile=self.request.params['userfile']
        #if ufile:
        name=ufile.filename
        mtype =os.path.splitext(name)[1][1:]
        bits = self.param('userfile')
        media=Media(name = name, mtype = mtype, bits = bits)
        media.put()
        self.write(simplejson.dumps({'name':media.name,'size':media.size,'id':str(media.key())}))

class FileManager(base.BaseRequestHandler):
    def __init__(self):
        base.BaseRequestHandler.__init__(self)
        self.current = 'files'

    @base.requires_admin
    def get(self):
        try:
            page_index=int(self.param('page'))
        except:
            page_index=1
        files = Media.all().order('-date')
        files,links=base.Pager(query=files,items_per_page=15).fetch(page_index)
        self.render2('views/admin/filemanager.html',{'files' : files,'pager':links})

    @base.requires_admin
    def post(self): # delete files
        delids = self.request.POST.getall('del')
        if delids:
            for id in delids:
                file = Media.get_by_id(int(id))
                file.delete()

        self.redirect('/admin/filemanager')

class admin_main(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug=None):
        if self.is_admin:
            self.redirect('/admin/setup')
        else:
            self.redirect('/admin/entries/post')

class admin_ThemeEdit(base.BaseRequestHandler):
    @base.requires_admin
    def get(self,slug):
        zfile=zipfile.ZipFile(os.path.join(rootpath,"themes",slug+".zip"))
        newfile=zipfile.ZipFile('')
        for item  in zfile.infolist():
            self.write(item.filename+"<br>")


def main():
    base.webapp.template.register_template_library('app.filter')
    base.webapp.template.register_template_library('app.recurse')

    application = base.webapp.WSGIApplication(
                    [
                    ('/admin/{0,1}',admin_main),
                    ('/admin/setup',admin_setup),
                    ('/admin/entries/(post|page)',admin_entries),
                    ('/admin/links',admin_links),
                    ('/admin/categories',admin_categories),
                    ('/admin/comments',admin_comments),
                    ('/admin/link',admin_link),
                    ('/admin/category',admin_category),
                     ('/admin/(post|page)',admin_entry),
                     ('/admin/status',admin_status),
                     ('/admin/authors',admin_authors),
                     ('/admin/author',admin_author),
                     ('/admin/import',admin_import),
                     ('/admin/tools',admin_tools),
                     ('/admin/plugins',admin_plugins),
                     ('/admin/plugins/(\w+)',admin_plugins_action),
                     ('/admin/sitemap',admin_sitemap),
                     ('/admin/export/micolog.xml',WpHandler),
                     ('/admin/do/(\w+)',admin_do_action),
                     ('/admin/lang',setlanguage),
                     ('/admin/theme/edit/(\w+)',admin_ThemeEdit),
                     ('/admin/upload', Upload),
                     ('/admin/filemanager', FileManager),
                     ('/admin/uploadex', UploadEx),
                     ('.*',Error404),
                     ],debug=True)
    g_blog.application=application
    g_blog.plugins.register_handlerlist(application)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = api_rpc
# -*- coding: utf-8 -*-
import cgi,os,sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
import wsgiref.handlers
import xmlrpclib
from xmlrpclib import Fault
from datetime import timedelta
#from datetime import datetime
from SimpleXMLRPCServer import SimpleXMLRPCDispatcher
from django.utils.html import strip_tags
sys.path.append('modules')
from base import *
from model import *
from micolog_plugin import *

MAX_NUM=100

def checkauth(pos=1):
    def _decorate(method):
        def _wrapper(*args, **kwargs):

            username = args[pos+0]
            password = args[pos+1]

            if not (username and password and g_blog.rpcuser and g_blog.rpcpassword
                    and (g_blog.rpcuser==username)
                    and (g_blog.rpcpassword==password)):
                 raise ValueError("Authentication Failure")
            args = args[0:pos]+args[pos+2:]
            return method(*args, **kwargs)

        return _wrapper
    return _decorate

def format_date(d):
    if not d: return None
    #return xmlrpclib.DateTime(d.isoformat())
    return xmlrpclib.DateTime(d)
def dateformat(creatdate):
    try:
        dt=datetime.strptime(creatdate, "%Y%m%dT%H:%M:%S")
    except:
        dt=datetime.strptime(creatdate, "%Y%m%dT%H:%M:%SZ")
    return dt

def post_struct(entry):
    if not entry:
         raise Fault(404, "Post does not exist")
    categories=[]
    if entry.categorie_keys:
        categories =[cate.name for cate in  entry.categories]


    struct = {
        'postid': str(entry.key().id()),
        'title': entry.title,
        'link': entry.fullurl,
        'permaLink': entry.fullurl,
        'description': unicode(entry.content),
        'categories': categories,
        'userid': '1',
        'mt_keywords':','.join(entry.tags),
        'mt_excerpt': '',
        'mt_text_more': '',
        'mt_allow_comments': entry.allow_comment and 1 or 0,
        'mt_allow_pings': entry.allow_trackback and 1 or 0,
        'custom_fields':[],
        'post_status':entry.post_status,
        'sticky':entry.sticky,
        'wp_author_display_name': entry.get_author_user().dispname,
        'wp_author_id': str(entry.get_author_user().key().id()),
        'wp_password': entry.password,
        'wp_slug':entry.slug
        }
    if entry.date:
        t=timedelta(seconds=3600*g_blog.timedelta)
        struct['dateCreated'] = format_date(entry.date+t)
        struct['date_created_gmt'] = format_date(entry.date)

    return struct

def page_struct(entry):
    if not entry:
         raise Fault(404, "Post does not exist")
    categories=[]
    if entry.categorie_keys:
        categories =[cate.name for cate in  entry.categories]


    struct = {
        'page_id': str(entry.key().id()),
        'title': entry.title,
        'link': entry.fullurl,
        'permaLink': entry.fullurl,
        'description': unicode(entry.content),
        'categories': categories,
        'userid': '1',
        'mt_allow_comments': entry.allow_comment and 1 or 0,
        'mt_allow_pings': entry.allow_trackback and 1 or 0,
        'custom_fields':[],
        'page_status':entry.post_status,
        'sticky':entry.sticky,
        'wp_author_display_name': entry.get_author_user().dispname,
        'wp_author_id': str(entry.get_author_user().key().id()),
        'wp_password': entry.password,
        'wp_slug':entry.slug,
        'text_more': '',
        'wp_author': 'admin',
        'wp_page_order': entry.menu_order,
        'wp_page_parent_id': 0,
        'wp_page_parent_title': '',
        'wp_page_template': 'default',
        }
    if entry.date:
        struct['dateCreated'] = format_date(entry.date)
        struct['date_created_gmt'] = format_date(entry.date)

    return struct

def entry_title_struct(entry):
    if not entry:
         raise Fault(404, "Post does not exist")
    struct = {
        'postid': str(entry.key().id()),
        'title': entry.title,
        'userid': '1',
        }
    if entry.date:
        struct['dateCreated'] = format_date(entry.date)
    return struct

class Logger(db.Model):
    request = db.TextProperty()
    response = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)


#-------------------------------------------------------------------------------
# blogger
#-------------------------------------------------------------------------------

@checkauth()
def blogger_getUsersBlogs(discard):
    return [{'url' : g_blog.baseurl, 'blogid' : '1','isAdmin':True, 'blogName' : g_blog.title,'xmlrpc':g_blog.baseurl+"/rpc"}]

@checkauth(pos=2)
def blogger_deletePost(appkey, postid, publish=False):
    post=Entry.get_by_id(int(postid))
    post.delete()
    return True

@checkauth()
def blogger_getUserInfo(appkey):
    for user in User.all():
        if user.isadmin:
            return {'email':user.email,'firstname':'','nickname':user.dispname,'userid':str(user.key().id()),
           'url':'','lastname':''}
    return None

#-------------------------------------------------------------------------------
# metaWeblog
#-------------------------------------------------------------------------------

@checkauth()
def metaWeblog_newPost(blogid, struct, publish):
    if struct.has_key('categories'):
        cates = struct['categories']
    else:
        cates = []

    newcates=[]
    for cate in cates:
      c=Category.all().filter('name =',cate)
      if c:
          newcates.append(c[0].key())
    entry=Entry(title = struct['title'],
            content = struct['description'],
            categorie_keys=newcates
     )

    if struct.has_key('mt_text_more'):
        content=struct['mt_text_more']
        if content:
            entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
    if struct.has_key('mt_keywords'):
        entry.settags(struct['mt_keywords'])

    if struct.has_key('wp_slug'):
        entry.slug=struct['wp_slug']

    if struct.has_key('mt_excerpt'):
        entry.excerpt=struct['mt_excerpt']

    try:
        if struct.has_key('date_created_gmt'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
            dt=str(struct['date_created_gmt'])
            entry.date=dateformat(dt)
        elif struct.has_key('dateCreated'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
            dt=str(struct['dateCreated'])
            entry.date=dateformat(dt)-timedelta(seconds=3600*g_blog.timedelta)
    except:
        pass

    if struct.has_key('wp_password'):
        entry.password=struct['wp_password']

    if struct.has_key('sticky'):
        entry.sticky=struct['sticky']


    if struct.has_key('wp_author_id'):
        author=User.get_by_id(int(struct['wp_author_id']))
        entry.author=author.user
        entry.author_name=author.dispname
    else:
        entry.author=g_blog.owner
        entry.author_name=g_blog.author

    if publish:
        entry.save(True)

        if struct.has_key('mt_tb_ping_urls'):
            links=struct['mt_tb_ping_urls'].split(' ')
            for url in links:
                util.do_trackback(url,entry.title,entry.get_content_excerpt(more='')[:60],entry.fullurl,g_blog.title)
        g_blog.tigger_action("xmlrpc_publish_post",entry)
    else:
        entry.save()
    postid =entry.key().id()
    return str(postid)

@checkauth()
def metaWeblog_newMediaObject(blogid,struct):
    name=struct['name']

    if struct.has_key('type'):
        mtype=struct['type']
    else:
        st=name.split('.')
        if len(st)>1:
            mtype=st[-1]
        else:
            mtype=None
    bits=db.Blob(str(struct['bits']))
    media=Media(name=name,mtype=mtype,bits=bits)
    media.put()

    return {'url':g_blog.baseurl+'/media/'+str(media.key())}

@checkauth()
def metaWeblog_editPost(postid, struct, publish):
    if struct.has_key('categories'):
        cates = struct['categories']
    else:
        cates = []
    newcates=[]
    for cate in cates:
      c=Category.all().filter('name =',cate).fetch(1)
      if c:
          newcates.append(c[0].key())
    entry=Entry.get_by_id(int(postid))


    if struct.has_key('mt_keywords'):
       entry.settags(struct['mt_keywords'])

    if struct.has_key('wp_slug'):
        entry.slug=struct['wp_slug']
    if struct.has_key('mt_excerpt'):
        entry.excerpt=struct['mt_excerpt']

    try:
        if struct.has_key('date_created_gmt'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
            dt=str(struct['date_created_gmt'])
            entry.date=dateformat(dt)
        elif struct.has_key('dateCreated'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
            dt=str(struct['dateCreated'])
            entry.date=dateformat(dt)-timedelta(seconds=3600*g_blog.timedelta)
    except:
        pass

    if struct.has_key('wp_password'):
        entry.password=struct['wp_password']

    if struct.has_key('sticky'):
        entry.sticky=struct['sticky']

    if struct.has_key('wp_author_id'):
        author=User.get_by_id(int(struct['wp_author_id']))
        entry.author=author.user
        entry.author_name=author.dispname
    else:
        entry.author=g_blog.owner
        entry.author_name=g_blog.author

    entry.title = struct['title']
    entry.content = struct['description']
    if struct.has_key('mt_text_more'):
        content=struct['mt_text_more']
        if content:
            entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
    entry.categorie_keys=newcates
    if publish:
        entry.save(True)
    else:
        entry.save()

    return True


@checkauth()
def metaWeblog_getCategories(blogid):
    categories =Category.all()
    cates=[]
    for cate in categories:
        cates.append({  'categoryDescription':'',
                        'categoryId' : str(cate.ID()),
                        'parentId':'0',
                        'description':cate.name,
                        'categoryName':cate.name,
                        'htmlUrl':'',
                        'rssUrl':''
                        })
    return cates

@checkauth()
def metaWeblog_getPost(postid):
    entry = Entry.get_by_id(int(postid))
    return post_struct(entry)

@checkauth()
def metaWeblog_getRecentPosts(blogid, num=20):
    entries = Entry.all().filter('entrytype =','post').order('-date').fetch(min(num, MAX_NUM))
    return [post_struct(entry) for entry in entries]



#-------------------------------------------------------------------------------
#  WordPress API
#-------------------------------------------------------------------------------
@checkauth(pos=0)
def wp_getUsersBlogs():
    #return [{'url' : g_blog.baseurl, 'blog_id' : 1,'is_admin':True, 'blog_name' : g_blog.title,'xmlrpc_url':g_blog.baseurl+"/xmlrpc.php"}]
    return [{'url' : g_blog.baseurl, 'blogid' : '1','isAdmin':True, 'blogName' : g_blog.title,'xmlrpc':g_blog.baseurl+"/rpc"}]

@checkauth()
def wp_getTags(blog_id):
    def func(blog_id):
        for tag in Tag.all():
            yield {'tag_ID':'0','name':tag.tag,'count':str(tag.tagcount),'slug':tag.tag,'html_url':'','rss_url':''}
    return list(func(blog_id))

@checkauth()
def wp_getCommentCount(blog_id,postid):
    entry = Entry.get_by_id(postid)
    if entry:
        return {'approved':entry.commentcount,'awaiting_moderation':0,'spam':0,'total_comments':entry.commentcount}

@checkauth()
def wp_getPostStatusList(blogid):
    return {'draft': 'Draft',
            'pending': 'Pending Review',
            'private': 'Private',
            'publish': 'Published'}

@checkauth()
def wp_getPageStatusList(blogid):
    return {'draft': 'Draft', 'private': 'Private', 'publish': 'Published'}

@checkauth()
def wp_getPageTemplates(blogid):
    return {}

@checkauth()
def wp_setOptions(blogid,options):
    for name,value in options,options.values():
        if hasattr(g_blog,name):
            setattr(g_blog,name,value)
    return options

@checkauth()
def wp_getOptions(blogid,options):
    #todo:Options is None ,return all attrbutes
    mdict={}
    if options:
        for option in options:
            if hasattr(g_blog,option):
                mdict[option]={'desc':option,
                                'readonly:':False,
                                'value':getattr(g_blog,option)}
    return mdict

@checkauth()
def wp_newCategory(blogid,struct):
    name=struct['name']

    category=Category.all().filter('name =',name).fetch(1)
    if category and len(category):
        return category[0].ID()
    else:
        #category=Category(key_name=urlencode(name), name=name,slug=urlencode(name))
        category=Category(name=name,slug=name)
        category.put()
        return category.ID()


@checkauth()
def wp_newPage(blogid,struct,publish):

        entry=Entry(title = struct['title'],
                content = struct['description'],
                )
        if struct.has_key('mt_text_more'):
            entry.content=entry.content+"<!--more-->"+struct['mt_text_more']

        try:
            if struct.has_key('date_created_gmt'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
                dt=str(struct['date_created_gmt'])
                entry.date=dateformat(dt)
            elif struct.has_key('dateCreated'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
                dt=str(struct['dateCreated'])
                entry.date=dateformat(dt)-timedelta(seconds=3600*g_blog.timedelta)
        except:
            pass

        if struct.has_key('wp_slug'):
            entry.slug=struct['wp_slug']
        if struct.has_key('wp_page_order'):
            entry.menu_order=int(struct['wp_page_order'])
        if struct.has_key('wp_password'):
            entry.password=struct['wp_password']

        if struct.has_key('wp_author_id'):
            author=User.get_by_id(int(struct['wp_author_id']))
            entry.author=author.user
            entry.author_name=author.dispname
        else:
            entry.author=g_blog.owner
            entry.author_name=g_blog.author

        entry.entrytype='page'
        if publish:
            entry.save(True)
        else:
            entry.save()

        postid =entry.key().id()
        return str(postid)


@checkauth(2)
def wp_getPage(blogid,pageid):
    entry = Entry.get_by_id(int(pageid))
    return page_struct(entry)

@checkauth()
def wp_getPages(blogid,num=20):
    entries = Entry.all().filter('entrytype =','page').order('-date').fetch(min(num, MAX_NUM))
    return [page_struct(entry) for entry in entries]

@checkauth(2)
def wp_editPage(blogid,pageid,struct,publish):

    entry=Entry.get_by_id(int(pageid))

    ##		if struct.has_key('mt_keywords'):
    ##			entry.tags=struct['mt_keywords'].split(',')

    if struct.has_key('wp_slug'):
        entry.slug=struct['wp_slug']

    if struct.has_key('wp_page_order'):
        entry.menu_order=int(struct['wp_page_order'])
    try:
        if struct.has_key('date_created_gmt'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
            dt=str(struct['date_created_gmt'])
            entry.date=dateformat(dt)
        elif struct.has_key('dateCreated'): #Â¶ÇÊûúÊúâÊó•ÊúüÂ±ûÊÄß
            dt=str(struct['dateCreated'])
            entry.date=dateformat(dt)-timedelta(seconds=3600*g_blog.timedelta)
    except:
        pass

    if struct.has_key('wp_password'):
        entry.password=struct['wp_password']
    if struct.has_key('wp_author_id'):
        author=User.get_by_id(int(struct['wp_author_id']))
        entry.author=author.user
        entry.author_name=author.dispname
    else:
        entry.author=g_blog.owner
        entry.author_name=g_blog.author
    entry.title = struct['title']
    entry.content = struct['description']
    if struct.has_key('mt_text_more'):
        entry.content=entry.content+"<!--more-->"+struct['mt_text_more']
    entry.save(True)

    return True


@checkauth()
def wp_deletePage(blogid,pageid):
    post=Entry.get_by_id(int(pageid))
    post.delete()
    return True

@checkauth()
def wp_getAuthors(blogid):
    ulist=[]
    i=1
    for user in User.all():
        ulist.append({'user_id':str(user.key().id()),'user_login':'admin','display_name':user.dispname})
        i += 1
    return ulist

@checkauth()
def wp_deleteComment(blogid,commentid):
    try:
        comment=Comment.get_by_id(int(commentid))
        if comment:
            comment.delit()
        return True

    except:
        return False

@checkauth()
def wp_editComment(blogid,commentid,struct):
    try:
        comment=Comment.get_by_id(int(commentid))
        if comment:
            url=struct['author_url']
            if url:
                try:
                    comment.weburl=url
                except:
                    comment.weburl=None
            #comment.date= format_date(datetime.now())
            comment.author=struct['author']
            #comment.weburl=struct['author_url']
            comment.email=struct['author_email']
            comment.content=struct['content']
            #comment.status=struct['status']
            comment.save()
            return True
    except:
        raise
        return False

@checkauth()
def wp_newComment(blogid,postid,struct):
    post=Entry.get_by_id(postid)
    if not post:
        raise Fault(404, "Post does not exist")
    comment=Comment(entry=post,content=struct['content'],
                    author=struct['author'],
                    email=struct['author_email'])
    url=struct['author_url']
    if url:
        try:
            comment.weburl=url
        except:
            comment.weburl=None

    comment.save()
    return comment.key().id()

@checkauth()
def wp_getCommentStatusList(blogid):
    return {'hold':0,'approve':Comment.all().count(),'spam':0}

@checkauth()
def wp_getPageList(blogid,num=20):
    def func(blogid):
        entries = Entry.all().filter('entrytype =','page').order('-date').fetch(min(num, MAX_NUM))
        for entry in entries:
            yield {'page_id':str(entry.key().id()),'page_title':entry.title,'page_parent_id':0,'dateCreated': format_date(entry.date),'date_created_gmt': format_date(entry.date)}
    return list(func(blogid))

@checkauth()
def wp_deleteCategory(blogid,cateid):
    try:
        cate=Category.get_from_id(int(cateid))
        cate.delete()
        return True
    except:
        return False
@checkauth()
def wp_suggestCategories(blogid,category,max_result):
    categories=Category.all()
    cates=[]
    for cate in categories:
        cates.append({  'categoryId' : str(cate.ID()),
                    'categoryName':cate.name
                    })
    return cates[:max_result]

@checkauth()
def wp_getComment(blogid,commentid):
    comment=Comment.get_by_id(int(commentid))
    return {
                    'dateCreated':format_date(comment.date),
                            'date_created_gmt':format_date(comment.date),
                            'user_id':'0',
                            'comment_id':str(comment.key().id()),
                            'parent':'',
                            'status':'approve',
                            'content':unicode(comment.content),
                            'link':comment.entry.link+"#comment-"+str(comment.key().id()),
                            'post_id':str(comment.entry.key().id()),
                            'post_title':comment.entry.title,
                            'author':comment.author,
                            'author_url':str(comment.weburl),
                            'author_email':str(comment.email),
                            'author_ip':comment.ip,
                            'type':''
            }

@checkauth()
def wp_getComments(blogid,data):
    def func(blogid,data):
        number=int(data['number'])
        try:
            offset=int(data['offset'])
        except:
            offset=0

        comments=[]

        if data['post_id']:
            postid=int(data['post_id'])
            post=Entry.get_by_id(postid)
            if post:
                comments=post.comments()
        else:
            comments=Comment.all()

        for comment in comments.fetch(number,offset):
            yield {
                        'dateCreated':format_date(comment.date),
                        'date_created_gmt':format_date(comment.date),
                        'user_id':'0',
                        'comment_id':str(comment.key().id()),
                        'parent':'',
                        'status':'approve',
                        'content':unicode(comment.content),
                        'link':comment.entry.link+"#comment-"+str(comment.key().id()),
                        'post_id':str(comment.entry.key().id()),
                        'post_title':comment.entry.title,
                        'author':comment.author,
                        'author_url':str(comment.weburl),
                        'author_email':str(comment.email),
                        'author_ip':comment.ip,
                        'type':''
                    }
    return list(func(blogid,data))


@checkauth()
def mt_getPostCategories(postid):
    post=Entry.get_by_id(int(postid))
    categories=post.categories
    cates=[]
    for cate in categories:
        #cate=Category(key)
        cates.append({'categoryId' : str(cate.ID()),
                    'categoryName':cate.name,
                    'isPrimary':True
                    })
    return cates

@checkauth()
def mt_getCategoryList(blogid):
    categories=Category.all()
    cates=[]
    for cate in categories:
            cates.append({  'categoryId' : str(cate.ID()),
                    'categoryName':cate.name
                    })
    return cates

@checkauth()
def mt_setPostCategories(postid,cates):
    try:
        entry=Entry.get_by_id(int(postid))
        newcates=[]

        for cate in cates:
            if cate.has_key('categoryId'):
                id=int(cate['categoryId'])
                c=Category.get_from_id(int(cate['categoryId']))
                if c:
                    newcates.append(c.key())
        entry.categorie_keys=newcates
        entry.put()
        return True
    except:
        return False

@checkauth()
def mt_getTrackbackPings(self,postid):
    try:
        entry=Entry.get_by_id(int(postid))
        Tracks=[]
        list=Comment.all().filter('entry =',entry).filter('ctype =',1)

        for track in list:
            Tracks.append({'pingIP':track.ip,'pingURL':track.weburl,'pingTitle':track.author})
        return Tracks
    except:
        return False

@checkauth()
def mt_publishPost(postid):
    try:
        entry=Entry.get_by_id(int(postid))
        entry.save(True)
        return entry.key().id()
    except:
        return 0

@checkauth()
def mt_getRecentPostTitles(blogid,num):
    entries = Entry.all().filter('entrytype =','post').order('-date').fetch(min(num, MAX_NUM))
    return [entry_title_struct(entry) for entry in entries]

#------------------------------------------------------------------------------
#pingback
#------------------------------------------------------------------------------
def pingback_extensions_getPingbacks(self,url):
    from urlparse import urlparse
    param=urlparse(url)
    slug=param[2]
    slug=urldecode(slug)
    try:
        entry = Entry.all().filter("published =", True).filter('link =', slug).fetch(1)
        pings=[]
        list=Comment.all().filter('entry =',entry).filter('ctype =',2)

        for ping in list:
            pings.append(ping.weburl)
        return pings
    except:
        return False
_title_re = re.compile(r'<title>(.*?)</title>(?i)')
_pingback_re = re.compile(r'<link rel="pingback" href="([^"]+)" ?/?>(?i)')
_chunk_re = re.compile(r'\n\n|<(?:p|div|h\d)[^>]*>')

def fetch_result(source_uri):
    for RETRY in range(5):
        rpc = urlfetch.create_rpc()
        urlfetch.make_fetch_call(rpc, source_uri)
        try:
            response = rpc.get_result()
            return response
        except urlfetch.DownloadError:
            logging.info('Download Error, Retry %s times'%RETRY)
            continue
        except:
            raise Fault(16, 'The source URL does not exist.%s'%source_uri)
    else:
        logging.info('Times Over')
        raise Fault(16, 'The source URL does not exist.%s'%source_uri)

def pingback_ping(source_uri, target_uri):
    # next we check if the source URL does indeed exist
    if not g_blog.allow_pingback:
        raise Fault(49,"Access denied.")
    try:

        g_blog.tigger_action("pre_ping",source_uri,target_uri)
        response = fetch_result(source_uri)
        logging.info('source_uri: '+source_uri+' target_uri:'+target_uri)
    except Exception ,e :
        #logging.info(e.message)
        logging.info('The source URL does not exist.%s'%source_uri)
        raise Fault(16, 'The source URL does not exist.%s'%source_uri)
    # we only accept pingbacks for links below our blog URL
    blog_url = g_blog.baseurl
    if not blog_url.endswith('/'):
        blog_url += '/'
    if not target_uri.startswith(blog_url):
        raise Fault(32, 'The specified target URL does not exist.')
    path_info = target_uri[len(blog_url):]
    if path_info.startswith('?'):
        try: postid = path_info.split('&')[0].split('=')[1]
        except: postid=None
        pingback_post(response,source_uri,target_uri,postid=postid)
    else:
        path = path_info.split('?')[0]
        pingback_post(response,source_uri,target_uri,slug=path)

    #pingback_post(response,source_uri,target_uri,path_info)
    try:
        logging.info('Micolog pingback succeed!')
        return "Micolog pingback succeed!"
    except:
        raise Fault(49,"Access denied.")


def get_excerpt(response, url_hint, body_limit=1024 * 512):
    """Get an excerpt from the given `response`.  `url_hint` is the URL
    which will be used as anchor for the excerpt.  The return value is a
    tuple in the form ``(title, body)``.  If one of the two items could
    not be calculated it will be `None`.
    """
    contents = response.content[:body_limit]
    if 'charset=gb2312' in contents[:400].lower():
        contents = contents.decode('gb2312').encode('UTF-8')
    elif 'charset=gbk"' in contents[:400].lower():
        contents = contents.decode('GBK').encode('UTF-8')
    elif 'charset=big5' in contents[:400].lower():
        contents = contents.decode('big5')
    try:
        contents=contents.decode('utf-8')
    except:
        pass

    title_match = _title_re.search(contents)
    title = title_match and strip_tags(title_match.group(1)) or None

    link_re = re.compile(r'<a[^>]+?"\s*%s\s*"[^>]*>(.*?)</a>(?is)' %
                         re.escape(url_hint))
    for chunk in _chunk_re.split(contents):
        match = link_re.search(chunk)
        if not match:
            continue
        before = chunk[:match.start()]
        after = chunk[match.end():]
        raw_body = '%s\0%s' % (strip_tags(before).replace('\0', ''),
                               strip_tags(after).replace('\0', ''))
        raw_body=raw_body.replace('\n', '').replace('\t', '')
        body_match = re.compile(r'(?:^|\b)(.{0,120})\0(.{0,120})(?:\b|$)') \
                       .search(raw_body)
        if body_match:
            break
    else:
        return title, None


    before, after = body_match.groups()
    link_text = strip_tags(match.group(1))
    if len(link_text) > 60:
        link_text = link_text[:60] + u' ‚Ä¶'

    bits = before.split()
    bits.append(link_text)
    bits.extend(after.split())
    return title, u'[‚Ä¶] %s [‚Ä¶]' % u' '.join(bits)

def pingback_post(response,source_uri, target_uri, slug=None, postid=None):
    """This is the pingback handler for posts."""
    if slug:
        entry = Entry.all().filter("published =", True).filter('link =', slug).get()
    else:
        entry = Entry.all().filter("published =", True).filter('post_id =', postid).get()
    #use allow_trackback as allow_pingback
    if entry is None or not entry.allow_trackback:
        raise Fault(33, 'no such post')
    title, excerpt = get_excerpt(response, target_uri)
    if not title:
        raise Fault(17, 'no title provided')
    elif not excerpt:
        raise Fault(17, 'no useable link to target')

    comment = Comment.all().filter("entry =", entry).filter("weburl =", source_uri).get()
    if comment:
        raise Fault(48, 'pingback has already been registered')
        return

    comment=Comment(author=title[:30],
            content="<strong>"+title[:250]+"...</strong><br/>" +
                    excerpt[:250] + '...',
            weburl=source_uri,
            entry=entry)
    comment.ctype=COMMENT_PINGBACK
    try:
        comment.save()
        g_blog.tigger_action("pingback_post",comment)
        logging.info("PingBack Successfully Added ! From  %s"%source_uri)
        memcache.delete("/"+entry.link)
        return True
    except:
        raise Fault(49,"Access denied.")
        return

##------------------------------------------------------------------------------
class PlogXMLRPCDispatcher(SimpleXMLRPCDispatcher):
    def __init__(self, funcs):
        SimpleXMLRPCDispatcher.__init__(self, True, 'utf-8')
        self.funcs = funcs
        self.register_introspection_functions()

dispatcher = PlogXMLRPCDispatcher({
    'blogger.getUsersBlogs' : blogger_getUsersBlogs,
    'blogger.deletePost' : blogger_deletePost,
    'blogger.getUserInfo': blogger_getUserInfo,

    'metaWeblog.newPost' : metaWeblog_newPost,
    'metaWeblog.editPost' : metaWeblog_editPost,
    'metaWeblog.getCategories' : metaWeblog_getCategories,
    'metaWeblog.getPost' : metaWeblog_getPost,
    'metaWeblog.getRecentPosts' : metaWeblog_getRecentPosts,
    'metaWeblog.newMediaObject':metaWeblog_newMediaObject,

    'wp.getUsersBlogs':wp_getUsersBlogs,
    'wp.getTags':wp_getTags,
    'wp.getCommentCount':wp_getCommentCount,
    'wp.getPostStatusList':wp_getPostStatusList,
    'wp.getPageStatusList':wp_getPageStatusList,
    'wp.getPageTemplates':wp_getPageTemplates,
    'wp.getOptions':wp_getOptions,
    'wp.setOptions':wp_setOptions,
    'wp.getCategories':metaWeblog_getCategories,
    'wp.newCategory':wp_newCategory,
    'wp.newPage':wp_newPage,
    'wp.getPage':wp_getPage,
    'wp.getPages':wp_getPages,
    'wp.editPage':wp_editPage,
    'wp.getPageList':wp_getPageList,
    'wp.deletePage':wp_deletePage,
    'wp.getAuthors':wp_getAuthors,
    'wp.deleteComment':wp_deleteComment,
    'wp.editComment':wp_editComment,
    'wp.newComment':wp_newComment,
    'wp.getCommentStatusList':wp_getCommentStatusList,
    'wp.deleteCategory':wp_deleteCategory,
    'wp.suggestCategories':wp_suggestCategories,
    'wp.getComment':wp_getComment,
    'wp.getComments':wp_getComments,
    'wp.uploadFile':metaWeblog_newMediaObject,

    'mt.setPostCategories':mt_setPostCategories,
    'mt.getPostCategories':mt_getPostCategories,
    'mt.getCategoryList':mt_getCategoryList,
    'mt.publishPost':mt_publishPost,
    'mt.getRecentPostTitles':mt_getRecentPostTitles,
    'mt.getTrackbackPings':mt_getTrackbackPings,

    ##pingback
    'pingback.ping':pingback_ping,
    'pingback.extensions.getPingbacks':pingback_extensions_getPingbacks,
    })


# {{{ Handlers
class CallApi(BaseRequestHandler):
    def get(self):
        Logger(request = self.request.uri, response = self.request.remote_addr+'----------------------------------').put()
        self.write('<h1>please use POST</h1>')

    def post(self):
        #self.response.headers['Content-Type'] = 'application/xml; charset=utf-8'
        request = self.request.body
        response = dispatcher._marshaled_dispatch(request)
        Logger(request = unicode(request, 'utf-8'), response = unicode(response, 'utf-8')).put()
        self.write(response)

class View(BaseRequestHandler):
    @requires_admin
    def get(self):
        self.write('<html><body><h1>Logger</h1>')
        for log in Logger.all().order('-date').fetch(5,0):
            self.write("<p>date: %s</p>" % log.date)
            self.write("<h1>Request</h1>")
            self.write('<pre>%s</pre>' % cgi.escape(log.request))
            self.write("<h1>Reponse</h1>")
            self.write('<pre>%s</pre>' % cgi.escape(log.response))
            self.write("<hr />")
        self.write('</body></html>')

class DeleteLog(BaseRequestHandler):
    def get(self):
        if self.chk_admin():
            for log in Logger.all():
                log.delete()
            self.redirect('/rpc/view')
#}}}

def main():
    #webapp.template.register_template_library("filter")
    application = webapp.WSGIApplication(
            [
                ('/rpc', CallApi),
                ('/xmlrpc\.php',CallApi),
                ('/rpc/view', View),
                ('/rpc/dellog', DeleteLog),
                ],
            debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = filter
# -*- coding: utf-8 -*-
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from django import template
from model import *
import django.template.defaultfilters as defaultfilters
import urllib
register = template.Library()
from datetime import *

@register.filter
def datetz(date,format):  #datetime with timedelta
	t=timedelta(seconds=3600*g_blog.timedelta)
	return defaultfilters.date(date+t,format)

@register.filter
def TimestampISO8601(t):
	"""Seconds since epoch (1970-01-01) --> ISO 8601 time string."""
	return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))

@register.filter
def urlencode(value):
	return urllib.quote(value.encode('utf8'))

@register.filter
def check_current(v1,v2):
	if v1==v2:
		return "current"
	else:
		return ""

@register.filter
def excerpt_more(entry,value='..more'):
	return entry.get_content_excerpt(value.decode('utf8'))

@register.filter
def dict_value(v1,v2):
	return v1[v2]


import app.html_filter

plog_filter = app.html_filter.html_filter()
plog_filter.allowed = {
		'a': ('href', 'target', 'name', 'rel'),
		'b': (),
		'blockquote': (),
		'pre': (),
		'em': (),
		'i': (),
		'img': ('src', 'width', 'height', 'alt', 'title'),
		'strong': (),
		'u': (),
		'font': ('color', 'size'),
		'p': (),
		'h1': (),
		'h2': (),
		'h3': (),
		'h4': (),
		'h5': (),
		'h6': (),
		'table': (),
		'tr': (),
		'th': (),
		'td': (),
		'ul': (),
		'ol': (),
		'li': (),
		'br': (),
		'hr': (),
		'code':(),
		}

plog_filter.no_close += ('br',)
plog_filter.allowed_entities += ('nbsp','ldquo', 'rdquo', 'hellip',)
plog_filter.make_clickable_urls = False # enable this will get a bug about a and img

@register.filter
def do_filter(data):
	return plog_filter.go(data)

'''
tag like {%mf header%}xxx xxx{%endmf%}
'''
@register.tag("mf")
def do_mf(parser, token):
	nodelist = parser.parse(('endmf',))
	parser.delete_first_token()
	return MfNode(nodelist,token)

class MfNode(template.Node):
	def __init__(self, nodelist,token):
		self.nodelist = nodelist
		self.token=token

	def render(self, context):
		tokens= self.token.split_contents()
		if len(tokens)<2:
			raise TemplateSyntaxError, "'mf' tag takes one argument: the filter name is needed"
		fname=tokens[1]
		output = self.nodelist.render(context)
		return g_blog.tigger_filter(fname,output)
########NEW FILE########
__FILENAME__ = gbtools
#!/usr/bin/env python
# -*- coding:GBK -*-

"""∫∫◊÷¥¶¿Ìµƒπ§æﬂ:
≈–∂œunicode «∑Ò «∫∫◊÷£¨ ˝◊÷£¨”¢Œƒ£¨ªÚ’ﬂ∆‰À˚◊÷∑˚°£
»´Ω«∑˚∫≈◊™∞ÎΩ«∑˚∫≈°£"""

__author__="internetsweeper <zhengbin0713@gmail.com>"
__date__="2007-08-04"

def is_chinese(uchar):
        """≈–∂œ“ª∏ˆunicode «∑Ò «∫∫◊÷"""
        if uchar >= u'\u4e00' and uchar<=u'\u9fa5':
                return True
        else:
                return False

def is_number(uchar):
        """≈–∂œ“ª∏ˆunicode «∑Ò « ˝◊÷"""
        if uchar >= u'\u0030' and uchar<=u'\u0039':
                return True
        else:
                return False

def is_alphabet(uchar):
        """≈–∂œ“ª∏ˆunicode «∑Ò «”¢Œƒ◊÷ƒ∏"""
        if (uchar >= u'\u0041' and uchar<=u'\u005a') or (uchar >= u'\u0061' and uchar<=u'\u007a'):
                return True
        else:
                return False

def is_other(uchar):
        """≈–∂œ «∑Ò∑«∫∫◊÷£¨ ˝◊÷∫Õ”¢Œƒ◊÷∑˚"""
        if not (is_chinese(uchar) or is_number(uchar) or is_alphabet(uchar)):
                return True
        else:
                return False

def B2Q(uchar):
        """∞ÎΩ«◊™»´Ω«"""
        inside_code=ord(uchar)
        if inside_code<0x0020 or inside_code>0x7e:      #≤ª «∞ÎΩ«◊÷∑˚æÕ∑µªÿ‘≠¿¥µƒ◊÷∑˚
                return uchar
        if inside_code==0x0020: #≥˝¡Àø’∏Ò∆‰À˚µƒ»´Ω«∞ÎΩ«µƒπ´ ΩŒ™:∞ÎΩ«=»´Ω«-0xfee0
                inside_code=0x3000
        else:
                inside_code+=0xfee0
        return unichr(inside_code)

def Q2B(uchar):
        """»´Ω«◊™∞ÎΩ«"""
        inside_code=ord(uchar)
        if inside_code==0x3000:
                inside_code=0x0020
        else:
                inside_code-=0xfee0
        if inside_code<0x0020 or inside_code>0x7e:      #◊™ÕÍ÷Æ∫Û≤ª «∞ÎΩ«◊÷∑˚∑µªÿ‘≠¿¥µƒ◊÷∑˚
                return uchar
        return unichr(inside_code)

def stringQ2B(ustring):
        """∞—◊÷∑˚¥Æ»´Ω«◊™∞ÎΩ«"""
        return "".join([Q2B(uchar) for uchar in ustring])

def uniform(ustring):
        """∏Ò ΩªØ◊÷∑˚¥Æ£¨ÕÍ≥…»´Ω«◊™∞ÎΩ«£¨¥Û–¥◊™–°–¥µƒπ§◊˜"""
        return stringQ2B(ustring).lower()

def string2List(ustring):
        """Ω´ustring∞¥’’÷–Œƒ£¨◊÷ƒ∏£¨ ˝◊÷∑÷ø™"""
        retList=[]
        utmp=[]
        for uchar in ustring:
                if is_other(uchar):
                        if not len(utmp):
                                continue
                        else:
                                retList.append("".join(utmp))
                                utmp=[]
                else:
                        utmp.append(uchar)
        if len(utmp):
                retList.append("".join(utmp))
        return retList

if __name__=="__main__":
        #test Q2B and B2Q
        for i in range(0x0020,0x007F):
                print Q2B(B2Q(unichr(i))),B2Q(unichr(i))

        #test uniform
        ustring=u'÷–π˙ »À√˚£·∏ﬂ∆µ£¡'
        ustring=uniform(ustring)
        ret=string2List(ustring)
        print ret

########NEW FILE########
__FILENAME__ = gmemsess
# gmemsess.py - memcache-backed session Class for Google Appengine
# Version 1.4
#	Copyright 2008 Greg Fawcett <greg@vig.co.nz>
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <http://www.gnu.org/licenses/>.

import random
from google.appengine.api import memcache

_sidChars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
_defaultTimeout=30*60 # 30 min
_defaultCookieName='gsid'

#----------------------------------------------------------------------
class Session(dict):
	"""A secure lightweight memcache-backed session Class for Google Appengine."""

	#----------------------------------------------------------
	def __init__(self,rh,name=_defaultCookieName,timeout=_defaultTimeout):
		"""Create a session object.

		Keyword arguments:
		rh -- the parent's request handler (usually self)
		name -- the cookie name (defaults to "gsid")
		timeout -- the number of seconds the session will last between
		           requests (defaults to 1800 secs - 30 minutes)
		"""
		self.rh=rh	# request handler
		self._timeout=timeout
		self._name=name
		self._new=True
		self._invalid=False
		dict.__init__(self)

		if name in rh.request.str_cookies:
			self._sid=rh.request.str_cookies[name]
			data=memcache.get(self._sid)
			if data is not None:
				self.update(data)
				# memcache timeout is absolute, so we need to reset it on each access
				memcache.set(self._sid,data,self._timeout)
				self._new=False
				return

		# Create a new session ID
		# There are about 10^14 combinations, so guessing won't work
		self._sid=random.choice(_sidChars)+random.choice(_sidChars)+\
							random.choice(_sidChars)+random.choice(_sidChars)+\
							random.choice(_sidChars)+random.choice(_sidChars)+\
							random.choice(_sidChars)+random.choice(_sidChars)
		# Added path so session works with any path
		rh.response.headers.add_header('Set-Cookie','%s=%s; path=/;'%(name,self._sid))

	#----------------------------------------------------------
	def save(self):
		"""Save session data."""
		if not self._invalid:
			memcache.set(self._sid,self.copy(),self._timeout)

	#----------------------------------------------------------
	def is_new(self):
		"""Returns True if session was created during this request."""
		return self._new

	#----------------------------------------------------------
	def get_id(self):
		"""Returns session id string."""
		return self._sid

	#----------------------------------------------------------
	def invalidate(self):
		"""Delete session data and cookie."""
		self.rh.response.headers.add_header('Set-Cookie',
				'%s=; expires=Sat, 1-Jan-2000 00:00:00 GMT;'%self._name)
		memcache.delete(self._sid)
		self.clear()
		self._invalid=True

########NEW FILE########
__FILENAME__ = html_filter
# -*- coding: utf-8 -*-
"""
    A Python HTML filtering library - html_filter.py, v 1.15.4

    Translated to Python by Samuel Adam <samuel.adam@gmail.com>
    http://amisphere.com/contrib/python-html-filter/
    
    
    Original PHP code ( lib_filter.php, v 1.15 ) by Cal Henderson  <cal@iamcal.com>
    
    http://iamcal.com/publish/articles/php/processing_html/
    http://iamcal.com/publish/articles/php/processing_html_part_2/
    
    This code is licensed under a Creative Commons Attribution-ShareAlike 2.5 License
    http://creativecommons.org/licenses/by-sa/2.5/

"""
    
import re
from cgi import escape
from HTMLParser import HTMLParser

class html_filter:
    """
    html_filter removes HTML tags that do not belong to a white list
                closes open tags and fixes broken ones
                removes javascript injections and black listed URLs
                makes text URLs and emails clickable
                adds rel="no-follow" to links except for white list
                
    default settings are based on Flickr's "Some HTML is OK"
    http://www.flickr.com/html.gne
                

    HOWTO
    
    1. Basic example
    
        from html_filter import html_filter
        filter = html_filter()
        
        #change settings to meet your needs
        filter.strip_comments = False
        filter.allowed['br'] = ()
        filter.no_close += 'br',
        
        raw_html = '<p><strong><br><!-- Text to filter !!!<div></p>'
        
        # go() is a shortcut to apply the most common methods
        filtered_html = filter.go(raw_html)
        
        # returns <strong><br />&lt;!-- Text to filter !!!</strong>
    
    
    2. You can only use one method at a time if you like
        
        from html_filter import html_filter
        filter = html_filter()
                
        please_dont_scream_this_is_a_pop_contest = filter.fix_case('HARD ROCK ALELUYAH!!!')
        # returns Hard rock aleluyah!!!
        
        filter.break_words_longer_than = 30
        wordwrap_text = filter.break_words('MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM...')
        # adds html entity "&#8203;" (zero width space) each 30 characters
    
    """
    
    def __init__(self):

        ### START Default Config ###
        
        # tags and attributes that are allowed
        self.allowed = {
            'a': ('href', 'target'), 
            'b': (), 
            'blockquote': (), 
            'em': (), 
            'i': (), 
            'img': ('src', 'width', 'height', 'alt', 'title'), 
            'strong': (), 
            'u': (), 
        }
    
        # tags which should always be self-closing (e.g. "<img />")
        self.no_close = (
            'img',
        )
        
        # tags which must always have seperate opening and closing tags (e.g. "<b></b>")
        self.always_close = (
            'a', 
            'b', 
            'blockquote', 
            'em', 
            'i', 
            'strong', 
            'u', 
        )

        # tags which should be removed if they contain no content (e.g. "<b></b>" or "<b />")
        self.remove_blanks = (
            'a', 
            'b', 
            'blockquote', 
            'em', 
            'i', 
            'strong', 
            'u', 
        )
        
        # attributes which should be checked for valid protocols
        self.protocol_attributes = (
            'src', 
            'href', 
        )
    
        # protocols which are allowed
        self.allowed_protocols = (
            'http', 
            'https', 
            'ftp', 
            'mailto', 
        )
        
        # forbidden urls ( regular expressions ) are replaced by #
        self.forbidden_urls = (
            r'^/delete-account',     
            r'^domain.ext/delete-account',     
        )

        # should we make urls clickable ?
        self.make_clickable_urls = True     

        # should we add a rel="nofollow" to the links ?
        self.add_no_follow = True
        
        # except for those domains
        self.follow_for = (
               'allowed-domain.ext',
       )
        
        # should we remove comments?
        self.strip_comments = True
        
        # should we removes blanks from beginning and end of data ?
        self.strip_data = True
    
        # should we try and make a b tag out of "b>"
        self.always_make_tags = False  
    
        # entity control options
        self.allow_numbered_entities = True
    
        self.allowed_entities = (
            'amp', 
            'gt', 
            'lt', 
            'quot', 
        )
        
        # should we "break" words longer than x chars ( 0 means "No", minimum is 8 chars )
        self.break_words_longer_than = 0        
        
        ### END Default Config ###

        # INIT
        
        self.tag_counts = {}

        # pre-compile some regexp patterns
        self.pat_entities = re.compile(r'&([^&;]*)(?=(;|&|$))')
        self.pat_quotes = re.compile(r'(>|^)([^<]+?)(<|$)', re.DOTALL|re.IGNORECASE)
        self.pat_valid_entity = re.compile(r'^#([0-9]+)$', re.IGNORECASE)
        self.pat_decode_entities_dec = re.compile(r'(&)#(\d+);?')
        self.pat_decode_entities_hex = re.compile(r'(&)#x([0-9a-f]+);?', re.IGNORECASE)
        self.pat_decode_entities_hex2 = re.compile(r'(%)([0-9a-f]{2});?', re.IGNORECASE)
        self.pat_entities2 = re.compile(r'&([^&;]*);?', re.IGNORECASE)
        self.pat_raw_url = re.compile('(('+'|'.join(self.allowed_protocols)+')://)(([a-z0-9](?:[a-z0-9\\-]*[a-z0-9])?\\.)+(com\\b|edu\\b|biz\\b|gov\\b|in(?:t|fo)\\b|mil\\b|net\\b|org\\b|[a-z][a-z]\\b)|((25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])))(:\\d+)?(/[-a-z0-9_:\\\\@&?=+,\\.!/~*\'%\\$]*)*(?<![.,?!])(?!((?!(?:<a )).)*?(?:</a>))(?!((?!(?:<!--)).)*?(?:-->))', re.IGNORECASE)
        
#

    def go(self, data):
        
        data = self.strip_whitespace(data)
        data = self.escape_comments(data)
        data = self.balance_html(data)
        data = self.clickable_urls(data)
        data = self.check_tags(data)
        data = self.process_remove_blanks(data)
        data = self.validate_entities(data)
        data = self.break_words(data)
        

        
        return data
          
#

    def strip_whitespace(self, data):
        if self.strip_data:
            data = data.strip()
        return data
#
    
    def escape_comments(self, data):
        pat = re.compile(r'<!--(.*?)-->', re.IGNORECASE)
        data = re.sub(pat, self.f0, data)
        return data
    def f0(self, m):
        return '<!--'+escape(m.group(1), True)+'-->'
    
#
    
    def balance_html(self, data):
        # try and form html
        if self.always_make_tags:
            data = re.sub(r'>>+', r'>', data)
            data = re.sub(r'<<+', r'<', data)
            data = re.sub(r'^>', r'', data)
            data = re.sub(r'<([^>]*?)(?=<|$)', r'<\1>', data)
            data = re.sub(r'(^|>)([^<]*?)(?=>)', r'\1<\2', data)
        else:
            data = data.replace('<>', '&lt;&gt;') # <> as text
            data = self.re_sub_overlap(r'<([^>]*?)(?=<|$)', r'&lt;\1', data)
            data = self.re_sub_overlap(r'(^|>)([^<]*?)(?=>)', r'\1\2&gt;<', data)
            data = re.sub(r'<(\s)+?', r'&lt;\1', data) # consider "< a href" as "&lt; a href"
            # this filter introduces an error, so we correct it
            data = data.replace('<>', '')
        return data

    # python re.sub() doesn't overlap matches
    def re_sub_overlap(self, pat, repl, data, i=0):
        data_temp = re.sub(pat, repl, data[i:])
        if data_temp != data[i:]:
            data = data[:i] + data_temp
            i += 1
            data = self.re_sub_overlap(pat, repl, data, i)
        return data

#

    def clickable_urls(self, data):
        if self.make_clickable_urls:
            # urls
#            pat = re.compile('(('+'|'.join(self.allowed_protocols)+')://)(([a-z0-9](?:[a-z0-9\\-]*[a-z0-9])?\\.)+(com\\b|edu\\b|biz\\b|gov\\b|in(?:t|fo)\\b|mil\\b|net\\b|org\\b|[a-z][a-z]\\b)|((25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])))(:\\d+)?(/[-a-z0-9_:\\\\@&?=+,\\.!/~*\'%\\$]*)*(?<![.,?!])(?!((?!(?:<a )).)*?(?:</a>))(?!((?!(?:<!--)).)*?(?:-->))', re.IGNORECASE)
            data = re.sub(self.pat_raw_url, self.f7, data)
            # emails
            if 'mailto' in self.allowed_protocols:
                pat = re.compile(r'((([a-z]|[0-9]|!|#|$|%|&|\'|\*|\+|\-|/|=|\?|\^|_|`|\{|\||\}|~)+(\.([a-z]|[0-9]|!|#|$|%|&|\'|\*|\+|\-|/|=|\?|\^|_|`|\{|\||\}|~)+)*)@((((([a-z]|[0-9])([a-z]|[0-9]|\-){0,61}([a-z]|[0-9])\.))*([a-z]|[0-9])([a-z]|[0-9]|\-){0,61}([a-z]|[0-9])\.(com|edu|gov|int|mil|net|org|biz|info|name|pro|aero|coop|museum|arpa|[a-z]{2}))|(((([0-9]){1,3}\.){3}([0-9]){1,3}))|(\[((([0-9]){1,3}\.){3}([0-9]){1,3})\])))(?!((?!(?:<a )).)*?(?:</a>))(?!((?!(?:<!--)).)*?(?:-->))', re.IGNORECASE)
                data = re.sub(pat, self.f8, data)
        return data
    
    def f7(self, m):          
        return '<a href="'+m.group(0)+'">'+m.group(0)+'</a>'
    def f8(self, m):          
        return '<a href="mailto:'+m.group(0)+'">'+m.group(0)+'</a>'
           
#

    def check_tags(self, data):
        # compile loop regexps
        self.pat_end_tag = re.compile(r'^/([a-z0-9]+)', re.DOTALL|re.IGNORECASE)
        self.pat_start_tag = re.compile(r'^([a-z0-9]+)(.*?)(/?)$', re.DOTALL|re.IGNORECASE)
        self.pat_matches_2 = re.compile(r'([a-z0-9]+)=(["\'])(.*?)\2', re.DOTALL|re.IGNORECASE)           # <foo a="b" />
        self.pat_matches_1 = re.compile(r'([a-z0-9]+)(=)([^"\s\']+)', re.DOTALL|re.IGNORECASE)            # <foo a=b />
        self.pat_matches_3 = re.compile(r'([a-z0-9]+)=(["\'])([^"\']*?)\s*$', re.DOTALL|re.IGNORECASE)    # <foo a="b />
        self.pat_comments = re.compile(r'^!--(.*)--$', re.DOTALL|re.IGNORECASE)
        self.pat_param_protocol = re.compile(r'^([^:]+):', re.DOTALL|re.IGNORECASE)
        
        pat = re.compile(r'<(.*?)>', re.DOTALL) 
        data = re.sub(pat, self.f1, data)

        for tag in self.tag_counts:
            count = self.tag_counts[tag]
            for i in range(count):
                data += '</'+tag+'>'
        self.tag_counts = {}

        return data
    
    def f1(self, m):
        return self.process_tag(m.group(1))
        
#

    def process_tag(self, data):

        # ending tags        
        m = re.match(self.pat_end_tag, data)
        if m:
            name = m.group(1).lower()
            if name in self.allowed:
                if name not in self.no_close:
                    if self.tag_counts.has_key(name):
                        self.tag_counts[name] -= 1
                        return '</' + name + '>'
            else:
                return ''
        
        # starting tags
        m = re.match(self.pat_start_tag, data)
        if m:
            name = m.group(1).lower()
            body = m.group(2)
            ending = m.group(3)
            
            if name in self.allowed:
                params = ''
                matches_2 = re.findall(self.pat_matches_2, body)    # <foo a="b" />
                matches_1 = re.findall(self.pat_matches_1, body)    # <foo a=b />
                matches_3 = re.findall(self.pat_matches_3, body)    # <foo a="b />
                
                matches = {}
                
                for match in matches_3:
                    matches[match[0].lower()] = match[2]
                for match in matches_1:
                    matches[match[0].lower()] = match[2]
                for match in matches_2:
                    matches[match[0].lower()] = match[2]
                    
                for pname in matches:
                    if pname in self.allowed[name]:
                        value = matches[pname]
                        if pname in self.protocol_attributes:
                            processed_value = self.process_param_protocol(value)
                            # add no_follow
                            if self.add_no_follow and name== 'a' and pname == 'href' and processed_value == value:
                                processed_value = re.sub(self.pat_raw_url, self.f9, processed_value)
                            value = processed_value
                        params += ' '+pname+'="'+value+'"'
                
                if name in self.no_close:
                    ending = ' /'
                
                if name in self.always_close:
                    ending = ''

                if not ending:
                    if self.tag_counts.has_key(name):
                        self.tag_counts[name] += 1
                    else:
                        self.tag_counts[name] = 1
                
                if ending:
                    ending = ' /'
                    
                return '<'+name+params+ending+'>'
            
            else:
                return ''
                    
        # comments
        m = re.match(self.pat_comments, data)
        
        if m:
            if self.strip_comments:
                return ''
            else:
                return '<'+data+'>'

        # garbage, ignore it
        return ''

    def f9(self, m):
        if m.group(3) not in self.follow_for:
            return m.group()+'" rel="no-follow'
        return m.group()
#

    def process_param_protocol(self, data):

        data = self.decode_entities(data)
        
        m = re.match(self.pat_param_protocol, data)
        if m:
            if not m.group(1) in self.allowed_protocols:
                start = len(m.group(1)) + 1
                data = '#' + data[start:]
        
        # remove forbidden urls
        for pat in self.forbidden_urls:
            m = re.search(pat, data)
            if m:
                data = '#'
        
        return data

#

    def process_remove_blanks(self, data):
        
        for tag in self.remove_blanks:
            data = re.sub(r'<'+tag+'(\s[^>]*)?></'+tag+'>', r'', data)
            data = re.sub(r'<'+tag+'(\s[^>]*)?/>', r'', data)
            
        return data
    
#

    def strip_tags(self, html):
        result = []
        parser = HTMLParser()
        parser.handle_data = result.append
        parser.feed(html)
        parser.close()
        return ''.join(result)
    

    def fix_case(self, data):
        
        # compile loop regexps
        self.pat_case_inner = re.compile(r'(^|[^\w\s\';,\\-])(\s*)([a-z])')
        
        data_notags = self.strip_tags(data)
        data_notags = re.sub(r'[^a-zA-Z]', r'', data_notags)
        
        if len(data_notags) < 5:
            return data

        m = re.search(r'[a-z]', data_notags)
        if m:
            return data
        
        pat = re.compile(r'(>|^)([^<]+?)(<|$)', re.DOTALL)
        data = re.sub(pat, self.f2, data)

        return data

    def f2(self, m):
        return m.group(1)+self.fix_case_inner(m.group(2))+m.group(3)
    
    def fix_case_inner(self, data):
        return re.sub(self.pat_case_inner, self.f3, data.lower())
    
    def f3(self, m):
        return m.group(1)+m.group(2)+m.group(3).upper()

#

    def validate_entities(self, data):        
        # validate entities throughout the string
        data = re.sub(self.pat_entities, self.f4, data)
        # validate quotes outside of tags
        data = re.sub(self.pat_quotes, self.f5, data)
        return data

    def f4(self, m):
        return self.check_entity(m.group(1), m.group(2))
    
    def f5(self, m):
        return m.group(1)+m.group(2).replace('"', '&quot;')+m.group(3)

#

    def check_entity(self, preamble, term):
        
        if term != ';':
            return '&amp;'+preamble
        
        if self.is_valid_entity(preamble):
            return '&'+preamble
        
        return '&amp;'+preamble

    def is_valid_entity(self, entity):
        
        m = re.match(self.pat_valid_entity, entity)
        if m:
            if int(m.group(1)) > 127:
                return True
            
            return self.allow_numbered_entities
        
        if entity in self.allowed_entities:
            return True
        
        return False

#

    # within attributes, we want to convert all hex/dec/url escape sequences into
    # their raw characters so that we can check we don't get stray quotes/brackets
    # inside strings
    
    def decode_entities(self, data):
        
        data = re.sub(self.pat_decode_entities_dec, self.decode_dec_entity, data)
        data = re.sub(self.pat_decode_entities_hex, self.decode_hex_entity, data)
        data = re.sub(self.pat_decode_entities_hex2, self.decode_hex_entity, data)
        
        data = self.validate_entities(data)
        
        return data
    
    
    def decode_hex_entity(self, m):
        
        return self.decode_num_entity(m.group(1), int(m.group(2), 16))

    def decode_dec_entity(self, m):
        
        return self.decode_num_entity(m.group(1), int(m.group(2)))

    def decode_num_entity(self, orig_type, d):
        
        if d < 0:
            d = 32 # space
        
        if d > 127:
            if orig_type == '%':
                return '%' + hex(d)[2:]
            if orig_type == '&':
                return '&#'+str(d)+';'
            
        return escape(chr(d))

#

    def break_words(self, data):
        if self.break_words_longer_than > 0:
            pat = re.compile(r'(>|^)([\s]*)([^<]+?)([\s]*)(<|$)', re.DOTALL)
            data = re.sub(pat, self.f6, data)
        return data

    def f6(self, m):
        return m.group(1)+m.group(2)+self.break_text(m.group(3))+m.group(4)+m.group(5)
    
    def break_text(self, text):
        ret = ''
        entity_max_length = 8
        if self.break_words_longer_than < entity_max_length:
            width = entity_max_length
        else:
            width = self.break_words_longer_than
            
        for word in text.split(' '):
            if len(word) > width:
                word = word.replace('&#8203;','')
                m = re.search(self.pat_entities2, word[width-entity_max_length:width+entity_max_length])
                if m:
                    width = width - entity_max_length + m.end()
                ret += word[0:width] + '&#8203;' + self.break_text(word[width:]) # insert "Zero Width" Space - helps wordwrap
            else:
                ret += word + ' '
        return ret.strip()
    

########NEW FILE########
__FILENAME__ = mktimefix
from time import *
from calendar import timegm

# fix for mktime bug
# https://garage.maemo.org/tracker/index.php?func=detail&aid=4453&group_id=854&atid=3201
mktime = lambda time_tuple: calendar.timegm(time_tuple) + timezone


########NEW FILE########
__FILENAME__ = pingback
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2003, Mathieu Fenniak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
A simple library that implements a pingback client.  The library supports
version 1.0 of the pingback library, based upon the specification published
at http://www.hixie.ch/specs/pingback/pingback.

Implementing a pingback server is beyond the scope of this library simply
because of the very application-specific nature of a server.  However, it is
also trivially easy to create a pingback server by using Python's
SimpleXMLRPCServer module.  The following simple framework could be used
by a CGI script to implement a pingback server::

    def pingback(sourceURI, targetURI):
        '''Do something interesting!'''
        return "arbitrary string return value."

    import SimpleXMLRPCServer
    handler = SimpleXMLRPCServer.CGIXMLRPCRequestHandler()
    handler.register_function(pingback, "pingback.ping")
    handler.handle_request()

It would still be necessary to provide an X-Pingback HTTP header which pointed
at the given CGI script.
"""
__author__ = "Mathieu Fenniak <laotzu@pobox.com>"
__date__ = "2003-01-26"
__version__ = "2003.01.26.01"
__changed__ = "2010.10.03@SkyCloud <admin@tangblog.info>"
__website__ = "www.tangblog.info"

import re
from base import util
from HTMLParser import HTMLParser

def reSTLinks(txt):
    reSTLink = re.compile("\n\\.\\.\\s+[^\n:]+:\s+(http://[^\n]+)", re.I)
    linkMatches = reSTLink.findall(txt)
    return linkMatches


class _LinkExtractor(HTMLParser, object):
    def __init__(self, links):
        super(_LinkExtractor, self).__init__()
        self.links = links

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for key, value in attrs:
                if key == "href" and value.startswith("http://"):
                    self.links.append(value)

class _HrefExtractor(HTMLParser,object):
    def __init__(self, links):
        super(_HrefExtractor, self).__init__()
        self.links = links
        self.currentLink=None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.currentLink=None
            self.buffer=""
            for key, value in attrs:
                if key == "href" and value.startswith("http://"):
                    self.currentLink=value
            
    def handle_endtag(self,tag):
        if tag == "a":
            if self.currentLink:
                self.links.append((self.currentLink,self.buffer))
                self.currentLink=None
                self.buffer=""
    def handle_data(self,data):
        if self.currentLink:
            self.buffer += data
            
def htmlLinks(txt):
    links = []
    le = _LinkExtractor(links)
    le.feed(txt)
    le.close()
    return links

def hrefExtractor(txt):
    links=[]
    le = _HrefExtractor(links)
    le.feed(txt)
    le.close()
    return links

def autoPingback(sourceURI, reST = None, HTML = None):
    """Scans the input text, which can be in either reStructuredText or HTML
    format, pings every linked website for auto-discovery-capable pingback
    servers, and does an appropriate pingback.

    The following specification details how this code should work:
        http://www.hixie.ch/specs/pingback/pingback"""
    assert reST is not None or HTML is not None

    if reST is not None:
        links = reSTLinks(reST)
    else:
        links = htmlLinks(HTML)

    for link in links:
        util.do_pingback(sourceURI,link)

########NEW FILE########
__FILENAME__ = pngcanvas
#!/usr/bin/env python

"""Simple PNG Canvas for Python"""
__version__ = "0.8"
__author__ = "Rui Carmo (http://the.taoofmac.com)"
__copyright__ = "CC Attribution-NonCommercial-NoDerivs 2.0 Rui Carmo"
__contributors__ = ["http://collaboa.weed.rbse.com/repository/file/branches/pgsql/lib/spark_pr.rb"], ["Eli Bendersky"]

import zlib, struct

signature = struct.pack("8B", 137, 80, 78, 71, 13, 10, 26, 10)

# alpha blends two colors, using the alpha given by c2
def blend(c1, c2):
  return [c1[i]*(0xFF-c2[3]) + c2[i]*c2[3] >> 8 for i in range(3)]

# calculate a new alpha given a 0-0xFF intensity
def intensity(c,i):
  return [c[0],c[1],c[2],(c[3]*i) >> 8]

# calculate perceptive grayscale value
def grayscale(c):
  return int(c[0]*0.3 + c[1]*0.59 + c[2]*0.11)

# calculate gradient colors
def gradientList(start,end,steps):
  delta = [end[i] - start[i] for i in range(4)]
  grad = []
  for i in range(steps+1):
    grad.append([start[j] + (delta[j]*i)/steps for j in range(4)])
  return grad

class PNGCanvas:
  def __init__(self, width, height,bgcolor=[0xff,0xff,0xff,0xff],color=[0,0,0,0xff]):
    self.canvas = []
    self.width = width
    self.height = height
    self.color = color #rgba
    bgcolor = bgcolor[0:3] # we don't need alpha for background
    for i in range(height):
      self.canvas.append([bgcolor] * width)

  def point(self,x,y,color=None):
    if x<0 or y<0 or x>self.width-1 or y>self.height-1: return
    if color == None: color = self.color
    self.canvas[y][x] = blend(self.canvas[y][x],color)

  def _rectHelper(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x0 > x1: x0, x1 = x1, x0
    if y0 > y1: y0, y1 = y1, y0
    return [x0,y0,x1,y1]

  def verticalGradient(self,x0,y0,x1,y1,start,end):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    grad = gradientList(start,end,y1-y0)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        self.point(x,y,grad[y-y0])

  def rectangle(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    self.polyline([[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]])

  def filledRectangle(self,x0,y0,x1,y1):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        self.point(x,y,self.color)

  def copyRect(self,x0,y0,x1,y1,dx,dy,destination):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        destination.canvas[dy+y-y0][dx+x-x0] = self.canvas[y][x]

  def blendRect(self,x0,y0,x1,y1,dx,dy,destination,alpha=0xff):
    x0, y0, x1, y1 = self._rectHelper(x0,y0,x1,y1)
    for x in range(x0, x1+1):
      for y in range(y0, y1+1):
        rgba = self.canvas[y][x] + [alpha]
        destination.point(dx+x-x0,dy+y-y0,rgba)

  # draw a line using Xiaolin Wu's antialiasing technique
  def line(self,x0, y0, x1, y1):
    # clean params
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if y0>y1:
      y0, y1, x0, x1 = y1, y0, x1, x0
    dx = x1-x0
    if dx < 0:
      sx = -1
    else:
      sx = 1
    dx *= sx
    dy = y1-y0

    # 'easy' cases
    if dy == 0:
      for x in range(x0,x1,sx):
        self.point(x, y0)
      return
    if dx == 0:
      for y in range(y0,y1):
        self.point(x0, y)
      self.point(x1, y1)
      return
    if dx == dy:
      for x in range(x0,x1,sx):
        self.point(x, y0)
        y0 = y0 + 1
      return

    # main loop
    self.point(x0, y0)
    e_acc = 0
    if dy > dx: # vertical displacement
      e = (dx << 16) / dy
      for i in range(y0,y1-1):
        e_acc_temp, e_acc = e_acc, (e_acc + e) & 0xFFFF
        if (e_acc <= e_acc_temp):
          x0 = x0 + sx
        w = 0xFF-(e_acc >> 8)
        self.point(x0, y0, intensity(self.color,(w)))
        y0 = y0 + 1
        self.point(x0 + sx, y0, intensity(self.color,(0xFF-w)))
      self.point(x1, y1)
      return

    # horizontal displacement
    e = (dy << 16) / dx
    for i in range(x0,x1-sx,sx):
      e_acc_temp, e_acc = e_acc, (e_acc + e) & 0xFFFF
      if (e_acc <= e_acc_temp):
        y0 = y0 + 1
      w = 0xFF-(e_acc >> 8)
      self.point(x0, y0, intensity(self.color,(w)))
      x0 = x0 + sx
      self.point(x0, y0 + 1, intensity(self.color,(0xFF-w)))
    self.point(x1, y1)

  def polyline(self,arr):
    for i in range(0,len(arr)-1):
      self.line(arr[i][0],arr[i][1],arr[i+1][0], arr[i+1][1])

  def dump(self):
    raw_list = []
    for y in range(self.height):
      raw_list.append(chr(0)) # filter type 0 (None)
      for x in range(self.width):
        raw_list.append(struct.pack("!3B",*self.canvas[y][x]))
    raw_data = ''.join(raw_list)

    # 8-bit image represented as RGB tuples
    # simple transparency, alpha is pure white
    return signature + \
      self.pack_chunk('IHDR', struct.pack("!2I5B",self.width,self.height,8,2,0,0,0)) + \
      self.pack_chunk('tRNS', struct.pack("!6B",0xFF,0xFF,0xFF,0xFF,0xFF,0xFF)) + \
      self.pack_chunk('IDAT', zlib.compress(raw_data,9)) + \
      self.pack_chunk('IEND', '')

  def pack_chunk(self,tag,data):
    to_check = tag + data
    return struct.pack("!I",len(data)) + to_check + struct.pack("!I", zlib.crc32(to_check) & 0xFFFFFFFF)

  def load(self,f):
    assert f.read(8) == signature
    self.canvas=[]
    for tag, data in self.chunks(f):
      if tag == "IHDR":
        ( width,
          height,
          bitdepth,
          colortype,
          compression, filter, interlace ) = struct.unpack("!2I5B",data)
        self.width = width
        self.height = height
        if (bitdepth,colortype,compression, filter, interlace) != (8,2,0,0,0):
          raise TypeError('Unsupported PNG format')
      # we ignore tRNS because we use pure white as alpha anyway
      elif tag == 'IDAT':
        raw_data = zlib.decompress(data)
        rows = []
        i = 0
        for y in range(height):
          filtertype = ord(raw_data[i])
          i = i + 1
          cur = [ord(x) for x in raw_data[i:i+width*3]]
          if y == 0:
            rgb = self.defilter(cur,None,filtertype)
          else:
            rgb = self.defilter(cur,prev,filtertype)
          prev = cur
          i = i+width*3
          row = []
          j = 0
          for x in range(width):
            pixel = rgb[j:j+3]
            row.append(pixel)
            j = j + 3
          self.canvas.append(row)

  def defilter(self,cur,prev,filtertype,bpp=3):
    if filtertype == 0: # No filter
      return cur
    elif filtertype == 1: # Sub
      xp = 0
      for xc in range(bpp,len(cur)):
        cur[xc] = (cur[xc] + cur[xp]) % 256
        xp = xp + 1
    elif filtertype == 2: # Up
      for xc in range(len(cur)):
        cur[xc] = (cur[xc] + prev[xc]) % 256
    elif filtertype == 3: # Average
      xp = 0
      for xc in range(len(cur)):
        cur[xc] = (cur[xc] + (cur[xp] + prev[xc])/2) % 256
        xp = xp + 1
    elif filtertype == 4: # Paeth
      xp = 0
      for i in range(bpp):
        cur[i] = (cur[i] + prev[i]) % 256
      for xc in range(bpp,len(cur)):
        a = cur[xp]
        b = prev[xc]
        c = prev[xp]
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
          value = a
        elif pb <= pc:
          value = b
        else:
          value = c
        cur[xc] = (cur[xc] + value) % 256
        xp = xp + 1
    else:
      raise TypeError('Unrecognized scanline filter type')
    return cur

  def chunks(self,f):
    while 1:
      try:
        length = struct.unpack("!I",f.read(4))[0]
        tag = f.read(4)
        data = f.read(length)
        crc = struct.unpack("!i",f.read(4))[0]
      except:
        return
      if zlib.crc32(tag + data) != crc:
        raise IOError
      yield [tag,data]

if __name__ == '__main__':
  width = 128
  height = 64
  print "Creating Canvas..."
  c = PNGCanvas(width,height)
  c.color = [0xff,0,0,0xff]
  c.rectangle(0,0,width-1,height-1)
  print "Generating Gradient..."
  c.verticalGradient(1,1,width-2, height-2,[0xff,0,0,0xff],[0x20,0,0xff,0x80])
  print "Drawing Lines..."
  c.color = [0,0,0,0xff]
  c.line(0,0,width-1,height-1)
  c.line(0,0,width/2,height-1)
  c.line(0,0,width-1,height/2)
  # Copy Rect to Self
  print "Copy Rect"
  c.copyRect(1,1,width/2-1,height/2-1,0,height/2,c)
  # Blend Rect to Self
  print "Blend Rect"
  c.blendRect(1,1,width/2-1,height/2-1,width/2,0,c)
  # Write test
  print "Writing to file..."
  f = open("test.png", "wb")
  f.write(c.dump())
  f.close()
  # Read test
  print "Reading from file..."
  f = open("test.png", "rb")
  c.load(f)
  f.close()
  # Write back
  print "Writing to new file..."
  f = open("recycle.png","wb")
  f.write(c.dump())
  f.close()

########NEW FILE########
__FILENAME__ = recurse
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from django.template import Library
from django.template import Node, NodeList
from django.template import TemplateSyntaxError, VariableDoesNotExist

register = Library()

class RecurseNode( Node ):
    def __init__(self, **kwargs):
        self.loopvar, self.sequence = kwargs['loopvar'], kwargs['sequence']
        self.children_name  = kwargs['children_name']
        self.nodelist_first, self.nodelist_second = kwargs['nodelist_first'], kwargs['nodelist_second']
        del kwargs['nodelist_first'], kwargs['nodelist_second'], kwargs['sequence'], kwargs['children_name'], kwargs['loopvar']
        self.kwargs = kwargs
        
    def __repr__(self):
        reversed_text = self.is_reversed and ' reversed' or ''
        return "<For Node: for %s in %s, tail_len: %d%s>" % \
            (', '.join(self.loopvars), self.sequence, len(self.nodelist_loop),
             reversed_text)

    def __iter__(self):
      for node in self.nodelist_first:
        yield node
      for node in self.nodelist_second:
        yield node

    def get_nodes_by_type(self, nodetype):
      nodes = []
      if isinstance(self, nodetype):
        nodes.append(self)
      nodes.extend( self.nodelist_first.get_nodes_by_type(nodetype) )
      nodes.extend( self.nodelist_second.get_nodes_by_type(nodetype) )
      return nodes

    def render(self, context, depth=0, values=False):
        nodelist = NodeList()
        if 'recurseloop' in context:
            parentloop = context['recurseloop']
        else:
            parentloop = {}
        context.push()
        
        # On the first recursion pass, we have no values
        if not values:
          try:
              values = self.sequence.resolve(context, True)
          except VariableDoesNotExist:
              values = []
          if values is None:
              values = []
          if not hasattr(values, '__len__'):
              values = list(values)

        len_values = len(values)
        
        # Create a recurseloop value in the context.  We'll update counters on each iteration just below.
        loop_dict = context['recurseloop'] = {'parent': parentloop}
        
        loop_dict['depth'] = depth + 1
        loop_dict['depth0'] = depth

        for i, item in enumerate(values):
            # Add the additional arguments to the context
            # They come in the form of {'name':(initial,increment)}
            # As for now only numbers are supported, but also strings can be multiplied 
            for k,v in self.kwargs.iteritems():
              context[k] = v[0] + v[1]*depth
              
            # Shortcuts for current loop iteration number.
            loop_dict['counter0'] = i
            loop_dict['counter'] = i+1

            # Boolean values designating first and last times through loop.
            loop_dict['first'] = (i == 0)
            loop_dict['last'] = (i == len_values - 1)

            context[ self.loopvar ] = item
            
            for node in self.nodelist_first:
                nodelist.append( node.render(context) )
            
            if len( getattr( item, self.children_name ) ):
                nodelist.append( self.render( context, depth+1, getattr( item, self.children_name ) ) )
            
            for node in self.nodelist_second:
                nodelist.append( node.render(context) )
                        
        context.pop()
        return nodelist.render(context)

#@register.tag(name="for")
def do_recurse(parser, token):
    """
    Recursively loops over each item in an array . 
    It also increments passed variables on each recursion depth.
    For example, to display a list of comments with replies given ``comment_list``:
    
      {% recurse comment in comments children="replies" indent=(0,20) %}
          <div style="margin-left:{{indent}}px">{{ comment.text }}</div>
      {% endrecurse %}
    
    ``children`` is the name of the iterable that contains the children of the current element
    ``children`` needs to be a property of comment, and is required for the recurseloop to work
    You can pass additional parameters after children in the form of:
        
      var_name=(intial_value, increment)
    
    You need to take care of creating the tree structure on your own.
    As for now there should be no spaces between the equal ``=`` 
    signs when assigning children or additional variables
    
    In addition to the variables passed, the recurse loop sets a 
    number of variables available within the loop:
        ==========================  ================================================
        Variable                    Description
        ==========================  ================================================
        ``recurseloop.depth``       The current depth of the loop (1 is the top level)
        ``recurseloop.depth0``      The current depth of the loop (0 is the top level)
        ``recurseloop.counter``     The current iteration of the current level(1-indexed)
        ``recurseloop.counter0``    The current iteration of the current level(0-indexed)
        ``recurseloop.first``       True if this is the first time through the current level
        ``recurseloop.last``        True if this is the last time through the current level
        ``recurseloop.parent``      This is the loop one level "above" the current one
        ==========================  ================================================
    
    You can also use the tag {% yield %} inside a recursion.
    The ``yield`` tag will output the same HTML that's between the recurse and endrecurse tags
    if the current element has children. If there are no children ``yield`` will output nothing
    You must not, however wrap the ``yield`` tag inside other tags, just like you must not wrap
    the ``else`` tag inside other tags when making if-else-endif 
    """
    # We will be throwing this a lot
    def tError( contents ):
      raise TemplateSyntaxError(
      "'recurse' statements should use the format"
      "'{%% recurse x in y children=\"iterable_property_name\" "
      "arg1=(float,float) arg2=(\"str\",\"str\") %%}: %s" % contents )

    bits = token.contents.split()
    quotes = ["'","\""]
    lenbits = len(bits)
    if lenbits < 5:
        tError(token.contents)
        
    in_index = 2
    children_index = 4
    if bits[in_index] != 'in':
        tError(token.contents)
                                  
    children_token = bits[children_index].split("=")
    
    if len(children_token) != 2 or children_token[0] != 'children':
        tError(token.contents)

    f = children_token[1][0]
    l = children_token[1][-1]
    
    if f != l or f not in quotes:
        tError(token.contents)
    else:
      children_token[1] = children_token[1].replace(f,"")
    
    def convert(val):
      try:
        val = float(val)
      except ValueError:
        f = val[0]
        l = val[-1]
        if f != l or f not in quotes:
            tError(token.contents)
        val = unicode( val.replace(f,"") )
      return val

    node_vars = {}
    if lenbits > 5:
      for bit in bits[5:]:
        arg = bit.split("=")

        if len(arg) != 2 :
          tError(token.contents)

        f = arg[1][0]
        l = arg[1][-1]
        if f != "(" or l != ")":
            tError(token.contents)
        
        try:
          argval = tuple([ convert(x) for x in arg[1].replace("(","").replace(")","").split(",") ])
        # Invalid float number, or missing comma
        except (IndexError, ValueError):
            tError(token.contents)
        node_vars[ str(arg[0]) ] = argval
        
    node_vars['children_name'] = children_token[1]
    node_vars['loopvar'] = bits[1]
    node_vars['sequence'] = parser.compile_filter(bits[3])
    
    nodelist_first = parser.parse( ('yield', 'endrecurse',) )
    token = parser.next_token()
    if token.contents == 'yield':
      nodelist_second = parser.parse( ('endrecurse', ) )
      parser.delete_first_token()
    else:
      nodelist_second = NodeList()
    node_vars['nodelist_first'] = nodelist_first
    node_vars['nodelist_second'] = nodelist_second
    return RecurseNode(**node_vars)
do_recurse = register.tag("recurse", do_recurse)

########NEW FILE########
__FILENAME__ = safecode
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright(C) 2008 SupDo.com
# Licensed under the GUN License, Version 3.0 (the "License");
#
# File:        safecode.py
# Author:      KuKei
# Create Date: 2008-07-16
# Description: Ë¥üË¥£È™åËØÅÁ†ÅÁîüÊàê„ÄÇ
# Modify Date: 2008-08-06

import hashlib
import random
from pngcanvas import PNGCanvas

class Image():
    text = None
    md5Text = None
    img = None
    width = 0
    height = 0
    #ÈïøÂ∫¶
    textX = 10
    textY = 10
    beginX = 5
    endX = 5
    beginY = 5
    endY = 5
    spare = 4

    def __init__(self,text=None):
        if(text==None):
            self.text = self.getRandom()
        else:
            self.text = text
        #self.getMd5Text()
        self.width = len(str(self.text))*(self.spare+self.textX)+self.beginX+self.endX
        self.height = self.textY + self.beginY + self.endY

    def create(self):
        self.img = PNGCanvas(self.width,self.height)
        self.img.color = [0xff,0xff,0xff,0xff]
        #self.img.color = [0x39,0x9e,0xff,0xff]
        #self.img.verticalGradient(1,1,self.width-2, self.height-2,[0xff,0,0,0xff],[0x60,0,0xff,0x80])
        self.img.verticalGradient(1,1,self.width-2, self.height-2,[0xff,0x45,0x45,0xff],[0xff,0xcb,0x44,0xff])

        for i in range(4):
            a = str(self.text)[i]
            self.writeText(a,i)

        return self.img.dump()

    def getRandom(self):
        intRand = random.randrange(1000,9999)
        return intRand

    def getMd5Text(self):
        m = md5.new()
        m.update(str(self.text))
        self.md5Text = m.hexdigest()

    def writeText(self,text,pos=0):
        if(text=="1"):
            self.writeLine(pos, "avc")
        elif(text=="2"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "hvtr")
            self.writeLine(pos, "ahc")
            self.writeLine(pos, "hvbl")
            self.writeLine(pos, "ahb")
        elif(text=="3"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "ahc")
            self.writeLine(pos, "ahb")
            self.writeLine(pos, "avr")
        elif(text=="4"):
            self.writeLine(pos, "hvtl")
            self.writeLine(pos, "ahc")
            self.writeLine(pos, "avc")
        elif(text=="5"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "hvtl")
            self.writeLine(pos, "ahc")
            self.writeLine(pos, "hvbr")
            self.writeLine(pos, "ahb")
        elif(text=="6"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "avl")
            self.writeLine(pos, "ahc")
            self.writeLine(pos, "hvbr")
            self.writeLine(pos, "ahb")
        elif(text=="7"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "avr")
        elif(text=="8"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "avl")
            self.writeLine(pos, "ahc")
            self.writeLine(pos, "avr")
            self.writeLine(pos, "ahb")
        elif(text=="9"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "avr")
            self.writeLine(pos, "ahc")
            self.writeLine(pos, "ahb")
            self.writeLine(pos, "hvtl")
        elif(text=="0"):
            self.writeLine(pos, "aht")
            self.writeLine(pos, "avl")
            self.writeLine(pos, "avr")
            self.writeLine(pos, "ahb")

    '''
    typeËß£Èáä
    a:ÂÖ®ÈÉ®,ÈÉ®ÂàÜ‰∏ä‰∏ã
    h:‰∏ÄÂçä
    h:Ê®™
    v:Á´ñ
    l:Â∑¶Ôºå‰∏ä
    c:‰∏≠Èó¥
    r:Âè≥Ôºå‰∏ã
    t:‰∏ä
    b:‰∏ã
    '''
    def writeLine(self,pos,type):
        if(type=="avl"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY,
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY+self.textY
                          )
        elif(type=="avc"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos+self.textX/2,
                          self.beginY,
                          self.beginX+(self.textX+self.spare)*pos+self.textX/2,
                          self.beginY+self.textY
                          )
        elif(type=="avr"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY,
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY+self.textY
                          )
        elif(type=="aht"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY,
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY,
                          )
        elif(type=="ahc"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY+self.textY/2,
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY+self.textY/2
                          )
        elif(type=="ahb"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY+self.textY,
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY+self.textY
                          )
        elif(type=="hvtl"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY,
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY+self.textY/2
                          )
        elif(type=="hvtr"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY,
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY+self.textY/2
                          )
        elif(type=="hvbl"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY+self.textY/2,
                          self.beginX+(self.textX+self.spare)*pos,
                          self.beginY+self.textY
                          )
        elif(type=="hvbr"):
            self.img.line(
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY+self.textY/2,
                          self.beginX+(self.textX+self.spare)*pos+self.textX,
                          self.beginY+self.textY
                          )


########NEW FILE########
__FILENAME__ = trackback
"""tblib.py: A Trackback (client) implementation in Python
"""
__author__ = "Matt Croydon <matt@ooiio.com>"
__copyright__ = "Copyright 2003, Matt Croydon"
__license__ = "GPL"
__version__ = "0.1.0"
__history__ = """
0.1.0: 1/29/03 - Code cleanup, release.  It can send pings, and autodiscover a URL to ping.
0.0.9: 1/29/03 - Basic error handling and autodiscovery works!
0.0.5: 1/29/03 - Internal development version.  Working on autodiscovery and error handling.
0.0.4: 1/22/03 - First public release, code cleanup.
0.0.3: 1/22/03 - Removed hard coding that was used for testing.
0.0.2: 1/21/03 - First working version.
0.0.1: 1/21/03 - Initial version.  Thanks to Mark Pilgrim for helping me figure some module basics out.
"""
import urllib, re
from google.appengine.api import urlfetch
import logging

class TrackBack:
    """
    Everything I needed to know about trackback I learned from the trackback tech specs page
    http://www.movabletype.org/docs/mttrackback.html.  All arguments are optional.  This allows us to create an empty TrackBack object,
    then use autodiscovery to populate its attributes.
    """

    def __init__(self, tbUrl=None, title=None, excerpt=None, url=None, blog_name=None):
        self.tbUrl = tbUrl
        self.title = title
        self.excerpt = excerpt
        self.url = url
        self.blog_name = blog_name
        self.tbErrorCode = None
        self.tbErrorMessage = None

    def ping(self):

        # Only execute if a trackback url has been defined.
        if self.tbUrl:
            # Create paramaters and make them play nice with HTTP
            # Python's httplib example helps a lot:
            # http://python.org/doc/current/lib/httplib-examples.html
            params = urllib.urlencode({'title': self.title, 'url': self.url, 'excerpt': self.excerpt, 'blog_name': self.blog_name})
            headers = ({"Content-type": "application/x-www-form-urlencoded",
            "User-Agent": "micolog"})
            # urlparse is my hero
            # http://www.python.org/doc/current/lib/module-urlparse.html
            logging.info("ping...%s",params)
            response=urlfetch.fetch(self.tbUrl,method=urlfetch.POST,payload=params,headers=headers)

            self.httpResponse = response.status_code
            data = response.content
            self.tbResponse = data
            logging.info("ping...%s"%data)
            # Thanks to Steve Holden's book: _Python Web Programming_ (http://pydish.holdenweb.com/pwp/)
            # Why parse really simple XML when you can just use regular expressions?  Rawk.
            errorpattern = r'<error>(.*?)</error>'
            reg = re.search(errorpattern, self.tbResponse)
            if reg:
                self.tbErrorCode = reg.group(1)
                if int(self.tbErrorCode) == 1:
                    errorpattern2 = r'<message>(.*?)</message>'
                    reg2 = re.search(errorpattern2, self.tbResponse)
                    if reg2:
                        self.tbErrorMessage = reg2.group(1)

        else:
            return 1

    def autodiscover(self, urlToCheck):

        response=urlfetch.fetch(urlToCheck)
        data = response.content
        tbpattern = r'trackback:ping="(.*?)"'
        reg = re.search(tbpattern, data)
        if reg:
            self.tbUrl = reg.group(1)
########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
import os,logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
import functools
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
##import app.webapp as webapp2
from django.template import TemplateDoesNotExist
from django.conf import settings
settings._target = None
#from model import g_blog,User
#activate(g_blog.language)
from google.appengine.api import taskqueue
from mimetypes import types_map
from datetime import datetime
import urllib
import traceback
import micolog_template


logging.info('module base reloaded')
def urldecode(value):
    return  urllib.unquote(urllib.unquote(value)).decode('utf8')
    #return  urllib.unquote(value).decode('utf8')

def urlencode(value):
    return urllib.quote(value.encode('utf8'))

def sid():
    now=datetime.datetime.now()
    return now.strftime('%y%m%d%H%M%S')+str(now.microsecond)


def requires_admin(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.is_login:
            self.redirect(users.create_login_url(self.request.uri))
            return
        elif not (self.is_admin
            or self.author):
            return self.error(403)
        else:
            return method(self, *args, **kwargs)
    return wrapper

def printinfo(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        print self #.__name__
        print dir(self)
        for x in self.__dict__:
            print x
        return method(self, *args, **kwargs)
    return wrapper
#only ajax methed allowed
def ajaxonly(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.request.headers["X-Requested-With"]=="XMLHttpRequest":
             self.error(404)
        else:
            return method(self, *args, **kwargs)
    return wrapper

#only request from same host can passed
def hostonly(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if  self.request.headers['Referer'].startswith(os.environ['HTTP_HOST'],7):
            return method(self, *args, **kwargs)
        else:
            self.error(404)
    return wrapper

def format_date(dt):
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def cache(key="",time=3600):
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            from model import g_blog
            if not g_blog.enable_memcache:
                method(*args, **kwargs)
                return

            request=args[0].request
            response=args[0].response
            skey=key+ request.path_qs
            #logging.info('skey:'+skey)
            html= memcache.get(skey)
            #arg[0] is BaseRequestHandler object

            if html:
                logging.info('cache:'+skey)
                response.last_modified =html[1]
                ilen=len(html)
                if ilen>=3:
                    response.set_status(html[2])
                if ilen>=4:
                    for skey,value in html[3].items():
                        response.headers[skey]=value
                response.out.write(html[0])
            else:
                if 'last-modified' not in response.headers:
                    response.last_modified = format_date(datetime.utcnow())

                method(*args, **kwargs)
                result=response.out.getvalue()
                status_code = response._Response__status[0]
                logging.debug("Cache:%s"%status_code)
                memcache.set(skey,(result,response.last_modified,status_code,response.headers),time)

        return _wrapper
    return _decorate

#-------------------------------------------------------------------------------
class PingbackError(Exception):
    """Raised if the remote server caused an exception while pingbacking.
    This is not raised if the pingback function is unable to locate a
    remote server.
    """

    _ = lambda x: x
    default_messages = {
        16: _(u'source URL does not exist'),
        17: _(u'The source URL does not contain a link to the target URL'),
        32: _(u'The specified target URL does not exist'),
        33: _(u'The specified target URL cannot be used as a target'),
        48: _(u'The pingback has already been registered'),
        49: _(u'Access Denied')
    }
    del _

    def __init__(self, fault_code, internal_message=None):
        Exception.__init__(self)
        self.fault_code = fault_code
        self._internal_message = internal_message

    def as_fault(self):
        """Return the pingback errors XMLRPC fault."""
        return Fault(self.fault_code, self.internal_message or
                     'unknown server error')

    @property
    def ignore_silently(self):
        """If the error can be ignored silently."""
        return self.fault_code in (17, 33, 48, 49)

    @property
    def means_missing(self):
        """If the error means that the resource is missing or not
        accepting pingbacks.
        """
        return self.fault_code in (32, 33)

    @property
    def internal_message(self):
        if self._internal_message is not None:
            return self._internal_message
        return self.default_messages.get(self.fault_code) or 'server error'

    @property
    def message(self):
        msg = self.default_messages.get(self.fault_code)
        if msg is not None:
            return _(msg)
        return _(u'An unknown server error (%s) occurred') % self.fault_code

class util:
    @classmethod
    def do_trackback(cls, tbUrl=None, title=None, excerpt=None, url=None, blog_name=None):
        taskqueue.add(url='/admin/do/trackback_ping',
            params={'tbUrl': tbUrl,'title':title,'excerpt':excerpt,'url':url,'blog_name':blog_name})

    #pingback ping
    @classmethod
    def do_pingback(cls,source_uri, target_uri):
        taskqueue.add(url='/admin/do/pingback_ping',
            params={'source': source_uri,'target':target_uri})



##cache variable

class Pager(object):

    def __init__(self, model=None,query=None, items_per_page=10):
        if model:
            self.query = model.all()
        else:
            self.query=query

        self.items_per_page = items_per_page

    def fetch(self, p):
        if hasattr(self.query,'__len__'):
            max_offset=len(self.query)
        else:
            max_offset = self.query.count()
        n = max_offset / self.items_per_page
        if max_offset % self.items_per_page:
            n += 1

        if p < 0 or p > n:
            p = 1
        offset = (p - 1) * self.items_per_page
        if hasattr(self.query,'fetch'):
            results = self.query.fetch(self.items_per_page, offset)
        else:
            results = self.query[offset:offset+self.items_per_page]



        links = {'count':max_offset,'page_index':p,'prev': p - 1, 'next': p + 1, 'last': n}
        if links['next'] > n:
            links['next'] = 0

        return (results, links)


class BaseRequestHandler(webapp.RequestHandler):
    def __init__(self):
        self.current='home'

##	def head(self, *args):
##		return self.get(*args)

    def initialize(self, request, response):
        webapp.RequestHandler.initialize(self, request, response)
        os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
        from model import g_blog,User
        self.blog = g_blog
        self.login_user = users.get_current_user()
        self.is_login = (self.login_user != None)
        self.loginurl=users.create_login_url(self.request.uri)
        self.logouturl=users.create_logout_url(self.request.uri)
        self.is_admin = users.is_current_user_admin()

        if self.is_admin:
            self.auth = 'admin'
            self.author=User.all().filter('email =',self.login_user.email()).get()
            if not self.author:
                self.author=User(dispname=self.login_user.nickname(),email=self.login_user.email())
                self.author.isadmin=True
                self.author.user=self.login_user
                self.author.put()
        elif self.is_login:
            self.author=User.all().filter('email =',self.login_user.email()).get()
            if self.author:
                self.auth='author'
            else:
                self.auth = 'login'
        else:
            self.auth = 'guest'

        try:
            self.referer = self.request.headers['referer']
        except:
            self.referer = None

        self.template_vals = {'self':self,'blog':self.blog,'current':self.current}

    def __before__(self,*args):
        pass

    def __after__(self,*args):
        pass

    def error(self,errorcode,message='an error occured'):
        if errorcode == 404:
            message = 'Sorry, we were not able to find the requested page.  We have logged this error and will look into it.'
        elif errorcode == 403:
            message = 'Sorry, that page is reserved for administrators.  '
        elif errorcode == 500:
            message = "Sorry, the server encountered an error.  We have logged this error and will look into it."

        message+="<p><pre>"+traceback.format_exc()+"</pre><br></p>"
        self.template_vals.update( {'errorcode':errorcode,'message':message})

        if errorcode>0:
            self.response.set_status(errorcode)


        #errorfile=getattr(self.blog.theme,'error'+str(errorcode))
        #logging.debug(errorfile)
##		if not errorfile:
##			errorfile=self.blog.theme.error
        errorfile='error'+str(errorcode)+".html"
        try:
            content=micolog_template.render(self.blog.theme,errorfile, self.template_vals)
        except TemplateDoesNotExist:
            try:
                content=micolog_template.render(self.blog.theme,"error.html", self.template_vals)
            except TemplateDoesNotExist:
                content=micolog_template.render(self.blog.default_theme,"error.html", self.template_vals)
        except:
            content=message
        self.response.out.write(content)

    def get_render(self,template_file,values):
        template_file=template_file+".html"
        self.template_vals.update(values)

        try:
            #sfile=getattr(self.blog.theme, template_file)
            logging.debug("get_render:"+template_file)
            html = micolog_template.render(self.blog.theme, template_file, self.template_vals)
        except TemplateDoesNotExist:
            #sfile=getattr(self.blog.default_theme, template_file)
            html = micolog_template.render(self.blog.default_theme, template_file, self.template_vals)

        return html

    def render(self,template_file,values):
        """
        Helper method to render the appropriate template
        """
        html=self.get_render(template_file,values)
        self.response.out.write(html)

    def message(self,msg,returl=None,title='Infomation'):
        self.render('msg',{'message':msg,'title':title,'returl':returl})

    def render2(self,template_file,template_vals={}):
        """
        Helper method to render the appropriate template
        """
        self.template_vals.update(template_vals)
        path = os.path.join(os.path.dirname(__file__), template_file)
        self.response.out.write(template.render(path, self.template_vals))

    def param(self, name, **kw):
        return self.request.get(name, **kw)

    def paramint(self, name, default=0):
        try:
           return int(self.request.get(name))
        except:
           return default

    def parambool(self, name, default=False):
        try:
           return self.request.get(name)=='on'
        except:
           return default

    def write(self, s):
        self.response.out.write(s)

    def chk_login(self, redirect_url='/'):
        if self.is_login:
            return True
        else:
            self.redirect(redirect_url)
            return False

    def chk_admin(self, redirect_url='/'):
        if self.is_admin:
            return True
        else:
            self.redirect(redirect_url)
            return False

########NEW FILE########
__FILENAME__ = blog
# -*- coding: utf-8 -*-
import cgi, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
import wsgiref.handlers

# Google App Engine imports.
##import app.webapp as webapp2

from datetime import timedelta
import random
from django.utils import simplejson
import app.filter as myfilter
from app.safecode import Image
from app.gmemsess import Session
from base import *
from model import *
from django.utils.translation import ugettext as _

##os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
##from django.utils.translation import  activate
##from django.conf import settings
##settings._target = None
##activate(g_blog.language)
from google.appengine.ext import zipserve

def doRequestHandle(old_handler,new_handler,**args):
        new_handler.initialize(old_handler.request,old_handler.response)
        return  new_handler.get(**args)

def doRequestPostHandle(old_handler,new_handler,**args):
        new_handler.initialize(old_handler.request,old_handler.response)
        return  new_handler.post(**args)

class BasePublicPage(BaseRequestHandler):
    def initialize(self, request, response):
        BaseRequestHandler.initialize(self,request, response)
        m_pages=Entry.all().filter('entrytype =','page')\
            .filter('published =',True)\
            .filter('entry_parent =',0)\
            .order('menu_order')
        blogroll=Link.all().filter('linktype =','blogroll')
        archives=Archive.all().order('-year').order('-month').fetch(12)
        alltags=Tag.all()
        self.template_vals.update(
            dict(menu_pages=m_pages, categories=Category.all(), blogroll=blogroll, archives=archives, alltags=alltags,
                 recent_comments=Comment.all().order('-date').fetch(5)))

    def m_list_pages(self):
        menu_pages=None
        entry=None
        if self.template_vals.has_key('menu_pages'):
            menu_pages= self.template_vals['menu_pages']
        if self.template_vals.has_key('entry'):
            entry=self.template_vals['entry']
        ret=''
        current=''
        for page in menu_pages:
            if entry and entry.entrytype=='page' and entry.key()==page.key():
                current= 'current_page_item'
            else:
                current= 'page_item'
            #page is external page ,and page.slug is none.
            if page.is_external_page and not page.slug:
                ret+='<li class="%s"><a href="%s" target="%s" >%s</a></li>'%( current,page.link,page.target, page.title)
            else:
                ret+='<li class="%s"><a href="/%s" target="%s">%s</a></li>'%( current,page.link, page.target,page.title)
        return ret

    def sticky_entrys(self):
        return Entry.all().filter('entrytype =','post')\
            .filter('published =',True)\
            .filter('sticky =',True)\
            .order('-date')

class MainPage(BasePublicPage):
    def head(self,page=1):
        if g_blog.allow_pingback :
            self.response.headers['X-Pingback']="%s/rpc"%str(g_blog.baseurl)
            
    def get(self,page=1):
        postid=self.param('p')
        if postid:
            try:
                postid=int(postid)
                return doRequestHandle(self,SinglePost(),postid=postid)  #singlepost.get(postid=postid)
            except:
                return self.error(404)
        if g_blog.allow_pingback :
            self.response.headers['X-Pingback']="%s/rpc"%str(g_blog.baseurl)
        self.doget(page)

    def post(self):
        postid=self.param('p')
        if postid:
            try:
                postid=int(postid)
                return doRequestPostHandle(self,SinglePost(),postid=postid)  #singlepost.get(postid=postid)
            except:
                return self.error(404)


    @cache()
    def doget(self,page):
        page=int(page)
        entrycount=g_blog.postscount()
        max_page = entrycount / g_blog.posts_per_page + ( entrycount % g_blog.posts_per_page and 1 or 0 )

        if page < 1 or page > max_page:
                return	self.error(404)

        entries = Entry.all().filter('entrytype =','post').\
                filter("published =", True).order('-sticky').order('-date').\
                fetch(self.blog.posts_per_page, offset = (page-1) * self.blog.posts_per_page)


        show_prev =entries and  (not (page == 1))
        show_next =entries and  (not (page == max_page))
        #print page,max_page,g_blog.entrycount,self.blog.posts_per_page

        return self.render('index',
                           dict(entries=entries, show_prev=show_prev, show_next=show_next, pageindex=page, ishome=True,
                                pagecount=max_page, postscounts=entrycount))

class entriesByCategory(BasePublicPage):
    @cache()
    def get(self,slug=None):
        if not slug:
            self.error(404)
            return

        try:
            page_index=int(self.param('page'))
        except:
            page_index=1

        slug=urldecode(slug)

        cats=Category.all().filter('slug =',slug).fetch(1)
        if cats:
            entries=Entry.all().filter("published =", True).filter('categorie_keys =',cats[0].key()).order("-date")
            entries,links=Pager(query=entries,items_per_page=20).fetch(page_index)
            self.render('category', dict(entries=entries, category=cats[0], pager=links))
        else:
            self.error(404,slug)

class archive_by_month(BasePublicPage):
    @cache()
    def get(self,year,month):
        try:
            page_index=int (self.param('page'))
        except:
            page_index=1

        firstday=datetime(int(year),int(month),1)
        if int(month)!=12:
            lastday=datetime(int(year),int(month)+1,1)
        else:
            lastday=datetime(int(year)+1,1,1)
        entries=db.GqlQuery("SELECT * FROM Entry WHERE date > :1 AND date <:2 AND entrytype =:3 AND published = True ORDER BY date DESC",firstday,lastday,'post')
        entries,links=Pager(query=entries).fetch(page_index)

        self.render('month', dict(entries=entries, year=year, month=month, pager=links))

class entriesByTag(BasePublicPage):
    @cache()
    def get(self,slug=None):
        if not slug:
             self.error(404)
             return
        try:
            page_index=int (self.param('page'))
        except:
            page_index=1
        slug=urldecode(slug)

        entries=Entry.all().filter("published =", True).filter('tags =',slug).order("-date")
        entries,links=Pager(query=entries,items_per_page=20).fetch(page_index)
        self.render('tag',{'entries':entries,'tag':slug,'pager':links})

class SinglePost(BasePublicPage):
    def head(self,slug=None,postid=None):
        if g_blog.allow_pingback :
            self.response.headers['X-Pingback']="%s/rpc"%str(g_blog.baseurl)

    @cache()
    def get(self,slug=None,postid=None):
        if postid:
            entries = Entry.all().filter("published =", True).filter('post_id =', postid).fetch(1)
        else:
            slug=urldecode(slug)
            entries = Entry.all().filter("published =", True).filter('link =', slug).fetch(1)
        if not entries or len(entries) == 0:
            return self.error(404)

        mp=self.paramint("mp",1)

        entry=entries[0]
        if entry.is_external_page:
            return self.redirect(entry.external_page_address,True)
        if g_blog.allow_pingback and entry.allow_trackback:
            self.response.headers['X-Pingback']="%s/rpc"%str(g_blog.baseurl)
        entry.readtimes += 1
        entry.put()
        self.entry=entry


        comments=entry.get_comments_by_page(mp,self.blog.comments_per_page)

##		commentuser=self.request.cookies.get('comment_user', '')
##		if commentuser:
##			commentuser=commentuser.split('#@#')
##		else:
        commentuser=['','','']

        comments_nav=self.get_comments_nav(mp,entry.purecomments().count())

        if entry.entrytype=='post':
            self.render('single',
                        dict(entry=entry, relateposts=entry.relateposts, comments=comments, user_name=commentuser[0],
                             user_email=commentuser[1], user_url=commentuser[2], checknum1=random.randint(1, 10),
                             checknum2=random.randint(1, 10), comments_nav=comments_nav))

        else:
            self.render('page',
                        dict(entry=entry, relateposts=entry.relateposts, comments=comments, user_name=commentuser[0],
                             user_email=commentuser[1], user_url=commentuser[2], checknum1=random.randint(1, 10),
                             checknum2=random.randint(1, 10), comments_nav=comments_nav))

    def post(self,slug=None,postid=None):
        '''handle trackback'''
        error = '''<?xml version="1.0" encoding="utf-8"?>
<response>
<error>1</error>
<message>%s</message>
</response>
'''
        success = '''<?xml version="1.0" encoding="utf-8"?>
<response>
<error>0</error>
</response>
'''

        if not g_blog.allow_trackback:
            self.response.out.write(error % "Trackback denied.")
            return
        self.response.headers['Content-Type'] = "text/xml"
        if postid:
            entries = Entry.all().filter("published =", True).filter('post_id =', postid).fetch(1)
        else:
            slug=urldecode(slug)
            entries = Entry.all().filter("published =", True).filter('link =', slug).fetch(1)

        if not entries or len(entries) == 0 :#or  (postid and not entries[0].link.endswith(g_blog.default_link_format%{'post_id':postid})):
            self.response.out.write(error % "empty slug/postid")
            return
        #check code ,rejest spam
        entry=entries[0]
        logging.info(self.request.remote_addr+self.request.path+" "+entry.trackbackurl)
        #key=self.param("code")
        #if (self.request.uri!=entry.trackbackurl) or entry.is_external_page or not entry.allow_trackback:
        #import cgi
        from urlparse import urlparse
        param=urlparse(self.request.uri)
        code=param[4]
        param=cgi.parse_qs(code)
        if param.has_key('code'):
            code=param['code'][0]

        if  (not str(entry.key())==code) or entry.is_external_page or not entry.allow_trackback:
            self.response.out.write(error % "Invalid trackback url.")
            return


        coming_url = self.param('url')
        blog_name = myfilter.do_filter(self.param('blog_name'))
        excerpt = myfilter.do_filter(self.param('excerpt'))
        title = myfilter.do_filter(self.param('title'))

        if not coming_url or not blog_name or not excerpt or not title:
            self.response.out.write(error % "not enough post info")
            return

        import time
        #wait for half second in case otherside hasn't been published
        time.sleep(0.5)

##		#also checking the coming url is valid and contains our link
##		#this is not standard trackback behavior
##		try:
##
##			result = urlfetch.fetch(coming_url)
##			if result.status_code != 200 :
##				#or ((g_blog.baseurl + '/' + slug) not in result.content.decode('ascii','ignore')):
##				self.response.out.write(error % "probably spam")
##				return
##		except Exception, e:
##			logging.info("urlfetch error")
##			self.response.out.write(error % "urlfetch error")
##			return

        comment = Comment.all().filter("entry =", entry).filter("weburl =", coming_url).get()
        if comment:
            self.response.out.write(error % "has pinged before")
            return

        comment=Comment(author=blog_name,
                content="...<strong>"+title[:250]+"</strong> " +
                        excerpt[:250] + '...',
                weburl=coming_url,
                entry=entry)

        comment.ip=self.request.remote_addr
        comment.ctype=COMMENT_TRACKBACK
        try:
            comment.save()

            memcache.delete("/"+entry.link)
            self.write(success)
            g_blog.tigger_action("pingback_post",comment)
        except:
            self.response.out.write(error % "unknow error")

    def get_comments_nav(self,pindex,count):
        maxpage=count / g_blog.comments_per_page + ( count % g_blog.comments_per_page and 1 or 0 )
        if maxpage==1:
            return {'nav':"",'current':pindex}

        result=""

        if pindex>1:
            result="<a class='comment_prev' href='"+self.get_comments_pagenum_link(pindex-1)+"'>¬´</a>"

        minr=max(pindex-3,1)
        maxr=min(pindex+3,maxpage)
        if minr>2:
            result+="<a class='comment_num' href='"+self.get_comments_pagenum_link(1)+"'>1</a>"
            result+="<span class='comment_dot' >...</span>"

        for n in range(minr,maxr+1):
            if n==pindex:
                result+="<span class='comment_current'>"+str(n)+"</span>"
            else:
                result+="<a class='comment_num' href='"+self.get_comments_pagenum_link(n)+"'>"+str(n)+"</a>"
        if maxr<maxpage-1:
            result+="<span class='comment_dot' >...</span>"
            result+="<a class='comment_num' href='"+self.get_comments_pagenum_link(maxpage)+"'>"+str(maxpage)+"</a>"

        if pindex<maxpage:
            result+="<a class='comment_next' href='"+self.get_comments_pagenum_link(pindex+1)+"'>¬ª</a>"

        return {'nav':result,'current':pindex,'maxpage':maxpage}

    def get_comments_pagenum_link(self,pindex):
        url=str(self.entry.link)
        if url.find('?')>=0:
            return "/"+url+"&mp="+str(pindex)+"#comments"
        else:
            return "/"+url+"?mp="+str(pindex)+"#comments"

class FeedHandler(BaseRequestHandler):
    @cache(time=600)
    def get(self,tags=None):
        entries = Entry.all().filter('entrytype =','post').filter('published =',True).order('-date').fetch(10)
        if entries and entries[0]:
            last_updated = entries[0].date
            last_updated = last_updated.strftime("%a, %d %b %Y %H:%M:%S +0000")
        for e in entries:
            e.formatted_date = e.date.strftime("%a, %d %b %Y %H:%M:%S +0000")
        self.response.headers['Content-Type'] = 'application/rss+xml; charset=utf-8'
        self.render2('views/rss.xml',{'entries':entries,'last_updated':last_updated})

class CommentsFeedHandler(BaseRequestHandler):
    @cache(time=600)
    def get(self,tags=None):
        comments = Comment.all().order('-date').filter('ctype =',0).fetch(10)
        if comments and comments[0]:
            last_updated = comments[0].date
            last_updated = last_updated.strftime("%a, %d %b %Y %H:%M:%S +0000")
        for e in comments:
            e.formatted_date = e.date.strftime("%a, %d %b %Y %H:%M:%S +0000")
        self.response.headers['Content-Type'] = 'application/rss+xml; charset=UTF-8'
        self.render2('views/comments.xml',{'comments':comments,'last_updated':last_updated})

class SitemapHandler(BaseRequestHandler):
    @cache(time=36000)
    def get(self,tags=None):
        urls = []
        def addurl(loc,lastmod=None,changefreq=None,priority=None):
            url_info = {
                'location':   loc,
                'lastmod':	lastmod,
                'changefreq': changefreq,
                'priority':   priority
            }
            urls.append(url_info)

        addurl(g_blog.baseurl,changefreq='daily',priority=0.9 )

        entries = Entry.all().filter('published =',True).order('-date').fetch(g_blog.sitemap_entries)

        for item in entries:
            loc = "%s/%s" % (g_blog.baseurl, item.link)
            addurl(loc,item.mod_date or item.date,'never',0.6)

        if g_blog.sitemap_include_category:
            cats=Category.all()
            for cat in cats:
                loc="%s/category/%s"%(g_blog.baseurl,cat.slug)
                addurl(loc,None,'weekly',0.5)

        if g_blog.sitemap_include_tag:
            tags=Tag.all()
            for tag in tags:
                loc="%s/tag/%s"%(g_blog.baseurl, urlencode(tag.tag))
                addurl(loc,None,'weekly',0.5)


##		self.response.headers['Content-Type'] = 'application/atom+xml'
        self.render2('views/sitemap.xml',{'urlset':urls})


class Error404(BaseRequestHandler):
    @cache(time=36000)
    def get(self,slug=None):
        self.error(404)

class Post_comment(BaseRequestHandler):
    #@printinfo
    def post(self,slug=None):
        useajax=self.param('useajax')=='1'

        name=self.param('author')
        email=self.param('email')
        url=self.param('url')

        key=self.param('key')
        content=self.param('comment')
        parent_id=self.paramint('parentid',0)
        reply_notify_mail=self.parambool('reply_notify_mail')

        sess=Session(self,timeout=180)
        if not self.is_login:
            #if not (self.request.cookies.get('comment_user', '')):
            try:
                check_ret=True
                if g_blog.comment_check_type in (1,2)  :
                    checkret=self.param('checkret')
                    check_ret=(int(checkret) == sess['code'])
                elif  g_blog.comment_check_type ==3:
                    import app.gbtools as gb
                    checknum=self.param('checknum')
                    checkret=self.param('checkret')
                    check_ret=eval(checknum)==int(gb.stringQ2B( checkret))

                if not check_ret:
                    if useajax:
                        self.write(simplejson.dumps((False,-102,_('Your check code is invalid .')),ensure_ascii = False))
                    else:
                        self.error(-102,_('Your check code is invalid .'))
                    return
            except:
                if useajax:
                    self.write(simplejson.dumps((False,-102,_('Your check code is invalid .')),ensure_ascii = False))
                else:
                    self.error(-102,_('Your check code is invalid .'))
                return

        sess.invalidate()
        content=content.replace('\n','<br />')
        content=myfilter.do_filter(content)
        name=cgi.escape(name)[:20]
        url=cgi.escape(url)[:100]

        if not (name and email and content):
            if useajax:
                        self.write(simplejson.dumps((False,-101,_('Please input name, email and comment .'))))
            else:
                self.error(-101,_('Please input name, email and comment .'))
        else:
            comment=Comment(author=name,
                            content=content,
                            email=email,
                            reply_notify_mail=reply_notify_mail,
                            entry=Entry.get(key))
            if url:
                try:
                    if not url.lower().startswith(('http://','https://')):
                        url = 'http://' + url
                    comment.weburl=url
                except:
                    comment.weburl=None

            #name=name.decode('utf8').encode('gb2312')

            info_str='#@#'.join([urlencode(name),urlencode(email),urlencode(url)])

             #info_str='#@#'.join([name,email,url.encode('utf8')])
            cookiestr='comment_user=%s;expires=%s;path=/;'%( info_str,
                       (datetime.now()+timedelta(days=100)).strftime("%a, %d-%b-%Y %H:%M:%S GMT")
                       )
            comment.ip=self.request.remote_addr

            if parent_id:
                comment.parent=Comment.get_by_id(parent_id)

            comment.no=comment.entry.commentcount+1
            try:
                comment.save()
                memcache.delete("/"+comment.entry.link)

                self.response.headers.add_header( 'Set-Cookie', cookiestr)
                if useajax:
                    comment_c=self.get_render('comment',{'comment':comment})
                    self.write(simplejson.dumps((True,comment_c.decode('utf8')),ensure_ascii = False))
                else:
                    self.redirect(self.referer+"#comment-"+str(comment.key().id()))

                comment.entry.removecache()
                memcache.delete("/feed/comments")
            except:
                if useajax:
                    self.write(simplejson.dumps((False,-102,_('Comment not allowed.'))))
                else:
                    self.error(-102,_('Comment not allowed .'))

class ChangeTheme(BaseRequestHandler):
    @requires_admin
    def get(self,slug=None):
       theme=self.param('t')
       g_blog.theme_name=theme
       g_blog.get_theme()
       self.redirect('/')


class do_action(BaseRequestHandler):
    def get(self,slug=None):

        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.error(404)
        except BaseException,e:
            self.error(404)

    def post(self,slug=None):
        try:
            func=getattr(self,'action_'+slug)
            if func and callable(func):
                func()
            else:
                self.error(404)
        except:
             self.error(404)

    @ajaxonly
    def action_info_login(self):
        if self.login_user:
            self.write(simplejson.dumps({'islogin':True,
                                         'isadmin':self.is_admin,
                                         'name': self.login_user.nickname()}))
        else:
            self.write(simplejson.dumps({'islogin':False}))

    #@hostonly
    @cache()
    def action_proxy(self):
        result=urlfetch.fetch(self.param("url"), headers=self.request.headers)
        if result.status_code == 200:
            self.response.headers['Expires'] = 'Thu, 15 Apr 3010 20:00:00 GMT'
            self.response.headers['Cache-Control'] = 'max-age=3600,public'
            self.response.headers['Content-Type'] = result.headers['Content-Type']
            self.response.out.write(result.content)
        return

    def action_getcomments(self):
        key=self.param('key')
        entry=Entry.get(key)
        comments=Comment.all().filter("entry =",key)

        commentuser=self.request.cookies.get('comment_user', '')
        if commentuser:
            commentuser=commentuser.split('#@#')
        else:
            commentuser=['','','']


        vals= dict(entry=entry, comments=comments, user_name=commentuser[0], user_email=commentuser[1],
                   user_url=commentuser[2], checknum1=random.randint(1, 10), checknum2=random.randint(1, 10))
        html=self.get_render('comments',vals)

        self.write(simplejson.dumps(html.decode('utf8')))

    def action_test(self):
        self.write(settings.LANGUAGE_CODE)
        self.write(_("this is a test"))


class getMedia(webapp.RequestHandler):
    def get(self,slug):
        media=Media.get(slug)
        if media:
            self.response.headers['Expires'] = 'Thu, 15 Apr 3010 20:00:00 GMT'
            self.response.headers['Cache-Control'] = 'max-age=3600,public'
            self.response.headers['Content-Type'] = str(media.mtype)
            self.response.out.write(media.bits)
            a=self.request.get('a')
            if a and a.lower()=='download':
                media.download+=1
                media.put()



class CheckImg(BaseRequestHandler):
    def get(self):
        img = Image()
        imgdata = img.create()
        sess=Session(self,timeout=900)
        if not sess.is_new():
            sess.invalidate()
            sess=Session(self,timeout=900)
        sess['code']=img.text
        sess.save()
        self.response.headers['Content-Type'] = "image/png"
        self.response.out.write(imgdata)


class CheckCode(BaseRequestHandler):
    def get(self):
        sess=Session(self,timeout=900)
        num1=random.randint(30,50)
        num2=random.randint(1,10)
        code="<span style='font-size:12px;color:red'>%d - %d =</span>"%(num1,num2)
        sess['code']=num1-num2
        sess.save()
        #self.response.headers['Content-Type'] = "text/html"
        self.response.out.write(code)

class Other(BaseRequestHandler):
    def get(self,slug=None):
        if not g_blog.tigger_urlmap(slug,page=self):
            self.error(404)

    def post(self,slug=None):
        content=g_blog.tigger_urlmap(slug,page=self)
        if content:
            self.write(content)
        else:
            self.error(404)

def getZipHandler(**args):
    return ('/xheditor/(.*)',zipserve.make_zip_handler('''D:\\Projects\\eric-guo\\plugins\\xheditor\\xheditor.zip'''))

def main():
    webapp.template.register_template_library('app.filter')
    webapp.template.register_template_library('app.recurse')
    urls=	[('/media/([^/]*)/{0,1}.*',getMedia),
            ('/checkimg/', CheckImg),
            ('/checkcode/', CheckCode),
            ('/skin',ChangeTheme),
            ('/feed', FeedHandler),
            ('/feed/comments',CommentsFeedHandler),
            ('/sitemap', SitemapHandler),
            ('/sitemap\.xml', SitemapHandler),
            ('/post_comment',Post_comment),
            ('/page/(?P<page>\d+)', MainPage),
            ('/category/(.*)',entriesByCategory),
            ('/(\d{4})/(\d{1,2})',archive_by_month),
            ('/tag/(.*)',entriesByTag),
            #('/\?p=(?P<postid>\d+)',SinglePost),
            ('/', MainPage),
            ('/do/(\w+)', do_action),
            ('/e/(.*)',Other),
            ('/([\\w\\-\\./%]+)', SinglePost),
            ('.*',Error404),
            ]
    application = webapp.WSGIApplication(urls)
    g_blog.application=application
    g_blog.plugins.register_handlerlist(application)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
    main()
########NEW FILE########
__FILENAME__ = micolog_plugin
import os,logging,re
from model import OptionSet
from google.appengine.ext.webapp import template
from google.appengine.ext import zipserve
RE_FIND_GROUPS = re.compile('\(.*?\)')

class PluginIterator:
	def __init__(self, plugins_path='plugins'):
		self.iterating = False
		self.plugins_path = plugins_path
		self.list = []
		self.cursor = 0

	def __iter__(self):
		return self

	def next(self):
		if not self.iterating:
			self.iterating = True
			self.list = os.listdir(self.plugins_path)
			self.cursor = 0

		if self.cursor >= len(self.list):
			self.iterating = False
			raise StopIteration
		else:
			value = self.list[self.cursor]
			self.cursor += 1
			if os.path.isdir(os.path.join(self.plugins_path, value)):
				return value,'%s.%s.%s'%(self.plugins_path,value,value)
			elif value.endswith('.py') and not value=='__init__.py':
				value=value[:-3]
				return value,'%s.%s'%(self.plugins_path,value)
			else:
				return self.next()

class Plugins:
	def __init__(self,blog=None):
		self.blog=blog
		self.list={}
		self._filter_plugins={}
		self._action_plugins={}
		self._urlmap={}
		self._handlerlist={}
		self._setupmenu=[]
		pi=PluginIterator()
		self.active_list=OptionSet.getValue("PluginActive",[])
		for v,m in pi:
			try:
				#import plugins modules
				mod=__import__(m,globals(),locals(),[v])
				plugin=getattr(mod,v)()
				#internal name
				plugin.iname=v
				plugin.active=v in self.active_list
				plugin.blog=self.blog
				self.list[v]=plugin
			except:
				pass

	def add_urlhandler(self,plugin,application):
		for regexp,handler in plugin._handlerlist.items():
			try:
				application._handler_map[handler.__name__] = handler
				if not regexp.startswith('^'):
					regexp = '^' + regexp
				if not regexp.endswith('$'):
					regexp += '$'
				compiled = re.compile(regexp)
				application._url_mapping.insert(-2,(compiled, handler))

				num_groups = len(RE_FIND_GROUPS.findall(regexp))
				handler_patterns = application._pattern_map.setdefault(handler, [])
				handler_patterns.insert(-2,(compiled, num_groups))
			except:
				pass

	def remove_urlhandler(self,plugin,application):
		for regexp,handler in plugin._handlerlist.items():
			try:
				if application._handler_map.has_key(handler.__name__):
					del application._handler_map[handler.__name__]
					for um in application._url_mapping:
						if um[1].__name__==handler.__name__:
							del um
							break
					for pm in application._pattern_map:
						if pm.__name__==handler.__name__:
							del pm
							break

			except:
				pass

	def register_handlerlist(self,application):
		for name,item in self.list.items():
			if item.active and item._handlerlist:
				self.add_urlhandler(item,application)


	def reload(self):
		pass

	def __getitem__(self,index):
		return self.list.values()[index]

	def getPluginByName(self,iname):
		if self.list.has_key(iname):
			return self.list[iname]
		else:
			return None

	def activate(self,iname,active):
		if active:
			plugin=self.getPluginByName(iname)
			if plugin:
				if iname not in self.active_list:
					self.active_list.append(iname)
					OptionSet.setValue("PluginActive",self.active_list)
				plugin.active=active
				#add filter
				for k,v in plugin._filter.items():
					if self._filter_plugins.has_key(k):
						if not v in self._filter_plugins[k]:
							self._filter_plugins[k].append(v)
				#add action
				for k,v in plugin._action.items():
					if self._action_plugins.has_key(k):
						if not v in self._action_plugins[k]:
							self._action_plugins[k].append(v)
				if self.blog.application:
					self.add_urlhandler(plugin,self.blog.application)

		else:
			plugin=self.getPluginByName(iname)
			if plugin:
				if iname in self.active_list:
					self.active_list.remove(iname)
					OptionSet.setValue("PluginActive",self.active_list)
				plugin.active=active
				#remove filter
				for k,v in plugin._filter.items():
					if self._filter_plugins.has_key(k):
						if v in self._filter_plugins[k]:
							self._filter_plugins[k].remove(v)
				#remove action
				for k,v in plugin._action.items():
					if self._action_plugins.has_key(k):
						if v in self._action_plugins[k]:
							self._action_plugins[k].remove(v)
				if self.blog.application:
					self.remove_urlhandler(plugin,self.blog.application)
		self._urlmap={}
		self._setupmenu=[]


	def filter(self,attr,value):
		rlist=[]
		for item in self:
			if item.active and hasattr(item,attr) and getattr(item,attr)==value:
				rlist.append(item)
		return rlist

	def get_filter_plugins(self,name):
		if not self._filter_plugins.has_key(name) :
			for item in self:
				if item.active and hasattr(item,"_filter") :
					if item._filter.has_key(name):
						if	self._filter_plugins.has_key(name):
							self._filter_plugins[name].append(item._filter[name])
						else:
							self._filter_plugins[name]=[item._filter[name]]



		if self._filter_plugins.has_key(name):
			return tuple(self._filter_plugins[name])
		else:
			return ()

	def get_action_plugins(self,name):
		if not self._action_plugins.has_key(name) :
			for item in self:
				if item.active and hasattr(item,"_action") :
					if item._action.has_key(name):
						if	self._action_plugins.has_key(name):
							self._action_plugins[name].append(item._action[name])
						else:
							self._action_plugins[name]=[item._action[name]]

		if self._action_plugins.has_key(name):
			return tuple(self._action_plugins[name])
		else:
			return ()

	def get_urlmap_func(self,url):
		if not self._urlmap:
			for item in self:
				if item.active:
					self._urlmap.update(item._urlmap)
		if self._urlmap.has_key(url):
			return self._urlmap[url]
		else:
			return None
	
	def get_setupmenu(self):
		#Get menu list for admin setup page
		if not self._setupmenu:
			for item in self:
				if item.active:
					self._setupmenu+=item._setupmenu
		return self._setupmenu	

	def get_handlerlist(self,url):
		if not self._handlerlist:
			for item in self:
				if item.active:
					self._handlerlist.update(item._handlerlist)
		if self._handlerlist.has_key(url):
			return self._handlerlist[url]
		else:
			return {}

	def tigger_filter(self,name,content,*arg1,**arg2):
		for func in self.get_filter_plugins(name):
			content=func(content,*arg1,**arg2)
		return content

	def tigger_action(self,name,*arg1,**arg2):
		for func in self.get_action_plugins(name):
			func(*arg1,**arg2)

	def tigger_urlmap(self,url,*arg1,**arg2):
		func=self.get_urlmap_func(url)
		if func:
			func(*arg1,**arg2)
			return True
		else:
			return None

class Plugin:
	def __init__(self,pfile=__file__):
		self.name="Unnamed"
		self.author=""
		self.description=""
		self.uri=""
		self.version=""
		self.authoruri=""
		self.template_vals={}
		self.dir=os.path.dirname(pfile)
		self._filter={}
		self._action={}
		self._urlmap={}
		self._handlerlist={}
		self._urlhandler={}
		self._setupmenu=[]

	def get(self,page):
		return "<h3>%s</h3><p>%s</p>"%(self.name,self.description)

	def render_content(self,template_file,template_vals={}):
		"""
		Helper method to render the appropriate template
		"""
		self.template_vals.update(template_vals)
		path = os.path.join(self.dir, template_file)
		return template.render(path, self.template_vals)

	def error(self,msg=""):
		return  "<h3>Error:%s</h3>"%msg

	def register_filter(self,name,func):
		self._filter[name]=func

	def register_action(self,name,func):
		self._action[name]=func

	def register_urlmap(self,url,func):
		self._urlmap[url]=func

	def register_urlhandler(self,url,handler):
		self._handlerlist[url]=handler

	def register_urlzip(self,name,zipfile):
		zipfile=os.path.join(self.dir,zipfile)
		self._handlerlist[name]=zipserve.make_zip_handler(zipfile)
		
	def register_setupmenu(self,m_id,title,url):
		#Add menu to admin setup page.
		#m_id is a flag to check current page
		self._setupmenu.append({'m_id':m_id,'title':title,'url':url})


class Plugin_importbase(Plugin):
	def __init__(self,pfile,name,description=""):
		Plugin.__init__(self,pfile)
		self.is_import_plugin=True
		self.import_name=name
		self.import_description=description

	def post(self):
		pass


########NEW FILE########
__FILENAME__ = micolog_template
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	 http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""A simple wrapper for Django templates.

The main purpose of this module is to hide all of the package import pain
you normally have to go through to get Django to work. We expose the Django
Template and Context classes from this module, handling the import nonsense
on behalf of clients.

Typical usage:

   from google.appengine.ext.webapp import template
   print template.render('templates/index.html', {'foo': 'bar'})

Django uses a global setting for the directory in which it looks for templates.
This is not natural in the context of the webapp module, so our load method
takes in a complete template path, and we set these settings on the fly
automatically.  Because we have to set and use a global setting on every
method call, this module is not thread safe, though that is not an issue
for applications.

Django template documentation is available at:
http://www.djangoproject.com/documentation/templates/
"""





import hashlib
import os,logging
from google.appengine.dist import use_library
use_library('django', '1.2')
import django

import django.conf
try:
  django.conf.settings.configure(
    DEBUG=False,
    TEMPLATE_DEBUG=False,
    TEMPLATE_LOADERS=(
      'django.template.loaders.filesystem.load_template_source',
    ),
  )
except (EnvironmentError, RuntimeError):
  pass
import django.template
import django.template.loader

from google.appengine.ext import webapp

def render(theme,template_file, template_dict, debug=False):
  """Renders the template at the given path with the given dict of values.

  Example usage:
    render("templates/index.html", {"name": "Bret", "values": [1, 2, 3]})

  Args:
    template_path: path to a Django template
    template_dict: dictionary of values to apply to the template
  """
  t = load(theme,template_file, debug)
  return t.render(Context(template_dict))


template_cache = {}

def load(theme,template_file, debug=False):
  """Loads the Django template from the given path.

  It is better to use this function than to construct a Template using the
  class below because Django requires you to load the template with a method
  if you want imports and extends to work in the template.
  """
  #template_file=os.path.join("templates",template_file)
  if theme.isZip:
    theme_path=theme.server_dir
  else:
    theme_path=os.path.join( theme.server_dir,"templates")

  abspath =os.path.join( theme_path,template_file)
  logging.debug("theme_path:%s,abspath:%s"%(theme_path,abspath))

  if not debug:
    template = template_cache.get(abspath)
  else:
    template = None

  if not template:
    #file_name = os.path.split(abspath)
    new_settings = {
        'TEMPLATE_DIRS': (theme_path,),
        'TEMPLATE_DEBUG': debug,
        'DEBUG': debug,
        }
    old_settings = _swap_settings(new_settings)
    try:
      template = django.template.loader.get_template(template_file)
    finally:
        _swap_settings(old_settings)

    if not debug:
      template_cache[abspath] = template

    def wrap_render(context, orig_render=template.render):
      URLNode = django.template.defaulttags.URLNode
      save_urlnode_render = URLNode.render
      old_settings = _swap_settings(new_settings)
      try:
        URLNode.render = _urlnode_render_replacement
        return orig_render(context)
      finally:
        _swap_settings(old_settings)
        URLNode.render = save_urlnode_render

    template.render = wrap_render

  return template


def _swap_settings(new):
  """Swap in selected Django settings, returning old settings.

  Example:
    save = _swap_settings({'X': 1, 'Y': 2})
    try:
      ...new settings for X and Y are in effect here...
    finally:
      _swap_settings(save)

  Args:
    new: A dict containing settings to change; the keys should
      be setting names and the values settings values.

  Returns:
    Another dict structured the same was as the argument containing
    the original settings.  Original settings that were not set at all
    are returned as None, and will be restored as None by the
    'finally' clause in the example above.  This shouldn't matter; we
    can't delete settings that are given as None, since None is also a
    legitimate value for some settings.  Creating a separate flag value
    for 'unset' settings seems overkill as there is no known use case.
  """
  settings = django.conf.settings
  old = {}
  for key, value in new.iteritems():
    old[key] = getattr(settings, key, None)
    setattr(settings, key, value)
  return old


def create_template_register():
  """Used to extend the Django template library with custom filters and tags.

  To extend the template library with a custom filter module, create a Python
  module, and create a module-level variable named "register", and register
  all custom filters to it as described at
  http://www.djangoproject.com/documentation/templates_python/
    #extending-the-template-system:

    templatefilters.py
    ==================
    register = webapp.template.create_template_register()

    def cut(value, arg):
      return value.replace(arg, '')
    register.filter(cut)

  Then, register the custom template module with the register_template_library
  function below in your application module:

    myapp.py
    ========
    webapp.template.register_template_library('templatefilters')
  """
  return django.template.Library()


def register_template_library(package_name):
  """Registers a template extension module to make it usable in templates.

  See the documentation for create_template_register for more information."""
  if not django.template.libraries.get(package_name):
    django.template.add_to_builtins(package_name)


Template = django.template.Template
Context = django.template.Context


def _urlnode_render_replacement(self, context):
  """Replacement for django's {% url %} block.

  This version uses WSGIApplication's url mapping to create urls.

  Examples:

  <a href="{% url MyPageHandler "overview" %}">
  {% url MyPageHandler implicit_args=False %}
  {% url MyPageHandler "calendar" %}
  {% url MyPageHandler "jsmith","calendar" %}
  """
  args = [arg.resolve(context) for arg in self.args]
  try:
    app = webapp.WSGIApplication.active_instance
    handler = app.get_registered_handler_by_name(self.view_name)
    return handler.get_url(implicit_args=True, *args)
  except webapp.NoUrlFoundError:
    return ''

########NEW FILE########
__FILENAME__ = model
Ôªø# -*- coding: utf-8 -*-
import os,logging
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from google.appengine.ext import db
from google.appengine.ext.db import Model as DBModel
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import datastore
from datetime import datetime
import urllib, hashlib,urlparse
import re,pickle
logging.info('module base reloaded')
from django.utils.translation import ugettext as _
rootpath=os.path.dirname(__file__)

def vcache(key="",time=3600):
    def _decorate(method):
        def _wrapper(*args, **kwargs):
            if not g_blog.enable_memcache:
                return method(*args, **kwargs)
            result=method(*args, **kwargs)
            memcache.set(key,result,time)
            return result
        return _wrapper
    return _decorate

class Theme:
    def __init__(self, name='default'):
        self.name = name
        self.mapping_cache = {}
        self.dir = '/themes/%s' % name
        self.viewdir=os.path.join(rootpath, 'view')
        self.server_dir = os.path.join(rootpath, 'themes',self.name)
        if os.path.exists(self.server_dir):
            self.isZip=False
        else:
            self.isZip=True
            self.server_dir += ".zip"
        #self.server_dir=os.path.join(self.server_dir,"templates")
        logging.debug('server_dir:%s'%self.server_dir)

    def __getattr__(self, name):
        if self.mapping_cache.has_key(name):
            return self.mapping_cache[name]
        else:
            path ="/".join((self.name,'templates', name + '.html'))
            logging.debug('path:%s'%path)
##			if not os.path.exists(path):
##				path = os.path.join(rootpath, 'themes', 'default', 'templates', name + '.html')
##				if not os.path.exists(path):
##					path = None
            self.mapping_cache[name]=path
            return path

class ThemeIterator:
    def __init__(self, theme_path='themes'):
        self.iterating = False
        self.theme_path = theme_path
        self.list = []

    def __iter__(self):
        return self

    def next(self):
        if not self.iterating:
            self.iterating = True
            self.list = os.listdir(self.theme_path)
            self.cursor = 0

        if self.cursor >= len(self.list):
            self.iterating = False
            raise StopIteration
        else:
            value = self.list[self.cursor]
            self.cursor += 1
            if value.endswith('.zip'):
                value=value[:-4]
            return value
            #return (str(value), unicode(value))

class LangIterator:
    def __init__(self,path='locale'):
        self.iterating = False
        self.path = path
        self.list = []
        for value in  os.listdir(self.path):
                if os.path.isdir(os.path.join(self.path,value)):
                    if os.path.exists(os.path.join(self.path,value,'LC_MESSAGES')):
                        try:
                            lang=open(os.path.join(self.path,value,'language')).readline()
                            self.list.append({'code':value,'lang':lang})
                        except:
                            self.list.append({'code':value,'lang':value})

    def __iter__(self):
        return self

    def next(self):
        if not self.iterating:
            self.iterating = True
            self.cursor = 0

        if self.cursor >= len(self.list):
            self.iterating = False
            raise StopIteration
        else:
            value = self.list[self.cursor]
            self.cursor += 1
            return value

    def getlang(self,language):
        from django.utils.translation import  to_locale
        for item in self.list:
            if item['code']==language or item['code']==to_locale(language):
                return item
        return {'code':'en_US','lang':'English'}

class BaseModel(db.Model):
    def __init__(self, parent=None, key_name=None, _app=None, **kwds):
        self.__isdirty = False
        DBModel.__init__(self, parent=None, key_name=None, _app=None, **kwds)

    def __setattr__(self,attrname,value):
        """
        DataStore api stores all prop values say "email" is stored in "_email" so
        we intercept the set attribute, see if it has changed, then check for an
        onchanged method for that property to call
        """
        if attrname.find('_') != 0:
            if hasattr(self,'_' + attrname):
                curval = getattr(self,'_' + attrname)
                if curval != value:
                    self.__isdirty = True
                    if hasattr(self,attrname + '_onchange'):
                        getattr(self,attrname + '_onchange')(curval,value)
        DBModel.__setattr__(self,attrname,value)

class Cache(db.Model):
    cachekey = db.StringProperty()
    content = db.TextProperty()

class Blog(db.Model):
    owner = db.UserProperty()
    author=db.StringProperty(default='admin')
    rpcuser=db.StringProperty(default='admin')
    rpcpassword=db.StringProperty(default='')
    description = db.TextProperty()
    baseurl = db.StringProperty(default=None)
    urlpath = db.StringProperty()
    title = db.StringProperty(default='Micolog')
    subtitle = db.StringProperty(default='This is a micro blog.')
    entrycount = db.IntegerProperty(default=0)
    posts_per_page= db.IntegerProperty(default=10)
    feedurl = db.StringProperty(default='/feed')
    blogversion = db.StringProperty(default='0.30')
    theme_name = db.StringProperty(default='default')
    enable_memcache = db.BooleanProperty(default = False)
    link_format=db.StringProperty(default='%(year)s/%(month)s/%(day)s/%(postname)s.html')
    comment_notify_mail=db.BooleanProperty(default=True)
    #ËØÑËÆ∫È°∫Â∫è
    comments_order=db.IntegerProperty(default=0)
    #ÊØèÈ°µËØÑËÆ∫Êï∞
    comments_per_page=db.IntegerProperty(default=20)
    #comment check type 0-No 1-ÁÆóÊúØ 2-È™åËØÅÁ†Å 3-ÂÆ¢Êà∑Á´ØËÆ°ÁÆó
    comment_check_type=db.IntegerProperty(default=1)
    #0 default 1 identicon
    avatar_style=db.IntegerProperty(default=0)
    blognotice=db.TextProperty(default='')
    domain=db.StringProperty()
    show_excerpt=db.BooleanProperty(default=True)
    version=0.743
    timedelta=db.FloatProperty(default=8.0)# hours
    language=db.StringProperty(default="en-us")
    sitemap_entries=db.IntegerProperty(default=30)
    sitemap_include_category=db.BooleanProperty(default=False)
    sitemap_include_tag=db.BooleanProperty(default=False)
    sitemap_ping=db.BooleanProperty(default=False)
    default_link_format=db.StringProperty(default='?p=%(post_id)s')
    default_theme=Theme()
    allow_pingback=db.BooleanProperty(default=False)
    allow_trackback=db.BooleanProperty(default=False)
    admin_essential=db.BooleanProperty(default=False)
    theme=None
    langs=None
    application=None

    def __init__(self,
               parent=None,
               key_name=None,
               _app=None,
               _from_entity=False,
               **kwds):
        from micolog_plugin import Plugins
        self.plugins=Plugins(self)
        db.Model.__init__(self,parent,key_name,_app,_from_entity,**kwds)

    def tigger_filter(self,name,content,*arg1,**arg2):
        return self.plugins.tigger_filter(name,content,blog=self,*arg1,**arg2)

    def tigger_action(self,name,*arg1,**arg2):
        return self.plugins.tigger_action(name,blog=self,*arg1,**arg2)

    def tigger_urlmap(self,url,*arg1,**arg2):
        return self.plugins.tigger_urlmap(url,blog=self,*arg1,**arg2)

    def get_ziplist(self):
        return self.plugins.get_ziplist();

    def save(self):
        self.put()

    def get_theme(self):
        self.theme= Theme(self.theme_name);
        return self.theme

    def get_langs(self):
        self.langs=LangIterator()
        return self.langs

    def cur_language(self):
        return self.get_langs().getlang(self.language)

    def rootpath(self):
        return rootpath

    @vcache("blog.hotposts")
    def hotposts(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-readtimes').fetch(7)

    @vcache("blog.recentposts")
    def recentposts(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').fetch(7)

    @vcache("blog.postscount")
    def postscount(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').count()

class Category(db.Model):
    uid=db.IntegerProperty()
    name=db.StringProperty()
    slug=db.StringProperty()
    parent_cat=db.SelfReferenceProperty()
    @property
    def posts(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).filter('categorie_keys =',self)

    @property
    def count(self):
        return self.posts.count()

    def put(self):
        db.Model.put(self)
        g_blog.tigger_action("save_category",self)

    def delete(self):
        for entry in Entry.all().filter('categorie_keys =',self):
            entry.categorie_keys.remove(self.key())
            entry.put()
        for cat in Category.all().filter('parent_cat =',self):
            cat.delete()
        db.Model.delete(self)
        g_blog.tigger_action("delete_category",self)

    def ID(self):
        try:
            id=self.key().id()
            if id:
                return id
        except:
            pass

        if self.uid :
            return self.uid
        else:
            #ÊóßÁâàÊú¨CategoryÊ≤°ÊúâID,‰∏∫‰∫Ü‰∏éwordpressÂÖºÂÆπ
            from random import randint
            uid=randint(0,99999999)
            cate=Category.all().filter('uid =',uid).get()
            while cate:
                uid=randint(0,99999999)
                cate=Category.all().filter('uid =',uid).get()
            self.uid=uid
            print uid
            self.put()
            return uid

    @classmethod
    def get_from_id(cls,id):
        cate=Category.get_by_id(id)
        if cate:
            return cate
        else:
            cate=Category.all().filter('uid =',id).get()
            return cate

    @property
    def children(self):
        key=self.key()
        return [c for c in Category.all().filter('parent_cat =',self)]


    @classmethod
    def allTops(self):
        return [c for c in Category.all() if not c.parent_cat]

class Archive(db.Model):
    monthyear = db.StringProperty()
    year = db.StringProperty()
    month = db.StringProperty()
    entrycount = db.IntegerProperty(default=0)
    date = db.DateTimeProperty(auto_now_add=True)

class Tag(db.Model):
    tag = db.StringProperty()
    tagcount = db.IntegerProperty(default=0)
    @property
    def posts(self):
        return Entry.all('entrytype =','post').filter("published =", True).filter('tags =',self)

    @classmethod
    def add(cls,value):
        if value:
            tag= Tag.get_by_key_name(value)
            if not tag:
                tag=Tag(key_name=value)
                tag.tag=value

            tag.tagcount+=1
            tag.put()
            return tag
        else:
            return None

    @classmethod
    def remove(cls,value):
        if value:
            tag= Tag.get_by_key_name(value)
            if tag:
                if tag.tagcount>1:
                    tag.tagcount-=1
                    tag.put()
                else:
                    tag.delete()

class Link(db.Model):
    href = db.StringProperty(default='')
    linktype = db.StringProperty(default='blogroll')
    linktext = db.StringProperty(default='')
    linkcomment = db.StringProperty(default='')
    createdate=db.DateTimeProperty(auto_now=True)

    @property
    def get_icon_url(self):
        """get ico url of the wetsite"""
        ico_path = '/favicon.ico'
        ix = self.href.find('/',len('http://') )
        return (ix>0 and self.href[:ix] or self.href ) + ico_path

    def put(self):
        db.Model.put(self)
        g_blog.tigger_action("save_link",self)


    def delete(self):
        db.Model.delete(self)
        g_blog.tigger_action("delete_link",self)

class Entry(BaseModel):
    author = db.UserProperty()
    author_name = db.StringProperty()
    published = db.BooleanProperty(default=False)
    content = db.TextProperty(default='')
    readtimes = db.IntegerProperty(default=0)
    title = db.StringProperty(default='')
    date = db.DateTimeProperty(auto_now_add=True)
    mod_date = db.DateTimeProperty(auto_now_add=True)
    tags = db.StringListProperty()
    categorie_keys=db.ListProperty(db.Key)
    slug = db.StringProperty(default='')
    link= db.StringProperty(default='')
    monthyear = db.StringProperty()
    entrytype = db.StringProperty(default='post',choices=[
        'post','page'])
    entry_parent=db.IntegerProperty(default=0)       #When level=0 show on main menu.
    menu_order=db.IntegerProperty(default=0)
    commentcount = db.IntegerProperty(default=0)
    trackbackcount = db.IntegerProperty(default=0)

    allow_comment = db.BooleanProperty(default=True) #allow comment
    #allow_pingback=db.BooleanProperty(default=False)
    allow_trackback=db.BooleanProperty(default=True)
    password=db.StringProperty()

    #compatible with wordpress
    is_wp=db.BooleanProperty(default=False)
    post_id= db.IntegerProperty()
    excerpt=db.StringProperty(multiline=True)

    #external page
    is_external_page=db.BooleanProperty(default=False)
    target=db.StringProperty(default="_self")
    external_page_address=db.StringProperty()

    #keep in top
    sticky=db.BooleanProperty(default=False)

    postname=''
    _relatepost=None

    @property
    def content_excerpt(self):
        return self.get_content_excerpt(_('..more'))

    def get_author_user(self):
        if not self.author:
            self.author=g_blog.owner
        return User.all().filter('email =',self.author.email()).get()

    def get_content_excerpt(self,more='..more'):
        if g_blog.show_excerpt:
            if self.excerpt:
                return self.excerpt+' <a href="/%s">%s</a>'%(self.link,more)
            else:
                sc=self.content.split('<!--more-->')
                if len(sc)>1:
                    return sc[0]+u' <a href="/%s">%s</a>'%(self.link,more)
                else:
                    return sc[0]
        else:
            return self.content

    def slug_onchange(self,curval,newval):
        if not (curval==newval):
            self.setpostname(newval)

    def setpostname(self,newval):
             #check and fix double slug
            if newval:
                slugcount=Entry.all()\
                          .filter('entrytype',self.entrytype)\
                          .filter('date <',self.date)\
                          .filter('slug =',newval)\
                          .filter('published',True)\
                          .count()
                if slugcount>0:
                    self.postname=newval+str(slugcount)
                else:
                    self.postname=newval
            else:
                self.postname=""

    @property
    def fullurl(self):
        return g_blog.baseurl+'/'+self.link;

    @property
    def categories(self):
        try:
            return db.get(self.categorie_keys)
        except:
            return []

    @property
    def post_status(self):
        return  self.published and 'publish' or 'draft'

    def settags(self,values):
        if not values:tags=[]
        if type(values)==type([]):
            tags=values
        else:
            tags=values.split(',')

        if not self.tags:
            removelist=[]
            addlist=tags
        else:
            #search different  tags
            removelist=[n for n in self.tags if n not in tags]
            addlist=[n for n in tags if n not in self.tags]
        for v in removelist:
            Tag.remove(v)
        for v in addlist:
            Tag.add(v)
        self.tags=tags

    def get_comments_by_page(self,index,psize):
        return self.comments().fetch(psize,offset = (index-1) * psize)

    @property
    def strtags(self):
        return ','.join(self.tags)

    @property
    def edit_url(self):
        return '/admin/%s?key=%s&action=edit'%(self.entrytype,self.key())

    def comments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =',self).order('-date')
        else:
            return Comment.all().filter('entry =',self).order('date')

    def purecomments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =',self).filter('ctype =',0).order('-date')
        else:
            return Comment.all().filter('entry =',self).filter('ctype =',0).order('date')

    def trackcomments(self):
        if g_blog.comments_order:
            return Comment.all().filter('entry =',self).filter('ctype IN',[1,2]).order('-date')
        else:
            return Comment.all().filter('entry =',self).filter('ctype IN',[1,2]).order('date')
    def commentsTops(self):
        return [c for c  in self.purecomments() if c.parent_key()==None]

    def delete_comments(self):
        cmts = Comment.all().filter('entry =',self)
        for comment in cmts:
            comment.delete()
        self.commentcount = 0
        self.trackbackcount = 0
    def update_commentno(self):
        cmts = Comment.all().filter('entry =',self).order('date')
        i=1
        for comment in cmts:
            if comment.no != i:
                comment.no = i
                comment.store()
            i+=1

    def update_archive(self,cnt=1):
        """Checks to see if there is a month-year entry for the
        month of current blog, if not creates it and increments count"""
        my = self.date.strftime('%B %Y') # September-2008
        sy = self.date.strftime('%Y') #2008
        sm = self.date.strftime('%m') #09


        archive = Archive.all().filter('monthyear',my).get()
        if self.entrytype == 'post':
            if not archive:
                archive = Archive(monthyear=my,year=sy,month=sm,entrycount=1)
                self.monthyear = my
                archive.put()
            else:
                # ratchet up the count
                archive.entrycount += cnt
                archive.put()
        g_blog.entrycount+=cnt
        g_blog.put()


    def save(self,is_publish=False):
        """
        Use this instead of self.put(), as we do some other work here
        @is_pub:Check if need publish id
        """
        g_blog.tigger_action("pre_save_post",self,is_publish)
        my = self.date.strftime('%B %Y') # September 2008
        self.monthyear = my
        old_publish=self.published
        self.mod_date=datetime.now()

        if is_publish:
            if not self.is_wp:
                self.put()
                self.post_id=self.key().id()

            #fix for old version
            if not self.postname:
                self.setpostname(self.slug)


            vals={'year':self.date.year,'month':str(self.date.month).zfill(2),'day':self.date.day,
                'postname':self.postname,'post_id':self.post_id}


            if self.entrytype=='page':
                if self.slug:
                    self.link=self.postname
                else:
                    #use external page address as link
                    if self.is_external_page:
                       self.link=self.external_page_address
                    else:
                       self.link=g_blog.default_link_format%vals
            else:
                if g_blog.link_format and self.postname:
                    self.link=g_blog.link_format.strip()%vals
                else:
                    self.link=g_blog.default_link_format%vals

        self.published=is_publish
        self.put()

        if is_publish:
            if g_blog.sitemap_ping:
                Sitemap_NotifySearch()

        if old_publish and not is_publish:
            self.update_archive(-1)
        if not old_publish and is_publish:
            self.update_archive(1)

        self.removecache()

        self.put()
        g_blog.tigger_action("save_post",self,is_publish)

    def removecache(self):
        memcache.delete('/')
        memcache.delete('/'+self.link)
        memcache.delete('/sitemap')
        memcache.delete('blog.postcount')
        g_blog.tigger_action("clean_post_cache",self)

    @property
    def next(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('date').filter('date >',self.date).fetch(1)


    @property
    def prev(self):
        return Entry.all().filter('entrytype =','post').filter("published =", True).order('-date').filter('date <',self.date).fetch(1)

    @property
    def relateposts(self):
        if  self._relatepost:
            return self._relatepost
        else:
            if self.tags:
                try: self._relatepost= Entry.gql("WHERE published=True and tags IN :1 and post_id!=:2 order by post_id desc ",self.tags,self.post_id).fetch(5)
                except: self._relatepost= []
            else:
                self._relatepost= []
            return self._relatepost

    @property
    def trackbackurl(self):
        if self.link.find("?")>-1:
            return g_blog.baseurl+"/"+self.link+"&code="+str(self.key())
        else:
            return g_blog.baseurl+"/"+self.link+"?code="+str(self.key())

    def getbylink(self):
        pass

    def delete(self):
        g_blog.tigger_action("pre_delete_post",self)
        if self.published:
            self.update_archive(-1)
        self.delete_comments()
        db.Model.delete(self)
        g_blog.tigger_action("delete_post",self)


class User(db.Model):
    user = db.UserProperty(required = False)
    dispname = db.StringProperty()
    email=db.StringProperty()
    website = db.LinkProperty()
    isadmin=db.BooleanProperty(default=False)
    isAuthor=db.BooleanProperty(default=True)
    #rpcpwd=db.StringProperty()

    def __unicode__(self):
        #if self.dispname:
            return self.dispname
        #else:
        #	return self.user.nickname()

    def __str__(self):
        return self.__unicode__().encode('utf-8')

COMMENT_NORMAL=0
COMMENT_TRACKBACK=1
COMMENT_PINGBACK=2
class Comment(db.Model):
    entry = db.ReferenceProperty(Entry)
    date = db.DateTimeProperty(auto_now_add=True)
    content = db.TextProperty(required=True)
    author=db.StringProperty()
    email=db.EmailProperty()
    weburl=db.URLProperty()
    status=db.IntegerProperty(default=0)
    reply_notify_mail=db.BooleanProperty(default=False)
    ip=db.StringProperty()
    ctype=db.IntegerProperty(default=COMMENT_NORMAL)
    no=db.IntegerProperty(default=0)
    comment_order=db.IntegerProperty(default=1)

    @property
    def mpindex(self):
        count=self.entry.commentcount
        no=self.no
        if g_blog.comments_order:
            no=count-no+1
        index=no / g_blog.comments_per_page
        if no % g_blog.comments_per_page or no==0:
            index+=1
        return index

    @property
    def shortcontent(self,len=20):
        scontent=self.content
        scontent=re.sub(r'<br\s*/>',' ',scontent)
        scontent=re.sub(r'<[^>]+>','',scontent)
        scontent=re.sub(r'(@[\S]+)-\d{2,7}',r'\1:',scontent)
        return scontent[:len].replace('<','&lt;').replace('>','&gt;')


    def gravatar_url(self):
        # Set your variables here
        if g_blog.avatar_style==0:
            default = g_blog.baseurl+'/static/images/homsar.jpeg'
        else:
            default='identicon'

        if not self.email:
            return default

        size = 50

        try:
            # construct the url
            imgurl = "http://www.gravatar.com/avatar/"
            imgurl +=hashlib.md5(self.email.lower()).hexdigest()+"?"+ urllib.urlencode({
                'd':default, 's':str(size),'r':'G'})
            return imgurl
        except:
            return default

    def save(self):
        self.put()
        self.comment_order=self.entry.commentcount
        self.entry.commentcount+=1
        if (self.ctype == COMMENT_TRACKBACK) or (self.ctype == COMMENT_PINGBACK):
            self.entry.trackbackcount+=1
        self.entry.put()
        memcache.delete("/"+self.entry.link)
        return True

    def delit(self):
        self.entry.commentcount-=1
        if self.entry.commentcount<0:
            self.entry.commentcount = 0
        if (self.ctype == COMMENT_TRACKBACK) or (self.ctype == COMMENT_PINGBACK):
            self.entry.trackbackcount-=1
        if self.entry.trackbackcount<0:
            self.entry.trackbackcount = 0
        self.entry.put()
        self.delete()

    def put(self):
        g_blog.tigger_action("pre_comment",self)
        db.Model.put(self)
        g_blog.tigger_action("save_comment",self)

    def delete(self):
        db.Model.delete(self)
        g_blog.tigger_action("delete_comment",self)

    @property
    def children(self):
        key=self.key()
        comments=Comment.all().ancestor(self)
        return [c for c in comments if c.parent_key()==key]

    def store(self, **kwargs):
        rpc = datastore.GetRpcFromKwargs(kwargs)
        self._populate_internal_entity()
        return datastore.Put(self._entity, rpc=rpc)

class Media(db.Model):
    name =db.StringProperty()
    mtype=db.StringProperty()
    bits=db.BlobProperty()
    date=db.DateTimeProperty(auto_now_add=True)
    download=db.IntegerProperty(default=0)

    @property
    def size(self):
        return len(self.bits)

class OptionSet(db.Model):
    name=db.StringProperty()
    value=db.TextProperty()
    #blobValue=db.BlobProperty()
    #isBlob=db.BooleanProperty()

    @classmethod
    def getValue(cls,name,default=None):
        try:
            opt=OptionSet.get_by_key_name(name)
            return pickle.loads(str(opt.value))
        except:
            return default

    @classmethod
    def setValue(cls,name,value):
        opt=OptionSet.get_or_insert(name)
        opt.name=name
        opt.value=pickle.dumps(value)
        opt.put()

    @classmethod
    def remove(cls,name):
        opt= OptionSet.get_by_key_name(name)
        if opt:
            opt.delete()

NOTIFICATION_SITES = [
  ('http', 'www.google.com', 'webmasters/sitemaps/ping', {}, '', 'sitemap')
  ]


def Sitemap_NotifySearch():
    """ Send notification of the new Sitemap(s) to the search engines. """


    url=g_blog.baseurl+"/sitemap"

    # Cycle through notifications
    # To understand this, see the comment near the NOTIFICATION_SITES comment
    for ping in NOTIFICATION_SITES:
      query_map			 = ping[3]
      query_attr			= ping[5]
      query_map[query_attr] = url
      query = urllib.urlencode(query_map)
      notify = urlparse.urlunsplit((ping[0], ping[1], ping[2], query, ping[4]))
      # Send the notification
      logging.info('Notifying search engines. %s'%ping[1])
      logging.info('url: %s'%notify)
      try:
          result = urlfetch.fetch(notify)
          if result.status_code == 200:
              logging.info('Notify Result: %s' % result.content)
          if result.status_code == 404:
              logging.info('HTTP error 404: Not Found')
              logging.warning('Cannot contact: %s' % ping[1])

      except :
          logging.error('Cannot contact: %s' % ping[1])

def InitBlogData():
    global g_blog
    OptionSet.setValue('PluginActive',[u'googleAnalytics', u'wordpress', u'sys_plugin'])

    g_blog = Blog(key_name = 'default')
    g_blog.domain=os.environ['HTTP_HOST']
    g_blog.baseurl="http://"+g_blog.domain
    g_blog.feedurl=g_blog.baseurl+"/feed"
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    g_blog.admin_essential = False
    if os.environ.has_key('HTTP_ACCEPT_LANGUAGE'):
        lang=os.environ['HTTP_ACCEPT_LANGUAGE'].split(',')[0]
    from django.utils.translation import  activate,to_locale
    g_blog.language=to_locale(lang)
    g_blog.admin_essential=False
    from django.conf import settings
    settings._target = None
    activate(g_blog.language)
    g_blog.save()

    entry=Entry(title="Hello world!".decode('utf8'))
    entry.content='<p>Welcome to micolog %s. This is your first post. Edit or delete it, then start blogging!</p>'%g_blog.version
    entry.save(True)
    link=Link(href='http://xuming.net',linktext="Xuming's blog".decode('utf8'))
    link.put()
    link=Link(href='http://eric.cloud-mes.com/',linktext="Eric Guo's blog".decode('utf8'))
    link.put()
    return g_blog

def gblog_init():
    global g_blog
    try:
       if g_blog :
           return g_blog
    except:
        pass
    g_blog = Blog.get_by_key_name('default')
    if not g_blog:
        g_blog=InitBlogData()

    g_blog.get_theme()
    g_blog.rootdir=os.path.dirname(__file__)
    return g_blog

try:
    g_blog=gblog_init()

    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
    from django.utils.translation import activate
    from django.conf import settings
    settings._target = None
    activate(g_blog.language)
except:
    pass




########NEW FILE########
__FILENAME__ = googleAnalytics
from micolog_plugin import *
from model import OptionSet
class googleAnalytics(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="Plugin for put google Analytics into micolog."
		self.name="google Analytics"
		self.version="0.1"
		self.register_filter('footer',self.filter)

	def filter(self,content,*arg1,**arg2):
		code=OptionSet.getValue("googleAnalytics_code",default="")
		return content+str(code)

	def get(self,page):
		code=OptionSet.getValue("googleAnalytics_code",default="")
		return '''<h3>Google Anslytics</h3>
					<form action="" method="post">
					<p>Analytics Code:</p>
					<textarea name="code" style="width:500px;height:100px">%s</textarea>
					<br>
					<input type="submit" value="submit">
					</form>'''%code

	def post(self,page):
		code=page.param("code")
		OptionSet.setValue("googleAnalytics_code",code)
		return self.get(page)

########NEW FILE########
__FILENAME__ = highsyntax
from micolog_plugin import *
import logging
from model import *
from google.appengine.api import users
class highsyntax(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="HighSyntax Plugin."
		self.name="HighSyntax plugin"
		self.version="0.1"
		self.register_filter('footer',self.footer)
		self.register_urlzip('/syntaxhighlighter/(.*)','syntaxhighlighter.zip')
		self.theme=OptionSet.getValue("highsyntax_theme",default="Default")


	def footer(self,content,blog=None,*arg1,**arg2):
		return content+'''
<script type="text/javascript">
if ($('pre[class^=brush:]').length > 0)
{
	$.getScript("/syntaxhighlighter/scripts/shCore.js", function() {
		SyntaxHighlighter.boot("/syntaxhighlighter/", {theme : "'''+str(self.theme)+'''", stripBrs : true}, {});
	});
}
</script>
'''

	def get(self,page):
		return '''<h3>HighSyntax Plugin</h3>
			   <p>HighSyntax plugin for micolog.</p>
			   <p>This plugin based on <a href="http://alexgorbatchev.com/wiki/SyntaxHighlighter" target="_blank">SyntaxHighlighter</a>
			    and <a href="http://www.outofwhatbox.com/blog/syntaxhighlighter-downloads/" target="_blank">SyntaxHighlighter.boot()</a></p>
				<form action="" method="post">
			   <p><B>Require:</B>
					<ol>
					<li><b>{%mf footer%} </b>in template "base.html".</li>
					<li><a href="http://jquery.org"  target="_blank">Jquery</a> version 1.3.2 or new.</li>
					</ol>
			   </p>
			   <p><b>Theme:</b>
			   </p>
				<p>
				<select name="theme" id="theme">
	<option value="Default">Default</option>
	<option value="Django">Django</option>
	<option value="Eclipse">Eclipse</option>
	<option value="Emacs">Emacs</option>
	<option value="FadeToGrey">FadeToGrey</option>
	<option value="Midnight">Midnight</option>
	<option value="RDark">RDark</option>
</select>
</p>
			   <p>
			   <input type="submit" value="submit">
			   </p>
				</form>
<script>
$("#theme").val("'''+str(self.theme)+'''");</script>
				'''

	def post(self,page):
		self.theme=page.param("theme")
		OptionSet.setValue("highsyntax_theme",self.theme)
		return self.get(page)
########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses a (possibly invalid) XML or HTML document into a
tree representation. It provides methods and Pythonic idioms that make
it easy to navigate, search, and modify the tree.

A well-formed XML/HTML document yields a well-formed data
structure. An ill-formed XML/HTML document yields a correspondingly
ill-formed data structure. If your document is only locally
well-formed, you can use this library to find and process the
well-formed part of it.

Beautiful Soup works with Python 2.2 and up. It has no external
dependencies, but you'll have more success at converting data to UTF-8
if you also install these three packages:

* chardet, for auto-detecting character encodings
  http://chardet.feedparser.org/
* cjkcodecs and iconv_codec, which add more encodings to the ones supported
  by stock Python.
  http://cjkpython.i18n.org/

Beautiful Soup defines classes for two main parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid. This class has web browser-like heuristics for
   obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup also defines a class (UnicodeDammit) for autodetecting
the encoding of an HTML or XML document, and converting it to
Unicode. Much of this code is taken from Mark Pilgrim's Universal Feed Parser.

For more than you ever wanted to know about Beautiful Soup, see the
documentation:
http://www.crummy.com/software/BeautifulSoup/documentation.html

Here, have some legalese:

Copyright (c) 2004-2010, Leonard Richardson

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the the Beautiful Soup Consortium and All
    Night Kosher Bakery nor the names of its contributors may be
    used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE, DAMMIT.

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.2.0"
__copyright__ = "Copyright (c) 2004-2010 Leonard Richardson"
__license__ = "New-style BSD"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import markupbase
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

def _match_css_class(str):
    """Build a RE to match the given CSS class."""
    return re.compile(r"(^|.*\s)%s($|\s)" % str)

# First, the classes that represent markup elements.

class PageElement(object):
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def setup(self, parent=None, previous=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = None
        self.previousSibling = None
        self.nextSibling = None
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def replaceWith(self, replaceWith):
        oldParent = self.parent
        myIndex = self.parent.index(self)
        if hasattr(replaceWith, "parent")\
                  and replaceWith.parent is self.parent:
            # We're replacing this element with one of its siblings.
            index = replaceWith.parent.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def replaceWithChildren(self):
        myParent = self.parent
        myIndex = self.parent.index(self)
        self.extract()
        reversedChildren = list(self.contents)
        reversedChildren.reverse()
        for child in reversedChildren:
            myParent.insert(myIndex, child)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                del self.parent.contents[self.parent.index(self)]
            except ValueError:
                pass

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        lastChild = self._lastRecursiveChild()
        nextElement = lastChild.next

        if self.previous:
            self.previous.next = nextElement
        if nextElement:
            nextElement.previous = self.previous
        self.previous = None
        lastChild.next = None

        self.parent = None
        if self.previousSibling:
            self.previousSibling.nextSibling = self.nextSibling
        if self.nextSibling:
            self.nextSibling.previousSibling = self.previousSibling
        self.previousSibling = self.nextSibling = None
        return self

    def _lastRecursiveChild(self):
        "Finds the last element beneath this object to be parsed."
        lastChild = self
        while hasattr(lastChild, 'contents') and lastChild.contents:
            lastChild = lastChild.contents[-1]
        return lastChild

    def insert(self, position, newChild):
        if isinstance(newChild, basestring) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent is self:
                index = self.index(newChild)
                if index > position:
                    # Furthermore we're moving it further down the
                    # list of this object's children. That means that
                    # when we extract this element, our target index
                    # will jump down one.
                    position = position - 1
            newChild.extract()

        newChild.parent = self
        previousChild = None
        if position == 0:
            newChild.previousSibling = None
            newChild.previous = self
        else:
            previousChild = self.contents[position-1]
            newChild.previousSibling = previousChild
            newChild.previousSibling.nextSibling = newChild
            newChild.previous = previousChild._lastRecursiveChild()
        if newChild.previous:
            newChild.previous.next = newChild

        newChildsLastElement = newChild._lastRecursiveChild()

        if position >= len(self.contents):
            newChild.nextSibling = None

            parent = self
            parentsNextSibling = None
            while not parentsNextSibling:
                parentsNextSibling = parent.nextSibling
                parent = parent.parent
                if not parent: # This is the last element in the document.
                    break
            if parentsNextSibling:
                newChildsLastElement.next = parentsNextSibling
            else:
                newChildsLastElement.next = None
        else:
            nextChild = self.contents[position]
            newChild.nextSibling = nextChild
            if newChild.nextSibling:
                newChild.nextSibling.previousSibling = newChild
            newChildsLastElement.next = nextChild

        if newChildsLastElement.next:
            newChildsLastElement.next.previous = newChildsLastElement
        self.contents.insert(position, newChild)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator,
                             **kwargs)

    def findNextSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._findOne(self.findNextSiblings, name, attrs, text,
                             **kwargs)

    def findNextSiblings(self, name=None, attrs={}, text=None, limit=None,
                         **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.nextSiblingGenerator, **kwargs)
    fetchNextSiblings = findNextSiblings # Compatibility with pre-3.x

    def findPrevious(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._findOne(self.findAllPrevious, name, attrs, text, **kwargs)

    def findAllPrevious(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.previousGenerator,
                           **kwargs)
    fetchPrevious = findAllPrevious # Compatibility with pre-3.x

    def findPreviousSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._findOne(self.findPreviousSiblings, name, attrs, text,
                             **kwargs)

    def findPreviousSiblings(self, name=None, attrs={}, text=None,
                             limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.previousSiblingGenerator, **kwargs)
    fetchPreviousSiblings = findPreviousSiblings # Compatibility with pre-3.x

    def findParent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _findOne because findParents takes a different
        # set of arguments.
        r = None
        l = self.findParents(name, attrs, 1)
        if l:
            r = l[0]
        return r

    def findParents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._findAll(name, attrs, None, limit, self.parentGenerator,
                             **kwargs)
    fetchParents = findParents # Compatibility with pre-3.x

    #These methods do the real heavy lifting.

    def _findOne(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _findAll(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        # (Possibly) special case some findAll*(...) searches
        elif text is None and not limit and not attrs and not kwargs:
            # findAll*(True)
            if name is True:
                return [element for element in generator()
                        if isinstance(element, Tag)]
            # findAll*('tag-name')
            elif isinstance(name, basestring):
                return [element for element in generator()
                        if isinstance(element, Tag) and
                        element.name == name]
            else:
                strainer = SoupStrainer(name, attrs, text, **kwargs)
        # Build a SoupStrainer
        else:
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These Generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    def nextGenerator(self):
        i = self
        while i is not None:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i is not None:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i is not None:
            i = i.parent
            yield i

    # Utility methods
    def substituteEncoding(self, str, encoding=None):
        encoding = encoding or "utf-8"
        return str.replace("%SOUP-ENCODING%", encoding)

    def toEncoding(self, s, encoding=None):
        """Encodes an object to a string in some encoding, or to Unicode.
        ."""
        if isinstance(s, unicode):
            if encoding:
                s = s.encode(encoding)
        elif isinstance(s, str):
            if encoding:
                s = s.encode(encoding)
            else:
                s = unicode(s)
        else:
            if encoding:
                s  = self.toEncoding(str(s), encoding)
            else:
                s = unicode(s)
        return s

class NavigableString(unicode, PageElement):

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __getnewargs__(self):
        return (NavigableString.__str__(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return str(self).decode(DEFAULT_OUTPUT_ENCODING)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        if encoding:
            return self.encode(encoding)
        else:
            return self

class CData(NavigableString):

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<![CDATA[%s]]>" % NavigableString.__str__(self, encoding)

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        return "<?%s?>" % self.toEncoding(output, encoding)

class Comment(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!--%s-->" % NavigableString.__str__(self, encoding)

class Declaration(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!%s>" % NavigableString.__str__(self, encoding)

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def _invert(h):
        "Cheap function to invert a hash."
        i = {}
        for k,v in h.items():
            i[v] = k
        return i

    XML_ENTITIES_TO_SPECIAL_CHARS = { "apos" : "'",
                                      "quot" : '"',
                                      "amp" : "&",
                                      "lt" : "<",
                                      "gt" : ">" }

    XML_SPECIAL_CHARS_TO_ENTITIES = _invert(XML_ENTITIES_TO_SPECIAL_CHARS)

    def _convertEntities(self, match):
        """Used in a call to re.sub to replace HTML, XML, and numeric
        entities with the appropriate Unicode characters. If HTML
        entities are being converted, any unrecognized entities are
        escaped."""
        x = match.group(1)
        if self.convertHTMLEntities and x in name2codepoint:
            return unichr(name2codepoint[x])
        elif x in self.XML_ENTITIES_TO_SPECIAL_CHARS:
            if self.convertXMLEntities:
                return self.XML_ENTITIES_TO_SPECIAL_CHARS[x]
            else:
                return u'&%s;' % x
        elif len(x) > 0 and x[0] == '#':
            # Handle numeric entities
            if len(x) > 1 and x[1] == 'x':
                return unichr(int(x[2:], 16))
            else:
                return unichr(int(x[1:]))

        elif self.escapeUnrecognizedEntities:
            return u'&amp;%s;' % x
        else:
            return u'&%s;' % x

    def __init__(self, parser, name, attrs=None, parent=None,
                 previous=None):
        "Basic constructor."

        # We don't actually store the parser object: that lets extracted
        # chunks be garbage-collected
        self.parserClass = parser.__class__
        self.isSelfClosing = parser.isSelfClosingTag(name)
        self.name = name
        if attrs is None:
            attrs = []
        elif isinstance(attrs, dict):
            attrs = attrs.items()
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        # Convert any HTML, XML, or numeric entities in the attribute values.
        convert = lambda(k, val): (k,
                                   re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                                          self._convertEntities,
                                          val))
        self.attrs = map(convert, self.attrs)

    def getString(self):
        if (len(self.contents) == 1
            and isinstance(self.contents[0], NavigableString)):
            return self.contents[0]

    def setString(self, string):
        """Replace the contents of the tag with a string"""
        self.clear()
        self.append(string)

    string = property(getString, setString)

    def getText(self, separator=u""):
        if not len(self.contents):
            return u""
        stopNode = self._lastRecursiveChild().next
        strings = []
        current = self.contents[0]
        while current is not stopNode:
            if isinstance(current, NavigableString):
                strings.append(current.strip())
            current = current.next
        return separator.join(strings)

    text = property(getText)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def clear(self):
        """Extract all children."""
        for child in self.contents[:]:
            child.extract()

    def index(self, element):
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

    def has_key(self, key):
        return self._getAttrMap().has_key(key)

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        findAll() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.findAll, args, kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.find(tag[:-3])
        elif tag.find('__') != 0:
            return self.find(tag)
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__, tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if other is self:
            return True
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.__str__(encoding)

    def __unicode__(self):
        return self.__str__(None)

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING,
                prettyPrint=False, indentLevel=0):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""

        encodedName = self.toEncoding(self.name, encoding)

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isinstance(val, basestring):
                    if self.containsSubstitutions and '%SOUP-ENCODING%' in val:
                        val = self.substituteEncoding(val, encoding)

                    # The attribute value either:
                    #
                    # * Contains no embedded double quotes or single quotes.
                    #   No problem: we enclose it in double quotes.
                    # * Contains embedded single quotes. No problem:
                    #   double quotes work here too.
                    # * Contains embedded double quotes. No problem:
                    #   we enclose it in single quotes.
                    # * Embeds both single _and_ double quotes. This
                    #   can't happen naturally, but it can happen if
                    #   you modify an attribute value after parsing
                    #   the document. Now we have a bit of a
                    #   problem. We solve it by enclosing the
                    #   attribute in single quotes, and escaping any
                    #   embedded single quotes to XML entities.
                    if '"' in val:
                        fmt = "%s='%s'"
                        if "'" in val:
                            # TODO: replace with apos when
                            # appropriate.
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, val)

                attrs.append(fmt % (self.toEncoding(key, encoding),
                                    self.toEncoding(val, encoding)))
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % encodedName

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.renderContents(encoding, prettyPrint, indentContents)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (encodedName, attributeString, close))
            if prettyPrint:
                s.append("\n")
            s.append(contents)
            if prettyPrint and contents and contents[-1] != "\n":
                s.append("\n")
            if prettyPrint and closeTag:
                s.append(space)
            s.append(closeTag)
            if prettyPrint and closeTag and self.nextSibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        self.extract()
        if len(self.contents) == 0:
            return
        current = self.contents[0]
        while current is not None:
            next = current.next
            if isinstance(current, Tag):
                del current.contents[:]
            current.parent = None
            current.previous = None
            current.previousSibling = None
            current.next = None
            current.nextSibling = None
            current = next

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.__str__(encoding, True)

    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.__str__(encoding)
            elif isinstance(c, Tag):
                s.append(c.__str__(encoding, prettyPrint, indentLevel))
            if text and prettyPrint:
                text = text.strip()
            if text:
                if prettyPrint:
                    s.append(" " * (indentLevel-1))
                s.append(text)
                if prettyPrint:
                    s.append("\n")
        return ''.join(s)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.findAll(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def findAll(self, name=None, attrs={}, recursive=True, text=None,
                limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._findAll(name, attrs, text, limit, generator, **kwargs)
    findChildren = findAll

    # Pre-3.x compatibility methods
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value
        return self.attrMap

    #Generator methods
    def childGenerator(self):
        # Just use the iterator from the contents
        return iter(self.contents)

    def recursiveChildGenerator(self):
        if not len(self.contents):
            raise StopIteration
        stopNode = self._lastRecursiveChild().next
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next


# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isinstance(attrs, basestring):
            kwargs['class'] = _match_css_class(attrs)
            attrs = None
        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        self.attrs = attrs
        self.text = text

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def searchTag(self, markupName=None, markupAttrs={}):
        found = None
        markup = None
        if isinstance(markupName, Tag):
            markup = markupName
            markupAttrs = markup
        callFunctionWithTagData = callable(self.name) \
                                and not isinstance(markupName, Tag)

        if (not self.name) \
               or callFunctionWithTagData \
               or (markup and self._matches(markup, self.name)) \
               or (not markup and self._matches(markupName, self.name)):
            if callFunctionWithTagData:
                match = self.name(markupName, markupAttrs)
            else:
                match = True
                markupAttrMap = None
                for attr, matchAgainst in self.attrs.items():
                    if not markupAttrMap:
                         if hasattr(markupAttrs, 'get'):
                            markupAttrMap = markupAttrs
                         else:
                            markupAttrMap = {}
                            for k,v in markupAttrs:
                                markupAttrMap[k] = v
                    attrValue = markupAttrMap.get(attr)
                    if not self._matches(attrValue, matchAgainst):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markupName
        return found

    def search(self, markup):
        #print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if hasattr(markup, "__iter__") \
                and not isinstance(markup, Tag):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text:
                found = self.searchTag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isinstance(markup, basestring):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst is True:
            result = markup is not None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isinstance(markup, basestring):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif hasattr(matchAgainst, '__iter__'): # list-like
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isinstance(markup, basestring):
                if isinstance(markup, unicode):
                    matchAgainst = unicode(matchAgainst)
                else:
                    matchAgainst = str(matchAgainst)

            if not result:
                result = matchAgainst == markup
        return result

class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

# Now, some helper functions.

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS, NESTABLE_TAGS, and
    NESTING_RESET_TAGS maps out of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif hasattr(portion, '__iter__'): # is a list
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class BeautifulStoneSoup(Tag, SGMLParser):

    """This class contains the basic parser and search code. It defines
    a parser that knows nothing about tag behavior except for the
    following:

      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}
    PRESERVE_WHITESPACE_TAGS = []

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"
    XHTML_ENTITIES = "xhtml"
    # TODO: This only exists for backwards-compatibility
    ALL_ENTITIES = XHTML_ENTITIES

    # Used when determining whether a text node is all whitespace and
    # can be replaced with a single space. A text node that contains
    # fancy Unicode spaces (usually non-breaking) should be left
    # alone.
    STRIP_ASCII_SPACES = { 9: None, 10: None, 12: None, 13: None, 32: None, }

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None, isHTML=False):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        sgmllib will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        sgmllib, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke sgmllib:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""

        self.parseOnlyThese = parseOnlyThese
        self.fromEncoding = fromEncoding
        self.smartQuotesTo = smartQuotesTo
        self.convertEntities = convertEntities
        # Set the rules for how we'll deal with the entities we
        # encounter
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
            if convertEntities == self.HTML_ENTITIES:
                self.convertXMLEntities = False
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = True
            elif convertEntities == self.XHTML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = False
            elif convertEntities == self.XML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = False
                self.escapeUnrecognizedEntities = False
        else:
            self.convertXMLEntities = False
            self.convertHTMLEntities = False
            self.escapeUnrecognizedEntities = False

        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        SGMLParser.__init__(self)

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed

    def convert_charref(self, name):
        """This method fixes a bug in Python's SGMLParser."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127 : # ASCII ends at 127, not 255
            return
        return self.convert_codepoint(n)

    def _feed(self, inDocumentEncoding=None, isHTML=False):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo, isHTML=isHTML)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
            self.declaredHTMLEncoding = dammit.declaredHTMLEncoding
        if markup:
            if self.markupMassage:
                if not hasattr(self.markupMassage, "__iter__"):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.reset()

        SGMLParser.feed(self, markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        #print "__getattr__ called on %s.%s" % (self.__class__, methodName)

        if methodName.startswith('start_') or methodName.startswith('end_') \
               or methodName.startswith('do_'):
            return SGMLParser.__getattr__(self, methodName)
        elif not methodName.startswith('__'):
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.contents.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = u''.join(self.currentData)
            if (currentData.translate(self.STRIP_ASCII_SPACES) == '' and
                not set([tag.name for tag in self.tagStack]).intersection(
                    self.PRESERVE_WHITESPACE_TAGS)):
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            self.currentData = []
            if self.parseOnlyThese and len(self.tagStack) <= 1 and \
                   (not self.parseOnlyThese.text or \
                    not self.parseOnlyThese.search(currentData)):
                return
            o = containerClass(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)


    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        #print "Popping to %s" % name
        if name == self.ROOT_TAG_NAME:
            return

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar *<p>* should pop to 'p', not 'b'.
         <p>Foo<table>Bar *<p>* should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar *<p>* should pop to 'tr', not 'p'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers is not None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers is None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):

                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.
                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s: %s" % (name, attrs)
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join([' %s="%s"' % (x, y) for x, y in attrs])
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()

        if not self.isSelfClosingTag(name) and not selfClosing:
            self._smartPop(name)

        if self.parseOnlyThese and len(self.tagStack) <= 1 \
               and (self.parseOnlyThese.text or not self.parseOnlyThese.searchTag(name, attrs)):
            return

        tag = Tag(self, name, attrs, self.currentTag, self.previous)
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or self.isSelfClosingTag(name):
            self.popTag()
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1
        return tag

    def unknown_endtag(self, name):
        #print "End tag %s" % name
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.endData()
        self.handle_data(text)
        self.endData(subclass)

    def handle_pi(self, text):
        """Handle a processing instruction as a ProcessingInstruction
        object, possibly one with a %SOUP-ENCODING% slot into which an
        encoding will be plugged later."""
        if text[:3] == "xml":
            text = u"xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.convertXMLEntities:
                data = self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.convertHTMLEntities and \
            not self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
                # TODO: We've got a problem here. We're told this is
                # an entity reference, but it's not an XML entity
                # reference or an HTML entity reference. Nonetheless,
                # the logical thing to do is to pass it through as an
                # unrecognized entity reference.
                #
                # Except: when the input is "&carol;" this function
                # will be called with input "carol". When the input is
                # "AT&T", this function will be called with input
                # "T". We have no way of knowing whether a semicolon
                # was present originally, so we don't know whether
                # this is an unknown entity or just a misplaced
                # ampersand.
                #
                # The more common case is a misplaced ampersand, so I
                # escape the ampersand and omit the trailing semicolon.
                data = "&amp;%s" % ref
        if not data:
            # This case is different from the one above, because we
            # haven't already gone through a supposedly comprehensive
            # mapping of entities to Unicode characters. We might not
            # have gone through any mapping at all. So the chances are
            # very high that this is a real entity, and not a
            # misplaced ampersand.
            data = "&%s;" % ref
        self.handle_data(data)

    def handle_decl(self, data):
        "Handle DOCTYPEs and the like as Declaration objects."
        self._toStringSubclass(data, Declaration)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as a CData object."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             data = self.rawdata[i+9:k]
             j = k+3
             self._toStringSubclass(data, CData)
        else:
            try:
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup, MinimalSoup, or
    BeautifulStoneSoup before writing your own subclass."""

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key('smartQuotesTo'):
            kwargs['smartQuotesTo'] = self.HTML_ENTITIES
        kwargs['isHTML'] = True
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ('br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base', 'col'))

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ('span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center')

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ('blockquote', 'div', 'fieldset', 'ins', 'del')

    #Lists can contain other lists, but there are restrictions.
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.
    NESTABLE_TABLE_TAGS = {'table' : [],
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           'thead' : ['table'],
                           'tbody' : ['table'],
                           'tfoot' : ['table'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ('address', 'form', 'p', 'pre')

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)

    # Used to detect the charset in a META tag; see start_meta
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def start_meta(self, attrs):
        """Beautiful Soup can detect a charset included in a META tag,
        try to convert the document to that charset, and re-parse the
        document from the beginning."""
        httpEquiv = None
        contentType = None
        contentTypeIndex = None
        tagNeedsEncodingSubstitution = False

        for i in range(0, len(attrs)):
            key, value = attrs[i]
            key = key.lower()
            if key == 'http-equiv':
                httpEquiv = value
            elif key == 'content':
                contentType = value
                contentTypeIndex = i

        if httpEquiv and contentType: # It's an interesting meta tag.
            match = self.CHARSET_RE.search(contentType)
            if match:
                if (self.declaredHTMLEncoding is not None or
                    self.originalEncoding == self.fromEncoding):
                    # An HTML encoding was sniffed while converting
                    # the document to Unicode, or an HTML encoding was
                    # sniffed during a previous pass through the
                    # document, or an encoding was specified
                    # explicitly and it worked. Rewrite the meta tag.
                    def rewrite(match):
                        return match.group(1) + "%SOUP-ENCODING%"
                    newAttr = self.CHARSET_RE.sub(rewrite, contentType)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the encoding information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
                    pass
        tag = self.unknown_starttag("meta", attrs)
        if tag and tagNeedsEncodingSubstitution:
            tag.containsSubstitutions = True

class StopParsing(Exception):
    pass

class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close a 'b' tag
    than to actually use nested 'b' tags, and the BeautifulSoup class
    handles the common case. This class handles the not-co-common
    case: where you can't believe someone wrote what they did, but
    it's valid HTML and BeautifulSoup screwed up by assuming it
    wouldn't be."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ('em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big')

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ('noscript',)

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class MinimalSoup(BeautifulSoup):
    """The MinimalSoup class is for parsing HTML that contains
    pathologically bad markup. It makes no assumptions about tag
    nesting, but it does know which tags are self-closing, that
    <script> tags contain Javascript and should not be parsed, that
    META tags may contain encoding information, and so on.

    This also makes it better for subclassing than BeautifulStoneSoup
    or BeautifulSoup."""

    RESET_NESTING_TAGS = buildTagMap('noscript')
    NESTABLE_TAGS = {}

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableString) and
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisiness,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class RobustInsanelyWackAssHTMLParser(MinimalSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

######################################################
#
# Bonus library: Unicode, Dammit
#
# This class forces XML data into a standard format (usually to UTF-8
# or Unicode).  It is heavily based on code from Mark Pilgrim's
# Universal Feed Parser. It does not rewrite the XML or HTML to
# reflect a new encoding: that happens in BeautifulStoneSoup.handle_pi
# (XML) and BeautifulSoup.start_meta (HTML).

# Autodetects character encodings.
# Download from http://chardet.feedparser.org/
try:
    import chardet
#    import chardet.constants
#    chardet.constants._debug = 1
except ImportError:
    chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except ImportError:
    pass
try:
    import iconv_codec
except ImportError:
    pass

class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = { "macintosh" : "mac-roman",
                        "x-sjis" : "shift-jis" }

    def __init__(self, markup, overrideEncodings=[],
                 smartQuotesTo='xml', isHTML=False):
        self.declaredHTMLEncoding = None
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup, isHTML)
        self.smartQuotesTo = smartQuotesTo
        self.triedEncodings = []
        if markup == '' or isinstance(markup, unicode):
            self.originalEncoding = None
            self.unicode = unicode(markup)
            return

        u = None
        for proposedEncoding in overrideEncodings:
            u = self._convertFrom(proposedEncoding)
            if u: break
        if not u:
            for proposedEncoding in (documentEncoding, sniffedEncoding):
                u = self._convertFrom(proposedEncoding)
                if u: break

        # If no luck and we have auto-detection library, try that:
        if not u and chardet and not isinstance(self.markup, unicode):
            u = self._convertFrom(chardet.detect(self.markup)['encoding'])

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convertFrom(proposed_encoding)
                if u: break

        self.unicode = u
        if not u: self.originalEncoding = None

    def _subMSChar(self, orig):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        sub = self.MS_CHARS.get(orig)
        if isinstance(sub, tuple):
            if self.smartQuotesTo == 'xml':
                sub = '&#x%s;' % sub[1]
            else:
                sub = '&%s;' % sub[0]
        return sub

    def _convertFrom(self, proposed):
        proposed = self.find_codec(proposed)
        if not proposed or proposed in self.triedEncodings:
            return None
        self.triedEncodings.append(proposed)
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if self.smartQuotesTo and proposed.lower() in("windows-1252",
                                                      "iso-8859-1",
                                                      "iso-8859-2"):
            markup = re.compile("([\x80-\x9f])").sub \
                     (lambda(x): self._subMSChar(x.group(1)),
                      markup)

        try:
            # print "Trying to convert document to %s" % proposed
            u = self._toUnicode(markup, proposed)
            self.markup = u
            self.originalEncoding = proposed
        except Exception, e:
            # print "That didn't work!"
            # print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _toUnicode(self, data, encoding):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding)
        return newdata

    def _detectEncoding(self, xml_data, isHTML=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == '\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == '\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') \
                     and (xml_data[2:4] != '\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and \
                     (xml_data[2:4] != '\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == '\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = re.compile(
            '^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
        if not xml_encoding_match and isHTML:
            regexp = re.compile('<\s*meta[^>]+charset=([^>]*?)[;\'">]', re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].lower()
            if isHTML:
                self.declaredHTMLEncoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding


    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset: return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None
    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    MS_CHARS = { '\x80' : ('euro', '20AC'),
                 '\x81' : ' ',
                 '\x82' : ('sbquo', '201A'),
                 '\x83' : ('fnof', '192'),
                 '\x84' : ('bdquo', '201E'),
                 '\x85' : ('hellip', '2026'),
                 '\x86' : ('dagger', '2020'),
                 '\x87' : ('Dagger', '2021'),
                 '\x88' : ('circ', '2C6'),
                 '\x89' : ('permil', '2030'),
                 '\x8A' : ('Scaron', '160'),
                 '\x8B' : ('lsaquo', '2039'),
                 '\x8C' : ('OElig', '152'),
                 '\x8D' : '?',
                 '\x8E' : ('#x17D', '17D'),
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : ('lsquo', '2018'),
                 '\x92' : ('rsquo', '2019'),
                 '\x93' : ('ldquo', '201C'),
                 '\x94' : ('rdquo', '201D'),
                 '\x95' : ('bull', '2022'),
                 '\x96' : ('ndash', '2013'),
                 '\x97' : ('mdash', '2014'),
                 '\x98' : ('tilde', '2DC'),
                 '\x99' : ('trade', '2122'),
                 '\x9a' : ('scaron', '161'),
                 '\x9b' : ('rsaquo', '203A'),
                 '\x9c' : ('oelig', '153'),
                 '\x9d' : '?',
                 '\x9e' : ('#x17E', '17E'),
                 '\x9f' : ('Yuml', ''),}

#######################################################################


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulSoup(sys.stdin)
    print soup.prettify()

########NEW FILE########
__FILENAME__ = live_import
# -*- coding: utf-8 -*-
from micolog_plugin import *
from BeautifulSoup import *
from datetime import datetime
from model import Entry,Comment,Media
import logging,math
import re
from base import BaseRequestHandler,urldecode


class Importhandler(BaseRequestHandler):
	def post(self):

		if not self.is_login:
			self.redirect(users.create_login_url(self.request.uri))
		filename=self.param('filename')
		do_comment=self.paramint('c',0)
		if filename[:4]=='img/':#Â§ÑÁêÜÂõæÁâá
			new_filename=filename.split('/')[1]
			mtype =new_filename.split('.')[1]
			bits = self.request.body
			media=Media.all().filter('name =',new_filename)
			if media.count()>0:
				media=media[0]
			else:
				media=Media()
			media.name=new_filename
			media.mtype=mtype
			media.bits=bits
			media.put()
			bid='_'.join(new_filename.split('_')[:-1])
			entries=Entry.all().filter('slug =',bid)
			if entries.count()>0:
				entry=entries[0]
				entry.content=entry.content.replace(filename,'/media/'+str(media.key()))
				entry.put()
			return

		if filename=="index.html" or filename[-5:]!='.html':
			return
		#Â§ÑÁêÜhtmlÈ°µÈù¢
		bid=filename[:-5]
		try:

			soup=BeautifulSoup(self.request.body)
			bp=soup.find(id='bp')
			title=self.getChineseStr( soup.title.text)
			logging.info(bid)
			pubdate=self.getdate( bp.find(id='bp-'+bid+'-publish').text)
			body=bp.find('div','blogpost')

			entries=Entry.all().filter('title = ',title)
			if entries.count()<1:
				entry=Entry()
			else:
				entry=entries[0]
##			entry=Entry.get_by_key_name(bid)
##			if not entry:
##				entry=Entry(key_name=bid)
			entry.slug=bid
			entry.title=title
			entry.author_name=self.login_user.nickname()
			entry.date=pubdate
			entry.settags("")
			entry.content=unicode(body)
			entry.author=self.login_user

			entry.save(True)
			if do_comment>0:
				comments=soup.find('div','comments','div')
				if comments:
					for comment in comments.contents:
						name,date=comment.h5.text.split(' - ')
						# modify by lastmind4
						name_date_pair = comment.h5.text
						if name_date_pair.index('- ') == 0:
							name_date_pair = 'Anonymous ' + name_date_pair
						name,date=name_date_pair.split(' - ')

						key_id=comment.h5['id']
						date=self.getdate(date)
						content=comment.contents[1].text
						comment=Comment.get_or_insert(key_id,content=content)
						comment.entry=entry
						comment.date=date
						comment.author=name
						comment.save()

		except Exception,e :
			logging.info("import error: %s"%e.message)

	def getdate(self,d):
		try:
			ret=datetime.strptime(d,"%Y/%m/%d %H&#58;%M&#58;%S")
		except:
			try:
				ret=datetime.strptime(d,"%m/%d/%Y %H&#58;%M&#58;%S %p")
			except:
				ret=datetime.now()
		return ret

	def getChineseStr(self,s):
		return re.sub(r'&#(\d+);',lambda x:unichr(int(x.group(1))) ,s)

class live_import(Plugin_importbase):
	def __init__(self):
		Plugin_importbase.__init__(self,__file__,"spaces.live.com","Plugin for import entries from space.zip.")
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description='''Plugin for import entries from space.zip.<br>
		Â∞ÜSpaces.Live.comÂçöÂÆ¢ÂØºÂÖ•Âà∞Micolog.'''
		self.name="LiveSapce Import"
		self.version="0.12"
		self.register_urlzip('/admin/live_import/swfupload/(.*)','swfupload.zip')
		self.register_urlhandler('/admin/live_import/import',Importhandler)



	def get(self,page):
		return self.render_content("import.html",{'name':self.name})


########NEW FILE########
__FILENAME__ = sys_plugin
# -*- coding: utf-8 -*-
from micolog_plugin import *
import logging,re
from google.appengine.api import mail
from model import *
from google.appengine.api import users
from base import BaseRequestHandler,urldecode
from google.appengine.ext.webapp import template

SBODY='''New comment on your post "%(title)s"
Author : %(author)s
E-mail : %(email)s
URL	: %(weburl)s
Comment:
%(content)s
You can see all comments on this post here:
%(commenturl)s
'''

BBODY='''Hi~ New reference on your comment for post "%(title)s"
Author : %(author)s
URL	: %(weburl)s
Comment:
%(content)s
You can see all comments on this post here:
%(commenturl)s
'''

class NotifyHandler(BaseRequestHandler):
	def __init__(self):
		BaseRequestHandler.__init__(self)
		self.current="config"
		self.sbody=OptionSet.getValue('sys_plugin_sbody',SBODY)
		self.bbody=OptionSet.getValue('sys_plugin_bbody',BBODY)

	def get(self):
		self.template_vals.update({'self':self})
		content=template.render('plugins/sys_plugin/setup.html',self.template_vals)
		self.render2('views/admin/setup_base.html',{'m_id':'sysplugin_notify','content':content})
		#Also you can use:
		#self.render2('plugins/sys_plugin/setup2.html',{'m_id':'sysplugin_notify','self':self})

	def post(self):
		self.bbody=self.param('bbody')
		self.sbody=self.param('sbody')
		self.blog.comment_notify_mail=self.parambool('comment_notify_mail')
		self.blog.put()
		OptionSet.setValue('sys_plugin_sbody',self.sbody)
		OptionSet.setValue('sys_plugin_bbody',self.bbody)

		self.get()


class sys_plugin(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="System plugin for micolog"
		self.name="Sys Plugin"
		self.version="0.2"
		self.blocklist=OptionSet.getValue("sys_plugin_blocklist",default="")
		self.register_filter('head',self.head)
		self.register_filter('footer',self.footer)

		self.register_urlmap('sys_plugin/setup',self.setup)

		self.register_urlhandler('/admin/sys_plugin/notify',NotifyHandler)
		self.register_setupmenu('sysplugin_notify','Notify','/admin/sys_plugin/notify')

		self.register_action('pre_comment',self.pre_comment)
		self.register_action('save_comment',self.save_comment)
		self.sbody=OptionSet.getValue('sys_plugin_sbody',SBODY)
		self.bbody=OptionSet.getValue('sys_plugin_bbody',BBODY)

	def head(self,content,blog=None,*arg1,**arg2):
		content=content+'<meta name="generator" content="Micolog %s" />'%blog.version
		return content

	def footer(self,content,blog=None,*arg1,**arg2):
		return content+'<!--Powered by micolog %s-->'%blog.version

	def setup(self,page=None,*arg1,**arg2):
		if not page.is_login:
			page.redirect(users.create_login_url(page.request.uri))
		tempstr='''
		    <p>blocklist:</p>
			<form action="" method="post">
			<p>
			<textarea name="ta_list" style="width:400px;height:300px">%s</textarea>
			</p>
			<input type="submit" value="submit">
			</form>'''
		if page.request.method=='GET':
			page.render2('views/admin/base.html',{'m_id':'sysplugin_block','content':tempstr%self.blocklist})
		else:
			self.blocklist=page.param("ta_list")
			OptionSet.setValue("sys_plugin_blocklist",self.blocklist)
			page.render2('views/admin/base.html',{'m_id':'sysplugin_block','content':tempstr%self.blocklist})

	def get(self,page):
		return '''<h3>Sys Plugin</h3>
			   <p>This is a system plugin for micolog. <br>Also a demo for how to write plugin for micolog.</p>
			   <h4>feature</h4>
			   <p><ol>
			   <li>Add Meta &lt;meta name="generator" content="Micolog x.x" /&gt;</li>
			   <li>Add footer "&lt;!--Powered by micolog x.x--&gt;"</li>
			   <li>Comments Filter with blocklist <a href="/e/sys_plugin/setup">Setup</a></li>
			   <li>Comment Notify <a href="/admin/sys_plugin/notify">Setup</a></li>
			   </ol></p>
				'''

	def pre_comment(self,comment,*arg1,**arg2):
		for s in self.blocklist.splitlines():
			if comment.content.find(s)>-1:
				raise Exception

	def save_comment(self,comment,*arg1,**arg2):
		if self.blog.comment_notify_mail:
			self.notify(comment)

	def notify(self,comment):
		try:
						sbody=self.sbody.decode('utf-8')
		except:
						sbody=self.sbody
		try:
						bbody=self.bbody.decode('utf-8')
		except:
						bbody=self.bbody

		if self.blog.comment_notify_mail and self.blog.owner and not users.is_current_user_admin() :
			sbody=sbody%{'title':comment.entry.title,
						   'author':comment.author,
						   'weburl':comment.weburl,
						   'email':comment.email,
						   'content':comment.content,
						   'commenturl':comment.entry.fullurl+"#comment-"+str(comment.key().id())
						 }
			mail.send_mail_to_admins(self.blog.owner.email(),'Comments:'+comment.entry.title, sbody,reply_to=comment.email)

		#reply comment mail notify
		refers = re.findall(r'#comment-(\d+)', comment.content)
		if len(refers)!=0:
			replyIDs=[int(a) for a in refers]
			commentlist=comment.entry.comments()
			emaillist=[c.email for c in commentlist if c.reply_notify_mail and c.key().id() in replyIDs]
			emaillist = {}.fromkeys(emaillist).keys()
			for refer in emaillist:
				if self.blog.owner and mail.is_email_valid(refer):
						emailbody = bbody%{'title':comment.entry.title,
						   'author':comment.author,
						   'weburl':comment.weburl,
						   'email':comment.email,
						   'content':comment.content,
						   'commenturl':comment.entry.fullurl+"#comment-"+str(comment.key().id())
						 }
						message = mail.EmailMessage(sender = self.blog.owner.email(),subject = 'Comments:'+comment.entry.title)
						message.to = refer
						message.body = emailbody
						message.send()

########NEW FILE########
__FILENAME__ = wordpress
from micolog_plugin import *
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from wp_import import *
from model import *
import logging,math
from django.utils import simplejson
from base import BaseRequestHandler,urldecode


class waphandler(BaseRequestHandler):
	def get(self):
		if not self.is_login:
			self.redirect(users.create_login_url(self.request.uri))

		action=self.param('action')

		if action=='stop':
			memcache.delete("imt")
			#OptionSet.remove('wpimport_data')
			self.write('"ok"')
			return

		imt=memcache.get('imt')
		#imt=OptionSet.getValue('wpimport_data')
		if imt and imt.cur_do:
			process=100-math.ceil(imt.count()*100/imt.total)
			if imt.cur_do[0]=='cat':
				msg="importing category '%s'"%imt.cur_do[1]['name']
			elif imt.cur_do[0]=='entry':
				msg="importing entry '%s'"%imt.cur_do[1]['title']
			else:
				msg="start importing..."
			self.write(simplejson.dumps((process,msg,not process==100)))
		else:
			self.write(simplejson.dumps((-1,"Have no data to import!",False)))

	def post(self):
		if not self.is_login:
			self.redirect(users.create_login_url(self.request.uri))


		try:
				#global imt
				imt=memcache.get("imt")
				#imt=OptionSet.getValue('wpimport_data')
				import_data=imt.pop()
				#if tdata=='men':
				memcache.set('imt',imt)
				#else:
				#	OptionSet.setValue('wpimport_data',imt)
				try:
					cmtimport=memcache.get("cmtimport")
				except:
					cmtimport=False

				if import_data:
					try:
						if import_data[0]=='cat':

							_cat=import_data[1]
							nicename=_cat['slug']
							cat=Category.get_by_key_name(nicename)
							if not cat:
								cat=Category(key_name=nicename)
							cat.name=_cat['name']
							cat.slug=nicename
							cat.put()
						elif import_data[0]=='entry':
							_entry=import_data[1]
							logging.debug('importing:'+_entry['title'])
							hashkey=str(hash(_entry['title']))
							entry=Entry.get_by_key_name(hashkey)
							if not entry:
								entry=Entry(key_name=hashkey)

							entry.title=_entry['title']
							entry.author=self.login_user
							entry.is_wp=True
						   #entry.date=datetime.strptime( _entry['pubDate'],"%a, %d %b %Y %H:%M:%S +0000")
							try:
								entry.date=datetime.strptime( _entry['pubDate'][:-6],"%a, %d %b %Y %H:%M:%S")
							except:
								try:
									entry.date=datetime.strptime( _entry['pubDate'][0:19],"%Y-%m-%d %H:%M:%S")
								except:
									entry.date=datetime.now()
							entry.entrytype=_entry['post_type']
							entry.content=_entry['content']

							entry.excerpt=_entry['excerpt']
							entry.post_id=_entry['post_id']
							entry.slug=urldecode(_entry['post_name'])
							entry.entry_parent=_entry['post_parent']
							entry.menu_order=_entry['menu_order']

							for cat in _entry['categories']:
								c=Category.get_by_key_name(cat['slug'])
								if c:
									entry.categorie_keys.append(c.key())
							entry.settags(','.join(_entry['tags']))
				##				for tag in _entry['tags']:
				##					entry.tags.append(tag)
							if _entry['published']:
								entry.save(True)
							else:
								entry.save()
							if cmtimport:
								for com in _entry['comments']:
										try:
											date=datetime.strptime(com['date'][0:19],"%Y-%m-%d %H:%M:%S")
										except:
											date=datetime.now()
										comment=Comment(author=com['author'],
														content=com['content'],
														entry=entry,
														date=date
														)
										try:
											comment.email=com['email']
											comment.weburl=com['weburl']
										except:
											pass
										try:
											if len(com['ip'])>4:
												comment.ip=com['ip']
										except:
											pass
										comment.store()
					finally:
						queue=taskqueue.Queue("import")
						queue.add(taskqueue.Task( url="/admin/wp_import"))
		except Exception,e :
			logging.info("import error: %s"%e.message)


class wordpress(Plugin_importbase):
	def __init__(self):
		Plugin_importbase.__init__(self,__file__,"wordpress","Import posts, pages, comments, categories, and tags from a WordPress export file.")
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="Plugin for import wxr file."
		self.name="Wordpress Import"
		self.version="0.7"
		self.register_urlhandler('/admin/wp_import',waphandler)

	def get(self,page):
		return self.render_content("wpimport.html",{'name':self.name})

	def post(self,page):
		try:

			queue=taskqueue.Queue("import")
			wpfile=page.param('wpfile')
			#global imt
			imt=import_wordpress(wpfile)
			imt.parse()
			#OptionSet.setValue('wpimport_data',imt)
			cmtimport=page.parambool('importcomments')
			memcache.set("cmtimport",cmtimport,time=3600)
			

			memcache.set("imt",imt)
			queue.add(taskqueue.Task( url="/admin/wp_import"))
			return self.render_content("wpimport.html",{'postback':True})

		except Exception , e:

			return self.error("Import Error:<p  style='color:red;font-size:11px;font-weight:normal'>%s</p>"%e.message)

########NEW FILE########
__FILENAME__ = wp_import
###Import post,page,category,tag from wordpress export file
import xml.etree.ElementTree as et
import logging
###import from wxr file
class import_wordpress:
	def __init__(self,source):
		self.categories=[]
		self.tags=[]
		self.entries=[]

		self.source=source
		self.doc=et.fromstring(source)
		#use namespace
		self.wpns='{http://wordpress.org/export/1.0/}'

		self.contentns="{http://purl.org/rss/1.0/modules/content/}"
		self.excerptns="{http://wordpress.org/export/1.0/excerpt/}"
		et._namespace_map[self.wpns]='wp'
		et._namespace_map[self.contentns]='content'
		et._namespace_map[self.excerptns]='excerpt'
		self.channel=self.doc.find('channel')
		self.dict={'category':self.wpns+'category','tag':self.wpns+'tag','item':'item'}
		self.cur_do=None

	def parse(self):
		categories=self.channel.findall(self.wpns+'category')
		#parse categories

		for cate in categories:
			slug=cate.findtext(self.wpns+'category_nicename')
			name=cate.findtext(self.wpns+'cat_name')
			self.categories.append({'slug':slug,'name':name})
		#parse tags
		tags=self.channel.findall(self.wpns+'tag')

		for tag in tags:
			slug=tag.findtext(self.wpns+'tag_slug')
			name=tag.findtext(self.wpns+'tag_name')
			self.tags.append({'slug':slug,'name':name})

		#parse entries
		items=self.channel.findall('item')

		for item in items:
			title=item.findtext('title')
			try:
				entry={}
				entry['title']=item.findtext('title')
				logging.info(title)
				entry['pubDate']=item.findtext('pubDate')
				entry['post_type']=item.findtext(self.wpns+'post_type')
				entry['content']= item.findtext(self.contentns+'encoded')
				entry['excerpt']= item.findtext(self.excerptns+'encoded')
				entry['post_id']=int(item.findtext(self.wpns+'post_id'))
				entry['post_name']=item.findtext(self.wpns+'post_name')
				entry['post_parent']=int(item.findtext(self.wpns+'post_parent'))
				entry['menu_order']=int(item.findtext(self.wpns+'menu_order'))

				entry['tags']=[]
				entry['categories']=[]

				cats=item.findall('category')

				for cat in cats:
					if cat.attrib.has_key('nicename'):
						nicename=cat.attrib['nicename']
						cat_type=cat.attrib['domain']
						if cat_type=='tag':
							entry['tags'].append(cat.text)
						else:
							entry['categories'].append({'slug':nicename,'name':cat.text})

				pub_status=item.findtext(self.wpns+'status')
				if pub_status=='publish':
					entry['published']=True
				else:
					entry['published']=False

				entry['comments']=[]

				comments=item.findall(self.wpns+'comment')

				for com in comments:
					try:
						comment_approved=int(com.findtext(self.wpns+'comment_approved'))
					except:
						comment_approved=0
					if comment_approved:
						comment=dict(author=com.findtext(self.wpns+'comment_author'),
										content=com.findtext(self.wpns+'comment_content'),
										email=com.findtext(self.wpns+'comment_author_email'),
										weburl=com.findtext(self.wpns+'comment_author_url'),
										date=com.findtext(self.wpns+'comment_date'),
										ip=com.findtext(self.wpns+'comment_author_IP')
										)
					entry['comments'].append(comment)
				self.entries.append(entry)
			except:
				logging.info("parse wordpress file error")
		self.total=self.count()
		self.cur_do=("begin","begin")
		self.source=None
		self.doc=None

	def count(self):
		return len(self.categories)+len(self.entries)

	def pop(self):
		if len(self.categories)>0:
			self.cur_do=('cat',self.categories.pop())
			return self.cur_do

		if len(self.entries)>0:
			self.cur_do=('entry', self.entries.pop())
			return self.cur_do
		return None

	def __getstate__(self):
		if self.cur_do[0]=='cat':
			c=('cat',self.cur_do[1]['name'])
		elif self.cur_do[0]=='entry':
			c=('entry',self.cur_do[1]['title'])
		else:
			c=('begin','begin')
		return (c,self.total,self.categories,self.tags,self.entries)

	def __setstate__(self,data):
		c=data[0]
		if c[0]=='cat':
			self.cur_do=('cat',{'name':c[1]})
		elif c[0]=='entry':
			self.cur_do=('entry',{'title':c[1]})
		else:
			self.cur_do=c
		self.total,self.categories,self.tags,self.entries=data[1:]

if __name__=='__main__':
	import sys
	#f=sys.argv[1]
	f='D:\\work\\micolog\\wordpress.xml'
	wp=import_wordpress(open(f).read())
	wp.parse()

	print wp.count()
	item=wp.pop()
	while item:
		print item[0]
		item=wp.pop()


########NEW FILE########
__FILENAME__ = xheditor
from micolog_plugin import *
import logging,os
from model import *
from google.appengine.api import users
class xheditor(Plugin):
	def __init__(self):
		Plugin.__init__(self,__file__)
		self.author="xuming"
		self.authoruri="http://xuming.net"
		self.uri="http://xuming.net"
		self.description="xheditor."
		self.name="xheditor plugin"
		self.version="0.1"
		self.register_urlzip('/xheditor/(.*)','xheditor.zip')
		self.register_filter('editor_header',self.head)



	def head(self,content,blog=None,*arg1,**arg2):
		if blog.language=='zh_CN':
			js='xheditor-zh-cn.js'
		else:
			js='xheditor-en.js'
		sret='''<script type="text/javascript" src="/xheditor/%s"></script>
<script type="text/javascript">
$(function(){
  $("#content").xheditor(true,{
  upImgUrl:'!/admin/uploadex?ext=jpg|png|jpeg|gif',
  upFlashUrl:'!/admin/uploadex?ext=swf',
  upMediaUrl:'!/admin/uploadex?ext=wmv|avi|wma|mp3|mid'});
});

</script>'''%js
		return sret


	def get(self,page):
		return '''<h3>xheditor Plugin </h3>
			   <p>This is a demo for write editor plugin.</p>
			   <h4>feature</h4>
			   <p><ol>
			   <li>Change editor as xheditor.</li>
			   </ol></p>
				'''

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
# Django settings for the example project.
DEBUG = False
TEMPLATE_DEBUG = False

##LANGUAGE_CODE = 'zh-CN'
##LANGUAGE_CODE = 'fr'
LOCALE_PATHS = 'locale'
USE_I18N = True

TEMPLATE_LOADERS=('django.template.loaders.filesystem.load_template_source',
                    'ziploader.zip_loader.load_template_source')
########NEW FILE########
__FILENAME__ = theme_files
# -*- coding: utf-8 -*-
import  os,sys,stat
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
import wsgiref.handlers
from mimetypes import types_map
from datetime import  timedelta
from google.appengine.ext.webapp import template
from google.appengine.ext.zipserve import *
sys.path.append('modules')
from model import *

# {{{ Handlers

cwd = os.getcwd()
theme_path = os.path.join(cwd, 'themes')
file_modifieds={}

max_age = 600  #expires in 10 minutes
def Error404(handler):
    handler.response.set_status(404)
    html = template.render(os.path.join(cwd,'views/404.html'), {'error':404})
    handler.response.out.write(html)


class GetFile(webapp.RequestHandler):
    def get(self,prefix,name):
        request_path = self.request.path[8:]


        server_path = os.path.normpath(os.path.join(cwd, 'themes', request_path))
        try:
            fstat=os.stat(server_path)
        except:
            #use zipfile
            theme_file=os.path.normpath(os.path.join(cwd, 'themes', prefix))
            if os.path.exists(theme_file+".zip"):
                #is file exist?
                fstat=os.stat(theme_file+".zip")
                zipdo=ZipHandler()
                zipdo.initialize(self.request,self.response)
                return zipdo.get(theme_file,name)
            else:
                Error404(self)
                return


        fmtime=datetime.fromtimestamp(fstat[stat.ST_MTIME])
        if self.request.if_modified_since and self.request.if_modified_since.replace(tzinfo=None) >= fmtime:
            self.response.headers['Date'] = format_date(datetime.utcnow())
            self.response.headers['Last-Modified'] = format_date(fmtime)
            cache_expires(self.response, max_age)
            self.response.set_status(304)
            self.response.clear()

        elif server_path.startswith(theme_path):
            ext = os.path.splitext(server_path)[1]
            if types_map.has_key(ext):
                mime_type = types_map[ext]
            else:
                mime_type = 'application/octet-stream'
            try:
                self.response.headers['Content-Type'] = mime_type
                self.response.headers['Last-Modified'] = format_date(fmtime)
                cache_expires(self.response, max_age)
                self.response.out.write(open(server_path, 'rb').read())
            except Exception, e:
                Error404(self)
        else:
            Error404(self)

class NotFound(webapp.RequestHandler):
    def get(self):
         Error404(self)

#}}}

def format_date(dt):
    return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def cache_expires(response, seconds=0, **kw):
    """
    Set expiration on this request.  This sets the response to
    expire in the given seconds, and any other attributes are used
    for cache_control (e.g., private=True, etc).

    this function is modified from webob.Response
    it will be good if google.appengine.ext.webapp.Response inherits from this class...
    """
    if not seconds:
        # To really expire something, you have to force a
        # bunch of these cache control attributes, and IE may
        # not pay attention to those still so we also set
        # Expires.
        response.headers['Cache-Control'] = 'max-age=0, must-revalidate, no-cache, no-store'
        response.headers['Expires'] = format_date(datetime.utcnow())
        if 'last-modified' not in self.headers:
            self.last_modified = format_date(datetime.utcnow())
        response.headers['Pragma'] = 'no-cache'
    else:
        response.headers['Cache-Control'] = 'max-age=%d' % seconds
        response.headers['Expires'] = format_date(datetime.utcnow() + timedelta(seconds=seconds))

def main():
    application = webapp.WSGIApplication(
            [
                ('/themes/[\\w\\-]+/templates/.*', NotFound),
                ('/themes/(?P<prefix>[\\w\\-]+)/(?P<name>.+)', GetFile),
                ('.*', NotFound),
                ],
            debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = compile-messages
#!/usr/bin/env python

import optparse
import os
import sys

def compile_messages(locale=None):
    basedir = None

    if os.path.isdir(os.path.join('conf', 'locale')):
        basedir = os.path.abspath(os.path.join('conf', 'locale'))
    elif os.path.isdir('locale'):
        basedir = os.path.abspath('locale')
    else:
        print "This script should be run from the Django SVN tree or your project or app tree."
        sys.exit(1)

    if locale is not None:
        basedir = os.path.join(basedir, locale, 'LC_MESSAGES')

    for dirpath, dirnames, filenames in os.walk(basedir):
        for f in filenames:
            if f.endswith('.po'):
                sys.stderr.write('processing file %s in %s\n' % (f, dirpath))
                pf = os.path.splitext(os.path.join(dirpath, f))[0]
                # Store the names of the .mo and .po files in an environment
                # variable, rather than doing a string replacement into the
                # command, so that we can take advantage of shell quoting, to
                # quote any malicious characters/escaping.
                # See http://cyberelk.net/tim/articles/cmdline/ar01s02.html
                os.environ['djangocompilemo'] = pf + '.mo'
                os.environ['djangocompilepo'] = pf + '.po'
                if sys.platform == 'win32': # Different shell-variable syntax
                    cmd = 'msgfmt -o "%djangocompilemo%" "%djangocompilepo%"'
                else:
                    cmd = 'msgfmt -o "$djangocompilemo" "$djangocompilepo"'
                os.system(cmd)

def main():
    parser = optparse.OptionParser()
    parser.add_option('-l', '--locale', dest='locale',
            help="The locale to process. Default is to process all.")
    options, args = parser.parse_args()
    if len(args):
        parser.error("This program takes no arguments")
    compile_messages(options.locale)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = make-messages
#!/usr/bin/env python

# Need to ensure that the i18n framework is enabled
from django.conf import settings
settings.configure(USE_I18N = True)

from django.utils.translation import templatize
import re
import os
import sys
import getopt

pythonize_re = re.compile(r'\n\s*//')

def make_messages():
    localedir = None

    if os.path.isdir(os.path.join('conf', 'locale')):
        localedir = os.path.abspath(os.path.join('conf', 'locale'))
    elif os.path.isdir('locale'):
        localedir = os.path.abspath('locale')
    else:
        print "This script should be run from the django svn tree or your project or app tree."
        print "If you did indeed run it from the svn checkout or your project or application,"
        print "maybe you are just missing the conf/locale (in the django tree) or locale (for project"
        print "and application) directory?"
        print "make-messages.py doesn't create it automatically, you have to create it by hand if"
        print "you want to enable i18n for your project or application."
        sys.exit(1)

    (opts, args) = getopt.getopt(sys.argv[1:], 'l:d:va')

    lang = None
    domain = 'django'
    verbose = False
    all = False

    for o, v in opts:
        if o == '-l':
            lang = v
        elif o == '-d':
            domain = v
        elif o == '-v':
            verbose = True
        elif o == '-a':
            all = True

    if domain not in ('django', 'djangojs'):
        print "currently make-messages.py only supports domains 'django' and 'djangojs'"
        sys.exit(1)
    if (lang is None and not all) or domain is None:
        print "usage: make-messages.py -l <language>"
        print "   or: make-messages.py -a"
        sys.exit(1)

    languages = []

    if lang is not None:
        languages.append(lang)
    elif all:
        languages = [el for el in os.listdir(localedir) if not el.startswith('.')]

    for lang in languages:

        print "processing language", lang
        basedir = os.path.join(localedir, lang, 'LC_MESSAGES')
        if not os.path.isdir(basedir):
            os.makedirs(basedir)

        pofile = os.path.join(basedir, '%s.po' % domain)
        potfile = os.path.join(basedir, '%s.pot' % domain)

        if os.path.exists(potfile):
            os.unlink(potfile)

        for (dirpath, dirnames, filenames) in os.walk("."):
            for file in filenames:
                if domain == 'djangojs' and file.endswith('.js'):
                    if verbose: sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                    src = open(os.path.join(dirpath, file), "rb").read()
                    src = pythonize_re.sub('\n#', src)
                    open(os.path.join(dirpath, '%s.py' % file), "wb").write(src)
                    thefile = '%s.py' % file
                    cmd = 'xgettext %s -d %s -L Perl --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy --from-code UTF-8 -o - "%s"' % (
                        os.path.exists(potfile) and '--omit-header' or '', domain, os.path.join(dirpath, thefile))
                    (stdin, stdout, stderr) = os.popen3(cmd, 'b')
                    msgs = stdout.read()
                    errors = stderr.read()
                    if errors:
                        print "errors happened while running xgettext on %s" % file
                        print errors
                        sys.exit(8)
                    old = '#: '+os.path.join(dirpath, thefile)[2:]
                    new = '#: '+os.path.join(dirpath, file)[2:]
                    msgs = msgs.replace(old, new)
                    if msgs:
                        open(potfile, 'ab').write(msgs)
                    os.unlink(os.path.join(dirpath, thefile))
                elif domain == 'django' and (file.endswith('.py') or file.endswith('.html')):
                    thefile = file
                    if file.endswith('.html'):
                        src = open(os.path.join(dirpath, file), "rb").read()
                        open(os.path.join(dirpath, '%s.py' % file), "wb").write(templatize(src))
                        thefile = '%s.py' % file
                    if verbose: sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                    cmd = 'xgettext %s -d %s -L Python --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy --from-code UTF-8 -o - "%s"' % (
                        os.path.exists(potfile) and '--omit-header' or '', domain, os.path.join(dirpath, thefile))
                    (stdin, stdout, stderr) = os.popen3(cmd, 'b')
                    msgs = stdout.read()
                    errors = stderr.read()
                    if errors:
                        print "errors happened while running xgettext on %s" % file
                        print errors
                        sys.exit(8)
                    if thefile != file:
                        old = '#: '+os.path.join(dirpath, thefile)[2:]
                        new = '#: '+os.path.join(dirpath, file)[2:]
                        msgs = msgs.replace(old, new)
                    if msgs:
                        open(potfile, 'ab').write(msgs)
                    if thefile != file:
                        os.unlink(os.path.join(dirpath, thefile))

        if os.path.exists(potfile):
            (stdin, stdout, stderr) = os.popen3('msguniq "%s"' % potfile, 'b')
            msgs = stdout.read()
            errors = stderr.read()
            if errors:
                print "errors happened while running msguniq"
                print errors
                sys.exit(8)
            open(potfile, 'w').write(msgs)
            if os.path.exists(pofile):
                (stdin, stdout, stderr) = os.popen3('msgmerge -q "%s" "%s"' % (pofile, potfile), 'b')
                msgs = stdout.read()
                errors = stderr.read()
                if errors:
                    print "errors happened while running msgmerge"
                    print errors
                    sys.exit(8)
            open(pofile, 'wb').write(msgs)
            os.unlink(potfile)

if __name__ == "__main__":
    make_messages()

########NEW FILE########
__FILENAME__ = unique-messages
#!/usr/bin/env python

import os
import sys

def unique_messages():
    basedir = None

    if os.path.isdir(os.path.join('conf', 'locale')):
        basedir = os.path.abspath(os.path.join('conf', 'locale'))
    elif os.path.isdir('locale'):
        basedir = os.path.abspath('locale')
    else:
        print "this script should be run from the django svn tree or your project or app tree"
        sys.exit(1)

    for (dirpath, dirnames, filenames) in os.walk(basedir):
        for f in filenames:
            if f.endswith('.po'):
                sys.stderr.write('processing file %s in %s\n' % (f, dirpath))
                pf = os.path.splitext(os.path.join(dirpath, f))[0]
                cmd = 'msguniq "%s.po"' % pf
                stdout = os.popen(cmd)
                msg = stdout.read()
                open('%s.po' % pf, 'w').write(msg)

if __name__ == "__main__":
    unique_messages()

########NEW FILE########
__FILENAME__ = zip_loader
# Wrapper for loading templates from zipfile.
import zipfile,logging,os
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from django.template import TemplateDoesNotExist
from django.conf import settings
logging.debug("zipload imported")
zipfile_cache={}
_TEMPLATES_='templates'
def get_from_zipfile(zipfilename,name):
    logging.debug("get_from_zipfile(%s,%s)"%(zipfilename,name))
    zipfile_object = zipfile_cache.get(zipfilename)
    if zipfile_object is None:
      try:
        zipfile_object = zipfile.ZipFile(zipfilename)
      except (IOError, RuntimeError), err:
        logging.error('Can\'t open zipfile %s: %s', zipfilename, err)
        zipfile_object = ''
      zipfile_cache[zipfilename] = zipfile_object

    if zipfile_object == '':
      return None
    try:
      data = zipfile_object.read(name)
      return data
    except (KeyError, RuntimeError), err:
      return None

def get_template_sources(template_dirs=None):
    if not template_dirs:
        template_dirs = settings.TEMPLATE_DIRS
    for template_dir in template_dirs:
        if template_dir.endswith(".zip"):
            yield template_dir#os.path.join(template_dir, zip_name)

def load_template_source(template_name, template_dirs=None):
    tried = []
    logging.debug("zip_loader::load_template_source:"+template_name)
##    spart= template_name.split('/')
##    theme_name=spart[0]
##
##    zipfile=theme_name+".zip"
##    template_file=os.path.join(theme_name,*spart[1:])
    template_file='/'.join((_TEMPLATES_, template_name))
    for zipfile in get_template_sources(template_dirs):
        try:
            return get_from_zipfile(zipfile,template_file), os.path.join(zipfile,template_file)
        except IOError:
            tried.append(zipfile)
    if tried:
        error_msg = "Tried %s" % tried
    else:
        error_msg = "Your TEMPLATE_DIRS setting is empty. Change it to point to at least one template directory."
    raise TemplateDoesNotExist, error_msg

load_template_source.is_usable = True

########NEW FILE########
