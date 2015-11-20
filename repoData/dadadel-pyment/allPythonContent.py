__FILENAME__ = example
def func1(param1, param2='default val'):
    '''Description of func with docstring javadoc style.

    @param param1: descr of param
    @type param1: type
    @return: some value
    @raise KeyError: raises a key exception

    '''
    pass

def func2(param1, param2='default val2'):
    '''Description of func with docstring reST style.

    :param param1: descr of param
    :type param1: type
    :returns: some value
    :raises keyError: raises exception

    '''
    pass

def func3(param1, param2='default val'):
    '''Description of func with docstring groups style.

    Params: 
        param1 - descr of param

    Returns:
        some value

    Raises:
        keyError: raises key exception
        TypeError: raises type exception

    '''
    pass

class SomeClass(object):
    '''My class.
    '''
    def method(self, prm):
        '''description'''
        pass

    def method2(self, prm1, prm2='defaultprm'):
        pass

    def method_numpy(self):
        """
        My numpydoc description of a kind
        of very exhautive numpydoc format docstring.

        Parameters
        ----------
        first : array_like
            the 1st param name `first`
        second :
            the 2nd param
        third : {'value', 'other'}, optional
            the 3rd param, by default 'value'

        Returns
        -------
        string
            a value in a string

        Raises
        ------
        KeyError
            when a key error
        OtherError
            when an other error

        See Also
        --------
        a_func : linked (optional), with things to say
                 on several lines
        some blabla

        Note
        ----
        Some informations.

        Some maths also:
        .. math:: f(x) = e^{- x}

        References
        ----------
        Biblio with cited ref [1]_. The ref can be cited in Note section.

        .. [1] Adel Daouzli, Sylvain Saïghi, Michelle Rudolph, Alain Destexhe,
           Sylvie Renaud: Convergence in an Adaptive Neural Network:
           The Influence of Noise Inputs Correlation. IWANN (1) 2009: 140-148

        Examples
        --------
        This is example of use
        >>> print "a"
        a

        """
        pass

########NEW FILE########
__FILENAME__ = docstring
# -*- coding: utf8 -*-

__author__ = "A. Daouzli"
__copyright__ = "Copyright dec. 2013, A. Daouzli"
__licence__ = "GPL3"
__version__ = "0.2.1-dev"
__maintainer__ = "A. Daouzli"

"""
Formats supported at the time:
 - javadoc, reST (restructured text, Sphinx):
 managed  -> description, param, type, return, rtype, raise
 - groups (Google like): only input
 managed  -> description, parameters, return, raises
 - numpydoc:
 managed  -> description, parameters, return (first of list only), raises

"""

import os
import re
from collections import defaultdict


def isin_alone(elems, line):
    '''Check if an element from a list is the only element of a string.

    '''
    found = False
    for e in elems:
        if line.strip().lower() == e.lower():
            found = True
            break
    return found

def isin_start(elems, line):
    '''Check if an element from a list starts a string.

    '''
    found = False
    for e in elems:
        if line.lstrip().lower().startswith(e):
            found = True
            break
    return found

def isin(elems, line):
    '''Check if an element from a list is in a string.

    '''
    found = False
    for e in elems:
        if e in line.lower():
            found = True
            break
    return found

def get_leading_spaces(data):
    '''Get the leading space of a string if it is not empty
    '''
    spaces = ''
    m = re.match(r'^(\s*)', data)
    if m:
        spaces = m.group(1)
    return spaces


class NumpydocTools:
    def __init__(self, first_line=None,
                 optional_sections=['raise', 'also', 'ref', 'note', 'other', 'example', 'method', 'attr'],
                 excluded_sections=[]):
        '''
        @param first_line: indicate if description should start
        on first or second line. By default it will follow global config.
        @type first_line: boolean
        @param optional_sections: list of sections that are not mandatory
        if empty. The accepted sections are:
        -param
        -return
        -raise
        -also
        -ref
        -note
        -other
        -example
        -method
        -attr
        @type optional_sections: list
        @param excluded_sections: list of sections that are excluded,
        even if mandatory. The list is the same than for optional sections.
        @type excluded_sections: list

        '''
        self.first_line = first_line
        #TODO: if in the two lists see which is more important
        self.optional_sections = optional_sections
        self.excluded_sections = excluded_sections
        self.opt = {
                'param': 'parameters',
                'return': 'returns',
                'raise': 'raises',
                'also': 'see also',
                'ref': 'references',
                'note': 'notes',
                'other': 'other parameters',
                'example': 'examples',
                'method': 'methods',
                'attr': 'attributes'
                }
        self.keywords = [':math:', '.. math::', 'see also', '.. image::']

    def __iter__(self):
        return self.opt.__iter__()

    def __getitem__(self, key):
        return self.opt[key]

    def get_optional_sections(self):
        return self.optional_sections

    def get_excluded_sections(self):
        return self.excluded_sections

    def get_mandatory_sections(self):
        return [s for s in self.opt
                if s not in self.optional_sections and
                   s not in self.excluded_sections]

    def get_next_section_start_line(self, data):
        '''Get the starting line number of next section.
        It will return -1 if no section was found.
        The section is a section key (e.g. 'Parameters') followed by underline
        (made by -), then the content

        '''
        start = -1
        for i, line in enumerate(data):
            if start != -1:
                # we found the key so check if this is the underline
                if line.strip() and isin_alone(['-' * len(line.strip())], line):
                    break
                else:
                    start = -1
            if isin_alone(self.opt.values(), line):
                start = i
        return start

    def get_section_key_line(self, data, key):
        '''Get the next section line for a given key.
        '''
        start = 0
        init = 0
        while start != -1:
            start = self.get_next_section_start_line(data[init:])
            init += start
            if start != -1:
                if data[init].strip().lower() == self.opt[key]:
                    break
                init += 1
        if start != -1:
            start = init
        return start

    def get_next_section_lines(self, data):
        '''Get the starting line number and the ending line number of next section.
        It will return (-1, -1) if no section was found.
        The section is a section key (e.g. 'Parameters') followed by underline
        (made by -), then the content
        The ending line number is the line after the end of the section or -1 if
        the section is at the end.

        '''
        end = -1
        start = self.get_next_section_start_line(data)
        if start != -1:
            end = self.get_next_section_start_line(data[start+1:])
        return start, end

    def get_list_key(self, data, key):
        '''Get the list of a key elements.
        Each element is a tuple (key=None, description, type=None).
        Note that the tuple's element can differ depending on the key.

        '''
        key_list = []
        data = data.split(os.linesep)
        init = self.get_section_key_line(data, key)
        if init == -1:
            return []
        start, end = self.get_next_section_lines(data[init:])

        # get the spacing of line with key
        spaces = get_leading_spaces(data[init + start])
        start += init + 2
        end += init
        parse_key = False
        key, desc, ptype = None, '', None
        for line in data[start:end]:
            if len(line.strip()) == 0:
                continue
            # on the same column of the key is the key
            curr_spaces = get_leading_spaces(line)
            if len(curr_spaces) == len(spaces):
                if parse_key:
                    key_list.append((key, desc, ptype))
                elems = line.split(':', 1)
                key = elems[0].strip()
                ptype = elems[1].strip() if len(elems) > 1 else None
                desc = ''
                parse_key = True
            else:
                if len(curr_spaces) > len(spaces):
                    line = line.replace(spaces, '', 1)
                if desc:
                    desc += os.linesep
                desc += line
        if parse_key:
            key_list.append((key, desc, ptype))

        return key_list

    def get_attr_list(self, data):
        '''Get the list of attributes.
        The list contains tuples (name, desc, type=None)

        '''
        return self.get_list_key(data, 'attr')

    def get_param_list(self, data):
        '''Get the list of parameters.
        The list contains tuples (name, desc, type=None)

        '''
        return self.get_list_key(data, 'param')

    def get_return_list(self, data):
        '''Get the list of return elements/values.
        The list contains tuples (name=None, desc, type)

        '''
        return_list = []
        lst = self.get_list_key(data, 'return')
        for l in lst:
            name, desc, rtype = l
            if l[2] == None:
                rtype = l[0]
                name = None
            return_list.append((name, desc, rtype))
        return return_list

    def get_raise_list(self, data):
        '''Get the list of exceptions.
        The list contains tuples (name, desc)

        '''
        return_list = []
        lst = self.get_list_key(data, 'raise')
        for l in lst:
            # assume raises are only a name and a description
            name, desc, _ = l
            return_list.append((name, desc))
        return return_list

    def get_raw_not_managed(self, data):
        '''Get elements not managed. They can be used as is.

        '''
        keys = ['also', 'ref', 'note', 'other', 'example', 'method', 'attr']
        elems = [self.opt[k] for k in self.opt if k in keys]
        data = data.split(os.linesep)
        start = 0
        init = 0
        raw = ''
        spaces = None
        while start != -1:
            start, end = self.get_next_section_lines(data[init:])
            if start != -1:
                init += start
                if isin_alone(elems, data[init]) and \
                        not isin_alone([self.opt[e] for e in self.excluded_sections], data[init]):
                    spaces = get_leading_spaces(data[init])
                    if end != -1:
                        section = [d.replace(spaces, '', 1).rstrip() for d in data[init:init+end]]
                    else:
                        section = [d.replace(spaces, '', 1).rstrip() for d in data[init:]]
                    raw += os.linesep.join(section) + os.linesep
                init += 2
        return raw

    def get_key_section_header(self, key, spaces):
        if key == 'param':
            header = 'Parameters'
        elif key == 'return':
            header = 'Returns'
        elif key == 'raise':
            header = 'Raises'
        else:
            return ''
        header = spaces + header + os.linesep + spaces + '-' * len(header) + os.linesep
        return header


