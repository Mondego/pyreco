__FILENAME__ = test_regex
import unittest
from xcolor.xparser import Xparser

class TestXcolorRegex(unittest.TestCase):

    # expected output for the tested patterns
    expected = dict(name='color5', value='aabbcc')

    def test_comments(self):
        line = ";*color5: rgb:aa/bb/cc"
        self.assertFalse(Xparser.valid(line))
        line = "#*color5: rgb:aa/bb/cc"
        self.assertFalse(Xparser.valid(line))

    def test_generic_rgb(self):
        line = "*color5: rgb:aa/bb/cc"
        self.assertTrue(Xparser.valid(line))
        output = Xparser.rgb(line)
        self.assertEqual(output, self.expected)

    def test_generic_hex(self):
        line = "*color5: #aabbcc"
        self.assertTrue(Xparser.valid(line))
        output = Xparser.hex(line)
        self.assertEqual(output, self.expected)

    def test_urxvt_rgb(self):
        line = "URxvt*color5: rgb:aa/bb/cc"
        self.assertTrue(Xparser.valid(line))
        output = Xparser.rgb(line)
        self.assertEqual(output, self.expected)

    def test_urxvt_hex(self):
        line = "URxvt*color5: #aabbcc"
        self.assertTrue(Xparser.valid(line))
        output = Xparser.hex(line)
        self.assertEqual(output, self.expected)

    def test_urxvt_dot_rgb(self):
        line = "URxvt.color5: rgb:aa/bb/cc"
        self.assertTrue(Xparser.valid(line))
        output = Xparser.rgb(line)
        self.assertEqual(output, self.expected)

    def test_urxvt_dot_hex(self):
        line = "URxvt.color5: #aabbcc"
        self.assertTrue(Xparser.valid(line))
        output = Xparser.hex(line)
        self.assertEqual(output, self.expected)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = generator
# -*- coding: utf-8 -*-
import re
import os
import sys
from jinja2 import Template
from glob import glob
from .xparser import Xparser

class Generator(object):

    # map color names with codes
    code = {
        # black
        'color0': '30m',
        'color8': '1;30m',
        # red
        'color1': '31m',
        'color9': '1;31m',
        # green
        'color2': '32m',
        'color10': '1;32m',
        # yellow
        'color3': '33m',
        'color11': '1;33m',
        # blue
        'color4': '34m',
        'color12': '1;34m',
        # magenta
        'color5': '35m',
        'color13': '1;35m',
        # cyan
        'color6': '36m',
        'color14': '1;36m',
        # white
        'color7': '37m',
        'color15': '1;37m'
    }

    # available color names
    colors = {
        0: 'color0',
        1: 'color8',
        2: 'color1',
        3: 'color9',
        4: 'color2',
        5: 'color10',
        6: 'color3',
        7: 'color11',
        8: 'color4',
        9: 'color12',
        10: 'color5',
        11: 'color13',
        12: 'color6',
        13: 'color14',
        14: 'color7',
        15: 'color15'
    }

    # default foreground/backgroud values for themes that do not specify them
    default_fg = 'dcdcdc'
    default_bg = '1c1c1c'

    def __init__(self, theme_folder, output_folder, text='txt'):
        self.theme_folder = theme_folder
        self.output_folder = output_folder
        self.text = text

        try:
            self.themes = os.listdir(self.theme_folder)
        except os.error:
            print("Error reading from path: {0}".format(self.theme_folder))
            sys.exit(1)

        # load template passed in jinja2
        path = os.path.dirname(__file__)
        tpl = os.path.join(path, 'template')
        try:
            with open(tpl, 'r') as f:
                tpl_contents = f.read()
        except IOError:
            print("Error opening template file for reading")
            sys.exit(1)
        self.tpl = Template(tpl_contents)

    def _parse_theme_file(self, f):
        contents = {}

        for line in f:
            # regex matching is easier by stripping leading/trailing whitespace
            line = line.strip()

            if Xparser.valid(line):
                # try matchig a line with rgb values
                match = Xparser.rgb(line)
                if match:
                    contents[match['name']] = match['value']
                    continue

                # rgb match failed, try with hex
                match = Xparser.hex(line)
                if match:
                    contents[match['name']] = match['value']
        return contents

    def _write_html_file(self, name, rgb):
        if 'foreground' not in rgb.keys():
            rgb['foreground'] = self.default_fg

        if 'background' not in rgb.keys():
            rgb['background'] = self.default_bg

        # append extension to theme filename
        name = '.'.join((name, 'html'))
        try:
            with open(os.path.join(self.output_folder, name), 'w') as f:
                f.write(self.tpl.render(rgb=rgb, colors=self.colors,
                                        text=self.text, code=self.code))
        except IOError:
            print("Cannot write html file for theme: {0}".format(name))
            pass

    def generate_files(self):
        for theme in self.themes:
            with open(os.path.join(self.theme_folder, theme), 'r') as f:
                rgb = self._parse_theme_file(f)
            self._write_html_file(theme, rgb)
        return glob("{0}/*.html".format(self.output_folder.rstrip('/')))

    def cleanup(self):
        themes_html = [os.path.basename(os.path.splitext(t)[0]) for t in
            glob("{0}/*.html".format(self.output_folder.rstrip('/')))]
        for theme in [t for t in themes_html if t not in self.themes]:
            try:
                os.remove(os.path.join(self.output_folder,
                                       "{0}.html".format(theme)))
            except os.error:
                print("Cannot remove generated file for theme: {0}".format(theme))
                continue


