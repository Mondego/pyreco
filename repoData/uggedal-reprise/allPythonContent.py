__FILENAME__ = reprise
#!/usr/bin/env python

from __future__ import with_statement

import os
import re
import time
import email
import shutil

import markdown

from os.path import abspath, realpath, dirname, join
from datetime import datetime, timedelta
from textwrap import dedent
from pygments.formatters import HtmlFormatter
from smartypants import smartyPants
from jinja2 import DictLoader, Environment
from lxml.builder import ElementMaker
from lxml.etree import tostring

TITLE = 'Journal'
URL = 'http://journal.uggedal.com'
STYLESHEET = 'style2.css'

AUTHOR = {
    'name': 'Eivind Uggedal',
    'email': 'eivind@uggedal.com',
    'url': 'http://uggedal.com',
    'elsewhere': {
        '@uggedal': 'http://twitter.com/uggedal/',
        'Was it up?': 'http://wasitup.com/',
    }
}

ROOT = abspath(dirname(__file__))
DIRS = {
    'source': join(ROOT, 'entries'),
    'build': join(ROOT, 'build'),
    'public': join(ROOT, 'public'),
    'assets': join(ROOT, 'assets'),
}

CONTEXT = {
    'author': AUTHOR,
    'body_title': "%s of %s" % (TITLE, AUTHOR['name']),
    'head_title': "%s of %s" % (TITLE, AUTHOR['name']),
    'analytics': 'UA-1857692-3',
    'stylesheet': STYLESHEET,
}

def _markdown(content):
    return markdown.markdown(content, ['codehilite', 'def_list'])

def read_and_parse_entries():
    files = sorted([join(DIRS['source'], f)
                    for f in os.listdir(DIRS['source'])], reverse=True)
    entries = []
    for file in files:
        match = META_REGEX.findall(file)
        if len(match):
            meta = match[0]
            with open(file, 'r') as open_file:
                msg = email.message_from_file(open_file)
                date = datetime(*[int(d) for d in meta[0:3]])
                entries.append({
                    'slug': slugify(meta[3]),
                    'title': meta[3].replace('.', ' '),
                    'tags': msg['Tags'].split(),
                    'date': {'iso8601': date.isoformat(),
                             'rfc3339': rfc3339(date),
                             'display': date.strftime('%Y-%m-%d'),},
                    'content_html': smartyPants(_markdown(msg.get_payload())),
                })
    return entries

def generate_index(entries, template):
    feed_url = "%s/index.atom" % URL
    html = template.render(dict(CONTEXT, **{'entries': entries,
                                            'feed_url': feed_url}))
    write_file(join(DIRS['build'], 'index.html'), html)
    atom = generate_atom(entries, feed_url)
    write_file(join(DIRS['build'], 'index.atom'), atom)

def generate_tag_indices(entries, template):
    for tag in set(sum([e['tags'] for e in entries], [])):
        tag_entries = [e for e in entries if tag in e['tags']]
        feed_url = "%s/tags/%s.atom" % (URL, tag)
        html = template.render(
            dict(CONTEXT, **{'entries': tag_entries,
                             'active_tag': tag,
                             'feed_url': feed_url,
                             'head_title': "%s: %s" % (CONTEXT['head_title'],
                                                       tag),}))
        write_file(join(DIRS['build'], 'tags', '%s.html' % tag), html)
        atom = generate_atom(tag_entries, feed_url)
        write_file(join(DIRS['build'], 'tags', '%s.atom' % tag), atom)

def generate_details(entries, template):
    for entry in entries:
        html = template.render(
            dict(CONTEXT, **{'entry': entry,
                             'head_title': "%s: %s" % (CONTEXT['head_title'],
                                                       entry['title'])}))
        write_file(join(DIRS['build'], '%s.html' % entry['slug']), html)

def generate_404(template):
        html = template.render(CONTEXT)
        write_file(join(DIRS['build'], '404.html'), html)

def generate_style(css):
    css2 = HtmlFormatter(style='trac').get_style_defs()
    write_file(join(DIRS['build'], STYLESHEET), ''.join([css, "\n\n", css2]))

def generate_atom(entries, feed_url):
    A = ElementMaker(namespace='http://www.w3.org/2005/Atom',
                     nsmap={None : "http://www.w3.org/2005/Atom"})
    entry_elements = []
    for entry in entries:
        entry_elements.append(A.entry(
            A.id(atom_id(entry=entry)),
            A.title(entry['title']),
            A.link(href="%s/%s" % (URL, entry['slug'])),
            A.updated(entry['date']['rfc3339']),
            A.content(entry['content_html'], type='html'),))
    return tostring(A.feed(A.author( A.name(AUTHOR['name']) ),
                           A.id(atom_id()),
                           A.title(TITLE),
                           A.link(href=URL),
                           A.link(href=feed_url, rel='self'),
                           A.updated(entries[0]['date']['rfc3339']),
                           *entry_elements), pretty_print=True)

