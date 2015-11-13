__FILENAME__ = accessor
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.node import Node


ACCESSOR = re.compile('''
    (?P<value>
        [a-z 0-9 \- _ \* \. \s , : # &]+?
        (
            \s*
            >
            
            \s*
            [a-z 0-9 \- _ \* \. \s , : # &]+?
        )+
    |
        [a-z 0-9 \- _ \* \. \s , : # &]+?
        \[
            .+?
        \]
    )
    
    \s*
    
    (
        ;
    |
        }
    )
''', re.DOTALL | re.VERBOSE)


def parse_accessor(less, parent=None, **kwargs):
    match = ACCESSOR.match(less)
    
    if not match:
        raise ValueError()
    
    code = match.group()
    accessor = match.group('value')
    
    return Accessor(accessor=accessor, code=code, parent=parent)


class Accessor(Node):
    
    __slots__ = ('__accessor',)
    
    def __init__(self, accessor, code, parent):
        Node.__init__(self, code=code, parent=parent)
        
        self.__accessor = accessor
        
    def __get_accessor(self):
        return self.__accessor
        
    accessor = property(fget=__get_accessor)
########NEW FILE########
__FILENAME__ = comment
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.node import Node


COMMENT = re.compile('''
    /\*
    
    (?P<comment>
        .*?
    )

    \*/
''', re.DOTALL | re.VERBOSE)


LESS_COMMENT = re.compile(r'''
    //
    
    (?P<comment>
        .*?
    )
    
    (
        \n
    |
        $
    )
''', re.VERBOSE)


def parse_comment(less, parent, **kwargs):
    match = COMMENT.match(less)
    
    if not match:
        match = LESS_COMMENT.match(less)
    
    if not match:
        raise ValueError()
    
    code = match.group()
    comment = match.group('comment')
    
    return Comment(code=code, comment=comment, parent=parent)


class Comment(Node):
    
    __slots__ = ('__comment',)
    
    def __init__(self, code, comment, parent):
        Node.__init__(self, code=code, parent=parent)
        
        self.__comment = comment
        
    def __get_comment(self):
        return self.__comment
        
    comment = property(fget=__get_comment)

########NEW FILE########
__FILENAME__ = constant
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.node import Node
from lesscss.property import Property


CONSTANT = re.compile('''
    (?P<name>
        @
        [a-z0-9\-_]+
    )
    
    \s*
    
    :
    
    \s*
    
    (?P<value>
        .+?
    )
    
    \s*
    
    ;
''', re.VERBOSE)


def parse_constant(less, parent, **kwargs):
    match = CONSTANT.match(less)
    
    if not match:
        raise ValueError()
        
    code = match.group()
    name = match.group('name')
    value = match.group('value')
    
    return Constant(code=code, name=name, parent=parent, value=value)
    
    
class Constant(Property):
    pass

########NEW FILE########
__FILENAME__ = console
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