class DocsTools(object):
    '''This class provides the tools to manage several type of docstring.
    Currently the following are managed:
    - 'javadoc': javadoc style
    - 'reST': restructured text style compatible with Sphinx
    - 'groups': parameters on beginning of lines (like Google Docs)
    - 'numpydoc': the numpy format for docstrings (using an external module)

    '''
    #TODO: enhance style dependent separation
    #TODO: add set methods to generate style specific outputs
    #TODO: manage C style (\param)
    def __init__(self, style_in='javadoc', style_out='reST', params=None):
        '''Choose the kind of docstring type.

        @param style_in: docstring input style ('javadoc', 'reST', 'groups', 'numpydoc')
        @type style_in: string
        @param style_out: docstring output style ('javadoc', 'reST', 'groups', 'numpydoc')
        @type style_out: string
        @param params: if known the parameters names that should be found in the docstring.
        @type params: list

        '''
        self.style = {'in': style_in,
                      'out': style_out}
        self.opt = {}
        self.keystyles = []
        self._set_available_styles()
        self.params = params
        self.numpydoc = NumpydocTools()

    def _set_available_styles(self):
        '''Set the internal styles list and available options in a structure as following:

            param: javadoc: name = '@param'
                            sep  = ':'
                   reST:    name = ':param'
                            sep  = ':'
                   ...
            type:  javadoc: name = '@type'
                            sep  = ':'
                   ...
            ...

        And sets the internal groups style:
            param:  'params', 'args', 'parameters', 'arguments'
            return: 'returns', 'return'
            raise:  'raises', 'raise', 'exceptions', 'exception'

        '''
        options_keystyle = {'keys': ['param', 'type', 'return', 'rtype', 'raise'],
                            'styles': {'javadoc': ('@', ':'),  # tuple:  key prefix, separator
                                       'reST': (':', ':'),
                                       'cstyle': ('\\', ' ')}
                           }
        self.keystyles = list(options_keystyle['styles'].keys())
        for op in options_keystyle['keys']:
            self.opt[op] = {}
            for style in options_keystyle['styles']:
                self.opt[op][style] = {'name': options_keystyle['styles'][style][0] + op,
                                       'sep': options_keystyle['styles'][style][1]
                                      }
        self.opt['return']['reST']['name'] = ':returns'
        self.opt['raise']['reST']['name'] = ':raises'
        self.groups = {
                    'param': ['params', 'args', 'parameters', 'arguments'],
                    'return': ['returns', 'return'],
                    'raise': ['raises', 'exceptions', 'raise', 'exception']
                    }

    def autodetect_style(self, data):
        '''Determine the style of a docstring,
        and sets it as the default input one for the instance.

        @param data: the docstring's data to recognize.
        @type data: str
        @return: the style detected else 'unknown'
        @rtype: str

        '''
        # evaluate styles with keys

        found_keys = defaultdict(int)
        for style in self.keystyles:
            for key in self.opt:
                found_keys[style] += data.count(self.opt[key][style]['name'])
        fkey = max(found_keys, key=found_keys.get)
        detected_style = fkey if found_keys[fkey] else 'unknown'

        # evaluate styles with groups

        if detected_style == 'unknown':
            found_groups = 0
            found_numpydoc = 0
            found_numpydocsep = 0
            for line in data.strip().split(os.linesep):
                for key in self.groups:
                    found_groups += 1 if isin_start(self.groups[key], line) else 0
                for key in self.numpydoc:
                    found_numpydoc += 1 if isin_start(self.numpydoc[key], line) else 0
                if line.strip() and isin_alone(['-' * len(line.strip())], line):
                    found_numpydocsep += 1
                elif isin(self.numpydoc.keywords, line):
                    found_numpydoc += 1
            #TODO: check if not necessary to have > 1??
            if found_numpydoc and found_numpydocsep:
                detected_style = 'numpydoc'
            elif found_groups:
                detected_style = 'groups'
        self.style['in'] = detected_style

        return detected_style

    def set_input_style(self, style):
        '''Set the input docstring style

        @param style: style to set for input docstring
        @type style: str

        '''
        self.style['in'] = style

    def set_output_style(self, style):
        '''Set the output docstring style

        @param style: style to set for output docstring
        @type style: str

        '''
        self.style['out'] = style

    def _get_options(self, style):
        '''Get the list of keywords for a particular style

        @param style: the style that the keywords are wanted

        '''
        return [self.opt[o][style]['name'] for o in self.opt]

    def get_key(self, key, target='in'):
        '''Get the name of a key in current style.
        e.g.: in javadoc style, the returned key for 'param' is '@param'

        @param key: the key wanted (param, type, return, rtype,..)
        @param target: the target docstring is 'in' for the input or
        'out' for the output to generate.

        '''
        target = 'out' if target == 'out' else 'in'
        return self.opt[key][self.style[target]]['name']

    def get_sep(self, key='param', target='in'):
        '''Get the separator of current style.
        e.g.: in javadoc style, it is ":"

        @param key: the key which separator is wanted (param, type, return, rtype,..)
        @param target: the target docstring is 'in' for the input or
        'out' for the output to generate.

        '''
        target = 'out' if target == 'out' else 'in'
        if self.style[target] == 'numpydoc':
            return ''
        return self.opt[key][self.style[target]]['sep']

    def set_known_parameters(self, params):
        '''Set known parameters names.

        @param params: the docstring parameters names
        @type params: list
        '''
        self.params = params

    def get_group_key_line(self, data, key):
        '''Get the next group-style key's line number.

        @param data: string to parse
        @param key: the key category
        @return: the found line number else -1

        '''
        idx = -1
        for i, line in enumerate(data.split(os.linesep)):
            if isin_start(self.groups[key], line):
                idx = i
        return idx
