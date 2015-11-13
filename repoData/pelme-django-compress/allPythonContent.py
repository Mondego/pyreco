__FILENAME__ = settings
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

COMPRESS = getattr(settings, 'COMPRESS', not settings.DEBUG)
COMPRESS_AUTO = getattr(settings, 'COMPRESS_AUTO', True)
COMPRESS_VERSION = getattr(settings, 'COMPRESS_VERSION', False)
COMPRESS_VERSION_PLACEHOLDER = getattr(settings, 'COMPRESS_VERSION_PLACEHOLDER', '?')
COMPRESS_VERSION_DEFAULT = getattr(settings, 'COMPRESS_VERSION_DEFAULT', '0')
COMPRESS_VERSIONING = getattr(settings, 'COMPRESS_VERSIONING', 'compress.versioning.mtime.MTimeVersioning')

COMPRESS_CSS_FILTERS = getattr(settings, 'COMPRESS_CSS_FILTERS', ['compress.filters.csstidy.CSSTidyFilter'])
COMPRESS_JS_FILTERS = getattr(settings, 'COMPRESS_JS_FILTERS', ['compress.filters.jsmin.JSMinFilter'])
COMPRESS_CSS = getattr(settings, 'COMPRESS_CSS', {})
COMPRESS_JS = getattr(settings, 'COMPRESS_JS', {})

if COMPRESS_CSS_FILTERS is None:
    COMPRESS_CSS_FILTERS = []

if COMPRESS_JS_FILTERS is None:
    COMPRESS_JS_FILTERS = []

########NEW FILE########
__FILENAME__ = csstidy
# CSSTidy - CSS Parse
#
# CSS Parser class
#
# This file is part of CSSTidy.
#
# CSSTidy is free software you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation either version 2 of the License, or
# (at your option) any later version.
#
# CSSTidy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CSSTidy if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# @license http://opensource.org/licenses/gpl-license.php GNU Public License
# @package csstidy
# @author Dj Gilcrease (digitalxero at gmail dot com) 2005-2006

import re

from optimizer import CSSOptimizer
from output import CSSPrinter
import data
from tools import SortedDict