Copyright (c) 2011 Evgeny V. Generalov. 
mailto:e.generalov@gmail.com
"""
import sys
import locale


class Writer(object):
    """text writer"""

    def __init__(self, output=None, out_encoding=None):
        self.out = None
        self.out_encoding = out_encoding
        self.set_output(output)

    def set_output(self, output=None):
        """set output stream"""
        self.out = output or sys.stdout

    def write(self, string):
        """write a string to the output"""
        self.out.write(self._encode(string))

    def writeln(self, string):
        """write a line to the output"""
        print >> self.out, self._encode(string)

    def _encode(self, data):
        """encode data to string"""
        # py3k streams handle their encoding :
        if sys.version_info >= (3, 0):
            return data
        if not isinstance(data, unicode):
            return data
        # data is string
        encoding = (self.out_encoding or
                    getattr(self.out, 'encoding', None) or
                    locale.getdefaultlocale()[1] or
                    sys.getdefaultencoding())
        return data.encode(encoding)


########NEW FILE########
__FILENAME__ = importer
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import os, re
from lesscss.node import Node


IMPORT = re.compile('''
    @import
    
    \s*
    
    (
        (?P<filename>
            '.*?(?!\\\\)'
        |
            ".*?(?!\\\\)"
        )
    |
        url\(
            (?P<url>
                .*?(?!\\\\)
            )
        \)
    )
    
    (
        \s*
    
        (?P<media>
            [a-z \s ,]*
        )
    )?
    
    \s*
    
    ;?
''', re.DOTALL | re.VERBOSE)


def read_file(filename, path):
    if not filename.endswith('.less'):
        filename += '.less'
        
    if path:
        filename = os.path.join(path, filename)

    handle = file(filename)
    
    return handle.read().strip()


def parse_import(less, parent=None, path=None, **kwargs):
    match = IMPORT.match(less)
    
    if not match:
        raise ValueError()
    
    code = match.group()
    
    media = [media.strip() for media in match.group('media').split(',')]
        
    media = tuple(media)
    
    if len(media) == 1 and media[0] == '':
        media = None
        
    filename = match.group('filename')
    
    if filename:
        # strip the quotation marks around the filename
        filename = filename[1:-1]
        
        less = read_file(filename, path)
        
        return Importer(parent, code, less, media=media)
    else:
        url = match.group('url')
        
        return CSSImport(parent=parent, code=code, target=media, url=url)
        
        
class CSSImport(Node):

    __slots__ = ('__target', '__url')
    
    def __init__(self, parent, code, target, url):
        Node.__init__(self, parent=parent, code=code)
        
        self.__target = target
        self.__url    = url
        
    def __get_target(self):
        return self.__target
        
    def __get_url(self):
        return self.__url
    
    target = property(fget=__get_target)
    url    = property(fget=__get_url)


class Importer(Node):
    
    __slots__ = ('__less', '__media')
    
    def __init__(self, parent, code, less, media):
        Node.__init__(self, parent=parent, code=code)
        
        self.__less  = less
        self.__media = media

    def __get_less(self):
        return self.__less
        
    def __get_media(self):
        return self.__media

    less  = property(fget=__get_less)
    media = property(fget=__get_media)
########NEW FILE########
__FILENAME__ = lessc
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


from lesscss.accessor import parse_accessor
from lesscss.comment  import parse_comment
from lesscss.constant import parse_constant
from lesscss.importer import parse_import
from lesscss.media    import parse_media, Media
from lesscss.mixin    import parse_mixin
from lesscss.property import parse_property
from lesscss.rules    import Rules
from lesscss.selector import parse_selector


PARSERS = (parse_accessor,
           parse_comment,
           parse_constant,
           parse_import,
           parse_media,
           parse_mixin,
           parse_property,
           parse_selector)


def compile(less, path=None):
    css = ''
    
    parsed = Rules(code=less)

    parse(less, path=path, parent=parsed)
        
    return unicode(parsed)


def parse(less, parent, path=None):
    # get rid of whitespace at the end of the less code
    less = less.rstrip()
    
    # keep reading the less code until no more exists
    while less:
    
        # get rid of whitespace before the less code
        less = less.lstrip()
        
        # give all of the parsers a shot at reading the remainder
        for parser in PARSERS:
        
            # parsers will throw a ValueError exception if they fail
            try:
                parsed_item = parser(less, path=path, parent=parent)

            # when the parser fails...
            except ValueError:
            
                # ...try the next one
                pass
            
            # when the parser is successful
            else:
            
                # cache the parsed code
                code = parsed_item.code
            
                # find out how much less code to chop off
                code_length = len(code)
                
                # cache the following code
                following_code = less[:code_length]
                
                # check that it is next
                if following_code != code:
                    raise AssertionError('The following code is "%s" not "%s"' %
                                         (following_code, code))
            
                # remove it
                less = less[code_length:]
                
                # detect imports
                try:
                
                    imported_less = parsed_item.less
                    
                    media = parsed_item.media
                    
                    if media:
                    
                        imported_less = '@media %s {\n%s\n}' % \
                                        (', '.join(media), imported_less)
                
                    if less:
                
                        # add a safety gap
                        less += '\n'
                        
                    less += imported_less
                    
                    # then move on to the rest
                    break
                    
                except AttributeError:
                
                    pass
                
                try:
                
                    # read the contents of the nested rule
                    contents = parsed_item.contents
                    
                    # if there are any contents then parse them
                    if contents:
                    
                        # parse the contents
                        parse(contents, parent=parsed_item, path=path)
                
                except AttributeError:
                
                    pass
                        
                # add the parsed item to its parent
                try:
                    parent.items.append(parsed_item)
                except AttributeError:
                    pass
                
                # then move on to the rest
                break;

        # if all of the parsers fail
        else:
        
            # report an error with the less code
            raise ValueError('Unable to read onwards from: %s' % less)


if __name__ == '__main__':
    import optparse
    import sys
    import traceback

    from lesscss.contrib import console

    usage = "usage: %prog [source [destination]]"
    parser = optparse.OptionParser(usage=usage)
    (options, argv) = parser.parse_args()

    def main(argv):
        source = open(argv[0]) if len(argv) > 0 else sys.stdin
        destination = argv[1] if len(argv) > 1 else sys.stdout
        output = console.Writer(destination)
        output.write(compile(source.read()))

    try:
        main(argv)
    except Exception, e:
        console.Writer(sys.stderr).writeln(
                traceback.format_exc() if __debug__
                else str(e))
        sys.exit(1)


########NEW FILE########
__FILENAME__ = media
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.nested import parse_nested
from lesscss.rules import Rules


MEDIA = re.compile('''
    (?P<names>
        @media
            
        \s*
        
        (?P<media>
        
            [a-z]+
            
            \s*
            
            (
                ,
                
                \s*
                
                [a-z]+
                
                \s*
                
            )*?
        
        )
    )

    \s*

    {
''', re.DOTALL | re.IGNORECASE | re.VERBOSE)


def parse_media(less, parent=None, **kwargs):
    match = MEDIA.match(less)

    if not match:
        raise ValueError()

    media = [media.strip() for media in match.group('media').split(',')]

    matched_length = len(match.group())

    remaining_less = less[matched_length:]

    contents = parse_nested(remaining_less)

    code = match.group() + contents + '}'

    return Media(code=code, media=media, contents=contents, parent=parent)


class Media(Rules):

    __slots__ = ('__media',)

    def __init__(self, parent, code, media, contents=None):
        Rules.__init__(self, parent=parent, code=code, contents=contents)

        self.__media = media
        
    def __get_media(self):
        return self.__media

    media = property(fget=__get_media)
########NEW FILE########
__FILENAME__ = mixin
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.nested   import parse_nested
from lesscss.params   import Param, parse_params
from lesscss.property import Property
from lesscss.rules    import Rules


MIXIN = re.compile('''
    (?P<name>
        \.
        [a-z 0-9 \- _ \* \s , :]+
    )

    \s*

    (
        (?P<param_detect>
            \(

            (?P<params>
                .*?
            )
        )

        \)

        \s*
    )?

    \s*

    (
        (?P<nested>
            {
        )
    |
        ;
    |
        }
    )
''', re.DOTALL | re.VERBOSE)


def parse_mixin(less, parent=None, **kwargs):
    match = MIXIN.match(less)

    if not match:
        raise ValueError()

    code = match.group()

    contents = None

    if match.group('nested'):
        matched_length = len(match.group())

        remaining_less = less[matched_length:]

        contents = parse_nested(remaining_less)

        code += contents + '}'

    params = parse_params(match.group('params'))

    if contents:
        for param in params:
            if param['value'] and not param['name']:
                param['name'] = param['value']
                param['value'] = None

    name = match.group('name')

    if match.group('nested') and not match.group('param_detect'):
        raise ValueError()

    return Mixin(parent=parent, code=code, name=name, params=params,
                 contents=contents)


class Mixin(Rules):

    __slots__ = ['__name', '__params']

    def __init__(self, parent, code, name, params, contents):
        Rules.__init__(self, parent=parent, code=code, contents=contents)

        self.__name = name
        self.__params = list()

        for param in params:
            param = Param(code=param['code'],
                          name=param['name'],
                          value=param['value'],
                          parent=self)

            self.__params.append(param)

    def __get_name(self):
        return self.__name

    def __get_params(self):
        return self.__params

    name = property(fget=__get_name)
    params = property(fget=__get_params)

########NEW FILE########
__FILENAME__ = nested
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


def parse_nested(less):
    nested = ''
    
    depth = 1
    
    delimiter = ''
    
    length = len(less)

    for i in range(length):
        char = less[i]
        
        if not (char == '}' and not depth and not delimiter):
            nested += char
        
        if delimiter:
            if char == delimiter and not less[i - 1] == '\\':
                delimiter = ''
        elif char in ('"', "'"):
            delimiter = char
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            
        if not depth and not delimiter and char == '}':
            break
    else:
        raise ValueError
    
    return nested[:-1]
########NEW FILE########
__FILENAME__ = node
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


from lesscss.value import get_value


class Node(object):

    __slots__ = ('__code', '__parent', 'items')

    def __init__(self, code, parent):
        self.__code = code
        self.__parent = parent

        self.items = list()

    def __str__(self):
        output = ''
        
        imports = self.get_imports()
        
        for url in imports.iterkeys():
            if output:
                output += '\n\n'
                
            output += '@import url(%s) %s;' % (url, ', '.join(imports[url]))

        for media in self.get_media_selectors():
            selectors = self.get_selectors(media=media)
        
            if not selectors:
                continue
        
            if media:
                output += '@media %s {\n' % ', '.join(media)

            for key in sorted(selectors.iterkeys()):
                selector = selectors[key]

                if not selector:
                    continue

                if output and not output[-2:] == '{\n':
                    output += '\n\n'
                    
                keys = sorted(selector.keys())
                
                if len(keys) == 1:
                    declaration = keys[0]
                    value = selector[declaration]
                
                    output += '%s { %s: %s; }' % (key, declaration, value)
                else:
                    output += '%s {\n' % key

                    for declaration in keys:
                        value = selector[declaration]

                        output += '  %s: %s;\n' % (declaration, value)

                    output += '}'
                
            if media:
                output += '\n}'

        return output

    def __get_code(self):
        return self.__code

    def __get_constants(self):
        try:
            constants = self.parent.constants
        except AttributeError:
            constants = dict()

        for item in self.items:
            try:
                name, value = item.name, item.value
            except AttributeError:
                pass
            else:
                if name[0] == '@':
                    constants[name] = value

        return constants
        
    def __get_media(self):
        try:
            return self.__media
        except AttributeError:
            pass
            
        parent = self.parent
            
        if parent:
            return parent.media
        else:
            return None

    def __get_parent(self):
        return self.__parent

    def get_declarations(self):
        declarations = dict()

        for item in self.items:
            try:
                name, value = item.name, item.value
            except AttributeError:
                pass
            else:
                if name[0] != '@':
                    declarations[name] = value
                continue
                
            try:
                name, params = item.name, item.params
            except AttributeError:
                pass
            else:
                mixin = self.get_mixin(name, params)
                
                mixin_declarations = mixin.get_declarations()
            
                for declaration in mixin_declarations:
                    declarations[declaration] = mixin_declarations[declaration]

        return declarations
        
    def get_imports(self):
        try:
            imports = self.parent.get_imports()
        except AttributeError:
            imports = dict()
            
        for item in self.items:
            try:
                target, url = item.target, item.url
            except AttributeError:
                pass
            else:
                try:
                    targets = imports[url]
                except KeyError:
                    targets = list()
                    imports[url] = targets
                
                for media in target:
                    if media not in targets:
                        targets.append(media)
                        
        return imports
        
    def get_media_selectors(self):
        media_selectors = list()
        
        media_selectors.append(None)
        
        try:
            media_selector = self.media
        except AttributeError:
            pass
        else:
            if media_selector not in media_selectors:
                media_selectors.append(media_selector)
        
        for item in self.items:
            for media_selector in item.get_media_selectors():
                if media_selector not in media_selectors:
                    media_selectors.append(media_selector)
        
        return tuple(media_selectors)
        
    def get_mixin(self, name, params):
        for item in self.items:
            if hasattr(item, 'params') and item.name == name and item.contents:
                return item
                
        for item in self.items:
            try:
                names = item.names
            except AttributeError:
                pass
            else:
                if name in names:
                    return item
        
        try:
            return self.parent.get_mixin(name, params)
        except AttributeError:
            raise AssertionError('mixin %s could not be found' % name)

    def get_selectors(self, media=None):
        selectors = dict()

        if self.media == media:        
            try:
                names = self.names
            except AttributeError:
                pass
            else:
                for name in names:
                    try:
                        selector = selectors[name]
                    except KeyError:
                        selector = dict()
                        selectors[name] = selector

                    declarations = self.get_declarations()

                    for key in declarations.iterkeys():
                        value = declarations[key]
                        value = self.get_value(value)
                        selector[key] = value

        for item in self.items:
            selectors.update(item.get_selectors(media=media))

        return selectors

    def get_value(self, less):
        constants = self.constants

        return get_value(less, constants)

    code      = property(fget=__get_code)
    constants = property(fget=__get_constants)
    media     = property(fget=__get_media)
    parent    = property(fget=__get_parent)

########NEW FILE########
__FILENAME__ = params
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.property import Property


PARAM = re.compile('''
    ^
    
    \s*
    
    (?P<name>
        [^:]+?
    )
    
    (
        \s*
    
        :
    
        \s*
        
        (?P<value>
            .+?
        )

    )?
    
    \s*
    
    $
''', re.DOTALL | re.VERBOSE)


def parse_params(less):
    params = list()
    
    depth = 0
    
    delimiter = ''
    
    chunk = ''
    
    try:
        length = len(less)
    except TypeError:
        return params

    for i in range(length):
        char = less[i]
        
        if not (char == ',' and not depth and not delimiter):
            chunk += char
        
        if delimiter:
            if char == delimiter and not less[i - 1] == '\\':
                delimiter = ''
        elif char in ('"', "'"):
            delimiter = char
        elif char == '(':
            depth += 1
        elif char == ')':
            depth -= 1
            
        if not depth and (char == ',' or i == length - 1):
            if char == ',' and i == length - 1:
                raise ValueError('Trailing param comma')
        
            match = PARAM.match(chunk)
            
            try:
                name, value = match.group('name'), match.group('value')
            except AttributeError:
                raise ValueError()
            
            if name and not value:
                value = name
                name = None
            
            param = {'code':  chunk,
                     'name':  name,
                     'value': value}
                     
            params.append(param)
            
            chunk = ''
            
    return params
    
    
class Param(Property):
    pass

########NEW FILE########
__FILENAME__ = property
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.node import Node


PROPERTY = re.compile('''
    (?P<name>
        [a-z0-9\-_]+
    )
    
    \s*
    
    :
    
    \s*
    
    (?P<value>
        [^;]+?
        (
            (
                '[^']*?(?!\\\\)'
            |
                "[^"]*?(?!\\\\)"
            )
            [^;'"]+?
        )*?
    )
    
    \s*
    
    (
        ;
    |
        $
    )
''', re.DOTALL | re.VERBOSE)


def parse_property(less, parent=None, **kwargs):
    match = PROPERTY.match(less)
    
    if not match:
        raise ValueError()
        
    code = match.group()
    name = match.group('name')
    value = match.group('value')
    
    return Property(parent=parent, code=code, name=name, value=value)


class Property(Node):
    
    __slots__ = ('__name', '__value')
    
    def __init__(self, code, name, parent, value):
        Node.__init__(self, code=code, parent=parent)
        
        self.__name = name
        self.__value = value
        
    def __get_name(self):
        return self.__name
        
    def __get_value(self):
        return self.__value
        
    name  = property(fget=__get_name)
    value = property(fget=__get_value)
########NEW FILE########
__FILENAME__ = rules
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


from lesscss.constant import Constant
from lesscss.node     import Node
from lesscss.property import Property


class Rules(Node):

    __slots__ = ('__contents')

    def __init__(self, code, contents=None, parent=None):
        Node.__init__(self, code=code, parent=parent)

        self.__contents = contents

    def __get_contents(self):
        return self.__contents

    contents = property(fget=__get_contents)
########NEW FILE########
__FILENAME__ = selector
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re
from lesscss.nested   import parse_nested
from lesscss.property import Property
from lesscss.rules    import Rules


SELECTOR = re.compile('''
    (?P<names>
        [a-z 0-9 \- _ \* \. \s , : # & @]+?
    )

    \s*

    {
''', re.DOTALL | re.VERBOSE)


def parse_selector(less, parent=None, **kwargs):
    match = SELECTOR.match(less)

    if not match:
        raise ValueError()
        
    names = match.group('names')
    
    if names.startswith('@media'):
        raise ValueError

    names = [name.strip() for name in names.split(',')]

    matched_length = len(match.group())

    remaining_less = less[matched_length:]

    contents = parse_nested(remaining_less)

    code = match.group() + contents + '}'

    return Selector(code=code, names=names, contents=contents, parent=parent)


class Selector(Rules):

    __slots__ = ('__names',)

    def __init__(self, parent, code, names=None, contents=None):
        Rules.__init__(self, parent=parent, code=code, contents=contents)

        self.__names = names

    def __get_names(self):
        try:
            parent_names = self.parent.names
        except AttributeError:
            return self.__names
        else:
            if not parent_names:
                return self.__names

        names = list()

        for parent_name in parent_names:
            for name in self.__names:
                if name[0] == ':':
                    name = parent_name + name
                else:
                    name = ' '.join((parent_name, name))
                name = name.replace(' &', '')

                names.append(name)

        return names

    names = property(fget=__get_names)
########NEW FILE########
__FILENAME__ = value
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import re


COLOURS = {'aliceblue':            '#f0f8ff', 'antiquewhite':         '#faebd7',
           'aqua':                 '#00ffff', 'aquamarine':           '#7fffd4',
           'azure':                '#f0ffff', 'beige':                '#f5f5dc',
           'bisque':               '#ffe4c4', 'black':                '#000000',
           'blanchedalmond':       '#ffebcd', 'blue':                 '#0000ff',
           'blueviolet':           '#8a2be2', 'brown':                '#a52a2a',
           'burlywood':            '#deb887', 'cadetblue':            '#5f9ea0',
           'chartreuse':           '#7fff00', 'chocolate':            '#d2691e',
           'coral':                '#ff7f50', 'cornflowerblue':       '#6495ed',
           'cornsilk':             '#fff8dc', 'crimson':              '#dc143c',
           'cyan':                 '#00ffff', 'darkblue':             '#00008b',
           'darkcyan':             '#008b8b', 'darkgoldenrod':        '#b8860b',
           'darkgray':             '#a9a9a9', 'darkgreen':            '#006400',
           'darkkhaki':            '#bdb76b', 'darkmagenta':          '#8b008b',
           'darkolivegreen':       '#556b2f', 'darkorange':           '#ff8c00',
           'darkorchid':           '#9932cc', 'darkred':              '#8b0000',
           'darksalmon':           '#e9967a', 'darkseagreen':         '#8fbc8f',
           'darkslateblue':        '#483d8b', 'darkslategray':        '#2f4f4f',
           'darkturquoise':        '#00ced1', 'darkviolet':           '#9400d3',
           'deeppink':             '#ff1493', 'deepskyblue':          '#00bfff',
           'dimgray':              '#696969', 'dodgerblue':           '#1e90ff',
           'firebrick':            '#b22222', 'floralwhite':          '#fffaf0',
           'forestgreen':          '#228b22', 'fuchsia':              '#ff00ff',
           'gainsboro':            '#dcdcdc', 'ghostwhite':           '#f8f8ff',
           'gold':                 '#ffd700', 'goldenrod':            '#daa520',
           'gray':                 '#808080', 'green':                '#008000',
           'greenyellow':          '#adff2f', 'honeydew':             '#f0fff0',
           'hotpink':              '#ff69b4', 'indianred ':           '#cd5c5c',
           'indigo ':              '#4b0082', 'ivory':                '#fffff0',
           'khaki':                '#f0e68c', 'lavender':             '#e6e6fa',
           'lavenderblush':        '#fff0f5', 'lawngreen':            '#7cfc00',
           'lemonchiffon':         '#fffacd', 'lightblue':            '#add8e6',
           'lightcoral':           '#f08080', 'lightcyan':            '#e0ffff',
           'lightgoldenrodyellow': '#fafad2', 'lightgrey':            '#d3d3d3',
           'lightgreen':           '#90ee90', 'lightpink':            '#ffb6c1',
           'lightsalmon':          '#ffa07a', 'lightseagreen':        '#20b2aa',
           'lightskyblue':         '#87cefa', 'lightslategray':       '#778899',
           'lightsteelblue':       '#b0c4de', 'lightyellow':          '#ffffe0',
           'lime':                 '#00ff00', 'limegreen':            '#32cd32',
           'linen':                '#faf0e6', 'magenta':              '#ff00ff',
           'maroon':               '#800000', 'mediumaquamarine':     '#66cdaa',
           'mediumblue':           '#0000cd', 'mediumorchid':         '#ba55d3',
           'mediumpurple':         '#9370d8', 'mediumseagreen':       '#3cb371',
           'mediumslateblue':      '#7b68ee', 'mediumspringgreen':    '#00fa9a',
           'mediumturquoise':      '#48d1cc', 'mediumvioletred':      '#c71585',
           'midnightblue':         '#191970', 'mintcream':            '#f5fffa',
           'mistyrose':            '#ffe4e1', 'moccasin':             '#ffe4b5',
           'navajowhite':          '#ffdead', 'navy':                 '#000080',
           'oldlace':              '#fdf5e6', 'olive':                '#808000',
           'olivedrab':            '#6b8e23', 'orange':               '#ffa500',
           'orangered':            '#ff4500', 'orchid':               '#da70d6',
           'palegoldenrod':        '#eee8aa', 'palegreen':            '#98fb98',
           'paleturquoise':        '#afeeee', 'palevioletred':        '#d87093',
           'papayawhip':           '#ffefd5', 'peachpuff':            '#ffdab9',
           'peru':                 '#cd853f', 'pink':                 '#ffc0cb',
           'plum':                 '#dda0dd', 'powderblue':           '#b0e0e6',
           'purple':               '#800080', 'red':                  '#ff0000',
           'rosybrown':            '#bc8f8f', 'royalblue':            '#4169e1',
           'saddlebrown':          '#8b4513', 'salmon':               '#fa8072',
           'sandybrown':           '#f4a460', 'seagreen':             '#2e8b57',
           'seashell':             '#fff5ee', 'sienna':               '#a0522d',
           'silver':               '#c0c0c0', 'skyblue':              '#87ceeb',
           'slateblue':            '#6a5acd', 'slategray':            '#708090',
           'snow':                 '#fffafa', 'springgreen':          '#00ff7f',
           'steelblue':            '#4682b4', 'tan':                  '#d2b48c',
           'teal':                 '#008080', 'thistle':              '#d8bfd8',
           'tomato':               '#ff6347', 'turquoise':            '#40e0d0',
           'violet':               '#ee82ee', 'wheat':                '#f5deb3',
           'white':                '#ffffff', 'whitesmoke':           '#f5f5f5',
           'yellow':               '#ffff00', 'yellowgreen':          '#9acd32'}
           
           
UNITS = ('%', 'in', 'cm', 'mm', 'em', 'ex', 'pt', 'pc', 'px')


VALUE = re.compile('''
        (?P<add>
            \+
        )
    |
        (?P<colour>
            \#
            [0-9A-F]{6}
        )
    |
        (?P<short_colour>
            \#
            [0-9A-F]{3}
        )
    |
        (?P<colour_name> AliceBlue | AntiqueWhite | Aqua | Aquamarine | Azure |
                         Beige | Bisque | Black | BlanchedAlmond | Blue |
                         BlueViolet | Brown | BurlyWood | CadetBlue | Chartreuse
                         | Chocolate | Coral | CornflowerBlue | Cornsilk |
                         Crimson | Cyan | DarkBlue | DarkCyan | DarkGoldenRod |
                         DarkGray | DarkGreen | DarkKhaki | DarkMagenta |
                         DarkOliveGreen | Darkorange | DarkOrchid | DarkRed
                         | DarkSalmon | DarkSeaGreen | DarkSlateBlue |
                         DarkSlateGray | DarkTurquoise | DarkViolet | DeepPink
                         | DeepSkyBlue | DimGray | DodgerBlue | FireBrick |
                         FloralWhite | ForestGreen | Fuchsia | Gainsboro |
                         GhostWhite | Gold | GoldenRod | Gray | Green |
                         GreenYellow | HoneyDew | HotPink | IndianRed | Indigo |
                         Ivory | Khaki | Lavender | LavenderBlush | LawnGreen |
                         LemonChiffon | LightBlue | LightCoral | LightCyan |
                         LightGoldenRodYellow | LightGrey | LightGreen |
                         LightPink | LightSalmon | LightSeaGreen | LightSkyBlue
                         | LightSlateGray | LightSteelBlue | LightYellow | Lime
                         | LimeGreen | Linen | Magenta | Maroon |
                         MediumAquaMarine | MediumBlue | MediumOrchid |
                         MediumPurple | MediumSeaGreen | MediumSlateBlue |
                         MediumSpringGreen | MediumTurquoise | MediumVioletRed |
                         MidnightBlue | MintCream | MistyRose | Moccasin |
                         NavajoWhite | Navy | OldLace | Olive | OliveDrab |
                         Orange | OrangeRed | Orchid | PaleGoldenRod | PaleGreen
                         | PaleTurquoise | PaleVioletRed | PapayaWhip |
                         PeachPuff | Peru | Pink | Plum | PowderBlue | Purple |
                         Red | RosyBrown | RoyalBlue | SaddleBrown | Salmon |
                         SandyBrown | SeaGreen | SeaShell | Sienna | Silver |
                         SkyBlue | SlateBlue | SlateGray | Snow | SpringGreen |
                         SteelBlue | Tan | Teal | Thistle | Tomato | Turquoise |
                         Violet | Wheat | White | WhiteSmoke | Yellow |
                         YellowGreen )
    |
        (?P<comma>
            ,
        )
    |
        (?P<constant>
            @
            [a-z0-9\-_]*
            [a-z0-9_]+
        )
    |
        (?P<divide>
            /
        )
    |
        (?P<format>
            format\(
                .+?
            \)
        )
    |
        (?P<local>
            local\(
                .+?
            \)
        )
    |
        (?P<multiply>
            \*
        )
    |
        (?P<number>
            [0-9]+
            
            (?P<unit>
                %                       # percentage
            |
                in                      # inch
            |
                cm                      # centimeter
            |
                mm                      # millimeter
            |
                em                      # 1em is equal to the current font size.
                                        # 2em means 2 times the size of the
                                        # current font. E.g., if an element is
                                        # displayed with a font of 12 pt, then
                                        # '2em' is 24 pt. The 'em' is a very
                                        # useful unit in CSS, since it can adapt
                                        # automatically to the font that the
                                        # reader uses
            |
                ex                      # one ex is the x-height of a font
                                        # (x-height is usually about half the
                                        # font-size)
            |
                pt                      # point (1 pt is the same as 1/72 inch)
            |
                pc                      # pica (1 pc is the same as 12 points)
            |
                px                      # pixels (a dot on the computer screen)
            )?
        )
    |
        (?P<url>
            url\(
                .+?
            \)
        )
    |
        (?P<subtract>
            -
        )
    |
        (?P<string>
            [a-z]+
        |
            '.*?(?!\\\\)'
        |
            ".*?(?!\\\\)"
        )
    |
        (?P<whitespace>
            \s+
        )
''', re.DOTALL | re.IGNORECASE | re.VERBOSE)


GROUPS = ('add', 'colour', 'colour_name', 'comma', 'constant', 'divide',
          'format', 'local', 'multiply', 'number', 'short_colour', 'string',
          'subtract', 'url', 'whitespace')
          
          
def add(arg1, arg2):
    if arg1['type'] == 'colour' and arg2['type'] == 'colour':
        colour1_red, colour1_green, colour1_blue = get_rgb(arg1['value'])
        colour2_red, colour2_green, colour2_blue = get_rgb(arg2['value'])
        
        red   = colour1_red   + colour2_red
        green = colour1_green + colour2_green
        blue  = colour1_blue  + colour2_blue
        
        return get_colour_value(red, green, blue)
    elif arg1['type'] == 'number' and arg2['type'] == 'number':
        num1, unit1 = get_number(arg1['value'])
        num2, unit2 = get_number(arg2['value'])
        
        unit = get_unit(unit1, unit2)
        
        num = num1 + num2
        
        return '%i%s' % (num, unit)
    else:
        raise ValueError('%s cannot be added to %s' %
                         (arg1['type'], arg2['type']))
          
          
def divide(arg1, arg2):
    if arg1['type'] == 'colour' and arg2['type'] == 'number':
        operand = int(arg2['value'])
        
        if operand == 0:
            raise ZeroDivisionError()
    
        colour1_red, colour1_green, colour1_blue = get_rgb(arg1['value'])
        
        red   = colour1_red   / operand
        green = colour1_green / operand
        blue  = colour1_blue  / operand
        
        return get_colour_value(red, green, blue)
    elif arg1['type'] == 'number' and arg2['type'] == 'number':
        num1, unit1 = get_number(arg1['value'])
        num2, unit2 = get_number(arg2['value'])
        
        unit = get_unit(unit1, unit2)
        
        num = int(num1 / num2)
        
        return '%i%s' % (num, unit)
    else:
        raise ValueError('%s cannot be divided by %s' %
                         (arg1['type'], arg2['type']))

                         
def get_colour(value):
    value = value.lower()

    for colour in COLOURS:
        if value == COLOURS[colour]:
            return colour
            
    if value[1:4] == value[4:7]:
        return value[0:4]
    
    return value
    
    
def get_colour_value(red, green, blue):
    hex_red   = hex(normalise_colour(red))
    hex_green = hex(normalise_colour(green))
    hex_blue  = hex(normalise_colour(blue))
    
    return '#%s%s%s' % (hex_red[2:], hex_green[2:], hex_blue[2:])

    
def get_matched_value(match):
    for group_name in GROUPS:
        grouped = match.group(group_name)
        
        if grouped:
            return group_name, grouped
    else:
        raise AssertionError('Unable to find matched group')
        
        
def get_number(number):
    for unit in UNITS:
        if number.endswith(unit):
            return int(number[:-len(unit)]), unit
    else:
        return int(number), None
        
        
def get_rgb(colour):
    red   = int(colour[1:3], 16)
    green = int(colour[3:5], 16)
    blue  = int(colour[5:7], 16)
    
    return red, green, blue
    
    
def get_unit(unit1, unit2):
    if unit1 and unit2 and unit1 != unit2:
        raise ValueError('%s cannot be mixed with a %s' % unit1, unit2)
    elif unit1:
        return unit1
    elif unit2:
        return unit2
    else:
        return ''


def get_value(less, constants):
    parsed = parse_value(less, constants)
    
    value = ''
    
    i = 0
    
    length = len(parsed)
    
    while i != length:
        item = parsed[i]
    
        if value and item['type'] != 'comma':
            value += ' '
        
        if i != length - 1 \
        and parsed[i + 1]['type'] in ('add', 'divide', 'multiply', 'subtract'):
            operator = parsed[i + 1]['type']
            
            if operator == 'add':
                this_value = add(parsed[i], parsed[i + 2])
            elif operator == 'divide':
                this_value = divide(parsed[i], parsed[i + 2])
            elif operator == 'multiply':
                this_value = multiply(parsed[i], parsed[i + 2])
            elif operator == 'subtract':
                this_value = subtract(parsed[i], parsed[i + 2])
                
            parsed[i]['value'] = this_value
            
            for _ in range(2):
                parsed.pop(i + 1)
        
            length -= 2
            
            continue
        else:
            this_value = item['value']
            
        if item['type'] == 'colour':
            this_value = get_colour(this_value)
            
        value += this_value
        
        i += 1
    
    return value
          
          
def multiply(arg1, arg2):
    if arg1['type'] == 'colour' and arg2['type'] == 'number':
        operand = int(arg2['value'])
    
        colour1_red, colour1_green, colour1_blue = get_rgb(arg1['value'])
        
        red   = colour1_red   * operand
        green = colour1_green * operand
        blue  = colour1_blue  * operand
        
        return get_colour_value(red, green, blue)
    elif arg1['type'] == 'number' and arg2['type'] == 'number':
        num1, unit1 = get_number(arg1['value'])
        num2, unit2 = get_number(arg2['value'])
        
        unit = get_unit(unit1, unit2)
        
        num = num1 * num2
        
        return '%i%s' % (num, unit)
    else:
        raise ValueError('%s cannot be multiplied by %s' %
                         (arg1['type'], arg2['type']))
        
        
def normalise_colour(colour):
    if colour < 0:
        return 0
    elif colour > 255:
        return 255
    else:
        return colour
    
    
def parse_value(less, constants):
    parsed = list()

    while less:
        match = VALUE.match(less)
        
        if not match:
            raise ValueError(less)
        
        group_name, grouped = get_matched_value(match)
        
        length = len(grouped)
        
        less = less[length:]
        
        if group_name == 'constant':
            constant = constants[grouped]
            
            value = ''
            
            while value != grouped:
                grouped = value
                
                value = get_value(constant, constants)
                
            group_name, value = get_matched_value(VALUE.match(grouped))
        
        if group_name == 'colour_name':
            group_name = 'colour'
            value = COLOURS[grouped.lower()]
        elif group_name == 'short_colour':
            group_name = 'colour'
            half = grouped[1:]
            value = '#%s%s' % (half, half)
        elif group_name == 'whitespace':
            continue
        else:
            value = grouped
            
        parsed.append({'type': group_name, 'value': value})

    return parsed
          
          
def subtract(arg1, arg2):
    if arg1['type'] == 'colour' and arg2['type'] == 'colour':
        colour1_red, colour1_green, colour1_blue = get_rgb(arg1['value'])
        colour2_red, colour2_green, colour2_blue = get_rgb(arg2['value'])
        
        red   = colour1_red   - colour2_red
        green = colour1_green - colour2_green
        blue  = colour1_blue  - colour2_blue
        
        return get_colour_value(red, green, blue)
    elif arg1['type'] == 'number' and arg2['type'] == 'number':
        num1, unit1 = get_number(arg1['value'])
        num2, unit2 = get_number(arg2['value'])
        
        unit = get_unit(unit1, unit2)
        
        num = num1 - num2
        
        return '%i%s' % (num, unit)
    else:
        raise ValueError('%s cannot be subtracted from %s' %
                         (arg1['type'], arg2['type']))

########NEW FILE########
__FILENAME__ = test
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
import test_accessor
import test_compile
import test_import
import test_media
import test_mixin
import test_nested
import test_parse
import test_property
import test_selector
import test_value
import test_lessc


def suite():
    test_suites = (test_accessor.suite(), test_compile.suite(),
                   test_import.suite(), test_media.suite(), test_mixin.suite(),
                   test_nested.suite(), test_parse.suite(),
                   test_property.suite(), test_selector.suite(),
                   test_value.suite())

    return unittest.TestSuite(test_suites)


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_accessor
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.accessor import parse_accessor


class TestAccessor(unittest.TestCase):
    def test_mixin(self):
        self.assertEqual(parse_accessor('#bundle > .button;').accessor,
                         '#bundle > .button')
                         
    def test_property(self):
        self.assertEqual(parse_accessor(".article['color'];").accessor,
                         ".article['color']")
                         
    def test_variable(self):
        self.assertEqual(parse_accessor("#defaults[@width];").accessor,
                         "#defaults[@width]")


def suite():
    test_cases = (TestAccessor,)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_compile
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.lessc import compile


class TestDocsExamples(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(compile(u'div { width: 1 + 1 }'), u'div { width: 2; }')

    def test_invoke1(self):
        self.assertEqual(compile(u'a { color: blue }'), u'a { color: blue; }')

    def test_invoke2(self):
        self.assertEqual(compile(u'.post { color: blue }'),
                         u'.post { color: blue; }')

    def test_variables(self):
        self.assertEqual(compile(u'''@nice-blue: #5B83AD;
@light-blue: @nice-blue + #111;

#header { color: @light-blue; }'''), u'#header { color: #6c94be; }')

    def test_mixin(self):
        self.assertEqual(compile(u'''.bordered {
  border-top: dotted 1px black;
  border-bottom: solid 2px black;
}

#menu a {
  color: #111;
  .bordered;
}

.post a {
  color: red;
  .bordered;
}'''), '''#menu a {
  border-bottom: solid 2px black;
  border-top: dotted 1px black;
  color: #111;
}

.bordered {
  border-bottom: solid 2px black;
  border-top: dotted 1px black;
}

.post a {
  border-bottom: solid 2px black;
  border-top: dotted 1px black;
  color: red;
}''')

    def test_nested_rules(self):
        self.assertEqual(compile(u'''#header {
  color: black;

  .navigation {
    font-size: 12px;
  }
  .logo {
    width: 300px;
    :hover { text-decoration: none }
  }
}'''), u'''#header { color: black; }

#header .logo { width: 300px; }

#header .logo:hover { text-decoration: none; }

#header .navigation { font-size: 12px; }''')

    def test_operations(self):
        self.assertEqual(compile(u'''@base: 5%;
@filler: @base * 2;
@other: @base + @filler;
@base-color: #222;

* {
  padding: @base;
  width: @filler;
  margin: @other;

  color: #888 / 4;
  background-color: @base-color + #111;
  height: 100% / 2 + @filler;
}'''), u'''* {
  background-color: #333;
  color: #222;
  height: 60%;
  margin: 15%;
  padding: 5%;
  width: 10%;
}''')

    def test_units(self):
        self.assertEqual(compile(u'''@var: 1px + 5;

* {
    width: @var;
}'''), u'* { width: 6px; }')

    def test_namespaces(self):
        self.assertEqual(compile(u'''#bundle {
  .button {
    display: block;
    border: 1px solid black;
    background-color: grey;
    :hover { background-color: white }
  }
  .tab { }
  .citation { }
}

#header a {
  color: orange;
  #bundle > .button;
}'''), u'''''')

    def test_accessors(self):
        self.assertEqual(compile(u'''#defaults {
  @width: 960px;
  @color: black;
}

.article { color: #294366; }

.comment {
  width: #defaults[@width];
  color: .article['color'];
}'''), u'''.article {
  color: #294366;
}

.comment {
  color: #294366;
  width: 960px;
}''')

    def test_scope(self):
        self.assertEqual(compile(u'''@var: red;

#page {
  @var: white;
  #header {
    color: @var; // white
  }
}'''), u'''#page #header { color: white; }''')

    def test_comments(self):
        self.assertEqual(compile(u'''/* One hell of a comment */
@var: red;

// Get in line!
@var: white;'''), '')


def suite():
    test_cases = (TestDocsExamples,)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())

########NEW FILE########
__FILENAME__ = test_import
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.importer import parse_import


class TestImport(unittest.TestCase):
    def setUp(self):
        self.parsed = parse_import('@import "test_file.less";')
        
    def test_code(self):
        self.assertEqual(self.parsed.code, '@import "test_file.less";')
        
    def test_less(self):
        self.assertEqual(self.parsed.less, '''a {
  text-decoration: none;
}''')


class TestURL(unittest.TestCase):
    def setUp(self):
        self.parsed = parse_import('@import url("fancyfonts.css") screen;')
        
    def test_media(self):
        self.assertEqual(self.parsed.target, ('screen',))
        
    def test_url(self):
        self.assertEqual(self.parsed.url, '"fancyfonts.css"')


def suite():
    test_cases = (TestImport, TestURL)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_lessc
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of lesscss-python.
#
# lesscss-python is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# lesscss-python is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
"""