#        search = '\s*(%s)' % '|'.join(self.groups[key])
#        m = re.match(search, data.lower())
#        if m:
#            key_param = m.group(1)

    def get_group_key_index(self, data, key):
        '''Get the next groups style's starting line index for a key

        @param data: string to parse
        @param key: the key category
        @return: the index if found else -1

        '''
        idx = -1
        li = self.get_group_key_line(data, key)
        if li != -1:
            idx = 0
            for line in data.split(os.linesep)[:li]:
                idx += len(line) + len(os.linesep)
        return idx

    def get_group_line(self, data):
        '''Get the next group-style key's line.
        '''
        idx = -1
        for key in self.groups:
            i = self.get_group_key_line(data, key)
            if (i < idx and i != -1) or idx == -1:
                idx = i
        return idx

    def get_group_index(self, data):
        '''Get the next groups style's starting line index

        @param data: string to parse
        @return: the index if found else -1

        '''
        idx = -1
        li = self.get_group_line(data)
        if li != -1:
            idx = 0
            for line in data.split(os.linesep)[:li]:
                idx += len(line) + len(os.linesep)
        return idx

    def get_key_index(self, data, key, starting=True):
        '''Get from a docstring the next option with a given key.

        @param data: string to parse
        @param starting: does the key element must start the line
        @type starting: boolean
        @param key: the key category. Can be 'param', 'type', 'return', ...
        @return: index of found element else -1
        @rtype: integer

        '''
        key = self.opt[key][self.style['in']]['name']
        idx = len(data)
        ini = 0
        loop = True
        if key in data:
            while loop:
                i = data.find(key)
                if i != -1:
                    if starting:
                        if not data[:i].rstrip(' \t').endswith(os.linesep) and len(data[:i].strip()) > 0:
                            ini = i + 1
                            data = data[ini:]
                        else:
                            idx = ini + i
                            loop = False
                    else:
                        idx = ini + i
                        loop = False
                else:
                    loop = False
        if idx == len(data):
            idx = -1
        return idx

    def get_elem_index(self, data, starting=True):
        '''Get from a docstring the next option.
        In javadoc style it could be @param, @return, @type,...

        @param data: string to parse
        @param starting: does the key element must start the line
        @type starting: boolean
        @return: index of found element else -1
        @rtype: integer

        '''
        idx = len(data)
        for opt in self.opt.keys():
            i = self.get_key_index(data, opt, starting)
            if i < idx and i != -1:
                idx = i
        if idx == len(data):
            idx = -1
        return idx

    def get_elem_desc(self, data, key):
        '''
        '''

    def get_elem_param(self):
        '''
        '''

    def get_raise_indexes(self, data):
        '''Get from a docstring the next raise name indexes.
        In javadoc style it is after @raise.

        @param data: string to parse
        @return: start and end indexes of found element else (-1, -1)
        or else (-2, -2) if try to use params style but no parameters were provided.
        Note: the end index is the index after the last name character
        @rtype: tuple

        '''
        start, end = -1, -1
        stl_param = self.opt['raise'][self.style['in']]['name']
        if self.style['in'] in self.keystyles + ['unknown']:
            idx_p = self.get_key_index(data, 'raise')
            if idx_p >= 0:
                idx_p += len(stl_param)
                m = re.match(r'^([\w]+)', data[idx_p:].strip())
                if m:
                    param = m.group(1)
                    start = idx_p + data[idx_p:].find(param)
                    end = start + len(param)

        if self.style['in'] in ['groups', 'unknown'] and (start, end) == (-1, -1):
            #search = '\s*(%s)' % '|'.join(self.groups['param'])
            #m = re.match(search, data.lower())
            #if m:
            #    key_param = m.group(1)
            pass

        return (start, end)

    def get_raise_description_indexes(self, data, prev=None):
        '''Get from a docstring the next raise's description.
        In javadoc style it is after @param.

        @param data: string to parse
        @param prev: index after the param element name
        @return: start and end indexes of found element else (-1, -1)
        @rtype: tuple

        '''
        start, end = -1, -1
        if not prev:
            _, prev = self.get_raise_indexes(data)
        if prev < 0:
            return (-1, -1)
        m = re.match(r'\W*(\w+)', data[prev:])
        if m:
            first = m.group(1)
            start = data[prev:].find(first)
            if start >= 0:
                start += prev
                if self.style['in'] in self.keystyles + ['unknown']:
                    end = self.get_elem_index(data[start:])
                    if end >= 0:
                        end += start
                if self.style['in'] in ['params', 'unknown'] and end == -1:
                    p1, _ = self.get_raise_indexes(data[start:])
                    if p1 >= 0:
                        end = p1
                    else:
                        end = len(data)

        return (start, end)

    def get_param_indexes(self, data):
        '''Get from a docstring the next parameter name indexes.
        In javadoc style it is after @param.

        @param data: string to parse
        @return: start and end indexes of found element else (-1, -1)
        or else (-2, -2) if try to use params style but no parameters were provided.
        Note: the end index is the index after the last name character
        @rtype: tuple

        '''
        #TODO: new method to extract an element's name so will be available for @param and @types and other styles (:param, \param)
        start, end = -1, -1
        stl_param = self.opt['param'][self.style['in']]['name']
        if self.style['in'] in self.keystyles + ['unknown']:
            idx_p = self.get_key_index(data, 'param')
            if idx_p >= 0:
                idx_p += len(stl_param)
                m = re.match(r'^([\w]+)', data[idx_p:].strip())
                if m:
                    param = m.group(1)
                    start = idx_p + data[idx_p:].find(param)
                    end = start + len(param)

        if self.style['in'] in ['groups', 'unknown'] and (start, end) == (-1, -1):
            #search = '\s*(%s)' % '|'.join(self.groups['param'])
            #m = re.match(search, data.lower())
            #if m:
            #    key_param = m.group(1)
            pass

        if self.style['in'] in ['params', 'groups', 'unknown'] and (start, end) == (-1, -1):
            if self.params == None:
                return (-2, -2)
            idx = -1
            param = None
            for p in self.params:
                if type(p) is tuple:
                    p = p[0]
                i = data.find(os.linesep + p)
                if i >= 0:
                    if idx == -1 or i < idx:
                        idx = i
                        param = p
            if idx != -1:
                start, end = idx, idx + len(param)
        return (start, end)

    def get_param_description_indexes(self, data, prev=None):
        '''Get from a docstring the next parameter's description.
        In javadoc style it is after @param.

        @param data: string to parse
        @param prev: index after the param element name
        @return: start and end indexes of found element else (-1, -1)
        @rtype: tuple

        '''
        start, end = -1, -1
        if not prev:
            _, prev = self.get_param_indexes(data)
        if prev < 0:
            return (-1, -1)
        m = re.match(r'\W*(\w+)', data[prev:])
        if m:
            first = m.group(1)
            start = data[prev:].find(first)
            if start >= 0:
                start += prev
                if self.style['in'] in self.keystyles + ['unknown']:
                    end = self.get_elem_index(data[start:])
                    if end >= 0:
                        end += start
                if self.style['in'] in ['params', 'unknown'] and end == -1:
                    p1, _ = self.get_param_indexes(data[start:])
                    if p1 >= 0:
                        end = p1
                    else:
                        end = len(data)

        return (start, end)

    def get_param_type_indexes(self, data, name=None, prev=None):
        '''Get from a docstring a parameter type indexes.
        In javadoc style it is after @type.

        @param data: string to parse
        @param name: the name of the parameter
        @param prev: index after the previous element (param or param's description)
        @return: start and end indexes of found element else (-1, -1)
        Note: the end index is the index after the last included character or -1 if
        reached the end
        @rtype: tuple

        '''
        start, end = -1, -1
        stl_type = self.opt['type'][self.style['in']]['name']
        if not prev:
            _, prev = self.get_param_description_indexes(data)
        if prev >= 0:
            if self.style['in'] in self.keystyles + ['unknown']:
                idx = self.get_elem_index(data[prev:])
                if idx >= 0 and data[prev + idx:].startswith(stl_type):
                    idx = prev + idx + len(stl_type)
                    m = re.match(r'\W*(\w+)\W+(\w+)\W*', data[idx:].strip())
                    if m:
                        param = m.group(1).strip()
                        if (name and param == name) or not name:
                            desc = m.group(2)
                            start = data[idx:].find(desc) + idx
                            end = self.get_elem_index(data[start:])
                            if end >= 0:
                                end += start

            if self.style['in'] in ['params', 'unknown'] and (start, end) == (-1, -1):
                #TODO: manage this
                pass

        return (start, end)

    def get_return_description_indexes(self, data):
        '''Get from a docstring the return parameter description indexes.
        In javadoc style it is after @return.

        @param data: string to parse
        @return: start and end indexes of found element else (-1, -1)
        Note: the end index is the index after the last included character or -1 if
        reached the end
        @rtype: tuple

        '''
        start, end = -1, -1
        stl_return = self.opt['return'][self.style['in']]['name']
        if self.style['in'] in self.keystyles + ['unknown']:
            idx = self.get_key_index(data, 'return')
            idx_abs = idx
            # search starting description
            if idx >= 0:
                #FIXME: take care if a return description starts with <, >, =,...
                m = re.match(r'\W*(\w+)', data[idx_abs + len(stl_return):])
                if m:
                    first = m.group(1)
                    idx = data[idx_abs:].find(first)
                    idx_abs += idx
                    start = idx_abs
                else:
                    idx = -1
            # search the end
            idx = self.get_elem_index(data[idx_abs:])
            if idx > 0:
                idx_abs += idx
                end = idx_abs

        if self.style['in'] in ['params', 'unknown'] and (start, end) == (-1, -1):
            #TODO: manage this
            pass

        return (start, end)

    def get_return_type_indexes(self, data):
        '''Get from a docstring the return parameter type indexes.
        In javadoc style it is after @rtype.

        @param data: string to parse
        @return: start and end indexes of found element else (-1, -1)
        Note: the end index is the index after the last included character or -1 if
        reached the end
        @rtype: tuple

        '''
        start, end = -1, -1
        stl_rtype = self.opt['rtype'][self.style['in']]['name']
        if self.style['in'] in self.keystyles + ['unknown']:
            dstart, dend = self.get_return_description_indexes(data)
            # search the start
            if dstart >= 0 and dend > 0:
                idx = self.get_elem_index(data[dend:])
                if idx >= 0 and data[dend + idx:].startswith(stl_rtype):
                    idx = dend + idx + len(stl_rtype)
                    m = re.match(r'\W*(\w+)', data[idx:])
                    if m:
                        first = m.group(1)
                        start = data[idx:].find(first) + idx
            # search the end
            idx = self.get_elem_index(data[start:])
            if idx > 0:
                end = idx + start

        if self.style['in'] in ['params', 'unknown'] and (start, end) == (-1, -1):
            #TODO: manage this
            pass

        return (start, end)