class CSSTidy(object):
    #Saves the parsed CSS
    _css = ""
    _raw_css = SortedDict()
    _optimized_css = SortedDict()

    #List of Tokens
    _tokens = []

    #Printer class
    _output = None

    #Optimiser class
    _optimizer = None

    #Saves the CSS charset (@charset)
    _charset = ''

    #Saves all @import URLs
    _import = []

    #Saves the namespace
    _namespace = ''

    #Contains the version of csstidy
    _version = '1.3'

    #Stores the settings
    _settings = {}

    # Saves the parser-status.
    #
    # Possible values:
    # - is = in selector
    # - ip = in property
    # - iv = in value
    # - instr = in string (started at " or ' or ( )
    # - ic = in comment (ignore everything)
    # - at = in @-block
    _status = 'is'

    #Saves the current at rule (@media)
    _at = ''

    #Saves the current selector
    _selector = ''

    #Saves the current property
    _property = ''

    #Saves the position of , in selectors
    _sel_separate = []

    #Saves the current value
    _value = ''

    #Saves the current sub-value
    _sub_value = ''

    #Saves all subvalues for a property.
    _sub_value_arr = []

    #Saves the char which opened the last string
    _str_char = ''
    _cur_string = ''

    #Status from which the parser switched to ic or instr
    _from = ''

    #Variable needed to manage string-in-strings, for example url("foo.png")
    _str_in_str = False

    #=True if in invalid at-rule
    _invalid_at = False

    #=True if something has been added to the current selector
    _added = False

    #Saves the message log
    _log = SortedDict()

    #Saves the line number
    _line = 1

    def __init__(self):
        self._settings['remove_bslash'] = True
        self._settings['compress_colors'] = True
        self._settings['compress_font-weight'] = True
        self._settings['lowercase_s'] = False
        self._settings['optimise_shorthands'] = 2
        self._settings['remove_last_'] = False
        self._settings['case_properties'] = 1
        self._settings['sort_properties'] = False
        self._settings['sort_selectors'] = False
        self._settings['merge_selectors'] = 2
        self._settings['discard_invalid_properties'] = False
        self._settings['css_level'] = 'CSS2.1'
        self._settings['preserve_css'] = False
        self._settings['timestamp'] = False
        self._settings['template'] = 'highest_compression'

        #Maps self._status to methods
        self.__statusMethod = {'is':self.__parseStatus_is, 'ip': self.__parseStatus_ip, 'iv':self.__parseStatus_iv, 'instr':self.__parseStatus_instr, 'ic':self.__parseStatus_ic, 'at':self.__parseStatus_at}

        self._output = CSSPrinter(self)
        self._optimizer = CSSOptimizer(self)

    #Public Methods
    def getSetting(self, setting):
        return self._settings.get(setting, False)

    #Set the value of a setting.
    def setSetting(self, setting, value):
        self._settings[setting] = value
        return True

    def log(self, message, ttype, line = -1):
        if line == -1:
            line = self._line

        line = int(line)

        add = {'m': message, 't': ttype}

        if not self._log.has_key(line):
            self._log[line] = []
            self._log[line].append(add)
        elif add not in self._log[line]:
            self._log[line].append(add)


    #Checks if a character is escaped (and returns True if it is)
    def escaped(self, string, pos):
        return not (string[pos-1] != '\\' or self.escaped(string, pos-1))

    #Adds CSS to an existing media/selector
    def merge_css_blocks(self, media, selector, css_add):
        for prop, value in css_add.iteritems():
            self.__css_add_property(media, selector, prop, value, False)

    #Checks if $value is !important.
    def is_important(self, value):
        return '!important' in value.lower()

    #Returns a value without !important
    def gvw_important(self, value):
        if self.is_important(value):
            ret = value.strip()
            ret = ret[0:-9]
            ret = ret.strip()
            ret = ret[0:-1]
            ret = ret.strip()
            return ret

        return value

    def parse(self, cssString):
        #Switch from \r\n to \n
        self._css = cssString.replace("\r\n", "\n") + ' '
        self._raw_css = {}
        self._optimized_css = {}
        self._curComment = ''

        #Start Parsing
        i = 0
        while i < len(cssString):
            if self._css[i] == "\n" or self._css[i] == "\r":
                self._line += 1

            i += self.__statusMethod[self._status](i)

            i += 1;

        self._optimized_css = self._optimizer.optimize(self._raw_css)

    def parseFile(self, filename):
        try:
            f = open(filename, "r")
            self.parse(f.read())
        finally:
            f.close()

    #Private Methods
    def __parseStatus_is(self, idx):
        """
            Parse in Selector
        """
        ret = 0

        if self.__is_token(self._css, idx):
            if self._css[idx] == '/' and self._css[idx+1] == '*' and self._selector.strip() == '':
                self._status = 'ic'
                self._from = 'is'
                return 1

            elif self._css[idx] == '@' and self._selector.strip() == '':
                #Check for at-rule
                self._invalid_at = True

                for name, ttype in data.at_rules.iteritems():
                    if self._css[idx+1:len(name)].lower() == name.lower():
                        if ttype == 'at':
                            self._at = '@' + name
                        else:
                            self._selector = '@' + name

                        self._status = ttype
                        self._invalid_at = False
                        ret += len(name)

                if self._invalid_at:
                    self._selector = '@'
                    invalid_at_name = ''
                    for j in xrange(idx+1, len(self._css)):
                        if not self._css[j].isalpha():
                            break;

                        invalid_at_name += self._css[j]

                    self.log('Invalid @-rule: ' + invalid_at_name + ' (removed)', 'Warning')

            elif self._css[idx] == '"' or self._css[idx] == "'":
                self._cur_string = self._css[idx]
                self._status = 'instr'
                self._str_char = self._css[idx]
                self._from = 'is'

            elif self._invalid_at and self._css[idx] == ';':
                self._invalid_at = False
                self._status = 'is'

            elif self._css[idx] == '{':
                self._status = 'ip'
                self.__add_token(data.SEL_START, self._selector)
                self._added = False;

            elif self._css[idx] == '}':
                self.__add_token(data.AT_END, self._at)
                self._at = ''
                self._selector = ''
                self._sel_separate = []

            elif self._css[idx] == ',':
                self._selector = self._selector.strip() + ','
                self._sel_separate.append(len(self._selector))

            elif self._css[idx] == '\\':
                self._selector += self.__unicode(idx)

            #remove unnecessary universal selector,  FS#147
            elif not (self._css[idx] == '*' and self._css[idx+1] in ('.', '#', '[', ':')):
                self._selector += self._css[idx]

        else:
            lastpos = len(self._selector)-1

            if lastpos == -1 or not ((self._selector[lastpos].isspace() or self.__is_token(self._selector, lastpos) and self._selector[lastpos] == ',') and self._css[idx].isspace()):
                self._selector += self._css[idx]

        return ret

    def __parseStatus_ip(self, idx):
        """
            Parse in property
        """
        if self.__is_token(self._css, idx):
            if (self._css[idx] == ':' or self._css[idx] == '=') and self._property != '':
                self._status = 'iv'

                if not self.getSetting('discard_invalid_properties') or self.__property_is_valid(self._property):
                    self.__add_token(data.PROPERTY, self._property)

            elif self._css[idx] == '/' and self._css[idx+1] == '*' and self._property == '':
                self._status = 'ic'
                self._from = 'ip'
                return 1

            elif self._css[idx] == '}':
                self.__explode_selectors()
                self._status = 'is'
                self._invalid_at = False
                self.__add_token(data.SEL_END, self._selector)
                self._selector = ''
                self._property = ''

            elif self._css[idx] == ';':
                self._property = ''

            elif self._css[idx] == '\\':
                self._property += self.__unicode(idx)

        elif not self._css[idx].isspace():
            self._property += self._css[idx]

        return 0

    def __parseStatus_iv(self, idx):
        """
            Parse in value
        """
        pn = (( self._css[idx] == "\n" or self._css[idx] == "\r") and self.__property_is_next(idx+1) or idx == len(self._css)) #CHECK#
        if self.__is_token(self._css, idx) or pn:
            if self._css[idx] == '/' and self._css[idx+1] == '*':
                self._status = 'ic'
                self._from = 'iv'
                return 1

            elif self._css[idx] == '"' or self._css[idx] == "'" or self._css[idx] == '(':
                self._cur_string = self._css[idx]
                self._str_char = ')' if self._css[idx] == '(' else self._css[idx]
                self._status = 'instr'
                self._from = 'iv'

            elif self._css[idx] == ',':
                self._sub_value = self._sub_value.strip() + ','

            elif self._css[idx] == '\\':
                self._sub_value += self.__unicode(idx)

            elif self._css[idx] == ';' or pn:
                if len(self._selector) > 0 and self._selector[0] == '@' and data.at_rules.has_key(self._selector[1:]) and data.at_rules[self._selector[1:]] == 'iv':
                    self._sub_value_arr.append(self._sub_value.strip())

                    self._status = 'is'

                    if '@charset' in self._selector:
                        self._charset = self._sub_value_arr[0]

                    elif '@namespace' in self._selector:
                        self._namespace = ' '.join(self._sub_value_arr)

                    elif '@import' in self._selector:
                        self._import.append(' '.join(self._sub_value_arr))


                    self._sub_value_arr = []
                    self._sub_value = ''
                    self._selector = ''
                    self._sel_separate = []

                else:
                    self._status = 'ip'

            elif self._css[idx] != '}':
                self._sub_value += self._css[idx]

            if (self._css[idx] == '}' or self._css[idx] == ';' or pn) and self._selector != '':
                if self._at == '':
                    self._at = data.DEFAULT_AT

                #case settings
                if self.getSetting('lowercase_s'):
                    self._selector = self._selector.lower()

                self._property = self._property.lower()

                if self._sub_value != '':
                    self._sub_value_arr.append(self._sub_value)
                    self._sub_value = ''

                self._value = ' '.join(self._sub_value_arr)


                self._selector = self._selector.strip()

                valid = self.__property_is_valid(self._property)

                if (not self._invalid_at or self.getSetting('preserve_css')) and (not self.getSetting('discard_invalid_properties') or valid):
                    self.__css_add_property(self._at, self._selector, self._property, self._value)
                    self.__add_token(data.VALUE, self._value)

                if not valid:
                    if self.getSetting('discard_invalid_properties'):
                        self.log('Removed invalid property: ' + self._property, 'Warning')

                    else:
                        self.log('Invalid property in ' + self.getSetting('css_level').upper() + ': ' + self._property, 'Warning')

                self._property = '';
                self._sub_value_arr = []
                self._value = ''

            if self._css[idx] == '}':
                self.__explode_selectors()
                self.__add_token(data.SEL_END, self._selector)
                self._status = 'is'
                self._invalid_at = False
                self._selector = ''

        elif not pn:
            self._sub_value += self._css[idx]

            if self._css[idx].isspace():
                if self._sub_value != '':
                    self._sub_value_arr.append(self._sub_value)
                    self._sub_value = ''

        return 0

    def __parseStatus_instr(self, idx):
        """
            Parse in String
        """
        if self._str_char == ')' and (self._css[idx] == '"' or self._css[idx] == "'") and not self.escaped(self._css, idx):
            self._str_in_str = not self._str_in_str

        temp_add = self._css[idx] # ...and no not-escaped backslash at the previous position
        if (self._css[idx] == "\n" or self._css[idx] == "\r") and not (self._css[idx-1] == '\\' and not self.escaped(self._css, idx-1)):
            temp_add = "\\A "
            self.log('Fixed incorrect newline in string', 'Warning')

        if not (self._str_char == ')' and self._css[idx].isspace() and not self._str_in_str):
            self._cur_string += temp_add

        if self._css[idx] == self._str_char and not self.escaped(self._css, idx) and not self._str_in_str:
            self._status = self._from
            regex = re.compile(r'([\s]+)', re.I | re.U | re.S)
            if regex.match(self._cur_string) is None and self._property != 'content':
                if self._str_char == '"' or self._str_char == "'":
                    self._cur_string = self._cur_string[1:-1]

                elif len(self._cur_string) > 3 and (self._cur_string[1] == '"' or self._cur_string[1] == "'"):
                    self._cur_string = self._cur_string[0] + self._cur_string[2:-2] + self._cur_string[-1]

            if self._from == 'iv':
                self._sub_value += self._cur_string

            elif self._from == 'is':
                self._selector += self._cur_string

        return 0

    def __parseStatus_ic(self, idx):
        """
            Parse css In Comment
        """
        if self._css[idx] == '*' and self._css[idx+1] == '/':
            self._status = self._from
            self.__add_token(data.COMMENT, self._curComment)
            self._curComment = ''
            return 1

        else:
            self._curComment += self._css[idx]

        return 0

    def __parseStatus_at(self, idx):
        """
            Parse in at-block
        """
        if self.__is_token(string, idx):
            if self._css[idx] == '/' and self._css[idx+1] == '*':
                self._status = 'ic'
                self._from = 'at'
                return 1

            elif self._css[i] == '{':
                self._status = 'is'
                self.__add_token(data.AT_START, self._at)

            elif self._css[i] == ',':
                self._at = self._at.strip() + ','

            elif self._css[i] == '\\':
                self._at += self.__unicode(i)
        else:
            lastpos = len(self._at)-1
            if not (self._at[lastpos].isspace() or self.__is_token(self._at, lastpos) and self._at[lastpos] == ',') and self._css[i].isspace():
                self._at += self._css[i]

        return 0

    def __explode_selectors(self):
        #Explode multiple selectors
        if self.getSetting('merge_selectors') == 1:
            new_sels = []
            lastpos = 0;
            self._sel_separate.append(len(self._selector))

            for num in xrange(len(self._sel_separate)):
                pos = self._sel_separate[num]
                if num == (len(self._sel_separate)): #CHECK#
                    pos += 1

                new_sels.append(self._selector[lastpos:(pos-lastpos-1)])
                lastpos = pos

            if len(new_sels) > 1:
                for selector in new_sels:
                    self.merge_css_blocks(self._at, selector, self._raw_css[self._at][self._selector])

                del self._raw_css[self._at][self._selector]

        self._sel_separate = []

    #Adds a property with value to the existing CSS code
    def __css_add_property(self, media, selector, prop, new_val):
        if self.getSetting('preserve_css') or new_val.strip() == '':
            return

        if not self._raw_css.has_key(media):
            self._raw_css[media] = SortedDict()

        if not self._raw_css[media].has_key(selector):
            self._raw_css[media][selector] = SortedDict()

        self._added = True
        if self._raw_css[media][selector].has_key(prop):
            if (self.is_important(self._raw_css[media][selector][prop]) and self.is_important(new_val)) or not self.is_important(self._raw_css[media][selector][prop]):
                del self._raw_css[media][selector][prop]
                self._raw_css[media][selector][prop] = new_val.strip()

        else:
            self._raw_css[media][selector][prop] = new_val.strip()

    #Checks if the next word in a string from pos is a CSS property
    def __property_is_next(self, pos):
        istring = self._css[pos: len(self._css)]
        pos = istring.find(':')
        if pos == -1:
            return False;

        istring = istring[:pos].strip().lower()
        if data.all_properties.has_key(istring):
            self.log('Added semicolon to the end of declaration', 'Warning')
            return True

        return False;

    #Checks if a property is valid
    def __property_is_valid(self, prop):
        return (data.all_properties.has_key(prop) and data.all_properties[prop].find(self.getSetting('css_level').upper()) != -1)

    #Adds a token to self._tokens
    def __add_token(self, ttype, cssdata, do=False):
        if self.getSetting('preserve_css') or do:
            if ttype == data.COMMENT:
                token = [ttype, cssdata]
            else:
                token = [ttype, cssdata.strip()]

            self._tokens.append(token)

    #Parse unicode notations and find a replacement character
    def __unicode(self, idx):
       ##FIX##
       return ''

    #Starts parsing from URL
    ##USED?
    def __parse_from_url(self, url):
        try:
            if "http" in url.lower() or "https" in url.lower():
                f = urllib.urlopen(url)
            else:
                f = open(url)

            data = f.read()
            return self.parse(data)
        finally:
            f.close()

    #Checks if there is a token at the current position
    def __is_token(self, string, idx):
        return (string[idx] in data.tokens and not self.escaped(string, idx))


    #Property Methods
    def _getOutput(self):
        self._output.prepare(self._optimized_css)
        return self._output.render

    def _getLog(self):
        ret = ""
        ks = self._log.keys()
        ks.sort()
        for line in ks:
            for msg in self._log[line]:
                ret += "Type: " + msg['t'] + "\n"
                ret += "Message: " + msg['m'] + "\n"
            ret += "\n"

        return ret

    def _getCSS(self):
        return self._css


    #Properties
    Output = property(_getOutput, None)
    Log = property(_getLog, None)
    CSS = property(_getCSS, None)