Copyright (c) 2011 Evgeny V. Generalov. 
mailto:e.generalov@gmail.com
"""

import unittest
import sys
import subprocess

from lesscss import lessc


class TestLessc(unittest.TestCase):

    def setUp(self):
        self.python = sys.executable
        self.lessc = lessc.__file__
        
    def test_should_compile_a_file(self):
        css = self._run([self.python, self.lessc, 'test_file.less'])
        self.assertEqual(css, '''a { text-decoration: none; }''')

    def test_should_compile_from_stdin(self):
        less = '''a {text-decoration: none}'''
        css = self._run([self.python, self.lessc], input=less)
        self.assertEqual(css, '''a { text-decoration: none; }''')

    def _run(self, cmd, input=None, *args, **kwargs):
        proc= subprocess.Popen(cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, *args, **kwargs)
        return ''.join(proc.communicate(input=input))


def suite():
    test_cases = (TestLessc,)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())


########NEW FILE########
__FILENAME__ = test_media
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.media import parse_media


class TestMedia(unittest.TestCase):
    def test_multi(self):
        self.assertEqual(parse_media('@media screen { }').media, ['screen'])
        
    def test_none(self):
        self.assertRaises(ValueError, parse_media, '@media { }')
        
    def test_single(self):
        self.assertEqual(parse_media('@media screen, print { }').media,
                         ['screen', 'print'])


def suite():
    test_cases = (TestMedia,)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_mixin
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.mixin import parse_mixin


NO_PARAMS = []


class TestBracedParams(unittest.TestCase):
    def setUp(self):
        self.params = parse_mixin(".mixin('{');").params

    def test_parsed(self):
        self.assertNotEqual(self.params, NO_PARAMS)

    def test_name(self):
        self.assertEqual(self.params[0].name, None)

    def test_value(self):
        self.assertEqual(self.params[0].value, "'{'")


class TestDeclaredBracedParams(unittest.TestCase):
    def setUp(self):
        self.params = parse_mixin(".mixin(@param: '{') { };").params

    def test_parsed(self):
        self.assertNotEqual(self.params, NO_PARAMS)

    def test_name(self):
        self.assertEqual(self.params[0].name, '@param')

    def test_value(self):
        self.assertEqual(self.params[0].value, "'{'")


class TestDeclaredParams(unittest.TestCase):
    def setUp(self):
        self.params = parse_mixin('.mixin(@param) { }').params

    def test_parsed(self):
        self.assertNotEqual(self.params, NO_PARAMS)

    def test_name(self):
        self.assertEqual(self.params[0].name, '@param')

    def test_value(self):
        self.assertEqual(self.params[0].value, None)


class TestDeclaredParamsWithDefaults(unittest.TestCase):
    def setUp(self):
        self.params = parse_mixin('.mixin(@param: 1) { }').params

    def test_parsed(self):
        self.assertNotEqual(self.params, NO_PARAMS)

    def test_name(self):
        self.assertEqual(self.params[0].name, '@param')

    def test_value(self):
        self.assertEqual(self.params[0].value, '1')


class TestDynamic(unittest.TestCase):
    def setUp(self):
        self.mixin = parse_mixin('''.fs (@main: 'TitilliumText15L400wt') {
    font-family: @main, 'Helvetica', sans-serif;
}''')

    def test_contents(self):
        self.assertEqual(self.mixin.contents, '''
    font-family: @main, 'Helvetica', sans-serif;
''')

    def test_param_name(self):
        self.assertEqual(self.mixin.params[0].name, '@main')

    def test_param_value(self):
        self.assertEqual(self.mixin.params[0].value, "'TitilliumText15L400wt'")


class TestEscaped(unittest.TestCase):
    def setUp(self):
        self.params = parse_mixin('''.mixin (@name: 'a\'', @b: 'b') {
    display: none;
}''').params

    def test_first_param_name(self):
        self.assertEqual(self.params[0].name, "@name")

    def test_first_param_value(self):
        self.assertEqual(self.params[0].value, "'a\''")

    def test_second_param_name(self):
        self.assertEqual(self.params[1].name, "@b")

    def test_first_param_value(self):
        self.assertEqual(self.params[1].value, "'b'")


class TestNestedParams(unittest.TestCase):
    def setUp(self):
        self.mixin = parse_mixin('''.box-shadow(0 2px 5px rgba(0, 0, 0, 0.125),
0 2px 10px rgba(0, 0, 0, 0.25));''')

    def test_count(self):
        self.assertEqual(len(self.mixin.params), 2)

    def test_first_param_name(self):
        self.assertEqual(self.mixin.params[0].name, None)

    def test_first_param_value(self):
        self.assertEqual(self.mixin.params[0].value,
                         '0 2px 5px rgba(0, 0, 0, 0.125)')

    def test_second_param_name(self):
        self.assertEqual(self.mixin.params[1].name, None)

    def test_second_param_value(self):
        self.assertEqual(self.mixin.params[1].value,
                         '0 2px 10px rgba(0, 0, 0, 0.25)')


class TestNoParams(unittest.TestCase):
    def test_declared(self):
        self.assertEqual(parse_mixin('.mixin() { }').params, NO_PARAMS)

    def test_used(self):
        self.assertEqual(parse_mixin('.mixin();').params, NO_PARAMS)

    def test_used_without_brackets(self):
        self.assertEqual(parse_mixin('.mixin;').params, NO_PARAMS)


class TestNotMixin(unittest.TestCase):
    def test_all(self):
        '''
        Wildcard Declarations with an asterisks should not be parsed.
        '''
        self.assertRaises(ValueError, parse_mixin, '* { }')

    def test_class(self):
        '''
        Class Declarations with a dot at the beginning should not be parsed.
        '''
        self.assertRaises(ValueError, parse_mixin, '.class { }')

    def test_element(self):
        '''
        Element Declarations should not be parsed.
        '''
        self.assertRaises(ValueError, parse_mixin, 'element { }')

    def test_id(self):
        '''
        ID Declarations with a hash at the beginning should not be parsed.
        '''
        self.assertRaises(ValueError, parse_mixin, '#hash { }')


class TestUsedParams(unittest.TestCase):
    def setUp(self):
        self.params = parse_mixin('.mixin(1);').params

    def test_used(self):
        self.assertNotEqual(self.params, NO_PARAMS)

    def test_used_name(self):
        self.assertEqual(self.params[0].name, None)

    def test_used_value(self):
        self.assertEqual(self.params[0].value, '1')


def suite():
    test_cases = (TestBracedParams, TestDeclaredBracedParams,
                  TestDeclaredParams, TestDeclaredParamsWithDefaults,
                  TestDynamic, TestEscaped, TestNestedParams, TestNoParams,
                  TestNotMixin, TestUsedParams)

    suite = unittest.TestSuite()

    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_nested
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.nested import parse_nested


class TestNested(unittest.TestCase):
    def test_braces_in_quotes(self):
        self.assertEqual('quotes: "{" "}"', parse_nested('quotes: "{" "}"}'))
        
    def test_bundle(self):
        self.assertEqual(".b { :h { } } .t { ... } .c { ... } ",
                         parse_nested(".b { :h { } } .t { ... } .c { ... } }"))
        
    def test_open_brace_in_quotes(self):
        self.assertEqual('quotes: "}"', parse_nested('quotes: "}"}'))
        
    def test_double_depth(self):
        self.assertEqual('{a}', parse_nested('{a}}'))
        
    def test_double_depth_spaced(self):
        self.assertEqual(' { a } ', parse_nested(' { a } } '))
        
    def test_open_brace_in_quotes(self):
        self.assertEqual('quotes: "{"', parse_nested('quotes: "{"}'))

    def test_single_depth(self):
        self.assertEqual('a', parse_nested('a}'))
        
    def test_single_depth_spaced(self):
        self.assertEqual(' a ', parse_nested(' a } '))
        
    def test_triple_depth(self):
        self.assertEqual('{{a}}', parse_nested('{{a}}}'))
        
    def test_triple_depth_spaced(self):
        self.assertEqual(' { { a } } ', parse_nested(' { { a } } } '))


def suite():
    test_cases = (TestNested,)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_parse
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.lessc import parse
from lesscss.rules import Rules


class TestConstantDeclaration(unittest.TestCase):
    def setUp(self):
        less = '''
@constant: 10px;

* {
    @constant: 20px;

    a {
        @constant: 30px;
    }
}'''
        self.parsed = Rules(code=less)
        parse(less=less, parent=self.parsed)

    def test_root_value(self):
        self.assertEqual(self.parsed.constants['@constant'], '10px')

    def test_first_value(self):
        self.assertEqual(self.parsed.items[1].constants['@constant'], '20px')

    def test_second_value(self):
        self.assertEqual(self.parsed.items[1].items[1].constants['@constant'],
                         '30px')


class TestConstantScope(unittest.TestCase):
    def setUp(self):
        less = '''@var: red;

#page {
  @var: white;
  #header {
    color: @var; // white
  }
}'''
        self.parsed = Rules(code=less)
        parse(less=less, parent=self.parsed)
        
    def get_page(self):
        for item in self.parsed.items:
            try:
                if item.names == ['#page']:
                    return item
            except AttributeError:
                pass
        else:
            self.fail()
        
    def get_header(self):
        for item in self.get_page().items:
            try:
                if item.names == ['#page #header']:
                    return item
            except AttributeError:
                pass
        else:
            self.fail()

    def test_root_value(self):
        self.assertEqual(self.parsed.get_value('@var'), 'red')

    def test_page_value(self):
        self.assertEqual(self.get_page().get_value('@var'), 'white')

    def test_header_value(self):
        self.assertEqual(self.get_header().get_value('@var'), 'white')
        
        
class TestCSSImport(unittest.TestCase):
    def setUp(self):
        self.css = '@import url("fancyfonts.css") screen;'
        self.parsed = Rules(code=self.css)
        parse(less=self.css, parent=self.parsed)

    def test_is_the_same(self):
        self.assertEqual(str(self.parsed), self.css)



class TestErrors(unittest.TestCase):
    def parse_less(self, less):
        parent = Rules(code=less)
        parse(less=less, parent=parent)

    def test_empty_param(self):
        self.assertRaises(ValueError, self.parse_less, '.class (,) { }')

    def test_non_mixin_id(self):
        self.assertRaises(ValueError, self.parse_less, '.class { #content; }')

    def test_non_mixin_selector(self):
        self.assertRaises(ValueError, self.parse_less, '.class { content; }')

    def test_non_mixin_wildcard(self):
        self.assertRaises(ValueError, self.parse_less, '.class { *; }')

    def test_trailing_param(self):
        self.assertRaises(ValueError, self.parse_less, '.class (@param,) { }')

    def test_unclosed_block(self):
        self.assertRaises(ValueError, self.parse_less, '.class { color: red;')

    def test_undeclared_constant(self):
        self.assertRaises(ValueError, self.parse_less, '.class { @constant; }')

    def test_unterminated_apos(self):
        self.assertRaises(ValueError, self.parse_less, ".class { content: '; }")

    def test_unterminated_string(self):
        self.assertRaises(ValueError, self.parse_less, '.class { content: "; }')


class TestFontDeclarationCorruption(unittest.TestCase):
    def setUp(self):
        self.css = '''@font-face {
  font-family: 'Cantarell';
  font-style: normal;
  font-weight: normal;
  src: local('Cantarell'), \
url('http://themes.googleusercontent.com/font?kit=tGao7ZPoloMxQHxq-2oxNA') \
format('truetype');
}'''
        self.parsed = Rules(code=self.css)
        parse(less=self.css, parent=self.parsed)

    def test_is_the_same(self):
        self.assertEqual(str(self.parsed), self.css)
        
        
class TestImport(unittest.TestCase):
    def setUp(self):
        self.css = '@import "test_file";'
        self.parsed = Rules(code=self.css)
        parse(less=self.css, parent=self.parsed)

    def test_parse(self):
        self.assertEqual(str(self.parsed), u'a { text-decoration: none; }')
        
        
class TestMediaImport(unittest.TestCase):
    def setUp(self):
        self.css = '@import "test_file" screen;'
        self.parsed = Rules(code=self.css)
        parse(less=self.css, parent=self.parsed)

    def test_parse(self):
        self.assertEqual(str(self.parsed), u'''@media screen {
a { text-decoration: none; }
}''')


class TestMedia(unittest.TestCase):
    def setUp(self):
        self.css = '''@media screen {
@font-face {
  font-family: 'Cantarell';
  font-style: normal;
  font-weight: normal;
  src: local('Cantarell'), \
url('http://themes.googleusercontent.com/font?kit=tGao7ZPoloMxQHxq-2oxNA') \
format('truetype');
}
}'''
        self.parsed = Rules(code=self.css)
        parse(less=self.css, parent=self.parsed)

    def test_is_the_same(self):
        self.assertEqual(str(self.parsed), self.css)

    def test_media_selector(self):
        self.assertEqual(self.parsed.get_selectors(media=['screen']),
                         {'@font-face': {'src': '''local('Cantarell'), \
url('http://themes.googleusercontent.com/font?kit=tGao7ZPoloMxQHxq-2oxNA') \
format('truetype')''',
                                         'font-weight': 'normal',
                                         'font-style': 'normal',
                                         'font-family': "'Cantarell'"}})

    def test_media_selectors(self):
        self.assertEqual(self.parsed.get_media_selectors(),
                         (None, ['screen']))

    def test_none_selector(self):
        self.assertEqual(self.parsed.get_selectors(), {})
        

class TestNoMedia(unittest.TestCase):
    def setUp(self):
        self.css = '@media screen { }'
        self.parsed = Rules(code=self.css)
        parse(less=self.css, parent=self.parsed)

    def test_is_the_same(self):
        self.assertEqual(str(self.parsed), '')


def suite():
    test_cases = (TestConstantDeclaration, TestConstantScope, TestCSSImport,
                  TestErrors, TestFontDeclarationCorruption, TestImport,
                  TestMedia, TestMediaImport, TestNoMedia)

    suite = unittest.TestSuite()

    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_property
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.property import parse_property


class TestAccessor(unittest.TestCase):
    def test_mixin(self):
        self.assertRaises(ValueError, parse_property, '#bundle > .button;')

    def test_property(self):
        self.assertRaises(ValueError, parse_property, ".article['color'];")

    def test_variable(self):
        self.assertRaises(ValueError, parse_property, "#defaults[@width];")


class TestAlpha(unittest.TestCase):
    def setUp(self):
        self.property = parse_property(\
"filter:progid:DXImageTransform.Microsoft.AlphaImageLoader(src='image.png');")

    def test_name(self):
        self.assertEqual(self.property.name, 'filter')

    def test_value(self):
        self.assertEqual(self.property.value, \
"progid:DXImageTransform.Microsoft.AlphaImageLoader(src='image.png')")


class TestBracesInQuotes(unittest.TestCase):
    def setUp(self):
        self.property = parse_property('quotes: "{" "}";')

    def test_name(self):
        self.assertEqual(self.property.name, 'quotes')

    def test_value(self):
        self.assertEqual(self.property.value, '"{" "}"')
        
        
class TestConstant(unittest.TestCase):
    def test_declaration(self):
        self.assertRaises(ValueError, parse_property, '@var: white;')


class TestContent(unittest.TestCase):
    def setUp(self):
        self.property = parse_property("content: '\0000A9';")

    def test_name(self):
        self.assertEqual(self.property.name, 'content')

    def test_value(self):
        self.assertEqual(self.property.value, "'\0000A9'")


class TestContentURL(unittest.TestCase):
    def setUp(self):
        self.property = parse_property('content: url(/uri);')

    def test_name(self):
        self.assertEqual(self.property.name, 'content')

    def test_value(self):
        self.assertEqual(self.property.value, 'url(/uri)')


class TestContentURLInQuotes(unittest.TestCase):
    def setUp(self):
        self.property = parse_property("content: url('/uri');")

    def test_name(self):
        self.assertEqual(self.property.name, 'content')

    def test_value(self):
        self.assertEqual(self.property.value, "url('/uri')")


class TestFont(unittest.TestCase):
    def setUp(self):
        self.property = parse_property('''src: local('Vollkorn'),
url('http://themes.googleusercontent.com/font?kit=_3YMy3W41J9lZ9YHm0HVxA')
format('truetype');''')

    def test_name(self):
        self.assertEqual(self.property.name, 'src')

    def test_value(self):
        self.assertEqual(self.property.value, '''local('Vollkorn'),
url('http://themes.googleusercontent.com/font?kit=_3YMy3W41J9lZ9YHm0HVxA')
format('truetype')''')


class TestFontFamily(unittest.TestCase):
    def setUp(self):
        self.property = parse_property("font-family: sans-serif;")

    def test_name(self):
        self.assertEqual(self.property.name, 'font-family')

    def test_value(self):
        self.assertEqual(self.property.value, 'sans-serif')


class TestLength(unittest.TestCase):
    def test_single_line(self):
        self.assertEqual(parse_property('display:block;display:none').value,
                         'block')

    def test_multi_line(self):
        self.assertEqual(parse_property('display:block;\ndisplay:none').value,
                         'block')

    def test_multi_line_value(self):
        self.assertEqual(parse_property('''src: local('Vollkorn'),
url('http://themes.googleusercontent.com/font?kit=_3YMy3W41J9lZ9YHm0HVxA')
format('truetype');
display: block;''').value,'''local('Vollkorn'),
url('http://themes.googleusercontent.com/font?kit=_3YMy3W41J9lZ9YHm0HVxA')
format('truetype')''')


def suite():
    test_cases = (TestAccessor, TestAlpha, TestBracesInQuotes, TestConstant,
                  TestContent, TestContentURL, TestContentURLInQuotes, TestFont,
                  TestFontFamily, TestLength)

    suite = unittest.TestSuite()

    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_rules
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.selector import parse_selector


class TestConstantDeclaration(unittest.TestCase):
    def setUp(self):
        self.selector = parse_selector('''* {
    @constant: 10px;
}''')

    def test_count(self):
        self.assertEqual(len(self.selector.constants), 1)

    def test_value(self):
        self.assertEqual(self.selector.constants['@constant'].value, '10px')


def suite():
    test_cases = (TestConstantDeclaration,)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_selector
#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.selector import parse_selector


class TestMedia(unittest.TestCase):
    def test_multi(self):
        self.assertRaises(ValueError, parse_selector, '@media screen { }')
        
    def test_none(self):
        self.assertRaises(ValueError, parse_selector, '@media { }')
        
    def test_single(self):
        self.assertRaises(ValueError, parse_selector,
                          '@media screen, print { }')


class TestSelector(unittest.TestCase):
    def test_all(self):
        '''
        Wildcard Declarations with an asterisks should be parsed.
        '''
        self.assertEqual(parse_selector('* { }').names, ['*'])

    def test_class(self):
        '''
        Class Declarations with a dot at the beginning should be parsed.
        '''
        self.assertEqual(parse_selector('.class { }').names, ['.class'])

    def test_element(self):
        '''
        Element Declarations should be parsed.
        '''
        self.assertEqual(parse_selector('element { }').names, ['element'])

    def test_font(self):
        '''
        Font Declarations should be parsed.
        '''
        self.assertEqual(parse_selector('@font-face { }').names, ['@font-face'])

    def test_id(self):
        '''
        ID Declarations with a hash at the beginning should be parsed.
        '''
        self.assertEqual(parse_selector('#hash { }').names, ['#hash'])

    def test_mixin(self):
        '''
        Mixin Declarations should be parsed.
        '''
        self.assertRaises(ValueError, parse_selector, '.mixin () { }')

    def test_multi(self):
        '''
        Multiple Declarations should be parsed.
        '''
        self.assertEqual(parse_selector('a, b { }').names, ['a', 'b'])

    def test_nested(self):
        '''
        Nested Declarations should be parsed.
        '''
        self.assertEqual(parse_selector('a b { }').names, ['a b'])


def suite():
    test_cases = (TestMedia, TestSelector)

    suite = unittest.TestSuite()

    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
__FILENAME__ = test_value
﻿#!/usr/bin/env python
# -*- coding: utf-8 -*-


'''
Copyright 2010 Beech Horn

This file is part of lesscss-python.

lesscss-python is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

lesscss-python is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with lesscss-python.  If not, see <http://www.gnu.org/licenses/>.
'''


import unittest
from lesscss.value import get_colour, get_value, parse_value


class TestAddition(unittest.TestCase):
    def test_colour(self):
        self.assertEqual(get_value('#111 + #111', {}), '#222')


class TestColour(unittest.TestCase):
    def test_blue_lower(self):
        self.assertEqual(get_colour('#0000ff'), 'blue')
        
    def test_blue_mixed(self):
        self.assertEqual(get_colour('#0000Ff'), 'blue')
        
    def test_blue_upper(self):
        self.assertEqual(get_colour('#0000FF'), 'blue')
        
    def test_triple_lower(self):
        self.assertEqual(get_colour('#aaaaaa'), '#aaa')
        
    def test_triple_mixed(self):
        self.assertEqual(get_colour('#aAaAaA'), '#aaa')
        
    def test_triple_number(self):
        self.assertEqual(get_colour('#777777'), '#777')
        
    def test_triple_upper(self):
        self.assertEqual(get_colour('#AAAAAA'), '#aaa')
        
        
class TestDivision(unittest.TestCase):
    def test_colour(self):
        self.assertEqual(get_value('#888 / 4', {}), '#222')
        
        
class TestMultiply(unittest.TestCase):
    def test_colour(self):
        self.assertEqual(get_value('#222 * 4', {}), '#888')
    

class TestParse(unittest.TestCase):
    def setUp(self):
        self.constants = {'@nice-blue': 'blue'}

    def test_constant(self):
        self.assertEqual(parse_value('@nice-blue', self.constants),
                         [{'type': 'colour', 'value': '#0000ff'}])


class TestSubtraction(unittest.TestCase):
    def test_colour(self):
        self.assertEqual(get_value('#222 - #111', {}), '#111')


def suite():
    test_cases = (TestAddition, TestColour, TestDivision, TestMultiply,
                  TestParse, TestSubtraction)
    
    suite = unittest.TestSuite()
    
    for tests in map(unittest.TestLoader().loadTestsFromTestCase, test_cases):
        suite.addTests(tests)

    return suite


if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
########NEW FILE########