class DocString(object):
    '''This class represents the docstring'''
    #TODO: manage raising

    def __init__(self, elem_raw, spaces='', docs_raw=None, quotes="'''", input_style=None, output_style=None, first_line=False, **kwargs):
        '''
        @param elem_raw: raw data of the element (def or class).
        @param spaces: the leading whitespaces before the element
        @param docs_raw: the raw data of the docstring part if any.
        @param quotes: the type of quotes to use for output: ' ' ' or " " "
        @param style_in: docstring input style ('javadoc', 'reST', 'groups', 'numpydoc', None). If None will be autodetected
        @type style_in: string
        @param style_out: docstring output style ('javadoc', 'reST', 'groups', 'numpydoc')
        @type style_out: string
        @param first_line: indicate if description should start
        on first or second line
        @type first_line: boolean

        '''
        self.dst = DocsTools()
        self.first_line = first_line
        if docs_raw and not input_style:
            self.dst.autodetect_style(docs_raw)
        elif input_style:
            self.set_input_style(input_style)
        if output_style:
            self.set_output_style(output_style)
        self.element = {
            'raw': elem_raw,
            'name': None,
            'type': None,
            'params': [],
            'spaces': spaces
            }
        if docs_raw:
            docs_raw = docs_raw.strip()
            if docs_raw.startswith('"""') or docs_raw.startswith("'''"):
                docs_raw = docs_raw[3:]
            if docs_raw.endswith('"""') or docs_raw.endswith("'''"):
                docs_raw = docs_raw[:-3]
        self.docs = {
            'in': {
                'raw': docs_raw,
                'desc': None,
                'params': [],
                'types': [],
                'return': None,
                'rtype': None,
                'raises': []
                },
            'out': {
                'raw': '',
                'desc': None,
                'params': [],
                'types': [],
                'return': None,
                'rtype': None,
                'raises': [],
                'spaces': spaces + ' ' * 2
                }
            }
        if '\t' in spaces:
            self.docs['out']['spaces'] = spaces + '\t'
        elif (len(spaces) % 4) == 0 or spaces == '':
            #FIXME: should bug if tabs for class or function (as spaces=='')
            self.docs['out']['spaces'] = spaces + ' ' * 4
        self.parsed_elem = False
        self.parsed_docs = False
        self.generated_docs = False

        self.parse_element()
        self.quotes = quotes

    def __str__(self):
        # !!! for debuging
        txt = "\n\n** " + str(self.element['name'])
        txt += ' of type ' + str(self.element['type']) + ':'
        txt += str(self.docs['in']['desc']) + os.linesep
        txt += '->' + str(self.docs['in']['params']) + os.linesep
        txt += '***>>' + str(self.docs['out']['raw']) + os.linesep + os.linesep
        return txt

    def __repr__(self):
        return self.__str__()

    def get_input_style(self):
        '''Gets the input docstring style

        @return: the style for input docstring
        @rtype style: str

        '''
        #TODO: use a getter
        return self.dst.style['in']

    def set_input_style(self, style):
        '''Sets the input docstring style

        @param style: style to set for input docstring
        @type style: str

        '''
        #TODO: use a setter
        self.dst.style['in'] = style

    def get_output_style(self):
        '''Sets the output docstring style

        @return: the style for output docstring
        @rtype style: str

        '''
        #TODO: use a getter
        return self.dst.style['out']

    def set_output_style(self, style):
        '''Sets the output docstring style

        @param style: style to set for output docstring
        @type style: str

        '''
        #TODO: use a setter
        self.dst.style['out'] = style

    def get_spaces(self):
        '''Get the output docstring initial spaces.

        @return: the spaces

        '''
        return self.docs['out']['spaces']

    def set_spaces(self, spaces):
        '''Set for output docstring the initial spaces.

        @param spaces: the spaces to set

        '''
        self.docs['out']['spaces'] = spaces

    def parse_element(self, raw=None):
        '''Parses the element's elements (type, name and parameters) :)
        e.g.: def methode(param1, param2='default')
            def                      -> type
            methode                  -> name
            param1, param2='default' -> parameters

        @param raw: raw data of the element (def or class).

        '''
        #TODO: retrieve return from element external code (in parameter)
        if raw is None:
            l = self.element['raw'].strip()
        else:
            l = raw.strip()
        is_class = False
        if l.startswith('def ') or l.startswith('class '):
            # retrieves the type
            if l.startswith('def'):
                self.element['type'] = 'def'
                l = l.replace('def ', '')
            else:
                self.element['type'] = 'class'
                l = l.replace('class ', '')
                is_class = True
            # retrieves the name
            self.element['name'] = l[:l.find('(')].strip()
            if not is_class:
                if l[-1] == ':':
                    l = l[:-1].strip()
                # retrieves the parameters
                l = l[l.find('(') + 1:l.find(')')].strip()
                lst = [c.strip() for c in l.split(',')]
                for e in lst:
                    if '=' in e:
                        k, v = e.split('=', 1)
                        self.element['params'].append((k.strip(), v.strip()))
                    elif e and e != 'self' and e != 'cls':
                        self.element['params'].append(e)
        self.parsed_elem = True

    def _extract_docs_description(self):
        '''Extract main description from docstring'''
        #FIXME: the indentation of descriptions is lost
        data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
        if self.dst.style['in'] == 'groups':
            idx = self.dst.get_group_index(data)
        elif self.dst.style['in'] == 'numpydoc':
            lines = data.split(os.linesep)
            line_num = self.dst.numpydoc.get_next_section_start_line(lines)
            if line_num == -1:
                idx = -1
            else:
                idx = len(os.linesep.join(lines[:line_num]))
        elif self.dst.style['in'] == 'unknown':
            idx = -1
        else:
            idx = self.dst.get_elem_index(data)
        if idx == 0:
            self.docs['in']['desc'] = ''
        elif idx == -1:
            self.docs['in']['desc'] = data
        else:
            self.docs['in']['desc'] = data[:idx]

    def _extract_groupstyle_docs_params(self):
        data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
        idx = self.dst.get_group_key_line(data, 'param')
        if idx >= 0:
            data = data.split(os.linesep)[idx+1:]
            end = self.dst.get_group_line(os.linesep.join(data))
            end = end if end != -1 else len(data)
            for i in xrange(end):
                #FIXME: see how retrieve multiline param description and how get type
                line = data[i]
                param = None
                desc = ''
                ptype = ''
                m = re.match(r'^\W*(\w+)[\W\s]+(\w[\s\w]+)', line.strip())
                if m:
                    param = m.group(1).strip()
                    desc = m.group(2).strip()
                else:
                    m = re.match(r'^\W*(\w+)\W*', line.strip())
                    if m:
                        param = m.group(1).strip()
                if param:
                    self.docs['in']['params'].append((param, desc, ptype))

    def _extract_keystyle_docs_params(self):
        data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
        listed = 0
        loop = True
        maxi = 10000  # avoid infinite loop but should never happen
        i = 0
        while loop:
            i += 1
            if i > maxi:
                loop = False
            start, end = self.dst.get_param_indexes(data)
            if start >= 0:
                param = data[start: end]
                desc = ''
                start, end = self.dst.get_param_description_indexes(data, prev=end)
                if start > 0:
                    desc = data[start: end].strip()
                ptype = ''
                start, pend = self.dst.get_param_type_indexes(data, name=param, prev=end)
                if start > 0:
                    ptype = data[start: pend].strip()
                # a parameter is stored with: (name, description, type)
                self.docs['in']['params'].append((param, desc, ptype))
                data = data[end:]
                listed += 1
            else:
                loop = False
        if i > maxi:
            print("WARNING: an infinite loop was reached while extracting docstring parameters (>10000). This should never happen!!!")

    def _extract_docs_params(self):
        '''Extract parameters description and type from docstring. The internal computed parameters list is
        composed by tuples (parameter, description, type).

        '''
        if self.dst.style['in'] == 'numpydoc':
            data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
            self.docs['in']['params'] += self.dst.numpydoc.get_param_list(data)
        elif self.dst.style['in'] == 'groups':
            self._extract_groupstyle_docs_params()
        elif self.dst.style['in'] in ['javadoc', 'reST']:
            self._extract_keystyle_docs_params()

    def _extract_groupstyle_docs_raises(self):
        data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
        idx = self.dst.get_group_key_line(data, 'raise')
        if idx >= 0:
            data = data.split(os.linesep)[idx+1:]
            end = self.dst.get_group_line(os.linesep.join(data))
            end = end if end != -1 else len(data)
            for i in xrange(end):
                #FIXME: see how retrieve multiline raise description
                line = data[i]
                param = None
                desc = ''
                m = re.match(r'^\W*(\w+)[\W\s]+(\w[\s\w]+)', line.strip())
                if m:
                    param = m.group(1).strip()
                    desc = m.group(2).strip()
                else:
                    m = re.match(r'^\W*(\w+)\W*', line.strip())
                    if m:
                        param = m.group(1).strip()
                if param:
                    self.docs['in']['raises'].append((param, desc))

    def _extract_keystyle_docs_raises(self):
        data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
        listed = 0
        loop = True
        maxi = 10000  # avoid infinite loop but should never happen
        i = 0
        while loop:
            i += 1
            if i > maxi:
                loop = False
            start, end = self.dst.get_raise_indexes(data)
            if start >= 0:
                param = data[start: end]
                desc = ''
                start, end = self.dst.get_raise_description_indexes(data, prev=end)
                if start > 0:
                    desc = data[start: end].strip()
                # a parameter is stored with: (name, description)
                self.docs['in']['raises'].append((param, desc))
                data = data[end:]
                listed += 1
            else:
                loop = False
        if i > maxi:
            print("WARNING: an infinite loop was reached while extracting docstring parameters (>10000). This should never happen!!!")

    def _extract_docs_raises(self):
        '''Extract raises description from docstring. The internal computed raises list is
        composed by tuples (raise, description).

        '''
        if self.dst.style['in'] == 'numpydoc':
            data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
            self.docs['in']['raises'] += self.dst.numpydoc.get_raise_list(data)
        elif self.dst.style['in'] == 'groups':
            self._extract_groupstyle_docs_raises()
        elif self.dst.style['in'] in ['javadoc', 'reST']:
            self._extract_keystyle_docs_raises()

    def _extract_groupstyle_docs_return(self):
        #TODO: manage rtype
        data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
        idx = self.dst.get_group_key_line(data, 'return')
        if idx >= 0:
            data = data.split(os.linesep)[idx+1:]
            end = self.dst.get_group_line(os.linesep.join(data))
            end = end if end != -1 else len(data)
            data = os.linesep.join(data[:end]).strip()
            self.docs['in']['return'] = data.rstrip()

    def _extract_keystyle_docs_return(self):
        data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
        start, end = self.dst.get_return_description_indexes(data)
        if start >= 0:
            if end >= 0:
                self.docs['in']['return'] = data[start:end].rstrip()
            else:
                self.docs['in']['return'] = data[start:].rstrip()
        start, end = self.dst.get_return_type_indexes(data)
        if start >= 0:
            if end >= 0:
                self.docs['in']['rtype'] = data[start:end].rstrip()
            else:
                self.docs['in']['rtype'] = data[start:].rstrip()

    def _extract_docs_return(self):
        '''Extract return description and type
        '''
        if self.dst.style['in'] == 'numpydoc':
            data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
            self.docs['in']['return'] = self.dst.numpydoc.get_return_list(data)
            self.docs['in']['rtype'] = None
        elif self.dst.style['in'] == 'groups':
            self._extract_groupstyle_docs_return()
        elif self.dst.style['in'] in ['javadoc', 'reST']:
            self._extract_keystyle_docs_return()

    def _extract_docs_other(self):
        '''Extract other specific sections
        '''
        if self.dst.style['in'] == 'numpydoc':
            data = os.linesep.join([d.rstrip().replace(self.docs['out']['spaces'], '', 1) for d in self.docs['in']['raw'].split(os.linesep)])
            lst = self.dst.numpydoc.get_list_key(data, 'also')
            lst = self.dst.numpydoc.get_list_key(data, 'ref')
            lst = self.dst.numpydoc.get_list_key(data, 'note')
            lst = self.dst.numpydoc.get_list_key(data, 'other')
            lst = self.dst.numpydoc.get_list_key(data, 'example')
            lst = self.dst.numpydoc.get_list_key(data, 'attr')

    def parse_docs(self, raw=None):
        '''Parses the docstring

        @param raw: the data to parse if not internally provided

        '''
        if raw is not None:
            raw = raw.strip()
            if raw.startswith('"""') or raw.startswith("'''"):
                raw = raw[3:]
            if raw.endswith('"""') or raw.endswith("'''"):
                raw = raw[:-3]
            self.docs['in']['raw'] = raw
            self.dst.autodetect_style(raw)
        if self.docs['in']['raw'] is None:
            return
        self.dst.set_known_parameters(self.element['params'])
        self._extract_docs_params()
        self._extract_docs_return()
        self._extract_docs_raises()
        self._extract_docs_description()
        self._extract_docs_other()
        self.parsed_docs = True

    def _set_desc(self):
        '''Sets the global description if any
        '''
        #TODO: manage different in/out styles
        if self.docs['in']['desc']:
            self.docs['out']['desc'] = self.docs['in']['desc']
        else:
            self.docs['out']['desc'] = ''

    def _set_params(self):
        '''Sets the parameters with types, descriptions and default value if any
        '''
        #TODO: manage different in/out styles
        if self.docs['in']['params']:
            # list of parameters is like: (name, description, type)
            self.docs['out']['params'] = list(self.docs['in']['params'])
        for e in self.element['params']:
            if type(e) is tuple:
                # tuple is: (name, default)
                param = e[0]
            else:
                param = e
            found = False
            for i, p in enumerate(self.docs['out']['params']):
                if param == p[0]:
                    found = True
                    # add default value if any
                    if type(e) is tuple:
                        # param will contain: (name, desc, type, default)
                        self.docs['out']['params'][i] = (p[0], p[1], p[2], e[1])
            if not found:
                if type(e) is tuple:
                    p = (param, '', None, e[1])
                else:
                    p = (param, '', None, None)
                self.docs['out']['params'].append(p)

    def _set_raises(self):
        '''Sets the raises and descriptions
        '''
        #TODO: manage different in/out styles
        #manage setting if not mandatory for numpy but optional
        if self.docs['in']['raises']:
            if self.dst.style['out'] != 'numpydoc' or self.dst.style['in'] == 'numpydoc' or \
                     (self.dst.style['out'] == 'numpydoc' and \
                    'raise' not in self.dst.numpydoc.get_excluded_sections()):
                # list of parameters is like: (name, description)
                self.docs['out']['raises'] = list(self.docs['in']['raises'])

    def _set_return(self):
        '''Sets the return parameter with description and rtype if any
        '''
        #TODO: manage return retrieved from element code (external)
        #TODO: manage different in/out styles
        if type(self.docs['in']['return']) is list and self.dst.style['out'] not in ['groups', 'numpydoc']:
            #TODO: manage return names
            #manage not setting return if not mandatory for numpy
            lst = self.docs['in']['return']
            if lst[0][0] is not None:
                self.docs['out']['return'] = "%s-> %s" % (lst[0][0], lst[0][1])
            else:
                self.docs['out']['return'] = lst[0][1]
            self.docs['out']['rtype'] = lst[0][2]
        else:
            self.docs['out']['return'] = self.docs['in']['return']
            self.docs['out']['rtype'] = self.docs['in']['rtype']


    def _set_other(self):
        '''Sets other specific sections
        '''
            #manage not setting if not mandatory for numpy
        if self.dst.style['in'] == 'numpydoc':
            self.docs['out']['post'] = self.dst.numpydoc.get_raw_not_managed(self.docs['in']['raw'])

    def _set_raw_params(self, sep):
        '''Set the output raw parameters section
        '''
        raw = os.linesep
        if self.dst.style['out'] == 'numpydoc':
            spaces = ' ' * 4
            with_space = lambda s: os.linesep.join([self.docs['out']['spaces'] + spaces + l.lstrip() if i > 0 else l for i, l in enumerate(s.split(os.linesep))])
            raw += self.dst.numpydoc.get_key_section_header('param', self.docs['out']['spaces'])
            for p in self.docs['out']['params']:
                raw += self.docs['out']['spaces'] + p[0] + ' :'
                if p[2] is not None and len(p[2]) > 0:
                    raw += ' ' + p[2]
                raw += os.linesep
                raw += self.docs['out']['spaces'] + spaces + with_space(p[1]).strip()
                if len(p) > 2:
                    if 'default' not in p[1].lower() and len(p) > 3 and p[3] is not None:
                        raw += ' (Default value = ' + str(p[3]) + ')'
                raw += os.linesep
        elif self.dst.style['out'] == 'groups':
            pass
        else:
            with_space = lambda s: os.linesep.join([self.docs['out']['spaces'] + l if i > 0 else l for i, l in enumerate(s.split(os.linesep))])
            if len(self.docs['out']['params']):
                for p in self.docs['out']['params']:
                    raw += self.docs['out']['spaces'] + self.dst.get_key('param', 'out') + ' ' + p[0] + sep + with_space(p[1]).strip()
                    if len(p) > 2:
                        if 'default' not in p[1].lower() and len(p) > 3 and p[3] is not None:
                            raw += ' (Default value = ' + str(p[3]) + ')'
                        if p[2] is not None and len(p[2]) > 0:
                            raw += os.linesep
                            raw += self.docs['out']['spaces'] + self.dst.get_key('type', 'out') + ' ' + p[0] + sep + p[2]
                        raw += os.linesep
                    else:
                        raw += os.linesep
        return raw

    def _set_raw_raise(self, sep):
        '''Set the output raw exception section
        '''
        raw = ''
        if self.dst.style['out'] == 'numpydoc':
            if 'raise' not in self.dst.numpydoc.get_excluded_sections():
                raw += os.linesep
                if 'raise' in self.dst.numpydoc.get_mandatory_sections() or \
                        (self.docs['out']['raises'] and 'raise' in self.dst.numpydoc.get_optional_sections()):
                    spaces = ' ' * 4
                    with_space = lambda s: os.linesep.join([self.docs['out']['spaces'] + spaces + l.lstrip() if i > 0 else l for i, l in enumerate(s.split(os.linesep))])
                    raw += self.dst.numpydoc.get_key_section_header('raise', self.docs['out']['spaces'])
                    if len(self.docs['out']['raises']):
                        for p in self.docs['out']['raises']:
                            raw += self.docs['out']['spaces'] + p[0] + os.linesep
                            raw += self.docs['out']['spaces'] + spaces + with_space(p[1]).strip() + os.linesep
                    raw += os.linesep
        elif self.dst.style['out'] == 'groups':
            pass
        else:
            with_space = lambda s: os.linesep.join([self.docs['out']['spaces'] + l if i > 0 else l for i, l in enumerate(s.split(os.linesep))])
            if len(self.docs['out']['raises']):
                if not self.docs['out']['params'] and not self.docs['out']['return']:
                    raw += os.linesep
                for p in self.docs['out']['raises']:
                    raw += self.docs['out']['spaces'] + self.dst.get_key('raise', 'out') + ' ' + p[0] + sep + with_space(p[1]).strip() + os.linesep
            raw += os.linesep
        return raw

    def _set_raw_return(self, sep):
        '''Set the output raw return section
        '''
        raw = ''
        if self.dst.style['out'] == 'numpydoc':
            raw += os.linesep
            spaces = ' ' * 4
            with_space = lambda s: os.linesep.join([self.docs['out']['spaces'] + spaces + l.lstrip() if i > 0 else l for i, l in enumerate(s.split(os.linesep))])
            raw += self.dst.numpydoc.get_key_section_header('return', self.docs['out']['spaces'])
            if self.docs['out']['rtype']:
                rtype = self.docs['out']['rtype']
            else:
                rtype = 'type'
            # case of several returns
            if type(self.docs['out']['return']) is list:
                for ret_elem in self.docs['out']['return']:
                    # if tuple (name, desc, rtype) else string desc
                    if type(ret_elem) is tuple and len(ret_elem) == 3:
                        rtype = ret_elem[2]
                        raw += self.docs['out']['spaces']
                        if ret_elem[0]:
                            raw += ret_elem[0] + ' : '
                        raw += rtype + os.linesep + self.docs['out']['spaces'] + spaces + with_space(ret_elem[1]).strip() + os.linesep
                    else:
                        # There can be a problem
                        raw += self.docs['out']['spaces'] + rtype + os.linesep
                        raw += self.docs['out']['spaces'] + spaces + with_space(str(ret_elem)).strip() + os.linesep
            # case of a unique return
            elif self.docs['out']['return'] is not None:
                raw += self.docs['out']['spaces'] + rtype
                raw += os.linesep + self.docs['out']['spaces'] + spaces + with_space(self.docs['out']['return']).strip() + os.linesep
        elif self.dst.style['out'] == 'groups':
            pass
        else:
            with_space = lambda s: os.linesep.join([self.docs['out']['spaces'] + l if i > 0 else l for i, l in enumerate(s.split(os.linesep))])
            if self.docs['out']['return']:
                if not self.docs['out']['params']:
                    raw += os.linesep
                raw += self.docs['out']['spaces'] + self.dst.get_key('return', 'out') + sep + with_space(self.docs['out']['return'].rstrip()).strip() + os.linesep
            if self.docs['out']['rtype']:
                if not self.docs['out']['params']:
                    raw += os.linesep
                raw += self.docs['out']['spaces'] + self.dst.get_key('rtype', 'out') + sep + self.docs['out']['rtype'].rstrip() + os.linesep
        return raw

    def _set_raw(self):
        '''Sets the output raw docstring
        '''
        sep = self.dst.get_sep(target='out')
        sep = sep + ' ' if sep != ' ' else sep
        with_space = lambda s: os.linesep.join([self.docs['out']['spaces'] + l if i > 0 else l for i, l in enumerate(s.split(os.linesep))])

        # sets the description section
        raw = self.docs['out']['spaces'] + self.quotes
        desc = self.docs['out']['desc'].strip()
        if not desc or not desc.count(os.linesep):
            if not self.docs['out']['params'] and not self.docs['out']['return'] and not self.docs['out']['rtype'] and not self.docs['out']['raises']:
                raw += desc if desc else ' '
                raw += self.quotes
                self.docs['out']['raw'] = raw.rstrip()
                return
        if not self.first_line:
            raw += os.linesep + self.docs['out']['spaces']
        raw += with_space(self.docs['out']['desc']).strip() + os.linesep

        # sets the parameters section
        raw += self._set_raw_params(sep)

        # sets the return section
        raw += self._set_raw_return(sep)

        # sets the raises section
        raw += self._set_raw_raise(sep)

        # sets post specific if any
        if 'post' in self.docs['out']:
            raw += self.docs['out']['spaces'] + with_space(self.docs['out']['post']).strip() + os.linesep

        if raw.count(self.quotes) == 1:
            raw += self.docs['out']['spaces'] + self.quotes
        self.docs['out']['raw'] = raw.rstrip()

    def generate_docs(self):
        '''
        '''
        if self.dst.style['out'] == 'numpydoc' and self.dst.numpydoc.first_line is not None:
            self.first_line = self.dst.numpydoc.first_line
        self._set_desc()
        self._set_params()
        self._set_return()
        self._set_raises()
        self._set_other()
        self._set_raw()
        self.generated_docs = True

    def get_raw_docs(self):
        '''Generates raw docstring

        @return: the raw docstring

        '''
        if not self.generated_docs:
            self.generate_docs()
        return self.docs['out']['raw']


