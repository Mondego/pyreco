__FILENAME__ = auto-auto-complete
#!/usr/bin/env python3
# -*- coding: utf-8 -*-


###############################################################################################
## Shell auto-completion script generator https://www.github.com/maandree/auto-auto-complete ##
## Used by build system to make completions for all supported shells.                        ##
##                                                                                           ##
##    auto-auto-complete is experimental, therefore, before updating the version of this     ##
##    make sure that is still work for all shells.                                           ##
###############################################################################################


'''
auto-auto-complete – Autogenerate shell auto-completion scripts

Copyright © 2012  Mattias Andrée (maandree@kth.se)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
import sys


'''
Hack to enforce UTF-8 in output (in the future, if you see anypony not using utf-8 in
programs by default, report them to Princess Celestia so she can banish them to the moon)

@param  text:str  The text to print (empty string is default)
@param  end:str   The appendix to the text to print (line breaking is default)
'''
def print(text = '', end = '\n'):
    sys.stdout.buffer.write((str(text) + end).encode('utf-8'))

'''
stderr equivalent to print()

@param  text:str  The text to print (empty string is default)
@param  end:str   The appendix to the text to print (line breaking is default)
'''
def printerr(text = '', end = '\n'):
    sys.stderr.buffer.write((str(text) + end).encode('utf-8'))




'''
Bracket tree parser
'''
class Parser:
    '''
    Parse a code and return a tree
    
    @param   code:str      The code to parse
    @return  :list<↑|str>  The root node in the tree
    '''
    @staticmethod
    def parse(code):
        stack = []
        stackptr = -1
        
        comment = False
        escape = False
        quote = None
        buf = None
        
        for charindex in range(0, len(code)):
            c = code[charindex]
            if comment:
                if c in '\n\r\f':
                    comment = False
            elif escape:
                escape = False
                if   c == 'a':  buf += '\a'
                elif c == 'b':  buf += chr(8)
                elif c == 'e':  buf += '\033'
                elif c == 'f':  buf += '\f'
                elif c == 'n':  buf += '\n'
                elif c == 'r':  buf += '\r'
                elif c == 't':  buf += '\t'
                elif c == 'v':  buf += chr(11)
                elif c == '0':  buf += '\0'
                else:
                    buf += c
            elif c == quote:
                quote = None
            elif (c in ';#') and (quote is None):
                if buf is not None:
                    stack[stackptr].append(buf)
                    buf = None
                comment = True
            elif (c == '(') and (quote is None):
                if buf is not None:
                    stack[stackptr].append(buf)
                    buf = None
                stackptr += 1
                if stackptr == len(stack):
                    stack.append([])
                else:
                    stack[stackptr] = []
            elif (c == ')') and (quote is None):
                if buf is not None:
                    stack[stackptr].append(buf)
                    buf = None
                if stackptr == 0:
                    return stack[0]
                stackptr -= 1
                stack[stackptr].append(stack[stackptr + 1])
            elif (c in ' \t\n\r\f') and (quote is None):
                if buf is not None:
                    stack[stackptr].append(buf)
                    buf = None
            else:
                if buf is None:
                    buf = ''
                if c == '\\':
                    escape = True
                elif (c in '\'\"') and (quote is None):
                    quote = c
                else:
                    buf += c
        
        raise Exception('premature end of file')
    
    
    '''
    Simplifies a tree
    
    @param  tree:list<↑|str>  The tree
    '''
    @staticmethod
    def simplify(tree):
        program = tree[0]
        stack = [tree]
        while len(stack) > 0:
            node = stack.pop()
            new = []
            edited = False
            for item in node:
                if isinstance(item, list):
                    if item[0] == 'multiple':
                        master = item[1]
                        for slave in item[2:]:
                            new.append([master] + slave)
                        edited = True
                    elif item[0] == 'case':
                        for alt in item[1:]:
                            if alt[0] == program:
                                new.append(alt[1])
                                break
                        edited = True
                    else:
                        new.append(item)
                else:
                    new.append(item)
            if edited:
                node[:] = new
            for item in node:
                if isinstance(item, list):
                    stack.append(item)



'''
Completion script generator for GNU Bash
'''
class GeneratorBASH:
    '''
    Constructor
    
    @param  program:str                              The command to generate completion for
    @param  unargumented:list<dict<str, list<str>>>  Specification of unargumented options
    @param  argumented:list<dict<str, list<str>>>    Specification of argumented options
    @param  variadic:list<dict<str, list<str>>>      Specification of variadic options
    @param  suggestion:list<list<↑|str>>             Specification of argument suggestions
    @param  default:dict<str, list<str>>?            Specification for optionless arguments
    '''
    def __init__(self, program, unargumented, argumented, variadic, suggestion, default):
        self.program      = program
        self.unargumented = unargumented
        self.argumented   = argumented
        self.variadic     = variadic
        self.suggestion   = suggestion
        self.default      = default
    
    
    '''
    Gets the argument suggesters for each option
    
    @return  :dist<str, str>  Map from option to suggester
    '''
    def __getSuggesters(self):
        suggesters = {}
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if 'suggest' in item:
                    suggester = item['suggest']
                    for option in item['options']:
                        suggesters[option] = suggester[0]
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if ('suggest' not in item) and ('bind' in item):
                    bind = item['bind'][0]
                    if bind in suggesters:
                        suggester = suggesters[bind]
                        for option in item['options']:
                            suggesters[option] = suggester
        
        return suggesters
    
    
    '''
    Returns the generated code
    
    @return  :str  The generated code
    '''
    def get(self):
        buf = '# bash completion for %s         -*- shell-script -*-\n\n' % self.program
        buf += '_%s()\n{\n' % self.program
        buf += '    local cur prev words cword\n'
        buf += '    _init_completion -n = || return\n\n'
        
        def verb(text):
            temp = text
            for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-+=/@:\'':
                temp = temp.replace(char, '')
            if len(temp) == 0:
                return text
            return '\'' + text.replace('\'', '\'\\\'\'') + '\''
        
        def makeexec(functionType, function):
            if functionType in ('exec', 'pipe', 'fullpipe', 'cat', 'and', 'or'):
                elems = [(' %s ' % makeexec(item[0], item[1:]) if isinstance(item, list) else verb(item)) for item in function]
                if functionType == 'exec':
                    return ' $( %s ) ' % (' '.join(elems))
                if functionType == 'pipe':
                    return ' ( %s ) ' % (' | '.join(elems))
                if functionType == 'fullpipe':
                    return ' ( %s ) ' % (' |% '.join(elems))
                if functionType == 'cat':
                    return ' ( %s ) ' % (' ; '.join(elems))
                if functionType == 'and':
                    return ' ( %s ) ' % (' && '.join(elems))
                if functionType == 'or':
                    return ' ( %s ) ' % (' || '.join(elems))
            if functionType in ('params', 'verbatim'):
                return ' '.join([verb(item) for item in function])
            return ' '.join([verb(functionType)] + [verb(item) for item in function])
        
        def makesuggestion(suggester):
            suggestion = '';
            for function in suggester:
                functionType = function[0]
                function = function[1:]
                if functionType == 'verbatim':
                    suggestion += ' %s' % (' '.join([verb(item) for item in function]))
                elif functionType == 'ls':
                    filter = ''
                    if len(function) > 1:
                        filter = ' | grep -v \\/%s\\$ | grep %s\\$' % (function[1], function[1])
                    suggestion += ' $(ls -1 --color=no %s%s)' % (function[0], filter)
                elif functionType in ('exec', 'pipe', 'fullpipe', 'cat', 'and', 'or'):
                    suggestion += (' %s' if functionType == 'exec' else ' $(%s)') % makeexec(functionType, function)
                elif functionType == 'calc':
                    expression = []
                    for item in function:
                        if isinstance(item, list):
                            expression.append(('%s' if item[0] == 'exec' else '$(%s)') % makeexec(item[0], item[1:]))
                        else:
                            expression.append(verb(item))
                    suggestion += ' $(( %s ))' % (' '.join(expression))
            return '"' + suggestion + '"'
        
        suggesters = self.__getSuggesters()
        suggestFunctions = {}
        for function in self.suggestion:
            suggestFunctions[function[0]] = function[1:]
        
        options = []
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if 'complete' in item:
                    options += item['complete']
        buf += '    options="%s "' % (' '.join(options))
        if self.default is not None:
            defSuggest = self.default['suggest'][0]
            if defSuggest is not None:
                buf += '%s' % makesuggestion(suggestFunctions[defSuggest])
        buf += '\n'
        buf += '    COMPREPLY=( $( compgen -W "$options" -- "$cur" ) )\n\n'
        
        indenticals = {}
        for option in suggesters:
            suggester = suggestFunctions[suggesters[option]]
            _suggester = str(suggester)
            if _suggester not in indenticals:
                indenticals[_suggester] = (suggester, [option])
            else:
                indenticals[_suggester][1].append(option)
        
        index = 0
        for _suggester in indenticals:
            (suggester, options) = indenticals[_suggester]
            conds = []
            for option in options:
                conds.append('[ $prev = "%s" ]' % option)
            buf += '    %s %s; then\n' % ('if' if index == 0 else 'elif', ' || '.join(conds))
            suggestion = makesuggestion(suggester);
            if len(suggestion) > 0:
                buf += '        suggestions=%s\n' % suggestion
                buf += '        COMPREPLY=( $( compgen -W "$suggestions" -- "$cur" ) )\n'
            index += 1
        
        if index > 0:
            buf += '    fi\n'
        
        buf += '}\n\ncomplete -o default -F _%s %s\n\n' % (self.program, self.program)
        return buf



'''
Completion script generator for fish
'''
class GeneratorFISH:
    '''
    Constructor
    
    @param  program:str                              The command to generate completion for
    @param  unargumented:list<dict<str, list<str>>>  Specification of unargumented options
    @param  argumented:list<dict<str, list<str>>>    Specification of argumented options
    @param  variadic:list<dict<str, list<str>>>      Specification of variadic options
    @param  suggestion:list<list<↑|str>>             Specification of argument suggestions
    @param  default:dict<str, list<str>>?            Specification for optionless arguments
    '''
    def __init__(self, program, unargumented, argumented, variadic, suggestion, default):
        self.program      = program
        self.unargumented = unargumented
        self.argumented   = argumented
        self.variadic     = variadic
        self.suggestion   = suggestion
        self.default      = default
    
    
    '''
    Gets the argument suggesters for each option
    
    @return  :dist<str, str>  Map from option to suggester
    '''
    def __getSuggesters(self):
        suggesters = {}
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if 'suggest' in item:
                    suggester = item['suggest']
                    for option in item['options']:
                        suggesters[option] = suggester[0]
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if ('suggest' not in item) and ('bind' in item):
                    bind = item['bind'][0]
                    if bind in suggesters:
                        suggester = suggesters[bind]
                        for option in item['options']:
                            suggesters[option] = suggester
        
        return suggesters
    
    
    '''
    Gets the file pattern for each option
    
    @return  :dist<str, list<str>>  Map from option to file pattern
    '''
    def __getFiles(self):
        files = {}
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if 'files' in item:
                    _files = item['files']
                    for option in item['options']:
                        files[option] = _files
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if ('files' not in item) and ('bind' in item):
                    bind = item['bind'][0]
                    if bind in files:
                        _files = files[bind]
                        for option in item['options']:
                            files[option] = _files
        
        return files
    
    
    '''
    Returns the generated code
    
    @return  :str  The generated code
    '''
    def get(self):
        buf = '# fish completion for %s         -*- shell-script -*-\n\n' % self.program
        
        files = self.__getFiles()
        
        suggesters = self.__getSuggesters()
        suggestFunctions = {}
        for function in self.suggestion:
            suggestFunctions[function[0]] = function[1:]
        
        def verb(text):
            temp = text
            for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-+=/@:\'':
                temp = temp.replace(char, '')
            if len(temp) == 0:
                return text
            return '\'' + text.replace('\'', '\'\\\'\'') + '\''
        
        def makeexec(functionType, function):
            if functionType in ('exec', 'pipe', 'fullpipe', 'cat', 'and', 'or'):
                elems = [(' %s ' % makeexec(item[0], item[1:]) if isinstance(item, list) else verb(item)) for item in function]
                if functionType == 'exec':
                    return ' ( %s ) ' % (' '.join(elems))
                if functionType == 'pipe':
                    return ' ( %s ) ' % (' | '.join(elems))
                if functionType == 'fullpipe':
                    return ' ( %s ) ' % (' |% '.join(elems))
                if functionType == 'cat':
                    return ' ( %s ) ' % (' ; '.join(elems))
                if functionType == 'and':
                    return ' ( %s ) ' % (' && '.join(elems))
                if functionType == 'or':
                    return ' ( %s ) ' % (' || '.join(elems))
            if functionType in ('params', 'verbatim'):
                return ' '.join([verb(item) for item in function])
            return ' '.join([verb(functionType)] + [verb(item) for item in function])
        
        index = 0
        for name in suggestFunctions:
            suggestion = '';
            for function in suggestFunctions[name]:
                functionType = function[0]
                function = function[1:]
                if functionType == 'verbatim':
                    suggestion += ' %s' % (' '.join([verb(item) for item in function]))
                elif functionType == 'ls':
                    filter = ''
                    if len(function) > 1:
                        filter = ' | grep -v \\/%s\\$ | grep %s\\$' % (function[1], function[1])
                    suggestion += ' (ls -1 --color=no %s%s)' % (function[0], filter)
                elif functionType in ('exec', 'pipe', 'fullpipe', 'cat', 'and', 'or'):
                    suggestion += (' %s' if functionType == 'exec' else ' $(%s)') % makeexec(functionType, function)
                #elif functionType == 'calc':
                #    expression = []
                #    for item in function:
                #        if isinstance(item, list):
                #            expression.append(('%s' if item[0] == 'exec' else '$(%s)') % makeexec(item[0], item[1:]))
                #        else:
                #            expression.append(verb(item))
                #    suggestion += ' $(( %s ))' % (' '.join(expression))
            if len(suggestion) > 0:
                suggestFunctions[name] = '"' + suggestion + '"'
        
        if self.default is not None:
            item = self.default
            buf += 'complete --command %s' % self.program
            if 'desc' in self.default:
                buf += ' --description %s' % verb(' '.join(item['desc']))
            defFiles = self.default['files']
            defSuggest = self.default['suggest'][0]
            if defFiles is not None:
                if (len(defFiles) == 1) and ('-0' in defFiles):
                    buf += ' --no-files'
            if defSuggest is not None:
                buf += ' --arguments %s' % suggestFunctions[defSuggest]
            buf += '\n'
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                options = item['options']
                shortopt = []
                longopt = []
                for opt in options:
                    if opt.startswith('--'):
                        if ('complete' in item) and (opt in item['complete']):
                            longopt.append(opt)
                    elif opt.startswith('-') and (len(opt) == 2):
                        shortopt.append(opt)
                options = shortopt + longopt
                if len(longopt) == 0:
                    continue
                buf += 'complete --command %s' % self.program
                if 'desc' in item:
                    buf += ' --description %s' % verb(' '.join(item['desc']))
                if options[0] in files:
                    if (len(files[options[0]]) == 1) and ('-0' in files[options[0]][0]):
                        buf += ' --no-files'
                if options[0] in suggesters:
                    buf += ' --arguments %s' % suggestFunctions[suggesters[options[0]]]
                if len(shortopt) > 0: buf += ' --short-option %s' % shortopt[0][1:]
                if len( longopt) > 0: buf +=  ' --long-option %s' %  longopt[0][2:]
                buf += '\n'
        
        return buf



'''
Completion script generator for zsh
'''
class GeneratorZSH:
    '''
    Constructor
    
    @param  program:str                              The command to generate completion for
    @param  unargumented:list<dict<str, list<str>>>  Specification of unargumented options
    @param  argumented:list<dict<str, list<str>>>    Specification of argumented options
    @param  variadic:list<dict<str, list<str>>>      Specification of variadic options
    @param  suggestion:list<list<↑|str>>             Specification of argument suggestions
    @param  default:dict<str, list<str>>?            Specification for optionless arguments
    '''
    def __init__(self, program, unargumented, argumented, variadic, suggestion, default):
        self.program      = program
        self.unargumented = unargumented
        self.argumented   = argumented
        self.variadic     = variadic
        self.suggestion   = suggestion
        self.default      = default
    
    
    '''
    Gets the argument suggesters for each option
    
    @return  :dist<str, str>  Map from option to suggester
    '''
    def __getSuggesters(self):
        suggesters = {}
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if 'suggest' in item:
                    suggester = item['suggest']
                    for option in item['options']:
                        suggesters[option] = suggester[0]
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if ('suggest' not in item) and ('bind' in item):
                    bind = item['bind'][0]
                    if bind in suggesters:
                        suggester = suggesters[bind]
                        for option in item['options']:
                            suggesters[option] = suggester
        
        return suggesters
    
    
    '''
    Gets the file pattern for each option
    
    @return  :dist<str, list<str>>  Map from option to file pattern
    '''
    def __getFiles(self):
        files = {}
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if 'files' in item:
                    _files = item['files']
                    for option in item['options']:
                        files[option] = _files
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                if ('files' not in item) and ('bind' in item):
                    bind = item['bind'][0]
                    if bind in files:
                        _files = files[bind]
                        for option in item['options']:
                            files[option] = _files
        
        return files
    
    
    '''
    Returns the generated code
    
    @return  :str  The generated code
    '''
    def get(self):
        buf = '# zsh completion for %s         -*- shell-script -*-\n\n' % self.program
        
        files = self.__getFiles()
        
        suggesters = self.__getSuggesters()
        suggestFunctions = {}
        for function in self.suggestion:
            suggestFunctions[function[0]] = function[1:]
        
        def verb(text):
            temp = text
            for char in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-+=/@:\'':
                temp = temp.replace(char, '')
            if len(temp) == 0:
                return text
            return '\'' + text.replace('\'', '\'\\\'\'') + '\''
        
        def makeexec(functionType, function):
            if functionType in ('exec', 'pipe', 'fullpipe', 'cat', 'and', 'or'):
                elems = [(' %s ' % makeexec(item[0], item[1:]) if isinstance(item, list) else verb(item)) for item in function]
                if functionType == 'exec':
                    return ' $( %s ) ' % (' '.join(elems))
                if functionType == 'pipe':
                    return ' ( %s ) ' % (' | '.join(elems))
                if functionType == 'fullpipe':
                    return ' ( %s ) ' % (' |% '.join(elems))
                if functionType == 'cat':
                    return ' ( %s ) ' % (' ; '.join(elems))
                if functionType == 'and':
                    return ' ( %s ) ' % (' && '.join(elems))
                if functionType == 'or':
                    return ' ( %s ) ' % (' || '.join(elems))
            if functionType in ('params', 'verbatim'):
                return ' '.join([verb(item) for item in function])
            return ' '.join([verb(functionType)] + [verb(item) for item in function])
        
        index = 0
        for name in suggestFunctions:
            suggestion = '';
            for function in suggestFunctions[name]:
                functionType = function[0]
                function = function[1:]
                if functionType == 'verbatim':
                    suggestion += ' %s ' % (' '.join([verb(item) for item in function]))
                elif functionType == 'ls':
                    filter = ''
                    if len(function) > 1:
                        filter = ' | grep -v \\/%s\\$ | grep %s\\$' % (function[1], function[1])
                    suggestion += ' $(ls -1 --color=no %s%s) ' % (function[0], filter)
                elif functionType in ('exec', 'pipe', 'fullpipe', 'cat', 'and', 'or'):
                    suggestion += ('%s' if functionType == 'exec' else '$(%s)') % makeexec(functionType, function)
                elif functionType == 'calc':
                    expression = []
                    for item in function:
                        if isinstance(item, list):
                            expression.append(('%s' if item[0] == 'exec' else '$(%s)') % makeexec(item[0], item[1:]))
                        else:
                            expression.append(verb(item))
                    suggestion += ' $(( %s )) ' % (' '.join(expression))
            if len(suggestion) > 0:
                suggestFunctions[name] = suggestion
        
        buf += '_opts=(\n'
        
        for group in (self.unargumented, self.argumented, self.variadic):
            for item in group:
                options = item['options']
                shortopt = []
                longopt = []
                for opt in options:
                    if len(opt) > 2:
                        if ('complete' in item) and (opt in item['complete']):
                            longopt.append(opt)
                    elif len(opt) == 2:
                        shortopt.append(opt)
                options = shortopt + longopt
                if len(longopt) == 0:
                    continue
                buf += '    \'(%s)\'{%s}' % (' '.join(options), ','.join(options))
                if 'desc' in item:
                    buf += '"["%s"]"' % verb(' '.join(item['desc']))
                if 'arg' in item:
                    buf += '":%s"' % verb(' '.join(item['arg']))
                elif options[0] in suggesters:
                    buf += '": "'
                if options[0] in suggesters:
                    suggestion = suggestFunctions[suggesters[options[0]]]
                    buf += '":( %s )"' % suggestion
                buf += '\n'
        
        buf += '    )\n\n_arguments "$_opts[@]"\n\n'
        return buf



'''
mane!