if __name__ == '__main__':
    import sys
    tidy = CSSTidy()
    f = open(sys.argv[1], "r")
    css = f.read()
    f.close()
    tidy.parse(css)
    tidy.Output('file', filename="Stylesheet.min.css")
    print tidy.Output()
    #print tidy._import
########NEW FILE########
__FILENAME__ = data
# Various CSS Data for CSSTidy
#
# This file is part of CSSTidy.
#
# CSSTidy is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# CSSTidy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CSSTidy; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# @license http://opensource.org/licenses/gpl-license.php GNU Public License
# @package csstidy
# @author Florian Schmitz (floele at gmail dot com) 2005

AT_START    = 1
AT_END      = 2
SEL_START   = 3
SEL_END     = 4
PROPERTY    = 5
VALUE       = 6
COMMENT     = 7
DEFAULT_AT  = 41

# All whitespace allowed in CSS
#
# @global array whitespace
# @version 1.0
whitespace = frozenset([' ',"\n","\t","\r","\x0B"])

# All CSS tokens used by csstidy
#
# @global string tokens
# @version 1.0
tokens = '/@}{;:=\'"(,\\!$%&)#+.<>?[]^`|~'

# All CSS units (CSS 3 units included)
#
# @see compress_numbers()
# @global array units
# @version 1.0
units = frozenset(['in','cm','mm','pt','pc','px','rem','em','%','ex','gd','vw','vh','vm','deg','grad','rad','ms','s','khz','hz'])

# Available at-rules
#
# @global array at_rules
# @version 1.0
at_rules = {'page':'is', 'font-face':'is', 'charset':'iv', 'import':'iv', 'namespace':'iv', 'media':'at'}

# Properties that need a value with unit
#
# @todo CSS3 properties
# @see compress_numbers()
# @global array unit_values
# @version 1.2
unit_values = frozenset(['background', 'background-position', 'border', 'border-top', 'border-right', 'border-bottom',
                                    'border-left', 'border-width', 'border-top-width', 'border-right-width', 'border-left-width',
                                    'border-bottom-width', 'bottom', 'border-spacing', 'font-size','height', 'left', 'margin', 'margin-top',
                                    'margin-right', 'margin-bottom', 'margin-left', 'max-height', 'max-width', 'min-height', 'min-width',
                                    'outline-width', 'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left','position',
                                    'right', 'top', 'text-indent', 'letter-spacing', 'word-spacing', 'width'
                                    ])


# Properties that allow <color> as value
#
# @todo CSS3 properties
# @see compress_numbers()
# @global array color_values
# @version 1.0
color_values = frozenset(['background-color', 'border-color', 'border-top-color', 'border-right-color',
                                        'border-bottom-color', 'border-left-color', 'color', 'outline-color'])


# Default values for the background properties
#
# @todo Possibly property names will change during CSS3 development
# @global array background_prop_default
# @see dissolve_short_bg()
# @see merge_bg()
# @version 1.0
background_prop_default = {}
background_prop_default['background-image'] = 'none'
background_prop_default['background-size'] = 'auto'
background_prop_default['background-repeat'] = 'repeat'
background_prop_default['background-position'] = '0 0'
background_prop_default['background-attachment'] = 'scroll'
background_prop_default['background-clip'] = 'border'
background_prop_default['background-origin'] = 'padding'
background_prop_default['background-color'] = 'transparent'

# A list of non-W3C color names which get replaced by their hex-codes
#
# @global array replace_colors
# @see cut_color()
# @version 1.0
replace_colors = {}
replace_colors['aliceblue'] = '#F0F8FF'
replace_colors['antiquewhite'] = '#FAEBD7'
replace_colors['aquamarine'] = '#7FFFD4'
replace_colors['azure'] = '#F0FFFF'
replace_colors['beige'] = '#F5F5DC'
replace_colors['bisque'] = '#FFE4C4'
replace_colors['blanchedalmond'] = '#FFEBCD'
replace_colors['blueviolet'] = '#8A2BE2'
replace_colors['brown'] = '#A52A2A'
replace_colors['burlywood'] = '#DEB887'
replace_colors['cadetblue'] = '#5F9EA0'
replace_colors['chartreuse'] = '#7FFF00'
replace_colors['chocolate'] = '#D2691E'
replace_colors['coral'] = '#FF7F50'
replace_colors['cornflowerblue'] = '#6495ED'
replace_colors['cornsilk'] = '#FFF8DC'
replace_colors['crimson'] = '#DC143C'
replace_colors['cyan'] = '#00FFFF'
replace_colors['darkblue'] = '#00008B'
replace_colors['darkcyan'] = '#008B8B'
replace_colors['darkgoldenrod'] = '#B8860B'
replace_colors['darkgray'] = '#A9A9A9'
replace_colors['darkgreen'] = '#006400'
replace_colors['darkkhaki'] = '#BDB76B'
replace_colors['darkmagenta'] = '#8B008B'
replace_colors['darkolivegreen'] = '#556B2F'
replace_colors['darkorange'] = '#FF8C00'
replace_colors['darkorchid'] = '#9932CC'
replace_colors['darkred'] = '#8B0000'
replace_colors['darksalmon'] = '#E9967A'
replace_colors['darkseagreen'] = '#8FBC8F'
replace_colors['darkslateblue'] = '#483D8B'
replace_colors['darkslategray'] = '#2F4F4F'
replace_colors['darkturquoise'] = '#00CED1'
replace_colors['darkviolet'] = '#9400D3'
replace_colors['deeppink'] = '#FF1493'
replace_colors['deepskyblue'] = '#00BFFF'
replace_colors['dimgray'] = '#696969'
replace_colors['dodgerblue'] = '#1E90FF'
replace_colors['feldspar'] = '#D19275'
replace_colors['firebrick'] = '#B22222'
replace_colors['floralwhite'] = '#FFFAF0'
replace_colors['forestgreen'] = '#228B22'
replace_colors['gainsboro'] = '#DCDCDC'
replace_colors['ghostwhite'] = '#F8F8FF'
replace_colors['gold'] = '#FFD700'
replace_colors['goldenrod'] = '#DAA520'
replace_colors['greenyellow'] = '#ADFF2F'
replace_colors['honeydew'] = '#F0FFF0'
replace_colors['hotpink'] = '#FF69B4'
replace_colors['indianred'] = '#CD5C5C'
replace_colors['indigo'] = '#4B0082'
replace_colors['ivory'] = '#FFFFF0'
replace_colors['khaki'] = '#F0E68C'
replace_colors['lavender'] = '#E6E6FA'
replace_colors['lavenderblush'] = '#FFF0F5'
replace_colors['lawngreen'] = '#7CFC00'
replace_colors['lemonchiffon'] = '#FFFACD'
replace_colors['lightblue'] = '#ADD8E6'
replace_colors['lightcoral'] = '#F08080'
replace_colors['lightcyan'] = '#E0FFFF'
replace_colors['lightgoldenrodyellow'] = '#FAFAD2'
replace_colors['lightgrey'] = '#D3D3D3'
replace_colors['lightgreen'] = '#90EE90'
replace_colors['lightpink'] = '#FFB6C1'
replace_colors['lightsalmon'] = '#FFA07A'
replace_colors['lightseagreen'] = '#20B2AA'
replace_colors['lightskyblue'] = '#87CEFA'
replace_colors['lightslateblue'] = '#8470FF'
replace_colors['lightslategray'] = '#778899'
replace_colors['lightsteelblue'] = '#B0C4DE'
replace_colors['lightyellow'] = '#FFFFE0'
replace_colors['limegreen'] = '#32CD32'
replace_colors['linen'] = '#FAF0E6'
replace_colors['magenta'] = '#FF00FF'
replace_colors['mediumaquamarine'] = '#66CDAA'
replace_colors['mediumblue'] = '#0000CD'
replace_colors['mediumorchid'] = '#BA55D3'
replace_colors['mediumpurple'] = '#9370D8'
replace_colors['mediumseagreen'] = '#3CB371'
replace_colors['mediumslateblue'] = '#7B68EE'
replace_colors['mediumspringgreen'] = '#00FA9A'
replace_colors['mediumturquoise'] = '#48D1CC'
replace_colors['mediumvioletred'] = '#C71585'
replace_colors['midnightblue'] = '#191970'
replace_colors['mintcream'] = '#F5FFFA'
replace_colors['mistyrose'] = '#FFE4E1'
replace_colors['moccasin'] = '#FFE4B5'
replace_colors['navajowhite'] = '#FFDEAD'
replace_colors['oldlace'] = '#FDF5E6'
replace_colors['olivedrab'] = '#6B8E23'
replace_colors['orangered'] = '#FF4500'
replace_colors['orchid'] = '#DA70D6'
replace_colors['palegoldenrod'] = '#EEE8AA'
replace_colors['palegreen'] = '#98FB98'
replace_colors['paleturquoise'] = '#AFEEEE'
replace_colors['palevioletred'] = '#D87093'
replace_colors['papayawhip'] = '#FFEFD5'
replace_colors['peachpuff'] = '#FFDAB9'
replace_colors['peru'] = '#CD853F'
replace_colors['pink'] = '#FFC0CB'
replace_colors['plum'] = '#DDA0DD'
replace_colors['powderblue'] = '#B0E0E6'
replace_colors['rosybrown'] = '#BC8F8F'
replace_colors['royalblue'] = '#4169E1'
replace_colors['saddlebrown'] = '#8B4513'
replace_colors['salmon'] = '#FA8072'
replace_colors['sandybrown'] = '#F4A460'
replace_colors['seagreen'] = '#2E8B57'
replace_colors['seashell'] = '#FFF5EE'
replace_colors['sienna'] = '#A0522D'
replace_colors['skyblue'] = '#87CEEB'
replace_colors['slateblue'] = '#6A5ACD'
replace_colors['slategray'] = '#708090'
replace_colors['snow'] = '#FFFAFA'
replace_colors['springgreen'] = '#00FF7F'
replace_colors['steelblue'] = '#4682B4'
replace_colors['tan'] = '#D2B48C'
replace_colors['thistle'] = '#D8BFD8'
replace_colors['tomato'] = '#FF6347'
replace_colors['turquoise'] = '#40E0D0'
replace_colors['violet'] = '#EE82EE'
replace_colors['violetred'] = '#D02090'
replace_colors['wheat'] = '#F5DEB3'
replace_colors['whitesmoke'] = '#F5F5F5'
replace_colors['yellowgreen'] = '#9ACD32'