if __name__ == "__main__":
    data1 = '''This is test

    @param par1: the first param1

    '''
    data2 = '''This is test

    @param par1: the first param1
    @param prm2: the second param2

    '''
    data3 = '''This is test

    @param par1: the first param1
    @param prm2: the second param2
    @return: the return value

    '''
    data = data3
    print("data:'''" + data + "'''")
    print("")
    dst = DocsTools('javadoc')
    loop = True
    i, maxi = 0, 10
    while loop:
        i += 1
        if i > maxi:
            loop = False
        start, end = dst.get_param_indexes(data)
        if start >= 0:
            new_start = end
            print("param='" + data[start:end] + "'")
            start, end = dst.get_param_description_indexes(data)
            if start >= 0:
                print("desc='" + data[start:end] + "'")
            else:
                print('NO desc')
            data = data[new_start:]
        else:
            print("NO param")
            loop = False

########NEW FILE########
__FILENAME__ = pyment
# -*- coding: utf8 -*-

__author__ = "A. Daouzli"
__copyright__ = "Copyright 2013/12"
__licence__ = "GPL3"
__version__ = "0.2.1-dev"
__maintainer__ = "A. Daouzli"

#TODO:
# -generate a return if return is used with argument in element
# -generate raises if raises are used
# -generate diagnosis/statistics
# -parse classes public methods and list them in class docstring
# -allow excluding files from processing
# -add managing a unique patch
# -manage docstrings templates
# -manage c/c++ sources
# -accept archives containing source files
# -dev a server that take sources and send back patches

