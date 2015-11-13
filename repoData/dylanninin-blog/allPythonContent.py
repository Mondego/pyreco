__FILENAME__ = blog
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Blog App Entrance
version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
"""

import web
from config import urls

app = web.application(urls, globals())

if __name__ == "__main__":
    app.run()
########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
global configuration
version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
"""

import web

blogconfig = web.storage(
    name = 'Pastime Paradise',
    home = 'http://dylanninin.com',
    author = 'dylan',
    disqus = '"webpymdblog"',
    google_analytics = '"UA-21870463-1"',
    template_dir = 'template',
    entry_dir = 'raw/entry',
    page_dir = 'raw/page',
    tweet_dir = 'raw/tweet',
    static_dir = 'static',
    url_suffix = '.html',
    raw_suffix = '.md',
    index_url = '/',
    entry_url = '/blog',
    tweet_url = '/tweet',
    archive_url = '/archive',
    about_url = '/about.html',
    subscribe_url = '/atom.xml',
    error_url = '/error.html',
    favicon_url = '/favicon.ico',
    search_url = '/search',
    static_url = '/static',
    raw_url = '/raw',
    other_url = '(.+)',
    start = 1,
    limit = 5,
    pagination = 15,
    search_holder = 'search all site',
    time_fmt = '%Y-%m-%d %H:%M:%S',
    date_fmt = '%Y-%m-%d',
    url_fmt = 'yyyy/mm/dd',
    url_date_fmt = '%Y/%m/%d',
    recently = 10,
    ranks = 10,
    subscribe = 10,
    cache = False,
    debug = True,
)

web.config.debug = blogconfig.debug
render = web.template.render(blogconfig.template_dir, cache=blogconfig.cache)
web.template.Template.globals['config'] = blogconfig
web.template.Template.globals['render'] = render

