__FILENAME__ = converter
# -*- coding: utf-8 -*-




import os

import requests
from html2text import html2text

READABILITY_URL = 'https://www.readability.com/api/content/v1/parser'

def readability(url):
    token = os.environ.get('READABILITY_TOKEN')
    params = {'url': url, 'token': token}

    r = requests.get(READABILITY_URL, params=params)
    return r.json()['content'], r.json()['title']

def convert(html, title=None):
    if title:
        title = '# {}'.format(title)
        html = '\n\n'.join([title, html])

    return html2text(html)

def meh(url):
    try:
        content, title = readability(url)
        return convert(content, title=title)
    except KeyError:
        return None


if __name__ == '__main__':
    print meh('http://kennethreitz.org/')
########NEW FILE########
__FILENAME__ = service
# -*- coding: utf-8 -*-

from flask import Flask, request, redirect, url_for, render_template
from converter import meh

app = Flask(__name__)

@app.route('/')
def fuck_gpl3():
    url = request.args.get('url')

    if url:
        content = meh(url)
        if content:
            return content, 200, {'Content-Type': 'text/x-markdown; charset=UTF-8'}
        else:
            return '404 Not Found', 404
    else:
        return render_template('index.html')

########NEW FILE########