import os
import re
import difflib

from .docstring import DocString


class PyComment(object):
    '''This class allow to manage several python scripts docstrings.
    It is used to parse and rewrite in a Pythonic way all the functions', methods' and classes' docstrings.
    The changes are then provided in a patch file.

    '''
    def __init__(self, input_file, input_style=None, output_style='reST', quotes="'''", first_line=True,
                 config_file=None, ignore_private=False, **kwargs):
        '''Sets the configuration including the source to proceed and options.

        @param input_file: path name (file or folder)
        @param input_style: the type of doctrings format of the output. By default, it will
        autodetect the format for each docstring.
        @param output_style: the docstring docstyle to generate.
        @param quotes: the type of quotes to use for output: ' ' ' or " " "
        @param first_line: indicate if description should start
        on first or second line. By default it is True
        @type first_line: boolean
        @param config_file: if given configuration file for Pyment
        @param ignore_private: don't proceed the private methods/functions starting with __ (two underscores)

        '''
        self.file_type = '.py'
        self.first_line = first_line
        self.filename_list = []
        self.input_file = input_file
        self.input_style = input_style
        self.output_style = output_style
        self.doc_index = -1
        self.file_index = 0
        self.docs_list = []
        self.parsed = False
        self.quotes = quotes
        self.config_file = config_file
        self.ignore_private = ignore_private
        self.kwargs = kwargs

    def _parse(self):
        '''Parses the input file's content and generates a list of its elements/docstrings.

        '''
        #TODO manage decorators
        #TODO manage default params with strings escaping chars as (, ), ', ', #, ...
        #TODO manage elements ending with comments like: def func(param): # blabla
        elem_list = []
        reading_element = None
        reading_docs = None
        waiting_docs = False
        elem = ''
        raw = ''
        start = 0
        end = 0
        lines = []
        try:
            with open(self.input_file) as fd:
                lines = fd.readlines()
        except IOError:
            msg = BaseException('Failed to open file "' + self.input_file + '". Please provide a valid file.')
            raise msg
        for i, ln in enumerate(lines):
            l = ln.strip()
            if reading_element:
                elem += l
                if l.endswith(':'):
                    reading_element = 'end'
            elif (l.startswith('def ') or l.startswith('class ')) and not reading_docs:
                if self.ignore_private and l[l.find(' '):].strip().startswith("__"):
                    continue
                reading_element = 'start'
                elem = l
                m = re.match(r'^(\s*)[dc]{1}', ln)
                if m is not None and m.group(1) is not None:
                    spaces = m.group(1)
                else:
                    spaces = ''
                if l.endswith(':'):
                    reading_element = 'end'
            if reading_element == 'end':
                reading_element = None
                # if currently reading an element content
                waiting_docs = True
                # *** Creates the DocString object ***
                e = DocString(elem.replace(os.linesep, ' '), spaces, quotes=self.quotes,
                              input_style=self.input_style,
                              output_style=self.output_style,
                              first_line=self.first_line,
                              **self.kwargs)
                elem_list.append({'docs': e, 'location': (-i, -i)})
            else:
                if waiting_docs and ('"""' in l or "'''" in l):
                    # start of docstring bloc
                    if not reading_docs:
                        start = i
                        # determine which delimiter
                        idx_c = l.find('"""')
                        idx_dc = l.find("'''")
                        lim = '"""'
                        if idx_c >= 0 and idx_dc >= 0:
                            if idx_c < idx_dc:
                                lim = '"""'
                            else:
                                lim = "'''"
                        elif idx_c < 0:
                            lim = "'''"
                        reading_docs = lim
                        raw = ln
                        # one line docstring
                        if l.count(lim) == 2:
                            end = i
                            elem_list[-1]['docs'].parse_docs(raw)
                            elem_list[-1]['location'] = (start, end)
                            reading_docs = None
                            waiting_docs = False
                            reading_element = False
                            raw = ''
                    # end of docstring bloc
                    elif waiting_docs and lim in l:
                        end = i
                        raw += ln
                        elem_list[-1]['docs'].parse_docs(raw)
                        elem_list[-1]['location'] = (start, end)
                        reading_docs = None
                        waiting_docs = False
                        reading_element = False
                        raw = ''
                    # inside a docstring bloc
                    elif waiting_docs:
                        raw += ln
                # no docstring found for current element
                elif waiting_docs and l != '' and reading_docs is None:
                    waiting_docs = False
                else:
                    if reading_docs is not None:
                        raw += ln
        self.docs_list = elem_list
        self.parsed = True
        return elem_list

    def docs_init_to_class(self):
        '''If found a __init__ method's docstring and the class
        without any docstring, so set the class docstring with __init__one,
        and let __init__ without docstring.

        @return: True if done
        @rtype: boolean

        '''
        result = False
        if not self.parsed:
            self._parse()
        einit = []
        eclass = []
        for e in self.docs_list:
            if len(eclass) == len(einit) + 1 and e['docs'].element['name'] == '__init__':
                einit.append(e)
            elif not eclass and e['docs'].element['type'] == 'class':
                eclass.append(e)
        for c, i in zip(eclass, einit):
            start, _ = c['location']
            if start < 0:
                start, _ = i['location']
                if start > 0:
                    result = True
                    cspaces = c['docs'].get_spaces()
                    ispaces = i['docs'].get_spaces()
                    c['docs'].set_spaces(ispaces)
                    i['docs'].set_spaces(cspaces)
                    c['docs'].generate_docs()
                    i['docs'].generate_docs()
                    c['docs'], i['docs'] = i['docs'], c['docs']
        return result

    def get_output_docs(self):
        '''Return the output docstrings once formated

        @return: the formated docstrings
        @rtype: list

        '''
        if not self.parsed:
            self._parse()
        lst = []
        for e in self.docs_list:
            lst.append(e['docs'].get_raw_docs())
        return lst

    def diff(self, source_path='', target_path='', which=-1):
        '''Build the diff between original docstring and proposed docstring.

        @param which: indicates which docstring to proceed:
        -> -1 means all the dosctrings of the file
        -> >=0 means the index of the docstring to proceed
        @type which: int
        @return: the resulted diff
        @rtype: string

        '''
        #TODO: manage which
        if not self.parsed:
            self._parse()
        list_from = []
        try:
            with open(self.input_file) as fd:
                list_from = fd.readlines()
        except IOError:
            msg = BaseException('Failed to open file "' + self.input_file + '". Please provide a valid file.')
            raise msg
        list_to = []
        last = 0
        for e in self.docs_list:
            start, end = e['location']
            if start < 0:
                start, end = -start, -end
                list_to.extend(list_from[last:start + 1])
            else:
                list_to.extend(list_from[last:start])
            docs = e['docs'].get_raw_docs()
            list_docs = [l + os.linesep for l in docs.split(os.linesep)]
            list_to.extend(list_docs)
            last = end + 1
        if last < len(list_from):
            list_to.extend(list_from[last:])
        if source_path.startswith(os.sep):
            source_path = source_path[1:]
        if source_path and not source_path.endswith(os.sep):
            source_path += os.sep
        if target_path.startswith(os.sep):
            target_path = target_path[1:]
        if target_path and not target_path.endswith(os.sep):
            target_path += os.sep
        fromfile = 'a/' + source_path + os.path.basename(self.input_file)
        tofile = 'b/' + target_path + os.path.basename(self.input_file)
        diff_list = difflib.unified_diff(list_from, list_to, fromfile, tofile)
        return [d for d in diff_list]

    def diff_to_file(self, patch_file, source_path='', target_path=''):
        '''
        '''
        diff = self.diff(source_path, target_path)
        with open(patch_file, 'w') as f:
            f.write("# Patch generated by Pyment v%s\n\n" % (__version__))
            f.writelines(diff)

    def proceed(self):
        '''
        '''
        self._parse()
        for e in self.docs_list:
            e['docs'].generate_docs()
        return self.docs_list