#A list of optimized colors
optimize_colors = {}
optimize_colors['black'] = '#000'
optimize_colors['fuchsia'] = '#F0F'
optimize_colors['white'] = '#FFF'
optimize_colors['yellow'] = '#FF0'
optimize_colors['cyan'] = '#0FF'
optimize_colors['magenta'] = '#F0F'
optimize_colors['lightslategray'] = '#789'

optimize_colors['#800000'] = 'maroon'
optimize_colors['#FFA500'] = 'orange'
optimize_colors['#808000'] = 'olive'
optimize_colors['#800080'] = 'purple'
optimize_colors['#008000'] = 'green'
optimize_colors['#000080'] = 'navy'
optimize_colors['#008080'] = 'teal'
optimize_colors['#C0C0C0'] = 'silver'
optimize_colors['#808080'] = 'gray'
optimize_colors['#4B0082'] = 'indigo'
optimize_colors['#FFD700'] = 'gold'
optimize_colors['#A52A2A'] = 'brown'
optimize_colors['#00FFFF'] = 'cyan'
optimize_colors['#EE82EE'] = 'violet'
optimize_colors['#DA70D6'] = 'orchid'
optimize_colors['#FFE4C4'] = 'bisque'
optimize_colors['#F0E68C'] = 'khaki'
optimize_colors['#F5DEB3'] = 'wheat'
optimize_colors['#FF7F50'] = 'coral'
optimize_colors['#F5F5DC'] = 'beige'
optimize_colors['#F0FFFF'] = 'azure'
optimize_colors['#A0522D'] = 'sienna'
optimize_colors['#CD853F'] = 'peru'
optimize_colors['#FFFFF0'] = 'ivory'
optimize_colors['#DDA0DD'] = 'plum'
optimize_colors['#D2B48C'] = 'tan'
optimize_colors['#FFC0CB'] = 'pink'
optimize_colors['#FFFAFA'] = 'snow'
optimize_colors['#FA8072'] = 'salmon'
optimize_colors['#FF6347'] = 'tomato'
optimize_colors['#FAF0E6'] = 'linen'
optimize_colors['#F00'] = 'red'


# A list of all shorthand properties that are devided into four properties and/or have four subvalues
#
# @global array shorthands
# @todo Are there new ones in CSS3?
# @see dissolve_4value_shorthands()
# @see merge_4value_shorthands()
# @version 1.0
shorthands = {}
shorthands['border-color'] = ['border-top-color','border-right-color','border-bottom-color','border-left-color']
shorthands['border-style'] = ['border-top-style','border-right-style','border-bottom-style','border-left-style']
shorthands['border-width'] = ['border-top-width','border-right-width','border-bottom-width','border-left-width']
shorthands['margin'] = ['margin-top','margin-right','margin-bottom','margin-left']
shorthands['padding'] = ['padding-top','padding-right','padding-bottom','padding-left']
shorthands['-moz-border-radius'] = 0