@param  shell:str   Shell to generato completion for
@param  output:str  Output file
@param  source:str  Source file
'''
def main(shell, output, source):
    with open(source, 'rb') as file:
        source = file.read().decode('utf8', 'replace')
    source = Parser.parse(source)
    Parser.simplify(source)
    
    program = source[0]
    unargumented = []
    argumented = []
    variadic = []
    suggestion = []
    default = None
    
    for item in source[1:]:
        if item[0] == 'unargumented':
            unargumented.append(item[1:]);
        elif item[0] == 'argumented':
            argumented.append(item[1:]);
        elif item[0] == 'variadic':
            variadic.append(item[1:]);
        elif item[0] == 'suggestion':
            suggestion.append(item[1:]);
        elif item[0] == 'default':
            default = item[1:];
    
    for group in (unargumented, argumented, variadic):
        for index in range(0, len(group)):
            item = group[index]
            map = {}
            for elem in item:
                map[elem[0]] = elem[1:]
            group[index] = map
    if default is not None:
        map = {}
        for elem in default:
            map[elem[0]] = elem[1:]
        default = map
    
    generator = 'Generator' + shell.upper()
    generator = globals()[generator]
    generator = generator(program, unargumented, argumented, variadic, suggestion, default)
    code = generator.get()
    
    with open(output, 'wb') as file:
        file.write(code.encode('utf-8'))



'''
mane!
'''
if __name__ == '__main__':
    if len(sys.argv) != 6:
        print("USAGE: auto-auto-complete SHELL --output OUTPUT_FILE --source SOURCE_FILE")
        exit(1)
    
    shell = sys.argv[1]
    output = None
    source = None
    
    option = None
    aliases = {'-o' : '--output',
               '-f' : '--source', '--file' : '--source',
               '-s' : '--source'}
    
    def useopt(option, arg):
        global source
        global output
        old = None
        if   option == '--output': old = output; output = arg
        elif option == '--source': old = source; source = arg
        else:
            raise Exception('Unrecognised option: ' + option)
        if old is not None:
            raise Exception('Duplicate option: ' + option)
    
    for arg in sys.argv[2:]:
        if option is not None:
            if option in aliases:
                option = aliases[option]
            useopt(option, arg)
            option = None
        else:
            if '=' in arg:
                useopt(arg[:index('=')], arg[index('=') + 1:])
            else:
                option = arg
    
    if output is None: raise Exception('Unused option: --output')
    if source is None: raise Exception('Unused option: --source')
    
    main(shell= shell, output= output, source= source)


########NEW FILE########
__FILENAME__ = catise
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Pipe the content of a pony file to this script to make the printed
# information easier to read. This is intended for inspection pony
# files in greater detail than using it in ponysay.


comment = False
while True:
    line = None
    try:
        line = input()
    except:
        pass
    if line is None:
        break
    if line == '$$$':
        comment = not comment
        continue
    if comment:
        continue
    line = line.replace('$\\$', '\\').replace('$/$', '/').replace('$X$', 'X');
    if line.startswith('$balloon'):
        line = line[len('$balloon'):]
        balloon = line[:line.find('$')]
        line = line[len(balloon) + 1:]
        for alpha in 'qwertyuiopasdfghjklzxcvbnm':
            balloon = balloon.replace(alpha, ',')
        balloon = balloon.split(',')[0]
        if len(balloon) == 0:
            line = '\033[01;33;41m%s\033[00m' % (50 * '/') + line
        else:
            line = '\033[42m%s\033[00m' % (int(balloon) * ' ') + line
    print(line)



########NEW FILE########
__FILENAME__ = argparser
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *



ARGUMENTLESS = 0
'''
Option takes no arguments
'''

ARGUMENTED = 1
'''
Option takes one argument per instance
'''

VARIADIC = 2
'''
Option consumes all following arguments
'''



class ArgParser():
    '''
    Simple argument parser
    '''
    
    def __init__(self, program, description, usage, longdescription = None):
        '''
        Constructor.
        The short description is printed on same line as the program name
        
        @param  program:str          The name of the program
        @param  description:str      Short, single-line, description of the program
        @param  usage:str            Formated, multi-line, usage text
        @param  longdescription:str  Long, multi-line, description of the program, may be `None`
        '''
        self.linuxvt = ('TERM' in os.environ) and (os.environ['TERM'] == 'linux')
        self.__program = program
        self.__description = description
        self.__usage = usage
        self.__longdescription = longdescription
        self.__arguments = []
        self.opts = {}
        self.optmap = {}
    
    
    def add_argumentless(self, alternatives, help = None):
        '''
        Add option that takes no arguments
        
        @param  alternatives:list<str>  Option names
        @param  help:str                Short description, use `None` to hide the option
        '''
        self.__arguments.append((ARGUMENTLESS, alternatives, None, help))
        stdalt = alternatives[0]
        self.opts[stdalt] = None
        for alt in alternatives:
            self.optmap[alt] = (stdalt, ARGUMENTLESS)
    
    def add_argumented(self, alternatives, arg, help = None):
        '''
        Add option that takes one argument
        
        @param  alternatives:list<str>  Option names
        @param  arg:str                 The name of the takes argument, one word
        @param  help:str                Short description, use `None` to hide the option
        '''
        self.__arguments.append((ARGUMENTED, alternatives, arg, help))
        stdalt = alternatives[0]
        self.opts[stdalt] = None
        for alt in alternatives:
            self.optmap[alt] = (stdalt, ARGUMENTED)
    
    def add_variadic(self, alternatives, arg, help = None):
        '''
        Add option that takes all following argument
        
        @param  alternatives:list<str>  Option names
        @param  arg:str                 The name of the takes arguments, one word
        @param  help:str                Short description, use `None` to hide the option
        '''
        self.__arguments.append((VARIADIC, alternatives, arg, help))
        stdalt = alternatives[0]
        self.opts[stdalt] = None
        for alt in alternatives:
            self.optmap[alt] = (stdalt, VARIADIC)
    
    
    def parse(self, argv = sys.argv):
        '''
        Parse arguments
        
        @param   args:list<str>  The command line arguments, should include the execute file at index 0, `sys.argv` is default
        @return  :bool           Whether no unrecognised option is used
        '''
        self.argcount = len(argv) - 1
        self.files = []
        
        argqueue = []
        optqueue = []
        deque = []
        for arg in argv[1:]:
            deque.append(arg)
        
        dashed = False
        tmpdashed = False
        get = 0
        dontget = 0
        self.rc = True
        
        self.unrecognisedCount = 0
        def unrecognised(arg):
            self.unrecognisedCount += 1
            if self.unrecognisedCount <= 5:
                sys.stderr.write('%s: warning: unrecognised option %s\n' % (self.__program, arg))
            self.rc = False
        
        while len(deque) != 0:
            arg = deque[0]
            deque = deque[1:]
            if (get > 0) and (dontget == 0):
                get -= 1
                argqueue.append(arg)
            elif tmpdashed:
                self.files.append(arg)
                tmpdashed = False
            elif dashed:        self.files.append(arg)
            elif arg == '++':   tmpdashed = True
            elif arg == '--':   dashed = True
            elif (len(arg) > 1) and (arg[0] in ('-', '+')):
                if (len(arg) > 2) and (arg[:2] in ('--', '++')):
                    if dontget > 0:
                        dontget -= 1
                    elif (arg in self.optmap) and (self.optmap[arg][1] == ARGUMENTLESS):
                        optqueue.append(arg)
                        argqueue.append(None)
                    elif '=' in arg:
                        arg_opt = arg[:arg.index('=')]
                        if (arg_opt in self.optmap) and (self.optmap[arg_opt][1] >= ARGUMENTED):
                            optqueue.append(arg_opt)
                            argqueue.append(arg[arg.index('=') + 1:])
                            if self.optmap[arg_opt][1] == VARIADIC:
                                dashed = True
                        else:
                            unrecognised(arg)
                    elif (arg in self.optmap) and (self.optmap[arg][1] == ARGUMENTED):
                        optqueue.append(arg)
                        get += 1
                    elif (arg in self.optmap) and (self.optmap[arg][1] == VARIADIC):
                        optqueue.append(arg)
                        argqueue.append(None)
                        dashed = True
                    else:
                        unrecognised(arg)
                else:
                    sign = arg[0]
                    i = 1
                    n = len(arg)
                    while i < n:
                        narg = sign + arg[i]
                        i += 1
                        if (narg in self.optmap):
                            if self.optmap[narg][1] == ARGUMENTLESS:
                                optqueue.append(narg)
                                argqueue.append(None)
                            elif self.optmap[narg][1] == ARGUMENTED:
                                optqueue.append(narg)
                                nargarg = arg[i:]
                                if len(nargarg) == 0:
                                    get += 1
                                else:
                                    argqueue.append(nargarg)
                                break
                            elif self.optmap[narg][1] == VARIADIC:
                                optqueue.append(narg)
                                nargarg = arg[i:]
                                argqueue.append(nargarg if len(nargarg) > 0 else None)
                                dashed = True
                                break
                        else:
                            unrecognised(narg)
            else:
                self.files.append(arg)
        
        i = 0
        n = len(optqueue)
        while i < n:
            opt = optqueue[i]
            arg = argqueue[i] if len(argqueue) > i else None
            i += 1
            opt = self.optmap[opt][0]
            if (opt not in self.opts) or (self.opts[opt] is None):
                self.opts[opt] = []
            if len(argqueue) >= i:
                self.opts[opt].append(arg)
        
        for arg in self.__arguments:
            if arg[0] == VARIADIC:
                varopt = self.opts[arg[1][0]]
                if varopt is not None:
                    additional = ','.join(self.files).split(',') if len(self.files) > 0 else []
                    if varopt[0] is None:
                        self.opts[arg[1][0]] = additional
                    else:
                        self.opts[arg[1][0]] = varopt[0].split(',') + additional
                    self.files = []
                    break
        
        self.message = ' '.join(self.files) if len(self.files) > 0 else None
        
        if self.unrecognisedCount > 5:
            sys.stderr.write('%s: warning: %i more unrecognised %s\n' % (self.unrecognisedCount - 5, 'options' if self.unrecognisedCount == 6 else 'options'))
        
        return self.rc
    
    
    def help(self, use_colours = None):
        '''
        Prints a colourful help message
        
        @param  use_colours:bool?  Whether to use colours, `None` if stdout is not piped
        '''
        if use_colours is None:
            use_colours = sys.stdout.isatty()
        
        print(('\033[1m%s\033[21m %s %s' if use_colours else '%s %s %s') % (self.__program, '-' if self.linuxvt else '—', self.__description))
        print()
        if self.__longdescription is not None:
            desc = self.__longdescription
            if not use_colours:
                while '\033' in desc:
                    esc = desc.find('\033')
                    desc = desc[:esc] + desc[desc.find('m', esc) + 1:]
            print(desc)
        print()
        
        print('\033[1mUSAGE:\033[21m' if use_colours else 'USAGE:', end='')
        first = True
        for line in self.__usage.split('\n'):
            if first:
                first = False
            else:
                print('    or', end='')
            if not use_colours:
                while '\033' in line:
                    esc = line.find('\033')
                    line = line[:esc] + line[line.find('m', esc) + 1:]
            print('\t%s' % line)
        print()
        
        maxfirstlen = []
        for opt in self.__arguments:
            opt_alts = opt[1]
            opt_help = opt[3]
            if opt_help is None:
                continue
            first = opt_alts[0]
            last = opt_alts[-1]
            if first is not last:
                maxfirstlen.append(first)
        maxfirstlen = len(max(maxfirstlen, key = len))
        
        print('\033[1mSYNOPSIS:\033[21m' if use_colours else 'SYNOPSIS')
        (lines, lens) = ([], [])
        for opt in self.__arguments:
            opt_type = opt[0]
            opt_alts = opt[1]
            opt_arg = opt[2]
            opt_help = opt[3]
            if opt_help is None:
                continue
            (line, l) = ('', 0)
            first = opt_alts[0]
            last = opt_alts[-1]
            alts = ['', last] if first is last else [first, last]
            alts[0] += ' ' * (maxfirstlen - len(alts[0]))
            for opt_alt in alts:
                if opt_alt is alts[-1]:
                    line += '%colour%' + opt_alt
                    l += len(opt_alt)
                    if use_colours:
                        if   opt_type == ARGUMENTED:  line += ' \033[4m%s\033[24m'      % (opt_arg);  l += len(opt_arg) + 1
                        elif opt_type == VARIADIC:    line += ' [\033[4m%s\033[24m...]' % (opt_arg);  l += len(opt_arg) + 6
                    else:
                        if   opt_type == ARGUMENTED:  line += ' %s'      % (opt_arg);  l += len(opt_arg) + 1
                        elif opt_type == VARIADIC:    line += ' [%s...]' % (opt_arg);  l += len(opt_arg) + 6
                else:
                    if use_colours:
                        line += '    \033[2m%s\033[22m  ' % (opt_alt)
                    else:
                        line += '    %s  ' % (opt_alt)
                    l += len(opt_alt) + 6
            lines.append(line)
            lens.append(l)
        
        col = max(lens)
        col += 8 - ((col - 4) & 7)
        index = 0
        for opt in self.__arguments:
            opt_help = opt[3]
            if opt_help is None:
                continue
            first = True
            colour = ('36' if (index & 1) == 0 else '34') if use_colours else ''
            print(lines[index].replace('%colour%', ('\033[%s;1m' % colour) if use_colours else ''), end=' ' * (col - lens[index]))
            for line in opt_help.split('\n'):
                if first:
                    first = False
                    print('%s' % (line), end='\033[21;39m\n' if use_colours else '\n')
                else:
                    print(('%s\033[%sm%s\033[39m' if use_colours else '%s%s%s') % (' ' * col, colour, line))
            index += 1
        
        print()


########NEW FILE########
__FILENAME__ = backend
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *
from balloon import *
from colourstack import *
from ucs import *



class Backend():
    '''
    Super-ultra-extreme-awesomazing replacement for cowsay
    '''
    
    def __init__(self, message, ponyfile, wrapcolumn, width, balloon, hyphen, linkcolour, ballooncolour, mode, infolevel):
        '''
        Constructor
        
        @param  message:str        The message spoken by the pony
        @param  ponyfile:str       The pony file
        @param  wrapcolumn:int     The column at where to wrap the message, `None` for no wrapping
        @param  width:int          The width of the screen, `None` if truncation should not be applied
        @param  balloon:Balloon    The balloon style object, `None` if only the pony should be printed
        @param  hyphen:str         How hyphens added by the wordwrapper should be printed
        @param  linkcolour:str     How to colour the link character, empty string if none
        @param  ballooncolour:str  How to colour the balloon, empty string if none
        @param  mode:str           Mode string for the pony
        @parma  infolevel:int      2 if ++info is used, 1 if --info is used and 0 otherwise
        '''
        self.message = message
        self.ponyfile = ponyfile
        self.wrapcolumn = None if wrapcolumn is None else wrapcolumn - (0 if balloon is None else balloon.minwidth)
        self.width = width
        self.balloon = balloon
        self.hyphen = hyphen
        self.ballooncolour = ballooncolour
        self.mode = mode
        self.balloontop = 0
        self.balloonbottom = 0
        self.infolevel = infolevel
        
        if self.balloon is not None:
            self.link = {'\\' : linkcolour + self.balloon.link,
                         '/'  : linkcolour + self.balloon.linkmirror,
                         'X'  : linkcolour + self.balloon.linkcross}
        else:
            self.link = {}
        
        self.output = ''
        self.pony = None
    
    
    def parse(self):
        '''
        Process all data
        '''
        self.__loadFile()
        
        if self.pony.startswith('$$$\n'):
            self.pony = self.pony[4:]
            if self.pony.startswith('$$$\n'):
                infoend = 4
                info = ''
            else:
                infoend = self.pony.index('\n$$$\n')
                info = self.pony[:infoend]
                infoend += 5
            if self.infolevel == 2:
                self.message = Backend.formatInfo(info)
                self.pony = self.pony[infoend:]
            elif self.infolevel == 1:
                self.pony = Backend.formatInfo(info).replace('$', '$$')
            else:
                info = info.split('\n')
                for line in info:
                    sep = line.find(':')
                    if sep > 0:
                        key = line[:sep].strip()
                        if key == 'BALLOON TOP':
                            value = line[sep + 1:].strip()
                            if len(value) > 0:
                                self.balloontop = int(value)
                        if key == 'BALLOON BOTTOM':
                            value = line[sep + 1:].strip()
                            if len(value) > 0:
                                self.balloonbottom = int(value)
                printinfo(info)
                self.pony = self.pony[infoend:]
        elif self.infolevel == 2:
            self.message = '\033[01;31mI am the mysterious mare...\033[21;39m'
        elif self.infolevel == 1:
            self.pony = 'There is not metadata for this pony file'
        self.pony = self.mode + self.pony
        
        self.__expandMessage()
        self.__unpadMessage()
        self.__processPony()
        self.__truncate()
    
    
    @staticmethod
    def formatInfo(info):
        '''
        Format metadata to be nicely printed, this include bold keys
        
        @param   info:str  The metadata
        @return  :str      The metadata nicely formated
        '''
        info = info.split('\n')
        tags = ''
        comment = ''
        for line in info:
            sep = line.find(':')
            if sep > 0:
                key = line[:sep]
                test = key
                for c in 'ABCDEFGHIJKLMN OPQRSTUVWXYZ':
                    test = test.replace(c, '')
                if (len(test) == 0) and (len(key.replace(' ', '')) > 0):
                    value = line[sep + 1:].strip()
                    line = '\033[1m%s\033[21m: %s\n' % (key.strip(), value)
                    tags += line
                    continue
            comment += '\n' + line
        comment = comment.lstrip('\n')
        if len(comment) > 0:
            comment = '\n' + comment
        return tags + comment
    
    
    def __unpadMessage(self):
        '''
        Remove padding spaces fortune cookies are padded with whitespace (damn featherbrains)
        '''
        lines = self.message.split('\n')
        for spaces in (128, 64, 32, 16, 8, 4, 2, 1):
            padded = True
            for line in lines:
                if not line.startswith(' ' * spaces):
                    padded = False
                    break
            if padded:
                for i in range(0, len(lines)):
                    line = lines[i]
                    line = line[spaces:]
                    lines[i] = line
        lines = [line.rstrip(' ') for line in lines]
        self.message = '\n'.join(lines)
    
    
    def __expandMessage(self):
        '''
        Converts all tabs in the message to spaces by expanding
        '''
        lines = self.message.split('\n')
        buf = ''
        for line in lines:
            (i, n, x) = (0, len(line), 0)
            while i < n:
                c = line[i]
                i += 1
                if c == '\033':
                    colour = Backend.getColour(line, i - 1)
                    i += len(colour) - 1
                    buf += colour
                elif c == '\t':
                    nx = 8 - (x & 7)
                    buf += ' ' * nx
                    x += nx
                else:
                    buf += c
                    if not UCS.isCombining(c):
                        x += 1
            buf += '\n'
        self.message = buf[:-1]
    
    
    def __loadFile(self):
        '''
        Loads the pony file
        '''
        with open(self.ponyfile, 'rb') as ponystream:
            self.pony = ponystream.read().decode('utf8', 'replace')
    
    
    def __truncate(self):
        '''
        Truncate output to the width of the screen
        '''
        if self.width is None:
            return
        lines = self.output.split('\n')
        self.output = ''
        for line in lines:
            (i, n, x) = (0, len(line), 0)
            while i < n:
                c = line[i]
                i += 1
                if c == '\033':
                    colour = Backend.getColour(line, i - 1)
                    i += len(colour) - 1
                    self.output += colour
                else:
                    if x < self.width:
                        self.output += c
                        if not UCS.isCombining(c):
                            x += 1
            self.output += '\n'
        self.output = self.output[:-1]
    
    
    def __processPony(self):
        '''
        Process the pony file and generate output to self.output
        '''
        self.output = ''
        
        AUTO_PUSH = '\033[01010~'
        AUTO_POP  = '\033[10101~'
        
        variables = {'' : '$'}
        for key in self.link:
            variables[key] = AUTO_PUSH + self.link[key] + AUTO_POP
        
        indent = 0
        dollar = None
        balloonLines = None
        colourstack = ColourStack(AUTO_PUSH, AUTO_POP)
        
        (i, n, lineindex, skip, nonskip) = (0, len(self.pony), 0, 0, 0)
        while i < n:
            c = self.pony[i]
            if c == '\t':
                n += 7 - (indent & 7)
                ed = ' ' * (8 - (indent & 7))
                c = ' '
                self.pony = self.pony[:i] + ed + self.pony[i + 1:]
            i += 1
            if c == '$':
                if dollar is not None:
                    if '=' in dollar:
                        name = dollar[:dollar.find('=')]
                        value = dollar[dollar.find('=') + 1:]
                        variables[name] = value
                    elif not dollar.startswith('balloon'):
                        data = variables[dollar].replace('$', '$$')
                        if data == '$$': # if not handled specially we will get an infinity loop
                            if (skip == 0) or (nonskip > 0):
                                if nonskip > 0:
                                    nonskip -= 1
                                self.output += '$'
                                indent += 1
                            else:
                                skip -= 1
                        else:
                            n += len(data)
                            self.pony = self.pony[:i] + data + self.pony[i:]
                    elif self.balloon is not None:
                        (w, h, x, justify) = ('0', 0, 0, None)
                        props = dollar[7:]
                        if len(props) > 0:
                            if ',' in props:
                                if props[0] is not ',':
                                    w = props[:props.index(',')]
                                h = int(props[props.index(',') + 1:])
                            else:
                                w = props
                        if 'l' in w:
                            (x, w) = (int(w[:w.find('l')]), int(w[w.find('l') + 1:]))
                            justify = 'l'
                            w -= x;
                        elif 'c' in w:
                            (x, w) = (int(w[:w.find('c')]), int(w[w.find('c') + 1:]))
                            justify = 'c'
                            w -= x;
                        elif 'r' in w:
                            (x, w) = (int(w[:w.find('r')]), int(w[w.find('r') + 1:]))
                            justify = 'r'
                            w -= x;
                        else:
                            w = int(w)
                        balloon = self.__getBalloon(w, h, x, justify, indent)
                        balloon = balloon.split('\n')
                        balloon = [AUTO_PUSH + self.ballooncolour + item + AUTO_POP for item in balloon]
                        for b in balloon[0]:
                            self.output += b + colourstack.feed(b)
                        if lineindex == 0:
                            balloonpre = '\n' + (' ' * indent)
                            for line in balloon[1:]:
                                self.output += balloonpre;
                                for b in line:
                                    self.output += b + colourstack.feed(b);
                            indent = 0
                        elif len(balloon) > 1:
                            balloonLines = balloon
                            balloonLine = 0
                            balloonIndent = indent
                            indent += Backend.len(balloonLines[0])
                            balloonLines[0] = None
                    dollar = None
                else:
                    dollar = ''
            elif dollar is not None:
                if c == '\033':
                    c = self.pony[i]
                    i += 1
                dollar += c
            elif c == '\033':
                colour = Backend.getColour(self.pony, i - 1)
                for b in colour:
                    self.output += b + colourstack.feed(b);
                i += len(colour) - 1
            elif c == '\n':
                self.output += c
                indent = 0
                (skip, nonskip) = (0, 0)
                lineindex += 1
                if balloonLines is not None:
                    balloonLine += 1
                    if balloonLine == len(balloonLines):
                        balloonLines = None
            else:
                if (balloonLines is not None) and (balloonLines[balloonLine] is not None) and (balloonIndent == indent):
                    data = balloonLines[balloonLine]
                    datalen = Backend.len(data)
                    skip += datalen
                    nonskip += datalen
                    data = data.replace('$', '$$')
                    n += len(data)
                    self.pony = self.pony[:i] + data + self.pony[i:]
                    balloonLines[balloonLine] = None
                else:
                    if (skip == 0) or (nonskip > 0):
                        if nonskip > 0:
                            nonskip -= 1
                        self.output += c + colourstack.feed(c);
                        if not UCS.isCombining(c):
                            indent += 1
                    else:
                        skip -= 1
        
        if balloonLines is not None:
            for line in balloonLines[balloonLine:]:
                data = ' ' * (balloonIndent - indent) + line + '\n'
                for b in data:
                    self.output += b + colourstack.feed(b);
                indent = 0
        
        self.output = self.output.replace(AUTO_PUSH, '').replace(AUTO_POP, '')
        
        if self.balloon is None:
            if (self.balloontop > 0) or (self.balloonbottom > 0):
                self.output = self.output.split('\n')
                self.output = self.output[self.balloontop : ~(self.balloonbottom)]
                self.output = '\n'.join(self.output)
    
    
    @staticmethod
    def getColour(input, offset):
        '''
        Gets colour code att the currect offset in a buffer
        
        @param   input:str   The input buffer
        @param   offset:int  The offset at where to start reading, a escape must begin here
        @return  :str        The escape sequence
        '''
        (i, n) = (offset, len(input))
        rc = input[i]
        i += 1
        if i == n: return rc
        c = input[i]
        i += 1
        rc += c
        
        if c == ']':
            if i == n: return rc
            c = input[i]
            i += 1
            rc += c
            if c == 'P':
                di = 0
                while (di < 7) and (i < n):
                    c = input[i]
                    i += 1
                    di += 1
                    rc += c
            while c == '0':
                c = input[i]
                i += 1
                rc += c
            if c == '4':
                c = input[i]
                i += 1
                rc += c
                if c == ';':
                    c = input[i]
                    i += 1
                    rc += c
                    while c != '\\':
                        c = input[i]
                        i += 1
                        rc += c
        elif c == '[':
            while i < n:
                c = input[i]
                i += 1
                rc += c
                if (c == '~') or (('a' <= c) and (c <= 'z')) or (('A' <= c) and (c <= 'Z')):
                    break
        
        return rc
    
    
    @staticmethod
    def len(input):
        '''
        Calculates the number of visible characters in a text
        
        @param   input:str  The input buffer
        @return  :int       The number of visible characters
        '''
        (rc, i, n) = (0, 0, len(input))
        while i < n:
            c = input[i]
            if c == '\033':
                i += len(Backend.getColour(input, i))
            else:
                i += 1
                if not UCS.isCombining(c):
                    rc += 1
        return rc
    
    
    def __getBalloon(self, width, height, innerleft, justify, left):
        '''
        Generates a balloon with the message
        
        @param   width:int      The minimum width of the balloon
        @param   height:int     The minimum height of the balloon
        @param   innerleft:int  The left column of the required span, excluding that of `left`
        @param   justify:str    Balloon placement justification, 'c' → centered,
                                'l' → left (expand to right), 'r' → right (expand to left)
        @param   left:int       The column where the balloon starts
        @return  :str           The balloon the the message as a string
        '''
        wrap = None
        if self.wrapcolumn is not None:
            wrap = self.wrapcolumn - left
            if wrap < 8:
                wrap = 8
        
        msg = self.message
        if wrap is not None:
            msg = self.__wrapMessage(msg, wrap)
        
        msg = msg.replace('\n', '\033[0m%s\n' % (self.ballooncolour)) + '\033[0m' + self.ballooncolour
        msg = msg.split('\n')
        
        extraleft = 0
        if justify is not None:
            msgwidth = self.len(max(msg, key = self.len)) + self.balloon.minwidth
            extraleft = innerleft
            if msgwidth > width:
                if (justify == 'l') and (wrap is not None):
                    if innerleft + msgwidth > wrap:
                        extraleft -= msgwidth - wrap
                elif justify == 'r':
                    extraleft -= msgwidth - width
                elif justify == 'c':
                    extraleft -= (msgwidth - width) >> 1
                    if extraleft < 0:
                        extraleft = 0
                    if wrap is not None:
                        if extraleft + msgwidth > wrap:
                            extraleft -= msgwidth - wrap
        
        rc = self.balloon.get(width, height, msg, Backend.len);
        if extraleft > 0:
            rc = ' ' * extraleft + rc.replace('\n', '\n' + ' ' * extraleft)
        return rc
    
    
    def __wrapMessage(self, message, wrap):
        '''
        Wraps the message
        
        @param   message:str  The message to wrap
        @param   wrap:int     The width at where to force wrapping
        @return  :str         The message wrapped
        '''
        wraplimit = os.environ['PONYSAY_WRAP_LIMIT'] if 'PONYSAY_WRAP_LIMIT' in os.environ else ''
        wraplimit = 8 if len(wraplimit) == 0 else int(wraplimit)
        
        wrapexceed = os.environ['PONYSAY_WRAP_EXCEED'] if 'PONYSAY_WRAP_EXCEED' in os.environ else ''
        wrapexceed = 5 if len(wrapexceed) == 0 else int(wrapexceed)
        
        buf = ''
        try:
            AUTO_PUSH = '\033[01010~'
            AUTO_POP  = '\033[10101~'
            msg = message.replace('\n', AUTO_PUSH + '\n' + AUTO_POP)
            cstack = ColourStack(AUTO_PUSH, AUTO_POP)
            for c in msg:
                buf += c + cstack.feed(c)
            lines = buf.replace(AUTO_PUSH, '').replace(AUTO_POP, '').split('\n')
            buf = ''
            
            for line in lines:
                b = [None] * len(line)
                map = {0 : 0}
                (bi, cols, w) = (0, 0, wrap)
                (indent, indentc) = (-1, 0)
                
                (i, n) = (0, len(line))
                while i <= n:
                    d = None
                    if i < n:
                        d = line[i]
                    i += 1
                    if d == '\033':
                        ## Invisible stuff
                        i -= 1
                        colourseq = Backend.getColour(line, i)
                        b[bi : bi + len(colourseq)] = colourseq
                        i += len(colourseq)
                        bi += len(colourseq)
                    elif (d is not None) and (d != ' '):
                        ## Fetch word
                        if indent == -1:
                            indent = i - 1
                            for j in range(0, indent):
                                if line[j] == ' ':
                                    indentc += 1
                        b[bi] = d
                        bi += 1
                        if (not UCS.isCombining(d)) and (d != '­'):
                            cols += 1
                        map[cols] = bi
                    else:
                        ## Wrap?
                        mm = 0
                        bisub = 0
                        iwrap = wrap - (0 if indent == 1 else indentc)
                        
                        while ((w > wraplimit) and (cols > w + wrapexceed)) or (cols > iwrap):
                            ## wrap
                            x = w;
                            if mm + x not in map: # Too much whitespace?
                                cols = 0
                                break
                            nbsp = b[map[mm + x]] == ' ' # nbsp
                            m = map[mm + x]
                            
                            if ('­' in b[bisub : m]) and not nbsp: # soft hyphen
                                hyphen = m - 1
                                while b[hyphen] != '­': # soft hyphen
                                    hyphen -= 1
                                while map[mm + x] > hyphen: ## Only looking backward, if forward is required the word is probabily not hyphenated correctly
                                    x -= 1
                                x += 1
                                m = map[mm + x]
                            
                            mm += x - (0 if nbsp else 1) ## − 1 so we have space for a hythen
                            
                            for bb in b[bisub : m]:
                                buf += bb
                            buf += '\n' if nbsp else '\0\n'
                            cols -= x - (0 if nbsp else 1)
                            bisub = m
                            
                            w = iwrap
                            if indent != -1:
                                buf += ' ' * indentc
                        
                        for j in range(bisub, bi):
                            b[j - bisub] = b[j]
                        bi -= bisub
                        
                        if cols > w:
                            buf += '\n'
                            w = wrap
                            if indent != -1:
                                buf += ' ' * indentc
                                w -= indentc
                        for bb in b[:bi]:
                            if bb is not None:
                                buf += bb
                        w -= cols
                        cols = 0
                        bi = 0
                        if d is None:
                            i += 1
                        else:
                            if w > 0:
                                buf += ' '
                                w -= 1
                            else:
                                buf += '\n'
                                w = wrap
                                if indent != -1:
                                    buf += ' ' * indentc
                                    w -= indentc
                buf += '\n'
            
            rc = '\n'.join(line.rstrip(' ') for line in buf[:-1].split('\n'));
            rc = rc.replace('­', ''); # remove soft hyphens
            rc = rc.replace('\0', '%s%s%s' % (AUTO_PUSH, self.hyphen, AUTO_POP))
            return rc
        except Exception as err:
            import traceback
            errormessage = ''.join(traceback.format_exception(type(err), err, None))
            rc = '\n'.join(line.rstrip(' ') for line in buf.split('\n'));
            rc = rc.replace('\0', '%s%s%s' % (AUTO_PUSH, self.hyphen, AUTO_POP))
            errormessage += '\n---- WRAPPING BUFFER ----\n\n' + rc
            try:
                if os.readlink('/proc/self/fd/2') != os.readlink('/proc/self/fd/1'):
                    printerr(errormessage, end='')
                    return message
            except:
                pass
            return message + '\n\n\033[0;1;31m---- EXCEPTION IN PONYSAY WHILE WRAPPING ----\033[0m\n\n' + errormessage


########NEW FILE########
__FILENAME__ = balloon
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *
from ucs import *



class Balloon():
    '''
    Balloon format class
    '''
    
    def __init__(self, link, linkmirror, linkcross, ww, ee, nw, nnw, n, nne, ne, nee, e, see, se, sse, s, ssw, sw, sww, w, nww):
        '''
        Constructor
        
        @param  link:str        The \-directional balloon line character
        @param  linkmirror:str  The /-directional balloon line character
        @param  linkcross:str   The /-directional balloon crossing a \-directional ballonon line character
        @param  ww:str          See the info manual
        @param  ee:str          See the info manual
        @param  nw:list<str>    See the info manual
        @param  nnw:list<str>   See the info manual
        @param  n:list<str>     See the info manual
        @param  nne:list<str>   See the info manual
        @param  ne:list<str>    See the info manual
        @param  nee:str         See the info manual
        @param  e:str           See the info manual
        @param  see:str         See the info manual
        @param  se:list<str>    See the info manual
        @param  sse:list<str>   See the info manual
        @param  s:list<str>     See the info manual
        @param  ssw:list<str>   See the info manual
        @param  sw:list<str>    See the info manual
        @param  sww:str         See the info manual
        @param  w:str           See the info manual
        @param  nww:str         See the info manual
        '''
        (self.link, self.linkmirror, self.linkcross) = (link, linkmirror, linkcross)
        (self.ww, self.ee) = (ww, ee)
        (self.nw, self.ne, self.se, self.sw) = (nw, ne, se, sw)
        (self.nnw, self.n, self.nne) = (nnw, n, nne)
        (self.nee, self.e, self.see) = (nee, e, see)
        (self.sse, self.s, self.ssw) = (sse, s, ssw)
        (self.sww, self.w, self.nww) = (sww, w, nww)
        
        _ne = max(ne, key = UCS.dispLen)
        _nw = max(nw, key = UCS.dispLen)
        _se = max(se, key = UCS.dispLen)
        _sw = max(sw, key = UCS.dispLen)
        
        minE = UCS.dispLen(max([_ne, nee, e, see, _se, ee], key = UCS.dispLen))
        minW = UCS.dispLen(max([_nw, nww, e, sww, _sw, ww], key = UCS.dispLen))
        minN = len(max([ne, nne, n, nnw, nw], key = len))
        minS = len(max([se, sse, s, ssw, sw], key = len))
        
        self.minwidth  = minE + minE
        self.minheight = minN + minS
    
    
    def get(self, minw, minh, lines, lencalc):
        '''
        Generates a balloon with a message
        
        @param   minw:int          The minimum number of columns of the balloon
        @param   minh:int          The minimum number of lines of the balloon
        @param   lines:list<str>   The text lines to display
        @param   lencalc:int(str)  Function used to compute the length of a text line
        @return  :str              The balloon as a formated string
        '''
        ## Get dimension
        h = self.minheight + len(lines)
        w = self.minwidth + lencalc(max(lines, key = lencalc))
        if w < minw:  w = minw
        if h < minh:  h = minh
        
        ## Create edges
        if len(lines) > 1:
            (ws, es) = ({0 : self.nww, len(lines) - 1 : self.sww}, {0 : self.nee, len(lines) - 1 : self.see})
            for j in range(1, len(lines) - 1):
                ws[j] = self.w
                es[j] = self.e
        else:
            (ws, es) = ({0 : self.ww}, {0 : self.ee})
        
        rc = []
        
        ## Create the upper part of the balloon
        for j in range(0, len(self.n)):
            outer = UCS.dispLen(self.nw[j]) + UCS.dispLen(self.ne[j])
            inner = UCS.dispLen(self.nnw[j]) + UCS.dispLen(self.nne[j])
            if outer + inner <= w:
                rc.append(self.nw[j] + self.nnw[j] + self.n[j] * (w - outer - inner) + self.nne[j] + self.ne[j])
            else:
                rc.append(self.nw[j] + self.n[j] * (w - outer) + self.ne[j])
        
        ## Encapsulate the message instead left and right edges of balloon
        for j in range(0, len(lines)):
            rc.append(ws[j] + lines[j] + ' ' * (w - lencalc(lines[j]) - UCS.dispLen(self.w) - UCS.dispLen(self.e)) + es[j])
        
        ## Create the lower part of the balloon
        for j in range(0, len(self.s)):
            outer = UCS.dispLen(self.sw[j]) + UCS.dispLen(self.se[j])
            inner = UCS.dispLen(self.ssw[j]) + UCS.dispLen(self.sse[j])
            if outer + inner <= w:
                rc.append(self.sw[j] + self.ssw[j] + self.s[j] * (w - outer - inner) + self.sse[j] + self.se[j])
            else:
                rc.append(self.sw[j] + self.s[j] * (w - outer) + self.se[j])
        
        return '\n'.join(rc)
    
    
    @staticmethod
    def fromFile(balloonfile, isthink):
        '''
        Creates the balloon style object
        
        @param   balloonfile:str  The file with the balloon style, may be `None`
        @param   isthink:bool     Whether the ponythink command is used
        @return  :Balloon         Instance describing the balloon's style
        '''
        ## Use default balloon if none is specified
        if balloonfile is None:
            if isthink:
                return Balloon('o', 'o', 'o', '( ', ' )', [' _'], ['_'], ['_'], ['_'], ['_ '], ' )',  ' )', ' )', ['- '], ['-'], ['-'], ['-'], [' -'],  '( ', '( ', '( ')
            return    Balloon('\\', '/', 'X', '< ', ' >', [' _'], ['_'], ['_'], ['_'], ['_ '], ' \\', ' |', ' /', ['- '], ['-'], ['-'], ['-'], [' -'], '\\ ', '| ', '/ ')
        
        ## Initialise map for balloon parts
        map = {}
        for elem in ('\\', '/', 'X', 'ww', 'ee', 'nw', 'nnw', 'n', 'nne', 'ne', 'nee', 'e', 'see', 'se', 'sse', 's', 'ssw', 'sw', 'sww', 'w', 'nww'):
            map[elem] = []
        
        ## Read all lines in the balloon file
        with open(balloonfile, 'rb') as balloonstream:
            data = balloonstream.read().decode('utf8', 'replace')
            data = [line.replace('\n', '') for line in data.split('\n')]
        
        ## Parse the balloon file, and fill the map
        last = None
        for line in data:
            if len(line) > 0:
                if line[0] == ':':
                    map[last].append(line[1:])
                else:
                    last = line[:line.index(':')]
                    value = line[len(last) + 1:]
                    map[last].append(value)
        
        ## Return the balloon
        return Balloon(map['\\'][0], map['/'][0], map['X'][0], map['ww'][0], map['ee'][0], map['nw'], map['nnw'], map['n'],
                       map['nne'], map['ne'], map['nee'][0], map['e'][0], map['see'][0], map['se'], map['sse'],
                       map['s'], map['ssw'], map['sw'], map['sww'][0], map['w'][0], map['nww'][0])


########NEW FILE########
__FILENAME__ = colourstack
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *



class ColourStack():
    '''
    ANSI colour stack
    
    This is used to make layers with independent coloursations
    '''
    
    def __init__(self, autopush, autopop):
        '''
        Constructor
        
        @param  autopush:str  String that, when used, will create a new independently colourised layer
        @param  autopop:str   String that, when used, will end the current layer and continue of the previous layer
        '''
        self.autopush = autopush
        self.autopop  = autopop
        self.lenpush  = len(autopush)
        self.lenpop   = len(autopop)
        self.bufproto = ' ' * (self.lenpush if self.lenpush > self.lenpop else self.lenpop)
        self.stack    = []
        self.push()
        self.seq      = None
    
    
    def push(self):
        '''
        Create a new independently colourised layer
        
        @return  :str  String that should be inserted into your buffer
        '''
        self.stack.insert(0, [self.bufproto, None, None, [False] * 9])
        if len(self.stack) == 1:
            return None
        return '\033[0m'
    
    
    def pop(self):
        '''
        End the current layer and continue of the previous layer
        
        @return  :str  String that should be inserted into your buffer
        '''
        old = self.stack.pop(0)
        rc = '\033[0;'
        if len(self.stack) == 0: # last resort in case something made it pop too mush
            push()
        new = self.stack[0]
        if new[1] is not None:  rc += new[1] + ';'
        if new[2] is not None:  rc += new[2] + ';'
        for i in range(0, 9):
            if new[3][i]:
                rc += str(i + 1) + ';'
        return rc[:-1] + 'm'
    
    
    def feed(self, char):
        '''
        Use this, in sequence, for which character in your buffer that contains yor autopush and autopop
        string, the automatically get push and pop string to insert after each character
        
        @param   :chr  One character in your buffer
        @return  :str  The text to insert after the input character
        '''
        if self.seq is not None:
            self.seq += char
            if (char == '~') or (('a' <= char) and (char <= 'z')) or (('A' <= char) and (char <= 'Z')):
                if (self.seq[0] == '[') and (self.seq[-1] == 'm'):
                    self.seq = self.seq[1:-1].split(';')
                    (i, n) = (0, len(self.seq))
                    while i < n:
                        part = self.seq[i]
                        p = 0 if part == '' else int(part)
                        i += 1
                        if p == 0:             self.stack[0][1:] = [None, None, [False] * 9]
                        elif 1 <= p <= 9:      self.stack[0][3][p - 1] = True
                        elif 21 <= p <= 29:    self.stack[0][3][p - 21] = False
                        elif p == 39:          self.stack[0][1] = None
                        elif p == 49:          self.stack[0][2] = None
                        elif 30 <= p <= 37:    self.stack[0][1] = part
                        elif 90 <= p <= 97:    self.stack[0][1] = part
                        elif 40 <= p <= 47:    self.stack[0][2] = part
                        elif 100 <= p <= 107:  self.stack[0][2] = part
                        elif p == 38:
                            self.stack[0][1] = '%s;%s;%s' % (part, self.seq[i], self.seq[i + 1])
                            i += 2
                        elif p == 48:
                            self.stack[0][2] = '%s;%s;%s' % (part, self.seq[i], self.seq[i + 1])
                            i += 2
                self.seq = None
        elif char == '\033':
            self.seq = ''
        buf = self.stack[0][0]
        buf = buf[1:] + char
        rc = ''
        if   buf[-self.lenpush:] == self.autopush:  rc = self.push()
        elif buf[-self.lenpop:]  == self.autopop:   rc = self.pop()
        self.stack[0][0] = buf
        return rc


########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''

import os
import shutil
import sys
import random
from subprocess import Popen, PIPE



VERSION = 'dev'  # this line should not be edited, it is fixed by the build system
'''
The version of ponysay
'''



def print(text = '', end = '\n'):
    '''
    Hack to enforce UTF-8 in output (in the future, if you see anypony not using utf-8 in
    programs by default, report them to Princess Celestia so she can banish them to the moon)
    
    @param  text:str  The text to print (empty string is default)
    @param  end:str   The appendix to the text to print (line breaking is default)
    '''
    sys.stdout.buffer.write((str(text) + end).encode('utf-8'))

def printerr(text = '', end = '\n'):
    '''
    stderr equivalent to print()
    
    @param  text:str  The text to print (empty string is default)
    @param  end:str   The appendix to the text to print (line breaking is default)
    '''
    sys.stderr.buffer.write((str(text) + end).encode('utf-8'))

fd3 = None
def printinfo(text = '', end = '\n'):
    '''
    /proc/self/fd/3 equivalent to print()
    
    @param  text:str  The text to print (empty string is default)
    @param  end:str   The appendix to the text to print (line breaking is default)
    '''
    global fd3
    if os.path.exists('/proc/self/fd/3') and not os.path.isdir(os.path.realpath('/proc/self/fd/3')):
        if fd3 is None:
            fd3 = os.fdopen(3, 'w')
    if fd3 is not None:
        fd3.write(str(text) + end)


def endswith(text, ending):
    '''
    Checks whether a text ends with a specific text, but has more
    
    @param   text:str    The text to test
    @param   ending:str  The desired end of the text
    @return  :bool       The result of the test
    '''
    return text.endswith(ending) and not (text == ending)


def gettermsize():
    '''
    Gets the size of the terminal in (rows, columns)
    
    @return  (rows, columns):(int, int)  The number or lines and the number of columns in the terminal's display area
    '''
    ## Call `stty` to determine the size of the terminal, this way is better than using python's ncurses
    for channel in (sys.stderr, sys.stdout, sys.stdin):
        termsize = Popen(['stty', 'size'], stdout=PIPE, stdin=channel, stderr=PIPE).communicate()[0]
        if len(termsize) > 0:
            termsize = termsize.decode('utf8', 'replace')[:-1].split(' ') # [:-1] removes a \n
            termsize = [int(item) for item in termsize]
            return termsize
    return (24, 80) # fall back to minimal sane size


########NEW FILE########
__FILENAME__ = kms
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *



KMS_VERSION = '2'
'''
KMS support version constant
'''



class KMS():
    '''
    KMS support utilisation
    '''
    
    @staticmethod
    def usingKMS(linuxvt):
        '''
        Identifies whether KMS support is utilised
        
        @param   linuxvt:bool  Whether Linux VT is used
        @return  :bool         Whether KMS support is utilised
        '''
        ## KMS is not utilised if Linux VT is not used
        if not linuxvt:
            return False
        
        ## If the palette string is empty KMS is not utilised
        return KMS.__getKMSPalette() != ''
    
    
    @staticmethod
    def __parseKMSCommand():
        '''
        Parse the KMS palette command stored in the environment variables
        
        @return  :str?  The KMS palette, `None` if none
        '''
        env_kms_cmd = os.environ['PONYSAY_KMS_PALETTE_CMD'] if 'PONYSAY_KMS_PALETTE_CMD' in os.environ else None
        if (env_kms_cmd is not None) and (not env_kms_cmd == ''):
            env_kms = Popen(shlex.split(env_kms_cmd), stdout=PIPE, stdin=sys.stderr).communicate()[0].decode('utf8', 'replace')
            if env_kms[-1] == '\n':
                env_kms = env_kms[:-1]
                return env_kms
        return None
    
    
    @staticmethod
    def __getKMSPalette():
        '''
        Get the KMS palette
        
        @return  :str  The KMS palette
        '''
        ## Read the PONYSAY_KMS_PALETTE environment variable
        env_kms = os.environ['PONYSAY_KMS_PALETTE'] if 'PONYSAY_KMS_PALETTE' in os.environ else None
        if env_kms is None:
            env_kms = ''
        
        ## Read the PONYSAY_KMS_PALETTE_CMD environment variable, and run it
        env_kms_cmd = KMS.__parseKMSCommand()
        if env_kms_cmd is not None:
            env_kms = env_kms_cmd
        
        return env_kms
    
    
    @staticmethod
    def __getCacheDirectory(home):
        '''
        Gets the KMS change directory, and creates it if it does not exist
        
        @param   home:str                        The user's home directory
        @return  (cachedir, shared):(str, bool)  The cache directory and whether it is user shared
        '''
        cachedir = '/var/cache/ponysay'
        shared = True
        if not os.path.isdir(cachedir):
            cachedir = home + '/.cache/ponysay'
            shared = False
            if not os.path.isdir(cachedir):
                os.makedirs(cachedir)
        return (cachedir, shared)
    
    
    @staticmethod
    def __isCacheOld(cachedir):
        '''
        Gets whether the cache is old
        
        @param   cachedir:str  The cache directory
        @return                Whether the cache is old
        '''
        newversion = False
        if not os.path.isfile(cachedir + '/.version'):
            newversion = True
        else:
            with open(cachedir + '/.version', 'rb') as cachev:
                if cachev.read().decode('utf8', 'replace').replace('\n', '') != KMS_VERSION:
                    newversion = True
        return newversion
    
    
    @staticmethod
    def __cleanCache(cachedir):
        '''
        Clean the cache directory
        
        @param  cachedir:str  The cache directory
        '''
        for cached in os.listdir(cachedir):
            cached = cachedir + '/' + cached
            if os.path.isdir(cached) and not os.path.islink(cached):
                shutil.rmtree(cached, False)
            else:
                os.remove(cached)
        with open(cachedir + '/.version', 'w+') as cachev:
            cachev.write(KMS_VERSION)
            if shared:
                try:
                    os.chmod(cachedir + '/.version', 0o7777)
                except:
                    pass
    
    
    @staticmethod
    def __createKMSPony(pony, kmspony, cachedir, palette, shared):
        '''
        Create KMS pony
        
        @param  pony:str      Choosen pony file
        @param  kmspony:str   The KMS pony file
        @param  cachedir:str  The cache directory
        @param  palette:str   The palette
        @parma  shared:str    Whether shared cache is used
        '''
        ## kmspony directory
        kmsponydir = kmspony[:kmspony.rindex('/')]
        
        ## Change file names to be shell friendly
        _kmspony  = '\'' +  kmspony.replace('\'', '\'\\\'\'') + '\''
        _pony     = '\'' +     pony.replace('\'', '\'\\\'\'') + '\''
        _cachedir = '\'' + cachedir.replace('\'', '\'\\\'\'') + '\''
        
        ## Create kmspony
        if not os.path.isdir(kmsponydir):
            os.makedirs(kmsponydir)
            if shared:
                Popen('chmod -R 7777 -- %s/kmsponies' % _cachedir, shell=True).wait()
        opts = '--balloon n --left - --right - --top - --bottom -'
        ponytoolcmd = 'ponytool --import ponysay --file %%s %s --export ponysay --file %%s --platform linux %s' % (opts, opts)
        ponytoolcmd += ' --colourful y --fullcolour y --palette %s'
        if not os.system(ponytoolcmd % (_pony, _kmspony, palette)) == 0:
            printerr('Unable to run ponytool successfully, you need util-say>=3 for KMS support')
            exit(1)
        if shared:
            try:
                os.chmod(kmspony, 0o7777)
            except:
                pass
    
    
    @staticmethod
    def kms(pony, home, linuxvt):
        '''
        Returns the file name of the input pony converted to a KMS pony, or if KMS is not used, the input pony itself
        
        @param   pony:str      Choosen pony file
        @param   home:str      The home directory
        @param   linuxvt:bool  Whether Linux VT is used
        @return  :str          Pony file to display
        '''
        ## If not in Linux VT, return the pony as is
        if not linuxvt:
            return pony
        
        ## Get KMS palette
        env_kms = KMS.__getKMSPalette()
        
        ## If not using KMS, return the pony as is
        if env_kms == '':
            return pony
        
        ## Store palette string and a clone with just the essentials
        palette = env_kms
        palettefile = env_kms.replace('\033]P', '')
        
        ## Get and if necessary make cache directory
        (cachedir, shared) = KMS.__getCacheDirectory(home)
        
        ## KMS support version control, clean everything if not matching
        if KMS.__isCacheOld(cachedir):
            KMS.__cleanCache(cachedir)
        
        ## Get kmspony directory and kmspony file
        kmsponies = cachedir + '/kmsponies/' + palettefile
        kmspony = kmsponies + '/' + pony
        
        ## If the kmspony is missing, create it
        if not os.path.isfile(kmspony):
            KMS.__createKMSPony(pony, kmspony, cachedir, palette, shared)
        
        return kmspony


########NEW FILE########
__FILENAME__ = list
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *
from ucs import *



class List():
    '''
    File listing functions
    '''
    
    @staticmethod
    def __columnise(ponies):
        '''
        Columnise a list and prints it
        
        @param  ponies:list<(str, str)>  All items to list, each item should have to elements: unformated name, formated name
        '''
        ## Get terminal width, and a 2 which is the space between columns
        termwidth = gettermsize()[1] + 2
        ## Sort the ponies, and get the cells' widths, and the largest width + 2
        ponies.sort(key = lambda pony : pony[0])
        widths = [UCS.dispLen(pony[0]) for pony in ponies]
        width = max(widths) + 2 # longest pony file name + space between columns
        
        ## Calculate the number of rows and columns, can create a list of empty columns
        cols = termwidth // width # do not believe electricians, this means ⌊termwidth / width⌋
        rows = (len(ponies) + cols - 1) // cols
        columns = []
        for c in range(0, cols):  columns.append([])
        
        ## Fill the columns with cells of ponies
        (y, x) = (0, 0)
        for j in range(0, len(ponies)):
            cell = ponies[j][1] + ' ' * (width - widths[j]);
            columns[x].append(cell)
            y += 1
            if y == rows:
                x += 1
                y = 0
        
        ## Make the columnisation nicer by letting the last row be partially empty rather than the last column
        diff = rows * cols - len(ponies)
        if (diff > 2) and (rows > 1):
            c = cols - 1
            diff -= 1
            while diff > 0:
                columns[c] = columns[c - 1][-diff:] + columns[c]
                c -= 1
                columns[c] = columns[c][:-diff]
                diff -= 1
        
        ## Create rows from columns
        lines = []
        for r in range(0, rows):
             lines.append([])
             for c in range(0, cols):
                 if r < len(columns[c]):
                     line = lines[r].append(columns[c][r])
        
        ## Print the matrix, with one extra blank row
        print('\n'.join([''.join(line)[:-2] for line in lines]))
        print()
    
    
    @staticmethod
    def simplelist(ponydirs, quoters = [], ucsiser = None):
        '''
        Lists the available ponies
        
        @param  ponydirs:itr<str>          The pony directories to use
        @param  quoters:__in__(str)→bool   Set of ponies that of quotes
        @param  ucsiser:(list<str>)?→void  Function used to UCS:ise names
        '''
        for ponydir in ponydirs: # Loop ponydirs
            ## Get all ponies in the directory
            _ponies = os.listdir(ponydir)
            
            ## Remove .pony from all files and skip those that does not have .pony
            ponies = []
            for pony in _ponies:
                if endswith(pony, '.pony'):
                    ponies.append(pony[:-5])
            
            ## UCS:ise pony names, they are already sorted
            if ucsiser is not None:
                ucsiser(ponies)
            
            ## If ther directory is not empty print its name and all ponies, columnised
            if len(ponies) == 0:
                continue
            print('\033[1mponies located in ' + ponydir + '\033[21m')
            List.__columnise([(pony, '\033[1m' + pony + '\033[21m' if pony in quoters else pony) for pony in ponies])
    
    
    @staticmethod
    def linklist(ponydirs = None, quoters = [], ucsiser = None):
        '''
        Lists the available ponies with alternatives inside brackets
        
        @param  ponydirs:itr<str>                        The pony directories to use
        @param  quoters:__in__(str)→bool                  Set of ponies that of quotes
        @param  ucsiser:(list<str>, map<str, str>)?→void  Function used to UCS:ise names
        '''
        ## Get the size of the terminal
        termsize = gettermsize()
        
        for ponydir in ponydirs: # Loop ponydirs
            ## Get all pony files in the directory
            _ponies = os.listdir(ponydir)
            
            ## Remove .pony from all files and skip those that does not have .pony
            ponies = []
            for pony in _ponies:
                if endswith(pony, '.pony'):
                    ponies.append(pony[:-5])
            
            ## If there are no ponies in the directory skip to next directory, otherwise, print the directories name
            if len(ponies) == 0:
                continue
            print('\033[1mponies located in ' + ponydir + '\033[21m')
            
            ## UCS:ise pony names
            pseudolinkmap = {}
            if ucsiser is not None:
                ucsiser(ponies, pseudolinkmap)
            
            ## Create target–link-pair, with `None` as link if the file is not a symlink or in `pseudolinkmap`
            pairs = []
            for pony in ponies:
                if pony in pseudolinkmap:
                    pairs.append((pony, pseudolinkmap[pony] + '.pony'));
                else:
                    pairs.append((pony, os.path.realpath(ponydir + pony + '.pony') if os.path.islink(ponydir + pony + '.pony') else None))
            
            ## Create map from source pony to alias ponies for each pony
            ponymap = {}
            for pair in pairs:
                if (pair[1] is None) or (pair[1] == ''):
                    if pair[0] not in ponymap:
                        ponymap[pair[0]] = []
                else:
                    target = pair[1][:-5]
                    if '/' in target:
                        target = target[target.rindex('/') + 1:]
                    if target in ponymap:
                        ponymap[target].append(pair[0])
                    else:
                        ponymap[target] = [pair[0]]
            
            ## Create list of source ponies concatenated with alias ponies in brackets
            ponies = {}
            for pony in ponymap:
                w = UCS.dispLen(pony)
                item = '\033[1m' + pony + '\033[21m' if (pony in quoters) else pony
                syms = ponymap[pony]
                syms.sort()
                if len(syms) > 0:
                    w += 2 + len(syms)
                    item += ' ('
                    first = True
                    for sym in syms:
                        w += UCS.dispLen(sym)
                        if first:  first = False
                        else:      item += ' '
                        item += '\033[1m' + sym + '\033[21m' if (sym in quoters) else sym
                    item += ')'
                ponies[(item.replace('\033[1m', '').replace('\033[21m', ''), item)] = w
            
            ## Print the ponies, columnised
            List.__columnise(list(ponies))
    
    
    @staticmethod
    def onelist(standarddirs, extradirs = None, ucsiser = None):
        '''
        Lists the available ponies on one column without anything bold or otherwise formated
        
        @param  standard:itr<str>?         Include standard ponies
        @param  extra:itr<str>?            Include extra ponies
        @param  ucsiser:(list<str>)?→void  Function used to UCS:ise names
        '''
        ## Get all pony files
        _ponies = []
        if standarddirs is not None:
            for ponydir in standarddirs:
                _ponies += os.listdir(ponydir)
        if extradirs is not None:
            for ponydir in extradirs:
                _ponies += os.listdir(ponydir)
            
        ## Remove .pony from all files and skip those that does not have .pony
        ponies = []
        for pony in _ponies:
            if endswith(pony, '.pony'):
                ponies.append(pony[:-5])
        
        ## UCS:ise and sort
        if ucsiser is not None:
            ucsiser(ponies)
        ponies.sort()
        
        ## Print each one on a seperate line, but skip duplicates
        last = ''
        for pony in ponies:
            if not pony == last:
                last = pony
                print(pony)
    
    
    @staticmethod
    def balloonlist(balloondirs, isthink):
        '''
        Prints a list of all balloons
        
        @param  balloondirs:itr<str>  The balloon directories to use
        @param  isthink:bool          Whether the ponythink command is used
        '''
        ## Get the size of the terminal
        termsize = gettermsize()
        
        ## Get all balloons
        balloonset = set()
        for balloondir in balloondirs:
            for balloon in os.listdir(balloondir):
                ## Use .think if running ponythink, otherwise .say
                if isthink and endswith(balloon, '.think'):
                    balloon = balloon[:-6]
                elif (not isthink) and endswith(balloon, '.say'):
                    balloon = balloon[:-4]
                else:
                    continue
                
                ## Add the balloon if there is none with the same name
                if balloon not in balloonset:
                    balloonset.add(balloon)
        
        ## Print all balloos, columnised
        List.__columnise([(balloon, balloon) for balloon in list(balloonset)])


########NEW FILE########
__FILENAME__ = metadata
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *



class Metadata():
    '''
    Metadata functions
    '''
    
    @staticmethod
    def makeRestrictionLogic(restriction):
        '''
        Make restriction test logic function
        
        @param   restriction:list<string>  Metadata based restrictions
        @return  :dict<str, str>→bool      Test function
        '''
        def get_test(cell):
            strict = cell[0][-1] != '?'
            key = cell[0]
            if not strict:
                key = key[:-1]
            invert = cell[1][0] == '!'
            value = cell[1][1 if invert else 0:]
            
            class SITest():
                def __init__(self, cellkey, cellvalue):
                    (self.cellkey, self.cellvalue) = (cellkey, cellvalue)
                def __call__(self, has):
                    return False if self.cellkey not in has else (self.cellvalue not in has[self.cellkey])
                def __str__(self):
                    return 'si(%s : %s)' % (self.cellkey, self.callvalue)
            class STest():
                def __init__(self, cellkey, cellvalue):
                    (self.cellkey, self.cellvalue) = (cellkey, cellvalue)
                def __call__(self, has):
                    return False if self.cellkey not in has else (self.cellvalue in has[self.cellkey])
                def __str__(self):
                    return 's(%s : %s)' % (self.cellkey, self.callvalue)
            class ITest():
                def __init__(self, cellkey, cellvalue):
                    (self.cellkey, self.cellvalue) = (cellkey, cellvalue)
                def __call__(self, has):
                    return True if self.cellkey not in has else (self.cellvalue not in has[self.cellkey])
                def __str__(self):
                    return 'i(%s : %s)' % (self.cellkey, self.callvalue)
            class NTest():
                def __init__(self, cellkey, cellvalue):
                    (self.cellkey, self.cellvalue) = (cellkey, cellvalue)
                def __call__(self, has):
                    return True if self.cellkey not in has else (self.cellvalue in has[self.cellkey])
                def __str__(self):
                    return 'n(%s : %s)' % (self.cellkey, self.callvalue)
            
            if strict and invert:  return SITest(key, value)
            if strict:             return STest(key, value)
            if invert:             return ITest(key, value)
            return NTest(key, value)
        
        class Logic():
            def __init__(self, table):
                self.table = table
            def __call__(self, cells):
                for alternative in self.table:
                    ok = True
                    for cell in alternative:
                        if not cell(cells):
                            ok = False
                            break
                    if ok:
                        return True
                return False
        
        table = [[get_test((cell[:cell.index('=')].upper(), cell[cell.index('=') + 1:]))
                  for cell in clause.replace('_', '').replace(' ', '').split('+')]
                  for clause in restriction
                ]
        
        return Logic(table)
    
    
    @staticmethod
    def restrictedPonies(ponydir, logic):
        '''
        Get ponies that pass restriction
        
        @param   ponydir:str       Pony directory, must end with `os.sep`
        @param   logic:(str)→bool  Restriction test functor
        @return  :list<str>        Passed ponies
        '''
        import pickle
        passed = []
        if os.path.exists(ponydir + 'metadata'):
            data = None
            with open(ponydir + 'metadata', 'rb') as file:
                data = pickle.load(file)
            for ponydata in data:
                (pony, meta) = ponydata
                if logic(meta):
                    passed.append(pony)
        return passed
    
    
    @staticmethod
    def getFitting(fitting, requirement, file):
        '''
        Get ponies that fit the terminal
        
        @param  fitting:add(str)→void  The set to fill
        @param  requirement:int        The maximum allowed value
        @param  file:istream           The file with all data
        '''
        data = file.read() # not too much data, can load everything at once
        ptr = 0
        while data[ptr] != 47: # 47 == ord('/')
            ptr += 1
        ptr += 1
        size = 0
        while data[ptr] != 47: # 47 == ord('/')
            size = (size * 10) - (data[ptr] & 15)
            ptr += 1
        ptr += 1
        jump = ptr - size
        stop = 0
        backjump = 0
        while ptr < jump:
            size = 0
            while data[ptr] != 47: # 47 == ord('/')
                size = (size * 10) - (data[ptr] & 15)
                ptr += 1
            ptr += 1
            if -size > requirement:
                if backjump > 0:
                    ptr = backjump
                    while data[ptr] != 47: # 47 == ord('/')
                        stop = (stop * 10) - (data[ptr] & 15)
                        ptr += 1
                    stop = -stop
                break
            backjump = ptr
            while data[ptr] != 47: # 47 == ord('/')
                ptr += 1
            ptr += 1
        if ptr == jump:
            stop = len(data)
        else:
            ptr = jump
            stop += ptr
        passed = data[jump : stop].decode('utf8', 'replace').split('/')
        for pony in passed:
            fitting.add(pony)


########NEW FILE########
__FILENAME__ = ponysay
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *
from backend import *
from balloon import *
from spellocorrecter import *
from ucs import *
from kms import *
from list import *
from metadata import *



class Ponysay():
    '''
    This is the mane class of ponysay
    '''
    
    def __init__(self):
        '''
        Constructor
        '''
        
        # The user's home directory
        self.HOME = os.environ['HOME'] if 'HOME' in os.environ else ''
        if len(self.HOME) == 0:
            os.environ['HOME'] = self.HOME = os.path.expanduser('~')
        
        
        ## Load extension and configurations via ponysayrc
        for file in ('$XDG_CONFIG_HOME/ponysay/ponysayrc', '$HOME/.config/ponysay/ponysayrc', '$HOME/.ponysayrc', '/etc/ponysayrc'):
            file = Ponysay.__parseFile(file)
            if (file is not None) and os.path.exists(file):
                with open(file, 'rb') as ponysayrc:
                    code = ponysayrc.read().decode('utf8', 'replace') + '\n'
                    env = os.environ
                    code = compile(code, file, 'exec')
                    exec(code)
                break
        
        self.HOME = os.environ['HOME'] if 'HOME' in os.environ else '' # in case ~/.ponysayrc changes it
        if len(self.HOME) == 0:
            os.environ['HOME'] = self.HOME = os.path.expanduser('~')
        
        
        # Whether any unrecognised options was parsed, this should be set by the invoker before run()
        self.unrecognised = False
        
        
        # Whether the program is execute in Linux VT (TTY)
        self.linuxvt = ('TERM' in os.environ) and (os.environ['TERM'] == 'linux')
        
        # Whether the script is executed as ponythink
        self.isthink = Ponysay.__isPonythink()
        
        
        # Whether stdin is piped
        self.pipelinein = not sys.stdin.isatty()
        
        # Whether stdout is piped
        self.pipelineout = not sys.stdout.isatty()
        
        # Whether stderr is piped
        self.pipelineerr = not sys.stderr.isatty()
        
        
        # Whether KMS is used
        self.usekms = KMS.usingKMS(self.linuxvt)
        
        
        # Mode string that modifies or adds $ variables in the pony image
        self.mode = ''
        
        
        # The directories where pony files are stored, ttyponies/ are used if the terminal is Linux VT (also known as TTY) and not with KMS
        self.xponydirs = Ponysay.__getShareDirectories('ponies/')
        self.vtponydirs = Ponysay.__getShareDirectories('ttyponies/')
        
        # The directories where pony files are stored, extrattyponies/ are used if the terminal is Linux VT (also known as TTY) and not with KMS
        self.extraxponydirs = Ponysay.__getShareDirectories('extraponies/')
        self.extravtponydirs = Ponysay.__getShareDirectories('extrattyponies/')
        
        # The directories where quotes files are stored
        self.quotedirs = Ponysay.__getShareDirectories('quotes/')
        
        # The directories where balloon style files are stored
        self.balloondirs = Ponysay.__getShareDirectories('balloons/')
        
        # ucsmap files
        self.ucsmaps = Ponysay.__getShareDirectories('ucsmap/')
        
        
    def __parseFile(file):
        '''
        Parse a file name encoded with environment variables
        
        @param   file  The encoded file name
        @return        The target file name, None if the environment variables are not declared
        '''
        if '$' in file:
            buf = ''
            esc = False
            var = None
            for c in file:
                if esc:
                    buf += c
                    esc = False
                elif var is not None:
                    if c == '/':
                        var = os.environ[var] if var in os.environ else ''
                        if len(var) == 0:
                            return None
                        buf += var + c
                        var = None
                    else:
                        var += c
                elif c == '$':
                    var = ''
                elif c == '\\':
                    esc = True
                else:
                    buf += c
            return buf
        return file

    
    def __getShareDirectories(directory):
        '''
        Gets existing unique /share directories
        
        @param   directory:str  The directory base name
        @return  :list<str>     Absolute directory names
        '''
        appendset = set()
        rc = []
        _ponydirs = Ponysay.__share(directory)
        for ponydir in _ponydirs:
            if (ponydir is not None) and os.path.isdir(ponydir) and (ponydir not in appendset):
                rc.append(ponydir)
                appendset.add(ponydir)
        return rc
    
    
    def __share(file):
        '''
        Gets /share files
        
        @param   file:str    The file base name
        @return  :list<str>  Absolute file names
        '''
        def cat(a, b):
            if a is None:
                return None
            return a + b
        # TODO use only ./ in development mode
        return [cat(Ponysay.__parseFile(item), file) for item in [
                '$XDG_DATA_HOME/ponysay/',
                '$HOME/.local/share/ponysay/',
                '/usr/share/ponysay/'
               ]]
    
    
    def __isPonythink():
        '''
        Check if ponythink is executed
        '''
        isthink = sys.argv[0]
        if os.sep in isthink:
            isthink = isthink[isthink.rfind(os.sep) + 1:]
        if os.extsep in isthink:
            isthink = isthink[:isthink.find(os.extsep)]
        isthink = isthink.endswith('think')
        return isthink
    
    
    
    def run(self, args):
        '''
        Starts the part of the program the arguments indicate
        
        @param  args:ArgParser  Parsed command line arguments
        '''
        if (args.argcount == 0) and not self.pipelinein:
            args.help()
            exit(254)
            return
        self.args = args;
        
        ## Emulate termial capabilities
        if   self.__test_nfdnf('-X'):  (self.linuxvt, self.usekms) = (False, False)
        elif self.__test_nfdnf('-V'):  (self.linuxvt, self.usekms) = (True, False)
        elif self.__test_nfdnf('-K'):  (self.linuxvt, self.usekms) = (True, True)
        self.ponydirs      = self.vtponydirs      if self.linuxvt and not self.usekms else self.xponydirs
        self.extraponydirs = self.extravtponydirs if self.linuxvt and not self.usekms else self.extraxponydirs
        
        ## Variadic variants of -f, -q &c
        for sign in ('-', '+'):
            for letter in ('f', 'F', 'q', 'Q'):
                ssl = sign + sign + letter
                sl = sign + letter
                if (ssl in args.opts) and (args.opts[ssl] is not None):
                    if args.opts[sl] is not None:  args.opts[sl] += args.opts[ssl]
                    else:                          args.opts[sl]  = args.opts[ssl]
        
        ## Save whether standard or extra ponies are used
        self.usingstandard = self.__test_nfdnf('-f', '-F', '-q') # -Q
        self.usingextra    = self.__test_nfdnf('+f', '-F') # +q -Q
        
        ## Run modes
        if   self.__test_nfdnf('-h'):                                     args.help()
        elif self.__test_nfdnf('+h'):                                     args.help(True)
        elif self.__test_nfdnf('-v'):                                     self.version()
        elif self.__test_nfdnf('--quoters'):                              self.quoters(True, False)
        elif self.__test_nfdnf('--Onelist', ('--onelist', '++onelist')):  self.onelist(True, True)
        elif self.__test_nfdnf('--onelist'):                              self.onelist(True, False)
        elif self.__test_nfdnf('++onelist'):                              self.onelist(False, True)
        elif self.__test_nfdnf('+A', ('-L', '+L')):                       self.linklist(); self.__extraponies(); self.linklist()
        elif self.__test_nfdnf('-A', ('-l', '+l')):                       self.list(); self.__extraponies(); self.list()
        elif self.__test_nfdnf('-L'):                                     self.linklist()
        elif self.__test_nfdnf('-l'):                                     self.list()
        elif self.__test_nfdnf('+L'):                                     self.__extraponies(); self.linklist()
        elif self.__test_nfdnf('+l'):                                     self.__extraponies(); self.list()
        elif self.__test_nfdnf('-B'):                                     self.balloonlist()
        else:
            self.__run()
    
    
    def __test_nfdnf(self, *keys):
        '''
        Test arguments written in negation-free disjunctive normal form
        
        @param   keys:*(str|itr<str>)  A list of keys and set of keys, any of which must exists, a set of keys only passes if all of those exists
        @return  :bool                 Whether the check passed
        '''
        for key in keys:
            if isinstance(key, str):
                if self.args.opts[key] is not None:
                    return True
            else:
                for skey in key:
                    if self.args.opts[skey] is None:
                        return False
                return True
        return False
    
    
    def __run(self):
        '''
        Run the important part of the program, the pony
        '''
        ## Colouring features
        if self.__test_nfdnf('--colour-pony'):
            self.mode += '\033[' + ';'.join(args.opts['--colour-pony']) + 'm'
        else:
            self.mode += '\033[0m'
        if self.__test_nfdnf('+c'):
            for part in ('msg', 'link', 'bubble'):
                if self.args.opts['--colour-' + part] is None:
                    self.args.opts['--colour-' + part] = self.args.opts['+c']
        
        ## Other extra features
        self.__bestpony(self.args)
        self.__ucsremap(self.args)
        if self.__test_nfdnf('-o'):
            self.mode += '$/= $$\\= $'
            self.args.message = ''
            self.ponyonly = True
        else:
            self.ponyonly = False
        if self.__test_nfdnf('-i', '+i'):
            self.args.message = ''
        self.restriction = self.args.opts['-r']
        
        ## The stuff
        if not self.unrecognised:
            self.printPony(self.args)
        else:
            self.args.help()
            exit(255)
    
    
    
    ##############################################
    ## Methods that run before the mane methods ##
    ##############################################
    
    def __extraponies(self):
        '''
        Use extra ponies
        '''
        ## Change ponydir to extraponydir
        self.ponydirs[:] = self.extraponydirs
        self.quotedirs[:] = [] ## TODO +q
    
    
    def __bestpony(self, args):
        '''
        Use best.pony if nothing else is set
        
        @param  args:ArgParser     Parsed command line arguments
        '''
        ## Set best.pony as the pony to display if none is selected
        def test(keys, strict):
            if strict:
                for key in keys:
                    if (args.opts[key] is not None) and (len(args.opts[key]) != 0):
                        return False
            else:
                for key in keys:
                    if args.opts[key] is not None:
                        return False
            return True
        keys = ['-f', '+f', '-F', '-q'] ## TODO +q -Q
        if test(keys, False):
            for ponydir in self.ponydirs:
                if os.path.isfile(ponydir + 'best.pony') or os.path.islink(ponydir + 'best.pony'):
                    pony = os.path.realpath(ponydir + 'best.pony') # Canonical path
                    if test(keys, True):
                        args.opts['-f'] = [pony]
                    else:
                        for key in keys:
                            if test(key, True):
                                args.opts[key] = [pony]
                    break
    
    
    def __ucsremap(self, args):
        '''
        Apply pony name remapping to args according to UCS settings
        
        @param  args:ArgParser  Parsed command line arguments
        '''
        ## Read UCS configurations
        env_ucs = os.environ['PONYSAY_UCS_ME'] if 'PONYSAY_UCS_ME' in os.environ else ''
        ucs_conf = 0
        if   env_ucs in ('yes',    'y', '1'):  ucs_conf = 1
        elif env_ucs in ('harder', 'h', '2'):  ucs_conf = 2
        
        ## Stop UCS is not used
        if ucs_conf == 0:
            return
        
        ## Read all lines in all UCS → ASCII map files
        maplines = []
        for ucsmap in self.ucsmaps:
            if os.path.isfile(ucsmap):
                with open(ucsmap, 'rb') as mapfile:
                    maplines += [line.replace('\n', '') for line in mapfile.read().decode('utf8', 'replace').split('\n')]
        
        ## Create UCS → ASCII mapping from read lines
        map = {}
        stripset = ' \t' # must be string, wtf! and way doesn't python's doc say so
        for line in maplines:
            if (len(line) > 0) and not (line[0] == '#'):
                s = line.index('→')
                ucs   = line[:s]    .strip(stripset)
                ascii = line[s + 1:].strip(stripset)
                map[ucs] = ascii
        
        ## Apply UCS → ASCII mapping to -f, +f, -F and -q arguments
        for flag in ('-f', '+f', '-F', '-q'): ## TODO +q -Q
            if args.opts[flag] is not None:
                for i in range(0, len(args.opts[flag])):
                    if args.opts[flag][i] in map:
                        args.opts[flag][i] = map[args.opts[flag][i]]
    
    
    #######################
    ## Auxiliary methods ##
    #######################
    
    def __ucsise(self, ponies, links = None):
        '''
        Apply UCS:ise pony names according to UCS settings
        
        @param  ponies:list<str>      List of all ponies (of interrest)
        @param  links:map<str, str>?  Map to fill with simulated symlink ponies, may be `None`
        '''
        ## Read UCS configurations
        env_ucs = os.environ['PONYSAY_UCS_ME'] if 'PONYSAY_UCS_ME' in os.environ else ''
        ucs_conf = 0
        if   env_ucs in ('yes',    'y', '1'):  ucs_conf = 1
        elif env_ucs in ('harder', 'h', '2'):  ucs_conf = 2
        
        ## Stop UCS is not used
        if ucs_conf == 0:
            return
        
        ## Read all lines in all UCS → ASCII map files
        maplines = []
        for ucsmap in self.ucsmaps:
            if os.path.isfile(ucsmap):
                with open(ucsmap, 'rb') as mapfile:
                    maplines += [line.replace('\n', '') for line in mapfile.read().decode('utf8', 'replace').split('\n')]
        
        ## Create UCS → ASCII mapping from read lines
        map = {}
        stripset = ' \t' # must be string, wtf! and way doesn't python's doc say so
        for line in maplines:
            if not line.startswith('#'):
                s = line.index('→')
                ucs   = line[:s]    .strip(stripset)
                ascii = line[s + 1:].strip(stripset)
                map[ascii] = ucs
        
        ## Apply UCS → ASCII mapping to ponies, by alias if weak settings
        if ucs_conf == 1:
            for pony in ponies:
                if pony in map:
                    ponies.append(map[pony])
                    if links is not None:
                        links[map[pony]] = pony
        else:
            for j in range(0, len(ponies)):
                if ponies[j] in map:
                    ponies[j] = map[ponies[j]]
    
    
    def __getPony(self, selection, args, alt = False):
        '''
        Returns one file with full path and ponyquote that should be used, names is filter for names, also accepts filepaths
        
        @param   selection:(name:str, dirfiles:itr<str>, quote:bool)?  Parsed command line arguments as name–directories–quoting tubles:
                                                                           name:      The pony name
                                                                           dirfiles:  Files, with the directory, in the pony directories
                                                                           quote:     Whether to use ponyquotes
        @param   args:ArgParser                                        Parsed command line arguments
        @param   alt:bool                                              For method internal use...
        @return  (path, quote):(str, str?)                             The file name of a pony, and the ponyquote that should be used if any
        '''
        ## If there is no selected ponies, choose all of them
        if (selection is None) or (len(selection) == 0):
            selection = [self.__selectAnypony(args)]
        
        ## Select a random pony of the choosen ones
        pony = selection[random.randrange(0, len(selection))]
        if os.path.exists(pony[0]):
            ponyname = pony[0].split(os.sep)[-1]
            if os.extsep in ponyname:
                ponyname = ponyname[:ponyname.rfind(os.extsep)]
            return (pony[0], self.__getQuote(ponyname, pony[0]) if pony[2] else None)
        else:
            possibilities = [f.split(os.sep)[-1][:-5] for f in pony[1]]
            if pony[0] not in possibilities:
                if not alt:
                    autocorrect = SpelloCorrecter(possibilities)
                    (alternatives, dist) = autocorrect.correct(pony[0])
                    limit = os.environ['PONYSAY_TYPO_LIMIT'] if 'PONYSAY_TYPO_LIMIT' in os.environ else ''
                    limit = 5 if len(limit) == 0 else int(limit)
                    if (len(alternatives) > 0) and (dist <= limit):
                        (_, files, quote) = pony
                        return self.__getPony([(a, files, quote) for a in alternatives], True)
                printerr('I have never heard of anypony named %s' % pony[0]);
                if not self.usingstandard:
                    printerr('Use -f/-q or -F if it a MLP:FiM pony');
                if not self.usingextra:
                    printerr('Have you tested +f or -F?');
                exit(252)
            else:
                file = pony[1][possibilities.index(pony[0])]
                return (file, self.__getQuote(pony[0], file) if pony[2] else None)
    
    
    def __selectAnypony(self, args):
        '''
        Randomly select a pony from all installed ponies
        
        @param   args:ArgParser                                 Parsed command line arguments
        @return  (name, dirfile, quote):(str, list<str>, bool)  The pony name, pony file with the directory, and whether to use ponyquotes
        '''
        quote    =  args.opts['-q'] is not None ## TODO +q -Q
        standard = (args.opts['-f'] is not None) or (args.opts['-F'] is not None) or (args.opts['-q'] is not None) ## TODO -Q
        extra    = (args.opts['+f'] is not None) or (args.opts['-F'] is not None) ## TODO +q -Q
        if not (standard or extra):
            standard = True
        ponydirs = (self.ponydirs if standard else []) + (self.extraponydirs if extra else []);
        quoters  = self.__quoters() if standard and quote else None ## TODO +q -Q
        if (quoters is not None) and (len(quoters) == 0):
            printerr('Princess Celestia! All the ponies are mute!')
            exit(250)
        
        ## Get all ponies, with quotes
        oldponies = {}
        self.__getAllPonies(standard, extra, oldponies, quoters)
        
        ## Apply restriction
        ponies = self.__applyRestriction(oldponies, ponydirs)
        
        ## Select one pony and set all information
        names = list(ponies.keys())
        if len(names) == 0:
            printerr('All the ponies are missing, call the Princess!')
            exit(249)
        pony = names[random.randrange(0, len(names))]
        return (pony, [ponies[pony]], quote)
    
    
    def __getAllPonies(self, standard, extra, collection, quoters):
        '''
        Get ponies for a set of directories
        
        @param  standard:bool              Whether to include standard ponies
        @parma  extra:bool                 Whether to include extra ponies
        @param  collection:dict<str, str>  Collection of already found ponies, and collection for new ponies, maps to the pony file
        @param  quoters:set<str>?          Ponies to limit to, or `None` to include all ponies
        '''
        if standard:
            self.__getPonies(self.ponydirs, collection, quoters)
        if extra:
            self.__getPonies(self.extraponydirs, collection, quoters)
    
    
    def __getPonies(self, directories, collection, quoters):
        '''
        Get ponies for a set of directories
        
        @param  directories:list<str>      Directories with ponies
        @param  collection:dict<str, str>  Collection of already found ponies, and collection for new ponies, maps to the pony file
        @param  quoters:set<str>?          Ponies to limit to, or `None` to include all ponies
        '''
        for ponydir in directories:
            for ponyfile in os.listdir(ponydir):
                if endswith(ponyfile, '.pony'):
                    pony = ponyfile[:-5]
                    if (pony not in collection) and ((quoters is None) or (pony in quoters)):
                        collection[pony] = ponydir + ponyfile
    
    
    def __applyRestriction(self, oldponies, ponydirs):
        '''
        Restrict ponies
        
        @param   oldponies:dict<str, str>  Collection of original ponies, maps to pony file
        @param   ponydirs:list<sr>         List of pony directories
        @return  :dict<str, str>           Map from restricted ponies to pony files
        '''
        ## Apply metadata restriction
        if self.restriction is not None:
            ponies = {}
            self.__applyMetadataRestriction(ponies, oldponies, ponydirs)
            if len(ponies) > 0:
                oldponies = ponies
            
        ## Apply dimension restriction
        ponies = {}
        self.__applyDimensionRestriction(ponies, oldponies, ponydirs)
        if len(ponies) > 0:
            oldponies = ponies
        
        return oldponies
    
    
    def __applyMetadataRestriction(self, ponies, oldponies, ponydirs):
        '''
        Restrict to ponies by metadata
        
        @param  ponies:dict<str, str>     Collection to fill with restricted ponies, mapped to pony file
        @param  oldponies:dict<str, str>  Collection of original ponies, maps to pony file
        @param  ponydirs:list<sr>         List of pony directories
        '''
        logic = Metadata.makeRestrictionLogic(self.restriction)
        for ponydir in ponydirs:
            for pony in Metadata.restrictedPonies(ponydir, logic):
                if (pony in oldponies) and not (pony in ponies):
                    ponies[pony] = ponydir + pony + '.pony'
    
    
    def __applyDimensionRestriction(self, ponies, oldponies, ponydirs):
        '''
        Restrict to ponies by dimension
        
        @param  ponies:dict<str, str>     Collection to fill with restricted ponies, mapped to pony file
        @param  oldponies:dict<str, str>  Collection of original ponies, maps to pony file
        @param  ponydirs:list<sr>         List of pony directories
        '''
        (termh, termw) = gettermsize()
        for ponydir in ponydirs:
            (fitw, fith) = (None, None)
            if os.path.exists(ponydir + 'widths'):
                fitw = set()
                with open(ponydir + 'widths', 'rb') as file:
                    Metadata.getFitting(fitw, termw, file)
            if os.path.exists(ponydir + ('onlyheights' if self.ponyonly else 'heights')):
                fith = set()
                with open(ponydir + ('onlyheights' if self.ponyonly else 'heights'), 'rb') as file:
                    Metadata.getFitting(fith, termh, file)
            for ponyfile in oldponies.values():
                if ponyfile.startswith(ponydir):
                    pony = ponyfile[len(ponydir) : -5]
                    if (fitw is None) or (pony in fitw):
                        if (fith is None) or (pony in fith):
                            ponies[pony] = ponyfile
    
    
    def __getQuote(self, pony, file):
        '''
        Select a quote for a pony
        
        @param   pony:str  The pony name
        @param   file:str  The pony's file name
        @return  :str      A quote from the pony, with a failure fall back message
        '''
        quote = []
        if (os.path.dirname(file) + os.sep).replace(os.sep + os.sep, os.sep) in self.ponydirs:
            realpony = pony
            if os.path.islink(file):
                realpony = os.path.basename(os.path.realpath(file))
                if os.extsep in realpony:
                    realpony = realpony[:realpony.rfind(os.extsep)]
            quote = self.__quotes(ponies = [realpony])
        if len(quote) == 0:
            quote = 'Zecora! Help me, I am mute!'
        else:
            quote = quote[random.randrange(0, len(quote))][1]
            printinfo('quote file: ' + quote)
            with open(quote, 'rb') as qfile:
                quote = qfile.read().decode('utf8', 'replace').strip()
        return quote
    
    
    def __quoters(self, ponydirs = None, quotedirs = None):
        '''
        Returns a set with all ponies that have quotes and are displayable
        
        @param   ponydirs:itr<str>?   The pony directories to use
        @param   quotedirs:itr<str>?  The quote directories to use
        @return  :set<str>            All ponies that have quotes and are displayable
        '''
        if ponydirs  is None:  ponydirs  = self.ponydirs
        if quotedirs is None:  quotedirs = self.quotedirs
        
        ## List all unique quote files
        quotes = []
        quoteshash = set()
        _quotes = []
        for quotedir in quotedirs:
            _quotes += [item[:item.index('.')] for item in os.listdir(quotedir)]
        for quote in _quotes:
            if not quote == '':
                if not quote in quoteshash:
                    quoteshash.add(quote)
                    quotes.append(quote)
        
        ## Create a set of all ponies that have quotes
        ponies = set()
        for ponydir in ponydirs:
            for pony in os.listdir(ponydir):
                if not pony[0] == '.':
                    p = pony[:-5] # remove .pony
                    for quote in quotes:
                        if ('+' + p + '+') in ('+' + quote + '+'):
                            if not p in ponies:
                                ponies.add(p)
        
        return ponies
    
    
    def __quotes(self, ponydirs = None, quotedirs = None, ponies = None):
        '''
        Returns a list with all (pony, quote file) pairs
        
        @param   ponydirs:itr<str>?        The pony directories to use
        @param   quotedirs:itr<str>?       The quote directories to use
        @param   ponies:itr<str>?          The ponies to use
        @return  (pony, quote):(str, str)  All ponies–quote file-pairs
        '''
        if ponydirs  is None:  ponydirs  = self.ponydirs
        if quotedirs is None:  quotedirs = self.quotedirs
        
        ## Get all ponyquote files
        quotes = []
        for quotedir in quotedirs:
            quotes += [quotedir + item for item in os.listdir(quotedir)]
        
        ## Create list of all pony–quote file-pairs
        rc = []
        if ponies is None:
            for ponydir in ponydirs:
                for pony in os.listdir(ponydir):
                    if endswith(pony, '.pony'):
                        p = pony[:-5] # remove .pony
                        for quote in quotes:
                            q = quote[quote.rindex('/') + 1:]
                            q = q[:q.rindex('.')]
                            if ('+' + p + '+') in ('+' + q + '+'):
                                rc.append((p, quote))
        else:
            for p in ponies:
                for quote in quotes:
                    q = quote[quote.rindex('/') + 1:]
                    q = q[:q.rindex('.')]
                    if ('+' + p + '+') in ('+' + q + '+'):
                        rc.append((p, quote))
        
        return rc
    
    
    
    #####################
    ## Listing methods ##
    #####################
    
    def list(self, ponydirs = None):
        '''
        Lists the available ponies
        
        @param  ponydirs:itr<str>?  The pony directories to use
        '''
        List.simplelist(self.ponydirs if ponydirs is None else ponydirs,
                        self.__quoters(), lambda x : self.__ucsise(x))
    
    
    def linklist(self, ponydirs = None):
        '''
        Lists the available ponies with alternatives inside brackets
        
        @param  ponydirs:itr<str>  The pony directories to use
        '''
        List.linklist(self.ponydirs if ponydirs is None else ponydirs,
                      self.__quoters(), lambda x, y : self.__ucsise(x, y))
    
    
    def onelist(self, standard = True, extra = False):
        '''
        Lists the available ponies on one column without anything bold or otherwise formated
        
        @param  standard:bool  Include standard ponies
        @param  extra:bool     Include extra ponies
        '''
        List.onelist(self.ponydirs if standard else None,
                     self.extraponydirs if extra else None,
                     lambda x : self.__ucsise(x))
    
    
    def quoters(self, standard = True, extra = False):
        '''
        Lists with all ponies that have quotes and are displayable, on one column without anything bold or otherwise formated
        
        @param  standard:bool  Include standard ponies
        @param  extra:bool     Include extra ponies
        '''
        ## Get all quoters
        ponies = list(self.__quoters()) if standard else []
        
        ## And now the extra ponies
        if extra:
            self.__extraponies()
            ponies += list(self.__quoters())
        
        ## UCS:ise here
        self.__ucsise(ponies)
        ponies.sort()
        
        ## Print each one on a seperate line, but skip duplicates
        last = ''
        for pony in ponies:
            if not pony == last:
                last = pony
                print(pony)
    
    
    
    #####################
    ## Balloon methods ##
    #####################
    
    def balloonlist(self):
        '''
        Prints a list of all balloons
        '''
        List.balloonlist(self.balloondirs, self.isthink)
    
    
    def __getBalloonPath(self, names, alt = False):
        '''
        Returns one file with full path, names is filter for style names, also accepts filepaths
        
        @param  names:list<str>  Balloons to choose from, may be `None`
        @param  alt:bool         For method internal use
        @param  :str             The file name of the balloon, will be `None` iff `names` is `None`
        '''
        ## Stop if there is no choosen balloon
        if names is None:
            return None
        
        ## Get all balloons
        balloons = {}
        for balloondir in self.balloondirs:
            for balloon in os.listdir(balloondir):
                balloonfile = balloon
                ## Use .think if running ponythink, otherwise .say
                if self.isthink and endswith(balloon, '.think'):
                    balloon = balloon[:-6]
                elif (not self.isthink) and endswith(balloon, '.say'):
                    balloon = balloon[:-4]
                else:
                    continue
                
                ## Add the balloon if there is none with the same name
                if balloon not in balloons:
                    balloons[balloon] = balloondir + balloonfile
        
        ## Support for explicit balloon file names
        for name in names:
            if os.path.exists(name):
                balloons[name] = name
        
        ## Select a random balloon of the choosen ones
        balloon = names[random.randrange(0, len(names))]
        if balloon not in balloons:
            if not alt:
                autocorrect = SpelloCorrecter(self.balloondirs, '.think' if self.isthink else '.say')
                (alternatives, dist) = autocorrect.correct(balloon)
                limit = os.environ['PONYSAY_TYPO_LIMIT'] if 'PONYSAY_TYPO_LIMIT' in os.environ else ''
                limit = 5 if len(limit) == 0 else int(limit)
                if (len(alternatives) > 0) and (dist <= limit):
                    return self.__getBalloonPath(alternatives, True)
            printerr('That balloon style %s does not exist' % balloon)
            exit(251)
        else:
            return balloons[balloon]
    
    
    def __getBalloon(self, balloonfile):
        '''
        Creates the balloon style object
        
        @param   balloonfile:str  The file with the balloon style, may be `None`
        @return  :Balloon         Instance describing the balloon's style
        '''
        return Balloon.fromFile(balloonfile, self.isthink)
    
    
    
    ########################
    ## Displaying methods ##
    ########################
    
    def version(self):
        '''
        Prints the name of the program and the version of the program
        '''
        ## Prints the "ponysay $VERSION", if this is modified, ./dev/dist.sh must be modified accordingly
        print('%s %s' % ('ponysay', VERSION))
    
    
    def printPony(self, args):
        '''
        Print the pony with a speech or though bubble. message, pony and wrap from args are used.
        
        @param  args:ArgParser  Parsed command line arguments
        '''
        ## Get the pony
        selection = []
        self.__getSelectedPonies(args, selection)
        (pony, quote) = self.__getPony(selection, args)
        
        ## Get message and manipulate it
        msg = self.__getMessage(args, quote)
        msg = self.__colouriseMessage(args, msg)
        msg = self.__compressMessage(args, msg)
        
        ## Print info
        printinfo('pony file: ' + pony)
        
        ## Use PNG file as pony file
        pony = self.__useImage(pony)
        
        ## If KMS is utilies, select a KMS pony file and create it if necessary
        pony = KMS.kms(pony, self.HOME, self.linuxvt)
        
        ## If in Linux VT clean the terminal (See info/pdf-manual [Printing in TTY with KMS])
        if self.linuxvt:
            print('\033[H\033[2J', end='')
        
        ## Get width truncation and wrapping
        widthtruncation = self.__getWidthTruncation()
        messagewrap = self.__getMessageWrap(args)
        
        ## Get balloon object
        balloonfile = self.__getBalloonPath(args.opts['-b'] if args.opts['-b'] is not None else None)
        printinfo('balloon style file: ' + str(balloonfile))
        balloon = self.__getBalloon(balloonfile) if args.opts['-o'] is None else None
        
        ## Get hyphen style
        hyphen = self.__getHyphen(args)
        
        ## Link and balloon colouring
        linkcolour = self.__getLinkColour(args)
        ballooncolour = self.__getBalloonColour(args)
        
        ## Determine --info/++info settings
        minusinfo = args.opts['-i'] is not None
        plusinfo  = args.opts['+i'] is not None
        
        ## Run cowsay replacement
        backend = Backend(message = msg, ponyfile = pony, wrapcolumn = messagewrap, width = widthtruncation, balloon = balloon,
                          hyphen = hyphen, linkcolour = linkcolour, ballooncolour = ballooncolour, mode = self.mode,
                          infolevel = 2 if plusinfo else (1 if minusinfo else 0))
        backend.parse()
        output = backend.output
        if output.endswith('\n'):
            output = output[:-1]
        
        ## Print the output, truncated on the height
        self.__printOutput(output)
    
    
    def __getSelectedPonies(self, args, selection):
        '''
        Get all selected ponies
        
        @param  args:ArgParser                                     Command line options
        @param  selection:list<(name:str, file:str, quotes:bool)>  List to fill with tuples of selected pony names, pony files and whether quotes are used
        '''
        (standard, extra) = ([], [])
        for ponydir in self.ponydirs:
            for pony in os.listdir(ponydir):
                if endswith(pony, '.pony'):
                    standard.append(ponydir + pony)
        for ponydir in self.extraponydirs:
            for pony in os.listdir(ponydir):
                if endswith(pony, '.pony'):
                    extra.append(ponydir + pony)
        both = standard + extra
        for (opt, ponies, quotes) in [('-f', standard, False), ('+f', extra, False), ('-F', both, False), ('-q', standard, True)]: ## TODO +q -Q
            if args.opts[opt] is not None:
                for pony in args.opts[opt]:
                    selection.append((pony, ponies, quotes))
    
    
    def __getMessage(self, args, quote):
        '''
        Get message and remove tailing whitespace from stdin (but not for each line)
        
        @param   args:ArgParser  Command line options
        @param   quote:str?      The quote, or `None` if none
        @return  :str            The message
        '''
        if quote is not None:
            return quote
        if args.message is None:
            return ''.join(sys.stdin.readlines()).rstrip()
        return args.message
    
    
    def __colouriseMessage(self, args, msg):
        '''
        Colourise message if option is set
        
        @param   args:ArgParser  Command line options
        @param   msg:str         The message
        @return  :str            The message colourised
        '''
        if args.opts['--colour-msg'] is not None:
            msg = '\033[' + ';'.join(args.opts['--colour-msg']) + 'm' + msg
        return msg
    
    
    def __compressMessage(self, args, msg):
        '''
        This algorithm should give some result as cowsay's, if option is set
        
        @param   args:ArgParser  Command line options
        @param   msg:str         The message
        @return  :str            The message compressed
        '''
        if args.opts['-c'] is None:
            return msg
        buf = ''
        last = ' '
        CHARS = '\t \n'
        for c in msg:
            if (c in CHARS) and (last in CHARS):
                if last == '\n':
                    buf += last
                last = c
            else:
                buf += c
                last = c
        msg = buf.strip(CHARS)
        buf = ''
        for c in msg:
            if (c != '\n') or (last != '\n'):
                buf += c
                last = c
        return buf.replace('\n', '\n\n')
    
    
    def __useImage(self, pony):
        '''
        Convert image to the ponysay format if it is a regular image
        
        @param   pony:str  The pony file
        @return  :str      The new pony file, or the old if it was already in the ponysay format
        '''
        if endswith(pony.lower(), '.png'):
            pony = '\'' + pony.replace('\'', '\'\\\'\'') + '\''
            pngcmd = 'ponytool --import image --file %s --balloon n --export ponysay --platform %s --balloon y'
            pngcmd %= (pony, ('linux' if self.linuxvt else 'xterm')) # XXX xterm should be haiku in Haiku
            pngpipe = os.pipe()
            Popen(pngcmd, stdout=os.fdopen(pngpipe[1], 'w'), shell=True).wait()
            pony = '/proc/' + str(os.getpid()) + '/fd/' + str(pngpipe[0])
        return pony
    
    
    def __getWidthTruncation(self):
        '''
        Gets the width trunction setting
        
        @return  :int?  The column the truncate the output at, or `None` to not truncate it
        '''
        env_width = os.environ['PONYSAY_FULL_WIDTH'] if 'PONYSAY_FULL_WIDTH' in os.environ else None
        if env_width is None:  env_width = 'auto'
        return gettermsize()[1] if env_width not in ('yes', 'y', '1') else None
    
    
    def __getMessageWrap(self, args):
        '''
        Gets the message balloon wrapping column
        
        @param   args:ArgParser  Command line options
        @return  :int?           The message balloon wrapping column, or `None` if disabled
        '''
        messagewrap = 65
        if (args.opts['-W'] is not None) and (len(args.opts['-W'][0]) > 0):
            messagewrap = args.opts['-W'][0]
            if messagewrap[0] in 'nmsNMS': # m is left to n on QWERTY and s is left to n on Dvorak
                messagewrap = None
            elif messagewrap[0] in 'iouIOU': # o is left to i on QWERTY and u is right to i on Dvorak
                messagewrap = gettermsize()[1]
            else:
                messagewrap = int(args.opts['-W'][0])
        return messagewrap
    
    
    def __getHyphen(self, args):
        '''
        Gets the hyphen to use a at hyphenation
        
        @param   args:ArgParser  Command line options
        @return  :str            The hyphen string to use at hyphenation
        '''
        hyphen = os.environ['PONYSAY_WRAP_HYPHEN'] if 'PONYSAY_WRAP_HYPHEN' in os.environ else None
        if (hyphen is None) or (len(hyphen) == 0):
            hyphen = '-'
        hyphencolour = ''
        if args.opts['--colour-wrap'] is not None:
            hyphencolour = '\033[' + ';'.join(args.opts['--colour-wrap']) + 'm'
        return '\033[31m' + hyphencolour + hyphen
    
    
    def __getLinkColour(self, args):
        '''
        Gets the colour of balloon links
        
        @param   args:ArgParser  Command line options
        @return  :str            The colour of balloon links
        '''
        linkcolour = ''
        if args.opts['--colour-link'] is not None:
            linkcolour = '\033[' + ';'.join(args.opts['--colour-link']) + 'm'
        return linkcolour
    
    
    def __getBalloonColour(self, args):
        '''
        Gets the colour of balloons
        
        @param   args:ArgParser  Command line options
        @return  :str            The colour of balloons
        '''
        ballooncolour = ''
        if args.opts['--colour-bubble'] is not None:
            ballooncolour = '\033[' + ';'.join(args.opts['--colour-bubble']) + 'm'
        return ballooncolour
    
    
    def __printOutput(self, output):
        '''
        Print the output, but truncate it on the height
        
        @param  output:str  The output truncated on the width but not on the height
        '''
        ## Load height trunction settings
        env_bottom = os.environ['PONYSAY_BOTTOM'] if 'PONYSAY_BOTTOM' in os.environ else None
        if env_bottom is None:  env_bottom = ''
        
        env_height = os.environ['PONYSAY_TRUNCATE_HEIGHT'] if 'PONYSAY_TRUNCATE_HEIGHT' in os.environ else None
        if env_height is None:  env_height = ''
        
        env_lines = os.environ['PONYSAY_SHELL_LINES'] if 'PONYSAY_SHELL_LINES' in os.environ else None
        if (env_lines is None) or (env_lines == ''):  env_lines = '2'
        
        ## Print the output, truncated on height if so set
        lines = gettermsize()[0] - int(env_lines)
        if self.linuxvt or (env_height in ('yes', 'y', '1')):
            if env_bottom in ('yes', 'y', '1'):
                for line in output.split('\n')[: -lines]:
                    print(line)
            else:
                for line in output.split('\n')[: lines]:
                    print(line)
        else:
            print(output)


########NEW FILE########
__FILENAME__ = ponysaytool
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''

import os
import sys
from subprocess import Popen, PIPE

from argparser import *
from ponysay import *
from metadata import *


VERSION = 'dev'  # this line should not be edited, it is fixed by the build system
'''
The version of ponysay
'''



def print(text = '', end = '\n'):
    '''
    Hack to enforce UTF-8 in output (in the future, if you see anypony not using utf-8 in
    programs by default, report them to Princess Celestia so she can banish them to the moon)
    
    @param  text:str  The text to print (empty string is default)
    @param  end:str   The appendix to the text to print (line breaking is default)
    '''
    sys.stdout.buffer.write((str(text) + end).encode('utf-8'))

def printerr(text = '', end = '\n'):
    '''
    stderr equivalent to print()
    
    @param  text:str  The text to print (empty string is default)
    @param  end:str   The appendix to the text to print (line breaking is default)
    '''
    sys.stderr.buffer.write((str(text) + end).encode('utf-8'))



class PonysayTool():
    '''
    This is the mane class of ponysay-tool
    '''
    
    def __init__(self, args):
        '''
        Starts the part of the program the arguments indicate
        
        @param  args:ArgParser  Parsed command line arguments
        '''
        if args.argcount == 0:
            args.help()
            exit(255)
            return
        
        opts = args.opts
        
        if unrecognised or (opts['-h'] is not None) or (opts['+h'] is not None):
            args.help(True if opts['+h'] is not None else None)
            if unrecognised:
                exit(254)
        
        elif opts['-v'] is not None:
            print('%s %s' % ('ponysay-tool', VERSION))
        
        elif opts['--kms'] is not None:
            self.generateKMS()
        
        elif (opts['--dimensions'] is not None) and (len(opts['--dimensions']) == 1):
            self.generateDimensions(opts['--dimensions'][0], args.files)
        
        elif (opts['--metadata'] is not None) and (len(opts['--metadata']) == 1):
            self.generateMetadata(opts['--metadata'][0], args.files)
        
        elif (opts['-b'] is not None) and (len(opts['-b']) == 1):
            try:
                if opts['--no-term-init'] is None:
                    print('\033[?1049h', end='') # initialise terminal
                cmd = 'stty %s < %s > /dev/null 2> /dev/null'
                cmd %= ('-echo -icanon -echo -isig -ixoff -ixon', os.path.realpath('/dev/stdout'))
                Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).wait()
                print('\033[?25l', end='') # hide cursor
                dir = opts['-b'][0]
                if not dir.endswith(os.sep):
                    dir += os.sep
                self.browse(dir, opts['-r'])
            finally:
                print('\033[?25h', end='') # show cursor
                cmd = 'stty %s < %s > /dev/null 2> /dev/null'
                cmd %= ('echo icanon echo isig ixoff ixon', os.path.realpath('/dev/stdout'))
                Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).wait()
                if opts['--no-term-init'] is None:
                    print('\033[?1049l', end='') # terminate terminal
        
        elif (opts['--edit'] is not None) and (len(opts['--edit']) == 1):
            pony = opts['--edit'][0]
            if not os.path.isfile(pony):
                printerr('%s is not an existing regular file' % pony)
                exit(252)
            linuxvt = ('TERM' in os.environ) and (os.environ['TERM'] == 'linux')
            try:
                if opts['--no-term-init'] is None:
                    print('\033[?1049h', end='') # initialise terminal
                if linuxvt: print('\033[?8c', end='') # use full block for cursor (_ is used by default in linux vt)
                cmd = 'stty %s < %s > /dev/null 2> /dev/null'
                cmd %= ('-echo -icanon -echo -isig -ixoff -ixon', os.path.realpath('/dev/stdout'))
                Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).wait()
                self.editmeta(pony)
            finally:
                cmd = 'stty %s < %s > /dev/null 2> /dev/null'
                cmd %= ('echo icanon echo isig ixoff ixon', os.path.realpath('/dev/stdout'))
                Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE).wait()
                if linuxvt: print('\033[?0c', end='') # restore cursor
                if opts['--no-term-init'] is None:
                    print('\033[?1049l', end='') # terminate terminal
        
        elif (opts['--edit-rm'] is not None) and (len(opts['--edit-rm']) == 1):
            ponyfile = opts['--edit-rm'][0]
            pony = None
            with open(ponyfile, 'rb') as file:
                pony = file.read().decode('utf8', 'replace')
            if pony.startswith('$$$\n'):
                pony = pony[3:]
                pony = pony[pony.index('\n$$$\n') + 5:]
                with open(ponyfile, 'wb') as file:
                    file.write(pony.encode('utf8'))
        
        elif (opts['--edit-stash'] is not None) and (len(opts['--edit-stash']) == 1):
            ponyfile = opts['--edit-stash'][0]
            pony = None
            with open(ponyfile, 'rb') as file:
                pony = file.read().decode('utf8', 'replace')
            if pony.startswith('$$$\n'):
                pony = pony[3:]
                pony = pony[:pony.index('\n$$$\n')]
                print('$$$' + pony + '\n$$$\n', end='')
            else:
                print('$$$\n$$$\n', end='')
        
        elif (opts['--edit-apply'] is not None) and (len(opts['--edit-apply']) == 1):
            data = ''
            while True:
                line = input()
                if data == '':
                    if line != '$$$':
                        printerr('Bad stash')
                        exit(251)
                    data += '$$$\n'
                else:
                    data += line + '\n'
                    if line == '$$$':
                        break
            ponyfile = opts['--edit-apply'][0]
            pony = None
            with open(ponyfile, 'rb') as file:
                pony = file.read().decode('utf8', 'replace')
            if pony.startswith('$$$\n'):
                pony = pony[3:]
                pony = pony[pony.index('\n$$$\n') + 5:]
            with open(ponyfile, 'wb') as file:
                file.write((data + pony).encode('utf8'))
        
        else:
            args.help()
            exit(253)
    
    
    def execPonysay(self, args, message = ''):
        '''
        Execute ponysay!
        
        @param  args     Arguments
        @param  message  Message
        '''
        class PhonyArgParser():
            def __init__(self, args, message):
                self.argcount = len(args) + (0 if message is None else 1)
                for key in args:
                    self.argcount += len(args[key]) if (args[key] is not None) and isinstance(args[key], list) else 1
                self.message = message
                self.opts = self
            def __getitem__(self, key):
                if key in args:
                    return args[key] if (args[key] is not None) and isinstance(args[key], list) else [args[key]]
                return None
            def __contains__(self, key):
                return key in args;
        
        stdout = sys.stdout
        class StringInputStream():
            def __init__(self):
                self.buf = ''
                class Buffer():
                    def __init__(self, parent):
                        self.parent = parent
                    def write(self, data):
                        self.parent.buf += data.decode('utf8', 'replace')
                    def flush(self):
                        pass
                self.buffer = Buffer(self)
            def flush(self):
                pass
            def isatty(self):
                return True
        sys.stdout = StringInputStream()
        ponysay = Ponysay()
        ponysay.run(PhonyArgParser(args, message))
        out = sys.stdout.buf[:-1]
        sys.stdout = stdout
        return out
    
    
    def browse(self, ponydir, restriction):
        '''
        Browse ponies
        
        @param  ponydir:str            The pony directory to browse
        @param  restriction:list<str>  Restrictions on listed ponies, may be None
        '''
        ## Call `stty` to determine the size of the terminal, this way is better than using python's ncurses
        termsize = None
        for channel in (sys.stdout, sys.stdin, sys.stderr):
            termsize = Popen(['stty', 'size'], stdout=PIPE, stdin=channel, stderr=PIPE).communicate()[0]
            if len(termsize) > 0:
                termsize = termsize.decode('utf8', 'replace')[:-1].split(' ') # [:-1] removes a \n
                termsize = [int(item) for item in termsize]
                break
        (termh, termw) = termsize
        
        ponies = set()
        for ponyfile in os.listdir(ponydir):
            if endswith(ponyfile, '.pony'):
                ponyfile = ponyfile[:-5]
                if ponyfile not in ponies:
                    ponies.add(ponyfile)
        if restriction is not None:
            oldponies = ponies
            logic = Metadata.makeRestrictionLogic(restriction)
            ponies = set()
            for pony in Metadata.restrictedPonies(ponydir, logic):
                if (pony not in ponies) and (pony in oldponies):
                    ponies.add(pony)
            oldponies = ponies
        ponies = list(ponies)
        ponies.sort()
        
        if len(ponies) == 0:
            print('\033[1;31m%s\033[21m;39m' % 'No ponies... press Enter to exit.')
            input()
        
        panelw = Backend.len(max(ponies, key = Backend.len))
        panely = 0
        panelx = termw - panelw
        
        (x, y) = (0, 0)
        (oldx, oldy) = (None, None)
        (quotes, info) = (False, False)
        (ponyindex, oldpony) = (0, None)
        (pony, ponywidth, ponyheight) = (None, None, None)
        
        stored = None
        while True:
            printpanel = -2 if ponyindex != oldpony else oldpony
            if (ponyindex != oldpony):
                ponyindex %= len(ponies)
                if ponyindex < 0:
                    ponyindex += len(ponies)
                oldpony = ponyindex
                
                ponyfile = (ponydir + '/' + ponies[ponyindex] + '.pony').replace('//', '/')
                pony = self.execPonysay({'-f' : ponyfile, '-W' : 'none', '-o' : None}).split('\n')
                
                preprint = '\033[H\033[2J'
                if pony[0].startswith(preprint):
                    pony[0] = pony[0][len(preprint):]
                ponyheight = len(pony)
                ponywidth = Backend.len(max(pony, key = Backend.len))
                
                AUTO_PUSH = '\033[01010~'
                AUTO_POP  = '\033[10101~'
                pony = '\n'.join(pony).replace('\n', AUTO_PUSH + '\n' + AUTO_POP)
                colourstack = ColourStack(AUTO_PUSH, AUTO_POP)
                buf = ''
                for c in pony:
                    buf += c + colourstack.feed(c)
                pony = buf.replace(AUTO_PUSH, '').replace(AUTO_POP, '').split('\n')
            
            if (oldx != x) or (oldy != y):
                (oldx, oldy) = (x, y)
                print('\033[H\033[2J', end='')
                
                def getprint(pony, ponywidth, ponyheight, termw, termh, px, py):
                    ponyprint = pony
                    if py < 0:
                        ponyprint = [] if -py > len(ponyprint) else ponyprint[-py:]
                    elif py > 0:
                        ponyprint = py * [''] + ponyprint
                    ponyprint = ponyprint[:len(ponyprint) if len(ponyprint) < termh else termh]
                    def findcolumn(line, column):
                        if Backend.len(line) >= column:
                            return len(line)
                        pos = len(line)
                        while Backend.len(line[:pos]) != column:
                            pos -= 1
                        return pos
                    if px < 0:
                        ponyprint = [('' if -px > Backend.len(line) else line[findcolumn(line, -px):]) for line in ponyprint]
                    elif px > 0:
                        ponyprint = [px * ' ' + line for line in ponyprint]
                    ponyprint = [(line if Backend.len(line) <= termw else line[:findcolumn(line, termw)]) for line in ponyprint]
                    ponyprint = ['\033[21;39;49;0m%s\033[21;39;49;0m' % line for line in ponyprint]
                    return '\n'.join(ponyprint)
                
                if quotes:
                    ponyquotes = None # TODO
                    quotesheight = len(ponyquotes)
                    quoteswidth = Backend.len(max(ponyquotes, key = Backend.len))
                    print(getprint(ponyquotes, quoteswidth, quotesheight, termw, termh, x, y), end='')
                elif info:
                    ponyfile = (ponydir + '/' + ponies[ponyindex] + '.pony').replace('//', '/')
                    ponyinfo = self.execPonysay({'-f' : ponyfile, '-W' : 'none', '-i' : None}).split('\n')
                    infoheight = len(ponyinfo)
                    infowidth = Backend.len(max(ponyinfo, key = Backend.len))
                    print(getprint(ponyinfo, infowidth, infoheight, termw, termh, x, y), end='')
                else:
                    print(getprint(pony, ponywidth, ponyheight, panelx, termh, x + (panelx - ponywidth) // 2, y + (termh - ponyheight) // 2), end='')
                    printpanel = -1
            
            if printpanel == -1:
                cury = 0
                for line in ponies[panely:]:
                    cury += 1
                    if os.path.islink((ponydir + '/' + line + '.pony').replace('//', '/')):
                        line = '\033[34m%s\033[39m' % ((line + ' ' * panelw)[:panelw])
                    else:
                        line = (line + ' ' * panelw)[:panelw]
                    print('\033[%i;%iH\033[%im%s\033[0m' % (cury, panelx + 1, 1 if panely + cury - 1 == ponyindex else 0, line), end='')
            elif printpanel >= 0:
                for index in (printpanel, ponyindex):
                    cury = index - panely
                    if (0 <= cury) and (cury < termh):
                        line = ponies[cury + panely]
                        if os.path.islink((ponydir + '/' + line + '.pony').replace('//', '/')):
                            line = '\033[34m%s\033[39m' % ((line + ' ' * panelw)[:panelw])
                        else:
                            line = (line + ' ' * panelw)[:panelw]
                        print('\033[%i;%iH\033[%im%s\033[0m' % (cury, panelx + 1, 1 if panely + cury - 1 == ponyindex else 0, line), end='')
            
            sys.stdout.buffer.flush()
            if stored is None:
                d = sys.stdin.read(1)
            else:
                d = stored
                stored = None
            
            recenter = False
            if (d == 'w') or (d == 'W') or (d == '<') or (d == 'ä') or (d == 'Ä'): # pad ↑
                y -= 1
            elif (d == 's') or (d == 'S') or (d == 'o') or (d == 'O'): # pad ↓
                y += 1
            elif (d == 'd') or (d == 'D') or (d == 'e') or (d == 'E'): # pad →
                x += 1
            elif (d == 'a') or (d == 'A'): # pad ←
                x -= 1
            elif (d == 'q') or (d == 'Q'): # toggle quotes
                quotes = False if info else not quotes
                recenter = True
            elif (d == 'i') or (d == 'I'): # toggle metadata
                info = False if quotes else not info
                recenter = True
            elif ord(d) == ord('L') - ord('@'): # recenter
                recenter = True
            elif ord(d) == ord('P') - ord('@'): # previous
                ponyindex -= 1
                recenter = True
            elif ord(d) == ord('N') - ord('@'): # next
                ponyindex += 1
                recenter = True
            elif ord(d) == ord('Q') - ord('@'):
                break
            elif ord(d) == ord('X') - ord('@'):
                if ord(sys.stdin.read(1)) == ord('C') - ord('@'):
                    break
            elif d == '\033':
                d = sys.stdin.read(1)
                if d == '[':
                    d = sys.stdin.read(1)
                    if   d == 'A':  stored = chr(ord('P') - ord('@')) if (not quotes) and (not info) else 'W'
                    elif d == 'B':  stored = chr(ord('N') - ord('@')) if (not quotes) and (not info) else 'S'
                    elif d == 'C':  stored = chr(ord('N') - ord('@')) if (not quotes) and (not info) else 'D'
                    elif d == 'D':  stored = chr(ord('P') - ord('@')) if (not quotes) and (not info) else 'A'
                    elif d == '1':
                        if sys.stdin.read(1) == ';':
                            if sys.stdin.read(1) == '5':
                                d = sys.stdin.read(1)
                                if   d == 'A':  stored = 'W'
                                elif d == 'B':  stored = 'S'
                                elif d == 'C':  stored = 'D'
                                elif d == 'D':  stored = 'A'
            if recenter:
                (oldx, oldy) = (None, None)
                (x, y) = (0, 0)
    
    
    def generateKMS(self):
        '''
        Generate all kmsponies for the current TTY palette
        '''
        class PhonyArgParser():
            def __init__(self, key, value):
                self.argcount = 3
                self.message = ''
                self.opts = self
                self.key = key
                self.value = value
            def __getitem__(self, key):
                return [self.value] if key == self.key else None
            def __contains__(self, key):
                return key == self.key;
        
        class StringInputStream():
            def __init__(self):
                self.buf = ''
                class Buffer():
                    def __init__(self, parent):
                        self.parent = parent
                    def write(self, data):
                        self.parent.buf += data.decode('utf8', 'replace')
                    def flush(self):
                        pass
                self.buffer = Buffer(self)
            def flush(self):
                pass
            def isatty(self):
                return True
        
        stdout = sys.stdout
        term = os.environ['TERM']
        os.environ['TERM'] = 'linux'
        
        sys.stdout = StringInputStream()
        ponysay = Ponysay()
        ponysay.run(PhonyArgParser('--onelist', None))
        stdponies = sys.stdout.buf[:-1].split('\n')
        
        sys.stdout = StringInputStream()
        ponysay = Ponysay()
        ponysay.run(PhonyArgParser('++onelist', None))
        extraponies = sys.stdout.buf[:-1].split('\n')
        
        for pony in stdponies:
            printerr('Genering standard kmspony: %s' % pony)
            sys.stderr.buffer.flush();
            sys.stdout = StringInputStream()
            ponysay = Ponysay()
            ponysay.run(PhonyArgParser('--pony', pony))
        
        for pony in extraponies:
            printerr('Genering extra kmspony: %s' % pony)
            sys.stderr.buffer.flush();
            sys.stdout = StringInputStream()
            ponysay = Ponysay()
            ponysay.run(PhonyArgParser('++pony', pony))
        
        os.environ['TERM'] = term
        sys.stdout = stdout
    
    
    def generateDimensions(self, ponydir, ponies = None):
        '''
        Generate pony dimension file for a directory
        
        @param  ponydir:str        The directory
        @param  ponies:itr<str>?   Ponies to which to limit
        '''
        dimensions = []
        ponyset = None if (ponies is None) or (len(ponies) == 0) else set(ponies)
        for ponyfile in os.listdir(ponydir):
            if (ponyset is not None) and (ponyfile not in ponyset):
                continue
            if ponyfile.endswith('.pony') and (ponyfile != '.pony'):
                class PhonyArgParser():
                    def __init__(self, balloon):
                        self.argcount = 5
                        self.message = ''
                        self.pony = (ponydir + '/' + ponyfile).replace('//', '/')
                        self.balloon = balloon
                        self.opts = self
                    def __getitem__(self, key):
                        if key == '-f':
                            return [self.pony]
                        if key == ('-W' if self.balloon else '-b'):
                            return [('none' if self.balloon else None)]
                        return None
                    def __contains__(self, key):
                        return key in ('-f', '-W', '-b');
                stdout = sys.stdout
                class StringInputStream():
                    def __init__(self):
                        self.buf = ''
                        class Buffer():
                            def __init__(self, parent):
                                self.parent = parent
                            def write(self, data):
                                self.parent.buf += data.decode('utf8', 'replace')
                            def flush(self):
                                pass
                        self.buffer = Buffer(self)
                    def flush(self):
                        pass
                    def isatty(self):
                        return True
                sys.stdout = StringInputStream()
                ponysay = Ponysay()
                ponysay.run(PhonyArgParser(True))
                printpony = sys.stdout.buf[:-1].split('\n')
                ponyheight = len(printpony) - 2 # using fallback balloon
                ponywidth = Backend.len(max(printpony, key = Backend.len))
                ponysay = Ponysay()
                ponysay.run(PhonyArgParser(False))
                printpony = sys.stdout.buf[:-1].split('\n')
                ponyonlyheight = len(printpony)
                sys.stdout = stdout
                dimensions.append((ponywidth, ponyheight, ponyonlyheight, ponyfile[:-5]))
        (widths, heights, onlyheights) = ([], [], [])
        for item in dimensions:
            widths     .append((item[0], item[3]))
            heights    .append((item[1], item[3]))
            onlyheights.append((item[2], item[3]))
        for items in (widths, heights, onlyheights):
            sorted(items, key = lambda item : item[0])
        for pair in ((widths, 'widths'), (heights, 'heights'), (onlyheights, 'onlyheights')):
            (items, dimfile) = pair
            dimfile = (ponydir + '/' + dimfile).replace('//', '/')
            ponies = [item[1] for item in items]
            dims = []
            last = -1
            index = 0
            for item in items:
                cur = item[0]
                if cur != last:
                    if last >= 0:
                        dims.append((last, index))
                    last = cur
                index += 1
            if last >= 0:
                dims.append((last, index))
            dims = ''.join([('%i/%i/' % (dim[0], len('/'.join(ponies[:dim[1]])))) for dim in dims])
            data = '/' + str(len(dims)) + '/' + dims + '/'.join(ponies) + '/'
            with open(dimfile, 'wb') as file:
                file.write(data.encode('utf8'))
                file.flush()
    
    
    def generateMetadata(self, ponydir, ponies = None):
        '''
        Generate pony metadata collection file for a directory
        
        @param  ponydir:str       The directory
        @param  ponies:itr<str>?  Ponies to which to limit
        '''
        if not ponydir.endswith('/'):
            ponydir += '/'
        def makeset(value):
            rc = set()
            bracket = 0
            esc = False
            buf = ''
            for c in value:
                if esc:
                    if bracket == 0:
                        if c not in (',', '\\', '(', ')'):
                            buf += '\\'
                        buf += c
                    esc = False
                elif c == '(':
                    bracket += 1
                elif c == ')':
                    if bracket == 0:
                        raise Exception('Bracket mismatch')
                    bracket -= 1
                elif c == '\\':
                    esc = True
                elif bracket == 0:
                    if c == ',':
                        buf = buf.strip()
                        if len(buf) > 0:
                            rc.add(buf)
                        buf = ''
                    else:
                        buf += c
            if bracket > 0:
                raise Exception('Bracket mismatch')
            buf = buf.strip()
            if len(buf) > 0:
                rc.add(buf)
            return rc
        everything = []
        ponyset = None if (ponies is None) or (len(ponies) == 0) else set(ponies)
        for ponyfile in os.listdir(ponydir):
            if (ponyset is not None) and (ponyfile not in ponyset):
                continue
            if ponyfile.endswith('.pony') and (ponyfile != '.pony'):
                with open(ponydir + ponyfile, 'rb') as file:
                    data = file.read().decode('utf8', 'replace')
                    data = [line.replace('\n', '') for line in data.split('\n')]
                if data[0] != '$$$':
                    meta = []
                else:
                    sep = 1
                    while data[sep] != '$$$':
                        sep += 1
                    meta = data[1 : sep]
                data = {}
                for line in meta:
                    if ':' in line:
                        key = line[:line.find(':')].strip()
                        value = line[line.find(':') + 1:]
                        test = key
                        for c in 'ABCDEFGHIJKLMN OPQRSTUVWXYZ':
                            test = test.replace(c, '')
                        if (len(test) == 0) and (len(key) > 0):
                            vals = makeset(value.replace(' ', ''))
                            if key not in data:
                                data[key] = vals
                            else:
                                dset = data[key]
                                for val in vals:
                                    dset.add(val)
                everything.append((ponyfile[:-5], data))
        import pickle
        with open((ponydir + '/metadata').replace('//', '/'), 'wb') as file:
            pickle.dump(everything, file, -1)
            file.flush()
    
    
    def editmeta(self, ponyfile):
        '''
        Edit a pony file's metadata
        
        @param  ponyfile:str  A pony file to edit
        '''
        (data, meta, image) = 3 * [None]
        
        with open(ponyfile, 'rb') as file:
            data = file.read().decode('utf8', 'replace')
            data = [line.replace('\n', '') for line in data.split('\n')]
        
        if data[0] != '$$$':
            image = data
            meta = []
        else:
            sep = 1
            while data[sep] != '$$$':
                sep += 1
            meta = data[1 : sep]
            image = data[sep + 1:]
        
        
        class PhonyArgParser():
            def __init__(self):
                self.argcount = 5
                self.message = ponyfile
                self.opts = self
            def __getitem__(self, key):
                if key == '-f':  return [ponyfile]
                if key == '-W':  return ['n']
                return None
            def __contains__(self, key):
                return key in ('-f', '-W');
        
        
        data = {}
        comment = []
        for line in meta:
            if ': ' in line.replace('\t', ' '):
                key = line.replace('\t', ' ')
                key = key[:key.find(': ')]
                test = key
                for c in 'ABCDEFGHIJKLMN OPQRSTUVWXYZ':
                    test = test.replace(c, '')
                if (len(test) == 0) and (len(key.replace(' ', '')) > 0):
                    key = key.strip(' ')
                    value = line.replace('\t', ' ')
                    value = value[value.find(': ') + 2:]
                    if key not in data:
                        data[key] = value.strip(' ')
                    else:
                        data[key] += '\n' + value.strip(' ')
                else:
                    comment.append(line)
            else:
                comment.append(line)
        
        cut = 0
        while (len(comment) > cut) and (len(comment[cut]) == 0):
            cut += 1
        comment = comment[cut:]
        
        
        stdout = sys.stdout
        class StringInputStream():
            def __init__(self):
                self.buf = ''
                class Buffer():
                    def __init__(self, parent):
                        self.parent = parent
                    def write(self, data):
                        self.parent.buf += data.decode('utf8', 'replace')
                    def flush(self):
                        pass
                self.buffer = Buffer(self)
            def flush(self):
                pass
            def isatty(self):
                return True
        sys.stdout = StringInputStream()
        ponysay = Ponysay()
        ponysay.run(PhonyArgParser())
        printpony = sys.stdout.buf[:-1].split('\n')
        sys.stdout = stdout
        
        preprint = '\033[H\033[2J'
        if printpony[0].startswith(preprint):
            printpony[0] = printpony[0][len(preprint):]
        ponyheight = len(printpony) - len(ponyfile.split('\n')) + 1 - 2 # using fallback balloon
        ponywidth = Backend.len(max(printpony, key = Backend.len))
        
        ## Call `stty` to determine the size of the terminal, this way is better than using python's ncurses
        termsize = None
        for channel in (sys.stdout, sys.stdin, sys.stderr):
            termsize = Popen(['stty', 'size'], stdout=PIPE, stdin=channel, stderr=PIPE).communicate()[0]
            if len(termsize) > 0:
                termsize = termsize.decode('utf8', 'replace')[:-1].split(' ') # [:-1] removes a \n
                termsize = [int(item) for item in termsize]
                break
        
        AUTO_PUSH = '\033[01010~'
        AUTO_POP  = '\033[10101~'
        modprintpony = '\n'.join(printpony).replace('\n', AUTO_PUSH + '\n' + AUTO_POP)
        colourstack = ColourStack(AUTO_PUSH, AUTO_POP)
        buf = ''
        for c in modprintpony:
            buf += c + colourstack.feed(c)
        modprintpony = buf.replace(AUTO_PUSH, '').replace(AUTO_POP, '')
        
        printpony = [('\033[21;39;49;0m%s%s\033[21;39;49;0m' % (' ' * (termsize[1] - ponywidth), line)) for line in modprintpony.split('\n')]
        
        
        print(preprint, end='')
        print('\n'.join(printpony), end='')
        print('\033[H', end='')
        print('Please see the info manual for details on how to fill out this form')
        print()
        
        
        if 'WIDTH'  in data:  del data['WIDTH']
        if 'HEIGHT' in data:  del data['HEIGHT']
        data['comment'] = '\n'.join(comment)
        fields = [key for key in data]
        fields.sort()
        standardfields = ['GROUP NAME', 'NAME', 'OTHER NAMES', 'APPEARANCE', 'KIND',
                          'GROUP', 'BALLOON', 'LINK', 'LINK ON', 'COAT', 'MANE', 'EYE',
                          'AURA', 'DISPLAY', 'BALLOON TOP', 'BALLOON BOTTOM', 'MASTER',
                          'POSE', 'BASED ON', 'SOURCE', 'MEDIA', 'LICENSE', 'FREE',
                          'comment']
        for standard in standardfields:
            if standard in fields:
                del fields[fields.index(standard)]
            if standard not in data:
                data[standard] = ''
        
        fields = standardfields[:-1] + fields + [standardfields[-1]]
        
        def saver(ponyfile, ponyheight, ponywidth, data, image):
            class Saver():
                def __init__(self, ponyfile, ponyheight, ponywidth, data, image):
                    (self.ponyfile, self.ponyheight, self.ponywidth, self.data, self.image) = (ponyfile, ponyheight, ponywidth, data, image)
                def __call__(self): # functor
                    comment = self.data['comment']
                    comment = ('\n' + comment + '\n').replace('\n$$$\n', '\n\\$$$\n')[:-1]
                    
                    meta = []
                    keys = [key for key in data]
                    keys.sort()
                    for key in keys:
                        if self.data[key] is None:
                            continue
                        if (key == 'comment') or (len(self.data[key].strip()) == 0):
                            continue
                        values = self.data[key].strip()
                        for value in values.split('\n'):
                            meta.append(key + ': ' + value)
                    
                    meta.append('WIDTH: ' + str(self.ponywidth))
                    meta.append('HEIGHT: ' + str(self.ponyheight))
                    # TODO auto fill in BALLOON {TOP,BOTTOM}
                    meta.append(comment)
                    meta = '\n'.join(meta)
                    ponydata = '$$$\n' + meta + '\n$$$\n' + '\n'.join(self.image)
                    
                    with open(self.ponyfile, 'wb') as file:
                        file.write(ponydata.encode('utf8'))
                        file.flush()
            return Saver(ponyfile, ponyheight, ponywidth, data, image)
        
        textarea = TextArea(fields, data, 1, 3, termsize[1] - ponywidth, termsize[0] - 2, termsize)
        textarea.run(saver(ponyfile, ponyheight, ponywidth, data, image))



class TextArea(): # TODO support small screens  (This is being work on in GNU-Pony/featherweight)
    '''
    GNU Emacs alike text area
    '''
    def __init__(self, fields, datamap, left, top, width, height, termsize):
        '''
        Constructor
        
        @param  fields:list<str>       Field names
        @param  datamap:dist<str,str>  Data map
        @param  left:int               Left position of the component
        @param  top:int                Top position of the component
        @param  width:int              Width of the component
        @param  height:int             Height of the component
        @param  termsize:(int,int)     The height and width of the terminal
        '''
        (self.fields, self.datamap, self.left, self.top, self.width, self.height, self.termsize) \
        = (fields, datamap, left, top, width - 1, height, termsize)
    
    
    def run(self, saver):
        '''
        Execute text reading
        
        @param  saver  Save method
        '''
        innerleft = UCS.dispLen(max(self.fields, key = UCS.dispLen)) + self.left + 3
        
        leftlines = []
        datalines = []
        
        for key in self.fields:
            for line in self.datamap[key].split('\n'):
                leftlines.append(key)
                datalines.append(line)
        
        (termh, termw) = self.termsize
        (y, x) = (0, 0)
        mark = None
        
        KILL_MAX = 50
        killring = []
        killptr = None
        
        def status(text):
            print('\033[%i;%iH\033[7m%s\033[27m\033[%i;%iH' % (termh - 1, 1, ' (' + text + ') ' + '-' * (termw - len(' (' + text + ') ')), self.top + y, innerleft + x), end='')
        
        status('unmodified')
        
        print('\033[%i;%iH' % (self.top, innerleft), end='')
        
        def alert(text):
            if text is None:
                alert('')
            else:
                print('\033[%i;%iH\033[2K%s\033[%i;%iH' % (termh, 1, text, self.top + y, innerleft + x), end='')
        
        modified = False
        override = False
        
        (oldy, oldx, oldmark) = (y, x, mark)
        stored = chr(ord('L') - ord('@'))
        alerted = False
        edited = False
        print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
        while True:
            if (oldmark is not None) and (oldmark >= 0):
                if oldmark < oldx:
                    print('\033[%i;%iH\033[49m%s\033[%i;%iH' % (self.top + oldy, innerleft + oldmark, datalines[oldy][oldmark : oldx], self.top + y, innerleft + x), end='')
                elif oldmark > oldx:
                    print('\033[%i;%iH\033[49m%s\033[%i;%iH' % (self.top + oldy, innerleft + oldx, datalines[oldy][oldx : oldmark], self.top + y, innerleft + x), end='')
            if (mark is not None) and (mark >= 0):
                if mark < x:
                    print('\033[%i;%iH\033[44;37m%s\033[49;39m\033[%i;%iH' % (self.top + y, innerleft + mark, datalines[y][mark : x], self.top + y, innerleft + x), end='')
                elif mark > x:
                    print('\033[%i;%iH\033[44;37m%s\033[49;39m\033[%i;%iH' % (self.top + y, innerleft + x, datalines[y][x : mark], self.top + y, innerleft + x), end='')
            if y != oldy:
                if (oldy > 0) and (leftlines[oldy - 1] == leftlines[oldy]) and (leftlines[oldy] == leftlines[-1]):
                    print('\033[%i;%iH\033[34m%s\033[39m' % (self.top + oldy, self.left, '>'), end='')
                else:
                    print('\033[%i;%iH\033[34m%s:\033[39m' % (self.top + oldy, self.left, leftlines[oldy]), end='')
                if (y > 0) and (leftlines[y - 1] == leftlines[y]) and (leftlines[y] == leftlines[-1]):
                    print('\033[%i;%iH\033[1;34m%s\033[21;39m' % (self.top + y, self.left, '>'), end='')
                else:
                    print('\033[%i;%iH\033[1;34m%s:\033[21;39m' % (self.top + y, self.left, leftlines[y]), end='')
                print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
            (oldy, oldx, oldmark) = (y, x, mark)
            if edited:
                edited = False
                if not modified:
                    modified = True
                    status('modified' + (' override' if override else ''))
            sys.stdout.flush()
            if stored is None:
                d = sys.stdin.read(1)
            else:
                d = stored
                stored = None
            if alerted:
                alerted = False
                alert(None)
            if ord(d) == ord('@') - ord('@'):
                if mark is None:
                    mark = x
                    alert('Mark set')
                elif mark == ~x:
                    mark = x
                    alert('Mark activated')
                elif mark == x:
                    mark = ~x
                    alert('Mark deactivated')
                else:
                    mark = x
                    alert('Mark set')
                alerted = True
            elif ord(d) == ord('K') - ord('@'):
                if x == len(datalines[y]):
                    alert('At end')
                    alerted = True
                else:
                    mark = len(datalines[y])
                    stored = chr(ord('W') - ord('@'))
            elif ord(d) == ord('W') - ord('@'):
                if (mark is not None) and (mark >= 0) and (mark != x):
                    selected = datalines[y][mark : x] if mark < x else datalines[y][x : mark]
                    killring.append(selected)
                    if len(killring) > KILL_MAX:
                        killring = killring[1:]
                    stored = chr(127)
                else:
                    alert('No text is selected')
                    alerted = True
            elif ord(d) == ord('Y') - ord('@'):
                if len(killring) == 0:
                    alert('Killring is empty')
                    alerted = True
                else:
                    mark = None
                    killptr = len(killring) - 1
                    yanked = killring[killptr]
                    print('\033[%i;%iH%s' % (self.top + y, innerleft + x, yanked + datalines[y][x:]), end='')
                    datalines[y] = datalines[y][:x] + yanked + datalines[y][x:]
                    x += len(yanked)
                    print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
            elif ord(d) == ord('X') - ord('@'):
                alert('C-x')
                alerted = True
                sys.stdout.flush()
                d = sys.stdin.read(1)
                alert(str(ord(d)))
                sys.stdout.flush()
                if ord(d) == ord('X') - ord('@'):
                    if (mark is not None) and (mark >= 0):
                        x ^= mark; mark ^= x; x ^= mark
                        alert('Mark swapped')
                    else:
                        alert('No mark is activated')
                elif ord(d) == ord('S') - ord('@'):
                    last = ''
                    for row in range(0, len(datalines)):
                        current = leftlines[row]
                        if len(datalines[row].strip()) == 0:
                            if current is not 'comment':
                                if current != last:
                                    self.datamap[current] = None
                                continue
                        if current == last:
                            self.datamap[current] += '\n' + datalines[row]
                        else:
                            self.datamap[current] = datalines[row]
                            last = current
                    saver()
                    status('unmodified' + (' override' if override else ''))
                    alert('Saved')
                elif ord(d) == ord('C') - ord('@'):
                    break
                else:
                    stored = d
                    alerted = False
                    alert(None)
            elif (ord(d) == 127) or (ord(d) == 8):
                removed = 1
                if (mark is not None) and (mark >= 0) and (mark != x):
                    if mark > x:
                        x ^= mark; mark ^= x; x ^= mark
                    removed = x - mark
                if x == 0:
                    alert('At beginning')
                    alerted = True
                    continue
                dataline = datalines[y]
                datalines[y] = dataline = dataline[:x - removed] + dataline[x:]
                x -= removed
                mark = None
                print('\033[%i;%iH%s%s\033[%i;%iH' % (self.top + y, innerleft, dataline, ' ' * removed, self.top + y, innerleft + x), end='')
                edited = True
            elif ord(d) < ord(' '):
                if ord(d) == ord('P') - ord('@'):
                    if y == 0:
                        alert('At first line')
                        alerted = True
                    else:
                        y -= 1
                        mark = None
                        x = 0
                elif ord(d) == ord('N') - ord('@'):
                    if y == len(datalines) - 1:
                        datalines.append('')
                        leftlines.append(leftlines[-1])
                    y += 1
                    mark = None
                    x = 0
                elif ord(d) == ord('F') - ord('@'):
                    if x < len(datalines[y]):
                        x += 1
                        print('\033[C', end='')
                    else:
                        alert('At end')
                        alerted = True
                elif ord(d) == ord('B') - ord('@'):
                    if x > 0:
                        x -= 1
                        print('\033[D', end='')
                    else:
                        alert('At beginning')
                        alerted = True
                elif ord(d) == ord('O') - ord('@'):
                    leftlines[y : y] = [leftlines[y]]
                    datalines[y : y] = ['']
                    y += 1
                    mark = None
                    x = 0
                    stored = chr(ord('L') - ord('@'))
                elif ord(d) == ord('L') - ord('@'):
                    empty = '\033[0m' + (' ' * self.width + '\n') * len(datalines)
                    print('\033[%i;%iH%s' % (self.top, self.left, empty), end='')
                    for row in range(0, len(leftlines)):
                        leftline = leftlines[row] + ':'
                        if (leftlines[row - 1] == leftlines[row]) and (leftlines[row] == leftlines[-1]):
                            leftline = '>'
                        print('\033[%i;%iH\033[%s34m%s\033[%s39m' % (self.top + row, self.left, '1;' if row == y else '', leftline, '21;' if row == y else ''), end='')
                    for row in range(0, len(datalines)):
                        print('\033[%i;%iH%s\033[49m' % (self.top + row, innerleft, datalines[row]), end='')
                    print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
                elif d == '\033':
                    d = sys.stdin.read(1)
                    if d == '[':
                        d = sys.stdin.read(1)
                        if d == 'A':
                            stored = chr(ord('P') - ord('@'))
                        elif d == 'B':
                            if y == len(datalines) - 1:
                                alert('At last line')
                                alerted = True
                            else:
                                stored = chr(ord('N') - ord('@'))
                        elif d == 'C':
                            stored = chr(ord('F') - ord('@'))
                        elif d == 'D':
                            stored = chr(ord('B') - ord('@'))
                        elif d == '2':
                            d = sys.stdin.read(1)
                            if d == '~':
                                override = not override
                                status(('modified' if modified else 'unmodified') + (' override' if override else ''))
                        elif d == '3':
                            d = sys.stdin.read(1)
                            if d == '~':
                                removed = 1
                                if (mark is not None) and (mark >= 0) and (mark != x):
                                    if mark < x:
                                        x ^= mark; mark ^= x; x ^= mark
                                    removed = mark - x
                                dataline = datalines[y]
                                if x == len(dataline):
                                    alert('At end')
                                    alerted = True
                                    continue
                                datalines[y] = dataline = dataline[:x] + dataline[x + removed:]
                                print('\033[%i;%iH%s%s\033[%i;%iH' % (self.top + y, innerleft, dataline, ' ' * removed, self.top + y, innerleft + x), end='')
                                mark = None
                                edited = True
                        else:
                            while True:
                                d = sys.stdin.read(1)
                                if (ord('a') <= ord(d)) and (ord(d) <= ord('z')): break
                                if (ord('A') <= ord(d)) and (ord(d) <= ord('Z')): break
                                if d == '~': break
                    elif (d == 'w') or (d == 'W'):
                        if (mark is not None) and (mark >= 0) and (mark != x):
                            selected = datalines[y][mark : x] if mark < x else datalines[y][x : mark]
                            killring.append(selected)
                            mark = None
                            if len(killring) > KILL_MAX:
                                killring = killring[1:]
                        else:
                            alert('No text is selected')
                            alerted = True
                    elif (d == 'y') or (d == 'Y'):
                        if killptr is not None:
                            yanked = killring[killptr]
                            dataline = datalines[y]
                            if (len(yanked) <= x) and (dataline[x - len(yanked) : x] == yanked):
                                killptr -= 1
                                if killptr < 0:
                                    killptr += len(killring)
                                dataline = dataline[:x - len(yanked)] + killring[killptr] + dataline[x:]
                                additional = len(killring[killptr]) - len(yanked)
                                x += additional
                                datalines[y] = dataline
                                print('\033[%i;%iH%s%s\033[%i;%iH' % (self.top + y, innerleft, dataline, ' ' * max(0, -additional), self.top + y, innerleft + x), end='')
                            else:
                                stored = chr(ord('Y') - ord('@'))
                        else:
                            stored = chr(ord('Y') - ord('@'))
                    elif d == 'O':
                        d = sys.stdin.read(1)
                        if d == 'H':
                            x = 0
                        elif d == 'F':
                            x = len(datalines[y])
                        print('\033[%i;%iH' % (self.top + y, innerleft + x), end='')
                elif d == '\n':
                    stored = chr(ord('N') - ord('@'))
            else:
                insert = d
                if len(insert) == 0:
                    continue
                dataline = datalines[y]
                if (not override) or (x == len(dataline)):
                    print(insert + dataline[x:], end='')
                    if len(dataline) - x > 0:
                        print('\033[%iD' % (len(dataline) - x), end='')
                    datalines[y] = dataline[:x] + insert + dataline[x:]
                    if (mark is not None) and (mark >= 0):
                        if mark >= x:
                            mark += len(insert)
                else:
                    print(insert, end='')
                    datalines[y] = dataline[:x] + insert + dataline[x + 1:]
                x += len(insert)
                edited = True



HOME = os.environ['HOME'] if 'HOME' in os.environ else os.path.expanduser('~')
'''
The user's home directory
'''

pipelinein = not sys.stdin.isatty()
'''
Whether stdin is piped
'''

pipelineout = not sys.stdout.isatty()
'''
Whether stdout is piped
'''

pipelineerr = not sys.stderr.isatty()
'''
Whether stderr is piped
'''


usage_program = '\033[34;1mponysay-tool\033[21;39m'

usage = '\n'.join(['%s %s' % (usage_program, '(--help | --version | --kms)'),
                   '%s %s' % (usage_program, '(--edit | --edit-rm) \033[33mPONY-FILE\033[39m'),
                   '%s %s' % (usage_program, '--edit-stash \033[33mPONY-FILE\033[39m > \033[33mSTASH-FILE\033[39m'),
                   '%s %s' % (usage_program, '--edit-apply \033[33mPONY-FILE\033[39m < \033[33mSTASH-FILE\033[39m'),
                   '%s %s' % (usage_program, '(--dimensions | --metadata) \033[33mPONY-DIR\033[39m'),
                   '%s %s' % (usage_program, '--browse \033[33mPONY-DIR\033[39m [-r \033[33mRESTRICTION\033[39m]*'),
               ])

usage = usage.replace('\033[', '\0')
for sym in ('[', ']', '(', ')', '|', '...', '*'):
    usage = usage.replace(sym, '\033[2m' + sym + '\033[22m')
usage = usage.replace('\0', '\033[')

'''
Argument parsing
'''
opts = ArgParser(program     = 'ponysay-tool',
                 description = 'Tool chest for ponysay',
                 usage       = usage,
                 longdescription = None)

opts.add_argumentless(['--no-term-init']) # for debugging

opts.add_argumentless(['-h', '--help'],                          help = 'Print this help message.')
opts.add_argumentless(['+h', '++help', '--help-colour'],         help = 'Print this help message with colours even if piped.')
opts.add_argumentless(['-v', '--version'],                       help = 'Print the version of the program.')
opts.add_argumentless(['--kms'],                                 help = 'Generate all kmsponies for the current TTY palette')
opts.add_argumented(  ['--dimensions'],     arg = 'PONY-DIR',    help = 'Generate pony dimension file for a directory')
opts.add_argumented(  ['--metadata'],       arg = 'PONY-DIR',    help = 'Generate pony metadata collection file for a directory')
opts.add_argumented(  ['-b', '--browse'],   arg = 'PONY-DIR',    help = 'Browse ponies in a directory')
opts.add_argumented(  ['-r', '--restrict'], arg = 'RESTRICTION', help = 'Metadata based restriction for --browse')
opts.add_argumented(  ['--edit'],           arg = 'PONY-FILE',   help = 'Edit a pony file\'s metadata')
opts.add_argumented(  ['--edit-rm'],        arg = 'PONY-FILE',   help = 'Remove metadata from a pony file')
opts.add_argumented(  ['--edit-apply'],     arg = 'PONY-FILE',   help = 'Apply metadata from stdin to a pony file')
opts.add_argumented(  ['--edit-stash'],     arg = 'PONY-FILE',   help = 'Print applyable metadata from a pony file')

unrecognised = not opts.parse()
'''
Whether at least one unrecognised option was used
'''

PonysayTool(args = opts)


########NEW FILE########
__FILENAME__ = spellocorrecter
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *



class SpelloCorrecter(): # Naïvely and quickly ported and adapted from optimised Java, may not be the nicest, or even fast, Python code
    '''
    Class used for correcting spellos and typos,
    
    Note that this implementation will not find that correctly spelled word are correct faster than it corrects words.
    It is also limited to words of size 0 to 127 (inclusive)
    '''
    
    def __init__(self, directories, ending = None):
        '''
        Constructor
        
        @param  directories:list<str>  List of directories that contains the file names with the correct spelling
        @param  ending:str             The file name ending of the correctly spelled file names, this is removed for the name
        
        -- OR -- (emulated overloading [overloading is absent in Python])
        
        @param  directories:list<str>  The file names with the correct spelling
        '''
        self.weights = {'k' : {'c' : 0.25, 'g' : 0.75, 'q' : 0.125},
                        'c' : {'k' : 0.25, 'g' : 0.75, 's' : 0.5, 'z' : 0.5, 'q' : 0.125},
                        's' : {'z' : 0.25, 'c' : 0.5},
                        'z' : {'s' : 0.25, 'c' : 0.5},
                        'g' : {'k' : 0.75, 'c' : 0.75, 'q' : 0.9},
                        'o' : {'u' : 0.5},
                        'u' : {'o' : 0.5, 'v' : 0.75, 'w' : 0.5},
                        'b' : {'v' : 0.75},
                        'v' : {'b' : 0.75, 'w' : 0.5, 'u' : 0.7},
                        'w' : {'v' : 0.5, 'u' : 0.5},
                        'q' : {'c' : 0.125, 'k' : 0.125, 'g' : 0.9}}
        
        self.corrections = None
        self.dictionary = [None] * 513
        self.reusable = [0] * 512
        self.dictionaryEnd = 512
        self.closestDistance = 0
        
        self.M = [None] * 128
        for y in range(0, 128):
            self.M[y] = [0] * 128
            self.M[y][0] = y
        m0 = self.M[0]
        x = 127
        while x > -1:
            m0[x] = x
            x -= 1
        
        previous = ''
        self.dictionary[-1] = previous;
        
        if ending is not None:
            for directory in directories:
                files = os.listdir(directory)
                files.sort()
                for filename in files:
                    if (not endswith(filename, ending)) or (len(filename) - len(ending) > 127):
                        continue
                    proper = filename[:-len(ending)]
                    
                    if self.dictionaryEnd == 0:
                        self.dictionaryEnd = len(self.dictionary)
                        self.reusable = [0] * self.dictionaryEnd + self.reusable
                        self.dictionary = [None] * self.dictionaryEnd + self.dictionary
                    
                    self.dictionaryEnd -= 1
                    self.dictionary[self.dictionaryEnd] = proper
                    
                    prevCommon = min(len(previous), len(proper))
                    for i in range(0, prevCommon):
                        if previous[i] != proper[i]:
                            prevCommon = i
                            break
                    previous = proper
                    self.reusable[self.dictionaryEnd] = prevCommon
        else:
            files = directories
            files.sort()
            for proper in files:
                if len(proper) > 127:
                    continue
                
                if self.dictionaryEnd == 0:
                    self.dictionaryEnd = len(self.dictionary)
                    self.reusable = [0] * self.dictionaryEnd + self.reusable
                    self.dictionary = [None] * self.dictionaryEnd + self.dictionary
                
                self.dictionaryEnd -= 1
                self.dictionary[self.dictionaryEnd] = proper
                
                prevCommon = min(len(previous), len(proper))
                for i in range(0, prevCommon):
                    if previous[i] != proper[i]:
                        prevCommon = i
                        break
                previous = proper
                self.reusable[self.dictionaryEnd] = prevCommon
        #part = self.dictionary[self.dictionaryEnd : len(self.dictionary) - 1]
        #part.sort()
        #self.dictionary[self.dictionaryEnd : len(self.dictionary) - 1] = part
        #
        #index = len(self.dictionary) - 1
        #while index >= self.dictionaryEnd:
        #    proper = self.dictionary[index]
        #    prevCommon = min(len(previous), len(proper))
        #    for i in range(0, prevCommon):
        #        if previous[i] != proper[i]:
        #            prevCommon = i
        #            break
        #    previous = proper
        #    self.reusable[self.dictionaryEnd] = prevCommon
        #    index -= 1;    
    
    
    def correct(self, used):
        '''
        Finds the closests correct spelled word
        
        @param   used:str                               The word to correct
        @return  (words, distance):(list<string>, int)  A list the closest spellings and the weighted distance
        '''
        if len(used) > 127:
            return ([used], 0)
        
        self.__correct(used)
        return (self.corrections, self.closestDistance)
    
    
    def __correct(self, used):
        '''
        Finds the closests correct spelled word
        
        @param  used:str  The word to correct, it must satisfy all restrictions
        '''
        self.closestDistance = 0x7FFFFFFF
        previous = self.dictionary[-1]
        prevLen = 0
        usedLen = len(used)
        
        proper = None
        prevCommon = 0
        
        d = len(self.dictionary) - 1
        while d > self.dictionaryEnd:
            d -= 1
            proper = self.dictionary[d]
            if abs(len(proper) - usedLen) <= self.closestDistance:
                if previous == self.dictionary[d + 1]:
                    prevCommon = self.reusable[d];
                else:
                    prevCommon = min(prevLen, len(proper))
                    for i in range(0, prevCommon):
                        if previous[i] != proper[i]:
                            prevCommon = i
                            break
                
                skip = min(prevLen, len(proper))
                i = prevCommon
                while i < skip:
                    for u in range(0, usedLen):
                        if (used[u] == previous[i]) or (used[u] == proper[i]):
                            skip = i
                            break
                    i += 1
                
                common = min(skip, min(usedLen, len(proper)))
                for i in range(0, common):
                    if used[i] != proper[i]:
                        common = i
                        break
                
                distance = self.__distance(proper, skip, len(proper), used, common, usedLen)
                
                if self.closestDistance > distance:
                    self.closestDistance = distance
                    self.corrections = [proper]
                elif self.closestDistance == distance:
                    self.corrections.append(proper)
                
                previous = proper;
                if distance >= 0x7FFFFF00:
                    prevLen = distance & 255
                else:
                    prevLen = len(proper)
    
    
    def __distance(self, proper, y0, yn, used, x0, xn):
        '''
        Calculate the distance between a correct word and a incorrect word
        
        @param   proper:str  The correct word
        @param   y0:int      The offset for `proper`
        @param   yn:int      The length, before applying `y0`, of `proper`
        @param   used:str    The incorrect word
        @param   x0:int      The offset for `used`
        @param   xn:int      The length, before applying `x0`, of `used`
        @return  :float      The distance between the words
        '''
        my = self.M[y0]
        for y in range(y0, yn):
            best = 0x7FFFFFFF
            p = proper[y]
            myy = self.M[y + 1] # only one array bound check, and at most one + ☺
            x = x0
            while x < xn:
                change = my[x]
                u = used[x]
                if p == u:
                    # commence black magick … twilight would be so disappointed
                    x += 1
                    myy[x] = change
                    best = min(best, change)
                remove = myy[x]
                add = my[x + 1]
                
                cw = 1
                if my[x] in self.weights:
                    if p in self.weights[u]:
                      cw = self.weights[u][p]
                x += 1
                
                myy[x] = min(cw + change, 1 + min(remove, add))
                if best > myy[x]:
                    best = myy[x]
            
            if best > self.closestDistance:
                return 0x7FFFFF00 | y
            my = myy
        return my[xn]


########NEW FILE########
__FILENAME__ = ucs
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.
'''
from common import *