########NEW FILE########
__FILENAME__ = origin_test
#!/usr/bin/python

import unittest

def my_func_full(first, second=None, third="value"):
    """This is a description of a method.
    It is on several lines.
    Several styles exists:
      -javadoc,
      -reST,
      -groups.
    It uses the javadoc style.

    @param first: the 1st argument.
    with multiple lines
    @type first: str
    @param second: the 2nd argument.
    @return: the result value
    @rtype: int
    @raise KeyError: raises an exception

    """
    print ("this is the code of my full func")

def my_func_multiline_elem(first,
                           second,
                           third=""):
    '''multiline'''
    print ("this has elems in several lines")

def my_func_empty_params(first, second=None, third="value"):
    print ("this is the code of my empty func")

def my_func_empty_no_params():
    print ("this is the code of my empty func no params")

def my_func_desc_lines_params(first, second=None, third="value"):
    '''This is a description but params not described.
    And a new line!
    '''
    print ("this is the code of my func")

def my_func_desc_line_params(first, second=None, third="value"):
    '''This is a description but params not described.
    '''
    print ("this is the code of my func")
 
def my_func_desc_line_no_params():
    '''This is a description but no params.
    '''
    print ("this is the code of my func")


def my_func_groups_style(first, second=None, third="value"):
    '''My desc of groups style.

    Parameters:
      first: the first param
      second: the 2nd param
      third: the 3rd param

    '''
    print("group style!")


class MyTestClass(object):

    def __init__(self, one_param=None):
        '''The init with one param

        @param one_param:
        '''
        self.param = one_param
        print("init")

    @classmethod
    def my_cls_method(cls):
        print("cls method")

    def my_method_no_param(self):
        """Do something
        perhaps!
        """
        print("or not")

    def my_method_params_no_docs(self, first, second=None, third="value"):
        print("method params no docs")

    def my_method_multiline_shift_elem(self, first,
                                             second,
                                             third="",
                                             **kwargs):
        '''there are multilines, shift and kwargs'''
        print ("this has elems in several lines")

    def my_method_full(self, first, second=None, third="value"):
        '''The desctiption of method with 3 params and return value
        on several lines

        @param first: the 1st param
        @type first: int
        @param second: the 2nd param with default at None
        @type first: tuple
        @param third: the 3rd param
        @type third: str
        @return: the value
        @rtype: str
        @raise KeyError: key exception

        '''
        print("method full")
        return third



########NEW FILE########
__FILENAME__ = test_docs
#!/usr/bin/python
# -*- coding: utf-8 -*-
import unittest
import pyment.docstring as docs

myelem = '    def my_method(self, first, second=None, third="value"):'
mydocs = '''        """This is a description of a method.
        It is on several lines.
        Several styles exists:
            -javadoc,
            -reST,
            -cstyle.
        It uses the javadoc style.

        @param first: the 1st argument.
        with multiple lines
        @type first: str
        @param second: the 2nd argument.
        @return: the result value
        @rtype: int
        @raise KeyError: raises a key error exception
        @raise OtherError: raises an other error exception

        """'''

mygrpdocs = '''
    """
    My desc of groups style.
    On two lines.

    Parameters:
      first: the 1st param
      second: the 2nd param
      third: the 3rd param

    Returns:
      a value in a string

    Raises:
      KeyError: when a key error
      OtherError: when an other error
    """'''

mygrpdocs2 = '''
    """
    My desc of an other kind 
    of groups style.

    Params:
      first -- the 1st param
      second -- the 2nd param
      third -- the 3rd param

    Returns:
      a value in a string

    Raises:
      KeyError -- when a key error
      OtherError -- when an other error
    """'''

mynumpydocs = '''
    """
    My numpydoc description of a kind 
    of very exhautive numpydoc format docstring.

    Parameters
    ----------
    first : array_like
        the 1st param name `first`
    second :
        the 2nd param
    third : {'value', 'other'}, optional
        the 3rd param, by default 'value'

    Returns
    -------
    string
        a value in a string

    Raises
    ------
    KeyError
        when a key error
    OtherError
        when an other error

    See Also
    --------
    a_func : linked (optional), with things to say
             on several lines
    some blabla

    Note
    ----
    Some informations.

    Some maths also:
    .. math:: f(x) = e^{- x}

    References
    ----------
    Biblio with cited ref [1]_. The ref can be cited in Note section.

    .. [1] Adel Daouzli, Sylvain Saïghi, Michelle Rudolph, Alain Destexhe, 
       Sylvie Renaud: Convergence in an Adaptive Neural Network: 
       The Influence of Noise Inputs Correlation. IWANN (1) 2009: 140-148

    Examples
    --------
    This is example of use
    >>> print "a"
    a

    """'''


def torest(docs):
    docs = docs.replace("@", ":")
    docs = docs.replace(":return", ":returns")
    docs = docs.replace(":raise", ":raises")
    return docs


