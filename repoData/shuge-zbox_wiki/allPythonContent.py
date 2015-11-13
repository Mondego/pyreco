__FILENAME__ = migrate_from_trac_wiki_to_zwiki
#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
This script assists you migrate data from Trac Wiki to ZWiki.

NOTICE: it supports SQLite3 database backend only.


File migrate_from_trac_wiki_to_zwiki_conf.py *MUST* contains following variables:

- trac_db_path
    full_path of your trac wiki database file, i.e., "/path/to/trac-wiki-instance/db/trac.db"

- trac_wiki_attachments_path
    full_path of your trac wiki attachements folder, i.e., "/Users/lee/backups/enjoy-series/attachments/wiki"

- zwiki_pages_path
    full_path of your zwiki instance' pages folder, i.e., /path/to/zwiki/pages"

- zwiki_host
    i.e., "127.0.0.1:8080"
"""

import httplib
import os
import shutil
import urllib
import web

import tracwiki2markdown
import migrate_from_trac_wiki_to_zwiki_conf as conf

osp = os.path
PWD = osp.dirname(osp.realpath(__file__))
db = web.database(dbn="sqlite", db=conf.trac_db_path)


def get_page_file_or_dir_full_path_by_req_path(req_path):
    if not req_path.endswith("/"):
        return "%s.md" % osp.join(conf.zwiki_pages_path, req_path)
    else:
        return osp.join(conf.zwiki_pages_path, req_path)


def quote_plus_page_name(page_name):
    return "/".join([urllib.quote_plus(i) for i in page_name.split("/")])

def create_page(req_path, content):
    fixed_req_path = urllib.unquote(req_path.strip()).replace(" ", "-").lower()
    content = web.utils.safestr(content)
    content = tracwiki2markdown.tracwiki2markdown(content)
    fixed_req_path = web.utils.safestr(fixed_req_path)

    params = urllib.urlencode({'content': content})
    conn = httplib.HTTPConnection(conf.zwiki_host)
    conn.request("POST", "/%s?action=update" % fixed_req_path, params)
    response = conn.getresponse()

    if response.status == httplib.NOT_FOUND:
        print 'response.status: NOT_FOUND'
        exit(-1)


    try:
        assert response.status == httplib.MOVED_PERMANENTLY
        assert response.reason == "Moved Permanently"
    except  AssertionError:
        print "create `%s` failed" % req_path
        raise AssertionError

    data = response.read()

    assert data == 'None'

    conn.close()
    

def create_attachments(page_name):
    page_name = quote_plus_page_name(web.utils.safestr(page_name))
    attaches_full_path =  osp.join(conf.trac_wiki_attachments_path, page_name)

#    print "attaches_full_path:", attaches_full_path
#    print

    if not osp.exists(attaches_full_path):
        print "warning: `%s` not found" % attaches_full_path
        return


    fixed_page_name = urllib.unquote(page_name.strip()).replace(" ", "-").lower()
    save_to = osp.join(conf.zwiki_pages_path, fixed_page_name)
    parent = osp.dirname(save_to)

    if page_name.count("/") > 0:
        if not osp.exists(parent):
            os.makedirs(parent)

    attaches = os.listdir(attaches_full_path)
    attaches = [i for i in attaches if not i.startswith(".")]

    for i in attaches:
        src = osp.join(attaches_full_path, i)
        if not osp.isfile(src):
            continue

        page_file_full_path = get_page_file_or_dir_full_path_by_req_path(fixed_page_name)

        if osp.isfile(page_file_full_path):
            dst = osp.join(parent, i)
        else:
            dst = page_file_full_path

#        print "copy"
#        print "\tsrc: ", src
#        print "\tdst: ", dst
#        print

        shutil.copy(src, dst)



def get_page_latest_rev_by_name(name):
    name = web.utils.safeunicode(name)
    sql = 'select name, text, time from wiki where name = $name order by time desc limit 1'
#    sql = 'select name, text from wiki where version = (select max(version) from wiki where name = $name);'

    vars = {"name" : name}
    records = db.query(sql, vars=vars)
    for record in records:
        return record

def create_page_and_attachments_by_name(name):
    page = get_page_latest_rev_by_name(name)
    create_page(urllib.unquote(page["name"]), page["text"])
    create_attachments(page["name"])


def main():
    total = 0
    step = 100
    offset = 0
    sql = 'select DISTINCT name from wiki limit $limit offset $offset'
    vars = {
        'limit' : step,
        'offset' : offset
    }

    records = list(db.query(sql, vars=vars))
    while len(records) and len(records) == 100:

        total += len(records)

        for record in records:
            create_page_and_attachments_by_name(record["name"])

        vars["offset"] = vars["offset"] + 100
        records = list(db.query(sql, vars=vars))

        if len(records) < 100:
            total += len(records)

            for record in records:
                create_page_and_attachments_by_name(record["name"])


    print "total:", total


def test():
    name = 'System-Management/Plan9/Installing-Plan9-on-Qemu'
    print "page_name:", name

    page = get_page_latest_rev_by_name(name)

    create_page(urllib.unquote(page["name"]), page["text"])
    create_attachments(page["name"])


def test2():
    name = 'note/系统管理/代理'
    print "page_name:", name

    page = get_page_latest_rev_by_name(name)
    content = page["text"]

    content = tracwiki2markdown.tracwiki2markdown(content)
    with open('/tmp/t.html', 'w') as f:
        f.write(web.utils.safestr(content))


if __name__ == "__main__":
#    test()
#    test2()
    main()
########NEW FILE########
__FILENAME__ = tracwiki2markdown
#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Trac Wiki to Markdown

 - http://trac.edgewall.org/wiki/TracDev/DatabaseApi
 - http://trac.edgewall.org/wiki/TracDev/DatabaseSchema
 - http://trac.edgewall.org/browser/trunk/trac/wiki/web_ui.py
 - from trac.wiki import parser
 - https://gist.github.com/619537/94091aa59bdf6d6e5ad2fbb063465b2d160156ad

Trac Wiki Syntax

 - http://trac.edgewall.org/wiki/WikiFormatting

Markdown Refs

 - http://daringfireball.net/projects/markdown

Regular Expression Refs

 - http://luy.li/2010/05/12/python-re/
 - http://docs.python.org/howto/regex.html#regex-howto
"""

import re


def tracwiki2markdown(text):
    # TODO: add table filter
#    text = text.replace("\r\n", "\n")

    h6_p = "^======\s(.+?)\s======"
    h6_p_obj = re.compile(h6_p, re.MULTILINE)
    text = h6_p_obj.sub('###### \\1', text)

    h5_p = "^=====\s(.+?)\s====="
    h5_p_obj = re.compile(h5_p, re.MULTILINE)
    text = h5_p_obj.sub('##### \\1', text)

    h4_p = "^====\s(.+?)\s===="
    h4_p_obj = re.compile(h4_p, re.MULTILINE)
    text = h4_p_obj.sub('#### \\1', text)

    h3_p = "^===\s(.+?)\s==="
    h3_p_obj = re.compile(h3_p, re.MULTILINE)
    text = h3_p_obj.sub('### \\1', text)

    h2_p = "^==\s(.+?)\s=="
    h2_p_obj = re.compile(h2_p, re.MULTILINE)
    text = h2_p_obj.sub('## \\1', text)

    h1_p = "^=\s(.+?)\s="
    h1_p_obj = re.compile(h1_p, re.MULTILINE)
    text = h1_p_obj.sub('# \\1', text)

    link_p = "\[(http[^\s\[\]]+)\s([^\[\]]+)\]"
    link_p_obj = re.compile(link_p, re.MULTILINE)
    text = link_p_obj.sub('[\\2](\\1)', text)

    text = re.sub("\!(([A-Z][a-z0-9]+){2,})", '\\1', text)

    bold_italic_p = "'''''(.+?)'''''"
    bold_italic_p_obj = re.compile(bold_italic_p)
    text = bold_italic_p_obj.sub('***\\1***', text)

    bold_p = "'''(.+?)'''"
    bold_p_obj = re.compile(bold_p)
    text = bold_p_obj.sub('**\\1**', text)

    italic_p = "''(.+?)''"
    italic_p_obj = re.compile(italic_p)
    text = italic_p_obj.sub('*\\1*', text)

    italic_wiki_p = "//(.+?)//"
    italic_wiki_p_obj = re.compile(italic_wiki_p)
    text = italic_wiki_p_obj.sub('*\\1*', text)

    underline_p = "__(.+?)__"
    underline_p_obj = re.compile(underline_p)
    text = underline_p_obj.sub('<u>\\1</u>', text)

#    strike_p = "~~(.+?)~~"
#    strike_p_obj = re.compile(strike_p)
#    strike_p_obj.sub('~~\\1~~')

    sub_script_p = ",,(.+?),,"
    sub_script_p_obj = re.compile(sub_script_p)
    text = sub_script_p_obj.sub("<sub>\\1</sub>", text)

    super_script_p = "\^(.+?)\^"
    super_script_p_obj = re.compile(super_script_p)
    text = super_script_p_obj.sub("<sub>\\1</sub>", text)


#    def img_url_repl(matchobj):
#        groups = matchobj.groups(0)
#        args = [i.strip() for i in groups[0].split(',')]
#        url = args[0]
#        if url.startswith("wiki:"):
#            img_match_obj = re.match(r"wiki:(?:[^:]+?):(.+)", url)
#            if img_match_obj:
#                img_url = img_match_obj.groups()[0]
#                return '![alt](%s)' % img_url
#
#        return '![alt](\\1)'
#
#    img_p = r"\[\[Image\((.+?)\)\]\]"
#    img_p_obj = re.compile(img_p, re.MULTILINE)
#    text = img_p_obj.sub(img_url_repl, text)


    def img_url_repl(match_obj):
        img_url = match_obj.group("img_url")
        if img_url:
            if img_url.startswith("wiki:"):
                img_match_obj = re.match(r"wiki:(?:[^:]+?):(.+)", img_url)
                if img_match_obj:
                    img_url = img_match_obj.groups()[0]
                    return '![alt](%s)' % img_url

            return '![alt](%s)' % img_url
        return '~~missing image~~'

    img_url_p = r"\[\[Image\((?P<img_url>.+?),\s(?:.+?)\)\]\]"
    img_url_p_obj = re.compile(img_url_p, re.MULTILINE)
    text = img_url_p_obj.sub(img_url_repl, text)


    def img_url_repl(match_obj):
        img_url = match_obj.group('img_url')
        if img_url:
            if img_url.startswith("wiki:"):
                img_match_obj = re.match(r"wiki:(?:[^:]+?):(.+)", img_url)
                if img_match_obj:
                    img_url = img_match_obj.groups()[0]
                    return '![alt](%s)' % img_url

            return '![alt](%s)' % img_url
        return '~~missing image~~'

    img_url_p = r"\[\[Image\((?P<img_url>.+?)\)\]\]"
    img_url_p_obj = re.compile(img_url_p, re.MULTILINE)
    text = img_url_p_obj.sub(img_url_repl, text)

    return text


if __name__ == "__main__":
    pass

########NEW FILE########
__FILENAME__ = api
import os
import sys

PWD = os.path.dirname(os.path.realpath(__file__))
parent_path = os.path.dirname(PWD)

if parent_path not in sys.path:
    sys.path.insert(0, parent_path)

import zbox_wiki

web_url = 'http://0.0.0.0:8000/'
instance_full_path = os.path.join(parent_path, "zbox_wiki")
########NEW FILE########
__FILENAME__ = test_cache
#!/usr/bin/env python
import os
import api

config_agent = api.zbox_wiki.config_agent
config_path = os.path.join(api.instance_full_path, "/default.cfg")
config = config_agent.load_config([config_path], instance_full_path = api.instance_full_path)
api.zbox_wiki.config_agent.config = config

#print config_agent.config.get("paths", "instance_full_path")
#print config_agent.get_full_path("paths", "pages_path")

print api.zbox_wiki.cache.get_all_pages_list_from_cache(config_agent)
########NEW FILE########
__FILENAME__ = test_crud
#!/usr/bin/env python
#-*- coding:utf-8 -*-
import httplib
import os
import types

import BeautifulSoup
import config
import requests


content = """# this is a
the page name is a
"""

new_content = """# this is b
the page name is b
"""

def test_create_page():
    content_p = "the page name is a"
    page_name = "a"
    url = os.path.join(config.web_url + "~new")
    params = {"action" : "create"}
    data = {"path" : page_name, "content" : content}
    r = requests.post(url, data = data, params = params)
    assert r.status_code == httplib.SEE_OTHER

    url = os.path.join(config.web_url + page_name)
    r = requests.get(url)
    assert r.status_code == httplib.OK

    soup = BeautifulSoup.BeautifulSoup(r.text)
    tag_div = soup.findAll('div', id="content")[0]
    chunk = str(tag_div)
    assert chunk.find(content_p) != -1

    url = os.path.join(config.web_url + page_name)
    params = {"action" : "source"}
    r = requests.get(url, data = data, params = params)
    assert r.content_type
    assert r.text == content
    assert r.headers['content-type'] == "text/plain; charset=UTF-8"

def test_view_page_source():
    pass

def test_update_page():
    content_p = "the page name is b"
    page_name = "aaa"
    url = os.path.join(config.web_url + "~new")
    data = {"path": page_name, "content": content}
    r = requests.post(url, data = data, params = {"action": "create"})
    assert r.status_code == httplib.SEE_OTHER

    data = {"content" : new_content}
    r = requests.post(config.web_url, data = data, params = {"action" : "edit"})
    assert r.status_code == httplib.SEE_OTHER

    url = os.path.join(config.web_url + page_name)
    r = requests.get(url)
    assert r.status_code == httplib.OK

    soup = BeautifulSoup.BeautifulSoup(r.text)
    tag_div = soup.findAll('div', id="content")[0]
    chunk = str(tag_div)
    assert chunk.find(content_p) != -1

    url = os.path.join(config.web_url + page_name)
    params = {"action" : "source"}
    r = requests.get(url, data = data, params = params)
    assert r.content_type
    assert r.text == content
    assert r.headers['content-type'] == "text/plain; charset=UTF-8"


def test_delete_page():
    pass

def test_rename_page():
    pass


def test_view_folder_source():
    pass

def test_update_folder():
    pass

def test_delete_folder():
    pass

def test_rename_folder():
    pass

def main_suck():
    keys = locals().keys()
    for key in keys:
        obj = locals()[key]
        if isinstance(obj, types.FunctionType):
            func = obj
            if func.func_name.startswith("test_"):
                func()

if __name__ == "__main__":
    main_suck()
#    import nose
#    nose.main()
########NEW FILE########
__FILENAME__ = test_element
import atom
from lxml import etree


def test_element():
    e = atom.Element(name="name", text="Mark Pilgrim")
#    assert str(e) == "<name>Mark Pilgrim</name>\n"

    tree = etree.fromstring(str(e))
    assert tree.attrib == {}
    assert tree.tag == "name"
    assert tree.text == "Mark Pilgrim"
    assert (not tree.getchildren())

def test_element_with_attributes():
    e = atom.Element(name="name", text="Mark Pilgrim", age=18, sex="man")
#    assert str(e) == '<name age="18" sex="man">Mark Pilgrim</name>\n'

    tree = etree.fromstring(str(e))
    assert tree.attrib == {'age': '18', 'sex': 'man'}
    assert tree.text == "Mark Pilgrim"
    assert (not tree.getchildren())

def test_element_with_children():
    child = atom.Element(name="name", text="Mark Pilgrim")
    parent = atom.Element(name="author")
    parent.append_children(child)
#    assert str(parent) == (
#        "<author>\n"
#        "  <name>Mark Pilgrim</name>\n"
#        "</author>\n"
#    )

    tree = etree.fromstring(str(parent))
    assert tree.attrib == {}
    assert tree.tag == "author"
    assert tree.text.strip() == ""
    assert len(tree.getchildren()) == 1

    child_tree = tree.getchildren()[0]
    assert child_tree.attrib == {}
    assert child_tree.tag == "name"
    assert child_tree.text.strip() == "Mark Pilgrim"
    assert (not child_tree.getchildren())

if __name__ == "__main__":
    test_element()
    test_element_with_attributes()
    test_element_with_children()
########NEW FILE########
__FILENAME__ = test_entry
import atom
from lxml import etree


def test_entry():
    e_link = atom.Element(name="link", href="http://example.org/2003/12/13/atom03")
    entry = atom.Entry(title="Atom-Powered Robots Run Amok",
                       link = e_link,
                       id="urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a",
                       updated="2003-12-13T18:30:02Z",
                       summary="Some text.")
#    assert str(entry) == (
#        "<entry>\n"
#        "  <summary>Some text.</summary>\n"
#        "  <updated>2003-12-13T18:30:02Z</updated>\n"
#        "  <link href=\"http://example.org/2003/12/13/atom03\"/>\n"
#        "  <title>Atom-Powered Robots Run Amok</title>\n"
#        "  <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>\n"
#        "</entry>\n"
#        )

    tree = etree.fromstring(str(entry))
    assert tree.attrib == {}
    assert tree.tag == "entry"
    assert not tree.text.strip()
    assert len(tree.getchildren()) == 5

    e_summary = tree.xpath("/entry/summary")[0]
    assert e_summary.attrib == {}
    assert e_summary.tag == "summary"
    assert e_summary.text.strip() == "Some text."

    e_updated = tree.xpath("/entry/updated")[0]
    assert e_updated.attrib == {}
    assert e_updated.tag == "updated"
    assert e_updated.text.strip() == "2003-12-13T18:30:02Z"

    e_link = tree.xpath("/entry/link")[0]
    assert e_link.attrib == {'href' : "http://example.org/2003/12/13/atom03"}
    assert e_link.tag == "link"
    assert not e_link.text


if __name__ == "__main__":
    test_entry()
########NEW FILE########
__FILENAME__ = test_feed
import atom
from lxml import etree


def test_feed():
    e_link = atom.Element(name="link",
                          href="http://example.org/2003/12/13/atom03")
    entry = atom.Entry(title="Atom-Powered Robots Run Amok",
                       link=e_link,
                       id="urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a",
                       updated="2003-12-13T18:30:02Z",
                       summary="Some text.")

    e_author = atom.Element(name="author")
    e_author.set_preverse_attrs("name", "John Doe")
    e_link = atom.Element(name="link", href="http://example.org/")
    feed = atom.Feed(title="Example Feed",
                     link=e_link,
                     updated="2003-12-13T18:30:02Z",
                     author=e_author,
                     id="urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6")
    feed.append_children(entry)

    buf = str(feed)
#    assert buf == (
#        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
#        "  <feed xmlns=\"http://www.w3.org/2005/Atom\">\n"
#        "  <title>Example Feed</title>\n"
#        "  <link href=\"http://example.org/\"/>\n"
#        "  <updated>2003-12-13T18:30:02Z</updated>\n"
#        "  <author>\n"
#        "    <name>John Doe</name>\n"
#        "  </author>\n"
#        "  <id>urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6</id>\n"
#        "  <entry>\n"
#        "    <title>Atom-Powered Robots Run Amok</title>\n"
#        "    <link href=\"http://example.org/2003/12/13/atom03\"/>\n"
#        "    <id>urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a</id>\n"
#        "    <updated>2003-12-13T18:30:02Z</updated>\n"
#        "    <summary>Some text.</summary>\n"
#        "  </entry>\n"
#        "</feed>\n"
#        )

    tree = etree.fromstring(buf)


if __name__ == "__main__":
    test_feed()
########NEW FILE########
__FILENAME__ = test_mdutils
import api

def test_path2hierarchy():
    for i in [
        ("/", [("index", "/~index")]), # name, link pairs

        ("/system-management/gentoo/abc",
         [("system-management", "/system-management"),("gentoo", "/system-management/gentoo"),("abc", "/system-management/gentoo/abc"),]),

        ("/programming-language",
         [("programming-language", "/programming-language"),]),

        ("/programming-language/",
         [("programming-language", "/programming-language"),]),
                                       ]:
        req_path = i[0]
        links = i[1]
        assert api.zbox_wiki.mdutils.path2hierarchy(req_path) == links
########NEW FILE########
__FILENAME__ = test_paginator
import api

def test_paginator():
    po = api.zbox_wiki.paginator.Paginator()

    po.total = 10
    po.limit = 3

    po.current_offset = 0
    assert po.count == 4
    assert po.has_previous_page == False
    assert po.has_next_page == True

    po.current_offset = 1
    assert po.count == 4
    assert po.has_previous_page == True
    assert po.has_next_page == True

    po.current_offset = 2
    assert po.count == 4
    assert po.has_previous_page == True
    assert po.has_next_page == True

    po.current_offset = 3
    assert po.count == 4
    assert po.has_previous_page == True
    assert po.has_next_page == False
########NEW FILE########
__FILENAME__ = test_req_path_to_local_full_path
import os
import api

def test_req_path_to_local_full_path():
    config_agent = api.zbox_wiki.config_agent
    config_path = os.path.join(api.instance_full_path, "default.cfg")
    config = config_agent.load_config([config_path], instance_full_path = api.instance_full_path)
    api.zbox_wiki.config_agent.config = config


    folder_pages_full_path = config.get("paths", "pages_path")

    for req_path, expected in (
            ("sandbox1", '/tmp/pages/sandbox1.md'),
            ("sandbox1/", '/tmp/pages/sandbox1/'),
            ("hacking/fetion/fetion-protocol/", '/tmp/pages/hacking/fetion/fetion-protocol/'),
            ("hacking/fetion/fetion-protocol/method-option.md", '/tmp/pages/hacking/fetion/fetion-protocol/method-option.md'),
            ("~all", '/tmp/pages/'),
            ("/", '/tmp/pages/'),
            ("", '/tmp/pages/')
        ):
        got = api.zbox_wiki.mdutils.req_path_to_local_full_path(req_path = req_path, folder_pages_full_path = folder_pages_full_path)
        assert got == expected

test_req_path_to_local_full_path()
########NEW FILE########
__FILENAME__ = test_shell
import os
from zbox_wiki_api import zbox_wiki

instance_full_path = os.path.join(os.getenv("HOME"), "sandbox/proj/man/")

config_agent = zbox_wiki.config_agent
config_full_path = os.path.join(instance_full_path, "/default.cfg")
config = config_agent.load_config([config_full_path], instance_full_path = instance_full_path)
zbox_wiki.config_agent.config = config


folder_pages_full_path = config_agent.config.get("paths", "pages_path")

req_path = "~all"
print zbox_wiki.shell.get_page_file_list_by_req_path(folder_pages_full_path, req_path)

req_path = "."
print zbox_wiki.shell.get_page_file_list_by_req_path(folder_pages_full_path,
                                                     req_path)

req_path = "sa/"
print zbox_wiki.shell.get_page_file_list_by_req_path(folder_pages_full_path,
                                                     req_path)

########NEW FILE########
__FILENAME__ = acl
import functools

from config_agent import config
import commons
import web


def _check_ip(req_obj, req_path):
    # allow_ips = ("192.168.0.10", )
    allow_ips = commons.netutils.INVALID_REMOTE_IP_ADDRESSES
    remote_ip = web.ctx.get("ip")
    return True
    # uncomment following to disallow access from WAN
#    if not remote_ip:
#        return False
#
#    if not commons.ip_in_network_ranges(remote_ip, allow_ips):
#        return False
#
#    return True

def check_ip(f):
    @functools.wraps(f)
    def wrapper(req_obj, req_path):
        if _check_ip(req_obj, req_path):
            return f(req_obj, req_path)

        raise web.Forbidden()
    return wrapper


def _check_rw(req_obj, req_path):
    inputs = web.input()
    action = inputs.get("action", "read")

    if config.getboolean("main", "readonly"):
        if (action not in ("read", "source")) or (req_path == "~new"):
            return False

    return True

def check_rw(f):
    @functools.wraps(f)
    def wrapper(req_obj, req_path):
        if _check_rw(req_obj, req_path):
            return f(req_obj, req_path)
        raise web.Forbidden()
    return wrapper

########NEW FILE########
__FILENAME__ = atom
"""
TODO: separate this file into a individual module
"""
import logging
import time


logging.getLogger("atom").setLevel(logging.DEBUG)

wrap = lambda name, text : "<%s>%s</%s>" % (name, text, name)


def generate_updated(ts=None):
    """
    http://tools.ietf.org/html/rfc4287#section-3.3
    http://www.w3.org/TR/1998/NOTE-datetime-19980827
    """
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))


class NotConfirmToRFC(Exception):
    def __init__(self, msg, *args, **kwargs):
        self.msg = msg
        super(NotConfirmToRFC, self, *args, **kwargs)


class Element(object):

    def __init__(self, name, text = "", **kwargs):
        self._name = name
        self._text = text
        self._attributes = kwargs
        self._children = []

    def __str__(self):
        chunks = []
        for k, v in self._attributes.iteritems():
            chunk = "%s=\"%s\"" % (k, v)
            chunks.append(chunk)
        attrs_in_str = " ".join(chunks)

        if attrs_in_str.strip():
            attrs_in_str = " " + attrs_in_str

        if not self._text:
            chunks = []
            for child in self._children:
                if isinstance(child, (tuple, list)):
                    chunk_list = ["  %s" % str(i) for i in child]
                    chunks.extends(chunk_list)
                else:
                    chunk = "  %s" % str(child)
                    chunks.append(chunk)
            text = "\n".join(chunks)

            if text.strip():
                text = "\n" + text
        else:
            text = self._text

        if text:
            buf = "<%s%s>%s</%s>\n" % (self._name, attrs_in_str, text, self._name)
        else:
            buf = "<%s%s/>\n" % (self._name, attrs_in_str)
        return buf

    @property
    def name(self):
        return self._name

    @property
    def text(self):
        return self._text

    @property
    def children(self):
        return (v
            for k, v in self.__dict__.iteritems()
            if isinstance(v, Element))

    def append_children(self, child):
        self._children.append(child)

    def set_preverse_attrs(self, k, v):
        """ walk around for
         `e_author = atom.Element(name="author", name="John Doe")`

         `e_author = atom.Element(name="author")`
         `e_author.set_preverse_attrs("name", "John Doe")`
         ->
         <author>
           <name>Join Doe</name>
        </author>
        """
        assert k in ("name", "text")
        self._attributes[k] = v


class AtomElement(Element):

    def _init(self, **kwargs):
        for k, v in kwargs.iteritems():
            if k not in self.__dict__:
                msg = "un-expected key `%s`" % k
                logging.error(msg)
                raise KeyError

            if isinstance(v, Element):
                self.__dict__[k] = v
            elif isinstance(v, basestring):
                self.__dict__[k] = Element(name=k, text=v)
            else:
                msg = "expected `%s`'s value in (Element, basestring), got `%s`" % (k, str(v))
                logging.error(msg)
                raise TypeError


class Entry(AtomElement):

    def __init__(self, **kwargs):
        super(Entry, self).__init__(name="entry")

        self.author = None
        self.category = None
        self.content = None
        self.contributor = None
        self.id = None

        self.link = None
        self.published = None
        self.rights = None
        self.source = None
        self.summary = None

        self.title = None
        self.updated = None
        self.extensionElement = None

        self._multiple_elements = ("category", "contributor")
        self._single_elements = ("published", "rights", "source", "summary", "title", "updated")

        self._required = ("id", "title", "updated")

        self._init(**kwargs)

    def __str__(self):
        for k in self._required:
            if not self.__dict__[k]:
                msg = "expected Entry:%s is not None, got None" % k
                logging.error(msg)
                raise NotConfirmToRFC(msg)

        if (not self.content) and (not self.link):
            msg = "expected Entry:content or entry:link is not None, got both None"
            raise NotConfirmToRFC(msg)

        old_children = self._children[:]
        self._children.extend(self.children)
        buf = super(Entry, self).__str__()
        self._children = old_children

        return buf


class Feed(AtomElement):
    TEMPLATE = (
        "<?xml version=\"1.0\" encoding=\"utf-8\" ?>\n"
        "%s"
        )

    def __init__(self, **kwargs):
        super(Feed, self).__init__(name="feed", xmlns="http://www.w3.org/2005/Atom")

        self.author = None
        self.category = None
        self.contributor = None
        self.generator = None
        self.icon = None

        self.id = None
        self.link = None
        self.logo = None
        self.rights = None
        self.subtitle = None

        self.title = None
        self.updated = None
        self.extensionElement = None

        self._multiple_elements = ("category", "contributor")
        self._single_elements = ("generator", "icon", "logo", "rights", "subtitle")

        self._required = ("id", "title", "updated")

        self._init(**kwargs)

    def __str__(self):
        for k in self._required:
            if not self.__dict__[k]:
                msg = "expected Feed:%s is not None, got None" % k
                logging.error(msg)
                raise NotConfirmToRFC(msg)

        if not self.author:
            for obj in self._children:
                if (not obj.author) and (not obj.source):
                    msg = "expected Atom:author is not None, or Entry:author and Entry:source is not None, got both None"
                    raise NotConfirmToRFC(msg)

        old_children = self._children[:]
        self._children.extend(self.children)
        buf = super(Feed, self).__str__()
        self._children = old_children
        buf = Feed.TEMPLATE % buf

        return buf

########NEW FILE########
__FILENAME__ = atom_output
#!/usr/bin/env python
import cgi
import os

import commons
import atom
import cache
import mdutils
import page
import static_file


def generate_feed(config_agent, req_path, tpl_render):
    folder_pages_full_path  = config_agent.config.get("paths", "pages_path")
    cache_file_full_path = os.path.join(folder_pages_full_path, ".zw_all_pages_list_cache")

    buf = cache.get_all_pages_list_from_cache(config_agent)
    md_list = buf.split()

    author = config_agent.config.get("main", "maintainer_email") or "Anonymous"

    e_author = atom.Element(name="author")
    child = atom.Element(name="name", text=author)
    e_author.append_children(child)

    ts = os.stat(cache_file_full_path).st_ctime
    updated = atom.generate_updated(ts)
    ts_as_id = "timestamp:" + commons.strutils.md5(updated)

    feed = atom.Feed(author=e_author, id=ts_as_id, updated=updated, title="Testing Feed Output")
    for md_file_name in md_list[:100]:
        req_path = commons.strutils.rstrips(md_file_name, ".md")
        req_path = commons.strutils.rstrips(req_path, ".markdown")
        local_full_path = mdutils.req_path_to_local_full_path(req_path, folder_pages_full_path)

        raw_text = commons.shutils.cat(local_full_path)
        page_title = mdutils.get_title_by_file_path_in_md(folder_pages_full_path, req_path)

        static_file_prefix = static_file.get_static_file_prefix_by_local_full_path(
            config_agent = config_agent,
            local_full_path = local_full_path,
            req_path = req_path)
        view_settings = page.get_view_settings(config_agent)
        page_content = mdutils.md2html(config_agent = config_agent,
                                  req_path = req_path,
                                  text = raw_text,
                                  static_file_prefix = static_file_prefix,
                                  **view_settings)

        text = cgi.escape(commons.strutils.safestr(page_content))
        e_content = atom.Element(name="content", text=text, type="html")
        if not page_title:
            continue

        hash_title_as_id = "md5:" + commons.strutils.md5(page_title)
        updated = atom.generate_updated(os.stat(local_full_path).st_ctime)
        entry = atom.Entry(id=hash_title_as_id,
                           title=page_title,
                           updated=updated,
                           content=e_content)
        feed.append_children(entry)

    buf = str(feed)
    return buf

########NEW FILE########
__FILENAME__ = cache
from __future__ import with_statement

import os
import time

import shell
import web


def update_recent_change_cache(folder_pages_full_path):
    path = os.path.join(folder_pages_full_path, ".zw_recent_changes_cache")
    buf = shell.get_page_file_list_by_req_path(folder_pages_full_path = folder_pages_full_path,
                                              req_path = "~recent", sort_by_modified_ts = True)

    with open(path, "w") as f:
        f.write(buf)

def get_recent_changes_from_cache(config_agent):
    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    path = os.path.join(folder_pages_full_path, ".zw_recent_changes_cache")

    if os.path.exists(path):
        stat = os.stat(path)

        if (time.time() - stat.st_mtime) > config_agent.config.getint("cache", "cache_update_interval"):
            update_recent_change_cache(folder_pages_full_path)
    else:
        update_recent_change_cache(folder_pages_full_path)

    with open(path) as f:
        buf = f.read()

    return web.utils.safeunicode(buf)

def update_all_pages_list_cache(folder_pages_full_path):
    buf = shell.get_page_file_list_by_req_path(folder_pages_full_path = folder_pages_full_path, req_path = "~all")
    path = os.path.join(folder_pages_full_path, ".zw_all_pages_list_cache")

    with open(path, "w") as f:
        f.write(buf)

def get_all_pages_list_from_cache(config_agent):
    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    path = os.path.join(folder_pages_full_path, ".zw_all_pages_list_cache")

    if os.path.exists(path):
        stat = os.stat(path)

        if (time.time() - stat.st_mtime) > config_agent.config.getint("cache", "cache_update_interval"):
            update_all_pages_list_cache(folder_pages_full_path)
    else:
        update_all_pages_list_cache(folder_pages_full_path)

    with open(path) as f:
        buf = f.read()

    return web.utils.safeunicode(buf)


########NEW FILE########
__FILENAME__ = config_agent
import ConfigParser
import os
import logging

logging.getLogger("config_agent").setLevel(logging.DEBUG)

__all__ = [
    "default_file_path",
    "load_config",
]


PWD = os.path.dirname(os.path.realpath(__file__))
default_file_path = os.path.join(PWD, "default.cfg")


def load_config(paths = None, instance_full_path = None):
    if paths:
        paths.insert(0, default_file_path)
    else:
        paths = [default_file_path]

    config = ConfigParser.SafeConfigParser()
    try:
        config.read(paths)
    except ConfigParser.Error:
        msg = "parsing configuration file %s failed. " \
            "upgrade your instance:" + "\n\n" +\
            "    zwdadmin.py upgrade <full path to instance>" + "\n\n" +\
            "if it still doesn't works, try re-install ZboxWiki" % default_file_path
        logging.exception(msg)

    maintainer_email = config.get("main", "maintainer_email")
    if maintainer_email:
        splits = maintainer_email.split("@")
        config.set("main", "maintainer_email_prefix", splits[0])
        config.set("main", "maintainer_email_suffix", splits[1])

    if instance_full_path:
        config.set("paths", "instance_full_path", instance_full_path)
        old_path = config.get("paths", "pages_path")
        if not os.path.isabs(old_path):
            pages_full_path = os.path.join(instance_full_path, config.get("paths", "pages_path"))
            config.set("paths", "pages_path", pages_full_path)

    return config


config = load_config()


def get_full_path(section, name):
    global config
    rel_path = config.get(section, name)
    instance_full_path = config.get("paths", "instance_full_path") or PWD
    rel2full_path = os.path.join(instance_full_path, rel_path)

    if os.path.exists(rel_path):
        path_fixed = rel_path
    elif os.path.exists(os.path.realpath(rel_path)):
        path_fixed = os.path.realpath(rel_path)
    elif os.path.exists(rel2full_path):
        path_fixed = rel2full_path
    elif (not os.path.exists(rel_path)):
        raise IOError("'%s' doesn't exists" % rel_path)
    else:
        raise IOError("composing full path of '%s' failed" % rel_path)

    return path_fixed


if __name__ == "__main__":
    path = os.path.join(os.getenv("HOME"), "lees_wiki", "default.cfg")
    paths = [path]
    my_config = load_config(paths)
    t =  my_config.getint("main", "version")
    print type(t), repr(t)

    t =  my_config.get("frontend", "home_link_name")
    print t
########NEW FILE########
__FILENAME__ = consts

g_redirect_paths = ("favicon.ico", "robots.txt")
g_special_paths = ("~all", "~recent", "~search", "~settings", "~stat", "~new", "~atom")
g_actions = ("update", "read", "rename", "delete", "source")
########NEW FILE########
__FILENAME__ = graphviz2png
#!/usr/bin/env python
"""
This script requires

 * PyGraphviz (python-pygraphviz on Ubuntu)

References

  - Trac Graphviz Plugin
"""
import os
import pygraphviz

__all__ = [
    "dot_text2png",
    "dot_file2png",
]


def dot_text2png(text, png_path, prog = "dot"):
    """ generate a image/png file from 'text' and write into 'png_path'.  """
    text = text.strip()
    filename = str(hash(text)).replace("-", "")
    fullname = filename + ".png"

    if os.path.isdir(png_path):
        save_to_prefix = png_path
    else:
        save_to_prefix = os.path.dirname(png_path)

    png_path = os.path.join(save_to_prefix, fullname)

    if os.path.exists(png_path):
        return png_path

#    print "generating ..."

    g = pygraphviz.AGraph(text)
    g.layout(prog = prog)
    g.draw(png_path)

    return png_path


def dot_file2png(dot_path, png_path):
    """ generate a image/png file from 'dot_path' and write into 'png_path'.  """
    text = file(dot_path).read()

    return dot_text2png(text = text, png_path = png_path)


test_text = """digraph G {
    rankdir = "LR"

    GraphvizPlugin[ URL = GraphvizPlugin ]

    ZBoxWiki[
      URL = "http://wiki.shuge-lab.org"
      fontcolor = red
    ]

    GraphvizPlugin -> ZBoxWiki
}
"""

if __name__ == "__main__":
    save_to_prefix = "/tmp/zbox_wiki_graphviz_demo"
    if not os.path.exists(save_to_prefix):
        os.makedirs(save_to_prefix)

    png_path = save_to_prefix
    png_path = "/tmp/zbox_wiki_graphviz_demo/9071973128666914760.png"
    dst_path = dot_text2png(test_text, png_path)

    msg = "save to: " + dst_path
    print msg


########NEW FILE########
__FILENAME__ = macro_cat
#!/usr/bin/env python
import logging
import os
import re
import commons

logging.getLogger("macro_cat").setLevel(logging.DEBUG)


def match_in_re(name, patterns):
    for p in patterns:
        re_obj = re.compile(p)
        if re_obj.match(name):
            return True

    return False

def get_files_list(path, ignore_patterns = ['^\.(.+?)$', '^(.+?)~$'], match_patterns = None):
    """ `ignore_patterns` is a list of regular expressions, ignore '.DS_Store', 'foo~' etc by default. """
    files = []
    for pending_filename in os.listdir(path):
        if ignore_patterns:
            if match_in_re(name = pending_filename, patterns = ignore_patterns):
                continue
        if match_patterns:
            if not match_in_re(name = pending_filename, patterns = match_patterns):
                continue
        files.append(pending_filename)
    return files


def fix_pattern(p):
    try:
        re.compile(p)
    except:
        if p.startswith("*.") and p.count("*.") == 1:
            suffix = p.split("*.")[-1]
            fixed = "^(.+?)\.%s$" % suffix
            return fixed
        else:
            msg = "expected regular expression or '*.suffix' style expression, got `%s`" % p
            logging.error(msg)
            return None

    return p


def parse_work_path(file_name, folder_pages_full_path, req_path):
    if os.path.exists(file_name):
        return file_name

    elif file_name.find("/") != -1:
        par = os.path.dirname(file_name)
        if os.path.exists(par):
            return par

        file_full_path = os.path.join(folder_pages_full_path, par)
        if os.path.exists(file_full_path):
            return file_full_path

    default_work_path = os.path.join(folder_pages_full_path, req_path)
    if req_path:
        par = os.path.dirname(default_work_path)
        if os.path.exists(par):
            return par

    return default_work_path


def cat_files(work_path, files):
    all = ""
    for filename in files:
        full_path = os.path.join(work_path, filename)
        chunk = filename + "\n"
        with open(full_path) as f:
            buf = commons.strutils.safeunicode(f.read())
            buf = "\n    ".join(buf.split("\n"))
            buf = commons.strutils.rstrips(buf, "    ")
            chunk += "\n\n    " + buf
        chunk += "\n"
        all += chunk

    return all


def macro_zw2md_cat(text, folder_pages_full_path, req_path, **view_settings):
    shebang_p = "#!zw"
    code_p = '(?P<code>[^\f\v]+?)'
    code_block_p = "^\{\{\{[\s]*%s*%s[\s]*\}\}\}" % (shebang_p, code_p)
    p_obj = re.compile(code_block_p, re.MULTILINE)

    def code_repl(match_obj):
        code = match_obj.group('code')
        code = code.split("\n")[1]

        if code.startswith("cat("):
            p = 'cat\((?P<file_name>.+?)\)'
            m = re.match(p, code, re.UNICODE | re.MULTILINE)
            file_name = m.group("file_name")
            file_name = file_name.strip()
            work_path = parse_work_path(file_name = file_name, folder_pages_full_path = folder_pages_full_path, req_path = req_path)

            match_pattern = file_name.strip("'").strip("\"")
            match_pattern = commons.strutils.lstrips(match_pattern, work_path)
            match_pattern = commons.strutils.strips(match_pattern, "/")
            match_pattern = fix_pattern(match_pattern)

            files = get_files_list(path = work_path, match_patterns = [match_pattern])

            buf = cat_files(work_path = work_path, files = files)
            return buf

#        return code
        buf_fixed = "{{{#!zw\n%s\n}}}" % code
        return buf_fixed

    return p_obj.sub(code_repl, text)

def test_fix_pattern():
    auto_patterns = (
        ("*.md", "^(.+?)\.md$"),
        ("^(.+?)\.md$", "^(.+?)\.md$"),
    )

    for e, g in auto_patterns:
        assert fix_pattern(e) == g


def test_macro_cat():
    text = """
{{{#!zw
cat("*.md")
}}}
"""
    req_path = ""
    folder_pages_full_path = "/tmp/lees_wiki/pages/"
    result = macro_zw2md_cat(text = text, folder_pages_full_path = folder_pages_full_path, req_path = req_path)
    result = commons.strutils.strips(result, "\n")
    print repr(result)


if __name__ == "__main__":
    test_fix_pattern()
    test_macro_cat()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#-*- coding:utf-8 -*-
import cgi
import os

# ship web.py with this project for walking around custom static files folder bug
import web

import acl
import atom_output
import consts
import commons
import page
import config_agent


web.config.debug = True


# declare for using in scripts/fcgi_main.py
__all__ = [
    "main",
    "web",
    "mapping",
    "Robots",
    "SpecialWikiPage",
    "WikiPage",
]


mapping = (
    "/robots.txt", "Robots",
    "/favicon.ico", "FaviconICO",
    "/(~[a-zA-Z0-9_\-/.]+)", "SpecialWikiPage",
    ur"/([a-zA-Z0-9_\-/.%s]*)" % commons.CJK_RANGE, "WikiPage",
)

app = web.application(mapping, globals())
folder_templates_full_path = config_agent.get_full_path("paths", "templates_path")
tpl_render = web.template.render(folder_templates_full_path)


def setup_session_folder_full_path():
    global session

    if not web.config.get("_session"):
        folder_sessions_full_path = config_agent.get_full_path("paths", "sessions_path")
        session = web.session.Session(app, web.session.DiskStore(folder_sessions_full_path), initializer = {"username": None})
        web.config._session = session
    else:
        session = web.config._session


def fix_403_msg():
    maintainer_email = config_agent.config.get("main", "maintainer_email")

    if maintainer_email:
        ro_tpl_p1 = """Page you request doesn't exists, and this site is READONLY. <br />
You could fork it and commit the changes, then send a pull request to the maintainer: <br />

<pre><code>%s</code></pre>"""

        # simple E-mail wrapper in CSS
        email = maintainer_email.replace("@", " &lt;AT&gt; ")
        buf = ro_tpl_p1 % email

        repo_url = config_agent.config.get("main", "repository_url")
        if repo_url:
            buf += "<pre><code>    git clone %s</code></pre>" % repo_url

        web.Forbidden.message = buf


class WikiPage(object):
    @acl.check_ip
    @acl.check_rw
    def GET(self, req_path):
        req_path = cgi.escape(req_path)

        inputs = web.input()
        action = inputs.get("action", "read")
        if action not in consts.g_actions:
            raise web.BadRequest()

        if action == "read":
            return page.wp_read(config_agent = config_agent, req_path = req_path, tpl_render = tpl_render)
        elif action == "update":
            return page.wp_update(config_agent = config_agent, req_path = req_path, tpl_render = tpl_render)
        elif action == "rename":
            return page.wp_rename(config_agent = config_agent, req_path = req_path, tpl_render = tpl_render)
        elif action == "delete":
            return page.wp_delete(config_agent = config_agent, req_path = req_path, tpl_render = tpl_render)
        elif action == "source":
            return page.wp_source(config_agent = config_agent, req_path = req_path, tpl_render = tpl_render)
        else:
            raise web.BadRequest()

    @acl.check_ip
    @acl.check_rw
    def POST(self, req_path):
        req_path = cgi.escape(req_path)

        inputs = web.input()
        action = inputs.get("action")
        if (not action) or (action not in ("update", "rename")):
            raise web.BadRequest()

        new_content = inputs.get("content")
        new_content = web.utils.safestr(new_content)

        if action == "update":
            if (req_path in consts.g_special_paths) or (req_path in consts.g_redirect_paths) or req_path.endswith("/"):
                raise web.BadRequest()

            return page.wp_update_post(config_agent = config_agent, req_path = req_path, new_content = new_content)

        elif action == "rename":
            new_path = inputs.get("new_path")
            if (req_path in consts.g_special_paths) or (req_path in consts.g_redirect_paths) or (not new_path):
                raise web.BadRequest()

            return page.wp_rename_post(config_agent = config_agent, tpl_render = tpl_render, req_path = req_path, new_path = new_path)

        url = os.path.join("/", req_path)
        web.redirect(url)
        return


class SpecialWikiPage(object):
    @acl.check_ip
    @acl.check_rw
    def GET(self, req_path):
        inputs = web.input()

        FIRST_PAGE = 0
        offset = int(inputs.get("offset", FIRST_PAGE))

        page_limit = config_agent.config.getint("pagination", "page_limit")
        limit = int(inputs.get("limit", page_limit))

        if req_path == "~recent":
            return page.wp_get_recent_changes_from_cache(config_agent = config_agent,
                                                         tpl_render = tpl_render,
                                                         req_path = req_path,
                                                         limit = limit,
                                                         offset = offset)
        elif req_path == "~all":
            return page.wp_get_all_pages(config_agent = config_agent,
                                         tpl_render = tpl_render,
                                         req_path = req_path,
                                         limit = limit, offset = offset)
        elif req_path == "~settings":
            return page.wp_view_settings(config_agent = config_agent,
                                         tpl_render = tpl_render,
                                         req_path = req_path)
        elif req_path == "~stat":
            return page.wp_stat(config_agent = config_agent,
                                tpl_render = tpl_render,
                                req_path = req_path)
        elif req_path == "~new":
            return page.wp_new(config_agent = config_agent,
                               tpl_render = tpl_render,
                               req_path = req_path)
        elif req_path == "~atom":
            buf = atom_output.generate_feed(config_agent = config_agent, req_path = req_path, tpl_render = tpl_render)
            web.header("Content-Type", "text/xml; charset=utf-8")
            return buf
        else:
            return web.BadRequest()

    @acl.check_ip
    @acl.check_rw
    def POST(self, req_path):
        inputs = web.input()
            
        if req_path == "~search":
            return page.wp_search(config_agent = config_agent, tpl_render = tpl_render, req_path = req_path)

        elif req_path == "~settings":
            show_full_path = inputs.get("show_full_path")
            auto_toc = inputs.get("auto_toc")
            highlight_code = inputs.get("highlight_code")

            if show_full_path == "on":
                show_full_path = 1
            else:
                show_full_path = 0
            web.setcookie(name = "zw_show_full_path", value = show_full_path, expires = 31536000)

            if auto_toc == "on":
                auto_toc = 1
            else:
                auto_toc = 0
            web.setcookie(name = "zw_auto_toc", value = auto_toc, expires = 31536000)

            if highlight_code == "on":
                highlight_code = 1
            else:
                highlight_code = 0
            web.setcookie(name = "zw_highlight", value = highlight_code, expires = 31536000)


            latest_req_path = web.cookies().get("zw_latest_req_path")

            if latest_req_path and (latest_req_path not in consts.g_redirect_paths) and latest_req_path != "/":
                web.setcookie(name = "zw_latest_req_path", value = "", expires = -1)
                latest_req_path = "/" + latest_req_path
            else:
                latest_req_path = "/"

            return web.seeother(latest_req_path)

        elif req_path == "~new":
            buf_path = inputs.get("path")
            buf_path = commons.strutils.lstrips(buf_path, "/")
            buf_path = commons.strutils.rstrips(buf_path, ".md")
            fixed_path = commons.strutils.rstrips(buf_path, ".markdown")
            if (not fixed_path) or (fixed_path in consts.g_special_paths) or (fixed_path in consts.g_redirect_paths):
                raise web.BadRequest()

            content = inputs.get("content")
            content = web.utils.safestr(content)
            if not content:
                raise web.BadRequest()

            page.wp_create(config_agent = config_agent, req_path = req_path, path = fixed_path, content = content)
            return

        else:
            raise web.NotFound()


class Robots(object):
    def GET(self):
        folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
        path = os.path.join(folder_pages_full_path, "robots.txt")
        content = commons.shutils.cat(path)

        web.header("Content-Type", "text/plain")
        return content


class FaviconICO(object):
   def GET(self):
       folder_static_full_path = config_agent.get_full_path("paths", "static_path")
       path = os.path.join(folder_static_full_path, "favicon.ico")

       if not os.path.exists(path):
           raise web.NotFound()

       with open(path) as f:
           content = f.read()

       web.header("Content-Type", "image/vnd.microsoft.icon")
       return content


def fix_pages_path_symlink(proj_root_full_path):
    src_full_path = os.path.join(proj_root_full_path, "pages")
    dst_full_path = os.path.join(proj_root_full_path, "static", "pages")

    if os.path.islink(dst_full_path) and os.readlink(dst_full_path) != src_full_path:
        if os.path.islink(dst_full_path):
            os.remove(dst_full_path)

    if not os.path.exists(dst_full_path):
        os.symlink(src_full_path, dst_full_path)

def main(instance_root_full_path):
    web.config.static_path = config_agent.get_full_path("paths", "static_path")

    fix_pages_path_symlink(instance_root_full_path)
    fix_403_msg()

    setup_session_folder_full_path()
    app.run()


########NEW FILE########
__FILENAME__ = blockparser

import util
import odict

class State(list):
    """ Track the current and nested state of the parser. 
    
    This utility class is used to track the state of the BlockParser and 
    support multiple levels if nesting. It's just a simple API wrapped around
    a list. Each time a state is set, that state is appended to the end of the
    list. Each time a state is reset, that state is removed from the end of
    the list.

    Therefore, each time a state is set for a nested block, that state must be 
    reset when we back out of that level of nesting or the state could be
    corrupted.

    While all the methods of a list object are available, only the three
    defined below need be used.

    """

    def set(self, state):
        """ Set a new state. """
        self.append(state)

    def reset(self):
        """ Step back one step in nested state. """
        self.pop()

    def isstate(self, state):
        """ Test that top (current) level is of given state. """
        if len(self):
            return self[-1] == state
        else:
            return False

class BlockParser:
    """ Parse Markdown blocks into an ElementTree object. 
    
    A wrapper class that stitches the various BlockProcessors together,
    looping through them and creating an ElementTree object.
    """

    def __init__(self, markdown):
        self.blockprocessors = odict.OrderedDict()
        self.state = State()
        self.markdown = markdown

    def parseDocument(self, lines):
        """ Parse a markdown document into an ElementTree. 
        
        Given a list of lines, an ElementTree object (not just a parent Element)
        is created and the root element is passed to the parser as the parent.
        The ElementTree object is returned.
        
        This should only be called on an entire document, not pieces.

        """
        # Create a ElementTree from the lines
        self.root = util.etree.Element(self.markdown.doc_tag)
        self.parseChunk(self.root, '\n'.join(lines))
        return util.etree.ElementTree(self.root)

    def parseChunk(self, parent, text):
        """ Parse a chunk of markdown text and attach to given etree node. 
        
        While the ``text`` argument is generally assumed to contain multiple
        blocks which will be split on blank lines, it could contain only one
        block. Generally, this method would be called by extensions when
        block parsing is required. 
        
        The ``parent`` etree Element passed in is altered in place. 
        Nothing is returned.

        """
        self.parseBlocks(parent, text.split('\n\n'))

    def parseBlocks(self, parent, blocks):
        """ Process blocks of markdown text and attach to given etree node. 
        
        Given a list of ``blocks``, each blockprocessor is stepped through
        until there are no blocks left. While an extension could potentially
        call this method directly, it's generally expected to be used internally.

        This is a public method as an extension may need to add/alter additional
        BlockProcessors which call this method to recursively parse a nested
        block.

        """
        while blocks:
           for processor in self.blockprocessors.values():
               if processor.test(parent, blocks[0]):
                   processor.run(parent, blocks)
                   break



########NEW FILE########
__FILENAME__ = blockprocessors
"""
CORE MARKDOWN BLOCKPARSER
=============================================================================

This parser handles basic parsing of Markdown blocks.  It doesn't concern itself
with inline elements such as **bold** or *italics*, but rather just catches 
blocks, lists, quotes, etc.

The BlockParser is made up of a bunch of BlockProssors, each handling a 
different type of block. Extensions may add/replace/remove BlockProcessors
as they need to alter how markdown blocks are parsed.

"""

import logging
import re
import util
from blockparser import BlockParser

logger =  logging.getLogger('MARKDOWN')


def build_block_parser(md_instance, **kwargs):
    """ Build the default block parser used by Markdown. """
    parser = BlockParser(md_instance)
    parser.blockprocessors['empty'] = EmptyBlockProcessor(parser)
    parser.blockprocessors['indent'] = ListIndentProcessor(parser)
    parser.blockprocessors['code'] = CodeBlockProcessor(parser)
    parser.blockprocessors['hashheader'] = HashHeaderProcessor(parser)
    parser.blockprocessors['setextheader'] = SetextHeaderProcessor(parser)
    parser.blockprocessors['hr'] = HRProcessor(parser)
    parser.blockprocessors['olist'] = OListProcessor(parser)
    parser.blockprocessors['ulist'] = UListProcessor(parser)
    parser.blockprocessors['quote'] = BlockQuoteProcessor(parser)
    parser.blockprocessors['paragraph'] = ParagraphProcessor(parser)
    return parser


class BlockProcessor:
    """ Base class for block processors. 
    
    Each subclass will provide the methods below to work with the source and
    tree. Each processor will need to define it's own ``test`` and ``run``
    methods. The ``test`` method should return True or False, to indicate
    whether the current block should be processed by this processor. If the
    test passes, the parser will call the processors ``run`` method.

    """

    def __init__(self, parser):
        self.parser = parser
        self.tab_length = parser.markdown.tab_length

    def lastChild(self, parent):
        """ Return the last child of an etree element. """
        if len(parent):
            return parent[-1]
        else:
            return None

    def detab(self, text):
        """ Remove a tab from the front of each line of the given text. """
        newtext = []
        lines = text.split('\n')
        for line in lines:
            if line.startswith(' '*self.tab_length):
                newtext.append(line[self.tab_length:])
            elif not line.strip():
                newtext.append('')
            else:
                break
        return '\n'.join(newtext), '\n'.join(lines[len(newtext):])

    def looseDetab(self, text, level=1):
        """ Remove a tab from front of lines but allowing dedented lines. """
        lines = text.split('\n')
        for i in range(len(lines)):
            if lines[i].startswith(' '*self.tab_length*level):
                lines[i] = lines[i][self.tab_length*level:]
        return '\n'.join(lines)

    def test(self, parent, block):
        """ Test for block type. Must be overridden by subclasses. 
        
        As the parser loops through processors, it will call the ``test`` method
        on each to determine if the given block of text is of that type. This
        method must return a boolean ``True`` or ``False``. The actual method of
        testing is left to the needs of that particular block type. It could 
        be as simple as ``block.startswith(some_string)`` or a complex regular
        expression. As the block type may be different depending on the parent
        of the block (i.e. inside a list), the parent etree element is also 
        provided and may be used as part of the test.

        Keywords:
        
        * ``parent``: A etree element which will be the parent of the block.
        * ``block``: A block of text from the source which has been split at 
            blank lines.
        """
        pass

    def run(self, parent, blocks):
        """ Run processor. Must be overridden by subclasses. 
        
        When the parser determines the appropriate type of a block, the parser
        will call the corresponding processor's ``run`` method. This method
        should parse the individual lines of the block and append them to
        the etree. 

        Note that both the ``parent`` and ``etree`` keywords are pointers
        to instances of the objects which should be edited in place. Each
        processor must make changes to the existing objects as there is no
        mechanism to return new/different objects to replace them.

        This means that this method should be adding SubElements or adding text
        to the parent, and should remove (``pop``) or add (``insert``) items to
        the list of blocks.

        Keywords:

        * ``parent``: A etree element which is the parent of the current block.
        * ``blocks``: A list of all remaining blocks of the document.
        """
        pass


class ListIndentProcessor(BlockProcessor):
    """ Process children of list items. 
    
    Example:
        * a list item
            process this part

            or this part

    """

    ITEM_TYPES = ['li']
    LIST_TYPES = ['ul', 'ol']

    def __init__(self, *args):
        BlockProcessor.__init__(self, *args)
        self.INDENT_RE = re.compile(r'^(([ ]{%s})+)'% self.tab_length)

    def test(self, parent, block):
        return block.startswith(' '*self.tab_length) and \
                not self.parser.state.isstate('detabbed') and  \
                (parent.tag in self.ITEM_TYPES or \
                    (len(parent) and parent[-1] and \
                        (parent[-1].tag in self.LIST_TYPES)
                    )
                )

    def run(self, parent, blocks):
        block = blocks.pop(0)
        level, sibling = self.get_level(parent, block)
        block = self.looseDetab(block, level)

        self.parser.state.set('detabbed')
        if parent.tag in self.ITEM_TYPES:
            # It's possible that this parent has a 'ul' or 'ol' child list
            # with a member.  If that is the case, then that should be the
            # parent.  This is intended to catch the edge case of an indented 
            # list whose first member was parsed previous to this point
            # see OListProcessor
            if len(parent) and parent[-1].tag in self.LIST_TYPES:
                self.parser.parseBlocks(parent[-1], [block])
            else:
                # The parent is already a li. Just parse the child block.
                self.parser.parseBlocks(parent, [block])
        elif sibling.tag in self.ITEM_TYPES:
            # The sibling is a li. Use it as parent.
            self.parser.parseBlocks(sibling, [block])
        elif len(sibling) and sibling[-1].tag in self.ITEM_TYPES:
            # The parent is a list (``ol`` or ``ul``) which has children.
            # Assume the last child li is the parent of this block.
            if sibling[-1].text:
                # If the parent li has text, that text needs to be moved to a p
                # The p must be 'inserted' at beginning of list in the event
                # that other children already exist i.e.; a nested sublist.
                p = util.etree.Element('p')
                p.text = sibling[-1].text
                sibling[-1].text = ''
                sibling[-1].insert(0, p)
            self.parser.parseChunk(sibling[-1], block)
        else:
            self.create_item(sibling, block)
        self.parser.state.reset()

    def create_item(self, parent, block):
        """ Create a new li and parse the block with it as the parent. """
        li = util.etree.SubElement(parent, 'li')
        self.parser.parseBlocks(li, [block])
 
    def get_level(self, parent, block):
        """ Get level of indent based on list level. """
        # Get indent level
        m = self.INDENT_RE.match(block)
        if m:
            indent_level = len(m.group(1))/self.tab_length
        else:
            indent_level = 0
        if self.parser.state.isstate('list'):
            # We're in a tightlist - so we already are at correct parent.
            level = 1
        else:
            # We're in a looselist - so we need to find parent.
            level = 0
        # Step through children of tree to find matching indent level.
        while indent_level > level:
            child = self.lastChild(parent)
            if child and (child.tag in self.LIST_TYPES or child.tag in self.ITEM_TYPES):
                if child.tag in self.LIST_TYPES:
                    level += 1
                parent = child
            else:
                # No more child levels. If we're short of indent_level,
                # we have a code block. So we stop here.
                break
        return level, parent


class CodeBlockProcessor(BlockProcessor):
    """ Process code blocks. """

    def test(self, parent, block):
        return block.startswith(' '*self.tab_length)
    
    def run(self, parent, blocks):
        sibling = self.lastChild(parent)
        block = blocks.pop(0)
        theRest = ''
        if sibling and sibling.tag == "pre" and len(sibling) \
                    and sibling[0].tag == "code":
            # The previous block was a code block. As blank lines do not start
            # new code blocks, append this block to the previous, adding back
            # linebreaks removed from the split into a list.
            code = sibling[0]
            block, theRest = self.detab(block)
            code.text = util.AtomicString('%s\n%s\n' % (code.text, block.rstrip()))
        else:
            # This is a new codeblock. Create the elements and insert text.
            pre = util.etree.SubElement(parent, 'pre')
            code = util.etree.SubElement(pre, 'code')
            block, theRest = self.detab(block)
            code.text = util.AtomicString('%s\n' % block.rstrip())
        if theRest:
            # This block contained unindented line(s) after the first indented 
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)


class BlockQuoteProcessor(BlockProcessor):

    RE = re.compile(r'(^|\n)[ ]{0,3}>[ ]?(.*)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # Lines before blockquote
            # Pass lines before blockquote in recursively for parsing forst.
            self.parser.parseBlocks(parent, [before])
            # Remove ``> `` from begining of each line.
            block = '\n'.join([self.clean(line) for line in 
                            block[m.start():].split('\n')])
        sibling = self.lastChild(parent)
        if sibling and sibling.tag == "blockquote":
            # Previous block was a blockquote so set that as this blocks parent
            quote = sibling
        else:
            # This is a new blockquote. Create a new parent element.
            quote = util.etree.SubElement(parent, 'blockquote')
        # Recursively parse block with blockquote as parent.
        # change parser state so blockquotes embedded in lists use p tags
        self.parser.state.set('blockquote')
        self.parser.parseChunk(quote, block)
        self.parser.state.reset()

    def clean(self, line):
        """ Remove ``>`` from beginning of a line. """
        m = self.RE.match(line)
        if line.strip() == ">":
            return ""
        elif m:
            return m.group(2)
        else:
            return line

class OListProcessor(BlockProcessor):
    """ Process ordered list blocks. """

    TAG = 'ol'
    # Detect an item (``1. item``). ``group(1)`` contains contents of item.
    RE = re.compile(r'^[ ]{0,3}\d+\.[ ]+(.*)')
    # Detect items on secondary lines. they can be of either list type.
    CHILD_RE = re.compile(r'^[ ]{0,3}((\d+\.)|[*+-])[ ]+(.*)')
    # Detect indented (nested) items of either type
    INDENT_RE = re.compile(r'^[ ]{4,7}((\d+\.)|[*+-])[ ]+.*')
    # The integer (python string) with which the lists starts (default=1)
    # Eg: If list is intialized as)
    #   3. Item
    # The ol tag will get starts="3" attribute
    STARTSWITH = '1'

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        # Check fr multiple items in one block.
        items = self.get_items(blocks.pop(0))
        sibling = self.lastChild(parent)

        if sibling and sibling.tag in ['ol', 'ul']:
            # Previous block was a list item, so set that as parent
            lst = sibling
            # make sure previous item is in a p- if the item has text, then it
            # it isn't in a p
            if lst[-1].text: 
                # since it's possible there are other children for this sibling,
                # we can't just SubElement the p, we need to insert it as the 
                # first item
                p = util.etree.Element('p')
                p.text = lst[-1].text
                lst[-1].text = ''
                lst[-1].insert(0, p)
            # if the last item has a tail, then the tail needs to be put in a p
            # likely only when a header is not followed by a blank line
            lch = self.lastChild(lst[-1])
            if lch is not None and lch.tail:
                p = util.etree.SubElement(lst[-1], 'p')
                p.text = lch.tail.lstrip()
                lch.tail = ''

            # parse first block differently as it gets wrapped in a p.
            li = util.etree.SubElement(lst, 'li')
            self.parser.state.set('looselist')
            firstitem = items.pop(0)
            self.parser.parseBlocks(li, [firstitem])
            self.parser.state.reset()
        elif parent.tag in ['ol', 'ul']:
            # this catches the edge case of a multi-item indented list whose 
            # first item is in a blank parent-list item:
            # * * subitem1
            #     * subitem2
            # see also ListIndentProcessor
            lst = parent
        else:
            # This is a new list so create parent with appropriate tag.
            lst = util.etree.SubElement(parent, self.TAG)
            # Check if a custom start integer is set
            if not self.parser.markdown.lazy_ol and self.STARTSWITH !='1':
                lst.attrib['start'] = self.STARTSWITH

        self.parser.state.set('list')
        # Loop through items in block, recursively parsing each with the
        # appropriate parent.
        for item in items:
            if item.startswith(' '*self.tab_length):
                # Item is indented. Parse with last item as parent
                self.parser.parseBlocks(lst[-1], [item])
            else:
                # New item. Create li and parse with it as parent
                li = util.etree.SubElement(lst, 'li')
                self.parser.parseBlocks(li, [item])
        self.parser.state.reset()

    def get_items(self, block):
        """ Break a block into list items. """
        items = []
        for line in block.split('\n'):
            m = self.CHILD_RE.match(line)
            if m:
                # This is a new list item
                # Check first item for the start index
                if not items and self.TAG=='ol':
                    # Detect the integer value of first list item
                    INTEGER_RE = re.compile('(\d+)')
                    self.STARTSWITH = INTEGER_RE.match(m.group(1)).group()
                # Append to the list
                items.append(m.group(3))
            elif self.INDENT_RE.match(line):
                # This is an indented (possibly nested) item.
                if items[-1].startswith(' '*self.tab_length):
                    # Previous item was indented. Append to that item.
                    items[-1] = '%s\n%s' % (items[-1], line)
                else:
                    items.append(line)
            else:
                # This is another line of previous item. Append to that item.
                items[-1] = '%s\n%s' % (items[-1], line)
        return items


class UListProcessor(OListProcessor):
    """ Process unordered list blocks. """

    TAG = 'ul'
    RE = re.compile(r'^[ ]{0,3}[*+-][ ]+(.*)')


class HashHeaderProcessor(BlockProcessor):
    """ Process Hash Headers. """

    # Detect a header at start of any line in block
    RE = re.compile(r'(^|\n)(?P<level>#{1,6})(?P<header>.*?)#*(\n|$)')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        if m:
            before = block[:m.start()] # All lines before header
            after = block[m.end():]    # All lines after header
            if before:
                # As the header was not the first line of the block and the
                # lines before the header must be parsed first,
                # recursively parse this lines as a block.
                self.parser.parseBlocks(parent, [before])
            # Create header using named groups from RE
            h = util.etree.SubElement(parent, 'h%d' % len(m.group('level')))
            h.text = m.group('header').strip()
            if after:
                # Insert remaining lines as first block for future parsing.
                blocks.insert(0, after)
        else:
            # This should never happen, but just in case...
            logger.warn("We've got a problem header: %r" % block)


class SetextHeaderProcessor(BlockProcessor):
    """ Process Setext-style Headers. """

    # Detect Setext-style header. Must be first 2 lines of block.
    RE = re.compile(r'^.*?\n[=-]+[ ]*(\n|$)', re.MULTILINE)

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        lines = blocks.pop(0).split('\n')
        # Determine level. ``=`` is 1 and ``-`` is 2.
        if lines[1].startswith('='):
            level = 1
        else:
            level = 2
        h = util.etree.SubElement(parent, 'h%d' % level)
        h.text = lines[0].strip()
        if len(lines) > 2:
            # Block contains additional lines. Add to  master blocks for later.
            blocks.insert(0, '\n'.join(lines[2:]))


class HRProcessor(BlockProcessor):
    """ Process Horizontal Rules. """

    RE = r'^[ ]{0,3}((-+[ ]{0,2}){3,}|(_+[ ]{0,2}){3,}|(\*+[ ]{0,2}){3,})[ ]*'
    # Detect hr on any line of a block.
    SEARCH_RE = re.compile(RE, re.MULTILINE)

    def test(self, parent, block):
        m = self.SEARCH_RE.search(block)
        # No atomic grouping in python so we simulate it here for performance.
        # The regex only matches what would be in the atomic group - the HR.
        # Then check if we are at end of block or if next char is a newline.
        if m and (m.end() == len(block) or block[m.end()] == '\n'):
            # Save match object on class instance so we can use it later.
            self.match = m
            return True
        return False

    def run(self, parent, blocks):
        block = blocks.pop(0)
        # Check for lines in block before hr.
        prelines = block[:self.match.start()].rstrip('\n')
        if prelines:
            # Recursively parse lines before hr so they get parsed first.
            self.parser.parseBlocks(parent, [prelines])
        # create hr
        hr = util.etree.SubElement(parent, 'hr')
        # check for lines in block after hr.
        postlines = block[self.match.end():].lstrip('\n')
        if postlines:
            # Add lines after hr to master blocks for later parsing.
            blocks.insert(0, postlines)



class EmptyBlockProcessor(BlockProcessor):
    """ Process blocks and start with an empty line. """

    # Detect a block that only contains whitespace 
    # or only whitespace on the first line.
    RE = re.compile(r'^\s*\n')

    def test(self, parent, block):
        return bool(self.RE.match(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.match(block)
        if m:
            # Add remaining line to master blocks for later.
            blocks.insert(0, block[m.end():])
            sibling = self.lastChild(parent)
            if sibling and sibling.tag == 'pre' and sibling[0] and \
                    sibling[0].tag == 'code':
                # Last block is a codeblock. Append to preserve whitespace.
                sibling[0].text = util.AtomicString('%s/n/n/n' % sibling[0].text )


class ParagraphProcessor(BlockProcessor):
    """ Process Paragraph blocks. """

    def test(self, parent, block):
        return True

    def run(self, parent, blocks):
        block = blocks.pop(0)
        if block.strip():
            # Not a blank block. Add to parent, otherwise throw it away.
            if self.parser.state.isstate('list'):
                # The parent is a tight-list.
                #
                # Check for any children. This will likely only happen in a 
                # tight-list when a header isn't followed by a blank line.
                # For example:
                #
                #     * # Header
                #     Line 2 of list item - not part of header.
                sibling = self.lastChild(parent)
                if sibling is not None:
                    # Insetrt after sibling.
                    if sibling.tail:
                        sibling.tail = '%s\n%s' % (sibling.tail, block)
                    else:
                        sibling.tail = '\n%s' % block
                else:
                    # Append to parent.text
                    if parent.text:
                        parent.text = '%s\n%s' % (parent.text, block)
                    else:
                        parent.text = block.lstrip()
            else:
                # Create a regular paragraph
                p = util.etree.SubElement(parent, 'p')
                p.text = block.lstrip()

########NEW FILE########
__FILENAME__ = etree_loader

## Import
def importETree():
    """Import the best implementation of ElementTree, return a module object."""
    etree_in_c = None
    try: # Is it Python 2.5+ with C implemenation of ElementTree installed?
        import xml.etree.cElementTree as etree_in_c
        from xml.etree.ElementTree import Comment
    except ImportError:
        try: # Is it Python 2.5+ with Python implementation of ElementTree?
            import xml.etree.ElementTree as etree
        except ImportError:
            try: # An earlier version of Python with cElementTree installed?
                import cElementTree as etree_in_c
                from elementtree.ElementTree import Comment
            except ImportError:
                try: # An earlier version of Python with Python ElementTree?
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise ImportError("Failed to import ElementTree")
    if etree_in_c: 
        if etree_in_c.VERSION < "1.0.5":
            raise RuntimeError("cElementTree version 1.0.5 or higher is required.")
        # Third party serializers (including ours) test with non-c Comment
        etree_in_c.test_comment = Comment
        return etree_in_c
    elif etree.VERSION < "1.1":
        raise RuntimeError("ElementTree version 1.1 or higher is required")
    else:
        return etree


########NEW FILE########
__FILENAME__ = abbr
'''
Abbreviation Extension for Python-Markdown
==========================================

This extension adds abbreviation handling to Python-Markdown.

Simple Usage:

    >>> import markdown
    >>> text = """
    ... Some text with an ABBR and a REF. Ignore REFERENCE and ref.
    ...
    ... *[ABBR]: Abbreviation
    ... *[REF]: Abbreviation Reference
    ... """
    >>> print markdown.markdown(text, ['abbr'])
    <p>Some text with an <abbr title="Abbreviation">ABBR</abbr> and a <abbr title="Abbreviation Reference">REF</abbr>. Ignore REFERENCE and ref.</p>

Copyright 2007-2008
* [Waylan Limberg](http://achinghead.com/)
* [Seemant Kulleen](http://www.kulleen.org/)
	

'''

import re
import markdown
from markdown.util import etree

# Global Vars
ABBR_REF_RE = re.compile(r'[*]\[(?P<abbr>[^\]]*)\][ ]?:\s*(?P<title>.*)')

class AbbrExtension(markdown.Extension):
    """ Abbreviation Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Insert AbbrPreprocessor before ReferencePreprocessor. """
        md.preprocessors.add('abbr', AbbrPreprocessor(md), '<reference')
        
           
class AbbrPreprocessor(markdown.preprocessors.Preprocessor):
    """ Abbreviation Preprocessor - parse text for abbr references. """

    def run(self, lines):
        '''
        Find and remove all Abbreviation references from the text.
        Each reference is set as a new AbbrPattern in the markdown instance.
        
        '''
        new_text = []
        for line in lines:
            m = ABBR_REF_RE.match(line)
            if m:
                abbr = m.group('abbr').strip()
                title = m.group('title').strip()
                self.markdown.inlinePatterns['abbr-%s'%abbr] = \
                    AbbrPattern(self._generate_pattern(abbr), title)
            else:
                new_text.append(line)
        return new_text
    
    def _generate_pattern(self, text):
        '''
        Given a string, returns an regex pattern to match that string. 
        
        'HTML' -> r'(?P<abbr>[H][T][M][L])' 
        
        Note: we force each char as a literal match (in brackets) as we don't 
        know what they will be beforehand.

        '''
        chars = list(text)
        for i in range(len(chars)):
            chars[i] = r'[%s]' % chars[i]
        return r'(?P<abbr>\b%s\b)' % (r''.join(chars))


class AbbrPattern(markdown.inlinepatterns.Pattern):
    """ Abbreviation inline pattern. """

    def __init__(self, pattern, title):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.title = title

    def handleMatch(self, m):
        abbr = etree.Element('abbr')
        abbr.text = m.group('abbr')
        abbr.set('title', self.title)
        return abbr

def makeExtension(configs=None):
    return AbbrExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = attr_list
"""
Attribute List Extension for Python-Markdown
============================================

Adds attribute list syntax. Inspired by 
[maruku](http://maruku.rubyforge.org/proposal.html#attribute_lists)'s
feature of the same name.

Copyright 2011 [Waylan Limberg](http://achinghead.com/).

Contact: markdown@freewisdom.org

License: BSD (see ../../LICENSE for details) 

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown
import re
from markdown.util import isBlockLevel

try:
    Scanner = re.Scanner
except AttributeError:
    # must be on Python 2.4
    from sre import Scanner

def _handle_double_quote(s, t):
    k, v = t.split('=')
    return k, v.strip('"')

def _handle_single_quote(s, t):
    k, v = t.split('=')
    return k, v.strip("'")

def _handle_key_value(s, t): 
    return t.split('=')

def _handle_word(s, t):
    if t.startswith('.'):
        return u'.', t[1:]
    if t.startswith('#'):
        return u'id', t[1:]
    return t, t

_scanner = Scanner([
    (r'[^ ]+=".*?"', _handle_double_quote),
    (r"[^ ]+='.*?'", _handle_single_quote),
    (r'[^ ]+=[^ ]*', _handle_key_value),
    (r'[^ ]+', _handle_word),
    (r' ', None)
])

def get_attrs(str):
    """ Parse attribute list and return a list of attribute tuples. """
    return _scanner.scan(str)[0]

def isheader(elem):
    return elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']

class AttrListTreeprocessor(markdown.treeprocessors.Treeprocessor):
    
    BASE_RE = r'\{\:?([^\}]*)\}'
    HEADER_RE = re.compile(r'[ ]*%s[ ]*$' % BASE_RE)
    BLOCK_RE = re.compile(r'\n[ ]*%s[ ]*$' % BASE_RE)
    INLINE_RE = re.compile(r'^%s' % BASE_RE)

    def run(self, doc):
        for elem in doc.getiterator():
            #import pdb; pdb.set_trace()
            if isBlockLevel(elem.tag):
                # Block level: check for attrs on last line of text
                RE = self.BLOCK_RE
                if isheader(elem):
                    # header: check for attrs at end of line
                    RE = self.HEADER_RE
                if len(elem) and elem[-1].tail:
                    # has children. Get from tail of last child
                    m = RE.search(elem[-1].tail)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem[-1].tail = elem[-1].tail[:m.start()]
                        if isheader(elem):
                            # clean up trailing #s
                            elem[-1].tail = elem[-1].tail.rstrip('#').rstrip()
                elif elem.text:
                    # no children. Get from text.
                    m = RE.search(elem.text)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem.text = elem.text[:m.start()]
                        if isheader(elem):
                            # clean up trailing #s
                            elem.text = elem.text.rstrip('#').rstrip()
            else:
                # inline: check for attrs at start of tail
                if elem.tail:
                    m = self.INLINE_RE.match(elem.tail)
                    if m:
                        self.assign_attrs(elem, m.group(1))
                        elem.tail = elem.tail[m.end():]

    def assign_attrs(self, elem, attrs):
        """ Assign attrs to element. """
        for k, v in get_attrs(attrs):
            if k == '.':
                # add to class
                cls = elem.get('class')
                if cls:
                    elem.set('class', '%s %s' % (cls, v))
                else:
                    elem.set('class', v)
            else:
                # assing attr k with v
                elem.set(k, v)


class AttrListExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md, md_globals):
        # insert after 'inline' treeprocessor
        md.treeprocessors.add('attr_list', AttrListTreeprocessor(md), '>inline')


def makeExtension(configs={}):
    return AttrListExtension(configs=configs)

########NEW FILE########
__FILENAME__ = codehilite
#!/usr/bin/python

"""
CodeHilite Extension for Python-Markdown
========================================

Adds code/syntax highlighting to standard Python-Markdown code blocks.

Copyright 2006-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/CodeHilite>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.3+](http://python.org/)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [Pygments](http://pygments.org/)

"""

import markdown
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
    from pygments.formatters import HtmlFormatter
    pygments = True
except ImportError:
    pygments = False

# ------------------ The Main CodeHilite Class ----------------------
class CodeHilite:
    """
    Determine language of source code, and pass it into the pygments hilighter.

    Basic Usage:
        >>> code = CodeHilite(src = 'some text')
        >>> html = code.hilite()

    * src: Source string or any object with a .readline attribute.

    * linenos: (Boolen) Turn line numbering 'on' or 'off' (off by default).

    * guess_lang: (Boolen) Turn language auto-detection 'on' or 'off' (on by default).

    * css_class: Set class name of wrapper div ('codehilite' by default).

    Low Level Usage:
        >>> code = CodeHilite()
        >>> code.src = 'some text' # String or anything with a .readline attr.
        >>> code.linenos = True  # True or False; Turns line numbering on or of.
        >>> html = code.hilite()

    """

    def __init__(self, src=None, linenos=False, guess_lang=True,
                css_class="codehilite", lang=None, style='default',
                noclasses=False, tab_length=4):
        self.src = src
        self.lang = lang
        self.linenos = linenos
        self.guess_lang = guess_lang
        self.css_class = css_class
        self.style = style
        self.noclasses = noclasses
        self.tab_length = tab_length

    def hilite(self):
        """
        Pass code to the [Pygments](http://pygments.pocoo.org/) highliter with
        optional line numbers. The output should then be styled with css to
        your liking. No styles are applied by default - only styling hooks
        (i.e.: <span class="k">).

        returns : A string of html.

        """

        self.src = self.src.strip('\n')

        if self.lang is None:
            self._getLang()

        if pygments:
            try:
                lexer = get_lexer_by_name(self.lang)
            except ValueError:
                try:
                    if self.guess_lang:
                        lexer = guess_lexer(self.src)
                    else:
                        lexer = TextLexer()
                except ValueError:
                    lexer = TextLexer()
            formatter = HtmlFormatter(linenos=self.linenos,
                                      cssclass=self.css_class,
                                      style=self.style,
                                      noclasses=self.noclasses)
            return highlight(self.src, lexer, formatter)
        else:
            # just escape and build markup usable by JS highlighting libs
            txt = self.src.replace('&', '&amp;')
            txt = txt.replace('<', '&lt;')
            txt = txt.replace('>', '&gt;')
            txt = txt.replace('"', '&quot;')
            classes = []
            if self.lang:
                classes.append('language-%s' % self.lang)
            if self.linenos:
                classes.append('linenums')
            class_str = ''
            if classes:
                class_str = ' class="%s"' % ' '.join(classes) 
            return '<pre class="%s"><code%s>%s</code></pre>\n'% \
                        (self.css_class, class_str, txt)

    def _getLang(self):
        """
        Determines language of a code block from shebang line and whether said
        line should be removed or left in place. If the sheband line contains a
        path (even a single /) then it is assumed to be a real shebang line and
        left alone. However, if no path is given (e.i.: #!python or :::python)
        then it is assumed to be a mock shebang for language identifitation of a
        code fragment and removed from the code block prior to processing for
        code highlighting. When a mock shebang (e.i: #!python) is found, line
        numbering is turned on. When colons are found in place of a shebang
        (e.i.: :::python), line numbering is left in the current state - off
        by default.

        """

        import re

        #split text into lines
        lines = self.src.split("\n")
        #pull first line to examine
        fl = lines.pop(0)

        c = re.compile(r'''
            (?:(?:::+)|(?P<shebang>[#]!))	# Shebang or 2 or more colons.
            (?P<path>(?:/\w+)*[/ ])?        # Zero or 1 path
            (?P<lang>[\w+-]*)               # The language
            ''',  re.VERBOSE)
        # search first line for shebang
        m = c.search(fl)
        if m:
            # we have a match
            try:
                self.lang = m.group('lang').lower()
            except IndexError:
                self.lang = None
            if m.group('path'):
                # path exists - restore first line
                lines.insert(0, fl)
            if m.group('shebang'):
                # shebang exists - use line numbers
                self.linenos = True
        else:
            # No match
            lines.insert(0, fl)

        self.src = "\n".join(lines).strip("\n")



# ------------------ The Markdown Extension -------------------------------
class HiliteTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """ Hilight source code in code blocks. """

    def run(self, root):
        """ Find code blocks and store in htmlStash. """
        blocks = root.getiterator('pre')
        for block in blocks:
            children = block.getchildren()
            if len(children) == 1 and children[0].tag == 'code':
                code = CodeHilite(children[0].text,
                            linenos=self.config['force_linenos'],
                            guess_lang=self.config['guess_lang'],
                            css_class=self.config['css_class'],
                            style=self.config['pygments_style'],
                            noclasses=self.config['noclasses'],
                            tab_length=self.markdown.tab_length)
                placeholder = self.markdown.htmlStash.store(code.hilite(),
                                                            safe=True)
                # Clear codeblock in etree instance
                block.clear()
                # Change to p element which will later
                # be removed when inserting raw html
                block.tag = 'p'
                block.text = placeholder


class CodeHiliteExtension(markdown.Extension):
    """ Add source code hilighting to markdown codeblocks. """

    def __init__(self, configs):
        # define default configs
        self.config = {
            'force_linenos' : [False, "Force line numbers - Default: False"],
            'guess_lang' : [True, "Automatic language detection - Default: True"],
            'css_class' : ["codehilite",
                           "Set class name for wrapper <div> - Default: codehilite"],
            'pygments_style' : ['default', 'Pygments HTML Formatter Style (Colorscheme) - Default: default'],
            'noclasses': [False, 'Use inline styles instead of CSS classes - Default false']
            }

        # Override defaults with user settings
        for key, value in configs:
            # convert strings to booleans
            if value == 'True': value = True
            if value == 'False': value = False
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        """ Add HilitePostprocessor to Markdown instance. """
        hiliter = HiliteTreeprocessor(md)
        hiliter.config = self.getConfigs()
        md.treeprocessors.add("hilite", hiliter, "<inline")

        md.registerExtension(self)


def makeExtension(configs={}):
  return CodeHiliteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = def_list
#!/usr/bin/env python
"""
Definition List Extension for Python-Markdown
=============================================

Added parsing of Definition Lists to Python-Markdown.

A simple example:

    Apple
    :   Pomaceous fruit of plants of the genus Malus in 
        the family Rosaceae.
    :   An american computer company.

    Orange
    :   The fruit of an evergreen tree of the genus Citrus.

Copyright 2008 - [Waylan Limberg](http://achinghead.com)

"""

import re
import markdown
from markdown.util import etree


class DefListProcessor(markdown.blockprocessors.BlockProcessor):
    """ Process Definition Lists. """

    RE = re.compile(r'(^|\n)[ ]{0,3}:[ ]{1,3}(.*?)(\n|$)')
    NO_INDENT_RE = re.compile(r'^[ ]{0,3}[^ :]')

    def test(self, parent, block):
        return bool(self.RE.search(block))

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)
        terms = [l.strip() for l in block[:m.start()].split('\n') if l.strip()]
        block = block[m.end():]
        no_indent = self.NO_INDENT_RE.match(block)
        if no_indent:
            d, theRest = (block, None)
        else:
            d, theRest = self.detab(block)
        if d:
            d = '%s\n%s' % (m.group(2), d)
        else:
            d = m.group(2)
        sibling = self.lastChild(parent)
        if not terms and sibling.tag == 'p':
            # The previous paragraph contains the terms
            state = 'looselist'
            terms = sibling.text.split('\n')
            parent.remove(sibling)
            # Aquire new sibling
            sibling = self.lastChild(parent)
        else:
            state = 'list'

        if sibling and sibling.tag == 'dl':
            # This is another item on an existing list
            dl = sibling
            if len(dl) and dl[-1].tag == 'dd' and len(dl[-1]):
                state = 'looselist'
        else:
            # This is a new list
            dl = etree.SubElement(parent, 'dl')
        # Add terms
        for term in terms:
            dt = etree.SubElement(dl, 'dt')
            dt.text = term
        # Add definition
        self.parser.state.set(state)
        dd = etree.SubElement(dl, 'dd')
        self.parser.parseBlocks(dd, [d])
        self.parser.state.reset()

        if theRest:
            blocks.insert(0, theRest)

class DefListIndentProcessor(markdown.blockprocessors.ListIndentProcessor):
    """ Process indented children of definition list items. """

    ITEM_TYPES = ['dd']
    LIST_TYPES = ['dl']

    def create_item(self, parent, block):
        """ Create a new dd and parse the block with it as the parent. """
        dd = markdown.etree.SubElement(parent, 'dd')
        self.parser.parseBlocks(dd, [block])
 


class DefListExtension(markdown.Extension):
    """ Add definition lists to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of DefListProcessor to BlockParser. """
        md.parser.blockprocessors.add('defindent',
                                      DefListIndentProcessor(md.parser),
                                      '>indent')
        md.parser.blockprocessors.add('deflist', 
                                      DefListProcessor(md.parser),
                                      '>ulist')


def makeExtension(configs={}):
    return DefListExtension(configs=configs)


########NEW FILE########
__FILENAME__ = extra
#!/usr/bin/env python
"""
Python-Markdown Extra Extension
===============================

A compilation of various Python-Markdown extensions that imitates
[PHP Markdown Extra](http://michelf.com/projects/php-markdown/extra/).

Note that each of the individual extensions still need to be available
on your PYTHONPATH. This extension simply wraps them all up as a 
convenience so that only one extension needs to be listed when
initiating Markdown. See the documentation for each individual
extension for specifics about that extension.

In the event that one or more of the supported extensions are not 
available for import, Markdown will issue a warning and simply continue 
without that extension. 

There may be additional extensions that are distributed with 
Python-Markdown that are not included here in Extra. Those extensions
are not part of PHP Markdown Extra, and therefore, not part of
Python-Markdown Extra. If you really would like Extra to include
additional extensions, we suggest creating your own clone of Extra
under a differant name. You could also edit the `extensions` global 
variable defined below, but be aware that such changes may be lost 
when you upgrade to any future version of Python-Markdown.

"""

import markdown

extensions = ['smart_strong',
              'fenced_code',
              'footnotes',
              'attr_list',
              'def_list',
              'tables',
              'abbr',
              ]
              

class ExtraExtension(markdown.Extension):
    """ Add various extensions to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Register extension instances. """
        md.registerExtensions(extensions, self.config)
        # Turn on processing of markdown text within raw html
        md.preprocessors['html_block'].markdown_in_raw = True

def makeExtension(configs={}):
    return ExtraExtension(configs=dict(configs))

########NEW FILE########
__FILENAME__ = fenced_code
#!/usr/bin/env python

"""
Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

    >>> import markdown
    >>> text = '''
    ... A paragraph before a fenced code block:
    ...
    ... ~~~
    ... Fenced code block
    ... ~~~
    ... '''
    >>> html = markdown.markdown(text, extensions=['fenced_code'])
    >>> print html
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Works with safe_mode also (we check this because we are using the HtmlStash):

    >>> print markdown.markdown(text, extensions=['fenced_code'], safe_mode='replace')
    <p>A paragraph before a fenced code block:</p>
    <pre><code>Fenced code block
    </code></pre>

Include tilde's in a code block and wrap with blank lines:

    >>> text = '''
    ... ~~~~~~~~
    ...
    ... ~~~~
    ... ~~~~~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code>
    ~~~~
    </code></pre>

Language tags:

    >>> text = '''
    ... ~~~~{.python}
    ... # Some python code
    ... ~~~~'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code class="python"># Some python code
    </code></pre>

Optionally backticks instead of tildes as per how github's code block markdown is identified:

    >>> text = '''
    ... `````
    ... # Arbitrary code
    ... ~~~~~ # these tildes will not close the block
    ... `````'''
    >>> print markdown.markdown(text, extensions=['fenced_code'])
    <pre><code># Arbitrary code
    ~~~~~ # these tildes will not close the block
    </code></pre>

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/Fenced__Code__Blocks>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [Pygments (optional)](http://pygments.org)

"""

import re
import markdown
from markdown.extensions.codehilite import CodeHilite, CodeHiliteExtension

# Global vars
FENCED_BLOCK_RE = re.compile( \
    r'(?P<fence>^(?:~{3,}|`{3,}))[ ]*(\{?\.?(?P<lang>[a-zA-Z0-9_-]*)\}?)?[ ]*\n(?P<code>.*?)(?<=\n)(?P=fence)[ ]*$',
    re.MULTILINE|re.DOTALL
    )
CODE_WRAP = '<pre><code%s>%s</code></pre>'
LANG_TAG = ' class="%s"'

class FencedCodeExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)

        md.preprocessors.add('fenced_code_block',
                                 FencedBlockPreprocessor(md),
                                 "_begin")


class FencedBlockPreprocessor(markdown.preprocessors.Preprocessor):

    def __init__(self, md):
        markdown.preprocessors.Preprocessor.__init__(self, md)

        self.checked_for_codehilite = False
        self.codehilite_conf = {}

    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash. """

        # Check for code hilite extension
        if not self.checked_for_codehilite:
            for ext in self.markdown.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.config
                    break

            self.checked_for_codehilite = True

        text = "\n".join(lines)
        while 1:
            m = FENCED_BLOCK_RE.search(text)
            if m:
                lang = ''
                if m.group('lang'):
                    lang = LANG_TAG % m.group('lang')

                # If config is not empty, then the codehighlite extension
                # is enabled, so we call it to highlite the code
                if self.codehilite_conf:
                    highliter = CodeHilite(m.group('code'),
                            linenos=self.codehilite_conf['force_linenos'][0],
                            guess_lang=self.codehilite_conf['guess_lang'][0],
                            css_class=self.codehilite_conf['css_class'][0],
                            style=self.codehilite_conf['pygments_style'][0],
                            lang=(m.group('lang') or None),
                            noclasses=self.codehilite_conf['noclasses'][0])

                    code = highliter.hilite()
                else:
                    code = CODE_WRAP % (lang, self._escape(m.group('code')))

                placeholder = self.markdown.htmlStash.store(code, safe=True)
                text = '%s\n%s\n%s'% (text[:m.start()], placeholder, text[m.end():])
            else:
                break
        return text.split("\n")

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(configs=None):
    return FencedCodeExtension(configs=configs)


if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = footnotes
"""
========================= FOOTNOTES =================================

This section adds footnote handling to markdown.  It can be used as
an example for extending python-markdown with relatively complex
functionality.  While in this case the extension is included inside
the module itself, it could just as easily be added from outside the
module.  Not that all markdown classes above are ignorant about
footnotes.  All footnote functionality is provided separately and
then added to the markdown instance at the run time.

Footnote functionality is attached by calling extendMarkdown()
method of FootnoteExtension.  The method also registers the
extension to allow it's state to be reset by a call to reset()
method.

Example:
    Footnotes[^1] have a label[^label] and a definition[^!DEF].

    [^1]: This is a footnote
    [^label]: A footnote on "label"
    [^!DEF]: The footnote for definition

"""

import re
import markdown
from markdown.util import etree

FN_BACKLINK_TEXT = "zz1337820767766393qq"
NBSP_PLACEHOLDER =  "qq3936677670287331zz"
DEF_RE = re.compile(r'[ ]{0,3}\[\^([^\]]*)\]:\s*(.*)')
TABBED_RE = re.compile(r'((\t)|(    ))(.*)')

class FootnoteExtension(markdown.Extension):
    """ Footnote Extension. """

    def __init__ (self, configs):
        """ Setup configs. """
        self.config = {'PLACE_MARKER':
                       ["///Footnotes Go Here///",
                        "The text string that marks where the footnotes go"],
                       'UNIQUE_IDS':
                       [False,
                        "Avoid name collisions across "
                        "multiple calls to reset()."],
                       "BACKLINK_TEXT":
                       ["&#8617;",
                        "The text string that links from the footnote to the reader's place."]
                       }

        for key, value in configs:
            self.config[key][0] = value

        # In multiple invocations, emit links that don't get tangled.
        self.unique_prefix = 0

        self.reset()

    def extendMarkdown(self, md, md_globals):
        """ Add pieces to Markdown. """
        md.registerExtension(self)
        self.parser = md.parser
        # Insert a preprocessor before ReferencePreprocessor
        md.preprocessors.add("footnote", FootnotePreprocessor(self),
                             "<reference")
        # Insert an inline pattern before ImageReferencePattern
        FOOTNOTE_RE = r'\[\^([^\]]*)\]' # blah blah [^1] blah
        md.inlinePatterns.add("footnote", FootnotePattern(FOOTNOTE_RE, self),
                              "<reference")
        # Insert a tree-processor that would actually add the footnote div
        # This must be before all other treeprocessors (i.e., inline and 
        # codehilite) so they can run on the the contents of the div.
        md.treeprocessors.add("footnote", FootnoteTreeprocessor(self),
                                 "_begin")
        # Insert a postprocessor after amp_substitute oricessor
        md.postprocessors.add("footnote", FootnotePostprocessor(self),
                                  ">amp_substitute")

    def reset(self):
        """ Clear the footnotes on reset, and prepare for a distinct document. """
        self.footnotes = markdown.odict.OrderedDict()
        self.unique_prefix += 1

    def findFootnotesPlaceholder(self, root):
        """ Return ElementTree Element that contains Footnote placeholder. """
        def finder(element):
            for child in element:
                if child.text:
                    if child.text.find(self.getConfig("PLACE_MARKER")) > -1:
                        return child, element, True
                if child.tail:
                    if child.tail.find(self.getConfig("PLACE_MARKER")) > -1:
                        return child, element, False
                finder(child)
            return None
                
        res = finder(root)
        return res

    def setFootnote(self, id, text):
        """ Store a footnote for later retrieval. """
        self.footnotes[id] = text

    def makeFootnoteId(self, id):
        """ Return footnote link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fn:%d-%s' % (self.unique_prefix, id)
        else:
            return 'fn:%s' % id

    def makeFootnoteRefId(self, id):
        """ Return footnote back-link id. """
        if self.getConfig("UNIQUE_IDS"):
            return 'fnref:%d-%s' % (self.unique_prefix, id)
        else:
            return 'fnref:%s' % id

    def makeFootnotesDiv(self, root):
        """ Return div of footnotes as et Element. """

        if not self.footnotes.keys():
            return None

        div = etree.Element("div")
        div.set('class', 'footnote')
        hr = etree.SubElement(div, "hr")
        ol = etree.SubElement(div, "ol")

        for id in self.footnotes.keys():
            li = etree.SubElement(ol, "li")
            li.set("id", self.makeFootnoteId(id))
            self.parser.parseChunk(li, self.footnotes[id])
            backlink = etree.Element("a")
            backlink.set("href", "#" + self.makeFootnoteRefId(id))
            backlink.set("rev", "footnote")
            backlink.set("title", "Jump back to footnote %d in the text" % \
                            (self.footnotes.index(id)+1))
            backlink.text = FN_BACKLINK_TEXT

            if li.getchildren():
                node = li[-1]
                if node.tag == "p":
                    node.text = node.text + NBSP_PLACEHOLDER
                    node.append(backlink)
                else:
                    p = etree.SubElement(li, "p")
                    p.append(backlink)
        return div


class FootnotePreprocessor(markdown.preprocessors.Preprocessor):
    """ Find all footnote references and store for later use. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, lines):
        """
        Loop through lines and find, set, and remove footnote definitions.

        Keywords:

        * lines: A list of lines of text

        Return: A list of lines of text with footnote definitions removed.

        """
        newlines = []
        i = 0
        #import pdb; pdb.set_trace() #for i, line in enumerate(lines):
        while True:
            m = DEF_RE.match(lines[i])
            if m:
                fn, _i = self.detectTabbed(lines[i+1:])
                fn.insert(0, m.group(2))
                i += _i-1 # skip past footnote
                self.footnotes.setFootnote(m.group(1), "\n".join(fn))
            else:
                newlines.append(lines[i])
            if len(lines) > i+1:
                i += 1
            else:
                break
        return newlines

    def detectTabbed(self, lines):
        """ Find indented text and remove indent before further proccesing.

        Keyword arguments:

        * lines: an array of strings

        Returns: a list of post processed items and the index of last line.

        """
        items = []
        blank_line = False # have we encountered a blank line yet?
        i = 0 # to keep track of where we are

        def detab(line):
            match = TABBED_RE.match(line)
            if match:
               return match.group(4)

        for line in lines:
            if line.strip(): # Non-blank line
                detabbed_line = detab(line)
                if detabbed_line:
                    items.append(detabbed_line)
                    i += 1
                    continue
                elif not blank_line and not DEF_RE.match(line):
                    # not tabbed but still part of first par.
                    items.append(line)
                    i += 1
                    continue
                else:
                    return items, i+1

            else: # Blank line: _maybe_ we are done.
                blank_line = True
                i += 1 # advance

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next_line = lines[j]; break
                else:
                    break # There is no more text; we are done.

                # Check if the next non-blank line is tabbed
                if detab(next_line): # Yes, more work to do.
                    items.append("")
                    continue
                else:
                    break # No, we are done.
        else:
            i += 1

        return items, i


class FootnotePattern(markdown.inlinepatterns.Pattern):
    """ InlinePattern for footnote markers in a document's body text. """

    def __init__(self, pattern, footnotes):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.footnotes = footnotes

    def handleMatch(self, m):
        id = m.group(2)
        if id in self.footnotes.footnotes.keys():
            sup = etree.Element("sup")
            a = etree.SubElement(sup, "a")
            sup.set('id', self.footnotes.makeFootnoteRefId(id))
            a.set('href', '#' + self.footnotes.makeFootnoteId(id))
            a.set('rel', 'footnote')
            a.text = unicode(self.footnotes.footnotes.index(id) + 1)
            return sup
        else:
            return None


class FootnoteTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """ Build and append footnote div to end of document. """

    def __init__ (self, footnotes):
        self.footnotes = footnotes

    def run(self, root):
        footnotesDiv = self.footnotes.makeFootnotesDiv(root)
        if footnotesDiv:
            result = self.footnotes.findFootnotesPlaceholder(root)
            if result:
                child, parent, isText = result
                ind = parent.getchildren().index(child)
                if isText:
                    parent.remove(child)
                    parent.insert(ind, footnotesDiv)
                else:
                    parent.insert(ind + 1, footnotesDiv)
                    child.tail = None
            else:
                root.append(footnotesDiv)

class FootnotePostprocessor(markdown.postprocessors.Postprocessor):
    """ Replace placeholders with html entities. """
    def __init__(self, footnotes):
        self.footnotes = footnotes

    def run(self, text):
        text = text.replace(FN_BACKLINK_TEXT, self.footnotes.getConfig("BACKLINK_TEXT"))
        return text.replace(NBSP_PLACEHOLDER, "&#160;")

def makeExtension(configs=[]):
    """ Return an instance of the FootnoteExtension """
    return FootnoteExtension(configs=configs)


########NEW FILE########
__FILENAME__ = headerid
#!/usr/bin/python

"""
HeaderID Extension for Python-Markdown
======================================

Auto-generate id attributes for HTML headers.

Basic usage:

    >>> import markdown
    >>> text = "# Some Header #"
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="some-header">Some Header</h1>

All header IDs are unique:

    >>> text = '''
    ... #Header
    ... #Header
    ... #Header'''
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="header">Header</h1>
    <h1 id="header_1">Header</h1>
    <h1 id="header_2">Header</h1>

To fit within a html template's hierarchy, set the header base level:

    >>> text = '''
    ... #Some Header
    ... ## Next Level'''
    >>> md = markdown.markdown(text, ['headerid(level=3)'])
    >>> print md
    <h3 id="some-header">Some Header</h3>
    <h4 id="next-level">Next Level</h4>

Works with inline markup.

    >>> text = '#Some *Header* with [markup](http://example.com).'
    >>> md = markdown.markdown(text, ['headerid'])
    >>> print md
    <h1 id="some-header-with-markup">Some <em>Header</em> with <a href="http://example.com">markup</a>.</h1>

Turn off auto generated IDs:

    >>> text = '''
    ... # Some Header
    ... # Another Header'''
    >>> md = markdown.markdown(text, ['headerid(forceid=False)'])
    >>> print md
    <h1>Some Header</h1>
    <h1>Another Header</h1>

Use with MetaData extension:

    >>> text = '''header_level: 2
    ... header_forceid: Off
    ...
    ... # A Header'''
    >>> md = markdown.markdown(text, ['headerid', 'meta'])
    >>> print md
    <h2>A Header</h2>

Copyright 2007-2011 [Waylan Limberg](http://achinghead.com/).

Project website: <http://www.freewisdom.org/project/python-markdown/HeaderId>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown
from markdown.util import etree
import re
from string import ascii_lowercase, digits, punctuation
import logging
import unicodedata

logger = logging.getLogger('MARKDOWN')

IDCOUNT_RE = re.compile(r'^(.*)_([0-9]+)$')


def slugify(value, separator):
    """ Slugify a string, to make it URL friendly. """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = re.sub('[^\w\s-]', '', value.decode('ascii')).strip().lower()
    return re.sub('[%s\s]+' % separator, separator, value)


def unique(id, ids):
    """ Ensure id is unique in set of ids. Append '_1', '_2'... if not """
    while id in ids:
        m = IDCOUNT_RE.match(id)
        if m:
            id = '%s_%d'% (m.group(1), int(m.group(2))+1)
        else:
            id = '%s_%d'% (id, 1)
    ids.append(id)
    return id


def itertext(elem):
    """ Loop through all children and return text only. 
    
    Reimplements method of same name added to ElementTree in Python 2.7
    
    """
    if elem.text:
        yield elem.text
    for e in elem:
        for s in itertext(e):
            yield s
        if e.tail:
            yield e.tail


class HeaderIdTreeprocessor(markdown.treeprocessors.Treeprocessor):
    """ Assign IDs to headers. """

    IDs = set()

    def run(self, doc):
        start_level, force_id = self._get_meta()
        slugify = self.config['slugify']
        sep = self.config['separator']
        for elem in doc.getiterator():
            if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if force_id:
                    if "id" in elem.attrib:
                        id = elem.id
                    else:
                        id = slugify(''.join(itertext(elem)), sep)
                    elem.set('id', unique(id, self.IDs))
                if start_level:
                    level = int(elem.tag[-1]) + start_level
                    if level > 6:
                        level = 6
                    elem.tag = 'h%d' % level


    def _get_meta(self):
        """ Return meta data suported by this ext as a tuple """
        level = int(self.config['level']) - 1
        force = self._str2bool(self.config['forceid'])
        if hasattr(self.md, 'Meta'):
            if self.md.Meta.has_key('header_level'):
                level = int(self.md.Meta['header_level'][0]) - 1
            if self.md.Meta.has_key('header_forceid'): 
                force = self._str2bool(self.md.Meta['header_forceid'][0])
        return level, force

    def _str2bool(self, s, default=False):
        """ Convert a string to a booleen value. """
        s = str(s)
        if s.lower() in ['0', 'f', 'false', 'off', 'no', 'n']:
            return False
        elif s.lower() in ['1', 't', 'true', 'on', 'yes', 'y']:
            return True
        return default


class HeaderIdExtension (markdown.Extension):
    def __init__(self, configs):
        # set defaults
        self.config = {
                'level' : ['1', 'Base level for headers.'],
                'forceid' : ['True', 'Force all headers to have an id.'],
                'separator' : ['-', 'Word separator.'],
                'slugify' : [slugify, 'Callable to generate anchors'], 
            }

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        md.registerExtension(self)
        self.processor = HeaderIdTreeprocessor()
        self.processor.md = md
        self.processor.config = self.getConfigs()
        # Replace existing hasheader in place.
        md.treeprocessors.add('headerid', self.processor, '>inline')

    def reset(self):
        self.processor.IDs = []


def makeExtension(configs=None):
    return HeaderIdExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = html_tidy
#!/usr/bin/env python

"""
HTML Tidy Extension for Python-Markdown
=======================================

Runs [HTML Tidy][] on the output of Python-Markdown using the [uTidylib][] 
Python wrapper. Both libtidy and uTidylib must be installed on your system.

Note than any Tidy [options][] can be passed in as extension configs. So, 
for example, to output HTML rather than XHTML, set ``output_xhtml=0``. To
indent the output, set ``indent=auto`` and to have Tidy wrap the output in 
``<html>`` and ``<body>`` tags, set ``show_body_only=0``.

[HTML Tidy]: http://tidy.sourceforge.net/
[uTidylib]: http://utidylib.berlios.de/
[options]: http://tidy.sourceforge.net/docs/quickref.html

Copyright (c)2008 [Waylan Limberg](http://achinghead.com)

License: [BSD](http://www.opensource.org/licenses/bsd-license.php) 

Dependencies:
* [Python2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
* [HTML Tidy](http://utidylib.berlios.de/)
* [uTidylib](http://utidylib.berlios.de/)

"""

import markdown
try:
    import tidy
except ImportError:
    tidy = None

class TidyExtension(markdown.Extension):

    def __init__(self, configs):
        # Set defaults to match typical markdown behavior.
        self.config = dict(output_xhtml=1,
                           show_body_only=1,
                           char_encoding='utf8'
                          )
        # Merge in user defined configs overriding any present if nessecary.
        for c in configs:
            self.config[c[0]] = c[1]

    def extendMarkdown(self, md, md_globals):
        # Save options to markdown instance
        md.tidy_options = self.config
        # Add TidyProcessor to postprocessors
        if tidy:
            md.postprocessors['tidy'] = TidyProcessor(md)


class TidyProcessor(markdown.postprocessors.Postprocessor):

    def run(self, text):
        # Pass text to Tidy. As Tidy does not accept unicode we need to encode
        # it and decode its return value.
        enc = self.markdown.tidy_options.get('char_encoding', 'utf8')
        return unicode(tidy.parseString(text.encode(enc), 
                                        **self.markdown.tidy_options),
                       encoding=enc) 


def makeExtension(configs=None):
    return TidyExtension(configs=configs)

########NEW FILE########
__FILENAME__ = meta
#!usr/bin/python

"""
Meta Data Extension for Python-Markdown
=======================================

This extension adds Meta Data handling to markdown.

Basic Usage:

    >>> import markdown
    >>> text = '''Title: A Test Doc.
    ... Author: Waylan Limberg
    ...         John Doe
    ... Blank_Data:
    ...
    ... The body. This is paragraph one.
    ... '''
    >>> md = markdown.Markdown(['meta'])
    >>> print md.convert(text)
    <p>The body. This is paragraph one.</p>
    >>> print md.Meta
    {u'blank_data': [u''], u'author': [u'Waylan Limberg', u'John Doe'], u'title': [u'A Test Doc.']}

Make sure text without Meta Data still works (markdown < 1.6b returns a <p>).

    >>> text = '    Some Code - not extra lines of meta data.'
    >>> md = markdown.Markdown(['meta'])
    >>> print md.convert(text)
    <pre><code>Some Code - not extra lines of meta data.
    </code></pre>
    >>> md.Meta
    {}

Copyright 2007-2008 [Waylan Limberg](http://achinghead.com).

Project website: <http://www.freewisdom.org/project/python-markdown/Meta-Data>
Contact: markdown@freewisdom.org

License: BSD (see ../docs/LICENSE for details)

"""
import re

import markdown

# Global Vars
META_RE = re.compile(r'^[ ]{0,3}(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)')
META_MORE_RE = re.compile(r'^[ ]{4,}(?P<value>.*)')

class MetaExtension (markdown.Extension):
    """ Meta-Data extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add MetaPreprocessor to Markdown instance. """

        md.preprocessors.add("meta", MetaPreprocessor(md), "_begin")


class MetaPreprocessor(markdown.preprocessors.Preprocessor):
    """ Get Meta-Data. """

    def run(self, lines):
        """ Parse Meta-Data and store in Markdown.Meta. """
        meta = {}
        key = None
        while 1:
            line = lines.pop(0)
            if line.strip() == '':
                break # blank line - done
            m1 = META_RE.match(line)
            if m1:
                key = m1.group('key').lower().strip()
                value = m1.group('value').strip()
                try:
                    meta[key].append(value)
                except KeyError:
                    meta[key] = [value]
            else:
                m2 = META_MORE_RE.match(line)
                if m2 and key:
                    # Add another line to existing key
                    meta[key].append(m2.group('value').strip())
                else:
                    lines.insert(0, line)
                    break # no meta data - done
        self.markdown.Meta = meta
        return lines
        

def makeExtension(configs={}):
    return MetaExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = nl2br
"""
NL2BR Extension
===============

A Python-Markdown extension to treat newlines as hard breaks; like
StackOverflow and GitHub flavored Markdown do.

Usage:

    >>> import markdown
    >>> print markdown.markdown('line 1\\nline 2', extensions=['nl2br'])
    <p>line 1<br />
    line 2</p>

Copyright 2011 [Brian Neal](http://deathofagremmie.com/)

Dependencies:
* [Python 2.4+](http://python.org)
* [Markdown 2.1+](http://www.freewisdom.org/projects/python-markdown/)

"""

import markdown

BR_RE = r'\n'

class Nl2BrExtension(markdown.Extension):

    def extendMarkdown(self, md, md_globals):
        br_tag = markdown.inlinepatterns.SubstituteTagPattern(BR_RE, 'br')
        md.inlinePatterns.add('nl', br_tag, '_end')


def makeExtension(configs=None):
    return Nl2BrExtension(configs)


########NEW FILE########
__FILENAME__ = rss
import markdown
from markdown.util import etree

DEFAULT_URL = "http://www.freewisdom.org/projects/python-markdown/"
DEFAULT_CREATOR = "Yuri Takhteyev"
DEFAULT_TITLE = "Markdown in Python"
GENERATOR = "http://www.freewisdom.org/projects/python-markdown/markdown2rss"

month_map = { "Jan" : "01",
              "Feb" : "02",
              "March" : "03",
              "April" : "04",
              "May" : "05",
              "June" : "06",
              "July" : "07",
              "August" : "08",
              "September" : "09",
              "October" : "10",
              "November" : "11",
              "December" : "12" }

def get_time(heading):

    heading = heading.split("-")[0]
    heading = heading.strip().replace(",", " ").replace(".", " ")

    month, date, year = heading.split()
    month = month_map[month]

    return rdftime(" ".join((month, date, year, "12:00:00 AM")))

def rdftime(time):

    time = time.replace(":", " ")
    time = time.replace("/", " ")
    time = time.split()
    return "%s-%s-%sT%s:%s:%s-08:00" % (time[0], time[1], time[2],
                                        time[3], time[4], time[5])


def get_date(text):
    return "date"

class RssExtension (markdown.Extension):

    def extendMarkdown(self, md, md_globals):

        self.config = { 'URL' : [DEFAULT_URL, "Main URL"],
                        'CREATOR' : [DEFAULT_CREATOR, "Feed creator's name"],
                        'TITLE' : [DEFAULT_TITLE, "Feed title"] }

        md.xml_mode = True
        
        # Insert a tree-processor that would actually add the title tag
        treeprocessor = RssTreeProcessor(md)
        treeprocessor.ext = self
        md.treeprocessors['rss'] = treeprocessor
        md.stripTopLevelTags = 0
        md.docType = '<?xml version="1.0" encoding="utf-8"?>\n'

class RssTreeProcessor(markdown.treeprocessors.Treeprocessor):

    def run (self, root):

        rss = etree.Element("rss")
        rss.set("version", "2.0")

        channel = etree.SubElement(rss, "channel")

        for tag, text in (("title", self.ext.getConfig("TITLE")),
                          ("link", self.ext.getConfig("URL")),
                          ("description", None)):
            
            element = etree.SubElement(channel, tag)
            element.text = text

        for child in root:

            if child.tag in ["h1", "h2", "h3", "h4", "h5"]:
      
                heading = child.text.strip()
                item = etree.SubElement(channel, "item")
                link = etree.SubElement(item, "link")
                link.text = self.ext.getConfig("URL")
                title = etree.SubElement(item, "title")
                title.text = heading

                guid = ''.join([x for x in heading if x.isalnum()])
                guidElem = etree.SubElement(item, "guid")
                guidElem.text = guid
                guidElem.set("isPermaLink", "false")

            elif child.tag in ["p"]:
                try:
                    description = etree.SubElement(item, "description")
                except UnboundLocalError:
                    # Item not defined - moving on
                    pass
                else:
                    if len(child):
                        content = "\n".join([etree.tostring(node)
                                             for node in child])
                    else:
                        content = child.text
                    pholder = self.markdown.htmlStash.store(
                                                "<![CDATA[ %s]]>" % content)
                    description.text = pholder
    
        return rss


def makeExtension(configs):

    return RssExtension(configs)

########NEW FILE########
__FILENAME__ = smart_strong
'''
Smart_Strong Extension for Python-Markdown
==========================================

This extention adds smarter handling of double underscores within words.

Simple Usage:

    >>> import markdown
    >>> print markdown.markdown('Text with double__underscore__words.',
    ...                   extensions=['smart_strong'])
    <p>Text with double__underscore__words.</p>
    >>> print markdown.markdown('__Strong__ still works.',
    ...                   extensions=['smart_strong'])
    <p><strong>Strong</strong> still works.</p>
    >>> print markdown.markdown('__this__works__too__.',
    ...                   extensions=['smart_strong'])
    <p><strong>this__works__too</strong>.</p>

Copyright 2011
[Waylan Limberg](http://achinghead.com)

'''

import re
import markdown
from markdown.inlinepatterns import SimpleTagPattern

SMART_STRONG_RE = r'(?<!\w)(_{2})(?!_)(.+?)(?<!_)\2(?!\w)'
STRONG_RE = r'(\*{2})(.+?)\2'

class SmartEmphasisExtension(markdown.extensions.Extension):
    """ Add smart_emphasis extension to Markdown class."""

    def extendMarkdown(self, md, md_globals):
        """ Modify inline patterns. """
        md.inlinePatterns['strong'] = SimpleTagPattern(STRONG_RE, 'strong')
        md.inlinePatterns.add('strong2', SimpleTagPattern(SMART_STRONG_RE, 'strong'), '>emphasis2')

def makeExtension(configs={}):
    return SmartEmphasisExtension(configs=dict(configs))

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = tables
#!/usr/bin/env python
"""
Tables Extension for Python-Markdown
====================================

Added parsing of tables to Python-Markdown.

A simple example:

    First Header  | Second Header
    ------------- | -------------
    Content Cell  | Content Cell
    Content Cell  | Content Cell

Copyright 2009 - [Waylan Limberg](http://achinghead.com)
"""
import markdown
from markdown.util import etree


class TableProcessor(markdown.blockprocessors.BlockProcessor):
    """ Process Tables. """

    def test(self, parent, block):
        rows = block.split('\n')
        return (len(rows) > 2 and '|' in rows[0] and 
                '|' in rows[1] and '-' in rows[1] and 
                rows[1].strip()[0] in ['|', ':', '-'])

    def run(self, parent, blocks):
        """ Parse a table block and build table. """
        block = blocks.pop(0).split('\n')
        header = block[0].strip()
        seperator = block[1].strip()
        rows = block[2:]
        # Get format type (bordered by pipes or not)
        border = False
        if header.startswith('|'):
            border = True
        # Get alignment of columns
        align = []
        for c in self._split_row(seperator, border):
            if c.startswith(':') and c.endswith(':'):
                align.append('center')
            elif c.startswith(':'):
                align.append('left')
            elif c.endswith(':'):
                align.append('right')
            else:
                align.append(None)
        # Build table
        table = etree.SubElement(parent, 'table')
        thead = etree.SubElement(table, 'thead')
        self._build_row(header, thead, align, border)
        tbody = etree.SubElement(table, 'tbody')
        for row in rows:
            self._build_row(row.strip(), tbody, align, border)

    def _build_row(self, row, parent, align, border):
        """ Given a row of text, build table cells. """
        tr = etree.SubElement(parent, 'tr')
        tag = 'td'
        if parent.tag == 'thead':
            tag = 'th'
        cells = self._split_row(row, border)
        # We use align here rather than cells to ensure every row 
        # contains the same number of columns.
        for i, a in enumerate(align):
            c = etree.SubElement(tr, tag)
            try:
                c.text = cells[i].strip()
            except IndexError:
                c.text = ""
            if a:
                c.set('align', a)

    def _split_row(self, row, border):
        """ split a row of text into list of cells. """
        if border:
            if row.startswith('|'):
                row = row[1:]
            if row.endswith('|'):
                row = row[:-1]
        return row.split('|')


class TableExtension(markdown.Extension):
    """ Add tables to Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Add an instance of TableProcessor to BlockParser. """
        md.parser.blockprocessors.add('table', 
                                      TableProcessor(md.parser),
                                      '<hashheader')


def makeExtension(configs={}):
    return TableExtension(configs=configs)

########NEW FILE########
__FILENAME__ = toc
"""
Table of Contents Extension for Python-Markdown
* * *

(c) 2008 [Jack Miller](http://codezen.org)

Dependencies:
* [Markdown 2.1+](http://www.freewisdom.org/projects/python-markdown/)

"""
import markdown
from markdown.util import etree
from markdown.extensions.headerid import slugify, unique, itertext

import re


class TocTreeprocessor(markdown.treeprocessors.Treeprocessor):
    # Iterator wrapper to get parent and child all at once
    def iterparent(self, root):
        for parent in root.getiterator():
            for child in parent:
                yield parent, child

    def run(self, doc):
        marker_found = False

        div = etree.Element("div")
        div.attrib["class"] = "toc"
        last_li = None

        # Add title to the div
        if self.config["title"]:
            header = etree.SubElement(div, "span")
            header.attrib["class"] = "toctitle"
            header.text = self.config["title"]

        level = 0
        list_stack=[div]
        header_rgx = re.compile("[Hh][123456]")

        # Get a list of id attributes
        used_ids = []
        for c in doc.getiterator():
            if "id" in c.attrib:
                used_ids.append(c.attrib["id"])

        for (p, c) in self.iterparent(doc):
            text = ''.join(itertext(c)).strip()
            if not text:
                continue

            # To keep the output from screwing up the
            # validation by putting a <div> inside of a <p>
            # we actually replace the <p> in its entirety.
            # We do not allow the marker inside a header as that
            # would causes an enless loop of placing a new TOC 
            # inside previously generated TOC.

            if c.text and c.text.strip() == self.config["marker"] and \
               not header_rgx.match(c.tag) and c.tag not in ['pre', 'code']:
                for i in range(len(p)):
                    if p[i] == c:
                        p[i] = div
                        break
                marker_found = True
                    
            if header_rgx.match(c.tag):
                try:
                    tag_level = int(c.tag[-1])
                    
                    while tag_level < level:
                        list_stack.pop()
                        level -= 1

                    if tag_level > level:
                        newlist = etree.Element("ul")
                        if last_li:
                            last_li.append(newlist)
                        else:
                            list_stack[-1].append(newlist)
                        list_stack.append(newlist)
                        if level == 0:
                            level = tag_level
                        else:
                            level += 1

                    # Do not override pre-existing ids 
                    if not "id" in c.attrib:
                        id = unique(self.config["slugify"](text, '-'), used_ids)
                        c.attrib["id"] = id
                    else:
                        id = c.attrib["id"]

                    # List item link, to be inserted into the toc div
                    last_li = etree.Element("li")
                    link = etree.SubElement(last_li, "a")
                    link.text = text
                    link.attrib["href"] = '#' + id

                    if self.config["anchorlink"] in [1, '1', True, 'True', 'true']:
                        anchor = etree.Element("a")
                        anchor.text = c.text
                        anchor.attrib["href"] = "#" + id
                        anchor.attrib["class"] = "toclink"
                        c.text = ""
                        for elem in c.getchildren():
                            anchor.append(elem)
                            c.remove(elem)
                        c.append(anchor)

                    list_stack[-1].append(last_li)
                except IndexError:
                    # We have bad ordering of headers. Just move on.
                    pass
        if not marker_found:
            # searialize and attach to markdown instance.
            prettify = self.markdown.treeprocessors.get('prettify')
            if prettify: prettify.run(div)
            toc = self.markdown.serializer(div)
            for pp in self.markdown.postprocessors.values():
                toc = pp.run(toc)
            self.markdown.toc = toc

class TocExtension(markdown.Extension):
    def __init__(self, configs):
        self.config = { "marker" : ["[TOC]", 
                            "Text to find and replace with Table of Contents -"
                            "Defaults to \"[TOC]\""],
                        "slugify" : [slugify,
                            "Function to generate anchors based on header text-"
                            "Defaults to the headerid ext's slugify function."],
                        "title" : [None,
                            "Title to insert into TOC <div> - "
                            "Defaults to None"],
                        "anchorlink" : [0,
                            "1 if header should be a self link"
                            "Defaults to 0"]}

        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        tocext = TocTreeprocessor(md)
        tocext.config = self.getConfigs()
        # Headerid ext is set to '>inline'. With this set to '<prettify',
        # it should always come after headerid ext (and honor ids assinged 
        # by the header id extension) if both are used. Same goes for 
        # attr_list extension. This must come last because we don't want
        # to redefine ids after toc is created. But we do want toc prettified.
        md.treeprocessors.add("toc", tocext, "<prettify")
	
def makeExtension(configs={}):
    return TocExtension(configs=configs)

########NEW FILE########
__FILENAME__ = wikilinks
#!/usr/bin/env python

'''
WikiLinks Extension for Python-Markdown
======================================

Converts [[WikiLinks]] to relative links.  Requires Python-Markdown 2.0+

Basic usage:

    >>> import markdown
    >>> text = "Some text with a [[WikiLink]]."
    >>> html = markdown.markdown(text, ['wikilinks'])
    >>> print html
    <p>Some text with a <a class="wikilink" href="/WikiLink/">WikiLink</a>.</p>

Whitespace behavior:

    >>> print markdown.markdown('[[ foo bar_baz ]]', ['wikilinks'])
    <p><a class="wikilink" href="/foo_bar_baz/">foo bar_baz</a></p>
    >>> print markdown.markdown('foo [[ ]] bar', ['wikilinks'])
    <p>foo  bar</p>

To define custom settings the simple way:

    >>> print markdown.markdown(text, 
    ...     ['wikilinks(base_url=/wiki/,end_url=.html,html_class=foo)']
    ... )
    <p>Some text with a <a class="foo" href="/wiki/WikiLink.html">WikiLink</a>.</p>
    
Custom settings the complex way:

    >>> md = markdown.Markdown(
    ...     extensions = ['wikilinks'], 
    ...     extension_configs = {'wikilinks': [
    ...                                 ('base_url', 'http://example.com/'), 
    ...                                 ('end_url', '.html'),
    ...                                 ('html_class', '') ]},
    ...     safe_mode = True)
    >>> print md.convert(text)
    <p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>

Use MetaData with mdx_meta.py (Note the blank html_class in MetaData):

    >>> text = """wiki_base_url: http://example.com/
    ... wiki_end_url:   .html
    ... wiki_html_class:
    ...
    ... Some text with a [[WikiLink]]."""
    >>> md = markdown.Markdown(extensions=['meta', 'wikilinks'])
    >>> print md.convert(text)
    <p>Some text with a <a href="http://example.com/WikiLink.html">WikiLink</a>.</p>

MetaData should not carry over to next document:

    >>> print md.convert("No [[MetaData]] here.")
    <p>No <a class="wikilink" href="/MetaData/">MetaData</a> here.</p>

Define a custom URL builder:

    >>> def my_url_builder(label, base, end):
    ...     return '/bar/'
    >>> md = markdown.Markdown(extensions=['wikilinks'], 
    ...         extension_configs={'wikilinks' : [('build_url', my_url_builder)]})
    >>> print md.convert('[[foo]]')
    <p><a class="wikilink" href="/bar/">foo</a></p>

From the command line:

    python markdown.py -x wikilinks(base_url=http://example.com/,end_url=.html,html_class=foo) src.txt

By [Waylan Limberg](http://achinghead.com/).

License: [BSD](http://www.opensource.org/licenses/bsd-license.php) 

Dependencies:
* [Python 2.3+](http://python.org)
* [Markdown 2.0+](http://www.freewisdom.org/projects/python-markdown/)
'''

import markdown
import re

def build_url(label, base, end):
    """ Build a url from the label, a base, and an end. """
    clean_label = re.sub(r'([ ]+_)|(_[ ]+)|([ ]+)', '_', label)
    return '%s%s%s'% (base, clean_label, end)


class WikiLinkExtension(markdown.Extension):
    def __init__(self, configs):
        # set extension defaults
        self.config = {
                        'base_url' : ['/', 'String to append to beginning or URL.'],
                        'end_url' : ['/', 'String to append to end of URL.'],
                        'html_class' : ['wikilink', 'CSS hook. Leave blank for none.'],
                        'build_url' : [build_url, 'Callable formats URL from label.'],
        }
        
        # Override defaults with user settings
        for key, value in configs :
            self.setConfig(key, value)
        
    def extendMarkdown(self, md, md_globals):
        self.md = md
    
        # append to end of inline patterns
        WIKILINK_RE = r'\[\[([\w0-9_ -]+)\]\]'
        wikilinkPattern = WikiLinks(WIKILINK_RE, self.getConfigs())
        wikilinkPattern.md = md
        md.inlinePatterns.add('wikilink', wikilinkPattern, "<not_strong")


class WikiLinks(markdown.inlinepatterns.Pattern):
    def __init__(self, pattern, config):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.config = config
  
    def handleMatch(self, m):
        if m.group(2).strip():
            base_url, end_url, html_class = self._getMeta()
            label = m.group(2).strip()
            url = self.config['build_url'](label, base_url, end_url)
            a = markdown.util.etree.Element('a')
            a.text = label 
            a.set('href', url)
            if html_class:
                a.set('class', html_class)
        else:
            a = ''
        return a

    def _getMeta(self):
        """ Return meta data or config data. """
        base_url = self.config['base_url']
        end_url = self.config['end_url']
        html_class = self.config['html_class']
        if hasattr(self.md, 'Meta'):
            if self.md.Meta.has_key('wiki_base_url'):
                base_url = self.md.Meta['wiki_base_url'][0]
            if self.md.Meta.has_key('wiki_end_url'):
                end_url = self.md.Meta['wiki_end_url'][0]
            if self.md.Meta.has_key('wiki_html_class'):
                html_class = self.md.Meta['wiki_html_class'][0]
        return base_url, end_url, html_class
    

def makeExtension(configs=None) :
    return WikiLinkExtension(configs=configs)


if __name__ == "__main__":
    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = inlinepatterns
"""
INLINE PATTERNS
=============================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

    pattern.getCompiledRegExp() # returns a regular expression

    pattern.handleMatch(m) # takes a match object and returns
                           # an ElementTree element or just plain text

All of python markdown's built-in patterns subclass from Pattern,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

* escape and backticks have to go before everything else, so
  that we can preempt any markdown patterns by escaping them.

* then we handle auto-links (must be done before inline html)

* then we handle inline HTML.  At this point we will simply
  replace all inline HTML strings with a placeholder and add
  the actual HTML to a hash.

* then inline images (must be done before links)

* then bracketed links, first regular then reference-style

* finally we apply strong and emphasis
"""

import util
import odict
import re
from urlparse import urlparse, urlunparse
import sys
# If you see an ImportError for htmlentitydefs after using 2to3 to convert for 
# use by Python3, then you are probably using the buggy version from Python 3.0.
# We recomend using the tool from Python 3.1 even if you will be running the 
# code on Python 3.0.  The following line should be converted by the tool to:
# `from html import entities` and later calls to `htmlentitydefs` should be
# changed to call `entities`. Python 3.1's tool does this but 3.0's does not.
import htmlentitydefs


def build_inlinepatterns(md_instance, **kwargs):
    """ Build the default set of inline patterns for Markdown. """
    inlinePatterns = odict.OrderedDict()
    inlinePatterns["backtick"] = BacktickPattern(BACKTICK_RE)
    inlinePatterns["escape"] = EscapePattern(ESCAPE_RE, md_instance)
    inlinePatterns["reference"] = ReferencePattern(REFERENCE_RE, md_instance)
    inlinePatterns["link"] = LinkPattern(LINK_RE, md_instance)
    inlinePatterns["image_link"] = ImagePattern(IMAGE_LINK_RE, md_instance)
    inlinePatterns["image_reference"] = \
            ImageReferencePattern(IMAGE_REFERENCE_RE, md_instance)
    inlinePatterns["short_reference"] = \
            ReferencePattern(SHORT_REF_RE, md_instance)
    inlinePatterns["autolink"] = AutolinkPattern(AUTOLINK_RE, md_instance)
    inlinePatterns["automail"] = AutomailPattern(AUTOMAIL_RE, md_instance)
    inlinePatterns["linebreak2"] = SubstituteTagPattern(LINE_BREAK_2_RE, 'br')
    inlinePatterns["linebreak"] = SubstituteTagPattern(LINE_BREAK_RE, 'br')
    if md_instance.safeMode != 'escape':
        inlinePatterns["html"] = HtmlPattern(HTML_RE, md_instance)
    inlinePatterns["entity"] = HtmlPattern(ENTITY_RE, md_instance)
    inlinePatterns["not_strong"] = SimpleTextPattern(NOT_STRONG_RE)
    inlinePatterns["strong_em"] = DoubleTagPattern(STRONG_EM_RE, 'strong,em')
    inlinePatterns["strong"] = SimpleTagPattern(STRONG_RE, 'strong')
    inlinePatterns["emphasis"] = SimpleTagPattern(EMPHASIS_RE, 'em')
    if md_instance.smart_emphasis:
        inlinePatterns["emphasis2"] = SimpleTagPattern(SMART_EMPHASIS_RE, 'em')
    else:
        inlinePatterns["emphasis2"] = SimpleTagPattern(EMPHASIS_2_RE, 'em')
    return inlinePatterns

"""
The actual regular expressions for patterns
-----------------------------------------------------------------------------
"""

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[('
        + (NOBRACKET + r'(\[')*6
        + (NOBRACKET+ r'\])*')*6
        + NOBRACKET + r')\]' )
NOIMG = r'(?<!\!)'

BACKTICK_RE = r'(?<!\\)(`+)(.+?)(?<!`)\2(?!`)' # `e=f()` or ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'(\*)([^\*]+)\2'                    # *emphasis*
STRONG_RE = r'(\*{2}|_{2})(.+?)\2'                      # **strong**
STRONG_EM_RE = r'(\*{3}|_{3})(.+?)\2'            # ***strong***
SMART_EMPHASIS_RE = r'(?<!\w)(_)(?!_)(.+?)(?<!_)\2(?!\w)'  # _smart_emphasis_
EMPHASIS_2_RE = r'(_)(.+?)\2'                 # _emphasis_
LINK_RE = NOIMG + BRK + \
r'''\(\s*(<.*?>|((?:(?:\(.*?\))|[^\(\)]))*?)\s*((['"])(.*?)\12\s*)?\)'''
# [text](url) or [text](<url>) or [text](url "title")

IMAGE_LINK_RE = r'\!' + BRK + r'\s*\((<.*?>|([^\)]*))\)'
# ![alttxt](http://x.com/) or ![alttxt](<http://x.com/>)
REFERENCE_RE = NOIMG + BRK+ r'\s?\[([^\]]*)\]'           # [Google][3]
SHORT_REF_RE = NOIMG + r'\[([^\]]+)\]'                   # [Google]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s?\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'((^| )(\*|_)( |$))'                        # stand-alone * or _
AUTOLINK_RE = r'<((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^>]*)>' # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>

HTML_RE = r'(\<([a-zA-Z/][^\>]*?|\!--.*?--)\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'               # &amp;
LINE_BREAK_RE = r'  \n'                     # two spaces at end of line
LINE_BREAK_2_RE = r'  $'                    # two spaces at end of text


def dequote(string):
    """Remove quotes from around a string."""
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ):
        return string[1:-1]
    else:
        return string

ATTR_RE = re.compile("\{@([^\}]*)=([^\}]*)}") # {@id=123}

def handleAttributes(text, parent):
    """Set values of an element based on attribute definitions ({@id=123})."""
    def attributeCallback(match):
        parent.set(match.group(1), match.group(2).replace('\n', ' '))
    return ATTR_RE.sub(attributeCallback, text)


"""
The pattern classes
-----------------------------------------------------------------------------
"""

class Pattern:
    """Base class that inline patterns subclass. """

    def __init__(self, pattern, markdown_instance=None):
        """
        Create an instant of an inline pattern.

        Keyword arguments:

        * pattern: A regular expression that matches a pattern

        """
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*?)%s(.*?)$" % pattern, 
                                      re.DOTALL | re.UNICODE)

        # Api for Markdown to pass safe_mode into instance
        self.safe_mode = False
        if markdown_instance:
            self.markdown = markdown_instance

    def getCompiledRegExp(self):
        """ Return a compiled regular expression. """
        return self.compiled_re

    def handleMatch(self, m):
        """Return a ElementTree element from the given match.

        Subclasses should override this method.

        Keyword arguments:

        * m: A re match object containing a match of the pattern.

        """
        pass

    def type(self):
        """ Return class name, to define pattern type """
        return self.__class__.__name__

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.markdown.treeprocessors['inline'].stashed_nodes
        except KeyError:
            return text
        def get_stash(m):
            id = m.group(1)
            if id in stash:
                return stash.get(id)
        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class SimpleTextPattern(Pattern):
    """ Return a simple text of group(2) of a Pattern. """
    def handleMatch(self, m):
        text = m.group(2)
        if text == util.INLINE_PLACEHOLDER_PREFIX:
            return None
        return text


class EscapePattern(Pattern):
    """ Return an escaped character. """

    def handleMatch(self, m):
        char = m.group(2)
        if char in self.markdown.ESCAPED_CHARS:
            return '%s%s%s' % (util.STX, ord(char), util.ETX)
        else:
            return '\\%s' % char


class SimpleTagPattern(Pattern):
    """
    Return element of type `tag` with a text attribute of group(3)
    of a Pattern.

    """
    def __init__ (self, pattern, tag):
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m):
        el = util.etree.Element(self.tag)
        el.text = m.group(3)
        return el


class SubstituteTagPattern(SimpleTagPattern):
    """ Return a eLement of type `tag` with no children. """
    def handleMatch (self, m):
        return util.etree.Element(self.tag)


class BacktickPattern(Pattern):
    """ Return a `<code>` element containing the matching text. """
    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m):
        el = util.etree.Element(self.tag)
        el.text = util.AtomicString(m.group(3).strip())
        return el


class DoubleTagPattern(SimpleTagPattern):
    """Return a ElementTree element nested in tag2 nested in tag1.

    Useful for strong emphasis etc.

    """
    def handleMatch(self, m):
        tag1, tag2 = self.tag.split(",")
        el1 = util.etree.Element(tag1)
        el2 = util.etree.SubElement(el1, tag2)
        el2.text = m.group(3)
        return el1


class HtmlPattern(Pattern):
    """ Store raw inline html and return a placeholder. """
    def handleMatch (self, m):
        rawhtml = self.unescape(m.group(2))
        place_holder = self.markdown.htmlStash.store(rawhtml)
        return place_holder

    def unescape(self, text):
        """ Return unescaped text given text with an inline placeholder. """
        try:
            stash = self.markdown.treeprocessors['inline'].stashed_nodes
        except KeyError:
            return text
        def get_stash(m):
            id = m.group(1)
            value = stash.get(id)
            if value is not None:
                try:
                    return self.markdown.serializer(value)
                except:
                    return '\%s' % value
            
        return util.INLINE_PLACEHOLDER_RE.sub(get_stash, text)


class LinkPattern(Pattern):
    """ Return a link element from the given match. """
    def handleMatch(self, m):
        el = util.etree.Element("a")
        el.text = m.group(2)
        title = m.group(13)
        href = m.group(9)

        if href:
            if href[0] == "<":
                href = href[1:-1]
            el.set("href", self.sanitize_url(self.unescape(href.strip())))
        else:
            el.set("href", "")

        if title:
            title = dequote(self.unescape(title)) 
            el.set("title", title)
        return el

    def sanitize_url(self, url):
        """
        Sanitize a url against xss attacks in "safe_mode".

        Rather than specifically blacklisting `javascript:alert("XSS")` and all
        its aliases (see <http://ha.ckers.org/xss.html>), we whitelist known
        safe url formats. Most urls contain a network location, however some
        are known not to (i.e.: mailto links). Script urls do not contain a
        location. Additionally, for `javascript:...`, the scheme would be
        "javascript" but some aliases will appear to `urlparse()` to have no
        scheme. On top of that relative links (i.e.: "foo/bar.html") have no
        scheme. Therefore we must check "path", "parameters", "query" and
        "fragment" for any literal colons. We don't check "scheme" for colons
        because it *should* never have any and "netloc" must allow the form:
        `username:password@host:port`.

        """
        if not self.markdown.safeMode:
            # Return immediately bipassing parsing.
            return url
        
        try:
            scheme, netloc, path, params, query, fragment = url = urlparse(url)
        except ValueError:
            # Bad url - so bad it couldn't be parsed.
            return ''
        
        locless_schemes = ['', 'mailto', 'news']
        if netloc == '' and scheme not in locless_schemes:
            # This fails regardless of anything else. 
            # Return immediately to save additional proccessing
            return ''

        for part in url[2:]:
            if ":" in part:
                # Not a safe url
                return ''

        # Url passes all tests. Return url as-is.
        return urlunparse(url)

class ImagePattern(LinkPattern):
    """ Return a img element from the given match. """
    def handleMatch(self, m):
        el = util.etree.Element("img")
        src_parts = m.group(9).split()
        if src_parts:
            src = src_parts[0]
            if src[0] == "<" and src[-1] == ">":
                src = src[1:-1]
            el.set('src', self.sanitize_url(self.unescape(src)))
        else:
            el.set('src', "")
        if len(src_parts) > 1:
            el.set('title', dequote(self.unescape(" ".join(src_parts[1:]))))

        if self.markdown.enable_attributes:
            truealt = handleAttributes(m.group(2), el)
        else:
            truealt = m.group(2)

        el.set('alt', truealt)
        return el

class ReferencePattern(LinkPattern):
    """ Match to a stored reference and return link element. """

    NEWLINE_CLEANUP_RE = re.compile(r'[ ]?\n', re.MULTILINE)

    def handleMatch(self, m):
        try:
            id = m.group(9).lower()
        except IndexError:
            id = None
        if not id:
            # if we got something like "[Google][]" or "[Goggle]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        # Clean up linebreaks in id
        id = self.NEWLINE_CLEANUP_RE.sub(' ', id)
        if not id in self.markdown.references: # ignore undefined refs
            return None
        href, title = self.markdown.references[id]

        text = m.group(2)
        return self.makeTag(href, title, text)

    def makeTag(self, href, title, text):
        el = util.etree.Element('a')

        el.set('href', self.sanitize_url(href))
        if title:
            el.set('title', title)

        el.text = text
        return el


class ImageReferencePattern(ReferencePattern):
    """ Match to a stored reference and return img element. """
    def makeTag(self, href, title, text):
        el = util.etree.Element("img")
        el.set("src", self.sanitize_url(href))
        if title:
            el.set("title", title)
        el.set("alt", text)
        return el


class AutolinkPattern(Pattern):
    """ Return a link Element given an autolink (`<http://example/com>`). """
    def handleMatch(self, m):
        el = util.etree.Element("a")
        el.set('href', self.unescape(m.group(2)))
        el.text = util.AtomicString(m.group(2))
        return el

class AutomailPattern(Pattern):
    """
    Return a mailto link Element given an automail link (`<foo@example.com>`).
    """
    def handleMatch(self, m):
        el = util.etree.Element('a')
        email = self.unescape(m.group(2))
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]

        def codepoint2name(code):
            """Return entity definition by code, or the code if not defined."""
            entity = htmlentitydefs.codepoint2name.get(code)
            if entity:
                return "%s%s;" % (util.AMP_SUBSTITUTE, entity)
            else:
                return "%s#%d;" % (util.AMP_SUBSTITUTE, code)

        letters = [codepoint2name(ord(letter)) for letter in email]
        el.text = util.AtomicString(''.join(letters))

        mailto = "mailto:" + email
        mailto = "".join([util.AMP_SUBSTITUTE + '#%d;' %
                          ord(letter) for letter in mailto])
        el.set('href', mailto)
        return el


########NEW FILE########
__FILENAME__ = odict
class OrderedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.
    
    Copied from Django's SortedDict with some modifications.

    """
    def __new__(cls, *args, **kwargs):
        instance = super(OrderedDict, cls).__new__(cls, *args, **kwargs)
        instance.keyOrder = []
        return instance

    def __init__(self, data=None):
        if data is None:
            data = {}
        super(OrderedDict, self).__init__(data)
        if isinstance(data, dict):
            self.keyOrder = data.keys()
        else:
            self.keyOrder = []
            for key, value in data:
                if key not in self.keyOrder:
                    self.keyOrder.append(key)

    def __deepcopy__(self, memo):
        from copy import deepcopy
        return self.__class__([(key, deepcopy(value, memo))
                               for key, value in self.iteritems()])

    def __setitem__(self, key, value):
        super(OrderedDict, self).__setitem__(key, value)
        if key not in self.keyOrder:
            self.keyOrder.append(key)

    def __delitem__(self, key):
        super(OrderedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        for k in self.keyOrder:
            yield k

    def pop(self, k, *args):
        result = super(OrderedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(OrderedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def items(self):
        return zip(self.keyOrder, self.values())

    def iteritems(self):
        for key in self.keyOrder:
            yield key, super(OrderedDict, self).__getitem__(key)

    def keys(self):
        return self.keyOrder[:]

    def iterkeys(self):
        return iter(self.keyOrder)

    def values(self):
        return [super(OrderedDict, self).__getitem__(k) for k in self.keyOrder]

    def itervalues(self):
        for key in self.keyOrder:
            yield super(OrderedDict, self).__getitem__(key)

    def update(self, dict_):
        for k, v in dict_.items():
            self.__setitem__(k, v)

    def setdefault(self, key, default):
        if key not in self.keyOrder:
            self.keyOrder.append(key)
        return super(OrderedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Return the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Insert the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(OrderedDict, self).__setitem__(key, value)

    def copy(self):
        """Return a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        obj = self.__class__(self)
        obj.keyOrder = self.keyOrder[:]
        return obj

    def __repr__(self):
        """
        Replace the normal dict.__repr__ with a version that returns the keys
        in their sorted order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def clear(self):
        super(OrderedDict, self).clear()
        self.keyOrder = []

    def index(self, key):
        """ Return the index of a given key. """
        return self.keyOrder.index(key)

    def index_for_location(self, location):
        """ Return index or None for a given location. """
        if location == '_begin':
            i = 0
        elif location == '_end':
            i = None
        elif location.startswith('<') or location.startswith('>'):
            i = self.index(location[1:])
            if location.startswith('>'):
                if i >= len(self):
                    # last item
                    i = None
                else:
                    i += 1
        else:
            raise ValueError('Not a valid location: "%s". Location key '
                             'must start with a ">" or "<".' % location)
        return i

    def add(self, key, value, location):
        """ Insert by key location. """
        i = self.index_for_location(location)
        if i is not None:
            self.insert(i, key, value)
        else:
            self.__setitem__(key, value)

    def link(self, key, location):
        """ Change location of an existing item. """
        n = self.keyOrder.index(key)
        del self.keyOrder[n]
        i = self.index_for_location(location)
        try:
            if i is not None:
                self.keyOrder.insert(i, key)
            else:
                self.keyOrder.append(key)
        except Error:
            # restore to prevent data loss and reraise
            self.keyOrder.insert(n, key)
            raise Error

########NEW FILE########
__FILENAME__ = postprocessors
"""
POST-PROCESSORS
=============================================================================

Markdown also allows post-processors, which are similar to preprocessors in
that they need to implement a "run" method. However, they are run after core
processing.

"""

import re
import util
import odict

def build_postprocessors(md_instance, **kwargs):
    """ Build the default postprocessors for Markdown. """
    postprocessors = odict.OrderedDict()
    postprocessors["raw_html"] = RawHtmlPostprocessor(md_instance)
    postprocessors["amp_substitute"] = AndSubstitutePostprocessor()
    postprocessors["unescape"] = UnescapePostprocessor()
    return postprocessors


class Postprocessor(util.Processor):
    """
    Postprocessors are run after the ElementTree it converted back into text.

    Each Postprocessor implements a "run" method that takes a pointer to a
    text string, modifies it as necessary and returns a text string.

    Postprocessors must extend markdown.Postprocessor.

    """

    def run(self, text):
        """
        Subclasses of Postprocessor should implement a `run` method, which
        takes the html document as a single text string and returns a
        (possibly modified) string.

        """
        pass


class RawHtmlPostprocessor(Postprocessor):
    """ Restore raw html to the document. """

    def run(self, text):
        """ Iterate over html stash and restore "safe" html. """
        for i in range(self.markdown.htmlStash.html_counter):
            html, safe  = self.markdown.htmlStash.rawHtmlBlocks[i]
            if self.markdown.safeMode and not safe:
                if str(self.markdown.safeMode).lower() == 'escape':
                    html = self.escape(html)
                elif str(self.markdown.safeMode).lower() == 'remove':
                    html = ''
                else:
                    html = self.markdown.html_replacement_text
            if self.isblocklevel(html) and (safe or not self.markdown.safeMode):
                text = text.replace("<p>%s</p>" % 
                            (self.markdown.htmlStash.get_placeholder(i)),
                            html + "\n")
            text =  text.replace(self.markdown.htmlStash.get_placeholder(i), 
                                 html)
        return text

    def escape(self, html):
        """ Basic html escaping """
        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')
        return html.replace('"', '&quot;')

    def isblocklevel(self, html):
        m = re.match(r'^\<\/?([^ ]+)', html)
        if m:
            if m.group(1)[0] in ('!', '?', '@', '%'):
                # Comment, php etc...
                return True
            return util.isBlockLevel(m.group(1))
        return False


class AndSubstitutePostprocessor(Postprocessor):
    """ Restore valid entities """

    def run(self, text):
        text =  text.replace(util.AMP_SUBSTITUTE, "&")
        return text


class UnescapePostprocessor(Postprocessor):
    """ Restore escaped chars """

    RE = re.compile('%s(\d+)%s' % (util.STX, util.ETX))

    def unescape(self, m):
        return unichr(int(m.group(1)))

    def run(self, text):
        return self.RE.sub(self.unescape, text)

########NEW FILE########
__FILENAME__ = preprocessors
"""
PRE-PROCESSORS
=============================================================================

Preprocessors work on source text before we start doing anything too
complicated. 
"""

import re
import util
import odict


def build_preprocessors(md_instance, **kwargs):
    """ Build the default set of preprocessors used by Markdown. """
    preprocessors = odict.OrderedDict()
    if md_instance.safeMode != 'escape':
        preprocessors["html_block"] = HtmlBlockPreprocessor(md_instance)
    preprocessors["reference"] = ReferencePreprocessor(md_instance)
    return preprocessors


class Preprocessor(util.Processor):
    """
    Preprocessors are run after the text is broken into lines.

    Each preprocessor implements a "run" method that takes a pointer to a
    list of lines of the document, modifies it as necessary and returns
    either the same pointer or a pointer to a new list.

    Preprocessors must extend markdown.Preprocessor.

    """
    def run(self, lines):
        """
        Each subclass of Preprocessor should override the `run` method, which
        takes the document as a list of strings split by newlines and returns
        the (possibly modified) list of lines.

        """
        pass


class HtmlBlockPreprocessor(Preprocessor):
    """Remove html blocks from the text and store them for later retrieval."""

    right_tag_patterns = ["</%s>", "%s>"]
    attrs_pattern = r"""
        \s+(?P<attr>[^>"'/= ]+)=(?P<q>['"])(?P<value>.*?)(?P=q)   # attr="value"
        |                                                         # OR 
        \s+(?P<attr1>[^>"'/= ]+)=(?P<value1>[^> ]+)               # attr=value
        |                                                         # OR
        \s+(?P<attr2>[^>"'/= ]+)                                  # attr
        """
    left_tag_pattern = r'^\<(?P<tag>[^> ]+)(?P<attrs>(%s)*)\s*\/?\>?' % attrs_pattern
    attrs_re = re.compile(attrs_pattern, re.VERBOSE)
    left_tag_re = re.compile(left_tag_pattern, re.VERBOSE)
    markdown_in_raw = False

    def _get_left_tag(self, block):
        m = self.left_tag_re.match(block)
        if m:
            tag = m.group('tag')
            raw_attrs = m.group('attrs')
            attrs = {}
            if raw_attrs:
                for ma in self.attrs_re.finditer(raw_attrs):
                    if ma.group('attr'):
                        if ma.group('value'):
                            attrs[ma.group('attr').strip()] = ma.group('value')
                        else:
                            attrs[ma.group('attr').strip()] = ""
                    elif ma.group('attr1'):
                        if ma.group('value1'):
                            attrs[ma.group('attr1').strip()] = ma.group('value1')
                        else:
                            attrs[ma.group('attr1').strip()] = ""
                    elif ma.group('attr2'):
                        attrs[ma.group('attr2').strip()] = ""
            return tag, len(m.group(0)), attrs
        else:
            tag = block[1:].split(">", 1)[0].lower()
            return tag, len(tag)+2, {}

    def _recursive_tagfind(self, ltag, rtag, start_index, block):
        while 1:
            i = block.find(rtag, start_index)
            if i == -1:
                return -1
            j = block.find(ltag, start_index) 
            # if no ltag, or rtag found before another ltag, return index
            if (j > i or j == -1):
                return i + len(rtag)
            # another ltag found before rtag, use end of ltag as starting
            # point and search again
            j = block.find('>', j)
            start_index = self._recursive_tagfind(ltag, rtag, j + 1, block)
            if start_index == -1:
                # HTML potentially malformed- ltag has no corresponding 
                # rtag
                return -1

    def _get_right_tag(self, left_tag, left_index, block):
        for p in self.right_tag_patterns:
            tag = p % left_tag
            i = self._recursive_tagfind("<%s" % left_tag, tag, left_index, block)
            if i > 2:
                return tag.lstrip("<").rstrip(">"), i
        return block.rstrip()[-left_index:-1].lower(), len(block)
    
    def _equal_tags(self, left_tag, right_tag):
        if left_tag[0] in ['?', '@', '%']: # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--"):
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] != "<":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    def run(self, lines):
        text = "\n".join(lines)
        new_blocks = []
        text = text.split("\n\n")
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag

        while text:
            block = text[0]
            if block.startswith("\n"):
                block = block[1:]
            text = text[1:]

            if block.startswith("\n"):
                block = block[1:]

            if not in_tag:
                if block.startswith("<") and len(block.strip()) > 1:

                    if block[1] == "!":
                        # is a comment block
                        left_tag, left_index, attrs  = "--", 2, ()
                    else:
                        left_tag, left_index, attrs = self._get_left_tag(block)
                    right_tag, data_index = self._get_right_tag(left_tag, 
                                                                left_index,
                                                                block)
                    # keep checking conditions below and maybe just append
                    
                    if data_index < len(block) \
                        and (util.isBlockLevel(left_tag)
                        or left_tag == '--'): 
                        text.insert(0, block[data_index:])
                        block = block[:data_index]

                    if not (util.isBlockLevel(left_tag) \
                        or block[1] in ["!", "?", "@", "%"]):
                        new_blocks.append(block)
                        continue

                    if self._is_oneliner(left_tag):
                        new_blocks.append(block.strip())
                        continue

                    if block.rstrip().endswith(">") \
                        and self._equal_tags(left_tag, right_tag):
                        if self.markdown_in_raw and 'markdown' in attrs.keys():
                            start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                                           '', block[:left_index])
                            end = block[-len(right_tag)-2:]
                            block = block[left_index:-len(right_tag)-2]
                            new_blocks.append(
                                self.markdown.htmlStash.store(start))
                            new_blocks.append(block)
                            new_blocks.append(
                                self.markdown.htmlStash.store(end))
                        else:
                            new_blocks.append(
                                self.markdown.htmlStash.store(block.strip()))
                        continue
                    else: 
                        # if is block level tag and is not complete

                        if util.isBlockLevel(left_tag) or left_tag == "--" \
                            and not block.rstrip().endswith(">"):
                            items.append(block.strip())
                            in_tag = True
                        else:
                            new_blocks.append(
                            self.markdown.htmlStash.store(block.strip()))

                        continue

                new_blocks.append(block)

            else:
                items.append(block)

                right_tag, data_index = self._get_right_tag(left_tag, 0, block)

                if self._equal_tags(left_tag, right_tag):
                    # if find closing tag
                    
                    if data_index < len(block):
                        # we have more text after right_tag
                        items[-1] = block[:data_index]
                        text.insert(0, block[data_index:])

                    in_tag = False
                    if self.markdown_in_raw and 'markdown' in attrs.keys():
                        start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                                       '', items[0][:left_index])
                        items[0] = items[0][left_index:]
                        end = items[-1][-len(right_tag)-2:]
                        items[-1] = items[-1][:-len(right_tag)-2]
                        new_blocks.append(
                            self.markdown.htmlStash.store(start))
                        new_blocks.extend(items)
                        new_blocks.append(
                            self.markdown.htmlStash.store(end))
                    else:
                        new_blocks.append(
                            self.markdown.htmlStash.store('\n\n'.join(items)))
                    items = []

        if items:
            if self.markdown_in_raw and 'markdown' in attrs.keys():
                start = re.sub(r'\smarkdown(=[\'"]?[^> ]*[\'"]?)?', 
                               '', items[0][:left_index])
                items[0] = items[0][left_index:]
                end = items[-1][-len(right_tag)-2:]
                items[-1] = items[-1][:-len(right_tag)-2]
                new_blocks.append(
                    self.markdown.htmlStash.store(start))
                new_blocks.extend(items)
                if end.strip():
                    new_blocks.append(
                        self.markdown.htmlStash.store(end))
            else:
                new_blocks.append(
                    self.markdown.htmlStash.store('\n\n'.join(items)))
            #new_blocks.append(self.markdown.htmlStash.store('\n\n'.join(items)))
            new_blocks.append('\n')

        new_text = "\n\n".join(new_blocks)
        return new_text.split("\n")


class ReferencePreprocessor(Preprocessor):
    """ Remove reference definitions from text and store for later use. """

    RE = re.compile(r'^(\ ?\ ?\ ?)\[([^\]]*)\]:\s*([^ ]*)(.*)$', re.DOTALL)

    def run (self, lines):
        new_text = [];
        for line in lines:
            m = self.RE.match(line)
            if m:
                id = m.group(2).strip().lower()
                link = m.group(3).lstrip('<').rstrip('>')
                t = m.group(4).strip()  # potential title
                if not t:
                    self.markdown.references[id] = (link, t)
                elif (len(t) >= 2
                      and (t[0] == t[-1] == "\""
                           or t[0] == t[-1] == "\'"
                           or (t[0] == "(" and t[-1] == ")") ) ):
                    self.markdown.references[id] = (link, t[1:-1])
                else:
                    new_text.append(line)
            else:
                new_text.append(line)

        return new_text #+ "\n"

########NEW FILE########
__FILENAME__ = serializers
# markdown/searializers.py
#
# Add x/html serialization to Elementree
# Taken from ElementTree 1.3 preview with slight modifications
#
# Copyright (c) 1999-2007 by Fredrik Lundh.  All rights reserved.
#
# fredrik@pythonware.com
# http://www.pythonware.com
#
# --------------------------------------------------------------------
# The ElementTree toolkit is
#
# Copyright (c) 1999-2007 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------


import util
ElementTree = util.etree.ElementTree
QName = util.etree.QName
if hasattr(util.etree, 'test_comment'):
    Comment = util.etree.test_comment
else:
    Comment = util.etree.Comment
PI = util.etree.PI
ProcessingInstruction = util.etree.ProcessingInstruction

__all__ = ['to_html_string', 'to_xhtml_string']

HTML_EMPTY = ("area", "base", "basefont", "br", "col", "frame", "hr",
              "img", "input", "isindex", "link", "meta" "param")

try:
    HTML_EMPTY = set(HTML_EMPTY)
except NameError:
    pass

_namespace_map = {
    # "well-known" namespace prefixes
    "http://www.w3.org/XML/1998/namespace": "xml",
    "http://www.w3.org/1999/xhtml": "html",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
    "http://schemas.xmlsoap.org/wsdl/": "wsdl",
    # xml schema
    "http://www.w3.org/2001/XMLSchema": "xs",
    "http://www.w3.org/2001/XMLSchema-instance": "xsi",
    # dublic core
    "http://purl.org/dc/elements/1.1/": "dc",
}


def _raise_serialization_error(text):
    raise TypeError(
        "cannot serialize %r (type %s)" % (text, type(text).__name__)
        )

def _encode(text, encoding):
    try:
        return text.encode(encoding, "xmlcharrefreplace")
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_cdata(text):
    # escape character data
    try:
        # it's worth avoiding do-nothing calls for strings that are
        # shorter than 500 character, or so.  assume that's, by far,
        # the most common case in most applications.
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _escape_attrib(text):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        if "\n" in text:
            text = text.replace("\n", "&#10;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)

def _escape_attrib_html(text):
    # escape attribute value
    try:
        if "&" in text:
            text = text.replace("&", "&amp;")
        if "<" in text:
            text = text.replace("<", "&lt;")
        if ">" in text:
            text = text.replace(">", "&gt;")
        if "\"" in text:
            text = text.replace("\"", "&quot;")
        return text
    except (TypeError, AttributeError):
        _raise_serialization_error(text)


def _serialize_html(write, elem, qnames, namespaces, format):
    tag = elem.tag
    text = elem.text
    if tag is Comment:
        write("<!--%s-->" % _escape_cdata(text))
    elif tag is ProcessingInstruction:
        write("<?%s?>" % _escape_cdata(text))
    else:
        tag = qnames[tag]
        if tag is None:
            if text:
                write(_escape_cdata(text))
            for e in elem:
                _serialize_html(write, e, qnames, None, format)
        else:
            write("<" + tag)
            items = elem.items()
            if items or namespaces:
                items.sort() # lexical order
                for k, v in items:
                    if isinstance(k, QName):
                        k = k.text
                    if isinstance(v, QName):
                        v = qnames[v.text]
                    else:
                        v = _escape_attrib_html(v)
                    if qnames[k] == v and format == 'html':
                        # handle boolean attributes
                        write(" %s" % v)
                    else:
                        write(" %s=\"%s\"" % (qnames[k], v))
                if namespaces:
                    items = namespaces.items()
                    items.sort(key=lambda x: x[1]) # sort on prefix
                    for v, k in items:
                        if k:
                            k = ":" + k
                        write(" xmlns%s=\"%s\"" % (k, _escape_attrib(v)))
            if format == "xhtml" and tag in HTML_EMPTY:
                write(" />")
            else:
                write(">")
                tag = tag.lower()
                if text:
                    if tag == "script" or tag == "style":
                        write(text)
                    else:
                        write(_escape_cdata(text))
                for e in elem:
                    _serialize_html(write, e, qnames, None, format)
                if tag not in HTML_EMPTY:
                    write("</" + tag + ">")
    if elem.tail:
        write(_escape_cdata(elem.tail))

def _write_html(root,
                encoding=None,
                default_namespace=None,
                format="html"):
    assert root is not None
    data = []
    write = data.append
    qnames, namespaces = _namespaces(root, default_namespace)
    _serialize_html(write, root, qnames, namespaces, format)
    if encoding is None:
        return "".join(data)
    else:
        return _encode("".join(data))


# --------------------------------------------------------------------
# serialization support

def _namespaces(elem, default_namespace=None):
    # identify namespaces used in this tree

    # maps qnames to *encoded* prefix:local names
    qnames = {None: None}

    # maps uri:s to prefixes
    namespaces = {}
    if default_namespace:
        namespaces[default_namespace] = ""

    def add_qname(qname):
        # calculate serialized qname representation
        try:
            if qname[:1] == "{":
                uri, tag = qname[1:].split("}", 1)
                prefix = namespaces.get(uri)
                if prefix is None:
                    prefix = _namespace_map.get(uri)
                    if prefix is None:
                        prefix = "ns%d" % len(namespaces)
                    if prefix != "xml":
                        namespaces[uri] = prefix
                if prefix:
                    qnames[qname] = "%s:%s" % (prefix, tag)
                else:
                    qnames[qname] = tag # default element
            else:
                if default_namespace:
                    raise ValueError(
                        "cannot use non-qualified names with "
                        "default_namespace option"
                        )
                qnames[qname] = qname
        except TypeError:
            _raise_serialization_error(qname)

    # populate qname and namespaces table
    try:
        iterate = elem.iter
    except AttributeError:
        iterate = elem.getiterator # cET compatibility
    for elem in iterate():
        tag = elem.tag
        if isinstance(tag, QName) and tag.text not in qnames:
            add_qname(tag.text)
        elif isinstance(tag, basestring):
            if tag not in qnames:
                add_qname(tag)
        elif tag is not None and tag is not Comment and tag is not PI:
            _raise_serialization_error(tag)
        for key, value in elem.items():
            if isinstance(key, QName):
                key = key.text
            if key not in qnames:
                add_qname(key)
            if isinstance(value, QName) and value.text not in qnames:
                add_qname(value.text)
        text = elem.text
        if isinstance(text, QName) and text.text not in qnames:
            add_qname(text.text)
    return qnames, namespaces

def to_html_string(element):
    return _write_html(ElementTree(element).getroot(), format="html")

def to_xhtml_string(element):
    return _write_html(ElementTree(element).getroot(), format="xhtml")

########NEW FILE########
__FILENAME__ = treeprocessors
import re
import inlinepatterns
import util
import odict


def build_treeprocessors(md_instance, **kwargs):
    """ Build the default treeprocessors for Markdown. """
    treeprocessors = odict.OrderedDict()
    treeprocessors["inline"] = InlineProcessor(md_instance)
    treeprocessors["prettify"] = PrettifyTreeprocessor(md_instance)
    return treeprocessors


def isString(s):
    """ Check if it's string """
    if not isinstance(s, util.AtomicString):
        return isinstance(s, basestring)
    return False


class Processor:
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance


class Treeprocessor(Processor):
    """
    Treeprocessors are run on the ElementTree object before serialization.

    Each Treeprocessor implements a "run" method that takes a pointer to an
    ElementTree, modifies it as necessary and returns an ElementTree
    object.

    Treeprocessors must extend markdown.Treeprocessor.

    """
    def run(self, root):
        """
        Subclasses of Treeprocessor should implement a `run` method, which
        takes a root ElementTree. This method can return another ElementTree 
        object, and the existing root ElementTree will be replaced, or it can 
        modify the current tree and return None.
        """
        pass


class InlineProcessor(Treeprocessor):
    """
    A Treeprocessor that traverses a tree, applying inline patterns.
    """

    def __init__(self, md):
        self.__placeholder_prefix = util.INLINE_PLACEHOLDER_PREFIX
        self.__placeholder_suffix = util.ETX
        self.__placeholder_length = 4 + len(self.__placeholder_prefix) \
                                      + len(self.__placeholder_suffix)
        self.__placeholder_re = util.INLINE_PLACEHOLDER_RE
        self.markdown = md

    def __makePlaceholder(self, type):
        """ Generate a placeholder """
        id = "%04d" % len(self.stashed_nodes)
        hash = util.INLINE_PLACEHOLDER % id
        return hash, id

    def __findPlaceholder(self, data, index):
        """
        Extract id from data string, start from index

        Keyword arguments:

        * data: string
        * index: index, from which we start search

        Returns: placeholder id and string index, after the found placeholder.
        
        """
        m = self.__placeholder_re.search(data, index)
        if m:
            return m.group(1), m.end()
        else:
            return None, index + 1

    def __stashNode(self, node, type):
        """ Add node to stash """
        placeholder, id = self.__makePlaceholder(type)
        self.stashed_nodes[id] = node
        return placeholder

    def __handleInline(self, data, patternIndex=0):
        """
        Process string with inline patterns and replace it
        with placeholders

        Keyword arguments:

        * data: A line of Markdown text
        * patternIndex: The index of the inlinePattern to start with

        Returns: String with placeholders.

        """
        if not isinstance(data, util.AtomicString):
            startIndex = 0
            while patternIndex < len(self.markdown.inlinePatterns):
                data, matched, startIndex = self.__applyPattern(
                    self.markdown.inlinePatterns.value_for_index(patternIndex),
                    data, patternIndex, startIndex)
                if not matched:
                    patternIndex += 1
        return data

    def __processElementText(self, node, subnode, isText=True):
        """
        Process placeholders in Element.text or Element.tail
        of Elements popped from self.stashed_nodes.

        Keywords arguments:

        * node: parent node
        * subnode: processing node
        * isText: bool variable, True - it's text, False - it's tail

        Returns: None

        """
        if isText:
            text = subnode.text
            subnode.text = None
        else:
            text = subnode.tail
            subnode.tail = None

        childResult = self.__processPlaceholders(text, subnode)

        if not isText and node is not subnode:
            pos = node.getchildren().index(subnode)
            node.remove(subnode)
        else:
            pos = 0

        childResult.reverse()
        for newChild in childResult:
            node.insert(pos, newChild)

    def __processPlaceholders(self, data, parent):
        """
        Process string with placeholders and generate ElementTree tree.

        Keyword arguments:

        * data: string with placeholders instead of ElementTree elements.
        * parent: Element, which contains processing inline data

        Returns: list with ElementTree elements with applied inline patterns.
        
        """
        def linkText(text):
            if text:
                if result:
                    if result[-1].tail:
                        result[-1].tail += text
                    else:
                        result[-1].tail = text
                else:
                    if parent.text:
                        parent.text += text
                    else:
                        parent.text = text
        result = []
        strartIndex = 0
        while data:
            index = data.find(self.__placeholder_prefix, strartIndex)
            if index != -1:
                id, phEndIndex = self.__findPlaceholder(data, index)

                if id in self.stashed_nodes:
                    node = self.stashed_nodes.get(id)

                    if index > 0:
                        text = data[strartIndex:index]
                        linkText(text)

                    if not isString(node): # it's Element
                        for child in [node] + node.getchildren():
                            if child.tail:
                                if child.tail.strip():
                                    self.__processElementText(node, child,False)
                            if child.text:
                                if child.text.strip():
                                    self.__processElementText(child, child)
                    else: # it's just a string
                        linkText(node)
                        strartIndex = phEndIndex
                        continue

                    strartIndex = phEndIndex
                    result.append(node)

                else: # wrong placeholder
                    end = index + len(self.__placeholder_prefix)
                    linkText(data[strartIndex:end])
                    strartIndex = end
            else:
                text = data[strartIndex:]
                if isinstance(data, util.AtomicString):
                    # We don't want to loose the AtomicString
                    text = util.AtomicString(text)
                linkText(text)
                data = ""

        return result

    def __applyPattern(self, pattern, data, patternIndex, startIndex=0):
        """
        Check if the line fits the pattern, create the necessary
        elements, add it to stashed_nodes.

        Keyword arguments:

        * data: the text to be processed
        * pattern: the pattern to be checked
        * patternIndex: index of current pattern
        * startIndex: string index, from which we start searching

        Returns: String with placeholders instead of ElementTree elements.

        """
        match = pattern.getCompiledRegExp().match(data[startIndex:])
        leftData = data[:startIndex]

        if not match:
            return data, False, 0

        node = pattern.handleMatch(match)

        if node is None:
            return data, True, len(leftData)+match.span(len(match.groups()))[0]

        if not isString(node):
            if not isinstance(node.text, util.AtomicString):
                # We need to process current node too
                for child in [node] + node.getchildren():
                    if not isString(node):
                        if child.text: 
                            child.text = self.__handleInline(child.text,
                                                            patternIndex + 1)
                        if child.tail:
                            child.tail = self.__handleInline(child.tail,
                                                            patternIndex)

        placeholder = self.__stashNode(node, pattern.type())

        return "%s%s%s%s" % (leftData,
                             match.group(1),
                             placeholder, match.groups()[-1]), True, 0

    def run(self, tree):
        """Apply inline patterns to a parsed Markdown tree.

        Iterate over ElementTree, find elements with inline tag, apply inline
        patterns and append newly created Elements to tree.  If you don't
        want to process your data with inline paterns, instead of normal string,
        use subclass AtomicString:

            node.text = markdown.AtomicString("This will not be processed.")

        Arguments:

        * tree: ElementTree object, representing Markdown tree.

        Returns: ElementTree object with applied inline patterns.

        """
        self.stashed_nodes = {}

        stack = [tree]

        while stack:
            currElement = stack.pop()
            insertQueue = []
            for child in currElement.getchildren():
                if child.text and not isinstance(child.text, util.AtomicString):
                    text = child.text
                    child.text = None
                    lst = self.__processPlaceholders(self.__handleInline(
                                                    text), child)
                    stack += lst
                    insertQueue.append((child, lst))
                if child.tail:
                    tail = self.__handleInline(child.tail)
                    dumby = util.etree.Element('d')
                    tailResult = self.__processPlaceholders(tail, dumby)
                    if dumby.text:
                        child.tail = dumby.text
                    else:
                        child.tail = None
                    pos = currElement.getchildren().index(child) + 1
                    tailResult.reverse()
                    for newChild in tailResult:
                        currElement.insert(pos, newChild)
                if child.getchildren():
                    stack.append(child)

            if self.markdown.enable_attributes:
                for element, lst in insertQueue:
                    if element.text:
                        element.text = \
                            inlinepatterns.handleAttributes(element.text, 
                                                                    element)
                    i = 0
                    for newChild in lst:
                        # Processing attributes
                        if newChild.tail:
                            newChild.tail = \
                                inlinepatterns.handleAttributes(newChild.tail,
                                                                    element)
                        if newChild.text:
                            newChild.text = \
                                inlinepatterns.handleAttributes(newChild.text,
                                                                    newChild)
                        element.insert(i, newChild)
                        i += 1
        return tree


class PrettifyTreeprocessor(Treeprocessor):
    """ Add linebreaks to the html document. """

    def _prettifyETree(self, elem):
        """ Recursively add linebreaks to ElementTree children. """

        i = "\n"
        if util.isBlockLevel(elem.tag) and elem.tag not in ['code', 'pre']:
            if (not elem.text or not elem.text.strip()) \
                    and len(elem) and util.isBlockLevel(elem[0].tag):
                elem.text = i
            for e in elem:
                if util.isBlockLevel(e.tag):
                    self._prettifyETree(e)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i

    def run(self, root):
        """ Add linebreaks to ElementTree root object. """

        self._prettifyETree(root)
        # Do <br />'s seperately as they are often in the middle of
        # inline content and missed by _prettifyETree.
        brs = root.getiterator('br')
        for br in brs:
            if not br.tail or not br.tail.strip():
                br.tail = '\n'
            else:
                br.tail = '\n%s' % br.tail

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
import re
from logging import CRITICAL

import etree_loader


"""
CONSTANTS
=============================================================================
"""

"""
Constants you might want to modify
-----------------------------------------------------------------------------
"""

BLOCK_LEVEL_ELEMENTS = re.compile("p|div|h[1-6]|blockquote|pre|table|dl|ol|ul"
                                  "|script|noscript|form|fieldset|iframe|math"
                                  "|ins|del|hr|hr/|style|li|dt|dd|thead|tbody"
                                  "|tr|th|td|section|footer|header|group|figure"
                                  "|figcaption|aside|article|canvas|output"
                                  "|progress|video")
# Placeholders
STX = u'\u0002'  # Use STX ("Start of text") for start-of-placeholder
ETX = u'\u0003'  # Use ETX ("End of text") for end-of-placeholder
INLINE_PLACEHOLDER_PREFIX = STX+"klzzwxh:"
INLINE_PLACEHOLDER = INLINE_PLACEHOLDER_PREFIX + "%s" + ETX
INLINE_PLACEHOLDER_RE = re.compile(INLINE_PLACEHOLDER % r'([0-9]{4})')
AMP_SUBSTITUTE = STX+"amp"+ETX

"""
Constants you probably do not need to change
-----------------------------------------------------------------------------
"""

RTL_BIDI_RANGES = ( (u'\u0590', u'\u07FF'),
                     # Hebrew (0590-05FF), Arabic (0600-06FF),
                     # Syriac (0700-074F), Arabic supplement (0750-077F),
                     # Thaana (0780-07BF), Nko (07C0-07FF).
                    (u'\u2D30', u'\u2D7F'), # Tifinagh
                    )

# Extensions should use "markdown.util.etree" instead of "etree" (or do `from
# markdown.util import etree`).  Do not import it by yourself.

etree = etree_loader.importETree()

"""
AUXILIARY GLOBAL FUNCTIONS
=============================================================================
"""


def isBlockLevel(tag):
    """Check if the tag is a block level HTML tag."""
    if isinstance(tag, basestring):
        return BLOCK_LEVEL_ELEMENTS.match(tag)
    # Some ElementTree tags are not strings, so return False.
    return False

"""
MISC AUXILIARY CLASSES
=============================================================================
"""

class AtomicString(unicode):
    """A string which should not be further processed."""
    pass


class Processor:
    def __init__(self, markdown_instance=None):
        if markdown_instance:
            self.markdown = markdown_instance


class HtmlStash:
    """
    This class is used for stashing HTML objects that we extract
    in the beginning and replace with place-holders.
    """

    def __init__ (self):
        """ Create a HtmlStash. """
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

    def store(self, html, safe=False):
        """
        Saves an HTML segment for later reinsertion.  Returns a
        placeholder string that needs to be inserted into the
        document.

        Keyword arguments:

        * html: an html segment
        * safe: label an html segment as safe for safemode

        Returns : a placeholder string

        """
        self.rawHtmlBlocks.append((html, safe))
        placeholder = self.get_placeholder(self.html_counter)
        self.html_counter += 1
        return placeholder

    def reset(self):
        self.html_counter = 0
        self.rawHtmlBlocks = []

    def get_placeholder(self, key):
        return "%swzxhzdk:%d%s" % (STX, key, ETX)


########NEW FILE########
__FILENAME__ = __main__
"""
COMMAND-LINE SPECIFIC STUFF
=============================================================================

"""

import markdown
import sys
import optparse

import logging
from logging import DEBUG, INFO, CRITICAL

logger =  logging.getLogger('MARKDOWN')

def parse_options():
    """
    Define and parse `optparse` options for command-line usage.
    """
    usage = """%prog [options] [INPUTFILE]
       (STDIN is assumed if no INPUTFILE is given)"""
    desc = "A Python implementation of John Gruber's Markdown. " \
           "http://www.freewisdom.org/projects/python-markdown/"
    ver = "%%prog %s" % markdown.version
    
    parser = optparse.OptionParser(usage=usage, description=desc, version=ver)
    parser.add_option("-f", "--file", dest="filename", default=sys.stdout,
                      help="Write output to OUTPUT_FILE. Defaults to STDOUT.",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="Encoding for input and output files.",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=CRITICAL+10, dest="verbose",
                      help="Suppress all warnings.")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="Print all warnings.")
    parser.add_option("-s", "--safe", dest="safe", default=False,
                      metavar="SAFE_MODE",
                      help="'replace', 'remove' or 'escape' HTML tags in input")
    parser.add_option("-o", "--output_format", dest="output_format", 
                      default='xhtml1', metavar="OUTPUT_FORMAT",
                      help="'xhtml1' (default), 'html4' or 'html5'.")
    parser.add_option("--noisy",
                      action="store_const", const=DEBUG, dest="verbose",
                      help="Print debug messages.")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "Load extension EXTENSION.", metavar="EXTENSION")
    parser.add_option("-n", "--no_lazy_ol", dest="lazy_ol", 
                      action='store_false', default=True,
                      help="Observe number of first item of ordered lists.")

    (options, args) = parser.parse_args()

    if len(args) == 0:
        input_file = None
    else:
        input_file = args[0]

    if not options.extensions:
        options.extensions = []

    return {'input': input_file,
            'output': options.filename,
            'safe_mode': options.safe,
            'extensions': options.extensions,
            'encoding': options.encoding,
            'output_format': options.output_format,
            'lazy_ol': options.lazy_ol}, options.verbose

def run():
    """Run Markdown from the command line."""

    # Parse options and adjust logging level if necessary
    options, logging_level = parse_options()
    if not options: sys.exit(2)
    logger.setLevel(logging_level)
    logger.addHandler(logging.StreamHandler())

    # Run
    markdown.markdownFromFile(**options)

if __name__ == '__main__':
    # Support running module as a commandline command. 
    # Python 2.5 & 2.6 do: `python -m markdown.__main__ [options] [args]`.
    # Python 2.7 & 3.x do: `python -m markdown [options] [args]`.
    run()

########NEW FILE########
__FILENAME__ = mdutils
#!/usr/bin/env python
#-*- coding:utf-8 -*-
import os
import re
import logging

import consts
import commons
import shell
import web


logging.getLogger("mdutils").setLevel(logging.DEBUG)

try:
    import graphviz2png
except ImportError:
    graphviz2png = None
    logging.warn("import graphviz2png module failed")

try:
    import tex2png
except ImportError:
    tex2png = None
    logging.warn("import tex2png module failed")

import md_table
import markdown
import macro_cat


__all__ = [
    "text_path_to_button_path",
    "md2html",
    "zw_macro2md",
    "sequence_to_unorder_list",
]


def trac_wiki_code_block_to_md_code(text):
    """ This API deprecated in the future. """
    alias_p = '[a-zA-Z0-9#\-\+ \.]'
    shebang_p = '(?P<shebang_line>[\s]*#!%s{1,21}[\s]*?)' % alias_p

    code_p = '(?P<code>[^\f\v]+?)'

    code_block_p = "^\{\{\{[\s]*%s*%s[\s]*\}\}\}" % (shebang_p, code_p)
    p_obj = re.compile(code_block_p, re.MULTILINE)

    def code_repl(match_obj):
        code = match_obj.group('code')
        buf = "\n    ".join(code.split(os.linesep))
        buf = "    %s" % buf
        return buf

    return p_obj.sub(code_repl, text)

def code_block_to_md_code(text):
    alias_p = '[a-zA-Z0-9#\-\+ \.]'
    shebang_p = '(?P<shebang_line>[\s]*#!%s{1,21}[\s]*?)' % alias_p

    code_p = '(?P<code>[^\f\v]+?)'

    code_block_p = "^```[\s]*%s*%s[\s]*```" % (shebang_p, code_p)
    p_obj = re.compile(code_block_p, re.MULTILINE)

    def code_repl(match_obj):
        code = match_obj.group('code')
        buf = "\n    ".join(code.split(os.linesep))
        buf = "    %s" % buf
        return buf

    return p_obj.sub(code_repl, text)

def macro_tex2md(text, save_to_prefix, **macro_graphviz2md):
    shebang_p = "#!tex"
    code_p = '(?P<code>[^\f\v]+?)'
    code_block_p = "^\{\{\{[\s]*%s*%s[\s]*\}\}\}" % (shebang_p, code_p)
    p_obj = re.compile(code_block_p, re.MULTILINE)

    def code_repl(match_obj):
        code = match_obj.group('code')
        png_filename = tex2png.tex_text2png(text = code, save_to_prefix = save_to_prefix)

        return "![%s](%s)" % (png_filename, png_filename)

    return p_obj.sub(code_repl, text)

def macro_graphviz2md(text, save_to_prefix, **view_settings):
    shebang_p = "#!graphviz"
    code_p = '(?P<code>[^\f\v]+?)'
    code_block_p = "^\{\{\{[\s]*%s*%s[\s]*\}\}\}" % (shebang_p, code_p)
    p_obj = re.compile(code_block_p, re.MULTILINE)

    def code_repl(match_obj):
        code = match_obj.group('code')
        dst_path = graphviz2png.dot_text2png(text = code, png_path = save_to_prefix)
        png_filename = os.path.basename(dst_path)

        return "![%s](%s)" % (png_filename, png_filename)

    return p_obj.sub(code_repl, text)


def _fix_img_url(text, static_file_prefix = None):
    """
        >>> text = '![blah blah](20100426-400x339.png)'
        >>> static_file_prefix = '/static/files/'
        >>> _fix_img_url(text, static_file_prefix)
        '![blah blah](/static/files/20100426-400x339.png)'
    """
    def img_url_repl(match_obj):
        img_alt = match_obj.group("img_alt")
        img_url = match_obj.group("img_url")
        if static_file_prefix:
            fixed_img_url = os.path.join(static_file_prefix, img_url)
            return '![%s](%s)' % (img_alt, fixed_img_url)
        else:
            return '![%s](%s)' % (img_alt, img_url)

    img_url_p = r"!\[(?P<img_alt>.+?)\]\((?P<img_url>[^\s]+?)\)"
    img_url_p_obj = re.compile(img_url_p, re.MULTILINE)
    return img_url_p_obj.sub(img_url_repl, text)

def _fix_img_url_with_option(text, static_file_prefix = None):
    """
        >>> text = '![blah blah](20100426-400x339.png "png title")'
        >>> static_file_prefix = '/static/files/'
        >>> _fix_img_url_with_option(text, static_file_prefix)
        '![blah blah](/static/files/20100426-400x339.png "png title")'
    """
    def img_url_repl(match_obj):
        img_alt = match_obj.group('img_alt')
        img_url = match_obj.group('img_url')
        img_title = match_obj.group('img_title')
        if static_file_prefix:
            fixed_img_url = os.path.join(static_file_prefix, img_url)
            return '![%s](%s "%s")' % (img_alt, fixed_img_url, img_title)
        else:
            return '![%s](%s "%s")' % (img_alt, img_url, img_title)

    img_url_p = r"!\[(?P<img_alt>.+?)\]\((?P<img_url>[^\s]+?)\s\"(?P<img_title>.+?)\"\)"
    img_url_p_obj = re.compile(img_url_p, re.MULTILINE)
    return img_url_p_obj.sub(img_url_repl, text)

def uri2html_link(text):
    """ References:

     - http://stackoverflow.com/questions/6718633/python-regular-expression-again-match-url
     - http://daringfireball.net/2010/07/improved_regex_for_matching_urls
    """
    p = r'''(?i)\b((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))'''
    p_obj = re.compile(p, re.UNICODE | re.MULTILINE)

    def repl(match_obj):
        url = match_obj.groups()[0]
        return '<a href="%s">%s</a>' % (url, url)

    return p_obj.sub(repl, text)

def convert_static_file_url(text, static_file_prefix):
    text = _fix_img_url(text, static_file_prefix)
    text = _fix_img_url_with_option(text, static_file_prefix)
    return text


def path2hierarchy(path):
    """ Parse path and return hierarchy name and link pairs,
    inspired by [GNOME Nautilus](http://library.gnome.org/users/user-guide/2.32/nautilus-location-bar.html.en)
    and [Trac Wiki](http://trac.edgewall.org/browser/trunk/trac/wiki/web_ui.py) .

        >>> path = '/shugelab/users/lee'
        >>> t1 = [('shugelab', '/shugelab'), ('users', '/shugelab/users'), ('lee', '/shugelab/users/lee')]
        >>> path2hierarchy(path) == t1
        True
        >>> path2hierarchy('/') == [('index', '/~index')]
        True
    """
    caches = []

    if "/" == path:
        return [("index", "/~index")]
    elif "/" in path:
        parts = path.split('/')
        start = len(parts) - 2
        stop = -1
        step = -1
        for i in range(start, stop, step):
            name = parts[i + 1]
            links = "/%s" % "/".join(parts[1 : i + 2])
            if name == '':
                continue
            caches.append((name, links))

    caches.reverse()

    return caches

def text_path_to_button_path(path):
    buf = path2hierarchy(path)
    IS_ONLY_ONE_LEVEL = len(buf) == 1
    button_path = " / ".join(["[%s](%s/)" % (i[0], i[1]) for i in buf[:-1]])

    latest_level = buf[-1]
    path_name = latest_level[0]

    if IS_ONLY_ONE_LEVEL:
        button_path = path_name
    else:
        button_path = "%s / %s" % (button_path, path_name)

    return button_path


def md2html(config_agent, req_path, text, static_file_prefix, **view_settings):
    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = req_path_to_local_full_path(req_path = req_path, folder_pages_full_path = folder_pages_full_path)
    save_to_prefix = os.path.dirname(local_full_path)

    buf = text
    
    if tex2png:
        try:
            buf = macro_tex2md(buf, save_to_prefix = save_to_prefix, **view_settings)
        except Exception, ex:
            logging.error(str(ex))

            msg = "it seems that latex or dvipng doesn't works well on your box, or source code is invalid"
            logging.error(msg)

            buf = text

    if graphviz2png:
        try:
            buf = macro_graphviz2md(buf, save_to_prefix = save_to_prefix, **view_settings)
        except Exception, ex:
            logging.error(str(ex))

            msg = "it seems that graphviz doesn't works well on your box, or source code is invalid"
            logging.error(msg)

            buf = text

    if static_file_prefix:
        buf = convert_static_file_url(buf, static_file_prefix)

    buf = zw_macro2md(buf, folder_pages_full_path = folder_pages_full_path, req_path = req_path, **view_settings)

    buf = md_table.md_table2html(buf)
    buf = code_block_to_md_code(buf)
    buf = trac_wiki_code_block_to_md_code(buf)

    buf = markdown.markdown(buf)
    
    return buf


def req_path_to_local_full_path(req_path, folder_pages_full_path):
    req_path = web.rstrips(req_path, ".md")
    req_path = web.rstrips(req_path, ".markdown")

    if req_path in consts.g_special_paths:
        return folder_pages_full_path

    elif not req_path.endswith("/"):
        HOME_PAGE = ""
        if req_path == HOME_PAGE:
            return folder_pages_full_path

        path_md = "%s.md" % os.path.join(folder_pages_full_path, req_path)
        path_markdown = "%s.markdown" % os.path.join(folder_pages_full_path, req_path)

        if os.path.exists(path_md):
            return path_md
        elif os.path.exists(path_markdown):
            return path_markdown
        else:
            return path_md

    elif req_path == "/":
        return folder_pages_full_path

    else:
        return os.path.join(folder_pages_full_path, req_path)


def get_title_by_file_path_in_md(folder_pages_full_path, file_path_suffix):
    prefix = os.path.join(folder_pages_full_path, file_path_suffix)
    a = prefix + ".md"
    b = prefix + ".markdown"

    if os.path.exists(prefix):
        local_full_path = prefix
    elif os.path.exists(a):
        local_full_path = a
    elif os.path.exists(b):
        local_full_path =  b
    else:
        return None

    buf = commons.shutils.cat(local_full_path)
    if buf:
        buf = commons.strip_bom(buf)

    p = '^#\s*(?P<title>.+?)\s*$'
    p_obj = re.compile(p, re.UNICODE | re.MULTILINE)
    match_obj = p_obj.search(buf)

    if match_obj:
        title = match_obj.group('title')
    else:
        title = None
    return title

def sequence_to_unorder_list(folder_pages_full_path, seq, **view_settings):
    """
        >>> sequence_to_unorder_list("", ['a','b','c'], show_full_path = 1)
        u'- [a](/a)\\n- [b](/b)\\n- [c](/c)'
    """
    lis = []
    for i in seq:
        i = web.utils.strips(i, "./")
        stripped_name = web.utils.rstrips(i, ".md")
        stripped_name = web.utils.rstrips(stripped_name, ".markdown")

        name, url = stripped_name, "/" + stripped_name
        if not view_settings["show_full_path"]:
            file_path_suffix = name
            buf = get_title_by_file_path_in_md(folder_pages_full_path, file_path_suffix)
            if buf is None:
                name = name.split('/')[-1].replace('-', ' ').title()
            else:
                name = buf

        lis.append('- [%s](%s)' % (name, url))

    buf = "\n".join(lis)
    buf = web.utils.safeunicode(buf)

    return buf

def macro_zw2md_ls(text, folder_pages_full_path, **view_settings):
    shebang_p = "#!zw"
    code_p = '(?P<code>[^\f\v]+?)'
    code_block_p = "^\{\{\{[\s]*%s*%s[\s]*\}\}\}" % (shebang_p, code_p)
    p_obj = re.compile(code_block_p, re.MULTILINE)

    def code_repl(match_obj):
        code = match_obj.group('code')
        code = code.split("\n")[1]

        if code.startswith("ls("):
            p = 'ls\("(?P<path>.+?)",\s*maxdepth\s*=\s*(?P<maxdepth>\d+)\s*\)'
            m = re.match(p, code, re.UNICODE | re.MULTILINE)
            req_path = m.group("path")
            full_path = os.path.join(folder_pages_full_path, req_path)
            max_depth = int(m.group("maxdepth"))

            if os.path.exists(full_path):
                buf = shell.get_page_file_list_by_req_path(folder_pages_full_path = folder_pages_full_path,
                                                           req_path = req_path,
                                                           max_depth = max_depth)
                buf = sequence_to_unorder_list(folder_pages_full_path = folder_pages_full_path,
                                               seq = buf.split("\n"),
                                               **view_settings)
            else:
                buf = ""
            return buf

        buf_fixed = "{{{#!zw\n%s\n}}}" % code
        return buf_fixed
#        return code

    return p_obj.sub(code_repl, text)

def zw_macro2md(text, folder_pages_full_path, req_path, **view_settings):
    buf = text
    buf = macro_cat.macro_zw2md_cat(text = buf, folder_pages_full_path = folder_pages_full_path, req_path = req_path, **view_settings)
    buf = macro_zw2md_ls(text = buf, folder_pages_full_path = folder_pages_full_path, req_path = req_path, **view_settings)
    return buf


if __name__ == "__main__":
    import doctest
    doctest.testmod()

#    test_path2hierarchy()

########NEW FILE########
__FILENAME__ = md_table
"""
Markdown Extensions

this script supports

 - simple table


Simple table syntax:

    || name || desc ||
    | lee | author |

will be:

    <table>
        <tr>
            <th> name </th><th> desc </th>
        </tr>
        <tr>
            <td> lee </td><td> author </td>
        </tr>
    </table>

"""

import markdown
import re
import commons

__all__ = [
    "md_table2html"
]


def _escape_table_special_chars(text):
    escape_p = "!\|"
    p_obj = re.compile(escape_p, re.UNICODE)
    return p_obj.sub('\v\f', text)

def _un_escape_table_special_chars(text):
    return text.replace("\v\f", "|")


def _match_table(line):
    if not line:
        return False

    t_p = "^\|{1,2} (?P<cells>.+?) \|{1,2}(?:[ ]*)$"
    p_obj = re.compile(t_p, re.UNICODE)

    if p_obj.match(line) and line.count('|') >= 2:
        return True
    else:
        return False

def _parse_cells(line):
    cells_p = "^(?P<splitter>\|){1,2} (?P<cells>.+?) \|{1,2}(?:[ ]*)$"
    p_obj = re.compile(cells_p, re.UNICODE)
    m_obj = p_obj.match(line)

    if m_obj:
        cells = m_obj.group('cells')

        cells = commons.strutils.strips(markdown.markdown(cells), "<p>")
        cells = commons.strutils.strips(cells, "</p>")
        
        splitter = m_obj.group('splitter')
        cells = [cell.strip()
                for cell in cells.split(splitter)
                if cell.strip()]

        is_table_header = line.startswith("||")
        if not is_table_header:
            total_columns = line.count(" |") + 1
            buf = " </td> <td> ".join(cells)
            buf = "    <td> %s </td>" % buf
        else:
            total_columns = line.count(" ||") + 1
            buf = " </th> <th> ".join(cells)
            buf = "    <th> %s </th>" % buf

        return total_columns, buf

    return None, line


def md_table2html(text):
    """
    Parsing Rules
    
    ||      \what is\ || tbl beginning   || tbl body        || tbl ending      ||
    |  previous line  |  None            |  ?               |  ?               |
    |  current line   |  startswith('|') |  startswith('|') |  startswith('|') |
    |  next line      |  ?               |  ?               |  None            |
    """
    text = _escape_table_special_chars(text)
    resp = []

    lines = text.split("\n")
    total_lines = len(lines)

    total_columns = None

    for i in xrange(total_lines):
        prev_line = None
        curr_line = lines[i]
        next_line = None

        is_first_line = i == 0
        if not is_first_line:
            prev_line = lines[i - 1]

        is_latest_line = (i + 1) == total_lines
        if not is_latest_line:
            next_line = lines[i + 1]


        is_first_line_of_table = _match_table(curr_line) and (not prev_line) and (curr_line.count('||') >= 2)
        is_latest_line_of_table = _match_table(curr_line) and (not next_line)

        if is_first_line_of_table:
            resp.append("<table>")

            resp.append("<tr>")
            curr_total_columns, buf = _parse_cells(curr_line)
            total_columns = curr_total_columns
            resp.append(buf)
            resp.append("</tr>")

        elif is_latest_line_of_table:
            resp.append("<tr>")

            curr_total_columns, buf = _parse_cells(curr_line)
            resp.append(buf)

            if total_columns and curr_total_columns < total_columns:
                buf = "<td>&nbsp;</td>" * (total_columns - curr_total_columns)
                resp.append(buf)

            resp.append("</tr>")
            resp.append("</table>")

        elif _match_table(curr_line):
            resp.append("<tr>")

            curr_total_columns, buf = _parse_cells(curr_line)
            resp.append(buf)

            if total_columns and curr_total_columns < total_columns:
                buf = "<td>&nbsp;</td>" * (total_columns - curr_total_columns)
                resp.append(buf)

            resp.append("</tr>")

        else:
            resp.append(curr_line)

    buf = "\n".join(resp)
    buf = _un_escape_table_special_chars(buf)

    return buf


if __name__ == "__main__":
    buf = """\n\n||      \what is\ || tbl beginning   || tbl body        || tbl ending      ||\n|  previous line  |  None            |  ?               |  ?               |\n|  current line   |  startswith('|') |  startswith('|') |  startswith('|') |\n|  next line      |  ?               |  ?               |  None            |\n\n"""
    html_buf = md_table2html(buf)
    print html_buf
########NEW FILE########
__FILENAME__ = page
import logging
import os
import shutil

import web

import cache
import commons
import mdutils
import paginator
import search
import shell
import static_file


logging.getLogger("page").setLevel(logging.DEBUG)


def delete_page_file_by_full_path(local_full_path):
    if os.path.isfile(local_full_path):
        os.remove(local_full_path)
        return True
    elif os.path.isdir(local_full_path):
        idx_dot_md = os.path.join(local_full_path, "index.md")
        os.remove(idx_dot_md)
        return True
    return False

def get_the_same_folders_cssjs_files(req_path, local_full_path, folder_pages_full_path):
    """ NOTICE: this features doesn't works on some file systems, such as those mounted by sshfs """
    if os.path.isfile(local_full_path):
        work_path = os.path.dirname(local_full_path)
        static_file_prefix = os.path.join("/static/pages", os.path.dirname(req_path))

    elif os.path.isdir(local_full_path):
        work_path = local_full_path
        static_file_prefix = os.path.join("/static/pages", req_path)

    elif req_path == "home":
        work_path = os.path.dirname(local_full_path)
        static_file_prefix = os.path.join("/static/pages", os.path.dirname(req_path))

    else:
        # special pages, such as '/~all'
        work_path = folder_pages_full_path
        static_file_prefix = "/static/pages"

    iters = os.listdir(work_path)
    cssjs_files = [i for i in iters
                   if (not i.startswith(".")) and (i.endswith(".js") or i.endswith(".css"))]

    if not cssjs_files:
        return ""

    css_buf = ""
    js_buf = ""
    for i in cssjs_files:
        if i.endswith(".css"):
            path = os.path.join(static_file_prefix, i)
            css_buf = static_file.append_static_file(css_buf, path, file_type = "css")
        elif i.endswith(".js"):
            path = os.path.join(static_file_prefix, i)
            js_buf = static_file.append_static_file(js_buf, path, file_type = "js")

    return "%s\n    %s" % (css_buf, js_buf)

def wp_create(config_agent, req_path, path, content):
    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(path, folder_pages_full_path)

    if path.endswith("/"):
        file_full_path = os.path.join(local_full_path, "index.md")
    else:
        file_full_path = local_full_path

    parent_path = os.path.dirname(file_full_path)
    if not os.path.exists(parent_path):
        os.makedirs(parent_path)

    with open(file_full_path, "w'") as f:
        f.write(content)

    cache.update_recent_change_cache(folder_pages_full_path)
    cache.update_all_pages_list_cache(folder_pages_full_path = folder_pages_full_path)

    web.seeother(path)


def wp_read(config_agent, tpl_render, req_path):
    view_settings = get_view_settings(config_agent)

    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path, folder_pages_full_path)
    static_file_prefix = static_file.get_static_file_prefix_by_local_full_path(config_agent = config_agent,
                                                                               local_full_path = local_full_path,
                                                                               req_path = req_path)
    path_info = web.ctx.environ["PATH_INFO"]

    HOME_PAGE = ""
    if req_path != HOME_PAGE and view_settings["button_mode_path"]:
        buf = mdutils.text_path_to_button_path("/%s" % req_path)
        button_path = mdutils.md2html(config_agent = config_agent, req_path = req_path, text = buf,
                                      static_file_prefix = static_file_prefix, **view_settings)
    else:
        button_path = None
        view_settings["show_quick_links"] = False

    title = ""
    if os.path.isfile(local_full_path):
        # os.path.exists(local_full_path)
        buf = commons.shutils.cat(local_full_path)
        buf = commons.strutils.strip_bom(buf)

        title = mdutils.get_title_by_file_path_in_md(folder_pages_full_path = folder_pages_full_path, file_path_suffix = local_full_path)

    elif os.path.isdir(local_full_path):
        # os.path.exists(local_full_path)
        if req_path == HOME_PAGE:
            a = os.path.join(local_full_path, "index.md")
            b = os.path.join(local_full_path, "index.markdown")
            if os.path.exists(a) or os.path.exists(b):
                fixed_req_path = os.path.join(path_info, "index")
                return web.seeother(fixed_req_path)
            else:
                fixed_req_path = os.path.join(path_info, "~all")
                return web.seeother(fixed_req_path)
        else:
            # listdir /path/to/folder/*
            buf = shell.get_page_file_list_by_req_path(folder_pages_full_path = folder_pages_full_path, req_path = req_path)
            if buf:
                buf = mdutils.sequence_to_unorder_list(folder_pages_full_path = folder_pages_full_path,
                                                       seq = buf.split("\n"),
                                                       **view_settings)
                title = req_path
            else:
                buf = "folder `%s` exists, but there is no files" % path_info
    else:
        # not os.path.exists(local_full_path)
        readonly = config_agent.config.get("main", "readonly")
        if readonly:
            raise web.Forbidden()
        else:
            if path_info.endswith("/"):
                fixed_req_path = path_info + "index?action=update"
            else:
                fixed_req_path = path_info + "?action=update"
            return web.seeother(fixed_req_path)

    content = mdutils.md2html(config_agent = config_agent,
                              req_path = req_path,
                              text = buf,
                              static_file_prefix = static_file_prefix,
                              **view_settings)

    static_files = get_the_same_folders_cssjs_files(req_path = req_path, local_full_path = local_full_path,
                                                    folder_pages_full_path = folder_pages_full_path)
    if not static_files:
        static_files = static_file.get_global_static_files(**view_settings) + "\n"

    buf = tpl_render.canvas(config = config_agent.config,
                            static_files = static_files,
                            button_path = button_path,
                            req_path = req_path,
                            title = title,
                            content = content,
                            **view_settings)

    return buf


def wp_update(config_agent, tpl_render, req_path):
    view_settings = get_view_settings(config_agent, simple = True)
    static_files = static_file.get_global_static_files(**view_settings)

    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path, folder_pages_full_path)

    title = "Editing %s" % req_path
    create_new = False

    if local_full_path.endswith("/"):
        msg = "not allow to edit path/to/folder, using path/to/folder/index instead"
        raise web.BadRequest(message = msg)

    # os.path.exists(local_full_path)
    if os.path.isfile(local_full_path):
        buf = commons.shutils.cat(local_full_path)
    else:
        # not os.path.exists(local_full_path)
        create_new = True
        buf = ""

    return tpl_render.update(config_agent = config_agent,
                             static_files = static_files,
                             req_path = req_path,
                             create_new = create_new,
                             title = title,
                             content = buf,
                             **view_settings)

def wp_update_post(config_agent, req_path, new_content):
    path_info = web.ctx.environ["PATH_INFO"]

    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path, folder_pages_full_path)

    folder_parent = os.path.dirname(local_full_path)
    if not os.path.exists(folder_parent):
        os.makedirs(folder_parent)

    content = new_content.replace("\r\n", "\n")

    with open(local_full_path, "w") as f:
        f.write(content)

    cache.update_recent_change_cache(folder_pages_full_path)

    return web.seeother(path_info)


def wp_rename(config_agent, tpl_render, req_path):
    view_settings = get_view_settings(config_agent, simple = True)
    static_files = static_file.get_global_static_files(**view_settings)

    title = "Rename %s" % req_path
    old_path = req_path

    return tpl_render.rename(config_agent = config_agent,
                             static_files = static_files,
                             title = title,
                             old_path = old_path,
                             **view_settings)

def wp_rename_post(config_agent, tpl_render, req_path, new_path):
    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")

    old_path = req_path
    old_full_path = mdutils.req_path_to_local_full_path(old_path, folder_pages_full_path)
    new_full_path = mdutils.req_path_to_local_full_path(new_path, folder_pages_full_path)

    if old_full_path == new_full_path:
        return web.seeother("/%s" % new_path)
    elif not os.path.exists(old_full_path):
        msg = "old %s doesn't exists" % old_full_path
        raise web.BadRequest(msg)

    msg = """<pre>
allow
    file -> new_file
    folder -> new_folder

not allow
    file -> new_folder
    folder -> new_file
</pre>"""

    if os.path.isfile(old_full_path):
        if new_full_path.endswith("/"):
            raise web.BadRequest(msg)
    elif os.path.isdir(old_full_path):
        if not new_full_path.endswith("/"):
            raise web.BadRequest(msg)

    parent = os.path.dirname(new_full_path)
    if not os.path.exists(parent):
        os.makedirs(parent)

    shutil.move(old_full_path, new_full_path)

    cache.update_all_pages_list_cache(folder_pages_full_path)
    cache.update_recent_change_cache(folder_pages_full_path)

    if os.path.isfile(new_full_path):
        return web.seeother("/%s" % new_path)
    elif os.path.isdir(new_full_path):
        return web.seeother("/%s/" % new_path)
    else:
        raise web.BadRequest()

def wp_delete(config_agent, tpl_render, req_path):
    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path, folder_pages_full_path)

    path_info = web.ctx.environ["PATH_INFO"]

    if os.path.isfile(local_full_path):
        redirect_to = os.path.dirname(path_info)
        delete_page_file_by_full_path(local_full_path)
    elif os.path.isdir(local_full_path):
        redirect_to = os.path.dirname(commons.strutils.rstrip(path_info, "/"))
        delete_page_file_by_full_path(local_full_path)
    else:
        raise web.NotFound()

    cache.update_recent_change_cache(folder_pages_full_path)
    cache.update_all_pages_list_cache(folder_pages_full_path)

    return web.seeother(redirect_to)


def wp_source(config_agent, tpl_render, req_path):
    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path, folder_pages_full_path)

    if os.path.isfile(local_full_path):
        web.header("Content-Type", "text/plain; charset=UTF-8")
        buf = commons.shutils.cat(local_full_path)
        return buf
    elif os.path.isdir(local_full_path):
        msg = "folder doesn't providers source in Markdown, using file instead"
        raise web.BadRequest(msg)
    else:
        raise web.NotFound()

_stat_tpl = """# Stat

|| _ || _ ||
| Wiki pages | %d |
| Folder | %d |

"""

def wp_stat(config_agent, tpl_render, req_path):
    view_settings = get_view_settings(config_agent, simple = True)
    static_files = static_file.get_global_static_files(**view_settings)

    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path = req_path, folder_pages_full_path = folder_pages_full_path)
    static_file_prefix = static_file.get_static_file_prefix_by_local_full_path(config_agent = config_agent,
                                                                               local_full_path = local_full_path,
                                                                               req_path = req_path)
    title = "Stat"

    cmd = "find . -type f -name '*.md' -or -name '*.markdown' | wc -l "
    page_count = commons.shutils.run(cmd, cwd = folder_pages_full_path) or 0
    cmd = "find . -type d | wc -l "
    folder_count = commons.shutils.run(cmd, cwd = folder_pages_full_path) or 0
    buf = _stat_tpl % (int(page_count), int(folder_count))
    content = mdutils.md2html(config_agent = config_agent,
                              req_path = req_path,
                              text = buf,
                              static_file_prefix = static_file_prefix,
                              **view_settings)

    return tpl_render.canvas(config = config_agent.config,
                             static_files = static_files,
                             button_path = "",
                             req_path = req_path,
                             title = title,
                             content = content,
                             **view_settings)

def wp_new(config_agent, req_path, tpl_render):
    view_settings = get_view_settings(config_agent)
    static_files = static_file.get_global_static_files(**view_settings)

    title = "Create %s" % req_path

    return tpl_render.update(config_agent = config_agent,
                             static_files = static_files,
                             req_path = "",
                             title = title,
                             content = "",
                             create_new = True,
                             **view_settings)


def get_view_settings(config_agent, simple = False):
    """ Deprecated """
    theme_name = config_agent.config.get("frontend", "theme_name")

    c_fp = config_agent.config.get("frontend", "show_full_path")
    try:
        show_full_path = int(web.cookies().get("zw_show_full_path", c_fp))
    except AttributeError:
        show_full_path = c_fp

    c_toc = config_agent.config.getboolean("frontend", "auto_toc")
    try:
        auto_toc = int(web.cookies().get("zw_auto_toc", c_toc))
    except AttributeError:
        auto_toc = c_toc

    c_hc = config_agent.config.get("frontend", "highlight_code")
    try:
        highlight_code = int(web.cookies().get("zw_highlight", c_hc))
    except AttributeError:
        highlight_code = c_hc

    reader_mode = config_agent.config.getboolean("frontend", "reader_mode")

    show_quick_links = config_agent.config.getboolean("frontend", "show_quick_links")
    show_home_link = config_agent.config.getboolean("frontend", "show_home_link")

    button_mode_path = config_agent.config.getboolean("frontend", "button_mode_path")
    show_toolbox = True
    show_view_source_button = config_agent.config.getboolean("frontend", "show_view_source_button")

    if simple:
        auto_toc = False
        reader_mode = False
        highlight_code = False

    settings = dict(theme_name = theme_name,
                    show_full_path = show_full_path,
                    auto_toc = auto_toc, highlight_code = highlight_code, reader_mode = reader_mode,
                    show_quick_links = show_quick_links, show_home_link = show_home_link,
                    button_mode_path = button_mode_path,
                    show_toolbox = show_toolbox,
                    show_view_source_button = show_view_source_button)
    return settings


def wp_view_settings(config_agent, tpl_render, req_path):
    settings = get_view_settings(config_agent)
    static_files = static_file.get_global_static_files(**settings)
    return tpl_render.view_settings(static_files = static_files, **settings)


def wp_get_all_pages(config_agent, tpl_render, req_path, limit, offset):
    view_settings = get_view_settings(config_agent)
    view_settings["show_toolbox"] = False

    static_files = static_file.get_global_static_files(**view_settings)

    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path, folder_pages_full_path)
    static_file_prefix = static_file.get_static_file_prefix_by_local_full_path(config_agent = config_agent,
                                                                                local_full_path = local_full_path,
                                                                                req_path = req_path)

    buf = cache.get_all_pages_list_from_cache(config_agent)
    all_lines = buf.split()
    total_lines = len(all_lines)
    title = "All Pages List (%d/%d)" % (offset, total_lines / limit)

    start = offset * limit
    end = start + limit
    lines = all_lines[start:end]

    buf = mdutils.sequence_to_unorder_list(folder_pages_full_path = folder_pages_full_path,
                                           seq = lines,
                                           **view_settings)
    content = mdutils.md2html(config_agent = config_agent,
                              req_path = req_path, text = buf,
                              static_file_prefix = static_file_prefix,
                              **view_settings)

    pg = paginator.Paginator()
    pg.total = total_lines
    pg.current_offset = offset
    pg.limit = limit
    pg.url = "/~all"

    return tpl_render.canvas(config = config_agent.config,
                             static_files = static_files,
                             button_path = title,
                             req_path = "~all",
                             title = title,
                             content = content,
                             paginator = pg,
                             **view_settings)

def wp_get_recent_changes_from_cache(config_agent, tpl_render, req_path, limit, offset):
    view_settings = get_view_settings(config_agent)
    static_files = static_file.get_global_static_files(**view_settings)

    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path,
                                                          folder_pages_full_path)
    static_file_prefix = static_file.get_static_file_prefix_by_local_full_path(
        config_agent = config_agent,
        local_full_path = local_full_path,
        req_path = req_path)

    buf = cache.get_recent_changes_from_cache(config_agent)
    all_lines = buf.split()
    total_lines = len(all_lines)

    title = "Recent Changes (%d/%d)" % (offset, total_lines / limit)

    start = offset * limit
    end = start + limit
    lines = all_lines[start : end]

    buf = mdutils.sequence_to_unorder_list(folder_pages_full_path = folder_pages_full_path,
                                           seq = lines,
                                           **view_settings)
    content = mdutils.md2html(config_agent = config_agent,
                              req_path = req_path,
                              text = buf,
                              static_file_prefix = static_file_prefix,
                              **view_settings)

    pg = paginator.Paginator()
    pg.total = total_lines
    pg.current_offset = offset
    pg.limit = limit
    pg.url = "/~recent"

    return tpl_render.canvas(config = config_agent.config,
                             static_files = static_files,
                             button_path = title,
                             req_path = req_path,
                             title = title,
                             content = content,
                             paginator = pg,
                             **view_settings)



def wp_search(config_agent, tpl_render, req_path):
    view_settings = get_view_settings(config_agent)

    folder_pages_full_path = config_agent.get_full_path("paths", "pages_path")
    local_full_path = mdutils.req_path_to_local_full_path(req_path,
                                                          folder_pages_full_path)
    static_file_prefix = static_file.get_static_file_prefix_by_local_full_path(
        config_agent = config_agent,
        local_full_path = local_full_path,
        req_path = req_path)

    keywords = web.input().get("k")
    keywords = web.utils.safestr(keywords)
    title = "Search %s" % keywords

    if keywords:
        limit = config_agent.config.getint("pagination", "search_page_limit")
        lines = search.search_by_filename_and_file_content(keywords,
                                                          limit = limit)
        if lines:
            buf = mdutils.sequence_to_unorder_list(folder_pages_full_path = folder_pages_full_path,
                                                   seq = lines,
                                                   **view_settings)
        else:
            buf = None
    else:
        buf = None

    if buf:
        content = mdutils.md2html(config_agent = config_agent,
                                  req_path = req_path,
                                  text = buf,
                                  static_file_prefix = static_file_prefix,
                                  **view_settings)
    else:
       content = "matched not found"

    static_files = static_file.get_global_static_files(**view_settings)

    return tpl_render.search(config_agent = config_agent,
                             static_files = static_files,
                             title = title,
                             keywords = keywords,
                             content = content)

########NEW FILE########
__FILENAME__ = paginator
#!/usr/bin/env python
import math

__all__ = [
    "Paginator",
]


class Paginator(object):
    def __init__(self):
        self.current_offset = 0

        self.total = None
        self.limit = None
        self.url = None

    @property
    def count(self):
        """
        DON'T USE round build-in method, use math.ceil() instead.

        http://php.net/manual/en/function.round.php
        http://docs.python.org/library/math.html
        """
        return int(math.ceil(self.total * 1.0 / self.limit))

    @property
    def previous_page_url(self):
        return "%s?limit=%d&offset=%d" % (self.url, self.limit, self.current_offset - 1)

    @property
    def next_page_url(self):
        return "%s?limit=%d&offset=%d" % (self.url, self.limit, self.current_offset + 1)

    @property
    def has_previous_page(self):
        return self.current_offset > 0

    @property
    def has_next_page(self):
        return (self.current_offset * self.limit + self.limit) < self.total

########NEW FILE########
__FILENAME__ = apache2_wsgi_main
#!/usr/bin/env python
import os
import sys

PWD = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, PWD)

import conf
from zbox_wiki.main import web, Robots, SpecialWikiPage, WikiPage, mapping

application = web.application(mapping, globals()).wsgifunc()

########NEW FILE########
__FILENAME__ = fcgi_main
#!/usr/bin/env python

if __name__ == "__main__":
    from zbox_wiki.main import web, Robots, SpecialWikiPage, WikiPage, mapping

    app = web.application(mapping, locals())

    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
    app.run()

########NEW FILE########
__FILENAME__ = zwadmin
#!/usr/bin/env python
import ConfigParser
import logging
import os
import platform
import shutil

from commons import argparse
import zbox_wiki


log = logging.getLogger(__name__)


ZW_MOD_FULL_PATH = zbox_wiki.__path__[0]

IS_DEB_BASED = platform.linux_distribution()[0].lower()
if IS_DEB_BASED not in ("ubuntu", "debian"):
    IS_DEB_BASED = None


zwd_help_msg_for_deb_based = """
Start ZBox Wiki:

    zwd.py --port 8000 --path %s

If you want to run it as daemon/FCGI:

    sudo apt-get install nginx spawn-fcgi python-flup --no-install-recommends

    cd %s

    sudo cp nginx-debian.conf /etc/nginx/sites-available/zbox_wiki.acodemonkey.com.conf
    sudo ln -sf /etc/nginx/sites-available/zbox_wiki.acodemonkey.com.conf /etc/nginx/sites-enabled/zbox_wiki.acodemonkey.com.conf
    sudo /etc/init.d/nginx restart

    sh start_fcgi.sh

Visit
    http://localhost:8080

View its log:

    tail -f /var/log/nginx/error.log

Stop process:

    sh stop_fcgi.sh

Please report bug to shuge.lee <AT> GMail.
"""

zwd_help_msg = """
start ZBox Wiki:
    zwd.py --port 8000 --path %s

If you want to run it as daemon/FCGI,
visit http://webpy.org/cookbook/fastcgi-nginx for more information.

Please report bug to shuge.lee <AT> GMail.
"""


parser = argparse.ArgumentParser(description = "create/upgrade ZBox Wiki instance",
                                 epilog = "Please report bug to shuge.lee <AT> GMail.")
parser.add_argument("--create", help = "full path of instance")
parser.add_argument("--upgrade", help = "full path of instance")


def get_ans(msg, expect_ans_list = ("Y", "y", "N", "n", "A", "a")):
    ans = raw_input(msg)
    while ans not in expect_ans_list:
        print "expected answer in", expect_ans_list
        ans = raw_input(msg)
    return ans


def print_zwd_help_msg(instance_full_path):
    if IS_DEB_BASED:
        msg = zwd_help_msg_for_deb_based % (instance_full_path, instance_full_path)
    else:
        msg = zwd_help_msg % instance_full_path

    print msg


def cp_fcgi_scripts(instance_full_path):
    src = os.path.join(ZW_MOD_FULL_PATH, "scripts", "fcgi_main.py")
    dst = os.path.join(instance_full_path, "fcgi_main.py")
    shutil.copyfile(src, dst)
    os.chmod(dst, 0774)

    src = os.path.join(ZW_MOD_FULL_PATH, "scripts", "start_fcgi.sh")
    dst = os.path.join(instance_full_path, "start_fcgi.sh")
    shutil.copyfile(src, dst)
    os.chmod(dst, 0774)

    src = os.path.join(ZW_MOD_FULL_PATH, "scripts", "stop_fcgi.sh")
    dst = os.path.join(instance_full_path, "stop_fcgi.sh")
    shutil.copyfile(src, dst)
    os.chmod(dst, 0774)


    if IS_DEB_BASED:
        conf_file_name = "nginx-debian.conf"
        nginx_conf_tpl = os.path.join(ZW_MOD_FULL_PATH, conf_file_name)
        with open(nginx_conf_tpl) as f:
            buf = f.read()
        buf = buf.replace("/path/to/zw_instance", instance_full_path)
        nginx_conf_path = os.path.join(instance_full_path, conf_file_name)
        with open(nginx_conf_path, "w") as f:
            f.write(buf)

def fix_folder_pages_sym_link(instance_full_path):
    src = os.path.join(instance_full_path, "pages")
    dst = os.path.join(instance_full_path, "static", "pages")

    if os.path.islink(dst):
        got = os.readlink(dst)
        if got != src:
            msg = "expected %s -> %s, got %s" % (src, dst, got)
            print msg
            os.remove(dst)

            msg = "link %s -> %s" % (src, dst)
            print msg
            os.symlink(src, dst)

    elif os.path.isdir(dst) and (not os.path.islink(dst)):
        msg = "expected %s is a symbolic link, got a directory, delete them" % dst
        print msg
        shutil.rmtree(dst)

        msg = "link %s -> %s" % (src, dst)
        print msg
        os.symlink(src, dst)

    elif os.path.isfile(dst):
        msg = "expected %s is a symbolic link, got a file, delete it" % dst
        print msg
        os.remove(dst)

        msg = "link %s -> %s" % (src, dst)
        print msg
        os.symlink(src, dst)

def action_create(instance_full_path):
    default_index_md = "index.md"
    default_index_md_full_path = os.path.join(instance_full_path, "pages", default_index_md)
    folder_pages_full_path = os.path.join(instance_full_path, "pages")

    for folder_name in ("static", "templates", "pages"):
        src = os.path.join(ZW_MOD_FULL_PATH, folder_name)
        dst = os.path.join(instance_full_path, folder_name)

        if not os.path.exists(src):
            msg = "source folder %s doesn't exists, skip copy, you should to create destination %s by manual" % (src, dst)
            log.warn(msg)
            continue

        if os.path.exists(dst):
            msg = "%s already exists, skip" % dst
            log.warn(msg)
            continue
        shutil.copytree(src, dst)

    if not os.path.exists(folder_pages_full_path):
        os.makedirs(folder_pages_full_path, 0774)
   
    if not os.path.exists(default_index_md_full_path):    
        with open(default_index_md_full_path, 'w') as f:
            f.write("default index page in markdown")

    fix_folder_pages_sym_link(instance_full_path)

    for folder_name in ("tmp", "sessions"):
        src_full_path = os.path.join(instance_full_path, folder_name)

        if os.path.exists(src_full_path):
            msg = "%s already exists, skip" % src_full_path
            print msg
            continue
        os.mkdir(src_full_path)

    src = os.path.join(ZW_MOD_FULL_PATH, "default.cfg")
    dst = os.path.join(instance_full_path, "default.cfg")
    if os.path.exists(dst):
        msg = "%s already exists, recover it from default? [Y]es / [N]o " % dst
        ans = get_ans(msg, expect_ans_list = ["Y", "y", "N", "n"])
        if ans in ["Y", "y"]:
            print "copy %s -> %s" % (src, dst)
            shutil.copyfile(src, dst)
    else:
        shutil.copyfile(src, dst)
    os.chmod(dst, 0644)

    cp_fcgi_scripts(instance_full_path)
    print_zwd_help_msg(instance_full_path)


def action_upgrace(instance_full_path):
    folders = ("static", "templates")
    yes_to_all = False

    for i in folders:
        src = os.path.join(ZW_MOD_FULL_PATH, i)
        dst = os.path.join(instance_full_path, i)

        if os.path.exists(dst):
            msg = "%s already exists, recover it from default?  [Y]es / [N]o / yes to [A]ll " % dst
            if yes_to_all:
                shutil.rmtree(dst)
                
                print "copy %s -> %s" % (src, dst)
                shutil.copytree(src, dst)
            else:
                ans = get_ans(msg)
                if ans in ["A", "a"]:
                    yes_to_all = True
                if ans in ["Y", "y", "A", "a"]:
                    shutil.rmtree(dst)
                    
                    print "copy %s -> %s" % (src, dst)
                    shutil.copytree(src, dst)
        else:
            print "copy %s -> %s" % (src, dst)
            shutil.copytree(src, dst)

    fix_folder_pages_sym_link(instance_full_path)


    instance_config_file = os.path.join(instance_full_path, "default.cfg")
    default_config_file = os.path.join(ZW_MOD_FULL_PATH, "default.cfg")

    if not os.path.exists(instance_config_file):
        print "copy %s -> %s" % (default_config_file, instance_config_file)
        shutil.copy(default_config_file, instance_config_file)
    else:
        try:
            zbox_wiki.config_agent.load_config(paths = [instance_config_file])
        except ConfigParser.ParsingError:
            msg = "parsing %s failed, recover it from default? [Y/n]" % instance_config_file
            ans = raw_input(msg)
            if ans in ("Y", "y"):
                shutil.copy(default_config_file, instance_config_file)

    print_zwd_help_msg(instance_full_path)


if __name__ == "__main__":
    args = parser.parse_args()

    if args.create:
        path = args.create
        if not os.path.exists(path):
            os.makedirs(path)

        instance_full_path = os.path.realpath(path)
        action_create(instance_full_path)
        exit(0)

    elif args.upgrade:
        path = args.upgrade
        instance_full_path = os.path.realpath(path)
        action_upgrace(instance_full_path)
        exit(0)

    parser.print_help()

########NEW FILE########
__FILENAME__ = zwd
#!/usr/bin/env python
import os
import sys

from commons import argparse


default_port = 8080
default_addr = "0.0.0.0"

parser = argparse.ArgumentParser(description = "run ZBox Wiki instance", epilog = "Please report bug to shuge.lee <AT> GMail.")
parser.add_argument("--ip", help = "the IP address to bind to")
parser.add_argument("--port", type = int, help = "the port number to bind to")
parser.add_argument("--path", help = "full path of instance")


def check_conf_compatible_issues(sys_conf, instance_conf, instance_root_full_path):
    changes = ""
    ignore_fields = ("maintainer_email_suffix", "maintainer_email_prefix")

    for key, val in sys_conf.__dict__.iteritems():
        if key in ignore_fields:
            continue

        if key not in instance_conf.__dict__:
            if isinstance(val, basestring):
                changes += key + " = '" + str(val) + "' \n"
            elif isinstance(val, (int, long)):
                changes += key + " = " + str(val) + "\n"

    if changes:
        msg = "\n" \
              "Your instance's configuration file does not compatible with default's, \n" \
              "you have to upgrade your instance: \n\n" \
              "    zwadmin.py upgrade %s \n" % instance_root_full_path
        print msg

        exit( -1 )

def run_instance(args):
    instance_root_full_path = os.path.realpath(args.path)
    port = args.port or default_port
    ip = args.ip or default_addr

    # custom web.py listen IP address and port
    # http://jarln.net/archives/972
    script_name = sys.argv[0]
    listen_ip_port = "%s:%d" % (ip, port)
    fake_argv = [script_name, listen_ip_port]
    sys.argv = fake_argv


    from zbox_wiki import config_agent
    instance_config_file_full_path = os.path.join(instance_root_full_path, "default.cfg")
    instance_config = config_agent.load_config(paths = [instance_config_file_full_path],
                                               instance_full_path = instance_root_full_path)
    config_agent.config = instance_config

    pages_path = config_agent.get_full_path("paths", "pages_path")
    os.chdir(pages_path)

    import zbox_wiki
    zbox_wiki.main(instance_root_full_path)


if __name__ == "__main__":
    args = parser.parse_args()

    if args.path:
        run_instance(args)
        exit(0)

    parser.print_help()


########NEW FILE########
__FILENAME__ = search
import logging
import os
import web

import config_agent


logging.getLogger("search").setLevel(logging.DEBUG)


def search_by_filename_and_file_content(keywords, limit):
    """
    Following doesn't works if cmd contains pipe character:

        p_obj = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
        p_obj.wait()
        resp = p_obj.stdout.read().strip()

    So we have to do use deprecated syntax ```os.popen```, for more detail, see
    http://stackoverflow.com/questions/89228/how-to-call-external-command-in-python .
    """

    find_by_filename_matched = " -o -name ".join([" '*%s*' " % i for i in keywords.split()])
    find_by_content_matched = " \| ".join(keywords.split())
    is_multiple_keywords = find_by_content_matched.find("\|") != -1
    folder_page_full_path = config_agent.get_full_path("paths", "pages_path")

    if is_multiple_keywords:
        find_by_filename_cmd = " cd %s; "\
                               " find . \( -name %s \) -type f | " \
                               " grep -E '(.md$|.markdown$)' | head -n %d " % \
                               (folder_page_full_path, find_by_filename_matched, limit)

        find_by_content_cmd = " cd %s; " \
                              " grep ./ --recursive --ignore-case --include=*.{md,markdown} --regexp ' \(%s\) ' | " \
                              " awk -F ':' '{print $1}' | uniq | head -n %d " % \
                              (folder_page_full_path, find_by_content_matched, limit)
    else:
        find_by_filename_cmd = " cd %s; " \
                               " find . -name %s -type f | " \
                               " grep -E '(.md$|.markdown$)' | head -n %d " % \
                               (folder_page_full_path, find_by_filename_matched, limit)

        find_by_content_cmd = " cd %s; " \
                              " grep ./ --recursive --ignore-case --include=*.{md,markdown} --regexp '%s' | " \
                              " awk -F ':' '{print $1}' | uniq | head -n %d " % \
                              (folder_page_full_path, find_by_content_matched, limit)

    msg = "find files by name >>>" + find_by_filename_cmd
    logging.debug(msg)

    msg = "find files by content >>>" + find_by_content_cmd
    logging.debug(msg)


    matched_content_lines = os.popen(find_by_content_cmd).read().strip()
    matched_content_lines = web.utils.safeunicode(matched_content_lines)
    if matched_content_lines:
        matched_content_lines = web.utils.safeunicode(matched_content_lines)
        matched_content_lines = matched_content_lines.split("\n")

    matched_filename_lines = os.popen(find_by_filename_cmd).read().strip()
    matched_filename_lines = web.utils.safeunicode(matched_filename_lines)
    if matched_filename_lines:
        matched_filename_lines = web.utils.safeunicode(matched_filename_lines)
        matched_filename_lines = matched_filename_lines.split("\n")

    if matched_content_lines and matched_filename_lines:
        # NOTICE: build-in function set() doesn't keep order, we shouldn't use it.
        # mixed = set(matched_filename_lines)
        # mixed.update(set(matched_content_lines))
        mixed = web.utils.uniq(matched_filename_lines + matched_content_lines)
    elif matched_content_lines and not matched_filename_lines:
        mixed = matched_content_lines
    elif not matched_content_lines and matched_filename_lines:
        mixed = matched_filename_lines
    else:
        return None

    lines = mixed
    return lines

########NEW FILE########
__FILENAME__ = shell
import os
import logging

import web


logging.getLogger("shell").setLevel(logging.DEBUG)


def get_page_file_list_by_req_path(folder_pages_full_path, req_path, sort_by_modified_ts = False, max_depth = None, limit = None):
    if req_path in ("~all", "~recent"):
        path = "."
    else:
        path = web.utils.strips(req_path, "/")

    if max_depth is None:
        cmd = " cd %s; find %s -follow -name '*.md' -or -name '*.markdown'  " % \
            (folder_pages_full_path, path)
    else:
        cmd = " cd %s; find %s -maxdepth %d -follow -name '*.md' -or -name '*.markdown'  " % \
            (folder_pages_full_path, path, max_depth)
    cmd += " | grep -v  -E '(.index.md|.index.markdown)' "

    if sort_by_modified_ts:
        cmd += " | xargs ls -t "
    if limit is not None:
        cmd += " | head -n %d " % limit
    logging.info(cmd)

    buf = os.popen(cmd).read().strip()
    return buf
########NEW FILE########
__FILENAME__ = static_file
import logging
import os

import commons


logging.getLogger("static_file").setLevel(logging.DEBUG)


def append_static_file(text, file_path, file_type, add_newline=False):
    assert file_type in ("css", "js")

    if file_type == "css":
        ref = '<link href="%s" rel="stylesheet" type="text/css">' % file_path
    else:
        ref = '<script type="text/javascript" src="%s"></script>' % file_path

    if not add_newline:
        static_files = "%s\n    %s" % (text, ref)
    else:
        static_files = "%s\n\n    %s" % (text, ref)

    return static_files

def get_global_static_files(**view_settings):
    static_files = ""

    css_files = ("zw-base.css",)
    for i in css_files:
        path = os.path.join("/static", view_settings["theme_name"], "css", i)
        static_files = append_static_file(static_files, path, file_type = "css")

    if view_settings["reader_mode"]:
        path = os.path.join("/static", view_settings["theme_name"], "css", "zw-reader.css")
        static_files = append_static_file(static_files, path, file_type = "css")

    if view_settings["auto_toc"]:
        path = os.path.join("/static", view_settings["theme_name"], "css", "zw-toc.css")
        static_files = append_static_file(static_files, path, file_type = "css")

    if view_settings["highlight_code"]:
        path = os.path.join("/static", view_settings["theme_name"], "js", "prettify", "prettify.css")
        static_files = append_static_file(static_files, path, file_type = "css", add_newline = True)


    static_files = "%s\n" % static_files

    js_files = ("jquery.js", "jquery-ui.js")
    static_files += "\n"
    for i in js_files:
        path = os.path.join("/static", view_settings["theme_name"], "js", i)
        static_files = append_static_file(static_files, path, file_type = "js")

    js_files = ("zw-base.js", )
    static_files += "\n"
    for i in js_files:
        path = os.path.join("/static", view_settings["theme_name"], "js", i)
        static_files = append_static_file(static_files, path, file_type = "js")

    if view_settings["auto_toc"]:
        static_files += "\n"
        path = os.path.join("/static", view_settings["theme_name"], "js", "zw-toc.js")
        static_files = append_static_file(static_files, path, file_type = "js")

    if view_settings["highlight_code"]:
        static_files += "\n"
        js_files = (os.path.join("prettify", "prettify.js"), "highlight.js")
        for i in js_files:
            path = os.path.join("/static", view_settings["theme_name"], "js", i)
            static_files = append_static_file(static_files, path, file_type = "js")

    return static_files

def get_folder_static_full_path(config_agent):
    folder_static_name = config_agent.config.get("paths", "static_path")

    if os.path.isabs(folder_static_name):
        path = folder_static_name
    else:
        folder_pages_name = config_agent.config.get("paths", "pages_path")
        path = "/%s/%s" % (folder_static_name, folder_pages_name)

    return path

def get_static_file_prefix_by_local_full_path(config_agent, local_full_path, req_path):
    folder_static_name = config_agent.config.get("paths", "static_path")
    components = []

    if os.path.isfile(folder_static_name):
        chunk = os.path.basename(folder_static_name)
        components.append(chunk)
    elif isinstance(folder_static_name, basestring):
        chunk = folder_static_name
        components.append(chunk)

    folder_pages_name = config_agent.config.get("paths", "pages_path")
    chunk = os.path.basename(folder_pages_name)
    components.append(chunk)

    if os.path.isdir(local_full_path):
        components.append(req_path)
    elif os.path.isfile(local_full_path):
        chunk = os.path.dirname(req_path)
        components.append(chunk)

    prefix = '/' + '/'.join(components)

    return prefix
########NEW FILE########
__FILENAME__ = tex2png
#!/usr/bin/env python
"""
This script requires

 * latex (texlive-latex-base on Ubuntu)
 * dvipng (dvipng on Ubuntu)

Reference

 - Trac LatexMacro
"""
import os
import shutil
import tempfile
import sys

__all__ = [
    "tex_text2png"
]


DEBUG = False


TEX_PREAMBLE = r'''
\documentclass{article}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\pagestyle{empty}
\begin{document}
\begin{equation*}
'''

TEX_END = r'''
\end{equation*}
\end{document}
'''

def tex_text2png(text, save_to_prefix):
    text = text.strip()

    filename = str(hash(text)).replace("-", "")
    fullname = filename + ".png"
    png_full_path = os.path.join(save_to_prefix, fullname)

    if os.path.exists(png_full_path):
        return fullname

#    print "generating ..."
    
    tex_work_full_path = tempfile.mkdtemp(prefix="latex_")
    tex_full_path = os.path.join(tex_work_full_path, filename + ".tex")

    f = open(tex_full_path, "w+")
    tex_tpl = "%s\n%s\n%s" % (TEX_PREAMBLE, text, TEX_END)
    f.write(tex_tpl)
    f.close()


    compile_cmd = 'latex -output-directory %s -interaction nonstopmode %s ' % \
                  (tex_work_full_path, tex_full_path)

    if DEBUG:
        msg = compile_cmd
        sys.stdout.write("\n" + msg + "\n")
    else:
        disabled_debug_ouptut = " > /dev/null 2>/dev/null"        
        compile_cmd += disabled_debug_ouptut
        
    assert os.system(compile_cmd) == 256


    dvi_full_path = os.path.join(tex_work_full_path, filename + ".dvi")
    compile_cmd = "dvipng -T tight -x 1200 -z 0 -bg Transparent -o %s %s " % \
                     (png_full_path, dvi_full_path)

    if DEBUG:
        msg = compile_cmd
        sys.stdout.write("\n" + msg + "\n")
    else:
        disabled_debug_ouptut = " 2>/dev/null 1>/dev/null"
        compile_cmd += disabled_debug_ouptut
        
    assert os.system(compile_cmd) == 0

    shutil.rmtree(tex_work_full_path)

    return fullname


if __name__ == "__main__":
    save_to_prefix = "/tmp/zbox_wiki_tex_demo"
    if not os.path.exists(save_to_prefix):
        os.makedirs(save_to_prefix)

    test_text = "\n$\x0crac{\x07lpha^{\x08eta^2}}{\\delta + \x07lpha}$\n"
    filename = tex_text2png(text = test_text, save_to_prefix = save_to_prefix)

    dst_path = os.path.join(save_to_prefix, filename)
    msg = "save to: " + dst_path
    print msg

########NEW FILE########
__FILENAME__ = application
"""
Web application
(from web.py)
"""
import webapi as web
import webapi, wsgi, utils
import debugerror
from utils import lstrips, safeunicode
import sys

import urllib
import traceback
import itertools
import os
import types
from exceptions import SystemExit

try:
    import wsgiref.handlers
except ImportError:
    pass # don't break people with old Pythons

__all__ = [
    "application", "auto_application",
    "subdir_application", "subdomain_application", 
    "loadhook", "unloadhook",
    "autodelegate"
]

class application:
    """
    Application to delegate requests based on path.
    
        >>> urls = ("/hello", "hello")
        >>> app = application(urls, globals())
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> app.request("/hello").data
        'hello'
    """
    def __init__(self, mapping=(), fvars={}, autoreload=None):
        if autoreload is None:
            autoreload = web.config.get('debug', False)
        self.init_mapping(mapping)
        self.fvars = fvars
        self.processors = []
        
        self.add_processor(loadhook(self._load))
        self.add_processor(unloadhook(self._unload))
        
        if autoreload:
            def main_module_name():
                mod = sys.modules['__main__']
                file = getattr(mod, '__file__', None) # make sure this works even from python interpreter
                return file and os.path.splitext(os.path.basename(file))[0]

            def modname(fvars):
                """find name of the module name from fvars."""
                file, name = fvars.get('__file__'), fvars.get('__name__')
                if file is None or name is None:
                    return None

                if name == '__main__':
                    # Since the __main__ module can't be reloaded, the module has 
                    # to be imported using its file name.                    
                    name = main_module_name()
                return name
                
            mapping_name = utils.dictfind(fvars, mapping)
            module_name = modname(fvars)
            
            def reload_mapping():
                """loadhook to reload mapping and fvars."""
                mod = __import__(module_name, None, None, [''])
                mapping = getattr(mod, mapping_name, None)
                if mapping:
                    self.fvars = mod.__dict__
                    self.init_mapping(mapping)

            self.add_processor(loadhook(Reloader()))
            if mapping_name and module_name:
                self.add_processor(loadhook(reload_mapping))

            # load __main__ module usings its filename, so that it can be reloaded.
            if main_module_name() and '__main__' in sys.argv:
                try:
                    __import__(main_module_name())
                except ImportError:
                    pass
                    
    def _load(self):
        web.ctx.app_stack.append(self)
        
    def _unload(self):
        web.ctx.app_stack = web.ctx.app_stack[:-1]
        
        if web.ctx.app_stack:
            # this is a sub-application, revert ctx to earlier state.
            oldctx = web.ctx.get('_oldctx')
            if oldctx:
                web.ctx.home = oldctx.home
                web.ctx.homepath = oldctx.homepath
                web.ctx.path = oldctx.path
                web.ctx.fullpath = oldctx.fullpath
                
    def _cleanup(self):
        # Threads can be recycled by WSGI servers.
        # Clearing up all thread-local state to avoid interefereing with subsequent requests.
        utils.ThreadedDict.clear_all()

    def init_mapping(self, mapping):
        self.mapping = list(utils.group(mapping, 2))

    def add_mapping(self, pattern, classname):
        self.mapping.append((pattern, classname))

    def add_processor(self, processor):
        """
        Adds a processor to the application. 
        
            >>> urls = ("/(.*)", "echo")
            >>> app = application(urls, globals())
            >>> class echo:
            ...     def GET(self, name): return name
            ...
            >>>
            >>> def hello(handler): return "hello, " +  handler()
            ...
            >>> app.add_processor(hello)
            >>> app.request("/web.py").data
            'hello, web.py'
        """
        self.processors.append(processor)

    def request(self, localpart='/', method='GET', data=None,
                host="0.0.0.0:8080", headers=None, https=False, **kw):
        """Makes request to this application for the specified path and method.
        Response will be a storage object with data, status and headers.

            >>> urls = ("/hello", "hello")
            >>> app = application(urls, globals())
            >>> class hello:
            ...     def GET(self): 
            ...         web.header('Content-Type', 'text/plain')
            ...         return "hello"
            ...
            >>> response = app.request("/hello")
            >>> response.data
            'hello'
            >>> response.status
            '200 OK'
            >>> response.headers['Content-Type']
            'text/plain'

        To use https, use https=True.

            >>> urls = ("/redirect", "redirect")
            >>> app = application(urls, globals())
            >>> class redirect:
            ...     def GET(self): raise web.seeother("/foo")
            ...
            >>> response = app.request("/redirect")
            >>> response.headers['Location']
            'http://0.0.0.0:8080/foo'
            >>> response = app.request("/redirect", https=True)
            >>> response.headers['Location']
            'https://0.0.0.0:8080/foo'

        The headers argument specifies HTTP headers as a mapping object
        such as a dict.

            >>> urls = ('/ua', 'uaprinter')
            >>> class uaprinter:
            ...     def GET(self):
            ...         return 'your user-agent is ' + web.ctx.env['HTTP_USER_AGENT']
            ... 
            >>> app = application(urls, globals())
            >>> app.request('/ua', headers = {
            ...      'User-Agent': 'a small jumping bean/1.0 (compatible)'
            ... }).data
            'your user-agent is a small jumping bean/1.0 (compatible)'

        """
        path, maybe_query = urllib.splitquery(localpart)
        query = maybe_query or ""
        
        if 'env' in kw:
            env = kw['env']
        else:
            env = {}
        env = dict(env, HTTP_HOST=host, REQUEST_METHOD=method, PATH_INFO=path, QUERY_STRING=query, HTTPS=str(https))
        headers = headers or {}

        for k, v in headers.items():
            env['HTTP_' + k.upper().replace('-', '_')] = v

        if 'HTTP_CONTENT_LENGTH' in env:
            env['CONTENT_LENGTH'] = env.pop('HTTP_CONTENT_LENGTH')

        if 'HTTP_CONTENT_TYPE' in env:
            env['CONTENT_TYPE'] = env.pop('HTTP_CONTENT_TYPE')

        if method not in ["HEAD", "GET"]:
            data = data or ''
            import StringIO
            if isinstance(data, dict):
                q = urllib.urlencode(data)
            else:
                q = data
            env['wsgi.input'] = StringIO.StringIO(q)
            if not env.get('CONTENT_TYPE', '').lower().startswith('multipart/') and 'CONTENT_LENGTH' not in env:
                env['CONTENT_LENGTH'] = len(q)
        response = web.storage()
        def start_response(status, headers):
            response.status = status
            response.headers = dict(headers)
            response.header_items = headers
        response.data = "".join(self.wsgifunc()(env, start_response))
        return response

    def browser(self):
        import browser
        return browser.AppBrowser(self)

    def handle(self):
        fn, args = self._match(self.mapping, web.ctx.path)
        return self._delegate(fn, self.fvars, args)
        
    def handle_with_processors(self):
        def process(processors):
            try:
                if processors:
                    p, processors = processors[0], processors[1:]
                    return p(lambda: process(processors))
                else:
                    return self.handle()
            except web.HTTPError:
                raise
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                print >> web.debug, traceback.format_exc()
                raise self.internalerror()
        
        # processors must be applied in the resvere order. (??)
        return process(self.processors)
                        
    def wsgifunc(self, *middleware):
        """Returns a WSGI-compatible function for this application."""
        def peep(iterator):
            """Peeps into an iterator by doing an iteration
            and returns an equivalent iterator.
            """
            # wsgi requires the headers first
            # so we need to do an iteration
            # and save the result for later
            try:
                firstchunk = iterator.next()
            except StopIteration:
                firstchunk = ''

            return itertools.chain([firstchunk], iterator)    
                                
        def is_generator(x): return x and hasattr(x, 'next')
        
        def wsgi(env, start_resp):
            # clear threadlocal to avoid inteference of previous requests
            self._cleanup()

            self.load(env)
            try:
                # allow uppercase methods only
                if web.ctx.method.upper() != web.ctx.method:
                    raise web.nomethod()

                result = self.handle_with_processors()
                if is_generator(result):
                    result = peep(result)
                else:
                    result = [result]
            except web.HTTPError, e:
                result = [e.data]

            result = web.safestr(iter(result))

            status, headers = web.ctx.status, web.ctx.headers
            start_resp(status, headers)
            
            def cleanup():
                self._cleanup()
                yield '' # force this function to be a generator
                            
            return itertools.chain(result, cleanup())

        for m in middleware: 
            wsgi = m(wsgi)

        return wsgi

    def run(self, *middleware):
        """
        Starts handling requests. If called in a CGI or FastCGI context, it will follow
        that protocol. If called from the command line, it will start an HTTP
        server on the port named in the first command line argument, or, if there
        is no argument, on port 8080.
        
        `middleware` is a list of WSGI middleware which is applied to the resulting WSGI
        function.
        """
        return wsgi.runwsgi(self.wsgifunc(*middleware))
    
    def cgirun(self, *middleware):
        """
        Return a CGI handler. This is mostly useful with Google App Engine.
        There you can just do:
        
            main = app.cgirun()
        """
        wsgiapp = self.wsgifunc(*middleware)

        try:
            from google.appengine.ext.webapp.util import run_wsgi_app
            return run_wsgi_app(wsgiapp)
        except ImportError:
            # we're not running from within Google App Engine
            return wsgiref.handlers.CGIHandler().run(wsgiapp)
    
    def load(self, env):
        """Initializes ctx using env."""
        ctx = web.ctx
        ctx.clear()
        ctx.status = '200 OK'
        ctx.headers = []
        ctx.output = ''
        ctx.environ = ctx.env = env
        ctx.host = env.get('HTTP_HOST')

        if env.get('wsgi.url_scheme') in ['http', 'https']:
            ctx.protocol = env['wsgi.url_scheme']
        elif env.get('HTTPS', '').lower() in ['on', 'true', '1']:
            ctx.protocol = 'https'
        else:
            ctx.protocol = 'http'
        ctx.homedomain = ctx.protocol + '://' + env.get('HTTP_HOST', '[unknown]')
        ctx.homepath = os.environ.get('REAL_SCRIPT_NAME', env.get('SCRIPT_NAME', ''))
        ctx.home = ctx.homedomain + ctx.homepath
        #@@ home is changed when the request is handled to a sub-application.
        #@@ but the real home is required for doing absolute redirects.
        ctx.realhome = ctx.home
        ctx.ip = env.get('REMOTE_ADDR')
        ctx.method = env.get('REQUEST_METHOD')
        ctx.path = env.get('PATH_INFO')
        # http://trac.lighttpd.net/trac/ticket/406 requires:
        if env.get('SERVER_SOFTWARE', '').startswith('lighttpd/'):
            ctx.path = lstrips(env.get('REQUEST_URI').split('?')[0], ctx.homepath)
            # Apache and CherryPy webservers unquote the url but lighttpd doesn't. 
            # unquote explicitly for lighttpd to make ctx.path uniform across all servers.
            ctx.path = urllib.unquote(ctx.path)

        if env.get('QUERY_STRING'):
            ctx.query = '?' + env.get('QUERY_STRING', '')
        else:
            ctx.query = ''

        ctx.fullpath = ctx.path + ctx.query
        
        for k, v in ctx.iteritems():
            # convert all string values to unicode values and replace 
            # malformed data with a suitable replacement marker.
            if isinstance(v, str):
                ctx[k] = v.decode('utf-8', 'replace') 

        # status must always be str
        ctx.status = '200 OK'
        
        ctx.app_stack = []

    def _delegate(self, f, fvars, args=[]):
        def handle_class(cls):
            meth = web.ctx.method
            if meth == 'HEAD' and not hasattr(cls, meth):
                meth = 'GET'
            if not hasattr(cls, meth):
                raise web.nomethod(cls)
            tocall = getattr(cls(), meth)
            return tocall(*args)
            
        def is_class(o): return isinstance(o, (types.ClassType, type))
            
        if f is None:
            raise web.notfound()
        elif isinstance(f, application):
            return f.handle_with_processors()
        elif is_class(f):
            return handle_class(f)
        elif isinstance(f, basestring):
            if f.startswith('redirect '):
                url = f.split(' ', 1)[1]
                if web.ctx.method == "GET":
                    x = web.ctx.env.get('QUERY_STRING', '')
                    if x:
                        url += '?' + x
                raise web.redirect(url)
            elif '.' in f:
                mod, cls = f.rsplit('.', 1)
                mod = __import__(mod, None, None, [''])
                cls = getattr(mod, cls)
            else:
                cls = fvars[f]
            return handle_class(cls)
        elif hasattr(f, '__call__'):
            return f()
        else:
            return web.notfound()

    def _match(self, mapping, value):
        for pat, what in mapping:
            if isinstance(what, application):
                if value.startswith(pat):
                    f = lambda: self._delegate_sub_application(pat, what)
                    return f, None
                else:
                    continue
            elif isinstance(what, basestring):
                what, result = utils.re_subm('^' + pat + '$', what, value)
            else:
                result = utils.re_compile('^' + pat + '$').match(value)
                
            if result: # it's a match
                return what, [x for x in result.groups()]
        return None, None
        
    def _delegate_sub_application(self, dir, app):
        """Deletes request to sub application `app` rooted at the directory `dir`.
        The home, homepath, path and fullpath values in web.ctx are updated to mimic request
        to the subapp and are restored after it is handled. 
        
        @@Any issues with when used with yield?
        """
        web.ctx._oldctx = web.storage(web.ctx)
        web.ctx.home += dir
        web.ctx.homepath += dir
        web.ctx.path = web.ctx.path[len(dir):]
        web.ctx.fullpath = web.ctx.fullpath[len(dir):]
        return app.handle_with_processors()
            
    def get_parent_app(self):
        if self in web.ctx.app_stack:
            index = web.ctx.app_stack.index(self)
            if index > 0:
                return web.ctx.app_stack[index-1]
        
    def notfound(self):
        """Returns HTTPError with '404 not found' message"""
        parent = self.get_parent_app()
        if parent:
            return parent.notfound()
        else:
            return web._NotFound()
            
    def internalerror(self):
        """Returns HTTPError with '500 internal error' message"""
        parent = self.get_parent_app()
        if parent:
            return parent.internalerror()
        elif web.config.get('debug'):
            import debugerror
            return debugerror.debugerror()
        else:
            return web._InternalError()

class auto_application(application):
    """Application similar to `application` but urls are constructed 
    automatiacally using metaclass.

        >>> app = auto_application()
        >>> class hello(app.page):
        ...     def GET(self): return "hello, world"
        ...
        >>> class foo(app.page):
        ...     path = '/foo/.*'
        ...     def GET(self): return "foo"
        >>> app.request("/hello").data
        'hello, world'
        >>> app.request('/foo/bar').data
        'foo'
    """
    def __init__(self):
        application.__init__(self)

        class metapage(type):
            def __init__(klass, name, bases, attrs):
                type.__init__(klass, name, bases, attrs)
                path = attrs.get('path', '/' + name)

                # path can be specified as None to ignore that class
                # typically required to create a abstract base class.
                if path is not None:
                    self.add_mapping(path, klass)

        class page:
            path = None
            __metaclass__ = metapage

        self.page = page

# The application class already has the required functionality of subdir_application
subdir_application = application
                
class subdomain_application(application):
    """
    Application to delegate requests based on the host.

        >>> urls = ("/hello", "hello")
        >>> app = application(urls, globals())
        >>> class hello:
        ...     def GET(self): return "hello"
        >>>
        >>> mapping = (r"hello\.example\.com", app)
        >>> app2 = subdomain_application(mapping)
        >>> app2.request("/hello", host="hello.example.com").data
        'hello'
        >>> response = app2.request("/hello", host="something.example.com")
        >>> response.status
        '404 Not Found'
        >>> response.data
        'not found'
    """
    def handle(self):
        host = web.ctx.host.split(':')[0] #strip port
        fn, args = self._match(self.mapping, host)
        return self._delegate(fn, self.fvars, args)
        
    def _match(self, mapping, value):
        for pat, what in mapping:
            if isinstance(what, basestring):
                what, result = utils.re_subm('^' + pat + '$', what, value)
            else:
                result = utils.re_compile('^' + pat + '$').match(value)

            if result: # it's a match
                return what, [x for x in result.groups()]
        return None, None
        
def loadhook(h):
    """
    Converts a load hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done before handling request"
        ...
        >>> app.add_processor(loadhook(f))
    """
    def processor(handler):
        h()
        return handler()
        
    return processor
    
def unloadhook(h):
    """
    Converts an unload hook into an application processor.
    
        >>> app = auto_application()
        >>> def f(): "something done after handling request"
        ...
        >>> app.add_processor(unloadhook(f))    
    """
    def processor(handler):
        try:
            result = handler()
            is_generator = result and hasattr(result, 'next')
        except:
            # run the hook even when handler raises some exception
            h()
            raise

        if is_generator:
            return wrap(result)
        else:
            h()
            return result
            
    def wrap(result):
        def next():
            try:
                return result.next()
            except:
                # call the hook at the and of iterator
                h()
                raise

        result = iter(result)
        while True:
            yield next()
            
    return processor

def autodelegate(prefix=''):
    """
    Returns a method that takes one argument and calls the method named prefix+arg,
    calling `notfound()` if there isn't one. Example:

        urls = ('/prefs/(.*)', 'prefs')

        class prefs:
            GET = autodelegate('GET_')
            def GET_password(self): pass
            def GET_privacy(self): pass

    `GET_password` would get called for `/prefs/password` while `GET_privacy` for 
    `GET_privacy` gets called for `/prefs/privacy`.
    
    If a user visits `/prefs/password/change` then `GET_password(self, '/change')`
    is called.
    """
    def internal(self, arg):
        if '/' in arg:
            first, rest = arg.split('/', 1)
            func = prefix + first
            args = ['/' + rest]
        else:
            func = prefix + arg
            args = []
        
        if hasattr(self, func):
            try:
                return getattr(self, func)(*args)
            except TypeError:
                raise web.notfound()
        else:
            raise web.notfound()
    return internal

class Reloader:
    """Checks to see if any loaded modules have changed on disk and, 
    if so, reloads them.
    """

    """File suffix of compiled modules."""
    if sys.platform.startswith('java'):
        SUFFIX = '$py.class'
    else:
        SUFFIX = '.pyc'
    
    def __init__(self):
        self.mtimes = {}

    def __call__(self):
        for mod in sys.modules.values():
            self.check(mod)

    def check(self, mod):
        # jython registers java packages as modules but they either
        # don't have a __file__ attribute or its value is None
        if not (mod and hasattr(mod, '__file__') and mod.__file__):
            return

        try: 
            mtime = os.stat(mod.__file__).st_mtime
        except (OSError, IOError):
            return
        if mod.__file__.endswith(self.__class__.SUFFIX) and os.path.exists(mod.__file__[:-1]):
            mtime = max(os.stat(mod.__file__[:-1]).st_mtime, mtime)
            
        if mod not in self.mtimes:
            self.mtimes[mod] = mtime
        elif self.mtimes[mod] < mtime:
            try: 
                reload(mod)
                self.mtimes[mod] = mtime
            except ImportError: 
                pass
                
if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = browser
"""Browser to test web applications.
(from web.py)
"""
from utils import re_compile
from net import htmlunquote

import httplib, urllib, urllib2
import copy
from StringIO import StringIO

DEBUG = False

__all__ = [
    "BrowserError",
    "Browser", "AppBrowser",
    "AppHandler"
]

class BrowserError(Exception):
    pass

class Browser:
    def __init__(self):
        import cookielib
        self.cookiejar = cookielib.CookieJar()
        self._cookie_processor = urllib2.HTTPCookieProcessor(self.cookiejar)
        self.form = None

        self.url = "http://0.0.0.0:8080/"
        self.path = "/"
        
        self.status = None
        self.data = None
        self._response = None
        self._forms = None

    def reset(self):
        """Clears all cookies and history."""
        self.cookiejar.clear()

    def build_opener(self):
        """Builds the opener using urllib2.build_opener. 
        Subclasses can override this function to prodive custom openers.
        """
        return urllib2.build_opener()

    def do_request(self, req):
        if DEBUG:
            print 'requesting', req.get_method(), req.get_full_url()
        opener = self.build_opener()
        opener.add_handler(self._cookie_processor)
        try:
            self._response = opener.open(req)
        except urllib2.HTTPError, e:
            self._response = e

        self.url = self._response.geturl()
        self.path = urllib2.Request(self.url).get_selector()
        self.data = self._response.read()
        self.status = self._response.code
        self._forms = None
        self.form = None
        return self.get_response()

    def open(self, url, data=None, headers={}):
        """Opens the specified url."""
        url = urllib.basejoin(self.url, url)
        req = urllib2.Request(url, data, headers)
        return self.do_request(req)

    def show(self):
        """Opens the current page in real web browser."""
        f = open('page.html', 'w')
        f.write(self.data)
        f.close()

        import webbrowser, os
        url = 'file://' + os.path.abspath('page.html')
        webbrowser.open(url)

    def get_response(self):
        """Returns a copy of the current response."""
        return urllib.addinfourl(StringIO(self.data), self._response.info(), self._response.geturl())

    def get_soup(self):
        """Returns beautiful soup of the current document."""
        import BeautifulSoup
        return BeautifulSoup.BeautifulSoup(self.data)

    def get_text(self, e=None):
        """Returns content of e or the current document as plain text."""
        e = e or self.get_soup()
        return ''.join([htmlunquote(c) for c in e.recursiveChildGenerator() if isinstance(c, unicode)])

    def _get_links(self):
        soup = self.get_soup()
        return [a for a in soup.findAll(name='a')]
        
    def get_links(self, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        """Returns all links in the document."""
        return self._filter_links(self._get_links(),
            text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)

    def follow_link(self, link=None, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        if link is None:
            links = self._filter_links(self.get_links(),
                text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)
            link = links and links[0]
            
        if link:
            return self.open(link['href'])
        else:
            raise BrowserError("No link found")
            
    def find_link(self, text=None, text_regex=None, url=None, url_regex=None, predicate=None):
        links = self._filter_links(self.get_links(), 
            text=text, text_regex=text_regex, url=url, url_regex=url_regex, predicate=predicate)
        return links and links[0] or None
            
    def _filter_links(self, links, 
            text=None, text_regex=None,
            url=None, url_regex=None,
            predicate=None):
        predicates = []
        if text is not None:
            predicates.append(lambda link: link.string == text)
        if text_regex is not None:
            predicates.append(lambda link: re_compile(text_regex).search(link.string or ''))
        if url is not None:
            predicates.append(lambda link: link.get('href') == url)
        if url_regex is not None:
            predicates.append(lambda link: re_compile(url_regex).search(link.get('href', '')))
        if predicate:
            predicate.append(predicate)

        def f(link):
            for p in predicates:
                if not p(link):
                    return False
            return True

        return [link for link in links if f(link)]

    def get_forms(self):
        """Returns all forms in the current document.
        The returned form objects implement the ClientForm.HTMLForm interface.
        """
        if self._forms is None:
            import ClientForm
            self._forms = ClientForm.ParseResponse(self.get_response(), backwards_compat=False)
        return self._forms

    def select_form(self, name=None, predicate=None, index=0):
        """Selects the specified form."""
        forms = self.get_forms()

        if name is not None:
            forms = [f for f in forms if f.name == name]
        if predicate:
            forms = [f for f in forms if predicate(f)]
            
        if forms:
            self.form = forms[index]
            return self.form
        else:
            raise BrowserError("No form selected.")
        
    def submit(self, **kw):
        """submits the currently selected form."""
        if self.form is None:
            raise BrowserError("No form selected.")
        req = self.form.click(**kw)
        return self.do_request(req)

    def __getitem__(self, key):
        return self.form[key]

    def __setitem__(self, key, value):
        self.form[key] = value

class AppBrowser(Browser):
    """Browser interface to test web.py apps.
    
        b = AppBrowser(app)
        b.open('/')
        b.follow_link(text='Login')
        
        b.select_form(name='login')
        b['username'] = 'joe'
        b['password'] = 'secret'
        b.submit()

        assert b.path == '/'
        assert 'Welcome joe' in b.get_text()
    """
    def __init__(self, app):
        Browser.__init__(self)
        self.app = app

    def build_opener(self):
        return urllib2.build_opener(AppHandler(self.app))

class AppHandler(urllib2.HTTPHandler):
    """urllib2 handler to handle requests using web.py application."""
    handler_order = 100

    def __init__(self, app):
        self.app = app

    def http_open(self, req):
        result = self.app.request(
            localpart=req.get_selector(),
            method=req.get_method(),
            host=req.get_host(),
            data=req.get_data(),
            headers=dict(req.header_items()),
            https=req.get_type() == "https"
        )
        return self._make_response(result, req.get_full_url())

    def https_open(self, req):
        return self.http_open(req)
    
    try:
        https_request = urllib2.HTTPHandler.do_request_
    except AttributeError:
        # for python 2.3
        pass

    def _make_response(self, result, url):
        data = "\r\n".join(["%s: %s" % (k, v) for k, v in result.header_items])
        headers = httplib.HTTPMessage(StringIO(data))
        response = urllib.addinfourl(StringIO(result.data), headers, url)
        code, msg = result.status.split(None, 1)
        response.code, response.msg = int(code), msg
        return response

########NEW FILE########
__FILENAME__ = template
"""
Interface to various templating engines.
"""
import os.path

__all__ = [
    "render_cheetah", "render_genshi", "render_mako",
    "cache", 
]

class render_cheetah:
    """Rendering interface to Cheetah Templates.

    Example:

        render = render_cheetah('templates')
        render.hello(name="cheetah")
    """
    def __init__(self, path):
        # give error if Chetah is not installed
        from Cheetah.Template import Template
        self.path = path

    def __getattr__(self, name):
        from Cheetah.Template import Template
        path = os.path.join(self.path, name + ".html")
        
        def template(**kw):
            t = Template(file=path, searchList=[kw])
            return t.respond()

        return template
    
class render_genshi:
    """Rendering interface genshi templates.
    Example:

    for xml/html templates.

        render = render_genshi(['templates/'])
        render.hello(name='genshi')

    For text templates:

        render = render_genshi(['templates/'], type='text')
        render.hello(name='genshi')
    """

    def __init__(self, *a, **kwargs):
        from genshi.template import TemplateLoader

        self._type = kwargs.pop('type', None)
        self._loader = TemplateLoader(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"

        if self._type == "text":
            from genshi.template import TextTemplate
            cls = TextTemplate
            type = "text"
        else:
            cls = None
            type = None

        t = self._loader.load(path, cls=cls)
        def template(**kw):
            stream = t.generate(**kw)
            if type:
                return stream.render(type)
            else:
                return stream.render()
        return template

class render_jinja:
    """Rendering interface to Jinja2 Templates
    
    Example:

        render= render_jinja('templates')
        render.hello(name='jinja2')
    """
    def __init__(self, *a, **kwargs):
        extensions = kwargs.pop('extensions', [])
        globals = kwargs.pop('globals', {})

        from jinja2 import Environment,FileSystemLoader
        self._lookup = Environment(loader=FileSystemLoader(*a, **kwargs), extensions=extensions)
        self._lookup.globals.update(globals)
        
    def __getattr__(self, name):
        # Assuming all templates end with .html
        path = name + '.html'
        t = self._lookup.get_template(path)
        return t.render
        
class render_mako:
    """Rendering interface to Mako Templates.

    Example:

        render = render_mako(directories=['templates'])
        render.hello(name="mako")
    """
    def __init__(self, *a, **kwargs):
        from mako.lookup import TemplateLookup
        self._lookup = TemplateLookup(*a, **kwargs)

    def __getattr__(self, name):
        # Assuming all templates are html
        path = name + ".html"
        t = self._lookup.get_template(path)
        return t.render

class cache:
    """Cache for any rendering interface.
    
    Example:

        render = cache(render_cheetah("templates/"))
        render.hello(name='cache')
    """
    def __init__(self, render):
        self._render = render
        self._cache = {}

    def __getattr__(self, name):
        if name not in self._cache:
            self._cache[name] = getattr(self._render, name)
        return self._cache[name]

########NEW FILE########
__FILENAME__ = db
"""
Database API
(part of web.py)
"""

__all__ = [
  "UnknownParamstyle", "UnknownDB", "TransactionError", 
  "sqllist", "sqlors", "reparam", "sqlquote",
  "SQLQuery", "SQLParam", "sqlparam",
  "SQLLiteral", "sqlliteral",
  "database", 'DB',
]

import time
try:
    import datetime
except ImportError:
    datetime = None

try: set
except NameError:
    from sets import Set as set
    
from utils import threadeddict, storage, iters, iterbetter, safestr, safeunicode

try:
    # db module can work independent of web.py
    from webapi import debug, config
except:
    import sys
    debug = sys.stderr
    config = storage()

class UnknownDB(Exception):
    """raised for unsupported dbms"""
    pass

class _ItplError(ValueError): 
    def __init__(self, text, pos):
        ValueError.__init__(self)
        self.text = text
        self.pos = pos
    def __str__(self):
        return "unfinished expression in %s at char %d" % (
            repr(self.text), self.pos)

class TransactionError(Exception): pass

class UnknownParamstyle(Exception): 
    """
    raised for unsupported db paramstyles

    (currently supported: qmark, numeric, format, pyformat)
    """
    pass
    
class SQLParam(object):
    """
    Parameter in SQLQuery.
    
        >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam("joe")])
        >>> q
        <sql: "SELECT * FROM test WHERE name='joe'">
        >>> q.query()
        'SELECT * FROM test WHERE name=%s'
        >>> q.values()
        ['joe']
    """
    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value
        
    def get_marker(self, paramstyle='pyformat'):
        if paramstyle == 'qmark':
            return '?'
        elif paramstyle == 'numeric':
            return ':1'
        elif paramstyle is None or paramstyle in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, paramstyle
        
    def sqlquery(self): 
        return SQLQuery([self])
        
    def __add__(self, other):
        return self.sqlquery() + other
        
    def __radd__(self, other):
        return other + self.sqlquery() 
            
    def __str__(self): 
        return str(self.value)
    
    def __repr__(self):
        return '<param: %s>' % repr(self.value)

sqlparam =  SQLParam

class SQLQuery(object):
    """
    You can pass this sort of thing as a clause in any db function.
    Otherwise, you can pass a dictionary to the keyword argument `vars`
    and the function will call reparam for you.

    Internally, consists of `items`, which is a list of strings and
    SQLParams, which get concatenated to produce the actual query.
    """
    __slots__ = ["items"]

    # tested in sqlquote's docstring
    def __init__(self, items=None):
        r"""Creates a new SQLQuery.
        
            >>> SQLQuery("x")
            <sql: 'x'>
            >>> q = SQLQuery(['SELECT * FROM ', 'test', ' WHERE x=', SQLParam(1)])
            >>> q
            <sql: 'SELECT * FROM test WHERE x=1'>
            >>> q.query(), q.values()
            ('SELECT * FROM test WHERE x=%s', [1])
            >>> SQLQuery(SQLParam(1))
            <sql: '1'>
        """
        if items is None:
            self.items = []
        elif isinstance(items, list):
            self.items = items
        elif isinstance(items, SQLParam):
            self.items = [items]
        elif isinstance(items, SQLQuery):
            self.items = list(items.items)
        else:
            self.items = [items]
            
        # Take care of SQLLiterals
        for i, item in enumerate(self.items):
            if isinstance(item, SQLParam) and isinstance(item.value, SQLLiteral):
                self.items[i] = item.value.v

    def append(self, value):
        self.items.append(value)

    def __add__(self, other):
        if isinstance(other, basestring):
            items = [other]
        elif isinstance(other, SQLQuery):
            items = other.items
        else:
            return NotImplemented
        return SQLQuery(self.items + items)

    def __radd__(self, other):
        if isinstance(other, basestring):
            items = [other]
        else:
            return NotImplemented
            
        return SQLQuery(items + self.items)

    def __iadd__(self, other):
        if isinstance(other, (basestring, SQLParam)):
            self.items.append(other)
        elif isinstance(other, SQLQuery):
            self.items.extend(other.items)
        else:
            return NotImplemented
        return self

    def __len__(self):
        return len(self.query())
        
    def query(self, paramstyle=None):
        """
        Returns the query part of the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.query()
            'SELECT * FROM test WHERE name=%s'
            >>> q.query(paramstyle='qmark')
            'SELECT * FROM test WHERE name=?'
        """
        s = []
        for x in self.items:
            if isinstance(x, SQLParam):
                x = x.get_marker(paramstyle)
                s.append(safestr(x))
            else:
                x = safestr(x)
                # automatically escape % characters in the query
                # For backward compatability, ignore escaping when the query looks already escaped
                if paramstyle in ['format', 'pyformat']:
                    if '%' in x and '%%' not in x:
                        x = x.replace('%', '%%')
                s.append(x)
        return "".join(s)
    
    def values(self):
        """
        Returns the values of the parameters used in the sql query.
            >>> q = SQLQuery(["SELECT * FROM test WHERE name=", SQLParam('joe')])
            >>> q.values()
            ['joe']
        """
        return [i.value for i in self.items if isinstance(i, SQLParam)]
        
    def join(items, sep=' ', prefix=None, suffix=None, target=None):
        """
        Joins multiple queries.
        
        >>> SQLQuery.join(['a', 'b'], ', ')
        <sql: 'a, b'>

        Optinally, prefix and suffix arguments can be provided.

        >>> SQLQuery.join(['a', 'b'], ', ', prefix='(', suffix=')')
        <sql: '(a, b)'>

        If target argument is provided, the items are appended to target instead of creating a new SQLQuery.
        """
        if target is None:
            target = SQLQuery()

        target_items = target.items

        if prefix:
            target_items.append(prefix)

        for i, item in enumerate(items):
            if i != 0:
                target_items.append(sep)
            if isinstance(item, SQLQuery):
                target_items.extend(item.items)
            else:
                target_items.append(item)

        if suffix:
            target_items.append(suffix)
        return target
    
    join = staticmethod(join)
    
    def _str(self):
        try:
            return self.query() % tuple([sqlify(x) for x in self.values()])            
        except (ValueError, TypeError):
            return self.query()
        
    def __str__(self):
        return safestr(self._str())
        
    def __unicode__(self):
        return safeunicode(self._str())

    def __repr__(self):
        return '<sql: %s>' % repr(str(self))

class SQLLiteral: 
    """
    Protects a string from `sqlquote`.

        >>> sqlquote('NOW()')
        <sql: "'NOW()'">
        >>> sqlquote(SQLLiteral('NOW()'))
        <sql: 'NOW()'>
    """
    def __init__(self, v): 
        self.v = v

    def __repr__(self): 
        return self.v

sqlliteral = SQLLiteral

def _sqllist(values):
    """
        >>> _sqllist([1, 2, 3])
        <sql: '(1, 2, 3)'>
    """
    items = []
    items.append('(')
    for i, v in enumerate(values):
        if i != 0:
            items.append(', ')
        items.append(sqlparam(v))
    items.append(')')
    return SQLQuery(items)

def reparam(string_, dictionary): 
    """
    Takes a string and a dictionary and interpolates the string
    using values from the dictionary. Returns an `SQLQuery` for the result.

        >>> reparam("s = $s", dict(s=True))
        <sql: "s = 't'">
        >>> reparam("s IN $s", dict(s=[1, 2]))
        <sql: 's IN (1, 2)'>
    """
    dictionary = dictionary.copy() # eval mucks with it
    vals = []
    result = []
    for live, chunk in _interpolate(string_):
        if live:
            v = eval(chunk, dictionary)
            result.append(sqlquote(v))
        else: 
            result.append(chunk)
    return SQLQuery.join(result, '')

def sqlify(obj): 
    """
    converts `obj` to its proper SQL version

        >>> sqlify(None)
        'NULL'
        >>> sqlify(True)
        "'t'"
        >>> sqlify(3)
        '3'
    """
    # because `1 == True and hash(1) == hash(True)`
    # we have to do this the hard way...

    if obj is None:
        return 'NULL'
    elif obj is True:
        return "'t'"
    elif obj is False:
        return "'f'"
    elif datetime and isinstance(obj, datetime.datetime):
        return repr(obj.isoformat())
    else:
        if isinstance(obj, unicode): obj = obj.encode('utf8')
        return repr(obj)

def sqllist(lst): 
    """
    Converts the arguments for use in something like a WHERE clause.
    
        >>> sqllist(['a', 'b'])
        'a, b'
        >>> sqllist('a')
        'a'
        >>> sqllist(u'abc')
        u'abc'
    """
    if isinstance(lst, basestring): 
        return lst
    else:
        return ', '.join(lst)

def sqlors(left, lst):
    """
    `left is a SQL clause like `tablename.arg = ` 
    and `lst` is a list of values. Returns a reparam-style
    pair featuring the SQL that ORs together the clause
    for each item in the lst.

        >>> sqlors('foo = ', [])
        <sql: '1=2'>
        >>> sqlors('foo = ', [1])
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', 1)
        <sql: 'foo = 1'>
        >>> sqlors('foo = ', [1,2,3])
        <sql: '(foo = 1 OR foo = 2 OR foo = 3 OR 1=2)'>
    """
    if isinstance(lst, iters):
        lst = list(lst)
        ln = len(lst)
        if ln == 0:
            return SQLQuery("1=2")
        if ln == 1:
            lst = lst[0]

    if isinstance(lst, iters):
        return SQLQuery(['('] + 
          sum([[left, sqlparam(x), ' OR '] for x in lst], []) +
          ['1=2)']
        )
    else:
        return left + sqlparam(lst)
        
def sqlwhere(dictionary, grouping=' AND '): 
    """
    Converts a `dictionary` to an SQL WHERE clause `SQLQuery`.
    
        >>> sqlwhere({'cust_id': 2, 'order_id':3})
        <sql: 'order_id = 3 AND cust_id = 2'>
        >>> sqlwhere({'cust_id': 2, 'order_id':3}, grouping=', ')
        <sql: 'order_id = 3, cust_id = 2'>
        >>> sqlwhere({'a': 'a', 'b': 'b'}).query()
        'a = %s AND b = %s'
    """
    return SQLQuery.join([k + ' = ' + sqlparam(v) for k, v in dictionary.items()], grouping)

def sqlquote(a): 
    """
    Ensures `a` is quoted properly for use in a SQL query.

        >>> 'WHERE x = ' + sqlquote(True) + ' AND y = ' + sqlquote(3)
        <sql: "WHERE x = 't' AND y = 3">
        >>> 'WHERE x = ' + sqlquote(True) + ' AND y IN ' + sqlquote([2, 3])
        <sql: "WHERE x = 't' AND y IN (2, 3)">
    """
    if isinstance(a, list):
        return _sqllist(a)
    else:
        return sqlparam(a).sqlquery()

class Transaction:
    """Database transaction."""
    def __init__(self, ctx):
        self.ctx = ctx
        self.transaction_count = transaction_count = len(ctx.transactions)

        class transaction_engine:
            """Transaction Engine used in top level transactions."""
            def do_transact(self):
                ctx.commit(unload=False)

            def do_commit(self):
                ctx.commit()

            def do_rollback(self):
                ctx.rollback()

        class subtransaction_engine:
            """Transaction Engine used in sub transactions."""
            def query(self, q):
                db_cursor = ctx.db.cursor()
                ctx.db_execute(db_cursor, SQLQuery(q % transaction_count))

            def do_transact(self):
                self.query('SAVEPOINT webpy_sp_%s')

            def do_commit(self):
                self.query('RELEASE SAVEPOINT webpy_sp_%s')

            def do_rollback(self):
                self.query('ROLLBACK TO SAVEPOINT webpy_sp_%s')

        class dummy_engine:
            """Transaction Engine used instead of subtransaction_engine 
            when sub transactions are not supported."""
            do_transact = do_commit = do_rollback = lambda self: None

        if self.transaction_count:
            # nested transactions are not supported in some databases
            if self.ctx.get('ignore_nested_transactions'):
                self.engine = dummy_engine()
            else:
                self.engine = subtransaction_engine()
        else:
            self.engine = transaction_engine()

        self.engine.do_transact()
        self.ctx.transactions.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exctype, excvalue, traceback):
        if exctype is not None:
            self.rollback()
        else:
            self.commit()

    def commit(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_commit()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

    def rollback(self):
        if len(self.ctx.transactions) > self.transaction_count:
            self.engine.do_rollback()
            self.ctx.transactions = self.ctx.transactions[:self.transaction_count]

class DB: 
    """Database"""
    def __init__(self, db_module, keywords):
        """Creates a database.
        """
        # some DB implementaions take optional paramater `driver` to use a specific driver modue
        # but it should not be passed to connect
        keywords.pop('driver', None)

        self.db_module = db_module
        self.keywords = keywords

        self._ctx = threadeddict()
        # flag to enable/disable printing queries
        self.printing = config.get('debug_sql', config.get('debug', False))
        self.supports_multiple_insert = False
        
        try:
            import DBUtils
            # enable pooling if DBUtils module is available.
            self.has_pooling = True
        except ImportError:
            self.has_pooling = False
            
        # Pooling can be disabled by passing pooling=False in the keywords.
        self.has_pooling = self.keywords.pop('pooling', True) and self.has_pooling
            
    def _getctx(self): 
        if not self._ctx.get('db'):
            self._load_context(self._ctx)
        return self._ctx
    ctx = property(_getctx)
    
    def _load_context(self, ctx):
        ctx.dbq_count = 0
        ctx.transactions = [] # stack of transactions
        
        if self.has_pooling:
            ctx.db = self._connect_with_pooling(self.keywords)
        else:
            ctx.db = self._connect(self.keywords)
        ctx.db_execute = self._db_execute
        
        if not hasattr(ctx.db, 'commit'):
            ctx.db.commit = lambda: None

        if not hasattr(ctx.db, 'rollback'):
            ctx.db.rollback = lambda: None
            
        def commit(unload=True):
            # do db commit and release the connection if pooling is enabled.            
            ctx.db.commit()
            if unload and self.has_pooling:
                self._unload_context(self._ctx)
                
        def rollback():
            # do db rollback and release the connection if pooling is enabled.
            ctx.db.rollback()
            if self.has_pooling:
                self._unload_context(self._ctx)
                
        ctx.commit = commit
        ctx.rollback = rollback
            
    def _unload_context(self, ctx):
        del ctx.db
            
    def _connect(self, keywords):
        return self.db_module.connect(**keywords)
        
    def _connect_with_pooling(self, keywords):
        def get_pooled_db():
            from DBUtils import PooledDB

            # In DBUtils 0.9.3, `dbapi` argument is renamed as `creator`
            # see Bug#122112
            
            if PooledDB.__version__.split('.') < '0.9.3'.split('.'):
                return PooledDB.PooledDB(dbapi=self.db_module, **keywords)
            else:
                return PooledDB.PooledDB(creator=self.db_module, **keywords)
        
        if getattr(self, '_pooleddb', None) is None:
            self._pooleddb = get_pooled_db()
        
        return self._pooleddb.connection()
        
    def _db_cursor(self):
        return self.ctx.db.cursor()

    def _param_marker(self):
        """Returns parameter marker based on paramstyle attribute if this database."""
        style = getattr(self, 'paramstyle', 'pyformat')

        if style == 'qmark':
            return '?'
        elif style == 'numeric':
            return ':1'
        elif style in ['format', 'pyformat']:
            return '%s'
        raise UnknownParamstyle, style

    def _db_execute(self, cur, sql_query): 
        """executes an sql query"""
        self.ctx.dbq_count += 1
        
        try:
            a = time.time()
            query, params = self._process_query(sql_query)
            out = cur.execute(query, params)
            b = time.time()
        except:
            if self.printing:
                print >> debug, 'ERR:', str(sql_query)
            if self.ctx.transactions:
                self.ctx.transactions[-1].rollback()
            else:
                self.ctx.rollback()
            raise

        if self.printing:
            print >> debug, '%s (%s): %s' % (round(b-a, 2), self.ctx.dbq_count, str(sql_query))
        return out

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        paramstyle = getattr(self, 'paramstyle', 'pyformat')
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, params
    
    def _where(self, where, vars): 
        if isinstance(where, (int, long)):
            where = "id = " + sqlparam(where)
        #@@@ for backward-compatibility
        elif isinstance(where, (list, tuple)) and len(where) == 2:
            where = SQLQuery(where[0], where[1])
        elif isinstance(where, SQLQuery):
            pass
        else:
            where = reparam(where, vars)        
        return where
    
    def query(self, sql_query, vars=None, processed=False, _test=False): 
        """
        Execute SQL query `sql_query` using dictionary `vars` to interpolate it.
        If `processed=True`, `vars` is a `reparam`-style list to use 
        instead of interpolating.
        
            >>> db = DB(None, {})
            >>> db.query("SELECT * FROM foo", _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.query("SELECT * FROM foo WHERE x = $x", vars=dict(x='f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
            >>> db.query("SELECT * FROM foo WHERE x = " + sqlquote('f'), _test=True)
            <sql: "SELECT * FROM foo WHERE x = 'f'">
        """
        if vars is None: vars = {}
        
        if not processed and not isinstance(sql_query, SQLQuery):
            sql_query = reparam(sql_query, vars)
        
        if _test: return sql_query
        
        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, sql_query)
        
        if db_cursor.description:
            names = [x[0] for x in db_cursor.description]
            def iterwrapper():
                row = db_cursor.fetchone()
                while row:
                    yield storage(dict(zip(names, row)))
                    row = db_cursor.fetchone()
            out = iterbetter(iterwrapper())
            out.__len__ = lambda: int(db_cursor.rowcount)
            out.list = lambda: [storage(dict(zip(names, x))) \
                               for x in db_cursor.fetchall()]
        else:
            out = db_cursor.rowcount
        
        if not self.ctx.transactions: 
            self.ctx.commit()
        return out
    
    def select(self, tables, vars=None, what='*', where=None, order=None, group=None, 
               limit=None, offset=None, _test=False): 
        """
        Selects `what` from `tables` with clauses `where`, `order`, 
        `group`, `limit`, and `offset`. Uses vars to interpolate. 
        Otherwise, each clause can be a SQLQuery.
        
            >>> db = DB(None, {})
            >>> db.select('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
            >>> db.select(['foo', 'bar'], where="foo.bar_id = bar.id", limit=5, _test=True)
            <sql: 'SELECT * FROM foo, bar WHERE foo.bar_id = bar.id LIMIT 5'>
        """
        if vars is None: vars = {}
        sql_clauses = self.sql_clauses(what, tables, where, group, order, limit, offset)
        clauses = [self.gen_clause(sql, val, vars) for sql, val in sql_clauses if val is not None]
        qout = SQLQuery.join(clauses)
        if _test: return qout
        return self.query(qout, processed=True)
    
    def where(self, table, what='*', order=None, group=None, limit=None, 
              offset=None, _test=False, **kwargs):
        """
        Selects from `table` where keys are equal to values in `kwargs`.
        
            >>> db = DB(None, {})
            >>> db.where('foo', bar_id=3, _test=True)
            <sql: 'SELECT * FROM foo WHERE bar_id = 3'>
            >>> db.where('foo', source=2, crust='dewey', _test=True)
            <sql: "SELECT * FROM foo WHERE source = 2 AND crust = 'dewey'">
            >>> db.where('foo', _test=True)
            <sql: 'SELECT * FROM foo'>
        """
        where_clauses = []
        for k, v in kwargs.iteritems():
            where_clauses.append(k + ' = ' + sqlquote(v))
            
        if where_clauses:
            where = SQLQuery.join(where_clauses, " AND ")
        else:
            where = None
            
        return self.select(table, what=what, order=order, 
               group=group, limit=limit, offset=offset, _test=_test, 
               where=where)
    
    def sql_clauses(self, what, tables, where, group, order, limit, offset): 
        return (
            ('SELECT', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order),
            ('LIMIT', limit),
            ('OFFSET', offset))
    
    def gen_clause(self, sql, val, vars): 
        if isinstance(val, (int, long)):
            if sql == 'WHERE':
                nout = 'id = ' + sqlquote(val)
            else:
                nout = SQLQuery(val)
        #@@@
        elif isinstance(val, (list, tuple)) and len(val) == 2:
            nout = SQLQuery(val[0], val[1]) # backwards-compatibility
        elif isinstance(val, SQLQuery):
            nout = val
        else:
            nout = reparam(val, vars)

        def xjoin(a, b):
            if a and b: return a + ' ' + b
            else: return a or b

        return xjoin(sql, nout)

    def insert(self, tablename, seqname=None, _test=False, **values): 
        """
        Inserts `values` into `tablename`. Returns current sequence ID.
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> q = db.insert('foo', name='bob', age=2, created=SQLLiteral('NOW()'), _test=True)
            >>> q
            <sql: "INSERT INTO foo (age, name, created) VALUES (2, 'bob', NOW())">
            >>> q.query()
            'INSERT INTO foo (age, name, created) VALUES (%s, %s, NOW())'
            >>> q.values()
            [2, 'bob']
        """
        def q(x): return "(" + x + ")"
        
        if values:
            _keys = SQLQuery.join(values.keys(), ', ')
            _values = SQLQuery.join([sqlparam(v) for v in values.values()], ', ')
            sql_query = "INSERT INTO %s " % tablename + q(_keys) + ' VALUES ' + q(_values)
        else:
            sql_query = SQLQuery(self._get_insert_default_values_query(tablename))

        if _test: return sql_query
        
        db_cursor = self._db_cursor()
        if seqname is not False: 
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find 
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try: 
            out = db_cursor.fetchone()[0]
        except Exception: 
            out = None
        
        if not self.ctx.transactions: 
            self.ctx.commit()
        return out
        
    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s DEFAULT VALUES" % table

    def multiple_insert(self, tablename, values, seqname=None, _test=False):
        """
        Inserts multiple rows into `tablename`. The `values` must be a list of dictioanries, 
        one for each row to be inserted, each with the same set of keys.
        Returns the list of ids of the inserted rows.        
        Set `seqname` to the ID if it's not the default, or to `False`
        if there isn't one.
        
            >>> db = DB(None, {})
            >>> db.supports_multiple_insert = True
            >>> values = [{"name": "foo", "email": "foo@example.com"}, {"name": "bar", "email": "bar@example.com"}]
            >>> db.multiple_insert('person', values=values, _test=True)
            <sql: "INSERT INTO person (name, email) VALUES ('foo', 'foo@example.com'), ('bar', 'bar@example.com')">
        """        
        if not values:
            return []
            
        if not self.supports_multiple_insert:
            out = [self.insert(tablename, seqname=seqname, _test=_test, **v) for v in values]
            if seqname is False:
                return None
            else:
                return out
                
        keys = values[0].keys()
        #@@ make sure all keys are valid

        # make sure all rows have same keys.
        for v in values:
            if v.keys() != keys:
                raise ValueError, 'Bad data'

        sql_query = SQLQuery('INSERT INTO %s (%s) VALUES ' % (tablename, ', '.join(keys)))

        for i, row in enumerate(values):
            if i != 0:
                sql_query.append(", ")
            SQLQuery.join([SQLParam(row[k]) for k in keys], sep=", ", target=sql_query, prefix="(", suffix=")")
        
        if _test: return sql_query

        db_cursor = self._db_cursor()
        if seqname is not False: 
            sql_query = self._process_insert_query(sql_query, tablename, seqname)

        if isinstance(sql_query, tuple):
            # for some databases, a separate query has to be made to find 
            # the id of the inserted row.
            q1, q2 = sql_query
            self._db_execute(db_cursor, q1)
            self._db_execute(db_cursor, q2)
        else:
            self._db_execute(db_cursor, sql_query)

        try: 
            out = db_cursor.fetchone()[0]
            out = range(out-len(values)+1, out+1)        
        except Exception: 
            out = None

        if not self.ctx.transactions: 
            self.ctx.commit()
        return out

    
    def update(self, tables, where, vars=None, _test=False, **values): 
        """
        Update `tables` with clause `where` (interpolated using `vars`)
        and setting `values`.

            >>> db = DB(None, {})
            >>> name = 'Joseph'
            >>> q = db.update('foo', where='name = $name', name='bob', age=2,
            ...     created=SQLLiteral('NOW()'), vars=locals(), _test=True)
            >>> q
            <sql: "UPDATE foo SET age = 2, name = 'bob', created = NOW() WHERE name = 'Joseph'">
            >>> q.query()
            'UPDATE foo SET age = %s, name = %s, created = NOW() WHERE name = %s'
            >>> q.values()
            [2, 'bob', 'Joseph']
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        query = (
          "UPDATE " + sqllist(tables) + 
          " SET " + sqlwhere(values, ', ') + 
          " WHERE " + where)

        if _test: return query
        
        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, query)
        if not self.ctx.transactions: 
            self.ctx.commit()
        return db_cursor.rowcount
    
    def delete(self, table, where, using=None, vars=None, _test=False): 
        """
        Deletes from `table` with clauses `where` and `using`.

            >>> db = DB(None, {})
            >>> name = 'Joe'
            >>> db.delete('foo', where='name = $name', vars=locals(), _test=True)
            <sql: "DELETE FROM foo WHERE name = 'Joe'">
        """
        if vars is None: vars = {}
        where = self._where(where, vars)

        q = 'DELETE FROM ' + table
        if using: q += ' USING ' + sqllist(using)
        if where: q += ' WHERE ' + where

        if _test: return q

        db_cursor = self._db_cursor()
        self._db_execute(db_cursor, q)
        if not self.ctx.transactions: 
            self.ctx.commit()
        return db_cursor.rowcount

    def _process_insert_query(self, query, tablename, seqname):
        return query

    def transaction(self): 
        """Start a transaction."""
        return Transaction(self.ctx)
    
class PostgresDB(DB): 
    """Postgres driver."""
    def __init__(self, **keywords):
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('pw')
            
        db_module = import_driver(["psycopg2", "psycopg", "pgdb"], preferred=keywords.pop('driver', None))
        if db_module.__name__ == "psycopg2":
            import psycopg2.extensions
            psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

        # if db is not provided postgres driver will take it from PGDATABASE environment variable
        if 'db' in keywords:
            keywords['database'] = keywords.pop('db')
        
        self.dbname = "postgres"
        self.paramstyle = db_module.paramstyle
        DB.__init__(self, db_module, keywords)
        self.supports_multiple_insert = True
        self._sequences = None
        
    def _process_insert_query(self, query, tablename, seqname):
        if seqname is None:
            # when seqname is not provided guess the seqname and make sure it exists
            seqname = tablename + "_id_seq"
            if seqname not in self._get_all_sequences():
                seqname = None
        
        if seqname:
            query += "; SELECT currval('%s')" % seqname
            
        return query
    
    def _get_all_sequences(self):
        """Query postgres to find names of all sequences used in this database."""
        if self._sequences is None:
            q = "SELECT c.relname FROM pg_class c WHERE c.relkind = 'S'"
            self._sequences = set([c.relname for c in self.query(q)])
        return self._sequences

    def _connect(self, keywords):
        conn = DB._connect(self, keywords)
        try:
            conn.set_client_encoding('UTF8')
        except AttributeError:
            # fallback for pgdb driver
            conn.cursor().execute("set client_encoding to 'UTF-8'")
        return conn
        
    def _connect_with_pooling(self, keywords):
        conn = DB._connect_with_pooling(self, keywords)
        conn._con._con.set_client_encoding('UTF8')
        return conn

class MySQLDB(DB): 
    def __init__(self, **keywords):
        import MySQLdb as db
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']

        if 'charset' not in keywords:
            keywords['charset'] = 'utf8'
        elif keywords['charset'] is None:
            del keywords['charset']

        self.paramstyle = db.paramstyle = 'pyformat' # it's both, like psycopg
        self.dbname = "mysql"
        DB.__init__(self, db, keywords)
        self.supports_multiple_insert = True
        
    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_id();')
        
    def _get_insert_default_values_query(self, table):
        return "INSERT INTO %s () VALUES()" % table

def import_driver(drivers, preferred=None):
    """Import the first available driver or preferred driver.
    """
    if preferred:
        drivers = [preferred]

    for d in drivers:
        try:
            return __import__(d, None, None, ['x'])
        except ImportError:
            pass
    raise ImportError("Unable to import " + " or ".join(drivers))

class SqliteDB(DB): 
    def __init__(self, **keywords):
        db = import_driver(["sqlite3", "pysqlite2.dbapi2", "sqlite"], preferred=keywords.pop('driver', None))

        if db.__name__ in ["sqlite3", "pysqlite2.dbapi2"]:
            db.paramstyle = 'qmark'
            
        # sqlite driver doesn't create datatime objects for timestamp columns unless `detect_types` option is passed.
        # It seems to be supported in sqlite3 and pysqlite2 drivers, not surte about sqlite.
        keywords.setdefault('detect_types', db.PARSE_DECLTYPES)

        self.paramstyle = db.paramstyle
        keywords['database'] = keywords.pop('db')
        self.dbname = "sqlite"        
        DB.__init__(self, db, keywords)

    def _process_insert_query(self, query, tablename, seqname):
        return query, SQLQuery('SELECT last_insert_rowid();')
    
    def query(self, *a, **kw):
        out = DB.query(self, *a, **kw)
        if isinstance(out, iterbetter):
            del out.__len__
        return out

class FirebirdDB(DB):
    """Firebird Database.
    """
    def __init__(self, **keywords):
        try:
            import kinterbasdb as db
        except Exception:
            db = None
            pass
        if 'pw' in keywords:
            keywords['passwd'] = keywords['pw']
            del keywords['pw']
        keywords['database'] = keywords['db']
        del keywords['db']
        DB.__init__(self, db, keywords)
        
    def delete(self, table, where=None, using=None, vars=None, _test=False):
        # firebird doesn't support using clause
        using=None
        return DB.delete(self, table, where, using, vars, _test)

    def sql_clauses(self, what, tables, where, group, order, limit, offset):
        return (
            ('SELECT', ''),
            ('FIRST', limit),
            ('SKIP', offset),
            ('', what),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order)
        )

class MSSQLDB(DB):
    def __init__(self, **keywords):
        import pymssql as db    
        if 'pw' in keywords:
            keywords['password'] = keywords.pop('pw')
        keywords['database'] = keywords.pop('db')
        self.dbname = "mssql"
        DB.__init__(self, db, keywords)

    def _process_query(self, sql_query):
        """Takes the SQLQuery object and returns query string and parameters.
        """
        # MSSQLDB expects params to be a tuple. 
        # Overwriting the default implementation to convert params to tuple.
        paramstyle = getattr(self, 'paramstyle', 'pyformat')
        query = sql_query.query(paramstyle)
        params = sql_query.values()
        return query, tuple(params)

    def sql_clauses(self, what, tables, where, group, order, limit, offset): 
        return (
            ('SELECT', what),
            ('TOP', limit),
            ('FROM', sqllist(tables)),
            ('WHERE', where),
            ('GROUP BY', group),
            ('ORDER BY', order),
            ('OFFSET', offset))
            
    def _test(self):
        """Test LIMIT.

            Fake presence of pymssql module for running tests.
            >>> import sys
            >>> sys.modules['pymssql'] = sys.modules['sys']
            
            MSSQL has TOP clause instead of LIMIT clause.
            >>> db = MSSQLDB(db='test', user='joe', pw='secret')
            >>> db.select('foo', limit=4, _test=True)
            <sql: 'SELECT * TOP 4 FROM foo'>
        """
        pass

class OracleDB(DB): 
    def __init__(self, **keywords): 
        import cx_Oracle as db 
        if 'pw' in keywords: 
            keywords['password'] = keywords.pop('pw') 

        #@@ TODO: use db.makedsn if host, port is specified 
        keywords['dsn'] = keywords.pop('db') 
        self.dbname = 'oracle' 
        db.paramstyle = 'numeric' 
        self.paramstyle = db.paramstyle

        # oracle doesn't support pooling 
        keywords.pop('pooling', None) 
        DB.__init__(self, db, keywords) 

    def _process_insert_query(self, query, tablename, seqname): 
        if seqname is None: 
            # It is not possible to get seq name from table name in Oracle
            return query
        else:
            return query + "; SELECT %s.currval FROM dual" % seqname 

_databases = {}
def database(dburl=None, **params):
    """Creates appropriate database using params.
    
    Pooling will be enabled if DBUtils module is available. 
    Pooling can be disabled by passing pooling=False in params.
    """
    dbn = params.pop('dbn')
    if dbn in _databases:
        return _databases[dbn](**params)
    else:
        raise UnknownDB, dbn

def register_database(name, clazz):
    """
    Register a database.

        >>> class LegacyDB(DB): 
        ...     def __init__(self, **params): 
        ...        pass 
        ...
        >>> register_database('legacy', LegacyDB)
        >>> db = database(dbn='legacy', db='test', user='joe', passwd='secret') 
    """
    _databases[name] = clazz

register_database('mysql', MySQLDB)
register_database('postgres', PostgresDB)
register_database('sqlite', SqliteDB)
register_database('firebird', FirebirdDB)
register_database('mssql', MSSQLDB)
register_database('oracle', OracleDB)

def _interpolate(format): 
    """
    Takes a format string and returns a list of 2-tuples of the form
    (boolean, string) where boolean says whether string should be evaled
    or not.

    from <http://lfw.org/python/Itpl.py> (public domain, Ka-Ping Yee)
    """
    from tokenize import tokenprog

    def matchorfail(text, pos):
        match = tokenprog.match(text, pos)
        if match is None:
            raise _ItplError(text, pos)
        return match, match.end()

    namechars = "abcdefghijklmnopqrstuvwxyz" \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_";
    chunks = []
    pos = 0

    while 1:
        dollar = format.find("$", pos)
        if dollar < 0: 
            break
        nextchar = format[dollar + 1]

        if nextchar == "{":
            chunks.append((0, format[pos:dollar]))
            pos, level = dollar + 2, 1
            while level:
                match, pos = matchorfail(format, pos)
                tstart, tend = match.regs[3]
                token = format[tstart:tend]
                if token == "{": 
                    level = level + 1
                elif token == "}":  
                    level = level - 1
            chunks.append((1, format[dollar + 2:pos - 1]))

        elif nextchar in namechars:
            chunks.append((0, format[pos:dollar]))
            match, pos = matchorfail(format, dollar + 1)
            while pos < len(format):
                if format[pos] == "." and \
                    pos + 1 < len(format) and format[pos + 1] in namechars:
                    match, pos = matchorfail(format, pos + 1)
                elif format[pos] in "([":
                    pos, level = pos + 1, 1
                    while level:
                        match, pos = matchorfail(format, pos)
                        tstart, tend = match.regs[3]
                        token = format[tstart:tend]
                        if token[0] in "([": 
                            level = level + 1
                        elif token[0] in ")]":  
                            level = level - 1
                else: 
                    break
            chunks.append((1, format[dollar + 1:pos]))
        else:
            chunks.append((0, format[pos:dollar + 1]))
            pos = dollar + 1 + (nextchar == "$")

    if pos < len(format): 
        chunks.append((0, format[pos:]))
    return chunks

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = debugerror
"""
pretty debug errors
(part of web.py)

portions adapted from Django <djangoproject.com> 
Copyright (c) 2005, the Lawrence Journal-World
Used under the modified BSD license:
http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5
"""

__all__ = ["debugerror", "djangoerror", "emailerrors"]

import sys, urlparse, pprint, traceback
from template import Template
from net import websafe
from utils import sendmail, safestr
import webapi as web

import os, os.path
whereami = os.path.join(os.getcwd(), __file__)
whereami = os.path.sep.join(whereami.split(os.path.sep)[:-1])
djangoerror_t = """\
$def with (exception_type, exception_value, frames)
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="robots" content="NONE,NOARCHIVE" />
  <title>$exception_type at $ctx.path</title>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { 
        border:1px solid #ccc; border-collapse: collapse; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { 
        padding:1px 6px 1px 3px; background:#fefefe; text-align:left; 
        font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { text-align:right; color:#666; padding-right:.5em; }
    table.vars { margin:5px 0 2px 40px; }
    table.vars td, table.req td { font-family:monospace; }
    table td.code { width:100%;}
    table td.code div { overflow:hidden; }
    table.source th { color:#666; }
    table.source td { 
        font-family:monospace; white-space:pre; border-bottom:1px solid #eee; }
    ul.traceback { list-style-type:none; }
    ul.traceback li.frame { margin-bottom:1em; }
    div.context { margin: 10px 0; }
    div.context ol { 
        padding-left:30px; margin:0 10px; list-style-position: inside; }
    div.context ol li { 
        font-family:monospace; white-space:pre; color:#666; cursor:pointer; }
    div.context ol.context-line li { color:black; background-color:#ccc; }
    div.context ol.context-line li span { float: right; }
    div.commands { margin-left: 40px; }
    div.commands a { color:black; text-decoration:none; }
    #summary { background: #ffc; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #template, #template-not-exist { background:#f6f6f6; }
    #template-not-exist ul { margin: 0 0 0 20px; }
    #traceback { background:#eee; }
    #requestinfo { background:#f6f6f6; padding-left:120px; }
    #summary table { border:none; background:transparent; }
    #requestinfo h2, #requestinfo h3 { position:relative; margin-left:-100px; }
    #requestinfo h3 { margin-bottom:-1em; }
    .error { background: #ffc; }
    .specific { color:#cc3300; font-weight:bold; }
  </style>
  <script type="text/javascript">
  //<!--
    function getElementsByClassName(oElm, strTagName, strClassName){
        // Written by Jonathan Snook, http://www.snook.ca/jon; 
        // Add-ons by Robert Nyman, http://www.robertnyman.com
        var arrElements = (strTagName == "*" && document.all)? document.all :
        oElm.getElementsByTagName(strTagName);
        var arrReturnElements = new Array();
        strClassName = strClassName.replace(/\-/g, "\\-");
        var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$$)");
        var oElement;
        for(var i=0; i<arrElements.length; i++){
            oElement = arrElements[i];
            if(oRegExp.test(oElement.className)){
                arrReturnElements.push(oElement);
            }
        }
        return (arrReturnElements)
    }
    function hideAll(elems) {
      for (var e = 0; e < elems.length; e++) {
        elems[e].style.display = 'none';
      }
    }
    window.onload = function() {
      hideAll(getElementsByClassName(document, 'table', 'vars'));
      hideAll(getElementsByClassName(document, 'ol', 'pre-context'));
      hideAll(getElementsByClassName(document, 'ol', 'post-context'));
    }
    function toggle() {
      for (var i = 0; i < arguments.length; i++) {
        var e = document.getElementById(arguments[i]);
        if (e) {
          e.style.display = e.style.display == 'none' ? 'block' : 'none';
        }
      }
      return false;
    }
    function varToggle(link, id) {
      toggle('v' + id);
      var s = link.getElementsByTagName('span')[0];
      var uarr = String.fromCharCode(0x25b6);
      var darr = String.fromCharCode(0x25bc);
      s.innerHTML = s.innerHTML == uarr ? darr : uarr;
      return false;
    }
    //-->
  </script>
</head>
<body>

$def dicttable (d, kls='req', id=None):
    $ items = d and d.items() or []
    $items.sort()
    $:dicttable_items(items, kls, id)
        
$def dicttable_items(items, kls='req', id=None):
    $if items:
        <table class="$kls"
        $if id: id="$id"
        ><thead><tr><th>Variable</th><th>Value</th></tr></thead>
        <tbody>
        $for k, v in items:
            <tr><td>$k</td><td class="code"><div>$prettify(v)</div></td></tr>
        </tbody>
        </table>
    $else:
        <p>No data.</p>

<div id="summary">
  <h1>$exception_type at $ctx.path</h1>
  <h2>$exception_value</h2>
  <table><tr>
    <th>Python</th>
    <td>$frames[0].filename in $frames[0].function, line $frames[0].lineno</td>
  </tr><tr>
    <th>Web</th>
    <td>$ctx.method $ctx.home$ctx.path</td>
  </tr></table>
</div>
<div id="traceback">
<h2>Traceback <span>(innermost first)</span></h2>
<ul class="traceback">
$for frame in frames:
    <li class="frame">
    <code>$frame.filename</code> in <code>$frame.function</code>
    $if frame.context_line is not None:
        <div class="context" id="c$frame.id">
        $if frame.pre_context:
            <ol start="$frame.pre_context_lineno" class="pre-context" id="pre$frame.id">
            $for line in frame.pre_context:
                <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
            </ol>
            <ol start="$frame.lineno" class="context-line"><li onclick="toggle('pre$frame.id', 'post$frame.id')">$frame.context_line <span>...</span></li></ol>
        $if frame.post_context:
            <ol start='${frame.lineno + 1}' class="post-context" id="post$frame.id">
            $for line in frame.post_context:
                <li onclick="toggle('pre$frame.id', 'post$frame.id')">$line</li>
            </ol>
      </div>
    
    $if frame.vars:
        <div class="commands">
        <a href='#' onclick="return varToggle(this, '$frame.id')"><span>&#x25b6;</span> Local vars</a>
        $# $inspect.formatargvalues(*inspect.getargvalues(frame['tb'].tb_frame))
        </div>
        $:dicttable(frame.vars, kls='vars', id=('v' + str(frame.id)))
      </li>
  </ul>
</div>

<div id="requestinfo">
$if ctx.output or ctx.headers:
    <h2>Response so far</h2>
    <h3>HEADERS</h3>
    $:dicttable_items(ctx.headers)

    <h3>BODY</h3>
    <p class="req" style="padding-bottom: 2em"><code>
    $ctx.output
    </code></p>
  
<h2>Request information</h2>

<h3>INPUT</h3>
$:dicttable(web.input(_unicode=False))

<h3 id="cookie-info">COOKIES</h3>
$:dicttable(web.cookies())

<h3 id="meta-info">META</h3>
$ newctx = [(k, v) for (k, v) in ctx.iteritems() if not k.startswith('_') and not isinstance(v, dict)]
$:dicttable(dict(newctx))

<h3 id="meta-info">ENVIRONMENT</h3>
$:dicttable(ctx.env)
</div>

<div id="explanation">
  <p>
    You're seeing this error because you have <code>web.config.debug</code>
    set to <code>True</code>. Set that to <code>False</code> if you don't want to see this.
  </p>
</div>

</body>
</html>
"""

djangoerror_r = None

def djangoerror():
    def _get_lines_from_file(filename, lineno, context_lines):
        """
        Returns context_lines before and after lineno from file.
        Returns (pre_context_lineno, pre_context, context_line, post_context).
        """
        try:
            source = open(filename).readlines()
            lower_bound = max(0, lineno - context_lines)
            upper_bound = lineno + context_lines

            pre_context = \
                [line.strip('\n') for line in source[lower_bound:lineno]]
            context_line = source[lineno].strip('\n')
            post_context = \
                [line.strip('\n') for line in source[lineno + 1:upper_bound]]

            return lower_bound, pre_context, context_line, post_context
        except (OSError, IOError, IndexError):
            return None, [], None, []    
    
    exception_type, exception_value, tback = sys.exc_info()
    frames = []
    while tback is not None:
        filename = tback.tb_frame.f_code.co_filename
        function = tback.tb_frame.f_code.co_name
        lineno = tback.tb_lineno - 1

        # hack to get correct line number for templates
        lineno += tback.tb_frame.f_locals.get("__lineoffset__", 0)
        
        pre_context_lineno, pre_context, context_line, post_context = \
            _get_lines_from_file(filename, lineno, 7)

        if '__hidetraceback__' not in tback.tb_frame.f_locals:
            frames.append(web.storage({
                'tback': tback,
                'filename': filename,
                'function': function,
                'lineno': lineno,
                'vars': tback.tb_frame.f_locals,
                'id': id(tback),
                'pre_context': pre_context,
                'context_line': context_line,
                'post_context': post_context,
                'pre_context_lineno': pre_context_lineno,
            }))
        tback = tback.tb_next
    frames.reverse()
    urljoin = urlparse.urljoin
    def prettify(x):
        try: 
            out = pprint.pformat(x)
        except Exception, e: 
            out = '[could not display: <' + e.__class__.__name__ + \
                  ': '+str(e)+'>]'
        return out
        
    global djangoerror_r
    if djangoerror_r is None:
        djangoerror_r = Template(djangoerror_t, filename=__file__, filter=websafe)
        
    t = djangoerror_r
    globals = {'ctx': web.ctx, 'web':web, 'dict':dict, 'str':str, 'prettify': prettify}
    t.t.func_globals.update(globals)
    return t(exception_type, exception_value, frames)

def debugerror():
    """
    A replacement for `internalerror` that presents a nice page with lots
    of debug information for the programmer.

    (Based on the beautiful 500 page from [Django](http://djangoproject.com/), 
    designed by [Wilson Miner](http://wilsonminer.com/).)
    """
    return web._InternalError(djangoerror())

def emailerrors(to_address, olderror, from_address=None):
    """
    Wraps the old `internalerror` handler (pass as `olderror`) to 
    additionally email all errors to `to_address`, to aid in
    debugging production websites.
    
    Emails contain a normal text traceback as well as an
    attachment containing the nice `debugerror` page.
    """
    from_address = from_address or to_address

    def emailerrors_internal():
        error = olderror()
        tb = sys.exc_info()
        error_name = tb[0]
        error_value = tb[1]
        tb_txt = ''.join(traceback.format_exception(*tb))
        path = web.ctx.path
        request = web.ctx.method + ' ' + web.ctx.home + web.ctx.fullpath
        
        message = "\n%s\n\n%s\n\n" % (request, tb_txt)
        
        sendmail(
            "your buggy site <%s>" % from_address,
            "the bugfixer <%s>" % to_address,
            "bug: %(error_name)s: %(error_value)s (%(path)s)" % locals(),
            message,
            attachments=[
                dict(filename="bug.html", content=safestr(djangoerror()))
            ],
        )
        return error
    
    return emailerrors_internal

if __name__ == "__main__":
    urls = (
        '/', 'index'
    )
    from application import application
    app = application(urls, globals())
    app.internalerror = debugerror
    
    class index:
        def GET(self):
            thisdoesnotexist

    app.run()

########NEW FILE########
__FILENAME__ = form
"""
HTML forms
(part of web.py)
"""

import copy, re
import webapi as web
import utils, net

def attrget(obj, attr, value=None):
    try:
        if hasattr(obj, 'has_key') and obj.has_key(attr): 
            return obj[attr]
    except TypeError:
        # Handle the case where has_key takes different number of arguments.
        # This is the case with Model objects on appengine. See #134
        pass
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return value

class Form(object):
    r"""
    HTML form.
    
        >>> f = Form(Textbox("x"))
        >>> f.render()
        '<table>\n    <tr><th><label for="x">x</label></th><td><input type="text" id="x" name="x"/></td></tr>\n</table>'
    """
    def __init__(self, *inputs, **kw):
        self.inputs = inputs
        self.valid = True
        self.note = None
        self.validators = kw.pop('validators', [])

    def __call__(self, x=None):
        o = copy.deepcopy(self)
        if x: o.validates(x)
        return o
    
    def render(self):
        out = ''
        out += self.rendernote(self.note)
        out += '<table>\n'
        
        for i in self.inputs:
            html = utils.safeunicode(i.pre) + i.render() + self.rendernote(i.note) + utils.safeunicode(i.post)
            if i.is_hidden():
                out += '    <tr style="display: none;"><th></th><td>%s</td></tr>\n' % (html)
            else:
                out += '    <tr><th><label for="%s">%s</label></th><td>%s</td></tr>\n' % (i.id, net.websafe(i.description), html)
        out += "</table>"
        return out
        
    def render_css(self): 
        out = [] 
        out.append(self.rendernote(self.note)) 
        for i in self.inputs:
            if not i.is_hidden():
                out.append('<label for="%s">%s</label>' % (i.id, net.websafe(i.description))) 
            out.append(i.pre)
            out.append(i.render()) 
            out.append(self.rendernote(i.note))
            out.append(i.post) 
            out.append('\n')
        return ''.join(out) 
        
    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
    
    def validates(self, source=None, _validate=True, **kw):
        source = source or kw or web.input()
        out = True
        for i in self.inputs:
            v = attrget(source, i.name)
            if _validate:
                out = i.validate(v) and out
            else:
                i.set_value(v)
        if _validate:
            out = out and self._validate(source)
            self.valid = out
        return out

    def _validate(self, value):
        self.value = value
        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def fill(self, source=None, **kw):
        return self.validates(source, _validate=False, **kw)
    
    def __getitem__(self, i):
        for x in self.inputs:
            if x.name == i: return x
        raise KeyError, i

    def __getattr__(self, name):
        # don't interfere with deepcopy
        inputs = self.__dict__.get('inputs') or []
        for x in inputs:
            if x.name == name: return x
        raise AttributeError, name
    
    def get(self, i, default=None):
        try:
            return self[i]
        except KeyError:
            return default
            
    def _get_d(self): #@@ should really be form.attr, no?
        return utils.storage([(i.name, i.get_value()) for i in self.inputs])
    d = property(_get_d)

class Input(object):
    def __init__(self, name, *validators, **attrs):
        self.name = name
        self.validators = validators
        self.attrs = attrs = AttributeList(attrs)
        
        self.description = attrs.pop('description', name)
        self.value = attrs.pop('value', None)
        self.pre = attrs.pop('pre', "")
        self.post = attrs.pop('post', "")
        self.note = None
        
        self.id = attrs.setdefault('id', self.get_default_id())
        
        if 'class_' in attrs:
            attrs['class'] = attrs['class_']
            del attrs['class_']
        
    def is_hidden(self):
        return False
        
    def get_type(self):
        raise NotImplementedError
        
    def get_default_id(self):
        return self.name

    def validate(self, value):
        self.set_value(value)

        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = self.get_type()
        if self.value is not None:
            attrs['value'] = self.value
        attrs['name'] = self.name
        return '<input %s/>' % attrs

    def rendernote(self, note):
        if note: return '<strong class="wrong">%s</strong>' % net.websafe(note)
        else: return ""
        
    def addatts(self):
        # add leading space for backward-compatibility
        return " " + str(self.attrs)

class AttributeList(dict):
    """List of atributes of input.
    
    >>> a = AttributeList(type='text', name='x', value=20)
    >>> a
    <attrs: 'type="text" name="x" value="20"'>
    """
    def copy(self):
        return AttributeList(self)
        
    def __str__(self):
        return " ".join(['%s="%s"' % (k, net.websafe(v)) for k, v in self.items()])
        
    def __repr__(self):
        return '<attrs: %s>' % repr(str(self))

class Textbox(Input):
    """Textbox input.
    
        >>> Textbox(name='foo', value='bar').render()
        '<input type="text" id="foo" value="bar" name="foo"/>'
        >>> Textbox(name='foo', value=0).render()
        '<input type="text" id="foo" value="0" name="foo"/>'
    """        
    def get_type(self):
        return 'text'

class Password(Input):
    """Password input.

        >>> Password(name='password', value='secret').render()
        '<input type="password" id="password" value="secret" name="password"/>'
    """
    
    def get_type(self):
        return 'password'

class Textarea(Input):
    """Textarea input.
    
        >>> Textarea(name='foo', value='bar').render()
        '<textarea id="foo" name="foo">bar</textarea>'
    """
    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        value = net.websafe(self.value or '')
        return '<textarea %s>%s</textarea>' % (attrs, value)

class Dropdown(Input):
    r"""Dropdown/select input.
    
        >>> Dropdown(name='foo', args=['a', 'b', 'c'], value='b').render()
        '<select id="foo" name="foo">\n  <option value="a">a</option>\n  <option selected="selected" value="b">b</option>\n  <option value="c">c</option>\n</select>\n'
        >>> Dropdown(name='foo', args=[('a', 'aa'), ('b', 'bb'), ('c', 'cc')], value='b').render()
        '<select id="foo" name="foo">\n  <option value="a">aa</option>\n  <option selected="selected" value="b">bb</option>\n  <option value="c">cc</option>\n</select>\n'
    """
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Dropdown, self).__init__(name, *validators, **attrs)

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        
        x = '<select %s>\n' % attrs
        
        for arg in self.args:
            if isinstance(arg, (tuple, list)):
                value, desc= arg
            else:
                value, desc = arg, arg 

            if self.value == value or (isinstance(self.value, list) and value in self.value):
                select_p = ' selected="selected"'
            else: select_p = ''
            x += '  <option%s value="%s">%s</option>\n' % (select_p, net.websafe(value), net.websafe(desc))
            
        x += '</select>\n'
        return x

class Radio(Input):
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Radio, self).__init__(name, *validators, **attrs)

    def render(self):
        x = '<span>'
        for arg in self.args:
            if isinstance(arg, (tuple, list)):
                value, desc= arg
            else:
                value, desc = arg, arg 
            attrs = self.attrs.copy()
            attrs['name'] = self.name
            attrs['type'] = 'radio'
            attrs['value'] = value
            if self.value == value:
                attrs['checked'] = 'checked'
            x += '<input %s/> %s' % (attrs, net.websafe(desc))
        x += '</span>'
        return x

class Checkbox(Input):
    """Checkbox input.

    >>> Checkbox('foo', value='bar', checked=True).render()
    '<input checked="checked" type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    >>> Checkbox('foo', value='bar').render()
    '<input type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    >>> c = Checkbox('foo', value='bar')
    >>> c.validate('on')
    True
    >>> c.render()
    '<input checked="checked" type="checkbox" id="foo_bar" value="bar" name="foo"/>'
    """
    def __init__(self, name, *validators, **attrs):
        self.checked = attrs.pop('checked', False)
        Input.__init__(self, name, *validators, **attrs)
        
    def get_default_id(self):
        value = utils.safestr(self.value or "")
        return self.name + '_' + value.replace(' ', '_')

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = 'checkbox'
        attrs['name'] = self.name
        attrs['value'] = self.value

        if self.checked:
            attrs['checked'] = 'checked'            
        return '<input %s/>' % attrs

    def set_value(self, value):
        self.checked = bool(value)

    def get_value(self):
        return self.checked

class Button(Input):
    """HTML Button.
    
    >>> Button("save").render()
    '<button id="save" name="save">save</button>'
    >>> Button("action", value="save", html="<b>Save Changes</b>").render()
    '<button id="action" value="save" name="action"><b>Save Changes</b></button>'
    """
    def __init__(self, name, *validators, **attrs):
        super(Button, self).__init__(name, *validators, **attrs)
        self.description = ""

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        if self.value is not None:
            attrs['value'] = self.value
        html = attrs.pop('html', None) or net.websafe(self.name)
        return '<button %s>%s</button>' % (attrs, html)

class Hidden(Input):
    """Hidden Input.
    
        >>> Hidden(name='foo', value='bar').render()
        '<input type="hidden" id="foo" value="bar" name="foo"/>'
    """
    def is_hidden(self):
        return True
        
    def get_type(self):
        return 'hidden'

class File(Input):
    """File input.
    
        >>> File(name='f').render()
        '<input type="file" id="f" name="f"/>'
    """
    def get_type(self):
        return 'file'
    
class Validator:
    def __deepcopy__(self, memo): return copy.copy(self)
    def __init__(self, msg, test, jstest=None): utils.autoassign(self, locals())
    def valid(self, value): 
        try: return self.test(value)
        except: return False

notnull = Validator("Required", bool)

class regexp(Validator):
    def __init__(self, rexp, msg):
        self.rexp = re.compile(rexp)
        self.msg = msg
    
    def valid(self, value):
        return bool(self.rexp.match(value))

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = http
"""
HTTP Utilities
(from web.py)
"""

__all__ = [
  "expires", "lastmodified", 
  "prefixurl", "modified", 
  "changequery", "url",
  "profiler",
]

import sys, os, threading, urllib, urlparse
try: import datetime
except ImportError: pass
import net, utils, webapi as web

def prefixurl(base=''):
    """
    Sorry, this function is really difficult to explain.
    Maybe some other time.
    """
    url = web.ctx.path.lstrip('/')
    for i in xrange(url.count('/')): 
        base += '../'
    if not base: 
        base = './'
    return base

def expires(delta):
    """
    Outputs an `Expires` header for `delta` from now. 
    `delta` is a `timedelta` object or a number of seconds.
    """
    if isinstance(delta, (int, long)):
        delta = datetime.timedelta(seconds=delta)
    date_obj = datetime.datetime.utcnow() + delta
    web.header('Expires', net.httpdate(date_obj))

def lastmodified(date_obj):
    """Outputs a `Last-Modified` header for `datetime`."""
    web.header('Last-Modified', net.httpdate(date_obj))

def modified(date=None, etag=None):
    """
    Checks to see if the page has been modified since the version in the
    requester's cache.
    
    When you publish pages, you can include `Last-Modified` and `ETag`
    with the date the page was last modified and an opaque token for
    the particular version, respectively. When readers reload the page, 
    the browser sends along the modification date and etag value for
    the version it has in its cache. If the page hasn't changed, 
    the server can just return `304 Not Modified` and not have to 
    send the whole page again.
    
    This function takes the last-modified date `date` and the ETag `etag`
    and checks the headers to see if they match. If they do, it returns 
    `True`, or otherwise it raises NotModified error. It also sets 
    `Last-Modified` and `ETag` output headers.
    """
    try:
        from __builtin__ import set
    except ImportError:
        # for python 2.3
        from sets import Set as set

    n = set([x.strip('" ') for x in web.ctx.env.get('HTTP_IF_NONE_MATCH', '').split(',')])
    m = net.parsehttpdate(web.ctx.env.get('HTTP_IF_MODIFIED_SINCE', '').split(';')[0])
    validate = False
    if etag:
        if '*' in n or etag in n:
            validate = True
    if date and m:
        # we subtract a second because 
        # HTTP dates don't have sub-second precision
        if date-datetime.timedelta(seconds=1) <= m:
            validate = True
    
    if date: lastmodified(date)
    if etag: web.header('ETag', '"' + etag + '"')
    if validate:
        raise web.notmodified()
    else:
        return True

def urlencode(query, doseq=0):
    """
    Same as urllib.urlencode, but supports unicode strings.
    
        >>> urlencode({'text':'foo bar'})
        'text=foo+bar'
        >>> urlencode({'x': [1, 2]}, doseq=True)
        'x=1&x=2'
    """
    def convert(value, doseq=False):
        if doseq and isinstance(value, list):
            return [convert(v) for v in value]
        else:
            return utils.safestr(value)
        
    query = dict([(k, convert(v, doseq)) for k, v in query.items()])
    return urllib.urlencode(query, doseq=doseq)

def changequery(query=None, **kw):
    """
    Imagine you're at `/foo?a=1&b=2`. Then `changequery(a=3)` will return
    `/foo?a=3&b=2` -- the same URL but with the arguments you requested
    changed.
    """
    if query is None:
        query = web.rawinput(method='get')
    for k, v in kw.iteritems():
        if v is None:
            query.pop(k, None)
        else:
            query[k] = v
    out = web.ctx.path
    if query:
        out += '?' + urlencode(query, doseq=True)
    return out

def url(path=None, doseq=False, **kw):
    """
    Makes url by concatenating web.ctx.homepath and path and the 
    query string created using the arguments.
    """
    if path is None:
        path = web.ctx.path
    if path.startswith("/"):
        out = web.ctx.homepath + path
    else:
        out = path

    if kw:
        out += '?' + urlencode(kw, doseq=doseq)
    
    return out

def profiler(app):
    """Outputs basic profiling information at the bottom of each response."""
    from utils import profile
    def profile_internal(e, o):
        out, result = profile(app)(e, o)
        return list(out) + ['<pre>' + net.websafe(result) + '</pre>']
    return profile_internal

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = httpserver
__all__ = ["runsimple"]

import sys, os
from SimpleHTTPServer import SimpleHTTPRequestHandler
import urllib
import posixpath

import webapi as web
import net
import utils

def runbasic(func, server_address=("0.0.0.0", 8080)):
    """
    Runs a simple HTTP server hosting WSGI app `func`. The directory `static/` 
    is hosted statically.

    Based on [WsgiServer][ws] from [Colin Stewart][cs].
    
  [ws]: http://www.owlfish.com/software/wsgiutils/documentation/wsgi-server-api.html
  [cs]: http://www.owlfish.com/
    """
    # Copyright (c) 2004 Colin Stewart (http://www.owlfish.com/)
    # Modified somewhat for simplicity
    # Used under the modified BSD license:
    # http://www.xfree86.org/3.3.6/COPYRIGHT2.html#5

    import SimpleHTTPServer, SocketServer, BaseHTTPServer, urlparse
    import socket, errno
    import traceback

    class WSGIHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
        def run_wsgi_app(self):
            protocol, host, path, parameters, query, fragment = \
                urlparse.urlparse('http://dummyhost%s' % self.path)

            # we only use path, query
            env = {'wsgi.version': (1, 0)
                   ,'wsgi.url_scheme': 'http'
                   ,'wsgi.input': self.rfile
                   ,'wsgi.errors': sys.stderr
                   ,'wsgi.multithread': 1
                   ,'wsgi.multiprocess': 0
                   ,'wsgi.run_once': 0
                   ,'REQUEST_METHOD': self.command
                   ,'REQUEST_URI': self.path
                   ,'PATH_INFO': path
                   ,'QUERY_STRING': query
                   ,'CONTENT_TYPE': self.headers.get('Content-Type', '')
                   ,'CONTENT_LENGTH': self.headers.get('Content-Length', '')
                   ,'REMOTE_ADDR': self.client_address[0]
                   ,'SERVER_NAME': self.server.server_address[0]
                   ,'SERVER_PORT': str(self.server.server_address[1])
                   ,'SERVER_PROTOCOL': self.request_version
                   }

            for http_header, http_value in self.headers.items():
                env ['HTTP_%s' % http_header.replace('-', '_').upper()] = \
                    http_value

            # Setup the state
            self.wsgi_sent_headers = 0
            self.wsgi_headers = []

            try:
                # We have there environment, now invoke the application
                result = self.server.app(env, self.wsgi_start_response)
                try:
                    try:
                        for data in result:
                            if data: 
                                self.wsgi_write_data(data)
                    finally:
                        if hasattr(result, 'close'): 
                            result.close()
                except socket.error, socket_err:
                    # Catch common network errors and suppress them
                    if (socket_err.args[0] in \
                       (errno.ECONNABORTED, errno.EPIPE)): 
                        return
                except socket.timeout, socket_timeout: 
                    return
            except:
                print >> web.debug, traceback.format_exc(),

            if (not self.wsgi_sent_headers):
                # We must write out something!
                self.wsgi_write_data(" ")
            return

        do_POST = run_wsgi_app
        do_PUT = run_wsgi_app
        do_DELETE = run_wsgi_app

        def do_GET(self):
            if self.path.startswith('/static/'):
                SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)
            else:
                self.run_wsgi_app()

        def wsgi_start_response(self, response_status, response_headers, 
                              exc_info=None):
            if (self.wsgi_sent_headers):
                raise Exception \
                      ("Headers already sent and start_response called again!")
            # Should really take a copy to avoid changes in the application....
            self.wsgi_headers = (response_status, response_headers)
            return self.wsgi_write_data

        def wsgi_write_data(self, data):
            if (not self.wsgi_sent_headers):
                status, headers = self.wsgi_headers
                # Need to send header prior to data
                status_code = status[:status.find(' ')]
                status_msg = status[status.find(' ') + 1:]
                self.send_response(int(status_code), status_msg)
                for header, value in headers:
                    self.send_header(header, value)
                self.end_headers()
                self.wsgi_sent_headers = 1
            # Send the data
            self.wfile.write(data)

    class WSGIServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
        def __init__(self, func, server_address):
            BaseHTTPServer.HTTPServer.__init__(self, 
                                               server_address, 
                                               WSGIHandler)
            self.app = func
            self.serverShuttingDown = 0

    print "http://%s:%d/" % server_address
    WSGIServer(func, server_address).serve_forever()

def runsimple(func, server_address=("0.0.0.0", 8080)):
    """
    Runs [CherryPy][cp] WSGI server hosting WSGI app `func`. 
    The directory `static/` is hosted statically.

    [cp]: http://www.cherrypy.org
    """
    func = StaticMiddleware(func)
    func = LogMiddleware(func)
    
    server = WSGIServer(server_address, func)

    if server.ssl_adapter:
        print "https://%s:%d/" % server_address
    else:
        print "http://%s:%d/" % server_address

    try:
        server.start()
    except (KeyboardInterrupt, SystemExit):
        server.stop()

def WSGIServer(server_address, wsgi_app):
    """Creates CherryPy WSGI server listening at `server_address` to serve `wsgi_app`.
    This function can be overwritten to customize the webserver or use a different webserver.
    """
    import wsgiserver
    
    # Default values of wsgiserver.ssl_adapters uses cherrypy.wsgiserver
    # prefix. Overwriting it make it work with web.wsgiserver.
    wsgiserver.ssl_adapters = {
        'builtin': 'web.wsgiserver.ssl_builtin.BuiltinSSLAdapter',
        'pyopenssl': 'web.wsgiserver.ssl_pyopenssl.pyOpenSSLAdapter',
    }
    
    server = wsgiserver.CherryPyWSGIServer(server_address, wsgi_app, server_name="localhost")
        
    def create_ssl_adapter(cert, key):
        # wsgiserver tries to import submodules as cherrypy.wsgiserver.foo.
        # That doesn't work as not it is web.wsgiserver. 
        # Patching sys.modules temporarily to make it work.
        import types
        cherrypy = types.ModuleType('cherrypy')
        cherrypy.wsgiserver = wsgiserver
        sys.modules['cherrypy'] = cherrypy
        sys.modules['cherrypy.wsgiserver'] = wsgiserver
        
        from wsgiserver.ssl_pyopenssl import pyOpenSSLAdapter
        adapter = pyOpenSSLAdapter(cert, key)
        
        # We are done with our work. Cleanup the patches.
        del sys.modules['cherrypy']
        del sys.modules['cherrypy.wsgiserver']

        return adapter

    # SSL backward compatibility
    if (server.ssl_adapter is None and
        getattr(server, 'ssl_certificate', None) and
        getattr(server, 'ssl_private_key', None)):
        server.ssl_adapter = create_ssl_adapter(server.ssl_certificate, server.ssl_private_key)

    server.nodelay = not sys.platform.startswith('java') # TCP_NODELAY isn't supported on the JVM
    return server

class StaticApp(SimpleHTTPRequestHandler):
    """WSGI application for serving static files."""
    def __init__(self, environ, start_response):
        self.headers = []
        self.environ = environ
        self.start_response = start_response

    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.unquote(path))
        words = path.split('/')
        words = filter(None, words)
        if hasattr(web.config, "static_path"):
            path = os.path.dirname(web.config.static_path)
        else:
            path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path

    def send_response(self, status, msg=""):
        self.status = str(status) + " " + msg

    def send_header(self, name, value):
        self.headers.append((name, value))

    def end_headers(self):
        pass

    def log_message(*a): pass

    def __iter__(self):
        environ = self.environ

        self.path = environ.get('PATH_INFO', '')
        self.client_address = environ.get('REMOTE_ADDR','-'), \
                              environ.get('REMOTE_PORT','-')
        self.command = environ.get('REQUEST_METHOD', '-')

        from cStringIO import StringIO
        self.wfile = StringIO() # for capturing error

        try:
            path = self.translate_path(self.path)
            etag = '"%s"' % os.path.getmtime(path)
            client_etag = environ.get('HTTP_IF_NONE_MATCH')
            self.send_header('ETag', etag)
            if etag == client_etag:
                self.send_response(304, "Not Modified")
                self.start_response(self.status, self.headers)
                raise StopIteration
        except OSError:
            pass # Probably a 404

        f = self.send_head()
        self.start_response(self.status, self.headers)

        if f:
            block_size = 16 * 1024
            while True:
                buf = f.read(block_size)
                if not buf:
                    break
                yield buf
            f.close()
        else:
            value = self.wfile.getvalue()
            yield value

class StaticMiddleware:
    """WSGI middleware for serving static files."""
    def __init__(self, app, prefix='/static/'):
        self.app = app
        self.prefix = prefix
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        path = self.normpath(path)

        if path.startswith(self.prefix):
            return StaticApp(environ, start_response)
        else:
            return self.app(environ, start_response)

    def normpath(self, path):
        path2 = posixpath.normpath(urllib.unquote(path))
        if path.endswith("/"):
            path2 += "/"
        return path2

    
class LogMiddleware:
    """WSGI middleware for logging the status."""
    def __init__(self, app):
        self.app = app
        self.format = '%s - - [%s] "%s %s %s" - %s'
    
        from BaseHTTPServer import BaseHTTPRequestHandler
        import StringIO
        f = StringIO.StringIO()
        
        class FakeSocket:
            def makefile(self, *a):
                return f
        
        # take log_date_time_string method from BaseHTTPRequestHandler
        self.log_date_time_string = BaseHTTPRequestHandler(FakeSocket(), None, None).log_date_time_string
        
    def __call__(self, environ, start_response):
        def xstart_response(status, response_headers, *args):
            out = start_response(status, response_headers, *args)
            self.log(status, environ)
            return out

        return self.app(environ, xstart_response)
             
    def log(self, status, environ):
        outfile = environ.get('wsgi.errors', web.debug)
        req = environ.get('PATH_INFO', '_')
        protocol = environ.get('ACTUAL_SERVER_PROTOCOL', '-')
        method = environ.get('REQUEST_METHOD', '-')
        host = "%s:%s" % (environ.get('REMOTE_ADDR','-'), 
                          environ.get('REMOTE_PORT','-'))

        time = self.log_date_time_string()

        msg = self.format % (host, time, protocol, method, req, status)
        print >> outfile, utils.safestr(msg)

########NEW FILE########
__FILENAME__ = net
"""
Network Utilities
(from web.py)
"""

__all__ = [
  "validipaddr", "validipport", "validip", "validaddr", 
  "urlquote",
  "httpdate", "parsehttpdate", 
  "htmlquote", "htmlunquote", "websafe",
]

import urllib, time
try: import datetime
except ImportError: pass

def validipaddr(address):
    """
    Returns True if `address` is a valid IPv4 address.
    
        >>> validipaddr('192.168.1.1')
        True
        >>> validipaddr('192.168.1.800')
        False
        >>> validipaddr('192.168.1')
        False
    """
    try:
        octets = address.split('.')
        if len(octets) != 4:
            return False
        for x in octets:
            if not (0 <= int(x) <= 255):
                return False
    except ValueError:
        return False
    return True

def validipport(port):
    """
    Returns True if `port` is a valid IPv4 port.
    
        >>> validipport('9000')
        True
        >>> validipport('foo')
        False
        >>> validipport('1000000')
        False
    """
    try:
        if not (0 <= int(port) <= 65535):
            return False
    except ValueError:
        return False
    return True

def validip(ip, defaultaddr="0.0.0.0", defaultport=8080):
    """Returns `(ip_address, port)` from string `ip_addr_port`"""
    addr = defaultaddr
    port = defaultport
    
    ip = ip.split(":", 1)
    if len(ip) == 1:
        if not ip[0]:
            pass
        elif validipaddr(ip[0]):
            addr = ip[0]
        elif validipport(ip[0]):
            port = int(ip[0])
        else:
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    elif len(ip) == 2:
        addr, port = ip
        if not validipaddr(addr) and validipport(port):
            raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
        port = int(port)
    else:
        raise ValueError, ':'.join(ip) + ' is not a valid IP address/port'
    return (addr, port)

def validaddr(string_):
    """
    Returns either (ip_address, port) or "/path/to/socket" from string_
    
        >>> validaddr('/path/to/socket')
        '/path/to/socket'
        >>> validaddr('8000')
        ('0.0.0.0', 8000)
        >>> validaddr('127.0.0.1')
        ('127.0.0.1', 8080)
        >>> validaddr('127.0.0.1:8000')
        ('127.0.0.1', 8000)
        >>> validaddr('fff')
        Traceback (most recent call last):
            ...
        ValueError: fff is not a valid IP address/port
    """
    if '/' in string_:
        return string_
    else:
        return validip(string_)

def urlquote(val):
    """
    Quotes a string for use in a URL.
    
        >>> urlquote('://?f=1&j=1')
        '%3A//%3Ff%3D1%26j%3D1'
        >>> urlquote(None)
        ''
        >>> urlquote(u'\u203d')
        '%E2%80%BD'
    """
    if val is None: return ''
    if not isinstance(val, unicode): val = str(val)
    else: val = val.encode('utf-8')
    return urllib.quote(val)

def httpdate(date_obj):
    """
    Formats a datetime object for use in HTTP headers.
    
        >>> import datetime
        >>> httpdate(datetime.datetime(1970, 1, 1, 1, 1, 1))
        'Thu, 01 Jan 1970 01:01:01 GMT'
    """
    return date_obj.strftime("%a, %d %b %Y %H:%M:%S GMT")

def parsehttpdate(string_):
    """
    Parses an HTTP date into a datetime object.

        >>> parsehttpdate('Thu, 01 Jan 1970 01:01:01 GMT')
        datetime.datetime(1970, 1, 1, 1, 1, 1)
    """
    try:
        t = time.strptime(string_, "%a, %d %b %Y %H:%M:%S %Z")
    except ValueError:
        return None
    return datetime.datetime(*t[:6])

def htmlquote(text):
    r"""
    Encodes `text` for raw use in HTML.
    
        >>> htmlquote(u"<'&\">")
        u'&lt;&#39;&amp;&quot;&gt;'
    """
    text = text.replace(u"&", u"&amp;") # Must be done first!
    text = text.replace(u"<", u"&lt;")
    text = text.replace(u">", u"&gt;")
    text = text.replace(u"'", u"&#39;")
    text = text.replace(u'"', u"&quot;")
    return text

def htmlunquote(text):
    r"""
    Decodes `text` that's HTML quoted.

        >>> htmlunquote(u'&lt;&#39;&amp;&quot;&gt;')
        u'<\'&">'
    """
    text = text.replace(u"&quot;", u'"')
    text = text.replace(u"&#39;", u"'")
    text = text.replace(u"&gt;", u">")
    text = text.replace(u"&lt;", u"<")
    text = text.replace(u"&amp;", u"&") # Must be done last!
    return text
    
def websafe(val):
    r"""Converts `val` so that it is safe for use in Unicode HTML.

        >>> websafe("<'&\">")
        u'&lt;&#39;&amp;&quot;&gt;'
        >>> websafe(None)
        u''
        >>> websafe(u'\u203d')
        u'\u203d'
        >>> websafe('\xe2\x80\xbd')
        u'\u203d'
    """
    if val is None:
        return u''
    elif isinstance(val, str):
        val = val.decode('utf-8')
    elif not isinstance(val, unicode):
        val = unicode(val)
        
    return htmlquote(val)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = python23
"""Python 2.3 compatabilty"""
import threading

class threadlocal(object):
    """Implementation of threading.local for python2.3.
    """
    def __getattribute__(self, name):
        if name == "__dict__":
            return threadlocal._getd(self)
        else:
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                try:
                    return self.__dict__[name]
                except KeyError:
                    raise AttributeError, name
            
    def __setattr__(self, name, value):
        self.__dict__[name] = value
        
    def __delattr__(self, name):
        try:
            del self.__dict__[name]
        except KeyError:
            raise AttributeError, name
    
    def _getd(self):
        t = threading.currentThread()
        if not hasattr(t, '_d'):
            # using __dict__ of thread as thread local storage
            t._d = {}
        
        _id = id(self)
        # there could be multiple instances of threadlocal.
        # use id(self) as key
        if _id not in t._d:
            t._d[_id] = {}
        return t._d[_id]
        
if __name__ == '__main__':
     d = threadlocal()
     d.x = 1
     print d.__dict__
     print d.x
     
########NEW FILE########
__FILENAME__ = session
"""
Session Management
(from web.py)
"""

import os, time, datetime, random, base64
import os.path
from copy import deepcopy
try:
    import cPickle as pickle
except ImportError:
    import pickle
try:
    import hashlib
    sha1 = hashlib.sha1
except ImportError:
    import sha
    sha1 = sha.new

import utils
import webapi as web

__all__ = [
    'Session', 'SessionExpired',
    'Store', 'DiskStore', 'DBStore',
]

web.config.session_parameters = utils.storage({
    'cookie_name': 'webpy_session_id',
    'cookie_domain': None,
    'cookie_path' : None,
    'timeout': 86400, #24 * 60 * 60, # 24 hours in seconds
    'ignore_expiry': True,
    'ignore_change_ip': True,
    'secret_key': 'fLjUfxqXtfNoIldA0A0J',
    'expired_message': 'Session expired',
    'httponly': True,
    'secure': False
})

class SessionExpired(web.HTTPError): 
    def __init__(self, message):
        web.HTTPError.__init__(self, '200 OK', {}, data=message)

class Session(object):
    """Session management for web.py
    """
    __slots__ = [
        "store", "_initializer", "_last_cleanup_time", "_config", "_data", 
        "__getitem__", "__setitem__", "__delitem__"
    ]

    def __init__(self, app, store, initializer=None):
        self.store = store
        self._initializer = initializer
        self._last_cleanup_time = 0
        self._config = utils.storage(web.config.session_parameters)
        self._data = utils.threadeddict()
        
        self.__getitem__ = self._data.__getitem__
        self.__setitem__ = self._data.__setitem__
        self.__delitem__ = self._data.__delitem__

        if app:
            app.add_processor(self._processor)

    def __contains__(self, name):
        return name in self._data

    def __getattr__(self, name):
        return getattr(self._data, name)
    
    def __setattr__(self, name, value):
        if name in self.__slots__:
            object.__setattr__(self, name, value)
        else:
            setattr(self._data, name, value)
        
    def __delattr__(self, name):
        delattr(self._data, name)

    def _processor(self, handler):
        """Application processor to setup session for every request"""
        self._cleanup()
        self._load()

        try:
            return handler()
        finally:
            self._save()

    def _load(self):
        """Load the session from the store, by the id from cookie"""
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        cookie_path = self._config.cookie_path
        httponly = self._config.httponly
        self.session_id = web.cookies().get(cookie_name)

        # protection against session_id tampering
        if self.session_id and not self._valid_session_id(self.session_id):
            self.session_id = None

        self._check_expiry()
        if self.session_id:
            d = self.store[self.session_id]
            self.update(d)
            self._validate_ip()
        
        if not self.session_id:
            self.session_id = self._generate_session_id()

            if self._initializer:
                if isinstance(self._initializer, dict):
                    self.update(deepcopy(self._initializer))
                elif hasattr(self._initializer, '__call__'):
                    self._initializer()
 
        self.ip = web.ctx.ip

    def _check_expiry(self):
        # check for expiry
        if self.session_id and self.session_id not in self.store:
            if self._config.ignore_expiry:
                self.session_id = None
            else:
                return self.expired()

    def _validate_ip(self):
        # check for change of IP
        if self.session_id and self.get('ip', None) != web.ctx.ip:
            if not self._config.ignore_change_ip:
               return self.expired() 
    
    def _save(self):
        if not self.get('_killed'):
            self._setcookie(self.session_id)
            self.store[self.session_id] = dict(self._data)
        else:
            self._setcookie(self.session_id, expires=-1)
            
    def _setcookie(self, session_id, expires='', **kw):
        cookie_name = self._config.cookie_name
        cookie_domain = self._config.cookie_domain
        cookie_path = self._config.cookie_path
        httponly = self._config.httponly
        secure = self._config.secure
        web.setcookie(cookie_name, session_id, expires=expires, domain=cookie_domain, httponly=httponly, secure=secure, path=cookie_path)
    
    def _generate_session_id(self):
        """Generate a random id for session"""

        while True:
            rand = os.urandom(16)
            now = time.time()
            secret_key = self._config.secret_key
            session_id = sha1("%s%s%s%s" %(rand, now, utils.safestr(web.ctx.ip), secret_key))
            session_id = session_id.hexdigest()
            if session_id not in self.store:
                break
        return session_id

    def _valid_session_id(self, session_id):
        rx = utils.re_compile('^[0-9a-fA-F]+$')
        return rx.match(session_id)
        
    def _cleanup(self):
        """Cleanup the stored sessions"""
        current_time = time.time()
        timeout = self._config.timeout
        if current_time - self._last_cleanup_time > timeout:
            self.store.cleanup(timeout)
            self._last_cleanup_time = current_time

    def expired(self):
        """Called when an expired session is atime"""
        self._killed = True
        self._save()
        raise SessionExpired(self._config.expired_message)
 
    def kill(self):
        """Kill the session, make it no longer available"""
        del self.store[self.session_id]
        self._killed = True

class Store:
    """Base class for session stores"""

    def __contains__(self, key):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

    def cleanup(self, timeout):
        """removes all the expired sessions"""
        raise NotImplementedError

    def encode(self, session_dict):
        """encodes session dict as a string"""
        pickled = pickle.dumps(session_dict)
        return base64.encodestring(pickled)

    def decode(self, session_data):
        """decodes the data to get back the session dict """
        pickled = base64.decodestring(session_data)
        return pickle.loads(pickled)

class DiskStore(Store):
    """
    Store for saving a session on disk.

        >>> import tempfile
        >>> root = tempfile.mkdtemp()
        >>> s = DiskStore(root)
        >>> s['a'] = 'foo'
        >>> s['a']
        'foo'
        >>> time.sleep(0.01)
        >>> s.cleanup(0.01)
        >>> s['a']
        Traceback (most recent call last):
            ...
        KeyError: 'a'
    """
    def __init__(self, root):
        # if the storage root doesn't exists, create it.
        if not os.path.exists(root):
            os.makedirs(
                    os.path.abspath(root)
                    )
        self.root = root

    def _get_path(self, key):
        if os.path.sep in key: 
            raise ValueError, "Bad key: %s" % repr(key)
        return os.path.join(self.root, key)
    
    def __contains__(self, key):
        path = self._get_path(key)
        return os.path.exists(path)

    def __getitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path): 
            pickled = open(path).read()
            return self.decode(pickled)
        else:
            raise KeyError, key

    def __setitem__(self, key, value):
        path = self._get_path(key)
        pickled = self.encode(value)    
        try:
            f = open(path, 'w')
            try:
                f.write(pickled)
            finally: 
                f.close()
        except IOError:
            pass

    def __delitem__(self, key):
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)
    
    def cleanup(self, timeout):
        now = time.time()
        for f in os.listdir(self.root):
            path = self._get_path(f)
            atime = os.stat(path).st_atime
            if now - atime > timeout :
                os.remove(path)

class DBStore(Store):
    """Store for saving a session in database
    Needs a table with the following columns:

        session_id CHAR(128) UNIQUE NOT NULL,
        atime DATETIME NOT NULL default current_timestamp,
        data TEXT
    """
    def __init__(self, db, table_name):
        self.db = db
        self.table = table_name
    
    def __contains__(self, key):
        data = self.db.select(self.table, where="session_id=$key", vars=locals())
        return bool(list(data)) 

    def __getitem__(self, key):
        now = datetime.datetime.now()
        try:
            s = self.db.select(self.table, where="session_id=$key", vars=locals())[0]
            self.db.update(self.table, where="session_id=$key", atime=now, vars=locals())
        except IndexError:
            raise KeyError
        else:
            return self.decode(s.data)

    def __setitem__(self, key, value):
        pickled = self.encode(value)
        now = datetime.datetime.now()
        if key in self:
            self.db.update(self.table, where="session_id=$key", data=pickled, vars=locals())
        else:
            self.db.insert(self.table, False, session_id=key, data=pickled )
                
    def __delitem__(self, key):
        self.db.delete(self.table, where="session_id=$key", vars=locals())

    def cleanup(self, timeout):
        timeout = datetime.timedelta(timeout/(24.0*60*60)) #timedelta takes numdays as arg
        last_allowed_time = datetime.datetime.now() - timeout
        self.db.delete(self.table, where="$last_allowed_time > atime", vars=locals())

class ShelfStore:
    """Store for saving session using `shelve` module.

        import shelve
        store = ShelfStore(shelve.open('session.shelf'))

    XXX: is shelve thread-safe?
    """
    def __init__(self, shelf):
        self.shelf = shelf

    def __contains__(self, key):
        return key in self.shelf

    def __getitem__(self, key):
        atime, v = self.shelf[key]
        self[key] = v # update atime
        return v

    def __setitem__(self, key, value):
        self.shelf[key] = time.time(), value
        
    def __delitem__(self, key):
        try:
            del self.shelf[key]
        except KeyError:
            pass

    def cleanup(self, timeout):
        now = time.time()
        for k in self.shelf.keys():
            atime, v = self.shelf[k]
            if now - atime > timeout :
                del self[k]

if __name__ == '__main__' :
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = template
"""
simple, elegant templating
(part of web.py)

Template design:

Template string is split into tokens and the tokens are combined into nodes. 
Parse tree is a nodelist. TextNode and ExpressionNode are simple nodes and 
for-loop, if-loop etc are block nodes, which contain multiple child nodes. 

Each node can emit some python string. python string emitted by the 
root node is validated for safeeval and executed using python in the given environment.

Enough care is taken to make sure the generated code and the template has line to line match, 
so that the error messages can point to exact line number in template. (It doesn't work in some cases still.)

Grammar:

    template -> defwith sections 
    defwith -> '$def with (' arguments ')' | ''
    sections -> section*
    section -> block | assignment | line

    assignment -> '$ ' <assignment expression>
    line -> (text|expr)*
    text -> <any characters other than $>
    expr -> '$' pyexpr | '$(' pyexpr ')' | '${' pyexpr '}'
    pyexpr -> <python expression>
"""

__all__ = [
    "Template",
    "Render", "render", "frender",
    "ParseError", "SecurityError",
    "test"
]

import tokenize
import os
import sys
import glob
import re
from UserDict import DictMixin
import warnings

from utils import storage, safeunicode, safestr, re_compile
from webapi import config
from net import websafe

def splitline(text):
    r"""
    Splits the given text at newline.
    
        >>> splitline('foo\nbar')
        ('foo\n', 'bar')
        >>> splitline('foo')
        ('foo', '')
        >>> splitline('')
        ('', '')
    """
    index = text.find('\n') + 1
    if index:
        return text[:index], text[index:]
    else:
        return text, ''

class Parser:
    """Parser Base.
    """
    def __init__(self):
        self.statement_nodes = STATEMENT_NODES
        self.keywords = KEYWORDS

    def parse(self, text, name="<template>"):
        self.text = text
        self.name = name
        
        defwith, text = self.read_defwith(text)
        suite = self.read_suite(text)
        return DefwithNode(defwith, suite)

    def read_defwith(self, text):
        if text.startswith('$def with'):
            defwith, text = splitline(text)
            defwith = defwith[1:].strip() # strip $ and spaces
            return defwith, text
        else:
            return '', text
    
    def read_section(self, text):
        r"""Reads one section from the given text.
        
        section -> block | assignment | line
        
            >>> read_section = Parser().read_section
            >>> read_section('foo\nbar\n')
            (<line: [t'foo\n']>, 'bar\n')
            >>> read_section('$ a = b + 1\nfoo\n')
            (<assignment: 'a = b + 1'>, 'foo\n')
            
        read_section('$for in range(10):\n    hello $i\nfoo)
        """
        if text.lstrip(' ').startswith('$'):
            index = text.index('$')
            begin_indent, text2 = text[:index], text[index+1:]
            ahead = self.python_lookahead(text2)
            
            if ahead == 'var':
                return self.read_var(text2)
            elif ahead in self.statement_nodes:
                return self.read_block_section(text2, begin_indent)
            elif ahead in self.keywords:
                return self.read_keyword(text2)
            elif ahead.strip() == '':
                # assignments starts with a space after $
                # ex: $ a = b + 2
                return self.read_assignment(text2)
        return self.readline(text)
        
    def read_var(self, text):
        r"""Reads a var statement.
        
            >>> read_var = Parser().read_var
            >>> read_var('var x=10\nfoo')
            (<var: x = 10>, 'foo')
            >>> read_var('var x: hello $name\nfoo')
            (<var: x = join_(u'hello ', escape_(name, True))>, 'foo')
        """
        line, text = splitline(text)
        tokens = self.python_tokens(line)
        if len(tokens) < 4:
            raise SyntaxError('Invalid var statement')
            
        name = tokens[1]
        sep = tokens[2]
        value = line.split(sep, 1)[1].strip()
        
        if sep == '=':
            pass # no need to process value
        elif sep == ':': 
            #@@ Hack for backward-compatability
            if tokens[3] == '\n': # multi-line var statement
                block, text = self.read_indented_block(text, '    ')
                lines = [self.readline(x)[0] for x in block.splitlines()]
                nodes = []
                for x in lines:
                    nodes.extend(x.nodes)
                    nodes.append(TextNode('\n'))         
            else: # single-line var statement
                linenode, _ = self.readline(value)
                nodes = linenode.nodes                
            parts = [node.emit('') for node in nodes]
            value = "join_(%s)" % ", ".join(parts)
        else:
            raise SyntaxError('Invalid var statement')
        return VarNode(name, value), text
                    
    def read_suite(self, text):
        r"""Reads section by section till end of text.
        
            >>> read_suite = Parser().read_suite
            >>> read_suite('hello $name\nfoo\n')
            [<line: [t'hello ', $name, t'\n']>, <line: [t'foo\n']>]
        """
        sections = []
        while text:
            section, text = self.read_section(text)
            sections.append(section)
        return SuiteNode(sections)
    
    def readline(self, text):
        r"""Reads one line from the text. Newline is supressed if the line ends with \.
        
            >>> readline = Parser().readline
            >>> readline('hello $name!\nbye!')
            (<line: [t'hello ', $name, t'!\n']>, 'bye!')
            >>> readline('hello $name!\\\nbye!')
            (<line: [t'hello ', $name, t'!']>, 'bye!')
            >>> readline('$f()\n\n')
            (<line: [$f(), t'\n']>, '\n')
        """
        line, text = splitline(text)

        # supress new line if line ends with \
        if line.endswith('\\\n'):
            line = line[:-2]
                
        nodes = []
        while line:
            node, line = self.read_node(line)
            nodes.append(node)
            
        return LineNode(nodes), text

    def read_node(self, text):
        r"""Reads a node from the given text and returns the node and remaining text.

            >>> read_node = Parser().read_node
            >>> read_node('hello $name')
            (t'hello ', '$name')
            >>> read_node('$name')
            ($name, '')
        """
        if text.startswith('$$'):
            return TextNode('$'), text[2:]
        elif text.startswith('$#'): # comment
            line, text = splitline(text)
            return TextNode('\n'), text
        elif text.startswith('$'):
            text = text[1:] # strip $
            if text.startswith(':'):
                escape = False
                text = text[1:] # strip :
            else:
                escape = True
            return self.read_expr(text, escape=escape)
        else:
            return self.read_text(text)
    
    def read_text(self, text):
        r"""Reads a text node from the given text.
        
            >>> read_text = Parser().read_text
            >>> read_text('hello $name')
            (t'hello ', '$name')
        """
        index = text.find('$')
        if index < 0:
            return TextNode(text), ''
        else:
            return TextNode(text[:index]), text[index:]
            
    def read_keyword(self, text):
        line, text = splitline(text)
        return StatementNode(line.strip() + "\n"), text

    def read_expr(self, text, escape=True):
        """Reads a python expression from the text and returns the expression and remaining text.

        expr -> simple_expr | paren_expr
        simple_expr -> id extended_expr
        extended_expr -> attr_access | paren_expr extended_expr | ''
        attr_access -> dot id extended_expr
        paren_expr -> [ tokens ] | ( tokens ) | { tokens }
     
            >>> read_expr = Parser().read_expr
            >>> read_expr("name")
            ($name, '')
            >>> read_expr("a.b and c")
            ($a.b, ' and c')
            >>> read_expr("a. b")
            ($a, '. b')
            >>> read_expr("name</h1>")
            ($name, '</h1>')
            >>> read_expr("(limit)ing")
            ($(limit), 'ing')
            >>> read_expr('a[1, 2][:3].f(1+2, "weird string[).", 3 + 4) done.')
            ($a[1, 2][:3].f(1+2, "weird string[).", 3 + 4), ' done.')
        """
        def simple_expr():
            identifier()
            extended_expr()
        
        def identifier():
            tokens.next()
        
        def extended_expr():
            lookahead = tokens.lookahead()
            if lookahead is None:
                return
            elif lookahead.value == '.':
                attr_access()
            elif lookahead.value in parens:
                paren_expr()
                extended_expr()
            else:
                return
        
        def attr_access():
            from token import NAME # python token constants
            dot = tokens.lookahead()
            if tokens.lookahead2().type == NAME:
                tokens.next() # consume dot
                identifier()
                extended_expr()
        
        def paren_expr():
            begin = tokens.next().value
            end = parens[begin]
            while True:
                if tokens.lookahead().value in parens:
                    paren_expr()
                else:
                    t = tokens.next()
                    if t.value == end:
                        break
            return

        parens = {
            "(": ")",
            "[": "]",
            "{": "}"
        }
        
        def get_tokens(text):
            """tokenize text using python tokenizer.
            Python tokenizer ignores spaces, but they might be important in some cases. 
            This function introduces dummy space tokens when it identifies any ignored space.
            Each token is a storage object containing type, value, begin and end.
            """
            readline = iter([text]).next
            end = None
            for t in tokenize.generate_tokens(readline):
                t = storage(type=t[0], value=t[1], begin=t[2], end=t[3])
                if end is not None and end != t.begin:
                    _, x1 = end
                    _, x2 = t.begin
                    yield storage(type=-1, value=text[x1:x2], begin=end, end=t.begin)
                end = t.end
                yield t
                
        class BetterIter:
            """Iterator like object with 2 support for 2 look aheads."""
            def __init__(self, items):
                self.iteritems = iter(items)
                self.items = []
                self.position = 0
                self.current_item = None
            
            def lookahead(self):
                if len(self.items) <= self.position:
                    self.items.append(self._next())
                return self.items[self.position]

            def _next(self):
                try:
                    return self.iteritems.next()
                except StopIteration:
                    return None
                
            def lookahead2(self):
                if len(self.items) <= self.position+1:
                    self.items.append(self._next())
                return self.items[self.position+1]
                    
            def next(self):
                self.current_item = self.lookahead()
                self.position += 1
                return self.current_item

        tokens = BetterIter(get_tokens(text))
                
        if tokens.lookahead().value in parens:
            paren_expr()
        else:
            simple_expr()
        row, col = tokens.current_item.end
        return ExpressionNode(text[:col], escape=escape), text[col:]    

    def read_assignment(self, text):
        r"""Reads assignment statement from text.
    
            >>> read_assignment = Parser().read_assignment
            >>> read_assignment('a = b + 1\nfoo')
            (<assignment: 'a = b + 1'>, 'foo')
        """
        line, text = splitline(text)
        return AssignmentNode(line.strip()), text
    
    def python_lookahead(self, text):
        """Returns the first python token from the given text.
        
            >>> python_lookahead = Parser().python_lookahead
            >>> python_lookahead('for i in range(10):')
            'for'
            >>> python_lookahead('else:')
            'else'
            >>> python_lookahead(' x = 1')
            ' '
        """
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return tokens.next()[1]
        
    def python_tokens(self, text):
        readline = iter([text]).next
        tokens = tokenize.generate_tokens(readline)
        return [t[1] for t in tokens]
        
    def read_indented_block(self, text, indent):
        r"""Read a block of text. A block is what typically follows a for or it statement.
        It can be in the same line as that of the statement or an indented block.

            >>> read_indented_block = Parser().read_indented_block
            >>> read_indented_block('  a\n  b\nc', '  ')
            ('a\nb\n', 'c')
            >>> read_indented_block('  a\n    b\n  c\nd', '  ')
            ('a\n  b\nc\n', 'd')
            >>> read_indented_block('  a\n\n    b\nc', '  ')
            ('a\n\n  b\n', 'c')
        """
        if indent == '':
            return '', text
            
        block = ""
        while text:
            line, text2 = splitline(text)
            if line.strip() == "":
                block += '\n'
            elif line.startswith(indent):
                block += line[len(indent):]
            else:
                break
            text = text2
        return block, text

    def read_statement(self, text):
        r"""Reads a python statement.
        
            >>> read_statement = Parser().read_statement
            >>> read_statement('for i in range(10): hello $name')
            ('for i in range(10):', ' hello $name')
        """
        tok = PythonTokenizer(text)
        tok.consume_till(':')
        return text[:tok.index], text[tok.index:]
        
    def read_block_section(self, text, begin_indent=''):
        r"""
            >>> read_block_section = Parser().read_block_section
            >>> read_block_section('for i in range(10): hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
            >>> read_block_section('for i in range(10):\n        hello $i\n    foo', begin_indent='    ')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, '    foo')
            >>> read_block_section('for i in range(10):\n  hello $i\nfoo')
            (<block: 'for i in range(10):', [<line: [t'hello ', $i, t'\n']>]>, 'foo')
        """
        line, text = splitline(text)
        stmt, line = self.read_statement(line)
        keyword = self.python_lookahead(stmt)
        
        # if there is some thing left in the line
        if line.strip():
            block = line.lstrip()
        else:
            def find_indent(text):
                rx = re_compile('  +')
                match = rx.match(text)    
                first_indent = match and match.group(0)
                return first_indent or ""

            # find the indentation of the block by looking at the first line
            first_indent = find_indent(text)[len(begin_indent):]

            #TODO: fix this special case
            if keyword == "code":
                indent = begin_indent + first_indent
            else:
                indent = begin_indent + min(first_indent, INDENT)
            
            block, text = self.read_indented_block(text, indent)
            
        return self.create_block_node(keyword, stmt, block, begin_indent), text
        
    def create_block_node(self, keyword, stmt, block, begin_indent):
        if keyword in self.statement_nodes:
            return self.statement_nodes[keyword](stmt, block, begin_indent)
        else:
            raise ParseError, 'Unknown statement: %s' % repr(keyword)
        
class PythonTokenizer:
    """Utility wrapper over python tokenizer."""
    def __init__(self, text):
        self.text = text
        readline = iter([text]).next
        self.tokens = tokenize.generate_tokens(readline)
        self.index = 0
        
    def consume_till(self, delim):        
        """Consumes tokens till colon.
        
            >>> tok = PythonTokenizer('for i in range(10): hello $i')
            >>> tok.consume_till(':')
            >>> tok.text[:tok.index]
            'for i in range(10):'
            >>> tok.text[tok.index:]
            ' hello $i'
        """
        try:
            while True:
                t = self.next()
                if t.value == delim:
                    break
                elif t.value == '(':
                    self.consume_till(')')
                elif t.value == '[':
                    self.consume_till(']')
                elif t.value == '{':
                    self.consume_till('}')

                # if end of line is found, it is an exception.
                # Since there is no easy way to report the line number,
                # leave the error reporting to the python parser later  
                #@@ This should be fixed.
                if t.value == '\n':
                    break
        except:
            #raise ParseError, "Expected %s, found end of line." % repr(delim)

            # raising ParseError doesn't show the line number. 
            # if this error is ignored, then it will be caught when compiling the python code.
            return
    
    def next(self):
        type, t, begin, end, line = self.tokens.next()
        row, col = end
        self.index = col
        return storage(type=type, value=t, begin=begin, end=end)
        
class DefwithNode:
    def __init__(self, defwith, suite):
        if defwith:
            self.defwith = defwith.replace('with', '__template__') + ':'
            # offset 4 lines. for encoding, __lineoffset__, loop and self.
            self.defwith += "\n    __lineoffset__ = -4"
        else:
            self.defwith = 'def __template__():'
            # offset 4 lines for encoding, __template__, __lineoffset__, loop and self.
            self.defwith += "\n    __lineoffset__ = -5"

        self.defwith += "\n    loop = ForLoop()"
        self.defwith += "\n    self = TemplateResult(); extend_ = self.extend"
        self.suite = suite
        self.end = "\n    return self"

    def emit(self, indent):
        encoding = "# coding: utf-8\n"
        return encoding + self.defwith + self.suite.emit(indent + INDENT) + self.end

    def __repr__(self):
        return "<defwith: %s, %s>" % (self.defwith, self.suite)

class TextNode:
    def __init__(self, value):
        self.value = value

    def emit(self, indent, begin_indent=''):
        return repr(safeunicode(self.value))
        
    def __repr__(self):
        return 't' + repr(self.value)

class ExpressionNode:
    def __init__(self, value, escape=True):
        self.value = value.strip()
        
        # convert ${...} to $(...)
        if value.startswith('{') and value.endswith('}'):
            self.value = '(' + self.value[1:-1] + ')'
            
        self.escape = escape

    def emit(self, indent, begin_indent=''):
        return 'escape_(%s, %s)' % (self.value, bool(self.escape))
        
    def __repr__(self):
        if self.escape:
            escape = ''
        else:
            escape = ':'
        return "$%s%s" % (escape, self.value)
        
class AssignmentNode:
    def __init__(self, code):
        self.code = code
        
    def emit(self, indent, begin_indent=''):
        return indent + self.code + "\n"
        
    def __repr__(self):
        return "<assignment: %s>" % repr(self.code)
        
class LineNode:
    def __init__(self, nodes):
        self.nodes = nodes
        
    def emit(self, indent, text_indent='', name=''):
        text = [node.emit('') for node in self.nodes]
        if text_indent:
            text = [repr(text_indent)] + text

        return indent + "extend_([%s])\n" % ", ".join(text)        
    
    def __repr__(self):
        return "<line: %s>" % repr(self.nodes)

INDENT = '    ' # 4 spaces
        
class BlockNode:
    def __init__(self, stmt, block, begin_indent=''):
        self.stmt = stmt
        self.suite = Parser().read_suite(block)
        self.begin_indent = begin_indent

    def emit(self, indent, text_indent=''):
        text_indent = self.begin_indent + text_indent
        out = indent + self.stmt + self.suite.emit(indent + INDENT, text_indent)
        return out
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.stmt), repr(self.suite))

class ForNode(BlockNode):
    def __init__(self, stmt, block, begin_indent=''):
        self.original_stmt = stmt
        tok = PythonTokenizer(stmt)
        tok.consume_till('in')
        a = stmt[:tok.index] # for i in
        b = stmt[tok.index:-1] # rest of for stmt excluding :
        stmt = a + ' loop.setup(' + b.strip() + '):'
        BlockNode.__init__(self, stmt, block, begin_indent)
        
    def __repr__(self):
        return "<block: %s, %s>" % (repr(self.original_stmt), repr(self.suite))

class CodeNode:
    def __init__(self, stmt, block, begin_indent=''):
        # compensate one line for $code:
        self.code = "\n" + block
        
    def emit(self, indent, text_indent=''):
        import re
        rx = re.compile('^', re.M)
        return rx.sub(indent, self.code).rstrip(' ')
        
    def __repr__(self):
        return "<code: %s>" % repr(self.code)
        
class StatementNode:
    def __init__(self, stmt):
        self.stmt = stmt
        
    def emit(self, indent, begin_indent=''):
        return indent + self.stmt
        
    def __repr__(self):
        return "<stmt: %s>" % repr(self.stmt)
        
class IfNode(BlockNode):
    pass

class ElseNode(BlockNode):
    pass

class ElifNode(BlockNode):
    pass

class DefNode(BlockNode):
    def __init__(self, *a, **kw):
        BlockNode.__init__(self, *a, **kw)

        code = CodeNode("", "")
        code.code = "self = TemplateResult(); extend_ = self.extend\n"
        self.suite.sections.insert(0, code)

        code = CodeNode("", "")
        code.code = "return self\n"
        self.suite.sections.append(code)
        
    def emit(self, indent, text_indent=''):
        text_indent = self.begin_indent + text_indent
        out = indent + self.stmt + self.suite.emit(indent + INDENT, text_indent)
        return indent + "__lineoffset__ -= 3\n" + out

class VarNode:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def emit(self, indent, text_indent):
        return indent + "self[%s] = %s\n" % (repr(self.name), self.value)
        
    def __repr__(self):
        return "<var: %s = %s>" % (self.name, self.value)

class SuiteNode:
    """Suite is a list of sections."""
    def __init__(self, sections):
        self.sections = sections
        
    def emit(self, indent, text_indent=''):
        return "\n" + "".join([s.emit(indent, text_indent) for s in self.sections])
        
    def __repr__(self):
        return repr(self.sections)

STATEMENT_NODES = {
    'for': ForNode,
    'while': BlockNode,
    'if': IfNode,
    'elif': ElifNode,
    'else': ElseNode,
    'def': DefNode,
    'code': CodeNode
}

KEYWORDS = [
    "pass",
    "break",
    "continue",
    "return"
]

TEMPLATE_BUILTIN_NAMES = [
    "dict", "enumerate", "float", "int", "bool", "list", "long", "reversed", 
    "set", "slice", "tuple", "xrange",
    "abs", "all", "any", "callable", "chr", "cmp", "divmod", "filter", "hex", 
    "id", "isinstance", "iter", "len", "max", "min", "oct", "ord", "pow", "range",
    "True", "False",
    "None",
    "__import__", # some c-libraries like datetime requires __import__ to present in the namespace
]

import __builtin__
TEMPLATE_BUILTINS = dict([(name, getattr(__builtin__, name)) for name in TEMPLATE_BUILTIN_NAMES if name in __builtin__.__dict__])

class ForLoop:
    """
    Wrapper for expression in for stament to support loop.xxx helpers.
    
        >>> loop = ForLoop()
        >>> for x in loop.setup(['a', 'b', 'c']):
        ...     print loop.index, loop.revindex, loop.parity, x
        ...
        1 3 odd a
        2 2 even b
        3 1 odd c
        >>> loop.index
        Traceback (most recent call last):
            ...
        AttributeError: index
    """
    def __init__(self):
        self._ctx = None
        
    def __getattr__(self, name):
        if self._ctx is None:
            raise AttributeError, name
        else:
            return getattr(self._ctx, name)
        
    def setup(self, seq):        
        self._push()
        return self._ctx.setup(seq)
        
    def _push(self):
        self._ctx = ForLoopContext(self, self._ctx)
        
    def _pop(self):
        self._ctx = self._ctx.parent
                
class ForLoopContext:
    """Stackable context for ForLoop to support nested for loops.
    """
    def __init__(self, forloop, parent):
        self._forloop = forloop
        self.parent = parent
        
    def setup(self, seq):
        try:
            self.length = len(seq)
        except:
            self.length = 0

        self.index = 0
        for a in seq:
            self.index += 1
            yield a
        self._forloop._pop()
            
    index0 = property(lambda self: self.index-1)
    first = property(lambda self: self.index == 1)
    last = property(lambda self: self.index == self.length)
    odd = property(lambda self: self.index % 2 == 1)
    even = property(lambda self: self.index % 2 == 0)
    parity = property(lambda self: ['odd', 'even'][self.even])
    revindex0 = property(lambda self: self.length - self.index)
    revindex = property(lambda self: self.length - self.index + 1)
        
class BaseTemplate:
    def __init__(self, code, filename, filter, globals, builtins):
        self.filename = filename
        self.filter = filter
        self._globals = globals
        self._builtins = builtins
        if code:
            self.t = self._compile(code)
        else:
            self.t = lambda: ''
        
    def _compile(self, code):
        env = self.make_env(self._globals or {}, self._builtins)
        exec(code, env)
        return env['__template__']

    def __call__(self, *a, **kw):
        __hidetraceback__ = True
        return self.t(*a, **kw)

    def make_env(self, globals, builtins):
        return dict(globals,
            __builtins__=builtins, 
            ForLoop=ForLoop,
            TemplateResult=TemplateResult,
            escape_=self._escape,
            join_=self._join
        )
    def _join(self, *items):
        return u"".join(items)
            
    def _escape(self, value, escape=False):
        if value is None: 
            value = ''
            
        value = safeunicode(value)
        if escape and self.filter:
            value = self.filter(value)
        return value

class Template(BaseTemplate):
    CONTENT_TYPES = {
        '.html' : 'text/html; charset=utf-8',
        '.xhtml' : 'application/xhtml+xml; charset=utf-8',
        '.txt' : 'text/plain',
    }
    FILTERS = {
        '.html': websafe,
        '.xhtml': websafe,
        '.xml': websafe
    }
    globals = {}
    
    def __init__(self, text, filename='<template>', filter=None, globals=None, builtins=None, extensions=None):
        self.extensions = extensions or []
        text = Template.normalize_text(text)
        code = self.compile_template(text, filename)
                
        _, ext = os.path.splitext(filename)
        filter = filter or self.FILTERS.get(ext, None)
        self.content_type = self.CONTENT_TYPES.get(ext, None)

        if globals is None:
            globals = self.globals
        if builtins is None:
            builtins = TEMPLATE_BUILTINS
                
        BaseTemplate.__init__(self, code=code, filename=filename, filter=filter, globals=globals, builtins=builtins)
        
    def normalize_text(text):
        """Normalizes template text by correcting \r\n, tabs and BOM chars."""
        text = text.replace('\r\n', '\n').replace('\r', '\n').expandtabs()
        if not text.endswith('\n'):
            text += '\n'

        # ignore BOM chars at the begining of template
        BOM = '\xef\xbb\xbf'
        if isinstance(text, str) and text.startswith(BOM):
            text = text[len(BOM):]
        
        # support fort \$ for backward-compatibility 
        text = text.replace(r'\$', '$$')
        return text
    normalize_text = staticmethod(normalize_text)
                
    def __call__(self, *a, **kw):
        __hidetraceback__ = True
        import webapi as web
        if 'headers' in web.ctx and self.content_type:
            web.header('Content-Type', self.content_type, unique=True)
            
        return BaseTemplate.__call__(self, *a, **kw)
        
    def generate_code(text, filename, parser=None):
        # parse the text
        parser = parser or Parser()
        rootnode = parser.parse(text, filename)
                
        # generate python code from the parse tree
        code = rootnode.emit(indent="").strip()
        return safestr(code)
        
    generate_code = staticmethod(generate_code)
    
    def create_parser(self):
        p = Parser()
        for ext in self.extensions:
            p = ext(p)
        return p
                
    def compile_template(self, template_string, filename):
        code = Template.generate_code(template_string, filename, parser=self.create_parser())

        def get_source_line(filename, lineno):
            try:
                lines = open(filename).read().splitlines()
                return lines[lineno]
            except:
                return None
        
        try:
            # compile the code first to report the errors, if any, with the filename
            compiled_code = compile(code, filename, 'exec')
        except SyntaxError, e:
            # display template line that caused the error along with the traceback.
            try:
                e.msg += '\n\nTemplate traceback:\n    File %s, line %s\n        %s' % \
                    (repr(e.filename), e.lineno, get_source_line(e.filename, e.lineno-1))
            except: 
                pass
            raise
        
        # make sure code is safe - but not with jython, it doesn't have a working compiler module
        if not sys.platform.startswith('java'):
            try:
                import compiler
                ast = compiler.parse(code)
                SafeVisitor().walk(ast, filename)
            except ImportError:
                warnings.warn("Unabled to import compiler module. Unable to check templates for safety.")
        else:
            warnings.warn("SECURITY ISSUE: You are using Jython, which does not support checking templates for safety. Your templates can execute arbitrary code.")

        return compiled_code
        
class CompiledTemplate(Template):
    def __init__(self, f, filename):
        Template.__init__(self, '', filename)
        self.t = f
        
    def compile_template(self, *a):
        return None
    
    def _compile(self, *a):
        return None
                
class Render:
    """The most preferred way of using templates.
    
        render = web.template.render('templates')
        print render.foo()
        
    Optional parameter can be `base` can be used to pass output of 
    every template through the base template.
    
        render = web.template.render('templates', base='layout')
    """
    def __init__(self, loc='templates', cache=None, base=None, **keywords):
        self._loc = loc
        self._keywords = keywords

        if cache is None:
            cache = not config.get('debug', False)
        
        if cache:
            self._cache = {}
        else:
            self._cache = None
        
        if base and not hasattr(base, '__call__'):
            # make base a function, so that it can be passed to sub-renders
            self._base = lambda page: self._template(base)(page)
        else:
            self._base = base
    
    def _add_global(self, obj, name=None):
        """Add a global to this rendering instance."""
        if 'globals' not in self._keywords: self._keywords['globals'] = {}
        if not name:
            name = obj.__name__
        self._keywords['globals'][name] = obj
    
    def _lookup(self, name):
        path = os.path.join(self._loc, name)
        if os.path.isdir(path):
            return 'dir', path
        else:
            path = self._findfile(path)
            if path:
                return 'file', path
            else:
                return 'none', None
        
    def _load_template(self, name):
        kind, path = self._lookup(name)
        
        if kind == 'dir':
            return Render(path, cache=self._cache is not None, base=self._base, **self._keywords)
        elif kind == 'file':
            return Template(open(path).read(), filename=path, **self._keywords)
        else:
            raise AttributeError, "No template named " + name            

    def _findfile(self, path_prefix): 
        p = [f for f in glob.glob(path_prefix + '.*') if not f.endswith('~')] # skip backup files
        p.sort() # sort the matches for deterministic order
        return p and p[0]
            
    def _template(self, name):
        if self._cache is not None:
            if name not in self._cache:
                self._cache[name] = self._load_template(name)
            return self._cache[name]
        else:
            return self._load_template(name)
        
    def __getattr__(self, name):
        t = self._template(name)
        if self._base and isinstance(t, Template):
            def template(*a, **kw):
                return self._base(t(*a, **kw))
            return template
        else:
            return self._template(name)

class GAE_Render(Render):
    # Render gets over-written. make a copy here.
    super = Render
    def __init__(self, loc, *a, **kw):
        GAE_Render.super.__init__(self, loc, *a, **kw)
        
        import types
        if isinstance(loc, types.ModuleType):
            self.mod = loc
        else:
            name = loc.rstrip('/').replace('/', '.')
            self.mod = __import__(name, None, None, ['x'])

        self.mod.__dict__.update(kw.get('builtins', TEMPLATE_BUILTINS))
        self.mod.__dict__.update(Template.globals)
        self.mod.__dict__.update(kw.get('globals', {}))

    def _load_template(self, name):
        t = getattr(self.mod, name)
        import types
        if isinstance(t, types.ModuleType):
            return GAE_Render(t, cache=self._cache is not None, base=self._base, **self._keywords)
        else:
            return t

render = Render
# setup render for Google App Engine.
#try:
#    from google import appengine
#    render = Render = GAE_Render
#except ImportError:
#    pass
        
def frender(path, **keywords):
    """Creates a template from the given file path.
    """
    return Template(open(path).read(), filename=path, **keywords)
    
def compile_templates(root):
    """Compiles templates to python code."""
    re_start = re_compile('^', re.M)
    
    for dirpath, dirnames, filenames in os.walk(root):
        filenames = [f for f in filenames if not f.startswith('.') and not f.endswith('~') and not f.startswith('__init__.py')]

        for d in dirnames[:]:
            if d.startswith('.'):
                dirnames.remove(d) # don't visit this dir

        out = open(os.path.join(dirpath, '__init__.py'), 'w')
        out.write('from web.template import CompiledTemplate, ForLoop, TemplateResult\n\n')
        if dirnames:
            out.write("import " + ", ".join(dirnames))
        out.write("\n")

        for f in filenames:
            path = os.path.join(dirpath, f)

            if '.' in f:
                name, _ = f.split('.', 1)
            else:
                name = f
                
            text = open(path).read()
            text = Template.normalize_text(text)
            code = Template.generate_code(text, path)

            code = code.replace("__template__", name, 1)
            
            out.write(code)

            out.write('\n\n')
            out.write('%s = CompiledTemplate(%s, %s)\n' % (name, name, repr(path)))
            out.write("join_ = %s._join; escape_ = %s._escape\n\n" % (name, name))

            # create template to make sure it compiles
            t = Template(open(path).read(), path)
        out.close()
                
class ParseError(Exception):
    pass
    
class SecurityError(Exception):
    """The template seems to be trying to do something naughty."""
    pass

# Enumerate all the allowed AST nodes
ALLOWED_AST_NODES = [
    "Add", "And",
#   "AssAttr",
    "AssList", "AssName", "AssTuple",
#   "Assert",
    "Assign", "AugAssign",
#   "Backquote",
    "Bitand", "Bitor", "Bitxor", "Break",
    "CallFunc","Class", "Compare", "Const", "Continue",
    "Decorators", "Dict", "Discard", "Div",
    "Ellipsis", "EmptyNode",
#   "Exec",
    "Expression", "FloorDiv", "For",
#   "From",
    "Function", 
    "GenExpr", "GenExprFor", "GenExprIf", "GenExprInner",
    "Getattr", 
#   "Global", 
    "If", "IfExp",
#   "Import",
    "Invert", "Keyword", "Lambda", "LeftShift",
    "List", "ListComp", "ListCompFor", "ListCompIf", "Mod",
    "Module",
    "Mul", "Name", "Not", "Or", "Pass", "Power",
#   "Print", "Printnl", "Raise",
    "Return", "RightShift", "Slice", "Sliceobj",
    "Stmt", "Sub", "Subscript",
#   "TryExcept", "TryFinally",
    "Tuple", "UnaryAdd", "UnarySub",
    "While", "With", "Yield",
]

class SafeVisitor(object):
    """
    Make sure code is safe by walking through the AST.
    
    Code considered unsafe if:
        * it has restricted AST nodes
        * it is trying to access resricted attributes   
        
    Adopted from http://www.zafar.se/bkz/uploads/safe.txt (public domain, Babar K. Zafar)
    """
    def __init__(self):
        "Initialize visitor by generating callbacks for all AST node types."
        self.errors = []

    def walk(self, ast, filename):
        "Validate each node in AST and raise SecurityError if the code is not safe."
        self.filename = filename
        self.visit(ast)
        
        if self.errors:        
            raise SecurityError, '\n'.join([str(err) for err in self.errors])
        
    def visit(self, node, *args):
        "Recursively validate node and all of its children."
        def classname(obj):
            return obj.__class__.__name__
        nodename = classname(node)
        fn = getattr(self, 'visit' + nodename, None)
        
        if fn:
            fn(node, *args)
        else:
            if nodename not in ALLOWED_AST_NODES:
                self.fail(node, *args)
            
        for child in node.getChildNodes():
            self.visit(child, *args)

    def visitName(self, node, *args):
        "Disallow any attempts to access a restricted attr."
        #self.assert_attr(node.getChildren()[0], node)
        pass
        
    def visitGetattr(self, node, *args):
        "Disallow any attempts to access a restricted attribute."
        self.assert_attr(node.attrname, node)
            
    def assert_attr(self, attrname, node):
        if self.is_unallowed_attr(attrname):
            lineno = self.get_node_lineno(node)
            e = SecurityError("%s:%d - access to attribute '%s' is denied" % (self.filename, lineno, attrname))
            self.errors.append(e)

    def is_unallowed_attr(self, name):
        return name.startswith('_') \
            or name.startswith('func_') \
            or name.startswith('im_')
            
    def get_node_lineno(self, node):
        return (node.lineno) and node.lineno or 0
        
    def fail(self, node, *args):
        "Default callback for unallowed AST nodes."
        lineno = self.get_node_lineno(node)
        nodename = node.__class__.__name__
        e = SecurityError("%s:%d - execution of '%s' statements is denied" % (self.filename, lineno, nodename))
        self.errors.append(e)

class TemplateResult(object, DictMixin):
    """Dictionary like object for storing template output.
    
    The result of a template execution is usally a string, but sometimes it
    contains attributes set using $var. This class provides a simple
    dictionary like interface for storing the output of the template and the
    attributes. The output is stored with a special key __body__. Convering
    the the TemplateResult to string or unicode returns the value of __body__.
    
    When the template is in execution, the output is generated part by part
    and those parts are combined at the end. Parts are added to the
    TemplateResult by calling the `extend` method and the parts are combined
    seemlessly when __body__ is accessed.
    
        >>> d = TemplateResult(__body__='hello, world', x='foo')
        >>> d
        <TemplateResult: {'__body__': 'hello, world', 'x': 'foo'}>
        >>> print d
        hello, world
        >>> d.x
        'foo'
        >>> d = TemplateResult()
        >>> d.extend([u'hello', u'world'])
        >>> d
        <TemplateResult: {'__body__': u'helloworld'}>
    """
    def __init__(self, *a, **kw):
        self.__dict__["_d"] = dict(*a, **kw)
        self._d.setdefault("__body__", u'')
        
        self.__dict__['_parts'] = []
        self.__dict__["extend"] = self._parts.extend
        
        self._d.setdefault("__body__", None)
    
    def keys(self):
        return self._d.keys()
        
    def _prepare_body(self):
        """Prepare value of __body__ by joining parts.
        """
        if self._parts:
            value = u"".join(self._parts)
            self._parts[:] = []
            body = self._d.get('__body__')
            if body:
                self._d['__body__'] = body + value
            else:
                self._d['__body__'] = value
                
    def __getitem__(self, name):
        if name == "__body__":
            self._prepare_body()
        return self._d[name]
        
    def __setitem__(self, name, value):
        if name == "__body__":
            self._prepare_body()
        return self._d.__setitem__(name, value)
        
    def __delitem__(self, name):
        if name == "__body__":
            self._prepare_body()
        return self._d.__delitem__(name)

    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value): 
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
        
    def __unicode__(self):
        self._prepare_body()
        return self["__body__"]
    
    def __str__(self):
        self._prepare_body()
        return self["__body__"].encode('utf-8')
        
    def __repr__(self):
        self._prepare_body()
        return "<TemplateResult: %s>" % self._d

def test():
    r"""Doctest for testing template module.

    Define a utility function to run template test.
    
        >>> class TestResult:
        ...     def __init__(self, t): self.t = t
        ...     def __getattr__(self, name): return getattr(self.t, name)
        ...     def __repr__(self): return repr(unicode(self))
        ...
        >>> def t(code, **keywords):
        ...     tmpl = Template(code, **keywords)
        ...     return lambda *a, **kw: TestResult(tmpl(*a, **kw))
        ...
    
    Simple tests.
    
        >>> t('1')()
        u'1\n'
        >>> t('$def with ()\n1')()
        u'1\n'
        >>> t('$def with (a)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(1)
        u'1\n'
        >>> t('$def with (a=0)\n$a')(a=1)
        u'1\n'
    
    Test complicated expressions.
        
        >>> t('$def with (x)\n$x.upper()')('hello')
        u'HELLO\n'
        >>> t('$(2 * 3 + 4 * 5)')()
        u'26\n'
        >>> t('${2 * 3 + 4 * 5}')()
        u'26\n'
        >>> t('$def with (limit)\nkeep $(limit)ing.')('go')
        u'keep going.\n'
        >>> t('$def with (a)\n$a.b[0]')(storage(b=[1]))
        u'1\n'
        
    Test html escaping.
    
        >>> t('$def with (x)\n$x', filename='a.html')('<html>')
        u'&lt;html&gt;\n'
        >>> t('$def with (x)\n$x', filename='a.txt')('<html>')
        u'<html>\n'
                
    Test if, for and while.
    
        >>> t('$if 1: 1')()
        u'1\n'
        >>> t('$if 1:\n    1')()
        u'1\n'
        >>> t('$if 1:\n    1\\')()
        u'1'
        >>> t('$if 0: 0\n$elif 1: 1')()
        u'1\n'
        >>> t('$if 0: 0\n$elif None: 0\n$else: 1')()
        u'1\n'
        >>> t('$if 0 < 1 and 1 < 2: 1')()
        u'1\n'
        >>> t('$for x in [1, 2, 3]: $x')()
        u'1\n2\n3\n'
        >>> t('$def with (d)\n$for k, v in d.iteritems(): $k')({1: 1})
        u'1\n'
        >>> t('$for x in [1, 2, 3]:\n\t$x')()
        u'    1\n    2\n    3\n'
        >>> t('$def with (a)\n$while a and a.pop():1')([1, 2, 3])
        u'1\n1\n1\n'

    The space after : must be ignored.
    
        >>> t('$if True: foo')()
        u'foo\n'
    
    Test loop.xxx.

        >>> t("$for i in range(5):$loop.index, $loop.parity")()
        u'1, odd\n2, even\n3, odd\n4, even\n5, odd\n'
        >>> t("$for i in range(2):\n    $for j in range(2):$loop.parent.parity $loop.parity")()
        u'odd odd\nodd even\neven odd\neven even\n'
        
    Test assignment.
    
        >>> t('$ a = 1\n$a')()
        u'1\n'
        >>> t('$ a = [1]\n$a[0]')()
        u'1\n'
        >>> t('$ a = {1: 1}\n$a.keys()[0]')()
        u'1\n'
        >>> t('$ a = []\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = {}\n$if not a: 1')()
        u'1\n'
        >>> t('$ a = -1\n$a')()
        u'-1\n'
        >>> t('$ a = "1"\n$a')()
        u'1\n'

    Test comments.
    
        >>> t('$# 0')()
        u'\n'
        >>> t('hello$#comment1\nhello$#comment2')()
        u'hello\nhello\n'
        >>> t('$#comment0\nhello$#comment1\nhello$#comment2')()
        u'\nhello\nhello\n'
        
    Test unicode.
    
        >>> t('$def with (a)\n$a')(u'\u203d')
        u'\u203d\n'
        >>> t('$def with (a)\n$a')(u'\u203d'.encode('utf-8'))
        u'\u203d\n'
        >>> t(u'$def with (a)\n$a $:a')(u'\u203d')
        u'\u203d \u203d\n'
        >>> t(u'$def with ()\nfoo')()
        u'foo\n'
        >>> def f(x): return x
        ...
        >>> t(u'$def with (f)\n$:f("x")')(f)
        u'x\n'
        >>> t('$def with (f)\n$:f("x")')(f)
        u'x\n'
    
    Test dollar escaping.
    
        >>> t("Stop, $$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        >>> t("Stop, \$money isn't evaluated.")()
        u"Stop, $money isn't evaluated.\n"
        
    Test space sensitivity.
    
        >>> t('$def with (x)\n$x')(1)
        u'1\n'
        >>> t('$def with(x ,y)\n$x')(1, 1)
        u'1\n'
        >>> t('$(1 + 2*3 + 4)')()
        u'11\n'
        
    Make sure globals are working.
            
        >>> t('$x')()
        Traceback (most recent call last):
            ...
        NameError: global name 'x' is not defined
        >>> t('$x', globals={'x': 1})()
        u'1\n'
        
    Can't change globals.
    
        >>> t('$ x = 2\n$x', globals={'x': 1})()
        u'2\n'
        >>> t('$ x = x + 1\n$x', globals={'x': 1})()
        Traceback (most recent call last):
            ...
        UnboundLocalError: local variable 'x' referenced before assignment
    
    Make sure builtins are customizable.
    
        >>> t('$min(1, 2)')()
        u'1\n'
        >>> t('$min(1, 2)', builtins={})()
        Traceback (most recent call last):
            ...
        NameError: global name 'min' is not defined
        
    Test vars.
    
        >>> x = t('$var x: 1')()
        >>> x.x
        u'1'
        >>> x = t('$var x = 1')()
        >>> x.x
        1
        >>> x = t('$var x:  \n    foo\n    bar')()
        >>> x.x
        u'foo\nbar\n'

    Test BOM chars.

        >>> t('\xef\xbb\xbf$def with(x)\n$x')('foo')
        u'foo\n'

    Test for with weird cases.

        >>> t('$for i in range(10)[1:5]:\n    $i')()
        u'1\n2\n3\n4\n'
        >>> t("$for k, v in {'a': 1, 'b': 2}.items():\n    $k $v")()
        u'a 1\nb 2\n'
        >>> t("$for k, v in ({'a': 1, 'b': 2}.items():\n    $k $v")()
        Traceback (most recent call last):
            ...
        SyntaxError: invalid syntax

    Test datetime.

        >>> import datetime
        >>> t("$def with (date)\n$date.strftime('%m %Y')")(datetime.datetime(2009, 1, 1))
        u'01 2009\n'
    """
    pass
            
if __name__ == "__main__":
    import sys
    if '--compile' in sys.argv:
        compile_templates(sys.argv[2])
    else:
        import doctest
        doctest.testmod()

########NEW FILE########
__FILENAME__ = test
"""test utilities
(part of web.py)
"""
import unittest
import sys, os
import web

TestCase = unittest.TestCase
TestSuite = unittest.TestSuite

def load_modules(names):
    return [__import__(name, None, None, "x") for name in names]

def module_suite(module, classnames=None):
    """Makes a suite from a module."""
    if classnames:
        return unittest.TestLoader().loadTestsFromNames(classnames, module)
    elif hasattr(module, 'suite'):
        return module.suite()
    else:
        return unittest.TestLoader().loadTestsFromModule(module)

def doctest_suite(module_names):
    """Makes a test suite from doctests."""
    import doctest
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(doctest.DocTestSuite(mod))
    return suite
    
def suite(module_names):
    """Creates a suite from multiple modules."""
    suite = TestSuite()
    for mod in load_modules(module_names):
        suite.addTest(module_suite(mod))
    return suite

def runTests(suite):
    runner = unittest.TextTestRunner()
    return runner.run(suite)

def main(suite=None):
    if not suite:
        main_module = __import__('__main__')
        # allow command line switches
        args = [a for a in sys.argv[1:] if not a.startswith('-')]
        suite = module_suite(main_module, args or None)

    result = runTests(suite)
    sys.exit(not result.wasSuccessful())


########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
"""
General Utilities
(part of web.py)
"""

__all__ = [
  "Storage", "storage", "storify", 
  "Counter", "counter",
  "iters", 
  "rstrips", "lstrips", "strips", 
  "safeunicode", "safestr", "utf8",
  "TimeoutError", "timelimit",
  "Memoize", "memoize",
  "re_compile", "re_subm",
  "group", "uniq", "iterview",
  "IterBetter", "iterbetter",
  "safeiter", "safewrite",
  "dictreverse", "dictfind", "dictfindall", "dictincr", "dictadd",
  "requeue", "restack",
  "listget", "intget", "datestr",
  "numify", "denumify", "commify", "dateify",
  "nthstr", "cond",
  "CaptureStdout", "capturestdout", "Profile", "profile",
  "tryall",
  "ThreadedDict", "threadeddict",
  "autoassign",
  "to36",
  "safemarkdown",
  "sendmail"
]

import re, sys, time, threading, itertools, traceback, os

try:
    import subprocess
except ImportError: 
    subprocess = None

try: import datetime
except ImportError: pass

try: set
except NameError:
    from sets import Set as set
    
try:
    from threading import local as threadlocal
except ImportError:
    from python23 import threadlocal

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.
    
        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'
    
    """
    def __getattr__(self, key): 
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __setattr__(self, key, value): 
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k
    
    def __repr__(self):     
        return '<Storage ' + dict.__repr__(self) + '>'

storage = Storage

def storify(mapping, *requireds, **defaults):
    """
    Creates a `storage` object from dictionary `mapping`, raising `KeyError` if
    d doesn't have all of the keys in `requireds` and using the default 
    values for keys found in `defaults`.

    For example, `storify({'a':1, 'c':3}, b=2, c=0)` will return the equivalent of
    `storage({'a':1, 'b':2, 'c':3})`.
    
    If a `storify` value is a list (e.g. multiple values in a form submission), 
    `storify` returns the last element of the list, unless the key appears in 
    `defaults` as a list. Thus:
    
        >>> storify({'a':[1, 2]}).a
        2
        >>> storify({'a':[1, 2]}, a=[]).a
        [1, 2]
        >>> storify({'a':1}, a=[]).a
        [1]
        >>> storify({}, a=[]).a
        []
    
    Similarly, if the value has a `value` attribute, `storify will return _its_
    value, unless the key appears in `defaults` as a dictionary.
    
        >>> storify({'a':storage(value=1)}).a
        1
        >>> storify({'a':storage(value=1)}, a={}).a
        <Storage {'value': 1}>
        >>> storify({}, a={}).a
        {}
        
    Optionally, keyword parameter `_unicode` can be passed to convert all values to unicode.
    
        >>> storify({'x': 'a'}, _unicode=True)
        <Storage {'x': u'a'}>
        >>> storify({'x': storage(value='a')}, x={}, _unicode=True)
        <Storage {'x': <Storage {'value': 'a'}>}>
        >>> storify({'x': storage(value='a')}, _unicode=True)
        <Storage {'x': u'a'}>
    """
    _unicode = defaults.pop('_unicode', False)
    def unicodify(s):
        if _unicode and isinstance(s, str): return safeunicode(s)
        else: return s
        
    def getvalue(x):
        if hasattr(x, 'file') and hasattr(x, 'value'):
            return x.value
        elif hasattr(x, 'value'):
            return unicodify(x.value)
        else:
            return unicodify(x)
    
    stor = Storage()
    for key in requireds + tuple(mapping.keys()):
        value = mapping[key]
        if isinstance(value, list):
            if isinstance(defaults.get(key), list):
                value = [getvalue(x) for x in value]
            else:
                value = value[-1]
        if not isinstance(defaults.get(key), dict):
            value = getvalue(value)
        if isinstance(defaults.get(key), list) and not isinstance(value, list):
            value = [value]
        setattr(stor, key, value)

    for (key, value) in defaults.iteritems():
        result = value
        if hasattr(stor, key): 
            result = stor[key]
        if value == () and not isinstance(result, tuple): 
            result = (result,)
        setattr(stor, key, result)
    
    return stor

class Counter(storage):
    """Keeps count of how many times something is added.
        
        >>> c = counter()
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('x')
        >>> c.add('y')
        >>> c
        <Counter {'y': 1, 'x': 5}>
        >>> c.most()
        ['x']
    """
    def add(self, n):
        self.setdefault(n, 0)
        self[n] += 1
    
    def most(self):
        """Returns the keys with maximum count."""
        m = max(self.itervalues())
        return [k for k, v in self.iteritems() if v == m]
        
    def least(self):
        """Returns the keys with mininum count."""
        m = min(self.itervalues())
        return [k for k, v in self.iteritems() if v == m]

    def percent(self, key):
       """Returns what percentage a certain key is of all entries.

           >>> c = counter()
           >>> c.add('x')
           >>> c.add('x')
           >>> c.add('x')
           >>> c.add('y')
           >>> c.percent('x')
           0.75
           >>> c.percent('y')
           0.25
       """
       return float(self[key])/sum(self.values())
             
    def sorted_keys(self):
        """Returns keys sorted by value.
             
             >>> c = counter()
             >>> c.add('x')
             >>> c.add('x')
             >>> c.add('y')
             >>> c.sorted_keys()
             ['x', 'y']
        """
        return sorted(self.keys(), key=lambda k: self[k], reverse=True)
    
    def sorted_values(self):
        """Returns values sorted by value.
            
            >>> c = counter()
            >>> c.add('x')
            >>> c.add('x')
            >>> c.add('y')
            >>> c.sorted_values()
            [2, 1]
        """
        return [self[k] for k in self.sorted_keys()]
    
    def sorted_items(self):
        """Returns items sorted by value.
            
            >>> c = counter()
            >>> c.add('x')
            >>> c.add('x')
            >>> c.add('y')
            >>> c.sorted_items()
            [('x', 2), ('y', 1)]
        """
        return [(k, self[k]) for k in self.sorted_keys()]
    
    def __repr__(self):
        return '<Counter ' + dict.__repr__(self) + '>'
       
counter = Counter

iters = [list, tuple]
import __builtin__
if hasattr(__builtin__, 'set'):
    iters.append(set)
if hasattr(__builtin__, 'frozenset'):
    iters.append(set)
if sys.version_info < (2,6): # sets module deprecated in 2.6
    try:
        from sets import Set
        iters.append(Set)
    except ImportError: 
        pass
    
class _hack(tuple): pass
iters = _hack(iters)
iters.__doc__ = """
A list of iterable items (like lists, but not strings). Includes whichever
of lists, tuples, sets, and Sets are available in this version of Python.
"""

def _strips(direction, text, remove):
    if isinstance(remove, iters):
        for subr in remove:
            text = _strips(direction, text, subr)
        return text
    
    if direction == 'l': 
        if text.startswith(remove): 
            return text[len(remove):]
    elif direction == 'r':
        if text.endswith(remove):   
            return text[:-len(remove)]
    else: 
        raise ValueError, "Direction needs to be r or l."
    return text

def rstrips(text, remove):
    """
    removes the string `remove` from the right of `text`

        >>> rstrips("foobar", "bar")
        'foo'
    
    """
    return _strips('r', text, remove)

def lstrips(text, remove):
    """
    removes the string `remove` from the left of `text`
    
        >>> lstrips("foobar", "foo")
        'bar'
        >>> lstrips('http://foo.org/', ['http://', 'https://'])
        'foo.org/'
        >>> lstrips('FOOBARBAZ', ['FOO', 'BAR'])
        'BAZ'
        >>> lstrips('FOOBARBAZ', ['BAR', 'FOO'])
        'BARBAZ'
    
    """
    return _strips('l', text, remove)

def strips(text, remove):
    """
    removes the string `remove` from the both sides of `text`

        >>> strips("foobarfoo", "foo")
        'bar'
    
    """
    return rstrips(lstrips(text, remove), remove)

def safeunicode(obj, encoding='utf-8'):
    r"""
    Converts any given object to unicode string.
    
        >>> safeunicode('hello')
        u'hello'
        >>> safeunicode(2)
        u'2'
        >>> safeunicode('\xe1\x88\xb4')
        u'\u1234'
    """
    t = type(obj)
    if t is unicode:
        return obj
    elif t is str:
        return obj.decode(encoding)
    elif t in [int, float, bool]:
        return unicode(obj)
    elif hasattr(obj, '__unicode__') or isinstance(obj, unicode):
        return unicode(obj)
    else:
        return str(obj).decode(encoding)
    
def safestr(obj, encoding='utf-8'):
    r"""
    Converts any given object to utf-8 encoded string. 
    
        >>> safestr('hello')
        'hello'
        >>> safestr(u'\u1234')
        '\xe1\x88\xb4'
        >>> safestr(2)
        '2'
    """
    if isinstance(obj, unicode):
        return obj.encode(encoding)
    elif isinstance(obj, str):
        return obj
    elif hasattr(obj, 'next'): # iterator
        return itertools.imap(safestr, obj)
    else:
        return str(obj)

# for backward-compatibility
utf8 = safestr
    
class TimeoutError(Exception): pass
def timelimit(timeout):
    """
    A decorator to limit a function to `timeout` seconds, raising `TimeoutError`
    if it takes longer.
    
        >>> import time
        >>> def meaningoflife():
        ...     time.sleep(.2)
        ...     return 42
        >>> 
        >>> timelimit(.1)(meaningoflife)()
        Traceback (most recent call last):
            ...
        TimeoutError: took too long
        >>> timelimit(1)(meaningoflife)()
        42

    _Caveat:_ The function isn't stopped after `timeout` seconds but continues 
    executing in a separate thread. (There seems to be no way to kill a thread.)

    inspired by <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/473878>
    """
    def _1(function):
        def _2(*args, **kw):
            class Dispatch(threading.Thread):
                def __init__(self):
                    threading.Thread.__init__(self)
                    self.result = None
                    self.error = None

                    self.setDaemon(True)
                    self.start()

                def run(self):
                    try:
                        self.result = function(*args, **kw)
                    except:
                        self.error = sys.exc_info()

            c = Dispatch()
            c.join(timeout)
            if c.isAlive():
                raise TimeoutError, 'took too long'
            if c.error:
                raise c.error[0], c.error[1]
            return c.result
        return _2
    return _1

class Memoize:
    """
    'Memoizes' a function, caching its return values for each input.
    If `expires` is specified, values are recalculated after `expires` seconds.
    If `background` is specified, values are recalculated in a separate thread.
    
        >>> calls = 0
        >>> def howmanytimeshaveibeencalled():
        ...     global calls
        ...     calls += 1
        ...     return calls
        >>> fastcalls = memoize(howmanytimeshaveibeencalled)
        >>> howmanytimeshaveibeencalled()
        1
        >>> howmanytimeshaveibeencalled()
        2
        >>> fastcalls()
        3
        >>> fastcalls()
        3
        >>> import time
        >>> fastcalls = memoize(howmanytimeshaveibeencalled, .1, background=False)
        >>> fastcalls()
        4
        >>> fastcalls()
        4
        >>> time.sleep(.2)
        >>> fastcalls()
        5
        >>> def slowfunc():
        ...     time.sleep(.1)
        ...     return howmanytimeshaveibeencalled()
        >>> fastcalls = memoize(slowfunc, .2, background=True)
        >>> fastcalls()
        6
        >>> timelimit(.05)(fastcalls)()
        6
        >>> time.sleep(.2)
        >>> timelimit(.05)(fastcalls)()
        6
        >>> timelimit(.05)(fastcalls)()
        6
        >>> time.sleep(.2)
        >>> timelimit(.05)(fastcalls)()
        7
        >>> fastcalls = memoize(slowfunc, None, background=True)
        >>> threading.Thread(target=fastcalls).start()
        >>> time.sleep(.01)
        >>> fastcalls()
        9
    """
    def __init__(self, func, expires=None, background=True): 
        self.func = func
        self.cache = {}
        self.expires = expires
        self.background = background
        self.running = {}
    
    def __call__(self, *args, **keywords):
        key = (args, tuple(keywords.items()))
        if not self.running.get(key):
            self.running[key] = threading.Lock()
        def update(block=False):
            if self.running[key].acquire(block):
                try:
                    self.cache[key] = (self.func(*args, **keywords), time.time())
                finally:
                    self.running[key].release()
        
        if key not in self.cache: 
            update(block=True)
        elif self.expires and (time.time() - self.cache[key][1]) > self.expires:
            if self.background:
                threading.Thread(target=update).start()
            else:
                update()
        return self.cache[key][0]

memoize = Memoize

re_compile = memoize(re.compile) #@@ threadsafe?
re_compile.__doc__ = """
A memoized version of re.compile.
"""

class _re_subm_proxy:
    def __init__(self): 
        self.match = None
    def __call__(self, match): 
        self.match = match
        return ''

def re_subm(pat, repl, string):
    """
    Like re.sub, but returns the replacement _and_ the match object.
    
        >>> t, m = re_subm('g(oo+)fball', r'f\\1lish', 'goooooofball')
        >>> t
        'foooooolish'
        >>> m.groups()
        ('oooooo',)
    """
    compiled_pat = re_compile(pat)
    proxy = _re_subm_proxy()
    compiled_pat.sub(proxy.__call__, string)
    return compiled_pat.sub(repl, string), proxy.match

def group(seq, size): 
    """
    Returns an iterator over a series of lists of length size from iterable.

        >>> list(group([1,2,3,4], 2))
        [[1, 2], [3, 4]]
        >>> list(group([1,2,3,4,5], 2))
        [[1, 2], [3, 4], [5]]
    """
    def take(seq, n):
        for i in xrange(n):
            yield seq.next()

    if not hasattr(seq, 'next'):  
        seq = iter(seq)
    while True: 
        x = list(take(seq, size))
        if x:
            yield x
        else:
            break

def uniq(seq, key=None):
    """
    Removes duplicate elements from a list while preserving the order of the rest.

        >>> uniq([9,0,2,1,0])
        [9, 0, 2, 1]

    The value of the optional `key` parameter should be a function that
    takes a single argument and returns a key to test the uniqueness.

        >>> uniq(["Foo", "foo", "bar"], key=lambda s: s.lower())
        ['Foo', 'bar']
    """
    key = key or (lambda x: x)
    seen = set()
    result = []
    for v in seq:
        k = key(v)
        if k in seen:
            continue
        seen.add(k)
        result.append(v)
    return result

def iterview(x):
   """
   Takes an iterable `x` and returns an iterator over it
   which prints its progress to stderr as it iterates through.
   """
   WIDTH = 70

   def plainformat(n, lenx):
       return '%5.1f%% (%*d/%d)' % ((float(n)/lenx)*100, len(str(lenx)), n, lenx)

   def bars(size, n, lenx):
       val = int((float(n)*size)/lenx + 0.5)
       if size - val:
           spacing = ">" + (" "*(size-val))[1:]
       else:
           spacing = ""
       return "[%s%s]" % ("="*val, spacing)

   def eta(elapsed, n, lenx):
       if n == 0:
           return '--:--:--'
       if n == lenx:
           secs = int(elapsed)
       else:
           secs = int((elapsed/n) * (lenx-n))
       mins, secs = divmod(secs, 60)
       hrs, mins = divmod(mins, 60)

       return '%02d:%02d:%02d' % (hrs, mins, secs)

   def format(starttime, n, lenx):
       out = plainformat(n, lenx) + ' '
       if n == lenx:
           end = '     '
       else:
           end = ' ETA '
       end += eta(time.time() - starttime, n, lenx)
       out += bars(WIDTH - len(out) - len(end), n, lenx)
       out += end
       return out

   starttime = time.time()
   lenx = len(x)
   for n, y in enumerate(x):
       sys.stderr.write('\r' + format(starttime, n, lenx))
       yield y
   sys.stderr.write('\r' + format(starttime, n+1, lenx) + '\n')

class IterBetter:
    """
    Returns an object that can be used as an iterator 
    but can also be used via __getitem__ (although it 
    cannot go backwards -- that is, you cannot request 
    `iterbetter[0]` after requesting `iterbetter[1]`).
    
        >>> import itertools
        >>> c = iterbetter(itertools.count())
        >>> c[1]
        1
        >>> c[5]
        5
        >>> c[3]
        Traceback (most recent call last):
            ...
        IndexError: already passed 3

    For boolean test, IterBetter peeps at first value in the itertor without effecting the iteration.

        >>> c = iterbetter(iter(range(5)))
        >>> bool(c)
        True
        >>> list(c)
        [0, 1, 2, 3, 4]
        >>> c = iterbetter(iter([]))
        >>> bool(c)
        False
        >>> list(c)
        []
    """
    def __init__(self, iterator): 
        self.i, self.c = iterator, 0

    def __iter__(self): 
        if hasattr(self, "_head"):
            yield self._head

        while 1:    
            yield self.i.next()
            self.c += 1

    def __getitem__(self, i):
        #todo: slices
        if i < self.c: 
            raise IndexError, "already passed "+str(i)
        try:
            while i > self.c: 
                self.i.next()
                self.c += 1
            # now self.c == i
            self.c += 1
            return self.i.next()
        except StopIteration: 
            raise IndexError, str(i)
            
    def __nonzero__(self):
        if hasattr(self, "__len__"):
            return len(self) != 0
        elif hasattr(self, "_head"):
            return True
        else:
            try:
                self._head = self.i.next()
            except StopIteration:
                return False
            else:
                return True

iterbetter = IterBetter

def safeiter(it, cleanup=None, ignore_errors=True):
    """Makes an iterator safe by ignoring the exceptions occured during the iteration.
    """
    def next():
        while True:
            try:
                return it.next()
            except StopIteration:
                raise
            except:
                traceback.print_exc()

    it = iter(it)
    while True:
        yield next()

def safewrite(filename, content):
    """Writes the content to a temp file and then moves the temp file to 
    given filename to avoid overwriting the existing file in case of errors.
    """
    f = file(filename + '.tmp', 'w')
    f.write(content)
    f.close()
    os.rename(f.name, filename)

def dictreverse(mapping):
    """
    Returns a new dictionary with keys and values swapped.
    
        >>> dictreverse({1: 2, 3: 4})
        {2: 1, 4: 3}
    """
    return dict([(value, key) for (key, value) in mapping.iteritems()])

def dictfind(dictionary, element):
    """
    Returns a key whose value in `dictionary` is `element` 
    or, if none exists, None.
    
        >>> d = {1:2, 3:4}
        >>> dictfind(d, 4)
        3
        >>> dictfind(d, 5)
    """
    for (key, value) in dictionary.iteritems():
        if element is value: 
            return key

def dictfindall(dictionary, element):
    """
    Returns the keys whose values in `dictionary` are `element`
    or, if none exists, [].
    
        >>> d = {1:4, 3:4}
        >>> dictfindall(d, 4)
        [1, 3]
        >>> dictfindall(d, 5)
        []
    """
    res = []
    for (key, value) in dictionary.iteritems():
        if element is value:
            res.append(key)
    return res

def dictincr(dictionary, element):
    """
    Increments `element` in `dictionary`, 
    setting it to one if it doesn't exist.
    
        >>> d = {1:2, 3:4}
        >>> dictincr(d, 1)
        3
        >>> d[1]
        3
        >>> dictincr(d, 5)
        1
        >>> d[5]
        1
    """
    dictionary.setdefault(element, 0)
    dictionary[element] += 1
    return dictionary[element]

def dictadd(*dicts):
    """
    Returns a dictionary consisting of the keys in the argument dictionaries.
    If they share a key, the value from the last argument is used.
    
        >>> dictadd({1: 0, 2: 0}, {2: 1, 3: 1})
        {1: 0, 2: 1, 3: 1}
    """
    result = {}
    for dct in dicts:
        result.update(dct)
    return result

def requeue(queue, index=-1):
    """Returns the element at index after moving it to the beginning of the queue.

        >>> x = [1, 2, 3, 4]
        >>> requeue(x)
        4
        >>> x
        [4, 1, 2, 3]
    """
    x = queue.pop(index)
    queue.insert(0, x)
    return x

def restack(stack, index=0):
    """Returns the element at index after moving it to the top of stack.

           >>> x = [1, 2, 3, 4]
           >>> restack(x)
           1
           >>> x
           [2, 3, 4, 1]
    """
    x = stack.pop(index)
    stack.append(x)
    return x

def listget(lst, ind, default=None):
    """
    Returns `lst[ind]` if it exists, `default` otherwise.
    
        >>> listget(['a'], 0)
        'a'
        >>> listget(['a'], 1)
        >>> listget(['a'], 1, 'b')
        'b'
    """
    if len(lst)-1 < ind: 
        return default
    return lst[ind]

def intget(integer, default=None):
    """
    Returns `integer` as an int or `default` if it can't.
    
        >>> intget('3')
        3
        >>> intget('3a')
        >>> intget('3a', 0)
        0
    """
    try:
        return int(integer)
    except (TypeError, ValueError):
        return default

def datestr(then, now=None):
    """
    Converts a (UTC) datetime object to a nice string representation.
    
        >>> from datetime import datetime, timedelta
        >>> d = datetime(1970, 5, 1)
        >>> datestr(d, now=d)
        '0 microseconds ago'
        >>> for t, v in {
        ...   timedelta(microseconds=1): '1 microsecond ago',
        ...   timedelta(microseconds=2): '2 microseconds ago',
        ...   -timedelta(microseconds=1): '1 microsecond from now',
        ...   -timedelta(microseconds=2): '2 microseconds from now',
        ...   timedelta(microseconds=2000): '2 milliseconds ago',
        ...   timedelta(seconds=2): '2 seconds ago',
        ...   timedelta(seconds=2*60): '2 minutes ago',
        ...   timedelta(seconds=2*60*60): '2 hours ago',
        ...   timedelta(days=2): '2 days ago',
        ... }.iteritems():
        ...     assert datestr(d, now=d+t) == v
        >>> datestr(datetime(1970, 1, 1), now=d)
        'January  1'
        >>> datestr(datetime(1969, 1, 1), now=d)
        'January  1, 1969'
        >>> datestr(datetime(1970, 6, 1), now=d)
        'June  1, 1970'
        >>> datestr(None)
        ''
    """
    def agohence(n, what, divisor=None):
        if divisor: n = n // divisor

        out = str(abs(n)) + ' ' + what       # '2 day'
        if abs(n) != 1: out += 's'           # '2 days'
        out += ' '                           # '2 days '
        if n < 0:
            out += 'from now'
        else:
            out += 'ago'
        return out                           # '2 days ago'

    oneday = 24 * 60 * 60

    if not then: return ""
    if not now: now = datetime.datetime.utcnow()
    if type(now).__name__ == "DateTime":
        now = datetime.datetime.fromtimestamp(now)
    if type(then).__name__ == "DateTime":
        then = datetime.datetime.fromtimestamp(then)
    elif type(then).__name__ == "date":
        then = datetime.datetime(then.year, then.month, then.day)

    delta = now - then
    deltaseconds = int(delta.days * oneday + delta.seconds + delta.microseconds * 1e-06)
    deltadays = abs(deltaseconds) // oneday
    if deltaseconds < 0: deltadays *= -1 # fix for oddity of floor

    if deltadays:
        if abs(deltadays) < 4:
            return agohence(deltadays, 'day')

        out = then.strftime('%B %e') # e.g. 'June 13'
        if then.year != now.year or deltadays < 0:
            out += ', %s' % then.year
        return out

    if int(deltaseconds):
        if abs(deltaseconds) > (60 * 60):
            return agohence(deltaseconds, 'hour', 60 * 60)
        elif abs(deltaseconds) > 60:
            return agohence(deltaseconds, 'minute', 60)
        else:
            return agohence(deltaseconds, 'second')

    deltamicroseconds = delta.microseconds
    if delta.days: deltamicroseconds = int(delta.microseconds - 1e6) # datetime oddity
    if abs(deltamicroseconds) > 1000:
        return agohence(deltamicroseconds, 'millisecond', 1000)

    return agohence(deltamicroseconds, 'microsecond')

def numify(string):
    """
    Removes all non-digit characters from `string`.
    
        >>> numify('800-555-1212')
        '8005551212'
        >>> numify('800.555.1212')
        '8005551212'
    
    """
    return ''.join([c for c in str(string) if c.isdigit()])

def denumify(string, pattern):
    """
    Formats `string` according to `pattern`, where the letter X gets replaced
    by characters from `string`.
    
        >>> denumify("8005551212", "(XXX) XXX-XXXX")
        '(800) 555-1212'
    
    """
    out = []
    for c in pattern:
        if c == "X":
            out.append(string[0])
            string = string[1:]
        else:
            out.append(c)
    return ''.join(out)

def commify(n):
    """
    Add commas to an integer `n`.

        >>> commify(1)
        '1'
        >>> commify(123)
        '123'
        >>> commify(1234)
        '1,234'
        >>> commify(1234567890)
        '1,234,567,890'
        >>> commify(123.0)
        '123.0'
        >>> commify(1234.5)
        '1,234.5'
        >>> commify(1234.56789)
        '1,234.56789'
        >>> commify('%.2f' % 1234.5)
        '1,234.50'
        >>> commify(None)
        >>>

    """
    if n is None: return None
    n = str(n)
    if '.' in n:
        dollars, cents = n.split('.')
    else:
        dollars, cents = n, None

    r = []
    for i, c in enumerate(str(dollars)[::-1]):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    out = ''.join(r)
    if cents:
        out += '.' + cents
    return out

def dateify(datestring):
    """
    Formats a numified `datestring` properly.
    """
    return denumify(datestring, "XXXX-XX-XX XX:XX:XX")


def nthstr(n):
    """
    Formats an ordinal.
    Doesn't handle negative numbers.

        >>> nthstr(1)
        '1st'
        >>> nthstr(0)
        '0th'
        >>> [nthstr(x) for x in [2, 3, 4, 5, 10, 11, 12, 13, 14, 15]]
        ['2nd', '3rd', '4th', '5th', '10th', '11th', '12th', '13th', '14th', '15th']
        >>> [nthstr(x) for x in [91, 92, 93, 94, 99, 100, 101, 102]]
        ['91st', '92nd', '93rd', '94th', '99th', '100th', '101st', '102nd']
        >>> [nthstr(x) for x in [111, 112, 113, 114, 115]]
        ['111th', '112th', '113th', '114th', '115th']

    """
    
    assert n >= 0
    if n % 100 in [11, 12, 13]: return '%sth' % n
    return {1: '%sst', 2: '%snd', 3: '%srd'}.get(n % 10, '%sth') % n

def cond(predicate, consequence, alternative=None):
    """
    Function replacement for if-else to use in expressions.
        
        >>> x = 2
        >>> cond(x % 2 == 0, "even", "odd")
        'even'
        >>> cond(x % 2 == 0, "even", "odd") + '_row'
        'even_row'
    """
    if predicate:
        return consequence
    else:
        return alternative

class CaptureStdout:
    """
    Captures everything `func` prints to stdout and returns it instead.
    
        >>> def idiot():
        ...     print "foo"
        >>> capturestdout(idiot)()
        'foo\\n'
    
    **WARNING:** Not threadsafe!
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args, **keywords):
        from cStringIO import StringIO
        # Not threadsafe!
        out = StringIO()
        oldstdout = sys.stdout
        sys.stdout = out
        try: 
            self.func(*args, **keywords)
        finally: 
            sys.stdout = oldstdout
        return out.getvalue()

capturestdout = CaptureStdout

class Profile:
    """
    Profiles `func` and returns a tuple containing its output
    and a string with human-readable profiling information.
        
        >>> import time
        >>> out, inf = profile(time.sleep)(.001)
        >>> out
        >>> inf[:10].strip()
        'took 0.0'
    """
    def __init__(self, func): 
        self.func = func
    def __call__(self, *args): ##, **kw):   kw unused
        import hotshot, hotshot.stats, os, tempfile ##, time already imported
        f, filename = tempfile.mkstemp()
        os.close(f)
        
        prof = hotshot.Profile(filename)

        stime = time.time()
        result = prof.runcall(self.func, *args)
        stime = time.time() - stime
        prof.close()

        import cStringIO
        out = cStringIO.StringIO()
        stats = hotshot.stats.load(filename)
        stats.stream = out
        stats.strip_dirs()
        stats.sort_stats('time', 'calls')
        stats.print_stats(40)
        stats.print_callers()

        x =  '\n\ntook '+ str(stime) + ' seconds\n'
        x += out.getvalue()

        # remove the tempfile
        try:
            os.remove(filename)
        except IOError:
            pass
            
        return result, x

profile = Profile


import traceback
# hack for compatibility with Python 2.3:
if not hasattr(traceback, 'format_exc'):
    from cStringIO import StringIO
    def format_exc(limit=None):
        strbuf = StringIO()
        traceback.print_exc(limit, strbuf)
        return strbuf.getvalue()
    traceback.format_exc = format_exc

def tryall(context, prefix=None):
    """
    Tries a series of functions and prints their results. 
    `context` is a dictionary mapping names to values; 
    the value will only be tried if it's callable.
    
        >>> tryall(dict(j=lambda: True))
        j: True
        ----------------------------------------
        results:
           True: 1

    For example, you might have a file `test/stuff.py` 
    with a series of functions testing various things in it. 
    At the bottom, have a line:

        if __name__ == "__main__": tryall(globals())

    Then you can run `python test/stuff.py` and get the results of 
    all the tests.
    """
    context = context.copy() # vars() would update
    results = {}
    for (key, value) in context.iteritems():
        if not hasattr(value, '__call__'): 
            continue
        if prefix and not key.startswith(prefix): 
            continue
        print key + ':',
        try:
            r = value()
            dictincr(results, r)
            print r
        except:
            print 'ERROR'
            dictincr(results, 'ERROR')
            print '   ' + '\n   '.join(traceback.format_exc().split('\n'))
        
    print '-'*40
    print 'results:'
    for (key, value) in results.iteritems():
        print ' '*2, str(key)+':', value
        
class ThreadedDict(threadlocal):
    """
    Thread local storage.
    
        >>> d = ThreadedDict()
        >>> d.x = 1
        >>> d.x
        1
        >>> import threading
        >>> def f(): d.x = 2
        ...
        >>> t = threading.Thread(target=f)
        >>> t.start()
        >>> t.join()
        >>> d.x
        1
    """
    _instances = set()
    
    def __init__(self):
        ThreadedDict._instances.add(self)
        
    def __del__(self):
        ThreadedDict._instances.remove(self)
        
    def __hash__(self):
        return id(self)
    
    def clear_all():
        """Clears all ThreadedDict instances.
        """
        for t in ThreadedDict._instances:
            t.clear()
    clear_all = staticmethod(clear_all)
    
    # Define all these methods to more or less fully emulate dict -- attribute access
    # is built into threading.local.

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __contains__(self, key):
        return key in self.__dict__

    has_key = __contains__
        
    def clear(self):
        self.__dict__.clear()

    def copy(self):
        return self.__dict__.copy()

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def items(self):
        return self.__dict__.items()

    def iteritems(self):
        return self.__dict__.iteritems()

    def keys(self):
        return self.__dict__.keys()

    def iterkeys(self):
        return self.__dict__.iterkeys()

    iter = iterkeys

    def values(self):
        return self.__dict__.values()

    def itervalues(self):
        return self.__dict__.itervalues()

    def pop(self, key, *args):
        return self.__dict__.pop(key, *args)

    def popitem(self):
        return self.__dict__.popitem()

    def setdefault(self, key, default=None):
        return self.__dict__.setdefault(key, default)

    def update(self, *args, **kwargs):
        self.__dict__.update(*args, **kwargs)

    def __repr__(self):
        return '<ThreadedDict %r>' % self.__dict__

    __str__ = __repr__
    
threadeddict = ThreadedDict

def autoassign(self, locals):
    """
    Automatically assigns local variables to `self`.
    
        >>> self = storage()
        >>> autoassign(self, dict(a=1, b=2))
        >>> self
        <Storage {'a': 1, 'b': 2}>
    
    Generally used in `__init__` methods, as in:

        def __init__(self, foo, bar, baz=1): autoassign(self, locals())
    """
    for (key, value) in locals.iteritems():
        if key == 'self': 
            continue
        setattr(self, key, value)

def to36(q):
    """
    Converts an integer to base 36 (a useful scheme for human-sayable IDs).
    
        >>> to36(35)
        'z'
        >>> to36(119292)
        '2k1o'
        >>> int(to36(939387374), 36)
        939387374
        >>> to36(0)
        '0'
        >>> to36(-393)
        Traceback (most recent call last):
            ... 
        ValueError: must supply a positive integer
    
    """
    if q < 0: raise ValueError, "must supply a positive integer"
    letters = "0123456789abcdefghijklmnopqrstuvwxyz"
    converted = []
    while q != 0:
        q, r = divmod(q, 36)
        converted.insert(0, letters[r])
    return "".join(converted) or '0'


r_url = re_compile('(?<!\()(http://(\S+))')
def safemarkdown(text):
    """
    Converts text to HTML following the rules of Markdown, but blocking any
    outside HTML input, so that only the things supported by Markdown
    can be used. Also converts raw URLs to links.

    (requires [markdown.py](http://webpy.org/markdown.py))
    """
    from markdown import markdown
    if text:
        text = text.replace('<', '&lt;')
        # TODO: automatically get page title?
        text = r_url.sub(r'<\1>', text)
        text = markdown(text)
        return text

def sendmail(from_address, to_address, subject, message, headers=None, **kw):
    """
    Sends the email message `message` with mail and envelope headers
    for from `from_address_` to `to_address` with `subject`. 
    Additional email headers can be specified with the dictionary 
    `headers.
    
    Optionally cc, bcc and attachments can be specified as keyword arguments.
    Attachments must be an iterable and each attachment can be either a 
    filename or a file object or a dictionary with filename, content and 
    optionally content_type keys.

    If `web.config.smtp_server` is set, it will send the message
    to that SMTP server. Otherwise it will look for 
    `/usr/sbin/sendmail`, the typical location for the sendmail-style
    binary. To use sendmail from a different path, set `web.config.sendmail_path`.
    """
    attachments = kw.pop("attachments", [])
    mail = _EmailMessage(from_address, to_address, subject, message, headers, **kw)

    for a in attachments:
        if isinstance(a, dict):
            mail.attach(a['filename'], a['content'], a.get('content_type'))
        elif hasattr(a, 'read'): # file
            filename = os.path.basename(getattr(a, "name", ""))
            content_type = getattr(a, 'content_type', None)
            mail.attach(filename, a.read(), content_type)
        elif isinstance(a, basestring):
            f = open(a, 'rb')
            content = f.read()
            f.close()
            filename = os.path.basename(a)
            mail.attach(filename, content, None)
        else:
            raise ValueError, "Invalid attachment: %s" % repr(a)
            
    mail.send()

class _EmailMessage:
    def __init__(self, from_address, to_address, subject, message, headers=None, **kw):
        def listify(x):
            if not isinstance(x, list):
                return [safestr(x)]
            else:
                return [safestr(a) for a in x]
    
        subject = safestr(subject)
        message = safestr(message)

        from_address = safestr(from_address)
        to_address = listify(to_address)    
        cc = listify(kw.get('cc', []))
        bcc = listify(kw.get('bcc', []))
        recipients = to_address + cc + bcc

        import email.Utils
        self.from_address = email.Utils.parseaddr(from_address)[1]
        self.recipients = [email.Utils.parseaddr(r)[1] for r in recipients]        
    
        self.headers = dictadd({
          'From': from_address,
          'To': ", ".join(to_address),
          'Subject': subject
        }, headers or {})

        if cc:
            self.headers['Cc'] = ", ".join(cc)
    
        self.message = self.new_message()
        self.message.add_header("Content-Transfer-Encoding", "7bit")
        self.message.add_header("Content-Disposition", "inline")
        self.message.add_header("MIME-Version", "1.0")
        self.message.set_payload(message, 'utf-8')
        self.multipart = False
        
    def new_message(self):
        from email.Message import Message
        return Message()
        
    def attach(self, filename, content, content_type=None):
        if not self.multipart:
            msg = self.new_message()
            msg.add_header("Content-Type", "multipart/mixed")
            msg.attach(self.message)
            self.message = msg
            self.multipart = True
                        
        import mimetypes
        try:
            from email import encoders
        except:
            from email import Encoders as encoders
            
        content_type = content_type or mimetypes.guess_type(filename)[0] or "applcation/octet-stream"
        
        msg = self.new_message()
        msg.set_payload(content)
        msg.add_header('Content-Type', content_type)
        msg.add_header('Content-Disposition', 'attachment', filename=filename)
        
        if not content_type.startswith("text/"):
            encoders.encode_base64(msg)
            
        self.message.attach(msg)

    def prepare_message(self):
        for k, v in self.headers.iteritems():
            if k.lower() == "content-type":
                self.message.set_type(v)
            else:
                self.message.add_header(k, v)

        self.headers = {}

    def send(self):
        try:
            import webapi
        except ImportError:
            webapi = Storage(config=Storage())

        self.prepare_message()
        message_text = self.message.as_string()
    
        if webapi.config.get('smtp_server'):
            server = webapi.config.get('smtp_server')
            port = webapi.config.get('smtp_port', 0)
            username = webapi.config.get('smtp_username') 
            password = webapi.config.get('smtp_password')
            debug_level = webapi.config.get('smtp_debuglevel', None)
            starttls = webapi.config.get('smtp_starttls', False)

            import smtplib
            smtpserver = smtplib.SMTP(server, port)

            if debug_level:
                smtpserver.set_debuglevel(debug_level)

            if starttls:
                smtpserver.ehlo()
                smtpserver.starttls()
                smtpserver.ehlo()

            if username and password:
                smtpserver.login(username, password)

            smtpserver.sendmail(self.from_address, self.recipients, message_text)
            smtpserver.quit()
        elif webapi.config.get('email_engine') == 'aws':
            import boto.ses
            c = boto.ses.SESConnection(
              aws_access_key_id=webapi.config.get('aws_access_key_id'),
              aws_secret_access_key=web.api.config.get('aws_secret_access_key'))
            c.send_raw_email(self.from_address, message_text, self.from_recipients)
        else:
            sendmail = webapi.config.get('sendmail_path', '/usr/sbin/sendmail')
        
            assert not self.from_address.startswith('-'), 'security'
            for r in self.recipients:
                assert not r.startswith('-'), 'security'
                
            cmd = [sendmail, '-f', self.from_address] + self.recipients

            if subprocess:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.stdin.write(message_text)
                p.stdin.close()
                p.wait()
            else:
                i, o = os.popen2(cmd)
                i.write(message)
                i.close()
                o.close()
                del i, o
                
    def __repr__(self):
        return "<EmailMessage>"
    
    def __str__(self):
        return self.message.as_string()

if __name__ == "__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = webapi
"""
Web API (wrapper around WSGI)
(from web.py)
"""

__all__ = [
    "config",
    "header", "debug",
    "input", "data",
    "setcookie", "cookies",
    "ctx", 
    "HTTPError", 

    # 200, 201, 202
    "OK", "Created", "Accepted",    
    "ok", "created", "accepted",
    
    # 301, 302, 303, 304, 307
    "Redirect", "Found", "SeeOther", "NotModified", "TempRedirect", 
    "redirect", "found", "seeother", "notmodified", "tempredirect",

    # 400, 401, 403, 404, 405, 406, 409, 410, 412
    "BadRequest", "Unauthorized", "Forbidden", "NotFound", "NoMethod", "NotAcceptable", "Conflict", "Gone", "PreconditionFailed",
    "badrequest", "unauthorized", "forbidden", "notfound", "nomethod", "notacceptable", "conflict", "gone", "preconditionfailed",

    # 500
    "InternalError", 
    "internalerror",
]

import sys, cgi, Cookie, pprint, urlparse, urllib
from utils import storage, storify, threadeddict, dictadd, intget, safestr

config = storage()
config.__doc__ = """
A configuration object for various aspects of web.py.

`debug`
   : when True, enables reloading, disabled template caching and sets internalerror to debugerror.
"""

class HTTPError(Exception):
    def __init__(self, status, headers={}, data=""):
        ctx.status = status
        for k, v in headers.items():
            header(k, v)
        self.data = data
        Exception.__init__(self, status)
        
def _status_code(status, data=None, classname=None, docstring=None):
    if data is None:
        data = status.split(" ", 1)[1]
    classname = status.split(" ", 1)[1].replace(' ', '') # 304 Not Modified -> NotModified    
    docstring = docstring or '`%s` status' % status

    def __init__(self, data=data, headers={}):
        HTTPError.__init__(self, status, headers, data)
        
    # trick to create class dynamically with dynamic docstring.
    return type(classname, (HTTPError, object), {
        '__doc__': docstring,
        '__init__': __init__
    })

ok = OK = _status_code("200 OK", data="")
created = Created = _status_code("201 Created")
accepted = Accepted = _status_code("202 Accepted")

class Redirect(HTTPError):
    """A `301 Moved Permanently` redirect."""
    def __init__(self, url, status='301 Moved Permanently', absolute=False):
        """
        Returns a `status` redirect to the new URL. 
        `url` is joined with the base URL so that things like 
        `redirect("about") will work properly.
        """
        newloc = urlparse.urljoin(ctx.path, url)

        if newloc.startswith('/'):
            if absolute:
                home = ctx.realhome
            else:
                home = ctx.home
            newloc = home + newloc

        headers = {
            'Content-Type': 'text/html',
            'Location': newloc
        }
        HTTPError.__init__(self, status, headers, "")

redirect = Redirect

class Found(Redirect):
    """A `302 Found` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '302 Found', absolute=absolute)

found = Found

class SeeOther(Redirect):
    """A `303 See Other` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '303 See Other', absolute=absolute)
    
seeother = SeeOther

class NotModified(HTTPError):
    """A `304 Not Modified` status."""
    def __init__(self):
        HTTPError.__init__(self, "304 Not Modified")

notmodified = NotModified

class TempRedirect(Redirect):
    """A `307 Temporary Redirect` redirect."""
    def __init__(self, url, absolute=False):
        Redirect.__init__(self, url, '307 Temporary Redirect', absolute=absolute)

tempredirect = TempRedirect

class BadRequest(HTTPError):
    """`400 Bad Request` error."""
    message = "bad request"
    def __init__(self, message=None):
        status = "400 Bad Request"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

badrequest = BadRequest

class Unauthorized(HTTPError):
    """`401 Unauthorized` error."""
    message = "unauthorized"
    def __init__(self):
        status = "401 Unauthorized"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

unauthorized = Unauthorized

class Forbidden(HTTPError):
    """`403 Forbidden` error."""
    message = "forbidden"
    def __init__(self):
        status = "403 Forbidden"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

forbidden = Forbidden

class _NotFound(HTTPError):
    """`404 Not Found` error."""
    message = "not found"
    def __init__(self, message=None):
        status = '404 Not Found'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

def NotFound(message=None):
    """Returns HTTPError with '404 Not Found' error from the active application.
    """
    if message:
        return _NotFound(message)
    elif ctx.get('app_stack'):
        return ctx.app_stack[-1].notfound()
    else:
        return _NotFound()

notfound = NotFound

class NoMethod(HTTPError):
    """A `405 Method Not Allowed` error."""
    def __init__(self, cls=None):
        status = '405 Method Not Allowed'
        headers = {}
        headers['Content-Type'] = 'text/html'
        
        methods = ['GET', 'HEAD', 'POST', 'PUT', 'DELETE']
        if cls:
            methods = [method for method in methods if hasattr(cls, method)]

        headers['Allow'] = ', '.join(methods)
        data = None
        HTTPError.__init__(self, status, headers, data)
        
nomethod = NoMethod

class NotAcceptable(HTTPError):
    """`406 Not Acceptable` error."""
    message = "not acceptable"
    def __init__(self):
        status = "406 Not Acceptable"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

notacceptable = NotAcceptable

class Conflict(HTTPError):
    """`409 Conflict` error."""
    message = "conflict"
    def __init__(self):
        status = "409 Conflict"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

conflict = Conflict

class Gone(HTTPError):
    """`410 Gone` error."""
    message = "gone"
    def __init__(self):
        status = '410 Gone'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

gone = Gone

class PreconditionFailed(HTTPError):
    """`412 Precondition Failed` error."""
    message = "precondition failed"
    def __init__(self):
        status = "412 Precondition Failed"
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, self.message)

preconditionfailed = PreconditionFailed

class _InternalError(HTTPError):
    """500 Internal Server Error`."""
    message = "internal server error"
    
    def __init__(self, message=None):
        status = '500 Internal Server Error'
        headers = {'Content-Type': 'text/html'}
        HTTPError.__init__(self, status, headers, message or self.message)

def InternalError(message=None):
    """Returns HTTPError with '500 internal error' error from the active application.
    """
    if message:
        return _InternalError(message)
    elif ctx.get('app_stack'):
        return ctx.app_stack[-1].internalerror()
    else:
        return _InternalError()

internalerror = InternalError

def header(hdr, value, unique=False):
    """
    Adds the header `hdr: value` with the response.
    
    If `unique` is True and a header with that name already exists,
    it doesn't add a new one. 
    """
    hdr, value = safestr(hdr), safestr(value)
    # protection against HTTP response splitting attack
    if '\n' in hdr or '\r' in hdr or '\n' in value or '\r' in value:
        raise ValueError, 'invalid characters in header'
        
    if unique is True:
        for h, v in ctx.headers:
            if h.lower() == hdr.lower(): return
    
    ctx.headers.append((hdr, value))
    
def rawinput(method=None):
    """Returns storage object with GET or POST arguments.
    """
    method = method or "both"
    from cStringIO import StringIO

    def dictify(fs): 
        # hack to make web.input work with enctype='text/plain.
        if fs.list is None:
            fs.list = [] 

        return dict([(k, fs[k]) for k in fs.keys()])
    
    e = ctx.env.copy()
    a = b = {}
    
    if method.lower() in ['both', 'post', 'put']:
        if e['REQUEST_METHOD'] in ['POST', 'PUT']:
            if e.get('CONTENT_TYPE', '').lower().startswith('multipart/'):
                # since wsgi.input is directly passed to cgi.FieldStorage, 
                # it can not be called multiple times. Saving the FieldStorage
                # object in ctx to allow calling web.input multiple times.
                a = ctx.get('_fieldstorage')
                if not a:
                    fp = e['wsgi.input']
                    a = cgi.FieldStorage(fp=fp, environ=e, keep_blank_values=1)
                    ctx._fieldstorage = a
            else:
                fp = StringIO(data())
                a = cgi.FieldStorage(fp=fp, environ=e, keep_blank_values=1)
            a = dictify(a)

    if method.lower() in ['both', 'get']:
        e['REQUEST_METHOD'] = 'GET'
        b = dictify(cgi.FieldStorage(environ=e, keep_blank_values=1))

    def process_fieldstorage(fs):
        if isinstance(fs, list):
            return [process_fieldstorage(x) for x in fs]
        elif fs.filename is None:
            return fs.value
        else:
            return fs

    return storage([(k, process_fieldstorage(v)) for k, v in dictadd(b, a).items()])

def input(*requireds, **defaults):
    """
    Returns a `storage` object with the GET and POST arguments. 
    See `storify` for how `requireds` and `defaults` work.
    """
    _method = defaults.pop('_method', 'both')
    out = rawinput(_method)
    try:
        defaults.setdefault('_unicode', True) # force unicode conversion by default.
        return storify(out, *requireds, **defaults)
    except KeyError:
        raise badrequest()

def data():
    """Returns the data sent with the request."""
    if 'data' not in ctx:
        cl = intget(ctx.env.get('CONTENT_LENGTH'), 0)
        ctx.data = ctx.env['wsgi.input'].read(cl)
    return ctx.data

def setcookie(name, value, expires='', domain=None,
              secure=False, httponly=False, path=None):
    """Sets a cookie."""
    morsel = Cookie.Morsel()
    name, value = safestr(name), safestr(value)
    morsel.set(name, value, urllib.quote(value))
    if expires < 0:
        expires = -1000000000
    morsel['expires'] = expires
    morsel['path'] = path or ctx.homepath+'/'
    if domain:
        morsel['domain'] = domain
    if secure:
        morsel['secure'] = secure
    value = morsel.OutputString()
    if httponly:
        value += '; httponly'
    header('Set-Cookie', value)

def cookies(*requireds, **defaults):
    """
    Returns a `storage` object with all the cookies in it.
    See `storify` for how `requireds` and `defaults` work.
    """
    cookie = Cookie.SimpleCookie()
    cookie.load(ctx.env.get('HTTP_COOKIE', ''))
    try:
        d = storify(cookie, *requireds, **defaults)
        for k, v in d.items():
            d[k] = v and urllib.unquote(v)
        return d
    except KeyError:
        badrequest()
        raise StopIteration

def debug(*args):
    """
    Prints a prettyprinted version of `args` to stderr.
    """
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    for arg in args:
        print >> out, pprint.pformat(arg)
    return ''

def _debugwrite(x):
    try: 
        out = ctx.environ['wsgi.errors']
    except: 
        out = sys.stderr
    out.write(x)
debug.write = _debugwrite

ctx = context = threadeddict()

ctx.__doc__ = """
A `storage` object containing various information about the request:
  
`environ` (aka `env`)
   : A dictionary containing the standard WSGI environment variables.

`host`
   : The domain (`Host` header) requested by the user.

`home`
   : The base path for the application.

`ip`
   : The IP address of the requester.

`method`
   : The HTTP method used.

`path`
   : The path request.
   
`query`
   : If there are no query arguments, the empty string. Otherwise, a `?` followed
     by the query string.

`fullpath`
   : The full path requested, including query arguments (`== path + query`).

### Response Data

`status` (default: "200 OK")
   : The status code to be used in the response.

`headers`
   : A list of 2-tuples to be used in the response.

`output`
   : A string to be used as the response.
"""

########NEW FILE########
__FILENAME__ = webopenid
"""openid.py: an openid library for web.py

Notes:

 - This will create a file called .openid_secret_key in the 
   current directory with your secret key in it. If someone 
   has access to this file they can log in as any user. And 
   if the app can't find this file for any reason (e.g. you 
   moved the app somewhere else) then each currently logged 
   in user will get logged out.

 - State must be maintained through the entire auth process 
   -- this means that if you have multiple web.py processes 
   serving one set of URLs or if you restart your app often 
   then log ins will fail. You have to replace sessions and 
   store for things to work.

 - We set cookies starting with "openid_".

"""

import os
import random
import hmac
import __init__ as web
import openid.consumer.consumer
import openid.store.memstore

sessions = {}
store = openid.store.memstore.MemoryStore()

def _secret():
    try:
        secret = file('.openid_secret_key').read()
    except IOError:
        # file doesn't exist
        secret = os.urandom(20)
        file('.openid_secret_key', 'w').write(secret)
    return secret

def _hmac(identity_url):
    return hmac.new(_secret(), identity_url).hexdigest()

def _random_session():
    n = random.random()
    while n in sessions:
        n = random.random()
    n = str(n)
    return n

def status():
    oid_hash = web.cookies().get('openid_identity_hash', '').split(',', 1)
    if len(oid_hash) > 1:
        oid_hash, identity_url = oid_hash
        if oid_hash == _hmac(identity_url):
            return identity_url
    return None

def form(openid_loc):
    oid = status()
    if oid:
        return '''
        <form method="post" action="%s">
          <img src="http://openid.net/login-bg.gif" alt="OpenID" />
          <strong>%s</strong>
          <input type="hidden" name="action" value="logout" />
          <input type="hidden" name="return_to" value="%s" />
          <button type="submit">log out</button>
        </form>''' % (openid_loc, oid, web.ctx.fullpath)
    else:
        return '''
        <form method="post" action="%s">
          <input type="text" name="openid" value="" 
            style="background: url(http://openid.net/login-bg.gif) no-repeat; padding-left: 18px; background-position: 0 50%%;" />
          <input type="hidden" name="return_to" value="%s" />
          <button type="submit">log in</button>
        </form>''' % (openid_loc, web.ctx.fullpath)

def logout():
    web.setcookie('openid_identity_hash', '', expires=-1)

class host:
    def POST(self):
        # unlike the usual scheme of things, the POST is actually called
        # first here
        i = web.input(return_to='/')
        if i.get('action') == 'logout':
            logout()
            return web.redirect(i.return_to)

        i = web.input('openid', return_to='/')

        n = _random_session()
        sessions[n] = {'webpy_return_to': i.return_to}
        
        c = openid.consumer.consumer.Consumer(sessions[n], store)
        a = c.begin(i.openid)
        f = a.redirectURL(web.ctx.home, web.ctx.home + web.ctx.fullpath)

        web.setcookie('openid_session_id', n)
        return web.redirect(f)

    def GET(self):
        n = web.cookies('openid_session_id').openid_session_id
        web.setcookie('openid_session_id', '', expires=-1)
        return_to = sessions[n]['webpy_return_to']

        c = openid.consumer.consumer.Consumer(sessions[n], store)
        a = c.complete(web.input(), web.ctx.home + web.ctx.fullpath)

        if a.status.lower() == 'success':
            web.setcookie('openid_identity_hash', _hmac(a.identity_url) + ',' + a.identity_url)

        del sessions[n]
        return web.redirect(return_to)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI Utilities
(from web.py)
"""

import os, sys

import http
import webapi as web
from utils import listget
from net import validaddr, validip
import httpserver
    
def runfcgi(func, addr=('localhost', 8000)):
    """Runs a WSGI function as a FastCGI server."""
    import flup.server.fcgi as flups
    return flups.WSGIServer(func, multiplexed=True, bindAddress=addr, debug=False).run()

def runscgi(func, addr=('localhost', 4000)):
    """Runs a WSGI function as an SCGI server."""
    import flup.server.scgi as flups
    return flups.WSGIServer(func, bindAddress=addr, debug=False).run()

def runwsgi(func):
    """
    Runs a WSGI-compatible `func` using FCGI, SCGI, or a simple web server,
    as appropriate based on context and `sys.argv`.
    """
    
    if os.environ.has_key('SERVER_SOFTWARE'): # cgi
        os.environ['FCGI_FORCE_CGI'] = 'Y'

    if (os.environ.has_key('PHP_FCGI_CHILDREN') #lighttpd fastcgi
      or os.environ.has_key('SERVER_SOFTWARE')):
        return runfcgi(func, None)
    
    if 'fcgi' in sys.argv or 'fastcgi' in sys.argv:
        args = sys.argv[1:]
        if 'fastcgi' in args: args.remove('fastcgi')
        elif 'fcgi' in args: args.remove('fcgi')
        if args:
            return runfcgi(func, validaddr(args[0]))
        else:
            return runfcgi(func, None)
    
    if 'scgi' in sys.argv:
        args = sys.argv[1:]
        args.remove('scgi')
        if args:
            return runscgi(func, validaddr(args[0]))
        else:
            return runscgi(func)
    
    return httpserver.runsimple(func, validip(listget(sys.argv, 1, '')))
    
def _is_dev_mode():
    # quick hack to check if the program is running in dev mode.
    if os.environ.has_key('SERVER_SOFTWARE') \
        or os.environ.has_key('PHP_FCGI_CHILDREN') \
        or 'fcgi' in sys.argv or 'fastcgi' in sys.argv \
        or 'mod_wsgi' in sys.argv:
            return False
    return True

# When running the builtin-server, enable debug mode if not already set.
web.config.setdefault('debug', _is_dev_mode())

########NEW FILE########
__FILENAME__ = ssl_builtin
"""A library for integrating Python's builtin ``ssl`` library with CherryPy.

The ssl module must be importable for SSL functionality.

To use this module, set ``CherryPyWSGIServer.ssl_adapter`` to an instance of
``BuiltinSSLAdapter``.
"""

try:
    import ssl
except ImportError:
    ssl = None

from cherrypy import wsgiserver


class BuiltinSSLAdapter(wsgiserver.SSLAdapter):
    """A wrapper for integrating Python's builtin ssl module with CherryPy."""
    
    certificate = None
    """The filename of the server SSL certificate."""
    
    private_key = None
    """The filename of the server's private key file."""
    
    def __init__(self, certificate, private_key, certificate_chain=None):
        if ssl is None:
            raise ImportError("You must install the ssl module to use HTTPS.")
        self.certificate = certificate
        self.private_key = private_key
        self.certificate_chain = certificate_chain
    
    def bind(self, sock):
        """Wrap and return the given socket."""
        return sock
    
    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries."""
        try:
            s = ssl.wrap_socket(sock, do_handshake_on_connect=True,
                    server_side=True, certfile=self.certificate,
                    keyfile=self.private_key, ssl_version=ssl.PROTOCOL_SSLv23)
        except ssl.SSLError, e:
            if e.errno == ssl.SSL_ERROR_EOF:
                # This is almost certainly due to the cherrypy engine
                # 'pinging' the socket to assert it's connectable;
                # the 'ping' isn't SSL.
                return None, {}
            elif e.errno == ssl.SSL_ERROR_SSL:
                if e.args[1].endswith('http request'):
                    # The client is speaking HTTP to an HTTPS server.
                    raise wsgiserver.NoSSLError
            raise
        return s, self.get_environ(s)
    
    # TODO: fill this out more with mod ssl env
    def get_environ(self, sock):
        """Create WSGI environ entries to be merged into each request."""
        cipher = sock.cipher()
        ssl_environ = {
            "wsgi.url_scheme": "https",
            "HTTPS": "on",
            'SSL_PROTOCOL': cipher[1],
            'SSL_CIPHER': cipher[0]
##            SSL_VERSION_INTERFACE 	string 	The mod_ssl program version
##            SSL_VERSION_LIBRARY 	string 	The OpenSSL program version
            }
        return ssl_environ
    
    def makefile(self, sock, mode='r', bufsize=-1):
        return wsgiserver.CP_fileobject(sock, mode, bufsize)


########NEW FILE########
__FILENAME__ = ssl_pyopenssl
"""A library for integrating pyOpenSSL with CherryPy.

The OpenSSL module must be importable for SSL functionality.
You can obtain it from http://pyopenssl.sourceforge.net/

To use this module, set CherryPyWSGIServer.ssl_adapter to an instance of
SSLAdapter. There are two ways to use SSL:

Method One
----------

 * ``ssl_adapter.context``: an instance of SSL.Context.

If this is not None, it is assumed to be an SSL.Context instance,
and will be passed to SSL.Connection on bind(). The developer is
responsible for forming a valid Context object. This approach is
to be preferred for more flexibility, e.g. if the cert and key are
streams instead of files, or need decryption, or SSL.SSLv3_METHOD
is desired instead of the default SSL.SSLv23_METHOD, etc. Consult
the pyOpenSSL documentation for complete options.

Method Two (shortcut)
---------------------

 * ``ssl_adapter.certificate``: the filename of the server SSL certificate.
 * ``ssl_adapter.private_key``: the filename of the server's private key file.

Both are None by default. If ssl_adapter.context is None, but .private_key
and .certificate are both given and valid, they will be read, and the
context will be automatically created from them.
"""

import socket
import threading
import time

from cherrypy import wsgiserver

try:
    from OpenSSL import SSL
    from OpenSSL import crypto
except ImportError:
    SSL = None


class SSL_fileobject(wsgiserver.CP_fileobject):
    """SSL file object attached to a socket object."""
    
    ssl_timeout = 3
    ssl_retry = .01
    
    def _safe_call(self, is_reader, call, *args, **kwargs):
        """Wrap the given call with SSL error-trapping.
        
        is_reader: if False EOF errors will be raised. If True, EOF errors
        will return "" (to emulate normal sockets).
        """
        start = time.time()
        while True:
            try:
                return call(*args, **kwargs)
            except SSL.WantReadError:
                # Sleep and try again. This is dangerous, because it means
                # the rest of the stack has no way of differentiating
                # between a "new handshake" error and "client dropped".
                # Note this isn't an endless loop: there's a timeout below.
                time.sleep(self.ssl_retry)
            except SSL.WantWriteError:
                time.sleep(self.ssl_retry)
            except SSL.SysCallError, e:
                if is_reader and e.args == (-1, 'Unexpected EOF'):
                    return ""
                
                errnum = e.args[0]
                if is_reader and errnum in wsgiserver.socket_errors_to_ignore:
                    return ""
                raise socket.error(errnum)
            except SSL.Error, e:
                if is_reader and e.args == (-1, 'Unexpected EOF'):
                    return ""
                
                thirdarg = None
                try:
                    thirdarg = e.args[0][0][2]
                except IndexError:
                    pass
                
                if thirdarg == 'http request':
                    # The client is talking HTTP to an HTTPS server.
                    raise wsgiserver.NoSSLError()
                
                raise wsgiserver.FatalSSLAlert(*e.args)
            except:
                raise
            
            if time.time() - start > self.ssl_timeout:
                raise socket.timeout("timed out")
    
    def recv(self, *args, **kwargs):
        buf = []
        r = super(SSL_fileobject, self).recv
        while True:
            data = self._safe_call(True, r, *args, **kwargs)
            buf.append(data)
            p = self._sock.pending()
            if not p:
                return "".join(buf)
    
    def sendall(self, *args, **kwargs):
        return self._safe_call(False, super(SSL_fileobject, self).sendall,
                               *args, **kwargs)

    def send(self, *args, **kwargs):
        return self._safe_call(False, super(SSL_fileobject, self).send,
                               *args, **kwargs)


class SSLConnection:
    """A thread-safe wrapper for an SSL.Connection.
    
    ``*args``: the arguments to create the wrapped ``SSL.Connection(*args)``.
    """
    
    def __init__(self, *args):
        self._ssl_conn = SSL.Connection(*args)
        self._lock = threading.RLock()
    
    for f in ('get_context', 'pending', 'send', 'write', 'recv', 'read',
              'renegotiate', 'bind', 'listen', 'connect', 'accept',
              'setblocking', 'fileno', 'close', 'get_cipher_list',
              'getpeername', 'getsockname', 'getsockopt', 'setsockopt',
              'makefile', 'get_app_data', 'set_app_data', 'state_string',
              'sock_shutdown', 'get_peer_certificate', 'want_read',
              'want_write', 'set_connect_state', 'set_accept_state',
              'connect_ex', 'sendall', 'settimeout', 'gettimeout'):
        exec("""def %s(self, *args):
        self._lock.acquire()
        try:
            return self._ssl_conn.%s(*args)
        finally:
            self._lock.release()
""" % (f, f))
    
    def shutdown(self, *args):
        self._lock.acquire()
        try:
            # pyOpenSSL.socket.shutdown takes no args
            return self._ssl_conn.shutdown()
        finally:
            self._lock.release()


class pyOpenSSLAdapter(wsgiserver.SSLAdapter):
    """A wrapper for integrating pyOpenSSL with CherryPy."""
    
    context = None
    """An instance of SSL.Context."""
    
    certificate = None
    """The filename of the server SSL certificate."""
    
    private_key = None
    """The filename of the server's private key file."""
    
    certificate_chain = None
    """Optional. The filename of CA's intermediate certificate bundle.
    
    This is needed for cheaper "chained root" SSL certificates, and should be
    left as None if not required."""
    
    def __init__(self, certificate, private_key, certificate_chain=None):
        if SSL is None:
            raise ImportError("You must install pyOpenSSL to use HTTPS.")
        
        self.context = None
        self.certificate = certificate
        self.private_key = private_key
        self.certificate_chain = certificate_chain
        self._environ = None
    
    def bind(self, sock):
        """Wrap and return the given socket."""
        if self.context is None:
            self.context = self.get_context()
        conn = SSLConnection(self.context, sock)
        self._environ = self.get_environ()
        return conn
    
    def wrap(self, sock):
        """Wrap and return the given socket, plus WSGI environ entries."""
        return sock, self._environ.copy()
    
    def get_context(self):
        """Return an SSL.Context from self attributes."""
        # See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/442473
        c = SSL.Context(SSL.SSLv23_METHOD)
        c.use_privatekey_file(self.private_key)
        if self.certificate_chain:
            c.load_verify_locations(self.certificate_chain)
        c.use_certificate_file(self.certificate)
        return c
    
    def get_environ(self):
        """Return WSGI environ entries to be merged into each request."""
        ssl_environ = {
            "HTTPS": "on",
            # pyOpenSSL doesn't provide access to any of these AFAICT
##            'SSL_PROTOCOL': 'SSLv2',
##            SSL_CIPHER 	string 	The cipher specification name
##            SSL_VERSION_INTERFACE 	string 	The mod_ssl program version
##            SSL_VERSION_LIBRARY 	string 	The OpenSSL program version
            }
        
        if self.certificate:
            # Server certificate attributes
            cert = open(self.certificate, 'rb').read()
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
            ssl_environ.update({
                'SSL_SERVER_M_VERSION': cert.get_version(),
                'SSL_SERVER_M_SERIAL': cert.get_serial_number(),
##                'SSL_SERVER_V_START': Validity of server's certificate (start time),
##                'SSL_SERVER_V_END': Validity of server's certificate (end time),
                })
            
            for prefix, dn in [("I", cert.get_issuer()),
                               ("S", cert.get_subject())]:
                # X509Name objects don't seem to have a way to get the
                # complete DN string. Use str() and slice it instead,
                # because str(dn) == "<X509Name object '/C=US/ST=...'>"
                dnstr = str(dn)[18:-2]
                
                wsgikey = 'SSL_SERVER_%s_DN' % prefix
                ssl_environ[wsgikey] = dnstr
                
                # The DN should be of the form: /k1=v1/k2=v2, but we must allow
                # for any value to contain slashes itself (in a URL).
                while dnstr:
                    pos = dnstr.rfind("=")
                    dnstr, value = dnstr[:pos], dnstr[pos + 1:]
                    pos = dnstr.rfind("/")
                    dnstr, key = dnstr[:pos], dnstr[pos + 1:]
                    if key and value:
                        wsgikey = 'SSL_SERVER_%s_DN_%s' % (prefix, key)
                        ssl_environ[wsgikey] = value
        
        return ssl_environ
    
    def makefile(self, sock, mode='r', bufsize=-1):
        if SSL and isinstance(sock, SSL.ConnectionType):
            timeout = sock.gettimeout()
            f = SSL_fileobject(sock, mode, bufsize)
            f.ssl_timeout = timeout
            return f
        else:
            return wsgiserver.CP_fileobject(sock, mode, bufsize)


########NEW FILE########