class UCS():
    '''
    UCS utility class
    '''
    
    @staticmethod
    def isCombining(char):
        '''
        Checks whether a character is a combining character
        
        @param   char:chr  The character to test
        @return  :bool     Whether the character is a combining character
        '''
        o = ord(char)
        if (0x0300 <= o) and (o <= 0x036F):  return True
        if (0x20D0 <= o) and (o <= 0x20FF):  return True
        if (0x1DC0 <= o) and (o <= 0x1DFF):  return True
        if (0xFE20 <= o) and (o <= 0xFE2F):  return True
        return False
    
    
    @staticmethod
    def countCombining(string):
        '''
        Gets the number of combining characters in a string
        
        @param   string:str  A text to count combining characters in
        @return  :int        The number of combining characters in the string
        '''
        rc = 0
        for char in string:
            if UCS.isCombining(char):
                rc += 1
        return rc
    
    
    @staticmethod
    def dispLen(string):
        '''
        Gets length of a string not counting combining characters
        
        @param   string:str  The text of which to determine the monospaced width
        @return              The determine the monospaced width of the text, provided it does not have escape sequnces
        '''
        return len(string) - UCS.countCombining(string)


########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
ponysay - Ponysay, cowsay reimplementation for ponies

Copyright (C) 2012, 2013, 2014  Erkin Batu Altunbaş et al.


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