class DocStringTests(unittest.TestCase):

    def testAutoInputStyleNumpydoc(self):
        doc = mynumpydocs
        d = docs.DocString(myelem, '    ', doc)
        self.failUnless(d.get_input_style() == 'numpydoc')

    def testAutoInputStyleJavadoc(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        self.failUnless(d.get_input_style() == 'javadoc')

    def testAutoInputStyleReST(self):
        doc = torest(mydocs)
        d = docs.DocString(myelem, '    ', doc)
        self.failUnless(d.get_input_style() == 'reST')

    def testAutoInputStyleGroups(self):
        doc = mygrpdocs
        d = docs.DocString(myelem, '    ', doc)
        self.failUnless(d.get_input_style() == 'groups')

    def testSameOutputJavadocReST(self):
        doc = mydocs
        dj = docs.DocString(myelem, '    ')
        dj.parse_docs(doc)
        doc = torest(mydocs)
        dr = docs.DocString(myelem, '    ')
        dr.parse_docs(doc)
        self.assertEqual(dj.get_raw_docs(), dr.get_raw_docs())

    def testParsingElement(self):
        d = docs.DocString(myelem, '    ')
        self.failUnless(d.element['type'] == 'def')
        self.failUnless(d.element['name'] == 'my_method')
        self.failUnless(len(d.element['params']) == 3)
        self.failUnless(type(d.element['params'][0]) is str)
        self.failUnless(d.element['params'][2] == ('third', '"value"'))

    def testIfParsedDocs(self):
        doc = mydocs
        # nothing to parse
        d = docs.DocString(myelem, '    ')
        d.parse_docs()
        self.failIf(d.parsed_docs)
        # parse docstring given at init
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(d.parsed_docs)
        # parse docstring given in parsing method
        d = docs.DocString(myelem, '    ')
        d.parse_docs(doc)
        self.failUnless(d.parsed_docs)

    def testParsingDocsDesc(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(d.docs['in']['desc'].strip().startswith('This '))
        self.failUnless(d.docs['in']['desc'].strip().endswith('style.'))

    def testParsingGroupsDocsDesc(self):
        doc = mygrpdocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(d.docs['in']['desc'].strip().startswith('My '))
        self.failUnless(d.docs['in']['desc'].strip().endswith('lines.'))
    
    def testParsingNumpyDocsDesc(self):
        doc = mynumpydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(d.docs['in']['desc'].strip().startswith('My numpydoc'))
        self.failUnless(d.docs['in']['desc'].strip().endswith('format docstring.'))
    
    def testParsingDocsParams(self):
        doc = torest(mydocs)
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(len(d.docs['in']['params']) == 2)
        self.failUnless(type(d.docs['in']['params'][1]) is tuple)
        # param's name
        self.failUnless(d.docs['in']['params'][1][0] == 'second')
        # param's type
        self.failUnless(d.docs['in']['params'][0][2] == 'str')
        self.failIf(d.docs['in']['params'][1][2])
        # param's description
        self.failUnless(d.docs['in']['params'][0][1].startswith("the 1"))

    def testParsingGroupsDocsParams(self):
        doc = mygrpdocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(len(d.docs['in']['params']) == 3)
        self.failUnless(d.docs['in']['params'][0][0] == 'first')
        self.failUnless(d.docs['in']['params'][0][1].startswith('the 1'))
        self.failUnless(d.docs['in']['params'][2][1].startswith('the 3rd'))

    def testParsingGroups2DocsParams(self):
        doc = mygrpdocs2
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(len(d.docs['in']['params']) == 3)
        self.failUnless(d.docs['in']['params'][0][0] == 'first')
        self.failUnless(d.docs['in']['params'][0][1].startswith('the 1'))
        self.failUnless(d.docs['in']['params'][2][1].startswith('the 3rd'))

    def testParsingNumpyDocsParams(self):
        doc = mynumpydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(len(d.docs['in']['params']) == 3)
        self.failUnless(d.docs['in']['params'][0][0] == 'first')
        self.failUnless(d.docs['in']['params'][0][1].strip().startswith('the 1'))
        self.failUnless(d.docs['in']['params'][2][1].strip().endswith("default 'value'"))

    def testParsingDocsRaises(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        d.generate_docs()
        self.failUnless(len(d.docs['in']['raises']) == 2)
        self.failUnless(d.docs['in']['raises'][0][0].startswith('KeyError'))
        self.failUnless(d.docs['in']['raises'][0][1].startswith('raises a key'))
        self.failUnless(d.docs['in']['raises'][1][0].startswith('OtherError'))
        self.failUnless(d.docs['in']['raises'][1][1].startswith('raises an other'))

    def testParsingGroupsDocsRaises(self):
        doc = mygrpdocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(len(d.docs['in']['raises']) == 2)
        self.failUnless(d.docs['in']['raises'][0][0] == 'KeyError')
        self.failUnless(d.docs['in']['raises'][0][1].startswith('when a key'))
        self.failUnless(d.docs['in']['raises'][1][0] == 'OtherError')
        self.failUnless(d.docs['in']['raises'][1][1].startswith('when an other'))

    def testParsingGroups2DocsRaises(self):
        doc = mygrpdocs2
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(len(d.docs['in']['raises']) == 2)
        self.failUnless(d.docs['in']['raises'][0][0] == 'KeyError')
        self.failUnless(d.docs['in']['raises'][0][1].startswith('when a key'))
        self.failUnless(d.docs['in']['raises'][1][0] == 'OtherError')
        self.failUnless(d.docs['in']['raises'][1][1].startswith('when an other'))

    def testParsingNumpyDocsRaises(self):
        doc = mynumpydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(len(d.docs['in']['raises']) == 2)
        self.failUnless(d.docs['in']['raises'][0][0] == 'KeyError')
        self.failUnless(d.docs['in']['raises'][0][1].strip().startswith('when a key'))
        self.failUnless(d.docs['in']['raises'][1][0] == 'OtherError')
        self.failUnless(d.docs['in']['raises'][1][1].strip().startswith('when an other'))

    def testParsingDocsReturn(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(d.docs['in']['return'].startswith('the result'))
        self.failUnless(d.docs['in']['rtype'] == 'int')

    def testParsingGroupsDocsReturn(self):
        doc = mygrpdocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(d.docs['in']['return'] == 'a value in a string')

    def testParsingNumpyDocsReturn(self):
        doc = mynumpydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        self.failUnless(d.docs['in']['return'][0][1] == 'a value in a string')
        d.set_output_style('numpydoc')

    def testGeneratingDocsDesc(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        d.generate_docs()
        self.failUnless(d.docs['out']['desc'] == d.docs['in']['desc'])

    def testGeneratingDocsReturn(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        d.generate_docs()
        self.failUnless(d.docs['out']['return'].startswith('the result'))
        self.failUnless(d.docs['out']['rtype'] == 'int')

    def testGeneratingDocsRaise(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        d.generate_docs()
        self.failUnless(len(d.docs['out']['raises']) == 2)
        self.failUnless(d.docs['out']['raises'][0][0].startswith('KeyError'))
        self.failUnless(d.docs['out']['raises'][0][1].startswith('raises a key'))
        self.failUnless(d.docs['out']['raises'][1][0].startswith('OtherError'))
        self.failUnless(d.docs['out']['raises'][1][1].startswith('raises an other'))

    def testGeneratingDocsParams(self):
        doc = mydocs
        d = docs.DocString(myelem, '    ', doc)
        d.parse_docs()
        d.generate_docs()
        self.failUnless(len(d.docs['out']['params']) == 3)
        self.failUnless(type(d.docs['out']['params'][2]) is tuple)
        self.failUnless(d.docs['out']['params'][2] == ('third', '', None, '"value"'))
        # param's description
        self.failUnless(d.docs['out']['params'][1][1].startswith("the 2"))

    def testNoParam(self):
        elem = "    def noparam():"
        doc = """        '''the no param docstring
        '''"""
        d = docs.DocString(elem, '    ', doc, input_style='javadoc')
        d.parse_docs()
        d.generate_docs()
        self.failIf(d.docs['out']['params'])

    def testOneLineDocs(self):
        elem = "    def oneline(self):"
        doc = """        '''the one line docstring
        '''"""
        d = docs.DocString(elem, '    ', doc, input_style='javadoc')
        d.parse_docs()
        d.generate_docs()
        #print(d.docs['out']['raw'])
        self.failIf(d.docs['out']['raw'].count('\n'))


def main():
    unittest.main()

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = test_pyment
#!/usr/bin/python

import unittest
import shutil
import os
import pyment.pyment as pym

myelem = '    def my_method(self, first, second=None, third="value"):'
mydocs = '''        """This is a description of a method.
        It is on several lines.
        Several styles exists:
            -javadoc,
            -reST,
            -cstyle.
        It uses the javadoc style.

        @param first: the 1st argument.
        with multiple lines
        @type first: str
        @param second: the 2nd argument.
        @return: the result value
        @rtype: int
        @raise KeyError: raises exception

        """'''

current_dir = os.path.dirname(__file__)
absdir = lambda f: os.path.join(current_dir, f)

inifile = absdir('origin_test.py')
jvdfile = absdir('javadoc_test.py')
rstfile = absdir('rest_test.py')


class DocStringTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # prepare test file
        txt = ""
        shutil.copyfile(inifile, jvdfile)
        with open(jvdfile, 'r') as fs:
            txt = fs.read()
        txt = txt.replace("@return", ":returns")
        txt = txt.replace("@raise", ":raises")
        txt = txt.replace("@", ":")
        with open(rstfile, 'w') as ft:
            ft.write(txt)
        print("setup")

    @classmethod
    def tearDownClass(cls):
        os.remove(jvdfile)
        os.remove(rstfile)
        print("end")

    def testParsedJavadoc(self):
        p = pym.PyComment(inifile)
        p._parse()
        self.failUnless(p.parsed)

    def testSameOutJavadocReST(self):
        pj = pym.PyComment(jvdfile)
        pr = pym.PyComment(rstfile)
        pj._parse()
        pr._parse()
        self.assertEqual(pj.get_output_docs(), pr.get_output_docs())

    def testMultiLinesElements(self):
        p = pym.PyComment(inifile)
        p._parse()
        self.failUnless('first' in p.get_output_docs()[1])
        self.failUnless('second' in p.get_output_docs()[1])
        self.failUnless('third' in p.get_output_docs()[1])
        self.failUnless('multiline' in p.get_output_docs()[1])

    def testMultiLinesShiftElements(self):
        p = pym.PyComment(inifile)
        p._parse()
        #TODO: improve this test
        self.assertEqual((len(p.get_output_docs()[13])-len(p.get_output_docs()[13].lstrip())), 8)
        self.failUnless('first' in p.get_output_docs()[13])
        self.failUnless('second' in p.get_output_docs()[13])
        self.failUnless('third' in p.get_output_docs()[13])
        self.failUnless('multiline' in p.get_output_docs()[13])

def main():
    unittest.main()

if __name__ == '__main__':
    main()

########NEW FILE########