urls = (
    blogconfig.index_url + '/?', 'controller.Index',
    blogconfig.entry_url + '(.*)','controller.Entry',
    blogconfig.archive_url + '(.*)', 'controller.Archive',
    blogconfig.about_url, 'controller.About',
    blogconfig.subscribe_url, 'controller.Subscribe',
    blogconfig.search_url + '?(.+)','controller.Search',
    blogconfig.raw_url + '(.*)','controller.Raw',
    blogconfig.favicon_url, 'controller.Image',
    blogconfig.other_url, 'controller.Error',
)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = controller
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Blog handler for urls
version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
"""

import os
import config
from __init__ import entryService

render = config.render
web = config.web
config = config.blogconfig

class Index:
    """
    Index Handler for /?
    example:
        /    
            request the index of this blog and list the first page of all
            entries of this blog from newest to oldest
            the default page size is 5 which is configured with config.limit
                
        /?start=1 
            equivalent with /
                
        /?start=1&limit=10
            request the second page with 10 entries
                
    template:
        template/index.html
        
    reference:
        config.py, model.py, service.py
    """
    def GET(self):
        params = web.input(start=config.start, limit=config.limit)
        limit = int(params.limit)
        start = int(params.start)
        params = entryService.search(entryService.types.index, config.index_url, '', start, limit)
        return render.index(params)


class Entry:
    """
    Entry Handler for /blog(.*)
        
    example:
        /blog
            the same as request /
                
        /blog/
            the same as request /blog/
                
        /blog/2013/06/20/webpy_introduction.html
            request entry with this url else error will be responsed
                
    template:
        template/entry.html, template/index.html

    reference:
        config.py, model.py, service.py
    """
    def GET(self, url):
        if not url in ['', '/']:
            url = config.entry_url + url
            params = entryService.find_by_url(entryService.types.entry, url)
            if params.entry == None:
                raise web.notfound(render.error(params))
            else:
                return render.entry(params)
        params = entryService.search(entryService.types.index, url)
        return render.index(params)


class Archive:
    """
    Archive Handler for /archive(.*)
    
    example:
        /archive
            request the archive of all posted entries on this blog
                
        /archive/
            the same as /archive
         
        /archive/2013
            request the archive of all posted entries on 2013
    
        /archive/2013/
            the same as /archive/2013
          
        /archive/2013/06
            request the archive of all posted entries on 2013/06
        
        /archive/2013/06/
            the same as /archive/2013/06
           
        /archive/2013/06/20
             request the archive of all posted entries 2013/06/20
          
        /archive/2013/06/20
            the same as /archive/2013/06/20
           
    template:
        template/archive.html
            
    reference:
        config.py, model.py, service.py
    """
    def GET(self, url):
        url= config.archive_url + url
        params = entryService.archive(entryService.types.entry, url)
        if params.entries == None:
            raise web.notfound(render.error(params))
        return render.archive(params)


class About:
    """
    Page Handler for /about.html
    
    template:
        template/entry.html
    
    reference:
        config.py, model.py, service.py
    """    
    def GET(self):
        url = config.about_url
        params = entryService.find_by_url(entryService.types.page, url)
        if params.entry == None:
            raise web.notfound(render.error(params))
        return render.entry(params)


class Subscribe:
    """
    Subscribe Handler for /atom.xml
    #TODO: FIXME: find related entries
    
    template:
        template/subscribe.xml
    
    reference:
        config.py, model.py, service.py
    """       
    def GET(self):
        params =  entryService.search(entryService.types.index, config.subscribe_url)
        web.header('Content-Type', 'text/xml')
        return render.atom(params)


class Search:
    """
    Search Handler for /search?type=type&value=value&start=start&limit=limit
    
    example:
        /search?type=query&value=input&start=1&limit=5
       
        /search?type=tag&value=webpy&start=1&limit=5
       
        /search?type=category&value=python
    
    template:
        template/search.html
        
    reference:
        config.py, model.py, service.py
    """
    def GET(self, url):
        params = web.input(type=entryService.types.query, value='',\
                           start=config.start, limit=config.limit)
        limit = int(params.limit)
        start = int(params.start)
        url = '%s/?type=%s&value=%s&start=%d&limit=%d' % (config.search_url, params.type, params.value, start, limit)
        params = entryService.search(params.type, url, params.value, start, limit)
        if not params.entries == None: 
            return render.search(params)
        raise web.notfound(render.error(params))

class Raw:
    """
    Raw Handler for /raw(.+)
    example:
        /raw
            request the archive of raw formats of all posted entries on this blog
                
        /raw/
            the same as /raw/
                
        /raw/2013/06/20/webpy_introduction.md
            request the raw content with url 2013/06/20/webpy_introduction.md
            and usually the rendered html url is 2013/06/20/webpy_introduction.html
                
        /raw/about.md
            request the raw content with url about.md its rendered html url is /abouts.html
                
    reference:
        config.py, model.py, service.py
    """
    def GET(self, url):
        url = config.raw_url + url
        raw = entryService.find_raw(url)
        if not raw == None:
            web.header('Context-Type', 'text/plain')
            web.header('Content-Encoding','utf-8')
            return raw
        params = entryService.archive(entryService.types.raw, url)
        if params.entries  == None:
            raise web.notfound(render.error(params))
        return render.archive(params)


class Image:
    """
    favicon.ico handler
        
    reference: 
        config.py
    """
    def GET(self):
        url = config.favicon_url
        name = url.lstrip('/')
        ext = name.split('.')[-1]
        cType = {
            "png":"images/png",
            "jpg":"images/jpeg",
            "gif":"images/gif",
            "ico":"images/x-icon"
        }
        if name in os.listdir(config.static_dir):
            web.header('Content-Type', cType[ext])
            return open('%s/%s' %(config.static_dir, name), 'rb').read()
        params =  entryService.error(url)
        raise web.notfound(render.error(params))


class Error():
    
    """
    Error Handler for any other url
        
    template:
        template/error.html
        
    reference:
        config.py, model.py, service.py
    """
    def GET(self, url):
        params = entryService.error(url)
        #return render.error(params)
        raise web.notfound(render.error(params))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
########NEW FILE########
__FILENAME__ = model
#!/usr/bin/env python
"""Models for the entry, page, templates, modules.

version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
2013-11-23    dylanninin@gmail.com     update default value for tag.rank