def write_file(file_name, contents):
    with open(file_name, 'w') as open_file:
        open_file.write(contents.encode("utf-8"))

def slugify(str):
    return re.sub(r'\s+', '-', re.sub(r'[^\w\s-]', '',
                                      str.replace('.', ' ').lower()))

def atom_id(entry=None):
    domain = re.sub(r'http://([^/]+).*', r'\1', URL)
    if entry:
        return "tag:%s,%s:/%s" % (domain, entry['date']['display'],
                                  entry['slug'])
    else:
        return "tag:%s,2009-03-04:/" % domain

def rfc3339(date):
    offset = -time.altzone if time.daylight else -time.timezone
    return (date + timedelta(seconds=offset)).strftime('%Y-%m-%dT%H:%M:%SZ')

def get_templates():
    templates = {
    'base.html': """
    <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"
    "http://www.w3.org/TR/html4/strict.dtd">
    <html>
      <head>
        <title>{{ head_title }}</title>
        <link rel='stylesheet' type='text/css' href='/{{ stylesheet }}'>
        <link rel="alternate" type="application/atom+xml"
              title="{{ head_title }}" href="{{ feed_url }}">
      </head>
      <body>
        <h1>
          {% block title %}
          {% endblock %}
        </h1>
        {% block content %}
        {% endblock %}
        <p id="elsewhere">
        {% for service, url in author.elsewhere.items() %}
          <a href="{{ url }}">{{ service }}</a>
        {% endfor %}
        </p>
        <p id="footer">
          <span class="author vcard">
            Written by
            <a class="url fn" href="{{ author.url }}">{{ author.name }}</a>
            &lt;<a class="email" href="mailto:{{ author.email }}">{{ author.email }}</a>&gt;.
          </span>
          Powered by
          <a href="http://github.com/uggedal/reprise">reprise.py</a>.
        </p>
      </body>
      <script type='text/javascript'>
        var gaJsHost = (("https:" == document.location.protocol) ?
                       "https://ssl." : "http://www.");
        document.write(unescape("%3Cscript src='" + gaJsHost +
                                "google-analytics.com/ga.js' type='text/" +
                                "javascript'%3E%3C/script%3E"));
      </script>
      <script type='text/javascript'>
        var pageTracker = _gat._getTracker("{{ analytics }}");
        pageTracker._initData();
        pageTracker._trackPageview();
      </script>
    </html>
    """,

    'list.html': """
    {% extends "base.html" %}
    {% block title %}
      {% if active_tag %}
        <a href="/">{{ body_title }}</a>
      {% else %}
        {{ body_title }}
      {% endif %}
    {% endblock %}
    {% block content %}
      {% for entry in entries %}
        {% set display_content = loop.first %}
        {% include '_entry.html' %}
      {% endfor %}
    {% endblock %}
    """,

    'detail.html': """
    {% extends "base.html" %}
    {% block title %}
      <a href="/">{{ body_title }}</a>
    {% endblock %}
    {% block content %}
      {% set display_content = True %}
      {% set plain_title = True %}
      {% include '_entry.html' %}
    {% endblock %}
    """,

    '_entry.html': """
    <div class="hentry">
      <abbr class="updated" title="{{ entry.date.iso8601 }}">
        {{ entry.date.display }}
      </abbr>
      <h2>
        {% if plain_title %}
          {{ entry.title }}
        {% else %}
          <a href="/{{ entry.slug }}" rel="bookmark">{{ entry.title }}</a>
        {% endif %}
      </h2>
      {% if display_content %}
        <ul class="tags">
          {% for tag in entry.tags %}
            <li{% if active_tag == tag %} class="active"{% endif %}>
              <a href="/tags/{{ tag }}" rel="tag" >{{ tag }}</a>
            </li>
          {% endfor %}
        </ul>
      {% endif %}
      {% if display_content %}
        <div class="entry-content">{{ entry.content_html }}</div>
      {% endif %}
    </div>
    """,

    '404.html': """
    {% extends "base.html" %}
    {% block title %}
      <a href="/">{{ body_title }}</a>
    {% endblock %}
    {% block content %}
      <p>Resource not found. Go back to <a href="/">the front</a> page.</p>
    {% endblock %}
    """,

    STYLESHEET: """
    body {
      color: #444;
      font-size: 1em;
      font-family: 'DejaVu Sans', 'Bitstream Vera Sans', Verdana, sans-serif;
      line-height: 1.6;
      padding: 0 3em 0 13em;
      width: 40em;
    }

    @font-face {
      font-family: "Sorts Mill Goudy";
      src: url("/OFLGoudyStM.otf");
    }

    a {
      color: #444;
    }

    p {
      margin-bottom: 1em;
    }

    ul, ol {
      padding: 0;
    }

    blockquote {
      font-style: italic;
      margin: 0;
    }

      blockquote em {
        font-weight: bold;
      }

    pre, code {
      font-family: 'DejaVu Sans Mono', 'Bitstream Vera Sans Mono',
                   Consolas, Monaco, 'Lucida Console', monospaced;
      font-size: .75em;
    }

      pre {
        border: 0.15em solid #eee;
        border-left: 1em solid #eee;
        display: block;
        padding: 1em 1em 1em 2em;
      }

    h1 {
      font-size: 2.5em;
      margin: 1.5em 0 1em 0;
    }

    h2 {
      font-size: 3em;
    }

    h3 {
      font-size: 2em;
    }

    img {
      margin: 1em 0 1em 0;
    }

    table {
      margin-top: 1em;
    }

      table th, table td {
        padding-right: 1em;
        text-align: left;
      }

      table.hanging {
        display: inline;
        float: left;
        padding: 0;
        margin: 1em 1em 1em -10em;
      }

        table caption {
          caption-side: bottom;
          color: #666;
          font-size: .75em;
          padding: 0 1em;
          text-align: left;
        }

          table.hanging img {
            border: .1em solid #ddd;
            margin: 0;
            padding: .5em;
          }

    h1 a, h2 a, h3 a, ul.tags a {
      text-decoration: none;
    }

    h1, h1 a, h2, h2 a, h3 {
      color: #222;
    }

      h1 a:hover, h2 a:hover {
        color: #c00;
      }

    h1, h2, h3, abbr.updated {
      font-family: "Sorts Mill Goudy", Georgia, 'DejaVu Serif', 'Bitstream Vera Serif', serif;
      font-style: normal;
      font-weight: normal;
    }

    abbr.updated, ul.tags {
      float: left;
    }

      abbr.updated {
        border: 0;
        color: #c00;
        font-size: 1.6em;
        line-height: 3.25em;
        margin: 0 0 0 -6.25em;
      }

    ul.tags {
      list-style-type: none;
      margin: 0 0 0 -10em;
    }

      ul.tags li {
        display: block;
        font-size: .8em;
        margin-bottom: .3em;
      }

        ul.tags li.active a, ul.tags a:hover {
          color: #c00;
        }

    .entry-content a {
      color: #c00;
    }

    .entry-content a:hover {
      color: #000;
    }

    p#footer {
      color: #bbb;
      font-size: .75em;
      margin-top: 3em;
      text-align: center;
      text-indent: 0;
    }

    p#footer a {
      color: #999;
    }

    #elsewhere {
      margin: 1em;
      position: absolute;
      right: 1em;
      top: .5em;
      z-index: 9000;
    }

    #elsewhere a {
      background: #c00;
      border-radius:.3em;
      -moz-border-radius:.3em;
      -webkit-border-radius:.3em;
      color: #fff;
      display: block;
      margin-bottom: .5em;
      opacity: .9;
      padding: .4em .6em;
      text-decoration: none;
    }

    #elsewhere a:hover {
      opacity: .6;
    }
    """,}
    return dict([(k, dedent(v).strip()) for k, v in templates.items()])

META_REGEX = re.compile(r"/(\d{4})\.(\d\d)\.(\d\d)\.(.+)")

if __name__ == "__main__":
    templates = get_templates()
    env = Environment(loader=DictLoader(templates))
    all_entries = read_and_parse_entries()
    shutil.copytree(DIRS['assets'], DIRS['build'])
    generate_index(all_entries, env.get_template('list.html'))
    os.mkdir(join(DIRS['build'], 'tags'))
    generate_tag_indices(all_entries, env.get_template('list.html'))
    generate_details(all_entries, env.get_template('detail.html'))
    generate_404(env.get_template('404.html'))
    generate_style(templates[STYLESHEET])
    shutil.rmtree(DIRS['public'])
    shutil.move(DIRS['build'], DIRS['public'])

########NEW FILE########