# All CSS Properties. Needed for csstidy::property_is_next()
#
# @global array all_properties
# @todo Add CSS3 properties
# @version 1.0
# @see csstidy::property_is_next()
all_properties = {}
all_properties['background'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['background-color'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['background-image'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['background-repeat'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['background-attachment'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['background-position'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-top'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-right'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-bottom'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-left'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-color'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-top-color'] = 'CSS2.0,CSS2.1'
all_properties['border-bottom-color'] = 'CSS2.0,CSS2.1'
all_properties['border-left-color'] = 'CSS2.0,CSS2.1'
all_properties['border-right-color'] = 'CSS2.0,CSS2.1'
all_properties['border-style'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-top-style'] = 'CSS2.0,CSS2.1'
all_properties['border-right-style'] = 'CSS2.0,CSS2.1'
all_properties['border-left-style'] = 'CSS2.0,CSS2.1'
all_properties['border-bottom-style'] = 'CSS2.0,CSS2.1'
all_properties['border-width'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-top-width'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-right-width'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-left-width'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-bottom-width'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['border-collapse'] = 'CSS2.0,CSS2.1'
all_properties['border-spacing'] = 'CSS2.0,CSS2.1'
all_properties['bottom'] = 'CSS2.0,CSS2.1'
all_properties['caption-side'] = 'CSS2.0,CSS2.1'
all_properties['content'] = 'CSS2.0,CSS2.1'
all_properties['clear'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['clip'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['color'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['counter-reset'] = 'CSS2.0,CSS2.1'
all_properties['counter-increment'] = 'CSS2.0,CSS2.1'
all_properties['cursor'] = 'CSS2.0,CSS2.1'
all_properties['empty-cells'] = 'CSS2.0,CSS2.1'
all_properties['display'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['direction'] = 'CSS2.0,CSS2.1'
all_properties['float'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['font'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['font-family'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['font-style'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['font-variant'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['font-weight'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['font-stretch'] = 'CSS2.0'
all_properties['font-size-adjust'] = 'CSS2.0'
all_properties['font-size'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['height'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['left'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['line-height'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['list-style'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['list-style-type'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['list-style-image'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['list-style-position'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['margin'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['margin-top'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['margin-right'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['margin-bottom'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['margin-left'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['marks'] = 'CSS1.0,CSS2.0'
all_properties['marker-offset'] = 'CSS2.0'
all_properties['max-height'] = 'CSS2.0,CSS2.1'
all_properties['max-width'] = 'CSS2.0,CSS2.1'
all_properties['min-height'] = 'CSS2.0,CSS2.1'
all_properties['min-width'] = 'CSS2.0,CSS2.1'
all_properties['overflow'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['orphans'] = 'CSS2.0,CSS2.1'
all_properties['outline'] = 'CSS2.0,CSS2.1'
all_properties['outline-width'] = 'CSS2.0,CSS2.1'
all_properties['outline-style'] = 'CSS2.0,CSS2.1'
all_properties['outline-color'] = 'CSS2.0,CSS2.1'
all_properties['padding'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['padding-top'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['padding-right'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['padding-bottom'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['padding-left'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['page-break-before'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['page-break-after'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['page-break-inside'] = 'CSS2.0,CSS2.1'
all_properties['page'] = 'CSS2.0'
all_properties['position'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['quotes'] = 'CSS2.0,CSS2.1'
all_properties['right'] = 'CSS2.0,CSS2.1'
all_properties['size'] = 'CSS1.0,CSS2.0'
all_properties['speak-header'] = 'CSS2.0,CSS2.1'
all_properties['table-layout'] = 'CSS2.0,CSS2.1'
all_properties['top'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['text-indent'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['text-align'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['text-decoration'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['text-shadow'] = 'CSS2.0'
all_properties['letter-spacing'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['word-spacing'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['text-transform'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['white-space'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['unicode-bidi'] = 'CSS2.0,CSS2.1'
all_properties['vertical-align'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['visibility'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['width'] = 'CSS1.0,CSS2.0,CSS2.1'
all_properties['widows'] = 'CSS2.0,CSS2.1'
all_properties['z-index'] = 'CSS1.0,CSS2.0,CSS2.1'

# Speech #
all_properties['volume'] = 'CSS2.0,CSS2.1'
all_properties['speak'] = 'CSS2.0,CSS2.1'
all_properties['pause'] = 'CSS2.0,CSS2.1'
all_properties['pause-before'] = 'CSS2.0,CSS2.1'
all_properties['pause-after'] = 'CSS2.0,CSS2.1'
all_properties['cue'] = 'CSS2.0,CSS2.1'
all_properties['cue-before'] = 'CSS2.0,CSS2.1'
all_properties['cue-after'] = 'CSS2.0,CSS2.1'
all_properties['play-during'] = 'CSS2.0,CSS2.1'
all_properties['azimuth'] = 'CSS2.0,CSS2.1'
all_properties['elevation'] = 'CSS2.0,CSS2.1'
all_properties['speech-rate'] = 'CSS2.0,CSS2.1'
all_properties['voice-family'] = 'CSS2.0,CSS2.1'
all_properties['pitch'] = 'CSS2.0,CSS2.1'
all_properties['pitch-range'] = 'CSS2.0,CSS2.1'
all_properties['stress'] = 'CSS2.0,CSS2.1'
all_properties['richness'] = 'CSS2.0,CSS2.1'
all_properties['speak-punctuation'] = 'CSS2.0,CSS2.1'
all_properties['speak-numeral'] = 'CSS2.0,CSS2.1'
########NEW FILE########
__FILENAME__ = optimizer
# CSSTidy - CSS Optimizer
#
# CSS Optimizer class
#
# This file is part of CSSTidy.
#
# CSSTidy is free software you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation either version 2 of the License, or
# (at your option) any later version.
#
# CSSTidy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CSSTidy if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# @license http://opensource.org/licenses/gpl-license.php GNU Public License
# @package csstidy
# @author Dj Gilcrease (digitalxero at gmail dot com) 2005-2006

import data
from tools import SortedDict


class CSSOptimizer(object):
    def __init__(self, parser):
        #raw_css is a dict
        self.parser = parser
        self._optimized_css = SortedDict


#PUBLIC METHODS
    def optimize(self, raw_css):
        if self.parser.getSetting('preserve_css'):
            return raw_css

        self._optimized_css = raw_css

        if self.parser.getSetting('merge_selectors') == 2:
            self.__merge_selectors()

        ##OPTIMIZE##
        for media, css in self._optimized_css.iteritems():
            for selector, cssdata in css.iteritems():
                if self.parser.getSetting('optimise_shorthands') >= 1:
                    cssdata = self.__merge_4value_shorthands(cssdata)

                if self.parser.getSetting('optimise_shorthands') >= 2:
                    cssdata = self.__merge_bg(cssdata)

                for item, value in cssdata.iteritems():
                    value = self.__compress_numbers(item, value)
                    value = self.__compress_important(value)

                    if item in data.color_values and self.parser.getSetting('compress_colors'):
                        old = value[:]
                        value = self.__compress_color(value)
                        if old != value:
                            self.parser.log('In "' + selector + '" Optimised ' + item + ': Changed ' + old + ' to ' + value, 'Information')

                    if item == 'font-weight' and self.parser.getSetting('compress_font-weight'):
                        if value  == 'bold':
                            value = '700'
                            self.parser.log('In "' + selector + '" Optimised font-weight: Changed "bold" to "700"', 'Information')

                        elif value == 'normal':
                            value = '400'
                            self.parser.log('In "' + selector + '" Optimised font-weight: Changed "normal" to "400"', 'Information')

                    self._optimized_css[media][selector][item] = value


        return self._optimized_css


#PRIVATE METHODS
    def __merge_bg(self, cssdata):
        """
            Merges all background properties
            @cssdata (dict) is a dictionary of the selector properties
        """
        #Max number of background images. CSS3 not yet fully implemented
        img = 1
        clr = 1
        bg_img_list = []
        if cssdata.has_key('background-image'):
            img = len(cssdata['background-image'].split(','))
            bg_img_list = self.parser.gvw_important(cssdata['background-image']).split(',')

        elif cssdata.has_key('background-color'):
            clr = len(cssdata['background-color'].split(','))


        number_of_values = max(img, clr, 1)

        new_bg_value = ''
        important = ''

        for i in xrange(number_of_values):
            for bg_property, default_value in data.background_prop_default.iteritems():
                #Skip if property does not exist
                if not cssdata.has_key(bg_property):
                    continue

                cur_value = cssdata[bg_property]

                #Skip some properties if there is no background image
                if (len(bg_img_list) > i and bg_img_list[i] == 'none') and bg_property in frozenset(['background-size', 'background-position', 'background-attachment', 'background-repeat']):
                    continue

                #Remove !important
                if self.parser.is_important(cur_value):
                    important = ' !important'
                    cur_value = self.parser.gvw_important(cur_value)

                #Do not add default values
                if cur_value == default_value:
                    continue

                temp = cur_value.split(',')

                if len(temp) > i:
                    if bg_property == 'background-size':
                        new_bg_value += '(' + temp[i] + ') '

                    else:
                        new_bg_value += temp[i] + ' '

            new_bg_value = new_bg_value.strip()
            if i != (number_of_values-1):
                new_bg_value += ','

        #Delete all background-properties
        for bg_property, default_value in data.background_prop_default.iteritems():
            try:
                del cssdata[bg_property]
            except:
                pass

        #Add new background property
        if new_bg_value != '':
            cssdata['background'] = new_bg_value + important

        return cssdata

    def __merge_4value_shorthands(self, cssdata):
        """
            Merges Shorthand properties again, the opposite of dissolve_4value_shorthands()
            @cssdata (dict) is a dictionary of the selector properties
        """
        for key, value in data.shorthands.iteritems():
            important = ''
            if value != 0 and cssdata.has_key(value[0]) and cssdata.has_key(value[1]) and cssdata.has_key(value[2]) and cssdata.has_key(value[3]):
                cssdata[key] = ''

                for i in xrange(4):
                    val = cssdata[value[i]]
                    if self.parser.is_important(val):
                        important = '!important'
                        cssdata[key] += self.parser.gvw_important(val) + ' '

                    else:
                        cssdata[key] += val + ' '

                    del cssdata[value[i]]
            if cssdata.has_key(key):
                cssdata[key] = self.__shorthand(cssdata[key] + important.strip())

        return cssdata


    def __merge_selectors(self):
        """
            Merges selectors with same properties. Example: a{color:red} b{color:red} . a,b{color:red}
            Very basic and has at least one bug. Hopefully there is a replacement soon.
            @selector_one (string) is the current selector
            @value_one (dict) is a dictionary of the selector properties
            Note: Currently is the elements of a selector are identical, but in a different order, they are not merged
        """

        ##OPTIMIZE##
        ##FIX##

        raw_css = self._optimized_css.copy()
        delete = []
        add = SortedDict()
        for media, css in raw_css.iteritems():
            for selector_one, value_one in css.iteritems():
                newsel = selector_one

                for selector_two, value_two in css.iteritems():
                    if selector_one == selector_two:
                        #We need to skip self
                        continue

                    if value_one == value_two:
                        #Ok, we need to merge these two selectors
                        newsel += ', ' + selector_two
                        delete.append((media, selector_two))


        if not add.has_key(media):
            add[media] = SortedDict()

        add[media][newsel] = value_one
        delete.append((media, selector_one))

        for item in delete:
            try:
                del self._optimized_css[item[0]][item[1]]
            except:
                #Must have already been deleted
                continue

        for media, css in add.iteritems():
            self._optimized_css[media].update(css)



    def __shorthand(self, value):
        """
            Compresses shorthand values. Example: margin:1px 1px 1px 1px . margin:1px
            @value (string)
        """

        ##FIX##

        important = '';
        if self.parser.is_important(value):
            value_list = self.parser.gvw_important(value)
            important = '!important'
        else:
            value_list = value

        ret = value
        value_list = value_list.split(' ')

        if len(value_list) == 4:
            if value_list[0] == value_list[1] and value_list[0] == value_list[2] and value_list[0] == value_list[3]:
                ret = value_list[0] + important

            elif value_list[1] == value_list[3] and value_list[0] == value_list[2]:
                ret = value_list[0] + ' ' + value_list[1] + important

            elif value_list[1] == value_list[3]:
                ret = value_list[0] + ' ' + value_list[1] + ' ' + value_list[2] + important

        elif len(value_list) == 3:
            if value_list[0] == value_list[1] and value_list[0] == value_list[2]:
                ret = value_list[0] + important

            elif value_list[0] == value_list[2]:
                return value_list[0] + ' ' + value_list[1] + important

        elif len(value_list) == 2:
            if value_list[0] == value_list[1]:
                ret = value_list[0] + important

        if ret != value:
            self.parser.log('Optimised shorthand notation: Changed "' + value + '" to "' + ret + '"', 'Information')

        return ret

    def __compress_important(self, value):
        """
            Removes unnecessary whitespace in ! important
            @value (string)
        """
        if self.parser.is_important(value):
            value = self.parser.gvw_important(value) + '!important'

        return value

    def __compress_numbers(self, prop, value):
        """
            Compresses numbers (ie. 1.0 becomes 1 or 1.100 becomes 1.1 )
            @value (string) is the posible number to be compressed
        """

        ##FIX##

        value = value.split('/')

        for l in xrange(len(value)):
            #continue if no numeric value
            if not (len(value[l]) > 0 and (value[l][0].isdigit() or value[l][0] in ('+', '-') )):
                continue

            #Fix bad colors
            if prop in data.color_values:
                value[l] = '#' + value[l]

            is_floatable = False
            try:
                float(value[l])
                is_floatable = True
            except:
                pass

            if is_floatable and float(value[l]) == 0:
                value[l] = '0'

            elif value[l][0] != '#':
                unit_found = False
                for unit in data.units:
                    pos = value[l].lower().find(unit)
                    if pos != -1 and prop not in data.shorthands:
                        value[l] = self.__remove_leading_zeros(float(value[l][:pos])) + unit
                        unit_found = True
                        break;

                if not unit_found and prop in data.unit_values and prop not in data.shorthands:
                    value[l] = self.__remove_leading_zeros(float(value[l])) + 'px'

                elif not unit_found and prop not in data.shorthands:
                    value[l] = self.__remove_leading_zeros(float(value[l]))


        if len(value) > 1:
            return '/'.join(value)

        return value[0]

    def __remove_leading_zeros(self, float_val):
        """
            Removes the leading zeros from a float value
            @float_val (float)
            @returns (string)
        """
        #Remove leading zero
        if abs(float_val) < 1:
            if float_val < 0:
                float_val = '-' . str(float_val)[2:]
            else:
                float_val = str(float_val)[1:]

        return str(float_val)

    def __compress_color(self, color):
        """
            Color compression function. Converts all rgb() values to #-values and uses the short-form if possible. Also replaces 4 color names by #-values.
            @color (string) the {posible} color to change
        """

        #rgb(0,0,0) . #000000 (or #000 in this case later)
        if color[:4].lower() == 'rgb(':
            color_tmp = color[4:(len(color)-5)]
            color_tmp = color_tmp.split(',')

            for c in color_tmp:
                c = c.strip()
                if c[:-1] == '%':
                    c = round((255*color_tmp[i])/100)

                if color_tmp[i] > 255:
                    color_tmp[i] = 255

            color = '#'

            for i in xrange(3):
                if color_tmp[i] < 16:
                    color += '0' + str(hex(color_tmp[i])).replace('0x', '')
                else:
                    color += str(hex(color_tmp[i])).replace('0x', '')

        #Fix bad color names
        if data.replace_colors.has_key(color.lower()):
            color = data.replace_colors[color.lower()]

        #aabbcc . #abc
        if len(color) == 7:
            color_temp = color.lower()
            if color_temp[0] == '#' and color_temp[1] == color_temp[2] and color_temp[3] == color_temp[4] and color_temp[5] == color_temp[6]:
                color = '#' + color[1] + color[3] + color[5]

        if data.optimize_colors.has_key(color.lower()):
            color = data.optimize_colors[color.lower()]

        return color
########NEW FILE########
__FILENAME__ = output
# CSSTidy - CSS Printer
#
# CSS Printer class
#
# This file is part of CSSTidy.
#
# CSSTidy is free software you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation either version 2 of the License, or
# (at your option) any later version.
#
# CSSTidy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CSSTidy if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# @license http://opensource.org/licenses/gpl-license.php GNU Public License
# @package csstidy
# @author Dj Gilcrease (digitalxero at gmail dot com) 2005-2006

import data

class CSSPrinter(object):
    def __init__(self, parser):
        self.parser = parser
        self._css = {}
        self.__renderMethods = {'string': self.__renderString, 'file': self.__renderFile}

#PUBLIC METHODS
    def prepare(self, css):
        self._css = css

    def render(self, output="string", *args, **kwargs):
        return self.__renderMethods[output](*args, **kwargs)

#PRIVATE METHODS
    def __renderString(self, *args, **kwargs):
        ##OPTIMIZE##
        template = self.parser.getSetting('template')
        ret = ""

        if template == 'highest_compression':
            top_line_end = ""
            iner_line_end = ""
            bottom_line_end = ""
            indent = ""

        elif template == 'high_compression':
            top_line_end = "\n"
            iner_line_end = ""
            bottom_line_end = "\n"
            indent = ""

        elif template == 'default':
            top_line_end = "\n"
            iner_line_end = "\n"
            bottom_line_end = "\n\n"
            indent = ""

        elif template == 'low_compression':
            top_line_end = "\n"
            iner_line_end = "\n"
            bottom_line_end = "\n\n"
            indent = "    "

        if self.parser.getSetting('timestamp'):
            ret += '/# CSSTidy ' + self.parser.version + ': ' + datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000") + ' #/' + top_line_end

        for item in self.parser._import:
            ret += '@import(' + item + ');' + top_line_end

        for item in self.parser._charset:
            ret += '@charset(' + item + ');' + top_line_end

        for item in self.parser._namespace:
            ret += '@namespace(' + item + ');' + top_line_end

        for media, css in self._css.iteritems():
            for selector, cssdata in css.iteritems():
                ret += selector + '{' + top_line_end

                for item, value in cssdata.iteritems():
                    ret += indent +  item + ':' + value + ';' + iner_line_end

                ret += '}' + bottom_line_end

        return ret

    def __renderFile(self, filename=None, *args, **kwargs):
        if filename is None:
            return self.__renderString()

        try:
            f = open(filename, "w")
            f.write(self.__renderString())
        finally:
            f.close()
########NEW FILE########
__FILENAME__ = tools

class SortedDict(dict):
    """
    A dictionary that keeps its keys in the order in which they're inserted.
    """
    def __init__(self, data=None):
        if data is None:
            data = {}
        super(SortedDict, self).__init__(data)
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
        super(SortedDict, self).__setitem__(key, value)
        if key not in self.keyOrder:
            self.keyOrder.append(key)

    def __delitem__(self, key):
        super(SortedDict, self).__delitem__(key)
        self.keyOrder.remove(key)

    def __iter__(self):
        for k in self.keyOrder:
            yield k

    def pop(self, k, *args):
        result = super(SortedDict, self).pop(k, *args)
        try:
            self.keyOrder.remove(k)
        except ValueError:
            # Key wasn't in the dictionary in the first place. No problem.
            pass
        return result

    def popitem(self):
        result = super(SortedDict, self).popitem()
        self.keyOrder.remove(result[0])
        return result

    def items(self):
        return zip(self.keyOrder, self.values())

    def iteritems(self):
        for key in self.keyOrder:
            yield key, super(SortedDict, self).__getitem__(key)

    def keys(self):
        return self.keyOrder[:]

    def iterkeys(self):
        return iter(self.keyOrder)

    def values(self):
        return [super(SortedDict, self).__getitem__(k) for k in self.keyOrder]

    def itervalues(self):
        for key in self.keyOrder:
            yield super(SortedDict, self).__getitem__(key)

    def update(self, dict_):
        for k, v in dict_.items():
            self.__setitem__(k, v)

    def setdefault(self, key, default):
        if key not in self.keyOrder:
            self.keyOrder.append(key)
        return super(SortedDict, self).setdefault(key, default)

    def value_for_index(self, index):
        """Returns the value of the item at the given zero-based index."""
        return self[self.keyOrder[index]]

    def insert(self, index, key, value):
        """Inserts the key, value pair before the item with the given index."""
        if key in self.keyOrder:
            n = self.keyOrder.index(key)
            del self.keyOrder[n]
            if n < index:
                index -= 1
        self.keyOrder.insert(index, key)
        super(SortedDict, self).__setitem__(key, value)

    def copy(self):
        """Returns a copy of this object."""
        # This way of initializing the copy means it works for subclasses, too.
        obj = self.__class__(self)
        obj.keyOrder = self.keyOrder[:]
        return obj

    def __repr__(self):
        """
        Replaces the normal dict.__repr__ with a version that returns the keys
        in their sorted order.
        """
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def clear(self):
        super(SortedDict, self).clear()
        self.keyOrder = []
########NEW FILE########
__FILENAME__ = jsmin
#!/usr/bin/python

# This code is original from jsmin by Douglas Crockford, it was translated to
# Python by Baruch Even. The original code had the following copyright and
# license.
#
# /* jsmin.c
#    2007-05-22
#
# Copyright (c) 2002 Douglas Crockford  (www.crockford.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# The Software shall be used for Good, not Evil.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# */

from StringIO import StringIO

def jsmin(js):
    ins = StringIO(js)
    outs = StringIO()
    JavascriptMinify().minify(ins, outs)
    str = outs.getvalue()
    if len(str) > 0 and str[0] == '\n':
        str = str[1:]
    return str

def isAlphanum(c):
    """return true if the character is a letter, digit, underscore,
           dollar sign, or non-ASCII character.
    """
    return ((c >= 'a' and c <= 'z') or (c >= '0' and c <= '9') or
            (c >= 'A' and c <= 'Z') or c == '_' or c == '$' or c == '\\' or (c is not None and ord(c) > 126));

class UnterminatedComment(Exception):
    pass

class UnterminatedStringLiteral(Exception):
    pass

class UnterminatedRegularExpression(Exception):
    pass

class JavascriptMinify(object):

    def _outA(self):
        self.outstream.write(self.theA)
    def _outB(self):
        self.outstream.write(self.theB)

    def _get(self):
        """return the next character from stdin. Watch out for lookahead. If
           the character is a control character, translate it to a space or
           linefeed.
        """
        c = self.theLookahead
        self.theLookahead = None
        if c == None:
            c = self.instream.read(1)
        if c >= ' ' or c == '\n':
            return c
        if c == '': # EOF
            return '\000'
        if c == '\r':
            return '\n'
        return ' '

    def _peek(self):
        self.theLookahead = self._get()
        return self.theLookahead

    def _next(self):
        """get the next character, excluding comments. peek() is used to see
           if a '/' is followed by a '/' or '*'.
        """
        c = self._get()
        if c == '/':
            p = self._peek()
            if p == '/':
                c = self._get()
                while c > '\n':
                    c = self._get()
                return c
            if p == '*':
                c = self._get()
                while 1:
                    c = self._get()
                    if c == '*':
                        if self._peek() == '/':
                            self._get()
                            return ' '
                    if c == '\000':
                        raise UnterminatedComment()

        return c

    def _action(self, action):
        """do something! What you do is determined by the argument:
           1   Output A. Copy B to A. Get the next B.
           2   Copy B to A. Get the next B. (Delete A).
           3   Get the next B. (Delete B).
           action treats a string as a single character. Wow!
           action recognizes a regular expression if it is preceded by ( or , or =.
        """
        if action <= 1:
            self._outA()

        if action <= 2:
            self.theA = self.theB
            if self.theA == "'" or self.theA == '"':
                while 1:
                    self._outA()
                    self.theA = self._get()
                    if self.theA == self.theB:
                        break
                    if self.theA <= '\n':
                        raise UnterminatedStringLiteral()
                    if self.theA == '\\':
                        self._outA()
                        self.theA = self._get()


        if action <= 3:
            self.theB = self._next()
            if self.theB == '/' and (self.theA == '(' or self.theA == ',' or
                                     self.theA == '=' or self.theA == ':' or
                                     self.theA == '[' or self.theA == '?' or
                                     self.theA == '!' or self.theA == '&' or
                                     self.theA == '|' or self.theA == ';' or
                                     self.theA == '{' or self.theA == '}' or
                                     self.theA == '\n'):
                self._outA()
                self._outB()
                while 1:
                    self.theA = self._get()
                    if self.theA == '/':
                        break
                    elif self.theA == '\\':
                        self._outA()
                        self.theA = self._get()
                    elif self.theA <= '\n':
                        raise UnterminatedRegularExpression()
                    self._outA()
                self.theB = self._next()


    def _jsmin(self):
        """Copy the input to the output, deleting the characters which are
           insignificant to JavaScript. Comments will be removed. Tabs will be
           replaced with spaces. Carriage returns will be replaced with linefeeds.
           Most spaces and linefeeds will be removed.
        """
        self.theA = '\n'
        self._action(3)

        while self.theA != '\000':
            if self.theA == ' ':
                if isAlphanum(self.theB):
                    self._action(1)
                else:
                    self._action(2)
            elif self.theA == '\n':
                if self.theB in ['{', '[', '(', '+', '-']:
                    self._action(1)
                elif self.theB == ' ':
                    self._action(3)
                else:
                    if isAlphanum(self.theB):
                        self._action(1)
                    else:
                        self._action(2)
            else:
                if self.theB == ' ':
                    if isAlphanum(self.theA):
                        self._action(1)
                    else:
                        self._action(3)
                elif self.theB == '\n':
                    if self.theA in ['}', ']', ')', '+', '-', '"', '\'']:
                        self._action(1)
                    else:
                        if isAlphanum(self.theA):
                            self._action(1)
                        else:
                            self._action(3)
                else:
                    self._action(1)

    def minify(self, instream, outstream):
        self.instream = instream
        self.outstream = outstream
        self.theA = '\n'
        self.theB = None
        self.theLookahead = None

        self._jsmin()
        self.instream.close()

if __name__ == '__main__':
    import sys
    jsm = JavascriptMinify()
    jsm.minify(sys.stdin, sys.stdout)
########NEW FILE########
__FILENAME__ = filter_base
class FilterBase:
    def __init__(self, verbose):
        self.verbose = verbose

    def filter_css(self, css):
        raise NotImplementedError
    def filter_js(self, js):
        raise NotImplementedError
        
class FilterError(Exception):
    """
    This exception is raised when a filter fails
    """
    pass
########NEW FILE########
__FILENAME__ = synccompress
from django.core.management.base import NoArgsCommand
from optparse import make_option

from django.conf import settings

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--force', action='store_true', default=False, help='Force update of all files, even if the source files are older than the current compressed file.'),
    )
    help = 'Updates and compresses CSS and JavsScript on-demand, without restarting Django'
    args = ''

    def handle_noargs(self, **options):
        
        force = options.get('force', False)
        verbosity = int(options.get('verbosity', 1))

        from compress.utils import needs_update, filter_css, filter_js

        for name, css in settings.COMPRESS_CSS.items():
            u, version = needs_update(css['output_filename'], 
                css['source_filenames'])

            if (force or u) or verbosity >= 2:
                msg = 'CSS Group \'%s\'' % name
                print msg
                print len(msg) * '-'
                print "Version: %s" % version

            if force or u:
                filter_css(css, verbosity)

            if (force or u) or verbosity >= 2:
                print

        for name, js in settings.COMPRESS_JS.items():
            u, version = needs_update(js['output_filename'], 
                js['source_filenames'])

            if (force or u) or verbosity >= 2:
                msg = 'JavaScript Group \'%s\'' % name
                print msg
                print len(msg) * '-'
                print "Version: %s" % version

            if force or u:
                filter_js(js, verbosity)

            if (force or u) or verbosity >= 2:
                print

# Backwards compatibility for Django r9110
if not [opt for opt in Command.option_list if opt.dest=='verbosity']:
    Command.option_list += (
    make_option('--verbosity', '-v', action="store", dest="verbosity",
        default='1', type='choice', choices=['0', '1', '2'],
        help="Verbosity level; 0=minimal output, 1=normal output, 2=all output"),
    )

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

css_filtered = Signal()
js_filtered = Signal()

########NEW FILE########
__FILENAME__ = compressed
import os

from django import template

from django.conf import settings as django_settings

from compress.conf import settings
from compress.utils import media_root, media_url, needs_update, filter_css, filter_js, get_output_filename, get_version, get_version_from_file

register = template.Library()

def render_common(template_name, obj, filename, version):
    if settings.COMPRESS:
        filename = get_output_filename(filename, version)

    context = obj.get('extra_context', {})
    prefix = context.get('prefix', None)
    if filename.startswith('http://'):
        context['url'] = filename
    else:
        context['url'] = media_url(filename, prefix)
        
    return template.loader.render_to_string(template_name, context)

def render_css(css, filename, version=None):
    return render_common(css.get('template_name', 'compress/css.html'), css, filename, version)

def render_js(js, filename, version=None):
    return render_common(js.get('template_name', 'compress/js.html'), js, filename, version)

class CompressedCSSNode(template.Node):
    def __init__(self, name):
        self.name = name

    def render(self, context):
        css_name = template.Variable(self.name).resolve(context)

        try:
            css = settings.COMPRESS_CSS[css_name]
        except KeyError:
            return '' # fail silently, do not return anything if an invalid group is specified

        if settings.COMPRESS:

            version = None

            if settings.COMPRESS_AUTO:
                u, version = needs_update(css['output_filename'], 
                    css['source_filenames'])
                if u:
                    filter_css(css)
            else:
                filename_base, filename = os.path.split(css['output_filename'])
                path_name = media_root(filename_base)
                version = get_version_from_file(path_name, filename)
                
            return render_css(css, css['output_filename'], version)
        else:
            # output source files
            r = ''
            for source_file in css['source_filenames']:
                r += render_css(css, source_file)

            return r

class CompressedJSNode(template.Node):
    def __init__(self, name):
        self.name = name

    def render(self, context):
        js_name = template.Variable(self.name).resolve(context)

        try:
            js = settings.COMPRESS_JS[js_name]
        except KeyError:
            return '' # fail silently, do not return anything if an invalid group is specified
        
        if 'external_urls' in js:
            r = ''
            for url in js['external_urls']:
                r += render_js(js, url)
            return r
                    
        if settings.COMPRESS:

            version = None

            if settings.COMPRESS_AUTO:
                u, version = needs_update(js['output_filename'], 
                    js['source_filenames'])
                if u:
                    filter_js(js)
            else: 
                filename_base, filename = os.path.split(js['output_filename'])
                path_name = media_root(filename_base)
                version = get_version_from_file(path_name, filename)

            return render_js(js, js['output_filename'], version)
        else:
            # output source files
            r = ''
            for source_file in js['source_filenames']:
                r += render_js(js, source_file)
            return r

#@register.tag
def compressed_css(parser, token):
    try:
        tag_name, name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, '%r requires exactly one argument: the name of a group in the COMPRESS_CSS setting' % token.split_contents()[0]

    return CompressedCSSNode(name)
compressed_css = register.tag(compressed_css)

#@register.tag
def compressed_js(parser, token):
    try:
        tag_name, name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, '%r requires exactly one argument: the name of a group in the COMPRESS_JS setting' % token.split_contents()[0]

    return CompressedJSNode(name)
compressed_js = register.tag(compressed_js)

########NEW FILE########
__FILENAME__ = utils
import os
import re
import tempfile

from django.conf import settings as django_settings
from django.utils.http import urlquote
from django.dispatch import dispatcher

from compress.conf import settings
from compress.signals import css_filtered, js_filtered

def get_class(class_string):
    """
    Convert a string version of a function name to the callable object.
    """

    if not hasattr(class_string, '__bases__'):

        try:
            class_string = class_string.encode('ascii')
            mod_name, class_name = get_mod_func(class_string)
            if class_name != '':
                class_string = getattr(__import__(mod_name, {}, {}, ['']), class_name)
        except (ImportError, AttributeError):
            raise Exception('Failed to import filter %s' % class_string)

    return class_string

def get_mod_func(callback):
    """
    Converts 'django.views.news.stories.story_detail' to
    ('django.views.news.stories', 'story_detail')
    """

    try:
        dot = callback.rindex('.')
    except ValueError:
        return callback, ''
    return callback[:dot], callback[dot+1:]

def needs_update(output_file, source_files, verbosity=0):
    """
    Scan the source files for changes and returns True if the output_file needs to be updated.
    """

    version = get_version(source_files)
    
    on = get_output_filename(output_file, version)
    compressed_file_full = media_root(on)

    if not os.path.exists(compressed_file_full):
        return True, version
        
    update_needed = getattr(get_class(settings.COMPRESS_VERSIONING)(), 'needs_update')(output_file, source_files, version)
    return update_needed

def media_root(filename):
    """
    Return the full path to ``filename``. ``filename`` is a relative path name in MEDIA_ROOT
    """
    return os.path.join(django_settings.MEDIA_ROOT, filename)

def media_url(url, prefix=None):
    if prefix:
        return prefix + urlquote(url)
    return django_settings.MEDIA_URL + urlquote(url)

def concat(filenames, separator=''):
    """
    Concatenate the files from the list of the ``filenames``, ouput separated with ``separator``.
    """
    r = ''
    for filename in filenames:
        fd = open(media_root(filename), 'rb')
        r += fd.read()
        r += separator
        fd.close()
    return r

def max_mtime(files):
    return int(max([os.stat(media_root(f)).st_mtime for f in files]))

def save_file(filename, contents):
    dirname = os.path.dirname(media_root(filename))
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    fd = open(media_root(filename), 'wb+')
    fd.write(contents)
    fd.close()

def get_output_filename(filename, version):
    if settings.COMPRESS_VERSION and version is not None:
        return filename.replace(settings.COMPRESS_VERSION_PLACEHOLDER, version)
    else:
        return filename.replace(settings.COMPRESS_VERSION_PLACEHOLDER, settings.COMPRESS_VERSION_DEFAULT)

def get_version(source_files, verbosity=0):
    version = getattr(get_class(settings.COMPRESS_VERSIONING)(), 'get_version')(source_files)
    return version
    
def get_version_from_file(path, filename):
    regex = re.compile(r'^%s$' % (get_output_filename(settings.COMPRESS_VERSION_PLACEHOLDER.join([re.escape(part) for part in filename.split(settings.COMPRESS_VERSION_PLACEHOLDER)]), r'([A-Za-z0-9]+)')))
    for f in os.listdir(path):
        result = regex.match(f)
        if result and result.groups():
            return result.groups()[0]

def remove_files(path, filename, verbosity=0):    
    regex = re.compile(r'^%s$' % (os.path.basename(get_output_filename(settings.COMPRESS_VERSION_PLACEHOLDER.join([re.escape(part) for part in filename.split(settings.COMPRESS_VERSION_PLACEHOLDER)]), r'[A-Za-z0-9]+'))))
    if os.path.exists(path):
        for f in os.listdir(path):
            if regex.match(f):
                if verbosity >= 1:
                    print "Removing outdated file %s" % f
        
                os.unlink(os.path.join(path, f))

def filter_common(obj, verbosity, filters, attr, separator, signal):
    output = concat(obj['source_filenames'], separator)
    
    filename = get_output_filename(obj['output_filename'], get_version(obj['source_filenames']))

    if settings.COMPRESS_VERSION:
        remove_files(os.path.dirname(media_root(filename)), obj['output_filename'], verbosity)

    if verbosity >= 1:
        print "Saving %s" % filename

    for f in filters:
        output = getattr(get_class(f)(verbose=(verbosity >= 2)), attr)(output)

    save_file(filename, output)
    signal.send(None)

def filter_css(css, verbosity=0):
    return filter_common(css, verbosity, filters=settings.COMPRESS_CSS_FILTERS, attr='filter_css', separator='', signal=css_filtered)

def filter_js(js, verbosity=0):
    return filter_common(js, verbosity, filters=settings.COMPRESS_JS_FILTERS, attr='filter_js', separator='', signal=js_filtered)

########NEW FILE########
__FILENAME__ = base
class VersioningBase(object):

    def get_version(self, source_files):
        raise NotImplementedError
        
    def needs_update(self, output_file, source_files, version):
        raise NotImplementedError
        
class VersioningError(Exception):
    """
    This exception is raised when version creation fails
    """
    pass
########NEW FILE########