If you intend to redistribute ponysay or a fork of it commercially,
it contains aggregated images, some of which may not be commercially
redistribute, you would be required to remove those. To determine
whether or not you may commercially redistribute an image make use
that line ‘FREE: yes’, is included inside the image between two ‘$$$’
lines and the ‘FREE’ is and upper case and directly followed by
the colon.


Authors:

         Erkin Batu Altunbaş:              Project leader, helped write the first implementation
         Mattias "maandree" Andrée:        Major contributor of both implementions
         Elis "etu" Axelsson:              Major contributor of current implemention and patcher of the first implementation
         Sven-Hendrik "svenstaro" Haase:   Major contributor of the first implementation
         Jan Alexander "heftig" Steffens:  Major contributor of the first implementation
         Kyah "L-four" Rindlisbacher:      Patched the first implementation
'''
from common import *
from argparser import *
from ponysay import *



'''
Start the program
'''
if __name__ == '__main__':
    istool = sys.argv[0]
    if os.sep in istool:
        istool = istool[istool.rfind(os.sep) + 1:]
    if os.extsep in istool:
        istool = istool[:istool.find(os.extsep)]
    istool = istool.endswith('-tool')
    if istool:
        from ponysaytool import * ## will start ponysay-tool
        exit(0)
    
    isthink = sys.argv[0]
    if os.sep in isthink:
        isthink = isthink[isthink.rfind(os.sep) + 1:]
    if os.extsep in isthink:
        isthink = isthink[:isthink.find(os.extsep)]
    isthink = isthink.endswith('think')
    
    usage_saythink = '\033[34;1m(ponysay | ponythink)\033[21;39m'
    usage_common   = '[-c] [-W\033[33mCOLUMN\033[39m] [-b\033[33mSTYLE\033[39m]'
    usage_listhelp = '(-l | -L | -B | +l | +L | -A | + A | -v | -h)'
    usage_file     = '[-f\033[33mPONY\033[39m]* [[--] \033[33mmessage\033[39m]'
    usage_xfile    = '(+f\033[33mPONY\033[39m)* [[--] \033[33mmessage\033[39m]'
    usage_afile    = '(-F\033[33mPONY\033[39m)* [[--] \033[33mmessage\033[39m]'
    usage_quote    = '(-q\033[33mPONY\033[39m)*'
    
    usage = ('%s %s' + 4 * '\n%s %s %s') % (usage_saythink, usage_listhelp,
                                            usage_saythink, usage_common, usage_file,
                                            usage_saythink, usage_common, usage_xfile,
                                            usage_saythink, usage_common, usage_afile,
                                            usage_saythink, usage_common, usage_quote)
    
    usage = usage.replace('\033[', '\0')
    for sym in ('[', ']', '(', ')', '|', '...', '*'):
        usage = usage.replace(sym, '\033[2m' + sym + '\033[22m')
    usage = usage.replace('\0', '\033[')
    
    '''
    Argument parsing
    '''
    opts = ArgParser(program     = 'ponythink' if isthink else 'ponysay',
                     description = 'cowsay reimplemention for ponies',
                     usage       = usage,
                     longdescription =
'''Ponysay displays an image of a pony saying some text provided by the user.
If \033[4mmessage\033[24m is not provided, it accepts standard input. For an extensive
documentation run `info ponysay`, or for just a little more help than this
run `man ponysay`. Ponysay has so much more to offer than described here.''')
    
    opts.add_argumentless(['--quoters'])
    opts.add_argumentless(['--onelist'])
    opts.add_argumentless(['++onelist'])
    opts.add_argumentless(['--Onelist'])
    
    opts.add_argumentless(['-X', '--256-colours', '--256colours', '--x-colours'])
    opts.add_argumentless(['-V', '--tty-colours', '--ttycolours', '--vt-colours'])
    opts.add_argumentless(['-K', '--kms-colours', '--kmscolours'])
    
    opts.add_argumentless(['-i', '--info'])
    opts.add_argumentless(['+i', '++info'])
    opts.add_argumented(  ['-r', '--restrict'], arg = 'RESTRICTION')
    
    opts.add_argumented(  ['+c', '--colour'],                      arg = 'COLOUR')
    opts.add_argumented(  ['--colour-bubble', '--colour-balloon'], arg = 'COLOUR')
    opts.add_argumented(  ['--colour-link'],                       arg = 'COLOUR')
    opts.add_argumented(  ['--colour-msg', '--colour-message'],    arg = 'COLOUR')
    opts.add_argumented(  ['--colour-pony'],                       arg = 'COLOUR')
    opts.add_argumented(  ['--colour-wrap', '--colour-hyphen'],    arg = 'COLOUR')
    
    _F = ['--any-file', '--anyfile', '--any-pony', '--anypony']
    __F = [_.replace("pony", "ponie") + 's' for _ in _F]
    opts.add_argumentless(['-h', '--help'],                                        help = 'Print this help message.')
    opts.add_argumentless(['+h', '++help', '--help-colour'],                       help = 'Print this help message with colours even if piped.')
    opts.add_argumentless(['-v', '--version'],                                     help = 'Print the version of the program.')
    opts.add_argumentless(['-l', '--list'],                                        help = 'List pony names.')
    opts.add_argumentless(['-L', '--symlist', '--altlist'],                        help = 'List pony names with alternatives.')
    opts.add_argumentless(['+l', '++list'],                                        help = 'List non-MLP:FiM pony names.')
    opts.add_argumentless(['+L', '++symlist', '++altlist'],                        help = 'List non-MLP:FiM pony names with alternatives.')
    opts.add_argumentless(['-A', '--all'],                                         help = 'List all pony names.')
    opts.add_argumentless(['+A', '++all', '--symall', '--altall'],                 help = 'List all pony names with alternatives.')
    opts.add_argumentless(['-B', '--bubblelist', '--balloonlist'],                 help = 'List balloon styles.')
    opts.add_argumentless(['-c', '--compress', '--compact'],                       help = 'Compress messages.')
    opts.add_argumentless(['-o', '--pony-only', '--ponyonly'],                     help = 'Print only the pony.')
    opts.add_argumented(  ['-W', '--wrap'],                        arg = 'COLUMN', help = 'Specify column where the message should be wrapped.')
    opts.add_argumented(  ['-b', '--bubble', '--balloon'],         arg = 'STYLE',  help = 'Select a balloon style.')
    opts.add_argumented(  ['-f', '--file', '--pony'],              arg = 'PONY',   help = 'Select a pony.\nEither a file name or a pony name.')
    opts.add_argumented(  ['+f', '++file', '++pony'],              arg = 'PONY',   help = 'Select a non-MLP:FiM pony.')
    opts.add_argumented(  ['-F'] + _F,                             arg = 'PONY',   help = 'Select a pony, that can be a non-MLP:FiM pony.')
    opts.add_argumented(  ['-q', '--quote'],                       arg = 'PONY',   help = 'Select a pony which will quote herself.')
    opts.add_variadic(    ['--f', '--files', '--ponies'],          arg = 'PONY')
    opts.add_variadic(    ['++f', '++files', '++ponies'],          arg = 'PONY')
    opts.add_variadic(    ['--F'] + __F,                           arg = 'PONY')
    opts.add_variadic(    ['--q', '--quotes'],                     arg = 'PONY')
    
    '''
    Whether at least one unrecognised option was used
    '''
    unrecognised = not opts.parse()
    
    
    ## Start
    ponysay = Ponysay()
    ponysay.unrecognised = unrecognised
    ponysay.run(opts)

########NEW FILE########