"""
# -*- coding: utf-8 -*-

import calendar
from datetime import datetime
from config import blogconfig as config
from tool import Dict2Object


class Models:
    """
    Models
    """
    def params(self):
        """
        parameters model for rendering templates

        reference:
            template/*/*
        """
        model ={
            'entries':None,
            'entry':None,
            'pager':None,
            'archive':None,
            'search':None,
            'subscribe':None,
            'error':None,
            'primary':{
                'abouts':None,
                'tags':None,
                'recently_entries':None,
            },
            'secondary':{
                'categories':None,
                'archive':None
            }
        }
        return Dict2Object(model)

    def entry(self, entry_type):
        """
        entry model for both entry and page

        args:
            entry_type: entry or page
                        entry is the one you'll post usually
                        page is just the one fulfills other parts of the blog, such as /about.html page

        reference:
            tempate/entry.html, templage/modules/entry.html
        """
        model = {
                 'author':{
                        'name':config.author,
                        'url':config.home
                           },
                 'path':'the path of the entry',
                 'name':'the displayed name of the entry',
                 'raw_url':'the url of the raw format of this entey',
                 'url':'the url of the entry in this blog',
                 'type':entry_type,
                 'status':'published',
                 'time':None,
                 'date':None,
                 'excerpt':'the excerpt of the entry',
                 'content':'the content of the entry',
                 'html':'the html content of the entry',
                 'tags':[],
                 'categories':[],
                 'count':0,
                 'raw_count':0
        }
        return Dict2Object(model)

    def search(self, search_type, value, total):
        """
        search model for queriery

        args:
            serach_type: seach by tag, category, keyword, and or just main index of the blog
            value: the keyword to be searched
            total: the number of result matching this search

        reference:
            template/search.html
        """
        model = {
            'type':search_type,
            'value':value,
            'title':str(total)+ ' ' + self.plurals('result', total) + ' matching "' + value + '" of ' + search_type
        }
        return  Dict2Object(model)

    def pager(self, pager_type, value, total=0, pages=1, start=config.start, limit=config.limit):
        """
        pager model for pagerbar

        args:
            pager_type: the type of this pagerbar, serach or main index
            value: current search value
            total: the number of total results
            pages: the number of pages
            start: current start page number
            limit: current page size, that is how many results displayed in one page

        reference:
            template/index.html, template/search.html
        """
        model ={
            'type':pager_type,
            'value':value,
            'total':total,
            'pages':pages,
            'start':start,
            'limit':limit,
            'pagination':[i for i in xrange(1, pages + 1)]
        }
        return Dict2Object(model)

    def archive(self, archive_type, archive_url, display, url, count=1):
        """
        archve model

        args:
            archive_type: the type of this archive, entry or raw
            archive_url: the url of this archive
            display: the title displayed
            url: current url of the archived item
            count: the number of archived items

        reference:
            template/archive.html, template/modules/archive.html
        """
        title = 'Archive ' + str(count) + ' '  +  self.plurals(archive_type, count) + ' of ' + display
        model = {
            'type':archive_type,
            'url':archive_url,
            'display':display,
            'title':title,
            'urls':[url],
            'count':count
        }
        return  Dict2Object(model)

    def subscribe(self, time):
        """
        subscribe model

        args:
            time: the last updated time of this blog

        reference:
            template/atom.xml
        """
        model = {
            'updated': time
        }
        return Dict2Object(model)

    def error(self, code='404', url=''):
        """
        error model

        args:
            code: error code
            url: the requested url brings out this error

        reference:
            template/error.html, template/modules/error.html
        """
        model = {
            'title': code + ' Not Found',
            'url':url,
            'statusCode':code,
            'message':'Oops! The requested url "' + url + '" could not be found...'
        }
        return Dict2Object(model)

    def about(self, about_type, prev_url=None, prev_name=None, next_url=None, next_name=None):
        """
        about model

        args:
            about_type: the type of this about, entry, or archive
            prev_url: the previous url
            prev_name: the name of previous url
            next_url: the next url
            next_name: the name of next url

        reference:
            template/widgets/about.html
        """
        model = {
            'type':about_type,
            'display':about_type.title(),
            'prev_url':prev_url,
            'prev_name':prev_name,
            'next_url':next_url,
            'next_name':next_name
        }
        return Dict2Object(model)

    def tag(self, tag, url):
        """
        tag model

        args:
            tag: the tag
            url: the entry url tagged by this tag

        reference:
            template/modules/tag.html, template/widgets/tag.html
        """
        model = {
            'name':tag,
            'count':1,
            'rank':config.ranks,
            'urls':[url]
        }
        return  Dict2Object(model)

    def category(self, category, url):
        """
        category model

        args:
            category: the category
            url: the entry url in this category

        reference:
            template/modules/category.html, template/widgets/category.html
        """
        model = {
            'name':category,
            'count':1,
            'rank':1,
            'subs':[],
            'urls':[url]
        }
        return  Dict2Object(model)

    def calendar(self, date):
        """
        calendar widget

        args:
            date: the date of current calendar

        reference:
            template/widgets/calendar.html
        """
        calendar.setfirstweekday(calendar.SUNDAY)
        ym = date[:len('yyyy-mm')]
        y, m, _ = [int(i) for i in date.split('-')]
        _, n = calendar.monthrange(y, m)
        urls = [None for _ in range(0, n + 1)]
        urls[0] = ''
        model = {
            'month':ym,
            'display':datetime(int(y), int(m), 1).strftime('%B %Y'),
            'days':calendar.monthcalendar(y, m),
            'urls':urls,
            'counts':[0 for _ in range(0, n+1)]
        }
        return Dict2Object(model)

    def monthly_archive(self, archive_type, month, url):
        """
        monthly archive model

        args:
            archive_type: the type of this archive
            month: current archived month
            url: the entry url of the archived item

        reference:
            template/widgets/archive.html
        """
        y, m , _ = month.split('/')
        display = datetime(int(y), int(m), 1).strftime('%B %Y')
        archive_url = config.archive_url + '/' +  month
        return  self.archive(archive_type, archive_url, display, url, 1)

    def plurals(self, key, count=0):
        """
        words model for its plural or singular form

        args:
            key: singular word
            count: 0, 1 or any number bigger than 1
        """
        words = {
            'entry':'entries',
            'raw':'raws',
            'tag':'tags',
            'category':'categories',
            'result':'results'
        }
        if count > 1 and not words.get(key) == None:
            return words.get(key)
        return key

    def types(self):
        """
        types model for miscellanies
        """
        model = {
        'blog':'blog',
        'entry':'entry',
        'page':'page',
        'raw':'raw',
        'query':'query',
        'tag':'tag',
        'category':'category',
        'index':'index',
        'add':'add',
        'delete':'delete',
        'archive':'archive',
        'all':'all'
        }
        return Dict2Object(model)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = service
#!/usr/bin/env python
"""Entry Service.

version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
2013-11-23    dylanninin@gmail.com     update tags, categories

"""
# -*- coding: utf-8 -*-

import os
import codecs
import re
import datetime
import random
import markdown
from config import blogconfig as config
from tool import Extract
from model import Models

extract = Extract()


class EntryService:
    """EntryService."""

    def __init__(self):
        self.entries = {}
        self.pages = {}
        self.urls = []
        self.by_tags = {}
        self.by_categories = {}
        self.by_months = {}
        self.models = Models()
        self.types = self.models.types()
        self.params = self.models.params()
        self._init_entries()

    def _init_entries(self):
        for root, _, files in os.walk(config.entry_dir):
            for f in files:
                self.add_entry(False, root + '/' + f)
        for root, _, files in os.walk(config.page_dir):
            for f in files:
                self._add_page(root + '/' + f)
        self._init_miscellaneous(self.types.add, self.entries.values())

    def add_entry(self, inotified, path):
        entry = self._init_entry(self.types.entry, path)
        if not entry == None:
            self.entries[entry.url] = entry
            if inotified:
                self._init_miscellaneous(self.types.add, [entry])

    def delete_entry(self, path):
        for entry in self.entries.values():
            if path == os.path.abspath(entry.path):
                self.entries.pop(entry.url)
                self._init_miscellaneous(self.types.delete, [entry])

    def _add_page(self, path):
        page = self._init_entry(self.types.page, path)
        if not page == None:
            self.pages[page.url] = page

    def _init_entry(self, entry_type, path):
        url, raw_url, name, date, time, content =  self._init_file(path, entry_type)
        if not url == None:
            entry = self.models.entry(entry_type)
            entry.path = path
            entry.name = name
            entry.url = url
            entry.raw_url = raw_url
            entry.date = date
            entry.time = time
            header, title, categories, tags = extract.parse(entry)
            entry.content = content
            content = content.replace(header, '')
            entry.html = markdown.markdown(content)
            entry.excerpt = content[:200] + ' ... ...'
            entry.categories = categories
            entry.tags = tags
            return entry
        return None

    def _init_file(self, file_path, entry_type):
        """
        #TODO: FIXME: how to determine the publish time of an entry
        """
        content, nones = None, [None for _ in xrange(6)]
        try:
            content = codecs.open(file_path, mode='r', encoding='utf-8').read()
        except:
            return nones
        if content == None or len(content.strip()) == 0:
            return nones
        date, mtime = None, None
        name, _ = os.path.splitext(os.path.basename(file_path))
        chars = ['_' ,'-', '~']
        pattern = r'\d{4}-\d{1,2}-\d{1,2}'
        match = re.search(pattern, name)
        if match:
            y, m, d = match.group().split('-')
            try:
                date = datetime.date(int(y), int(m), int(d))
            except:
                pass
            name = name[len(match.group()):]
            for c in chars:
                if name.startswith(c):
                    name = name[1:]
        stat = os.stat(file_path)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
        if date == None:
            date = mtime
        prefix, url_prefix, raw_prefix = date.strftime(config.url_date_fmt), '', ''
        if entry_type == self.types.entry:
            url_prefix = config.entry_url + '/' + prefix + '/'
            raw_prefix = config.raw_url + '/' + prefix + '/'
        if entry_type == self.types.page:
            url_prefix = '/'
            raw_prefix = config.raw_url + '/'
        date = date.strftime(config.date_fmt)
        time = date + mtime.strftime(config.time_fmt)[len('yyyy-mm-dd'):]
        url = url_prefix + name + config.url_suffix
        raw_url = raw_prefix + name + config.raw_suffix
        for c in chars:
            name = name.replace(c, ' ')
        return url, raw_url, name, date, time, content

    def _init_miscellaneous(self,init_type, entries):
        for entry in entries:
            self._init_tag(init_type, entry.url, entry.tags)
            self._init_category(init_type, entry.url, entry.categories)
            self._init_monthly_archive(init_type, entry.url)
        self.urls = sorted(self.entries.keys(), reverse=True)
        self._init_params()

    def _init_subscribe(self):
        time = None
        if self.urls == []:
            time = datetime.datetime.now().strftime(config.time_fmt)
        else:
            time = self.entries[self.urls[0]].time
        return self.models.subscribe(time)

    def _init_tag(self,init_type, url, tags):
        for tag in tags:
            if tag not in self.by_tags:
                if init_type == self.types.add:
                    self.by_tags[tag] = self.models.tag(tag, url)
                if init_type == self.types.delete:
                    pass
            else:
                if init_type == self.types.add:
                    self.by_tags[tag].urls.insert(0, url)
                    self.by_tags[tag].count += 1
                if init_type == self.types.delete:
                    self.by_tags[tag].count -= 1
                    self.by_tags[tag].urls.remove(url)
                    if self.by_tags[tag].count == 0:
                        self.by_tags.pop(tag)

    def _init_category(self, init_type, url, categories):
        for category in categories:
            if category not in self.by_categories:
                if init_type == self.types.add:
                    self.by_categories[category] = \
                    self.models.category(category, url)
                if init_type == self.types.delete:
                    pass
            else:
                if init_type == self.types.add:
                    self.by_categories[category].urls.insert(0, url)
                    self.by_categories[category].count += 1
                if init_type == self.types.delete:
                    self.by_categories[category].count -= 1
                    self.by_categories[category].urls.remove(url)
                    if self.by_categories[category].count == 0:
                        self.by_categories.pop(category)

    def _init_monthly_archive(self,init_type, url):
        start = len(config.entry_url) + 1
        end = start + len('/yyyy/mm')
        month = url[start:end]
        if month not in self.by_months:
            if init_type == self.types.add:
                self.by_months[month] = \
                self.models.monthly_archive(self.types.entry, month, url)
            if init_type == self.types.delete:
                pass
        else:
            if init_type == self.types.add:
                self.by_months[month].urls.insert(0, url)
                self.by_months[month].count += 1
            else:
                self.by_months[month].count -= 1
                self.by_months[month].urls.remove(url)
                if self.by_months[month].count == 0:
                    self.by_months.pop(month)

    def _init_params(self):
        self.params.subscribe = self._init_subscribe()
        self.params.primary.tags = self._init_tags_widget()
        self.params.primary.recently_entries = self._init_recently_entries_widget()
        self.params.secondary.categories = self._init_categories_widget()
        self.params.secondary.calendar = self._init_calendar_widget()
        self.params.secondary.archive = self._init_archive_widget()

    def _init_related_entries(self, url):
        """
        #TODO: FIXME: related entries
        """
        urls, index = [], 0
        try:
            index = self.urls.index(url)
        except:
            return None
        urls = self.urls[:index]
        urls.extend(self.urls[index + 1:])
        urls = random.sample(urls, min(len(urls), 10))
        return [self.entries.get(url) for url in sorted(urls, reverse=True)]

    def _init_abouts_widget(self, about_types=[], url=None):
        abouts = []
        for about_type in about_types:
            about = self.models.about(about_type)
            if about_type == self.types.entry and not url == None:
                try:
                    i = self.urls.index(url)
                    p, n = i + 1, i - 1
                except:
                    p, n = 999999999, -1
                if p < len(self.urls):
                    url = self.urls[p]
                    about.prev_url = url
                    about.prev_name = self.entries[url].name
                if n >= 0:
                    url = self.urls[n]
                    about.next_url = url
                    about.next_name = self.entries[url].name
            if about_type == self.types.archive:
                about.prev_url = '/'
                about.prev_name = 'main index'
            if about_type == self.types.blog:
                about.prev_url = '/'
                about.prev_name = 'main  index'
                about.next_url = config.archive_url
                about.next_name = 'archives'
            abouts.append(about)
        return abouts

    def _init_tags_widget(self):
        """
        #TODO: FIXME: calculate tags' rank
        """
        tags = sorted(self.by_tags.values(), key=lambda v:v.count, reverse=True)
        ranks = config.ranks
        div, mod = divmod(len(tags), ranks)
        if div == 0:
            ranks, div = mod, 1
        for r in range(ranks):
            s, e = r * div, (r + 1) * div
            for tag in tags[s:e]:
                tag.rank = r + 1
        return tags

    def _init_recently_entries_widget(self):
        return [self.entries[url] for url in self.urls[:config.recently]]

    def _init_calendar_widget(self):
        date = datetime.datetime.today().strftime(config.date_fmt)
        if len(self.urls)> 0:
            date = self.entries[self.urls[0]].date
        calendar = self.models.calendar(date)
        y, m = calendar.month.split('-')
        for url in self.urls:
            _, _, _, _, d, _ = url.split('/')
            prefix = config.entry_url + '/' +  y + '/' + m + '/' + d
            d = int(d)
            if url.startswith(prefix):
                calendar.counts[d] += 1
                if calendar.counts[d] > 1:
                    start = len(config.entry_url)
                    end = start + len('/yyyy/mm/dd')
                    calendar.urls[d] = config.archive_url + url[start:end]
                else:
                    calendar.urls[d] = url
            else:
                break
        return calendar

    def _init_categories_widget(self):
        return sorted(self.by_categories.values(), key=lambda c:c.name)

    def _init_archive_widget(self):
        return sorted(self.by_months.values(), key=lambda m:m.url, reverse=True)

    def _find_by_query(self, query, start, limit):
        """
        #TODO: FIXME: how to search in the content of entries
        """
        queries = [q.lower() for q  in query.split(' ')]
        urls = []
        for query in queries:
            for entry in self.entries.values():
                try:
                    entry.content.index(query)
                    urls.append(entry.url)
                except:
                    pass
        return self._find_by_page(sorted(urls), start, limit)

    def _find_by_page(self, urls, start, limit):
        if urls == None or start < 0 or limit <= 0:
            return [], 0
        total = len(urls)
        urls = sorted(urls, reverse=True)
        s, e = (start - 1) * limit, start * limit
        if s > total or s < 0:
            return [], 0
        return [self.entries[url] for url in urls[s:e]], total

    def _paginate(self, pager_type, value, total, start, limit):
        if limit <= 0:
            return self.models.pager(pager_type, value, total, 0, start, limit)
        pages, mod = divmod(total,limit)
        if mod > 0:
            pages += 1
        return self.models.pager(pager_type, value, total, pages, start, limit)

    def find_by_url(self, entry_type, url):
        entry, abouts = None, [self.types.blog]
        if entry_type == self.types.entry:
            entry = self.entries.get(url)
            abouts.insert(0, self.types.entry)
        if entry_type == self.types.page:
            entry = self.pages.get(url)
        self.params.entry = entry
        self.params.entries = self._init_related_entries(url)
        self.params.error = self.models.error(url=url)
        self.params.primary.abouts = self._init_abouts_widget(abouts, url)
        return self.params

    def find_raw(self, raw_url):
        page_url = raw_url.replace(config.raw_url, '').replace(config.raw_suffix, config.url_suffix)
        page = self.find_by_url(self.types.page, page_url).entry
        if not page== None and page.raw_url == raw_url:
            return page.content
        entry_url = raw_url.replace(config.raw_url, config.entry_url).replace(config.raw_suffix, config.url_suffix)
        entry = self.find_by_url(self.types.entry, entry_url).entry
        if not entry == None and entry.raw_url == raw_url:
            return entry.content
        return None

    def archive(self, archive_type, url, start=1, limit=999999999):
        self.params.error = self.models.error(url=url)

        if archive_type == self.types.raw:
            url = url.replace(config.raw_url,config.archive_url)

        entries, count, = [], 0
        archive_url = url.replace(config.archive_url, '').strip('/')
        prefix =  url.replace(config.archive_url, config.entry_url)
        pattern = r'\d{4}/\d{2}/\d{2}|\d{4}/\d{2}|\d{4}'
        match = re.search(pattern, archive_url)
        if match and match.group() == archive_url or archive_url == '':
            urls = [url for url in self.urls if url.startswith(prefix)]
            entries, _  =  self._find_by_page(urls, start, limit)
            count = len(entries)
        else:
            entries = None
        if archive_url == '':
            archive_url = self.types.all

        self.params.entries = entries
        self.params.archive = self.models.archive(archive_type, url, archive_url, url, count)
        self.params.primary.abouts = self._init_abouts_widget([self.types.archive])
        return self.params

    def search(self, search_type, url, value='', start=config.start, limit=config.limit):
        entries, total, abouts = None, 0, [self.types.blog]
        if  search_type == self.types.query:
            entries, total = self._find_by_query(value, start, limit)
        if search_type == self.types.tag:
            if self.by_tags.get(value) == None:
                entries = None
            else:
                entries, total = self._find_by_page(self.by_tags.get(value).urls, start, limit)
        if search_type == self.types.category:
            if self.by_categories.get(value) == None:
                entries = None
            else:
                entries, total = self._find_by_page(self.by_categories.get(value).urls, start, limit)
        if search_type == self.types.index:
            entries, total = self._find_by_page(self.urls, start, limit)
            abouts = []
        self.params.error = self.models.error(url=url)
        self.params.entries = entries
        self.params.search = self.models.search(search_type, value, total)
        self.params.pager = self._paginate(search_type, value, total, start, limit)
        self.params.primary.abouts = self._init_abouts_widget(abouts)
        return self.params

    def error(self, url):
        self.params.error = self.models.error(url=url)
        self.params.primary.abouts = self._init_abouts_widget([self.types.blog])
        return self.params


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = tool
#!/usr/bin/env python
"""ToolKit.

version 1.0
history:
2013-6-19    dylanninin@gmail.com    init
2013-11-23    dylanninin@gmail.com     update tags, categories

"""
# -*- coding: utf-8 -*-

import yaml


class Extract:
    """Extrace tool."""

    def __init__(self):
        """
        #TODO: FIXME: init
        """
        self.stop_words = []
        self.categories = ['Web', 'Linux', 'Database', 'Development']

    def auto_keyphrase(self, entry):
        """
        #TODO: FIXME: extract keyphrase automaticly

        reference:
            http://www.ruanyifeng.com/blog/2013/03/tf-idf.html
        """
        return self.categories

    def auto_categories(self, entry):
        """
        #TODO: FIXME: extract categories automaticly
        """
        return self.categories

    def auto_summarization(self, entry):
        """
        #TODO: FIXME: extract summarization automaticly

        reference:
            http://www.ruanyifeng.com/blog/2013/03/automatic_summarization.html
        """
        return entry.content[:200]

    def auto_similiarities(self, entry, entries):
        """
        #TODO: FIXME: extract similiarities  automaticly

        reference:
            http://www.ruanyifeng.com/blog/2013/03/cosine_similarity.html
        """
        return entries


    def parse(self, entry):
        """
        parse the raw content of a markdown entry
        TODO: FIXME ... ...

        args:
            filename:    the filename of a markdown entry

        return:
            a tuple like (yaml_header, title, categories, tags)
            the content will be preprocessed if it does have a yaml header declaration.

        yaml header field options:
            title
            category or categories
            tags

        blog example:
            ---
            title: the title, default None if it's empty
            category: category, default Uncategorised if it's empty.
            tags: [tag1, tag2], default [Untagged] if it's empty.
            ---

            ##header
            the content of the blog
            blah blah ...
            ... ...

        reference:
            http://jekyllrb.com/docs/frontmatter/

        """
        seperators = ['---\n', '---\r\n']
        newlines = ['\n', '\r\n']
        title = None
        categories = ['Uncategorised']
        tags = ['Untagged']
        number = 4
        yml = []
        header = ''
        with open(entry.path, 'r') as f:
            first = f.readline()
            if first in seperators:
                count, line = 1, f.readline()
                while count <= number and not line in seperators:
                    yml.append(line)
                    line = f.readline()
                    count += 1
                if len(yml) == 0 or not line in seperators or not f.readline() in newlines:
                    msg = 'Error, YAML header declaration with %s does not match in %s ' % (seperators, entry.path)
                    raise Exception(msg)
                skip = count + 2
                f.seek(0)
                header = ''.join([f.readline() for i in xrange(skip)])
        yml = ''.join(yml)
        if not yml == '':
            y = yaml.load(yml)
            title = y.get('title') or title
            categories = y.get('categories') or categories
            category = y.get('category')
            if not category == None:
                categories = [category]
            tags = y.get('tags') or tags
        return header, title, categories, tags


class Dict2Object(dict):
    """
    dict to object
    so you can access like a.attribute but not a['attribute']

    reference:
        http://stackoverflow.com/questions/1305532/convert-python-dict-to-object
    """
    def __init__(self, data = None):
        super(Dict2Object, self).__init__()
        if data:
            self.__update(data, {})

    def __update(self, data, did):
        dataid = id(data)
        did[dataid] = self

        for k in data:
            dkid = id(data[k])
            if did.has_key(dkid):
                self[k] = did[dkid]
            elif isinstance(data[k], Dict2Object):
                self[k] = data[k]
            elif isinstance(data[k], dict):
                obj = Dict2Object()
                obj.__update(data[k], did)
                self[k] = obj
                obj = None
            else:
                self[k] = data[k]

    def __getattr__(self, key):
        return self.get(key, None)

    def __setattr__(self, key, value):
        if isinstance(value,dict):
            self[key] = Dict2Object(value)
        else:
            self[key] = value

    def update(self, *args):
        for obj in args:
            for k in obj:
                if isinstance(obj[k],dict):
                    self[k] = Dict2Object(obj[k])
                else:
                    self[k] = obj[k]
        return self

    def merge(self, *args):
        for obj in args:
            for k in obj:
                if self.has_key(k):
                    if isinstance(self[k],list) and isinstance(obj[k],list):
                        self[k] += obj[k]
                    elif isinstance(self[k],list):
                        self[k].append(obj[k])
                    elif isinstance(obj[k],list):
                        self[k] = [self[k]] + obj[k]
                    elif isinstance(self[k],Dict2Object) and isinstance(obj[k],Dict2Object):
                        self[k].merge(obj[k] )
                    elif isinstance(self[k],Dict2Object) and isinstance(obj[k],dict):
                        self[k].merge(obj[k])
                    else:
                        self[k] = [self[k], obj[k]]
                else:
                    if isinstance(obj[k],dict):
                        self[k] = Dict2Object(obj[k])
                    else:
                        self[k] = obj[k]
        return self


if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