if __name__ == '__main__':
    print("Import to use, not intented to run standalone.")
    sys.exit(1)


########NEW FILE########
__FILENAME__ = xparser
import re

class Xparser(object):
    """Match color line definitions from Xdefaults style files"""

    @classmethod
    def valid(cls, line):
        """line starting with '*' or '*' with whitespace prepended are valid
        also, lines starting with "Urxvt*" "Urxvt." are valid
        """
        pattern = r'^\s*[a-zA-Z]*[\*\.]'
        return True if re.match(pattern, line) else False

    @classmethod
    def rgb(cls, line):
        """matches lines with values using slashes and the rgb keyword

        *color4: rgb:ff/ff/ff
        Urxvt*color4: rgb:ff/ff/ff
        Urxvt.color4: rgb:ff/ff/ff
        """
        pattern = r'(?:^\*|^\w*[\*\.])\.*(?P<name>[a-zA-Z]+\d{,2})\s*:\s*'\
            'rgb:(?P<value>[a-zA-Z0-9/]*)'

        match = re.match(pattern, line)
        if match:
            return dict(name=match.group('name'), value=match.group('value').replace('/', ''))

        return {}

    @classmethod
    def hex(cls, line):
        """matches lines using the hash symbol before the hex value

        *color4: #ffffff
        Urxvt*color4: #ffffff
        Urxvt.color4: #ffffff
        """
        pattern = r'(?:^\*|^\w*[\*\.])\.*(?P<name>[a-zA-Z]+\d{,2})\s*:\s*'\
            '#(?P<value>[a-zA-Z0-9]{6})'

        match = re.match(pattern, line)
        if match:
            return dict(name=match.group('name'), value=match.group('value'))

        return {}

########NEW FILE########
__FILENAME__ = xcolors
# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, send_from_directory, url_for
from glob import glob

app = Flask(__name__)

@app.route('/')
def index():
    directory = os.path.dirname(__file__)
    path = os.path.join(directory, 'templates', 'xcolors')
    themes = [os.path.splitext(os.path.basename(t))[0]
              for t in glob('{0}/*.html'.format(path))]
    return render_template('index.html', themes=themes)

@app.route('/dl/<path:filename>')
def download(filename):
    return send_from_directory('themes', filename,
                               mimetype='text/plain')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contribute')
def contribute():
    return render_template('contribute.html')

@app.template_filter()
def html_path(theme):
    """return relative path of html file for given theme"""
    return "xcolors/{0}.html".format(theme)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    from xcolor.generator import Generator
    path = os.path.dirname(__file__)
    xcolor = Generator(os.path.join(path, 'themes'),
                       os.path.join(path, 'templates', 'xcolors'))
    xcolor.cleanup()
    xcolor.generate_files()

    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG') in ("true", "True")

    app.run(host=host, port=port, debug=debug)

########NEW FILE########
