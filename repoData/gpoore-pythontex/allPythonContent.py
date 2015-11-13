__FILENAME__ = depythontex
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is the depythontex wrapper script.  It automatically detects the version
of Python, and then imports the correct code from depythontex2.py or 
depythontex3.py.  It is intended for use with the default Python installation 
on your system.  If you wish to use a different version of Python, you could 
launch depythontex2.py or depythontex3.py directly.  The version of Python
does not matter for depythontex, since no code is executed.

Copyright (c) 2013-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''

import sys
if sys.version_info[0] == 2:
    import depythontex2 as depythontex
elif sys.version_info[0] == 3:
    import depythontex3 as depythontex

########NEW FILE########
__FILENAME__ = depythontex2
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
PythonTeX depythontex script.

This script takes a LaTeX document that uses the PythonTeX package and 
creates a new document that does not depend on PythonTeX.  It substitutes all 
externally generated content into a copy of the original LaTeX document.  
This is useful when you need a document that relies on few external packages 
or custom macros (for example, for submission to a journal or conversion to 
another document format).

If you just want to share a document that uses PythonTeX, keep in mind that 
the document can be modified and compiled just like a regular LaTeX document, 
without needing Python or any other external tools, so long as the following 
conditions are met:

  * A copy of pythontex.sty is included with the document.
  * The pythontex-files-<name> directory is included with the document.
  * The PythonTeX-specific parts of the document are not modified.

To work, this script requires that the original LaTeX document be compiled 
with the package option `depythontex`.  That creates an auxiliary file with 
the extension .depytx that contains information about all content that needs
to be substituted.

This script is purposely written in a simple, largely linear form to 
facilitate customization.  Most of the key substitutions are performed by a 
few functions defined near the beginning of the script, so if you need custom
substitutions, you should begin there.  By default, all typeset code is 
wrapped in `\verb` commands and verbatim environments, since these have the 
greatest generality.  However, the command-line option --listing allows code 
to be typeset with the fancyvrb, listings, minted, or PythonTeX packages 
instead.

The script automatically extracts all arguments of all commands and 
environments that it replaces, so that these are available if desired for 
customized substitution.  Two additional pieces of information are also 
available for any typeset code:  the Pygments lexer (often the same as the 
language) and the starting line number (if line numbering was used).

Keep in mind that some manual adjustments may be required after a document is
depythontex'ed.  While depythontex attempts to create an exact copy of the 
original document, in many cases an identical copy is impossible.  For 
example, typeset code may have a different appearance or layout when it is 
typeset with a different package.


Copyright (c) 2013-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
#// Python 2
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
#\\ End Python 2
import sys
import os
#// Python 2
if sys.version_info.major != 2:
    sys.exit('This version of the PythonTeX script requires Python 2.')
#\\ End Python 2
#// Python 3
#if sys.version_info.major != 3:
#    sys.exit('This version of the PythonTeX script requires Python 3.')
#\\ End Python 3

#// Python 2
from io import open
input = raw_input
#\\ End Python 2
import argparse
from collections import defaultdict
from re import match, sub, search
import textwrap
import codecs


# Script parameters
# Version
version = 'v0.13-beta'


# Functions and parameters for customizing the script output

# Style or package for replacing code listings
# This is actually set via command-line option --listing
# It is created here simply for reference
listing = None  #'verbatim', 'fancyvrb', 'listings', 'minted', 'pythontex'

# List of things to add to the preamble
# It can be appended to via the command-line option --preamble
# It is also appended to based on the code listing style that is used
# And it could be manually edited here as well, as long as it remains a list
preamble_additions = list()

# Lexer dict
# If you are using Pygments lexers that don't directly correspond to the 
# languages used by the listings package, you can submit replacements via the 
# command line option --lexer-dict, or edit this dict manually here.  When 
# listings is used, all lexers are checked against this dict to see if a 
# substitution should be made.  This approach could easily be modified to 
# work with another, non-Pygments highlighting package.
lexer_dict = dict()


def replace_code_cmd(name, arglist, linenum, code_replacement, 
                     code_replacement_mode, after, lexer, firstnumber):
    '''
    Typeset code from a command with a command.
    
    It is only ever called if there is indeed code to typeset.
    
    Usually, code from a command is also typeset with a command.  This 
    function primarily deals with that case.  In cases where code from a 
    command is typeset with an environment (for example, `\inputpygments`),
    this function performs some preprocessing and then uses 
    replace_code_env() to do the real work.  This approach prevents the two
    functions from unnecessarily duplicating each other, while still giving
    the desired output.
    
    Args:
        name (str):  name of the command
        arglist (list, of str/None):  all arguments given to the original 
            command; the last argument is what is typeset, unless a 
            code_replacement is specified or other instructions are given
        linenum (int):  line number in the original TeX document
        code_replacement (str/None):  replacement for the code; usually None
            for commands, because typically the code to be typeset is the 
            last argument passed to the command, rather than something 
            captured elsewhere (like the body of an environment) or something
            preprocessed (like a console environment's content)
        code_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX; generally unused for code), 
            verb (inline), or verbatim (environment)
        after (str):  text immediately following the command; usually 
            shouldn't be needed
        lexer (str/None):  Pygments lexer
    Returns:
        (replacement, after) (tuple, of str)
    
    '''
    # Get the correct replacement
    if code_replacement is None:
        code_replacement = arglist[-1]
    
    # We only consider two possible modes of typesetting, verbatim and inline
    # verbatim
    if code_replacement_mode == 'verbatim':
        # Sometimes we must replace a command with an environment, for 
        # example, for `\inputpygments`
        
        # Make sure the introduction of an environment where a command was 
        # previously won't produce errors with following content; make sure 
        # that any following content is on a separate line
        if bool(match('[ \t]*\S', after)):
            after = '\n' + after
        # Rather than duplicating much of replace_code_env(), just use it
        return replace_code_env(name, arglist, linenum, code_replacement, 
                                code_replacement_mode, after, lexer, firstnumber)
    else:
        # Usually, we're replacing a command with a command
        
        # Wrap the replacement in appropriate delimiters
        if (listing in ('verbatim', 'fancyvrb', 'minted') or 
                (listing in ('listings', 'pythontex') and 
                ('{' in code_replacement or '}' in code_replacement))):
            for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$', 
                          '=', '+', '-', '^', '_', '?', ';'):
                if delim not in code_replacement:
                    break
            code_replacement = delim + code_replacement + delim
        else:
            code_replacement = '{' + code_replacement + '}'
        # Assemble the actual replacement
        if listing in ('verbatim', 'minted'): # `\mint` isn't for inline use
            code_replacement = r'\verb' + code_replacement
        elif listing == 'fancyvrb':
            code_replacement = r'\Verb' + code_replacement
        elif listing == 'listings':
            if lexer is None:
                code_replacement = r'\lstinline[language={}]' + code_replacement
            else:
                if lexer in lexer_dict:
                    lexer = lexer_dict[lexer]
                code_replacement = r'\lstinline[language=' + lexer + ']' + code_replacement
        elif listing == 'pythontex':
            if lexer is None:
                code_replacement = r'\pygment{text}' + code_replacement
            else:
                code_replacement = r'\pygment{' + lexer + '}' + code_replacement
        return (code_replacement, after)
    

def replace_code_env(name, arglist, linenum, code_replacement, 
                     code_replacement_mode, after, lexer, firstnumber):
    '''
    Typeset code from an environment with an environment.
    
    It is only ever called if there is indeed code to typeset.
    
    Usually it is only used to typeset code from an environment.  However,
    some commands bring in code that must be typeset as an environment.  In
    those cases, replace_code_cmd() is called initially, and after it 
    performs some preprocessing, this function is called.  This approach
    avoids unnecessary duplication between the two functions.
    
    Args:
        name (str):  name of the environment
        arglist (list, of str/None):  all arguments given to the original 
            environment
        linenum (int):  line number in the original TeX document where 
            the environment began
        code_replacement (str):  replacement for the code; unlike the case of
            commands, this is always not None if the function is called
        code_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX; generally unused for code), 
            verb (inline), or verbatim (environment)
        after (str):  text immediately following the environment; usually 
            shouldn't be needed
        lexer (str/None):  Pygments lexer
        firstnumber (str/None):  the first number of the listing, if the listing
            had numbered lines
    Returns:
        (replacement, after) (tuple, of str)
    
    '''
    # Currently, there is no need to test for code_replacement_mode, because
    # this function is only ever called if the mode is 'verbatim'.  That may
    # change in the future, but it seems unlikely that code entered in an
    # environment would end up typeset with a command.
    if listing == 'verbatim':
        pre = '\\begin{verbatim}'
        post = '\\end{verbatim}'
    elif listing == 'fancyvrb':
        if firstnumber is None:
            pre = '\\begin{Verbatim}'
        else:
            pre = '\\begin{{Verbatim}}[numbers=left,firstnumber={0}]'.format(firstnumber)
        post = '\\end{Verbatim}'        
    elif listing == 'listings':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{lstlisting}[language={}]'
            else:
                pre = '\\begin{{lstlisting}}[language={{}},numbers=left,firstnumber={0}]'.format(firstnumber)
        else:
            if lexer in lexer_dict:
                lexer = lexer_dict[lexer]
            if firstnumber is None:
                pre = '\\begin{{lstlisting}}[language={0}]'.format(lexer)
            else:
                pre = '\\begin{{lstlisting}}[language={0},numbers=left,firstnumber={1}]'.format(lexer, firstnumber)
        post = '\\end{lstlisting}'
    elif listing == 'minted':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{minted}{text}'
            else:
                pre = '\\begin{{minted}}[linenos,firstnumber={0}]{{text}}'.format(firstnumber)
        else:
            if firstnumber is None:
                pre = '\\begin{{minted}}{{{0}}}'.format(lexer)
            else:
                pre = '\\begin{{minted}}[linenos,firstnumber={0}]{{{1}}}'.format(firstnumber, lexer)
        post = '\\end{minted}'
    elif listing == 'pythontex':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{pygments}{text}'
            else:
                pre = '\\begin{{pygments}}[numbers=left,firstnumber={0}]{{text}}'.format(firstnumber)
        else:
            if firstnumber is None:
                pre = '\\begin{{pygments}}{{{0}}}'.format(lexer)
            else:
                pre = '\\begin{{pygments}}[numbers=left,firstnumber={0}]{{{1}}}'.format(firstnumber, lexer)
        post = '\\end{pygments}'
    code_replacement = pre + code_replacement + post
    return (code_replacement, after)


# We will need to issue a warning every time that a substitution of printed
# content results in a forced double space.  We could just do this as we go,
# but it's easier for the user to read if we just collect all the warnings
# of this type, and print them once.
forced_double_space_list = list()


def replace_print_cmd(name, arglist, linenum,
                      print_replacement, print_replacement_mode, source,
                      after):
    '''
    Typeset printed content from a command.
    
    It is only ever called if there is indeed printed content to typeset.
    
    Args:
        name (str):  name of the command
        arglist (list, of str/None):  all arguments given to the original 
            command
        linenum (int):  line number in the original TeX document
        print_replacement (str):  printed content, read directly from file
            into a single string
        print_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX), inlineverb (or v) (as inline), 
            or verb (as environment)
        source (str/None):  source of the replacement content
        after (str):  text immediately following the command; important in
            some situations, because spacing can depend on what's next
    Returns:
        (replacement, after) (tuple, of str)
    
    '''    
    if print_replacement_mode == 'verb':
        if print_replacement.count('\n') > 1:
            print('* DePythonTeX error:')
            print('    Attempt to print multiple lines of content near line ' + str(linenum))
            print('    This is not possible in inline verbatim mode')
            sys.exit(1)
        print_replacement = print_replacement.rstrip('\n')
        for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$', 
                      '=', '+', '-', '^', '_', '?', ';'):
            if delim not in print_replacement:
                break
        print_replacement = r'\verb' + delim + print_replacement + delim
    elif print_replacement_mode == 'verbatim':
        if bool(match('\s*?\n', after)):
            # Usually, we would end the verbatim environment with a newline.
            # This is fine if there is content in `after` before the next 
            # newline---in fact, it's desirable, because the verbatim package
            # doesn't allow for content on the same line as the end of the 
            # environment.  But if `after` is an empty line, then adding a 
            # newline will throw off spacing and must be avoided
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}'
        else:
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}\n'
    else:
        # When printed content from a file is included as LaTeX code, we have 
        # to be particularly careful to ensure that the content produces the 
        # same output when substituted as when brought in by `\input`.  In 
        # particular, `\input` strips newlines from each line of content and 
        # adds a space at the end of each line.  This space is inside the
        # `\input`, so it will not merge with following spaces.  So when we 
        # substitute the content, sometimes we need to replace the final 
        # newline with a space that cannot be gobbled.
        #
        # It gets more complicated.  This final space is often not 
        # desirable.  It can be prevented by either printing an `\endinput` 
        # command, to terminate the `\input`, or printing a percent 
        # character % in the last line of the content, which comments out the
        # final newline.  So we must check for `\endinput` anywhere in 
        # printed content, and % in the final line, and remove any content 
        # after them.  It's also possible that the print is followed by 
        # an `\unskip` that eats the space, so we need to check for that too.
        #
        # It turns out that the same approach is needed when a command like 
        # `\py` brings in content ending in a newline
        if (print_replacement.endswith('\\endinput\n') and 
                not print_replacement.endswith('\\string\\endinput\n')):
            # If `\endinput` is present, everything from it on should be 
            # discarded, unless the `\endinput` is not actually a command
            # but rather a typeset name (for example, `\string\endinput` or 
            # `\verb|\endinput|`).  It's impossible to check for all cases in 
            # which `\endinput` is not a command (at least, without actually 
            # using LaTeX), and even checking for most of them would require 
            # a good bit of parsing.  We assume that `\endinput`, as a 
            # command, will only ever occur at the immediate end of the 
            # printed content.  Later, we issue a warning in case it appears 
            # anywhere else.
            print_replacement = print_replacement.rsplit(r'\endinput', 1)[0]
        elif (print_replacement.endswith('%\n') and 
                not print_replacement.endswith('\\%\n') and 
                not print_replacement.endswith('\\string%\n')):
            # Perform an analogous check for a terminating percent characer %.
            # This case would be a bit easier to parse fully, since a percent 
            # that comments out the last newline would have to be in the 
            # final line of the replacement.  But it would still be 
            # very difficult to perform a complete check.  Later, we issue a 
            # warning if there is reason to think that a percent character 
            # was active in the last line.
            print_replacement = print_replacement.rsplit(r'%', 1)[0]
        elif print_replacement.endswith('\n'):
            # We can't just use `else` because that would catch content
            # from `\py` and similar
            # By default, LaTeX strips newlines and adds a space at the end 
            # of each line of content that is brought in by `\input`.  This 
            # may or may not be desirable, but we replicate the effect here 
            # for consistency with the original document.  We use `\space{}` 
            # because plain `\space` would gobble a following space, which 
            # isn't consistent with the `\input` behavior being replicated.
            if bool(match(r'\\unskip\s+\S', after)):
                # If there's an `\unskip`, fix the spacing and remove the 
                # `\unskip`.  Since this is inline, the `\unskip` must 
                # immediately follow the command to do any good; otherwise,
                # it eliminates spaces that precede it, but doesn't get into
                # the `\input` content.
                print_replacement = print_replacement.rstrip(' \t\n')
                after = sub(r'^\\unskip\s+', '', after)
            elif bool(match('\S', after)):
                # If the next character is not whitespace, we can just leave
                # the `\n`, and it will yield a space.
                pass
            elif bool(match('\s*$', after)):
                # If the rest of the current line, and the next line, are 
                # whitespace, we will get the correct spacing without needing
                # `\space{}`.  We could leave `\n`, but it would be 
                # extraneous whitespace.
                print_replacement = print_replacement[:-1]
            else:
                # Otherwise, we do need to insert `\space{}`
                # We keep the newline at the end of printed content, in case
                # it's at the end of an environment, and thus is needed to
                # protect the following content
                print_replacement += '\\space{}'
                after = sub('^\s+', '', after)
                forced_double_space_list.append((name, linenum))
        else:
            if bool(match('\s+\S', after)):
                # If the following line starts with whitespace, replace it
                # with a newline, to protect in the event that the printed
                # content ended with an end-of-environment command
                after = sub('^\s+', '\n', after)
        # Issue warnings, if warranted
        # Warn about `\endinput`
        if (r'\endinput' in print_replacement and 
                print_replacement.count(r'\endinput') != print_replacement.count(r'\string\endinput')):
            print('* DePythonTeX warning:')
            print('    "\\endinput" was present in printed content near line ' + str(linenum))
            print('    If this "\\endinput" was verbatim, you have nothing to worry about')
            print('    If this "\\endinput" is to be active, it should be printed last')
            print('    If you need "\\endinput" elsewhere, customize depythontex.py')
        # Warn if it looks like there are active `%` that could comment
        # out part of the original document.  We only need to check the
        # last line of printed content, because only there could
        # percent characters escape from their original confines within 
        # `\input`, and comment out part of the document.
        if print_replacement.endswith('\n'):
            if print_replacement.count('\n') > 1:
                last_line = print_replacement.rsplit('\n', 2)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following newline')
        else:
            if '\n' in print_replacement:
                last_line = print_replacement.rsplit('\n', 1)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following text')
        # Warn if there were `\unskip`'s in the output, in case they weren't
        # positioned correctly
        if bool(match(r'\s*\\unskip', after)):
            print('* DePythonTeX warning:')
            print('    "\\unskip" survived substitution near line ' + str(linenum))
            print('    If it should have adjusted the spacing of printed content')
            print('    you should double-check the spacing')
    return (print_replacement, after)
    

def replace_print_env(name, arglist, linenum,
                      print_replacement, print_replacement_mode, source,
                      after):
    '''
    Typeset printed content from an environment.
    
    It is only ever called if there is indeed printed content to typeset.
    
    This should be similar to replace_print_cmd().  The main difference is
    that the environment context typically ends with a newline, so 
    substitution has to be a little different to ensure that spacing after
    the environment isn't modified.
    
    Args:
        name (str):  name of the environment
        arglist (list, of str/None):  all arguments given to the original 
            environment
        linenum (int):  line number in the original TeX document where the 
            environment began
        print_replacement (str):  printed content, read directly from file
            into a single string
        print_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX), inlineverb (or v) (as inline), 
            or verb (as environment)
        source (str/None):  source of the replacement content
        after (str):  text immediately following the command; important in
            some situations, because spacing can depend on what's next
    Returns:
        (replacement, after) (tuple, of str)
    
    #### The inlineverb and verb modes should work, but haven't been tested
    since there are currently no environments that use them; they are only
    used by `\printpythontex`, which is a command.
    ''' 
    if print_replacement_mode == 'verb':
        if print_replacement.count('\n') > 1:
            print('* DePythonTeX error:')
            print('    Attempt to print multiple lines of content near line ' + str(linenum))
            print('    This is not possible in inline verbatim mode')
            sys.exit(1)
        print_replacement = print_replacement.rstrip('\n')
        for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$', 
                      '=', '+', '-', '^', '_', '?', ';'):
            if delim not in print_replacement:
                break
        print_replacement = r'\verb' + delim + print_replacement + delim
        if not bool(match('[ \t]+\S', after)):
            # If there is text on the same line as the end of the 
            # environment, we're fine (this is unusual).  Otherwise, 
            # we need to toss the newline at the end of the environment
            # and gobble leading spaces.  Leading spaces need to be 
            # gobbled because previously they were at the beginning of a 
            # line, where they would have been discarded.
            if not bool(match('\s*$', after)):
                after = sub('^\s*?\n\s*', '', after)
    elif print_replacement_mode == 'verbatim':
        if bool(match('\s*?\n', after)):
            # Usually, we would end the verbatim environment with a newline.
            # This is fine if there is content in `after` before the next 
            # newline---in fact, it's desirable, because the verbatim package
            # doesn't allow for content on the same line as the end of the 
            # environment.  But if `after` is an empty line, then adding a 
            # newline will throw off spacing and must be avoided
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}'
        else:
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}\n'
    else:
        # When printed content is included as LaTeX code, we have to be 
        # particularly careful to ensure that the content produces the same 
        # output when substituted as when brought in by `\input`.  In 
        # particular, `\input` strips newlines from each line of content and 
        # adds a space at the end of each line.  This space is inside the
        # `\input`, so it will not merge with following spaces.  So when we 
        # substitute the content, sometimes we need to replace the final 
        # newline with a space that cannot be gobbled.
        #
        # It gets more complicated.  This final space is often not 
        # desirable.  It can be prevented by either printing an `\endinput` 
        # command, to terminate the `\input`, or printing a percent 
        # character % in the last line of the content, which comments out the
        # final newline.  So we must check for `\endinput` anywhere in 
        # printed content, and % in the final line, and remove any content 
        # after them.  It's also possible that the print is followed by 
        # an `\unskip` that eats the space, so we need to check for that too.
        if (print_replacement.endswith('\\endinput\n') and 
                not print_replacement.endswith('\\string\\endinput\n')):
            # If `\endinput` is present, everything from it on should be 
            # discarded, unless the `\endinput` is not actually a command
            # but rather a typeset name (for example, `\string\endinput` or 
            # `\verb|\endinput|`).  It's impossible to check for all cases in 
            # which `\endinput` is not a command (at least, without actually 
            # using LaTeX), and even checking for most of them would require 
            # a good bit of parsing.  We assume that `\endinput`, as a 
            # command, will only ever occur at the immediate end of the 
            # printed content.  Later, we issue a warning in case it appears 
            # anywhere else.
            print_replacement = print_replacement.rsplit(r'\endinput', 1)[0]
            if not bool(match('[ \t]+\S', after)):
                # If there is text on the same line as the end of the 
                # environment, we're fine (this is unusual).  Otherwise, 
                # we need to toss the newline at the end of the environment
                # and gobble leading spaces.  Leading spaces need to be 
                # gobbled because previously they were at the beginning of a 
                # line, where they would have been discarded.
                if not bool(match('\s*$', after)):
                    after = sub('^\s*?\n\s*', '', after)
        elif (print_replacement.endswith('%\n') and 
                not print_replacement.endswith('\\%\n') and 
                not print_replacement.endswith('\\string%\n')):
            # Perform an analogous check for a terminating percent characer %.
            # This case would be a bit easier to parse fully, since a percent 
            # that comments out the last newline would have to be in the 
            # final line of the replacement.  But it would still be 
            # very difficult to perform a complete check.  Later, we issue a 
            # warning if there is reason to think that a percent character 
            # was active in the last line.
            print_replacement = print_replacement.rsplit(r'%', 1)[0]
            if not bool(match('[ \t]+\S', after)):
                # If there is text on the same line as the end of the 
                # environment, we're fine (this is unusual).  Otherwise, 
                # we need to toss the newline at the end of the environment
                # and gobble leading spaces.  Leading spaces need to be 
                # gobbled because previously they were at the beginning of a 
                # line, where they would have been discarded.
                if not bool(match('\s*$', after)):
                    after = sub('^\s*?\n\s*', '', after)
        else:
            # By default, LaTeX strips newlines and adds a space at the end 
            # of each line of content that is brought in by `\input`.  This 
            # may or may not be desirable, but we replicate the effect here 
            # for consistency with the original document.  We use `\space{}` 
            # because plain `\space` would gobble a following space, which 
            # isn't consistent with the `\input` behavior being replicated.
            if bool(match(r'\s*\\unskip\s+\S', after)):
                # If there's an `\unskip`, fix the spacing and remove the 
                # `\unskip`
                print_replacement = print_replacement.rstrip(' \t\n')
                after = sub(r'^\s*\\unskip\s+', '', after)
            elif bool(match('[ \t]+\S', after)):
                # If the next character after the end of the environment is 
                # not whitespace (usually not allowed), we can just leave
                # the `\n` in printed content, and it will yield a space.  
                # So we need do nothing.  But if there is text on that line 
                # we need `\space{}`.
                after = sub('^\s+', '\\space', after)
                forced_double_space_list.append((name, linenum))
            else:
                # If the line at the end of the environment is blank,
                # we can just discard it and keep the newline at the end of 
                # the printed content; the newline gives us the needed space
                after = after.split('\n', 1)[1]
        # Issue warnings, if warranted
        # Warn about `\endinput`
        if (r'\endinput' in print_replacement and 
                print_replacement.count(r'\endinput') != print_replacement.count(r'\string\endinput')):
            print('* DePythonTeX warning:')
            print('    "\\endinput" was present in printed content near line ' + str(linenum))
            print('    If this "\\endinput" was verbatim, you have nothing to worry about')
            print('    If this "\\endinput" is to be active, it should be printed last')
            print('    If you need "\\endinput" elsewhere, customize depythontex.py')
        # Warn if it looks like there are active `%` that could comment
        # out part of the original document.  We only need to check the
        # last line of printed content, because only there could
        # percent characters escape from their original confines within 
        # `\input`, and comment out part of the document.
        if print_replacement.endswith('\n'):
            if print_replacement.count('\n') > 1:
                last_line = print_replacement.rsplit('\n', 2)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following newline')
        else:
            if '\n' in print_replacement:
                last_line = print_replacement.rsplit('\n', 1)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following text')
        # Warn if there were `\unskip`'s in the output, in case they weren't
        # positioned correctly
        if bool(match(r'\s*\\unskip', after)):
            print('* DePythonTeX warning:')
            print('    "\\unskip" survived substitution near line ' + str(linenum))
            print('    If it should have adjusted the spacing of printed content')
            print('    you should double-check the spacing')
    return (print_replacement, after)




# Deal with argv
# Parse argv
parser = argparse.ArgumentParser()
parser.add_argument('--version', action='version', 
                    version='DePythonTeX {0}'.format(version))
parser.add_argument('--encoding', default='utf-8', 
                    help='encoding for all text files (see codecs module for encodings)')
parser.add_argument('--overwrite', default=False, action='store_true',
                    help='overwrite existing output, if it exists (off by default)')
parser.add_argument('--listing', default='verbatim',
                    choices=('verbatim', 'fancyvrb', 'listings', 'minted', 'pythontex'),
                    help='style or package used for typesetting code')
parser.add_argument('--lexer-dict', default=None,
                    help='add mappings from Pygments lexer names to the language names of other highlighting packages; should be a comma-separated list of the form "<Pygments lexer>:<language>, <Pygments lexer>:<language>, ..."')
parser.add_argument('--preamble', default=None,
                    help='line of commands to add to output preamble')
parser.add_argument('--graphicspath', default=False, action='store_true',
                    help=r'Add the outputdir to the graphics path, by modifying an existing \graphicspath command or adding one.')
parser.add_argument('-o', '--output', default=None,
                    help='output file')
parser.add_argument('TEXNAME',
                    help='LaTeX file')
args = parser.parse_args()

# Process argv
encoding = args.encoding
listing = args.listing
if args.preamble is not None:
    preamble_additions.append(args.preamble)
if args.lexer_dict is not None:
    args.lexer_dict = args.lexer_dict.replace(' ', '').replace("'", "").replace('"','').strip('{}')
    for entry in args.lexer_dict.split(','):
        k, v = entry.split(':')
        lexer_dict[k] = v
if args.listing == 'verbatim':
    # In some contexts, the verbatim package might be desirable.
    # But we assume that the user wants minimal packages.
    # Also, the default verbatim environment doesn't allow text to follow the
    # end-of-environment command.
    # If the verbatim package is ever desired, simply uncomment the following:
    # preamble_additions.append('\\usepackage{verbatim}')
    pass
elif args.listing == 'fancyvrb':
    preamble_additions.append('\\usepackage{fancyvrb}')
elif args.listing == 'listings':
    preamble_additions.append('\\usepackage{listings}')
elif args.listing == 'minted':
    preamble_additions.append('\\usepackage{minted}')
elif args.listing == 'pythontex':
    preamble_additions.append('\\usepackage{pythontex}')




# Let the user know things have started
if args.output is not None:
    print('This is DePythonTeX {0}'.format(version))
    sys.stdout.flush()




# Make sure we have a valid texfile
texfile_name = os.path.expanduser(os.path.normcase(args.TEXNAME))
if not os.path.isfile(texfile_name):
    resolved = False
    if not texfile_name.endswith('.tex'):
        for ext in ('.tex', '.ltx', '.dtx'):
            if os.path.isfile(texfile_name + ext):
                texfile_name = texfile_name + ext
                resolved = True
                break
    if not resolved:
        print('* DePythonTeX error:')
        print('    Could not locate file "' + texfile_name + '"')
        sys.exit(1)
# Make sure we have a valid outfile
if args.output is not None:
    outfile_name = os.path.expanduser(os.path.normcase(args.output))
    if not args.overwrite and os.path.isfile(outfile_name):
        print('* DePythonTeX warning:')
        print('    Output file "' + outfile_name + '" already exists')
        ans = input('    Do you want to overwrite this file? [y,n]\n    ')
        if ans != 'y':
            sys.exit(1)
# Make sure the .depytx file exists    
depytxfile_name = texfile_name.rsplit('.')[0] + '.depytx'
if not os.path.isfile(depytxfile_name):
    print('* DePythonTeX error:')
    print('    Could not find DePythonTeX auxiliary file "' + depytxfile_name + '"')
    print('    Use package option depythontex to creat it')
    sys.exit(1)




# Start opening files and loading data
# Read in the LaTeX file
# We read into a list with an empty first entry, so that we don't have to 
# worry about zero indexing when comparing list index to file line number
f = open(texfile_name, 'r', encoding=encoding)
tex = ['']
tex.extend(f.readlines())
f.close()
# Load the .depytx
f = open(depytxfile_name, 'r', encoding=encoding)
depytx = f.readlines()
f.close()
# Process the .depytx by getting the settings contained in the last few lines
settings = dict()
n = len(depytx) - 1
while depytx[n].startswith('=>DEPYTHONTEX:SETTINGS#'):
    content = depytx[n].split('#', 1)[1].rsplit('#', 1)[0]
    k, v = content.split('=', 1)
    if v in ('true', 'True'):
        v = True
    elif v in ('false', 'False'):
        v = False
    settings[k] = v
    depytx[n] = ''
    n -= 1
# Check .depytx version to make sure it is compatible
if settings['version'] != version:
    print('* DePythonTeX warning:')
    print('    Version mismatch with DePythonTeX auxiliary file')
    print('    Do a complete compile cycle to update the auxiliary file')
    print('    Attempting to proceed')
# Go ahead and open the outfile, even though we don't need it until the end
# This lets us change working directories for convenience without worrying 
# about having to modify the outfile path
if args.output is not None:
    outfile = open(outfile_name, 'w', encoding=encoding)




# Change working directory to the document directory
# Technically, we could get by without this, but that would require a lot of 
# path modification.  This way, we can just use all paths straight out of the 
# .depytx without any modification, which is much simpler and less error-prone.
if os.path.split(texfile_name)[0] != '':
    os.chdir(os.path.split(texfile_name)[0])



  
# Open and process the file of macros
# Read in the macros
if os.path.isfile(settings['macrofile']):
    f = open(settings['macrofile'], 'r', encoding=encoding)
    macros = f.readlines()
    f.close()
else:
    print('* DePythonTeX error:')
    print('    The macro file could not be found:')
    print('      "' + settings['macrofile'] + '"')
    print('    Run PythonTeX to create it')
    sys.exit(1)
# Create a dict for storing macros
macrodict = defaultdict(list)
# Create variables for keeping track of whether we're inside a macro or 
# environment
# These must exist before we begin processing
inside_macro = False
inside_environment = False
# Loop through the macros, and extract everything
# We just extract content; we get content wrappers later, when we process all
# substituted content
for line in macros:
    if inside_macro:
        # If we're in a macro, look for the end-of-macro command
        if r'\endpytx@SVMCR' in line:
            # If the current line contains the end-of-macro command, split 
            # off any content that comes before it.  Also reset 
            # `inside_macro`.
            macrodict[current_macro].append(line.rsplit(r'\endpytx@SVMCR', 1)[0])
            inside_macro = False
        else:
            # If the current line doesn't end the macro, we add the whole 
            # line to the macro dict
            macrodict[current_macro].append(line)
    elif inside_environment:
        if line.startswith(end_environment):
            # If the environment is ending, we reset inside_environment
            inside_environment = False
        else:
            # If we're still in the environment, add the current line to the 
            # macro dict
            macrodict[current_macro].append(line)
    else:
        # If we're not in a macro or environment, we need to figure out which
        # we are dealing with (if either; there are blank lines in the macro
        # file to increase readability).  Once we've determined which one,
        # we need to get its name and extract any content.
        if line.startswith(r'\begin{'):
            # Any \begin will indicate a use of fancyvrb to save verbatim 
            # content, since that is the only time an environment is used in 
            # the macro file.  All other content is saved in a standard macro.
            # We extract the name of the macro in which the verbatim content 
            # is saved.
            current_macro = line.rsplit('{', 1)[1].rstrip('}\n')
            inside_environment = True
            # We assemble the end-of-environment string we will need to look
            # for.  We don't assume any particular name, for generality.
            end_environment = r'\end{' + line.split('}', 1)[0].split('{', 1)[1] + '}'
            # Code typset in an environment needs to have a leading newline,
            # because the content of a normal verbatim environment keeps its
            # leading newline.
            macrodict[current_macro].append('\n')
        elif line.startswith(r'\pytx@SVMCR{'):
            # Any regular macro will use `\pytx@SVMCR`
            current_macro = line.split('{', 1)[1].split('}', 1)[0]
            inside_macro = True
            # Any content will always be on the next line, so we don't need
            # to check for it




# Do the actual processing
# Create a variable for keeping track of the current line in the LaTeX file
# Start at 1, since the first entry in the tex list is `''`
texlinenum = 1
# Create a variable for storing the current line(s) we are processing.
# This contains all lines from immediately after the last successfully 
# processed line up to and including texlinenum.  We may have to process 
# multiple lines at once if a macro is split over multiple lines, etc.
texcontent = tex[texlinenum]
# Create a list for storing processed content.
texout = list()
# Loop through the depytx and process
for n, depytxline in enumerate(depytx):
    if depytxline.startswith('=>DEPYTHONTEX#'):
        # Process info
        depytxcontent = depytxline.split('#', 1)[1].rstrip('#\n')
        depy_type, depy_name, depy_args, depy_typeset, depy_linenum, depy_lexer = depytxcontent.split(':')
        if depy_lexer == '':
            depy_lexer = None
        
        # Do a quick check on validity of info
        # #### Eventually add 'cp' and 'pc'
        if not (depy_type in ('cmd', 'env') and
                all([letter in ('o', 'm', 'v', 'n', '|') for letter in depy_args]) and
                ('|' not in depy_args or (depy_args.count('|') == 1 and depy_args.endswith('|'))) and
                depy_typeset in ('c', 'p', 'n')):  
            print('* PythonTeX error:')
            print('    Invalid \\Depythontex string for operation on line ' + str(depy_linenum))
            print('    The offending string was ' + depytxcontent)
            sys.exit(1)
        # If depy_args contains a `|` to indicate `\obeylines`, strip it and 
        # store in a variable.  Create a bool to keep track of obeylines 
        # status, which governs whether we can look on the next line for 
        # arguments.  (If obeylines is active, a newline terminates the 
        # argument search.)
        if depy_args.endswith('|'):
            obeylines = True
            depy_args = depy_args.rstrip('|')
        else:
            obeylines = False
        # Get the line number as an integer
        # We don't have to adjust for zero indexing in tex
        depy_linenum = int(depy_linenum)
        
        
        # Check for information passed from LaTeX
        # This will be extra listings information, or replacements to plug in
        code_replacement = None
        code_replacement_mode = None
        print_replacement = None
        print_replacement_mode = None
        firstnumber = None
        source = None
        scan_ahead_line = n + 1
        nextdepytxline = depytx[scan_ahead_line]
        while not nextdepytxline.startswith('=>DEPYTHONTEX#'):
            if nextdepytxline.startswith('LISTING:'):
                listingcontent = nextdepytxline.split(':', 1)[1].rstrip('\n')
                if bool(match(r'firstnumber=\d+$', listingcontent)):
                    firstnumber = listingcontent.split('=', 1)[1]
                else:
                    print('* DePythonTeX error:')
                    print('    Unknown information in listings data on line ' + str(depy_linenum))
                    print('    The listings content was "' + listingcontent + '"')
                    sys.exit(1)
            elif nextdepytxline.startswith('MACRO:'):
                source = 'macro'
                try:
                    typeset, macro = nextdepytxline.rstrip('\n').split(':', 2)[1:]
                except:
                    print('* DePythonTeX error:')
                    print('    Improperly formatted macro information on line ' + str(depy_linenum))
                    print('    The macro information was "' + nextdepytxline + '"')
                    sys.exit(1)
                if macro not in macrodict:
                    print('* DePythonTeX error:')
                    print('    Could not find replacement content for macro "' + macro + '"')
                    print('    This is probably because the document needs to be recompiled')
                    sys.exit(1)
                if typeset == 'c':
                    if depy_type == 'cmd':
                        code_replacement = ''.join(macrodict[macro]).strip('\n')
                    else:
                        code_replacement = ''.join(macrodict[macro])
                elif typeset == 'p':
                    print_replacement = ''.join(macrodict[macro])
                else:
                    print('* DePythonTeX error:')
                    print('    Improper typesetting information for macro information on line ' + str(depy_linenum))
                    print('    The macro information was "' + nextdepytxline + '"')
                    sys.exit(1)
            elif nextdepytxline.startswith('FILE:'):
                source = 'file'
                try:
                    typeset, f_name = nextdepytxline.rstrip('\n').split(':', 2)[1:]    
                except:
                    print('* DePythonTeX error:')
                    print('    Improperly formatted file information on line ' + str(depy_linenum))
                    print('    The file information was "' + nextdepytxline + '"')
                    sys.exit(1)
                # Files that are brought in have an optional mode that 
                # determines if they need special handling (for example, verbatim)
                if ':mode=' in f_name:
                    f_name, mode = f_name.split(':mode=')
                else:
                    mode = None
                f = open(f_name, 'r', encoding=encoding)
                replacement = f.read()
                f.close()
                if typeset == 'c':
                    code_replacement_mode = mode
                    if depy_type == 'cmd' and code_replacement_mode != 'verbatim':
                        # Usually, code from commands is typeset with commands
                        # and code from environments is typeset in 
                        # environments.  The except is code from commands 
                        # that bring in external files, like `\inputpygments`
                        code_replacement = replacement
                    else:
                        # If we're replacing an environment of code with a
                        # file, then we lose the newline at the beginning
                        # of the environment, and need to get it back.
                        code_replacement = '\n' + replacement                    
                elif typeset == 'p':
                    print_replacement_mode = mode
                    print_replacement = replacement                    
                else:
                    print('* DePythonTeX error:')
                    print('    Improper typesetting information for file information on line ' + str(depy_linenum))
                    print('    The file information was "' + nextdepytxline + '"')
                    sys.exit(1)
            # Increment the line in depytx to check for more information 
            # from LaTeX
            scan_ahead_line += 1
            if scan_ahead_line == len(depytx):
                break
            else:
                nextdepytxline = depytx[scan_ahead_line]
        
        
        # If the line we're looking for is within the range currently held by
        # texcontent, do nothing.  Otherwise, transfer content from tex
        # to texout until we get to the line of tex that we're looking for
        if depy_linenum > texlinenum:
            texout.append(texcontent)
            texlinenum += 1
            while texlinenum < depy_linenum:
                texout.append(tex[texlinenum])
                texlinenum += 1
            texcontent = tex[texlinenum]

        
        # Deal with arguments
        # All arguments are parsed and stored in a list variables, even if 
        # they are not used, for completeness; this makes it easy to add 
        # functionality
        # Start by splitting the current line into what comes before the 
        # command or environment, and what is after it
        if depy_type == 'cmd':
            try:
                before, after = texcontent.split('\\' + depy_name, 1)
            except:
                print('* DePythonTeX error:')
                print('    Could not find command "' + depy_name + '" on line ' + str(depy_linenum))
                sys.exit(1)
        else:  # depy_type == 'env':
            try:
                before, after = texcontent.split(r'\begin{' + depy_name + '}', 1)
            except:
                print('* DePythonTeX error:')
                print('    Could not find environment "' + depy_name + '" on line ' + str(depy_linenum))
                sys.exit(1)
        # We won't need the content from before the command or environment 
        # again, so we go ahead and store it
        texout.append(before)
        
        # Parse the arguments
        # Create a list for storing the recovered arguments
        arglist = list()
        for argindex, arg in enumerate(depy_args):
            if arg == 'n':
                pass
            elif arg == 'o':
                if after[0] == '[':
                    # Account for possible line breaks before end of arg
                    while ']' not in after:
                        texlinenum += 1
                        after += tex[texlinenum]                  
                    optarg, after = after[1:].split(']', 1)
                else:
                    if obeylines:
                        # Take into account possible whitespace before arg
                        if bool(match('[ \t]*\[', after)):
                            after = after.split('[', 1)[1]
                            while ']' not in after:
                                texlinenum += 1
                                after += tex[texlinenum]               
                            optarg, after = after.split(']', 1)
                        else:
                            optarg = None
                            # If this is the last arg, and it wasn't found,
                            # the macro should eat all whitespace following it
                            if argindex == len(depy_args) - 1:
                                after = sub('^[ \t]*', '', after)
                    else:
                        # Allow peeking ahead a line for the argument
                        if bool(match('\s*$', after)) and after.count('\n') < 2:
                            texlinenum += 1
                            after += tex[texlinenum]
                        # Take into account possible whitespace before arg
                        if bool(match('\s*\[', after)):
                            after = after.split('[', 1)[1]
                            while ']' not in after:
                                texlinenum += 1
                                after += tex[texlinenum]               
                            optarg, after = after.split(']', 1)
                        else:
                            optarg = None
                            # Account for eating whitespace afterward, if arg not found
                            if argindex == len(depy_args) - 1:
                                if bool(match('\s*$', after)) and after.count('\n') < 2:
                                    texlinenum += 1
                                    after += tex[texlinenum]
                                if not bool(match('\s*$', after)):
                                    after = sub('^\s*', '', after)
                arglist.append(optarg)
            elif arg == 'm':
                # Account for possible line breaks or spaces before arg
                if after[0] == '{':
                    after = after[1:]
                else:
                    if obeylines:
                        # Account for possible leading whitespace
                        if bool(match('[ \t\f\v]*\{', after)):
                            after = after.split('{', 1)[1]
                        else:
                            print('* DePythonTeX error:')
                            print('    Flawed mandatory argument for "' + depy_name + '" on line ' + str(depy_linenum))
                            sys.exit(1)
                    else:
                        # Peek ahead a line if needed
                        if bool(match('\s*$', after)) and after.count('\n') < 2:
                            texlinenum += 1
                            after += tex[texlinenum]
                        if bool(match('\s*\{', after)):
                            after = after.split('{', 1)[1]
                        else:
                            print('* DePythonTeX error:')
                            print('    Flawed mandatory argument for "' + depy_name + '" on line ' + str(depy_linenum))
                            sys.exit(1)
                # Go through the argument character by character to find the
                # closing brace.
                # If possible, use a very simple approach
                if (r'\{' not in after and r'\}' not in after and 
                        r'\string' not in after and 
                        after.count('{') + 1 == after.count('}')):
                    pos = 0
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            lbraces += 1
                        elif after[pos] == '}':
                            rbraces += 1
                        if lbraces == rbraces:
                            break
                        pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                # If a simple parsing approach won't work, parse in much 
                # greater depth
                else:
                    pos = 0
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            # If the current character is a brace, we count it
                            lbraces += 1
                            if lbraces == rbraces:
                                break
                            pos += 1
                        elif after[pos] == '}':
                            # If the current character is a brace, we count it
                            rbraces += 1
                            if lbraces == rbraces:
                                break
                            pos += 1
                        elif after[pos:].startswith(r'\string'):
                            # If the current position marks the beginning of `\string`, we
                            # resolve the `\string` command
                            # First, jump ahead to after `\string`
                            pos += 7 #+= len(r'\string')
                            # See if `\string` is followed by a regular macro
                            # If so, jump past it; otherwise, figure out if a 
                            # single-character macro, or just a single character, is next,
                            # and jump past it
                            standard_macro = match(r'\\[a-zA-Z]+', line[pos:])
                            if bool(standard_macro):
                                pos += standard_macro.end()
                            elif line[pos] == '\\':
                                pos += 2
                            else:
                                pos += 1
                        elif line[pos] == '\\':
                            # If the current position is a backslash, figure out what 
                            # macro is used, and jump past it
                            # The macro must either be a standard alphabetic macro,
                            # or a single-character macro
                            standard_macro = match(r'\\[a-zA-Z]+', line[pos:])
                            if bool(standard_macro):
                                pos += standard_macro.end()
                            else:
                                pos += 2
                        else:
                            pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                mainarg = after[:pos]
                after = after[pos+1:]
                arglist.append(mainarg)
            elif arg == 'v':
                if after[0] == '{':
                    # Account for the possibility of matched brace delimiters
                    # Not all verbatim commands allow for these
                    pos = 1
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            lbraces += 1
                        elif after[pos] == '}':
                            rbraces += 1
                        if lbraces == rbraces:
                            break
                        pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                    mainarg = after[1:pos]
                    after = after[pos+1:]
                else:
                    # Deal with matched character delims
                    delim = after[0]
                    while after.count(delim) < 2:
                        texlinenum += 1
                        after += tex[texlinenum]
                    mainarg, after = after[1:].split(delim, 1)
                arglist.append(mainarg)
            
        
        # Do substitution, depending on what is required
        # Need a variable for processed content to be added to texout
        processed = None
        if depy_typeset == 'c':
            if depy_type == 'cmd':
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_code_cmd(depy_name, arglist, 
                                                         depy_linenum, 
                                                         code_replacement,
                                                         code_replacement_mode,
                                                         after, depy_lexer,
                                                         firstnumber)
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if code_replacement is None:
                    if end_environment not in after:
                        while True:
                            texlinenum += 1
                            after += tex[texlinenum]
                            if end_environment in tex[texlinenum]:
                                break
                    code_replacement, after = after.split(end_environment, 1)
                    # If there's content on the line with the end-environment
                    # command, it should be discarded, to imitate TeX
                    if not code_replacement.endswith('\n'):
                        code_replacement = code_replacement.rsplit('\n', 1)[0] + '\n'
                    # Take care of `gobble`
                    if settings['gobble'] == 'auto':
                        code_replacement = textwrap.dedent(code_replacement)
                else:
                    if end_environment not in after:
                        while True:
                            texlinenum += 1
                            if end_environment in tex[texlinenum]:
                                after = tex[texlinenum]
                                break
                    after = after.split(end_environment, 1)[1]
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_code_env(depy_name, arglist,
                                                         depy_linenum,
                                                         code_replacement,
                                                         code_replacement_mode,
                                                         after, depy_lexer, 
                                                         firstnumber)
        elif depy_typeset == 'p' and print_replacement is not None:
            if depy_type == 'cmd':
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_print_cmd(depy_name, arglist, 
                                                          depy_linenum,
                                                          print_replacement,
                                                          print_replacement_mode,
                                                          source,
                                                          after)
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if end_environment not in after:
                    while True:
                        texlinenum += 1
                        if end_environment in tex[texlinenum]:
                            after = tex[texlinenum]
                            break
                after = after.split(end_environment, 1)[1]
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_print_env(depy_name, arglist, 
                                                          depy_linenum,
                                                          print_replacement, 
                                                          print_replacement_mode,
                                                          source,
                                                          after)
        else:  # depy_typeset == 'n' or (depy_typeset == 'p' and print_replacement is None):
            if depy_type == 'cmd':
                texcontent = after
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if end_environment not in after:
                    while True:
                        texlinenum += 1
                        if end_environment in tex[texlinenum]:
                            after = tex[texlinenum]
                            break
                after = after.split(end_environment, 1)[1]
                if bool(match('\s*\n', after)):
                    # If the line following `after` is whitespace, it should
                    # be stripped, since most environments throw away
                    # anything after the end of the environment
                    after = after.split('\n')[1]
                texcontent = after
        # #### Once it's supported on the TeX side, need to add support for
        # pc and cp
        
        
        # Store any processed content
        if processed is not None:
            texout.append(processed)


# Transfer anything that's left in tex to texout
texout.append(texcontent)
texout.extend(tex[texlinenum+1:])




# Replace the `\usepackage{pythontex}`
for n, line in enumerate(texout):
    if '{pythontex}' in line:
        startline = n
        while '\\usepackage' not in texout[startline] and startline >= 0:
            startline -= 1
        if startline == n:
            if bool(search(r'\\usepackage(?:\[.*?\]){0,1}\{pythontex\}', line)):
                texout[n] = sub(r'\\usepackage(?:\[.*?\]){0,1}\{pythontex\}', '', line)
                if texout[n].isspace():
                    texout[n] = ''
                break
        else:
            content = ''.join(texout[startline:n+1])
            if bool(search(r'(?s)\\usepackage(?:\[.*?\]\s*){0,1}\{pythontex\}', content)):
                replacement = sub(r'(?s)\\usepackage(?:\[.*?\]\s*){0,1}\{pythontex\}', '', content)
                if replacement.isspace():
                    replacement = ''
                texout[startline] = replacement
                for l in range(startline+1, n+1):
                    texout[l] = ''
                break
    elif line.startswith(r'\begin{document}'):
        break
if preamble_additions:
    texout[n] += '\n'.join(preamble_additions) + '\n'
# Take care of graphicspath
if args.graphicspath and settings['graphicx']:
    for n, line in enumerate(texout):
        if '\\graphicspath' in line and not bool(match('\s*%', line)):
            texout[n] = line.replace('\\graphicspath{', '\\graphicspath{{' + settings['outputdir'] +'/}')
            break
        elif line.startswith(r'\begin{document}'):
            texout[n] = '\\graphicspath{{' + settings['outputdir'] + '/}}\n' + line
            break




# Print any final messages
if forced_double_space_list:
    print('* DePythonTeX warning:')
    print('    A trailing double space was forced with "\\space{}" for the following')
    print('    This can happen when printed content is included inline')
    print('    The forced double space is only an issue if it is not intentional')
    for name, linenum in forced_double_space_list:
        print('      "' + name + '" near line ' + str(linenum))




# Write output
if args.output is not None:
    for line in texout:
        outfile.write(line)
    outfile.close()
else:
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter(encoding)(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter(encoding)(sys.stderr.buffer, 'strict')
    for line in texout:
        sys.stdout.write(line)

########NEW FILE########
__FILENAME__ = depythontex3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
PythonTeX depythontex script.

This script takes a LaTeX document that uses the PythonTeX package and 
creates a new document that does not depend on PythonTeX.  It substitutes all 
externally generated content into a copy of the original LaTeX document.  
This is useful when you need a document that relies on few external packages 
or custom macros (for example, for submission to a journal or conversion to 
another document format).

If you just want to share a document that uses PythonTeX, keep in mind that 
the document can be modified and compiled just like a regular LaTeX document, 
without needing Python or any other external tools, so long as the following 
conditions are met:

  * A copy of pythontex.sty is included with the document.
  * The pythontex-files-<name> directory is included with the document.
  * The PythonTeX-specific parts of the document are not modified.

To work, this script requires that the original LaTeX document be compiled 
with the package option `depythontex`.  That creates an auxiliary file with 
the extension .depytx that contains information about all content that needs
to be substituted.

This script is purposely written in a simple, largely linear form to 
facilitate customization.  Most of the key substitutions are performed by a 
few functions defined near the beginning of the script, so if you need custom
substitutions, you should begin there.  By default, all typeset code is 
wrapped in `\verb` commands and verbatim environments, since these have the 
greatest generality.  However, the command-line option --listing allows code 
to be typeset with the fancyvrb, listings, minted, or PythonTeX packages 
instead.

The script automatically extracts all arguments of all commands and 
environments that it replaces, so that these are available if desired for 
customized substitution.  Two additional pieces of information are also 
available for any typeset code:  the Pygments lexer (often the same as the 
language) and the starting line number (if line numbering was used).

Keep in mind that some manual adjustments may be required after a document is
depythontex'ed.  While depythontex attempts to create an exact copy of the 
original document, in many cases an identical copy is impossible.  For 
example, typeset code may have a different appearance or layout when it is 
typeset with a different package.


Copyright (c) 2013-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
#// Python 2
#from __future__ import absolute_import
#from __future__ import division
#from __future__ import print_function
#from __future__ import unicode_literals
#\\ End Python 2
import sys
import os
#// Python 2
#if sys.version_info.major != 2:
#    sys.exit('This version of the PythonTeX script requires Python 2.')
#\\ End Python 2
#// Python 3
if sys.version_info.major != 3:
    sys.exit('This version of the PythonTeX script requires Python 3.')
#\\ End Python 3

#// Python 2
#from io import open
#input = raw_input
#\\ End Python 2
import argparse
from collections import defaultdict
from re import match, sub, search
import textwrap
import codecs


# Script parameters
# Version
version = 'v0.13-beta'


# Functions and parameters for customizing the script output

# Style or package for replacing code listings
# This is actually set via command-line option --listing
# It is created here simply for reference
listing = None  #'verbatim', 'fancyvrb', 'listings', 'minted', 'pythontex'

# List of things to add to the preamble
# It can be appended to via the command-line option --preamble
# It is also appended to based on the code listing style that is used
# And it could be manually edited here as well, as long as it remains a list
preamble_additions = list()

# Lexer dict
# If you are using Pygments lexers that don't directly correspond to the 
# languages used by the listings package, you can submit replacements via the 
# command line option --lexer-dict, or edit this dict manually here.  When 
# listings is used, all lexers are checked against this dict to see if a 
# substitution should be made.  This approach could easily be modified to 
# work with another, non-Pygments highlighting package.
lexer_dict = dict()


def replace_code_cmd(name, arglist, linenum, code_replacement, 
                     code_replacement_mode, after, lexer, firstnumber):
    '''
    Typeset code from a command with a command.
    
    It is only ever called if there is indeed code to typeset.
    
    Usually, code from a command is also typeset with a command.  This 
    function primarily deals with that case.  In cases where code from a 
    command is typeset with an environment (for example, `\inputpygments`),
    this function performs some preprocessing and then uses 
    replace_code_env() to do the real work.  This approach prevents the two
    functions from unnecessarily duplicating each other, while still giving
    the desired output.
    
    Args:
        name (str):  name of the command
        arglist (list, of str/None):  all arguments given to the original 
            command; the last argument is what is typeset, unless a 
            code_replacement is specified or other instructions are given
        linenum (int):  line number in the original TeX document
        code_replacement (str/None):  replacement for the code; usually None
            for commands, because typically the code to be typeset is the 
            last argument passed to the command, rather than something 
            captured elsewhere (like the body of an environment) or something
            preprocessed (like a console environment's content)
        code_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX; generally unused for code), 
            verb (inline), or verbatim (environment)
        after (str):  text immediately following the command; usually 
            shouldn't be needed
        lexer (str/None):  Pygments lexer
    Returns:
        (replacement, after) (tuple, of str)
    
    '''
    # Get the correct replacement
    if code_replacement is None:
        code_replacement = arglist[-1]
    
    # We only consider two possible modes of typesetting, verbatim and inline
    # verbatim
    if code_replacement_mode == 'verbatim':
        # Sometimes we must replace a command with an environment, for 
        # example, for `\inputpygments`
        
        # Make sure the introduction of an environment where a command was 
        # previously won't produce errors with following content; make sure 
        # that any following content is on a separate line
        if bool(match('[ \t]*\S', after)):
            after = '\n' + after
        # Rather than duplicating much of replace_code_env(), just use it
        return replace_code_env(name, arglist, linenum, code_replacement, 
                                code_replacement_mode, after, lexer, firstnumber)
    else:
        # Usually, we're replacing a command with a command
        
        # Wrap the replacement in appropriate delimiters
        if (listing in ('verbatim', 'fancyvrb', 'minted') or 
                (listing in ('listings', 'pythontex') and 
                ('{' in code_replacement or '}' in code_replacement))):
            for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$', 
                          '=', '+', '-', '^', '_', '?', ';'):
                if delim not in code_replacement:
                    break
            code_replacement = delim + code_replacement + delim
        else:
            code_replacement = '{' + code_replacement + '}'
        # Assemble the actual replacement
        if listing in ('verbatim', 'minted'): # `\mint` isn't for inline use
            code_replacement = r'\verb' + code_replacement
        elif listing == 'fancyvrb':
            code_replacement = r'\Verb' + code_replacement
        elif listing == 'listings':
            if lexer is None:
                code_replacement = r'\lstinline[language={}]' + code_replacement
            else:
                if lexer in lexer_dict:
                    lexer = lexer_dict[lexer]
                code_replacement = r'\lstinline[language=' + lexer + ']' + code_replacement
        elif listing == 'pythontex':
            if lexer is None:
                code_replacement = r'\pygment{text}' + code_replacement
            else:
                code_replacement = r'\pygment{' + lexer + '}' + code_replacement
        return (code_replacement, after)
    

def replace_code_env(name, arglist, linenum, code_replacement, 
                     code_replacement_mode, after, lexer, firstnumber):
    '''
    Typeset code from an environment with an environment.
    
    It is only ever called if there is indeed code to typeset.
    
    Usually it is only used to typeset code from an environment.  However,
    some commands bring in code that must be typeset as an environment.  In
    those cases, replace_code_cmd() is called initially, and after it 
    performs some preprocessing, this function is called.  This approach
    avoids unnecessary duplication between the two functions.
    
    Args:
        name (str):  name of the environment
        arglist (list, of str/None):  all arguments given to the original 
            environment
        linenum (int):  line number in the original TeX document where 
            the environment began
        code_replacement (str):  replacement for the code; unlike the case of
            commands, this is always not None if the function is called
        code_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX; generally unused for code), 
            verb (inline), or verbatim (environment)
        after (str):  text immediately following the environment; usually 
            shouldn't be needed
        lexer (str/None):  Pygments lexer
        firstnumber (str/None):  the first number of the listing, if the listing
            had numbered lines
    Returns:
        (replacement, after) (tuple, of str)
    
    '''
    # Currently, there is no need to test for code_replacement_mode, because
    # this function is only ever called if the mode is 'verbatim'.  That may
    # change in the future, but it seems unlikely that code entered in an
    # environment would end up typeset with a command.
    if listing == 'verbatim':
        pre = '\\begin{verbatim}'
        post = '\\end{verbatim}'
    elif listing == 'fancyvrb':
        if firstnumber is None:
            pre = '\\begin{Verbatim}'
        else:
            pre = '\\begin{{Verbatim}}[numbers=left,firstnumber={0}]'.format(firstnumber)
        post = '\\end{Verbatim}'        
    elif listing == 'listings':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{lstlisting}[language={}]'
            else:
                pre = '\\begin{{lstlisting}}[language={{}},numbers=left,firstnumber={0}]'.format(firstnumber)
        else:
            if lexer in lexer_dict:
                lexer = lexer_dict[lexer]
            if firstnumber is None:
                pre = '\\begin{{lstlisting}}[language={0}]'.format(lexer)
            else:
                pre = '\\begin{{lstlisting}}[language={0},numbers=left,firstnumber={1}]'.format(lexer, firstnumber)
        post = '\\end{lstlisting}'
    elif listing == 'minted':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{minted}{text}'
            else:
                pre = '\\begin{{minted}}[linenos,firstnumber={0}]{{text}}'.format(firstnumber)
        else:
            if firstnumber is None:
                pre = '\\begin{{minted}}{{{0}}}'.format(lexer)
            else:
                pre = '\\begin{{minted}}[linenos,firstnumber={0}]{{{1}}}'.format(firstnumber, lexer)
        post = '\\end{minted}'
    elif listing == 'pythontex':
        if lexer is None:
            if firstnumber is None:
                pre = '\\begin{pygments}{text}'
            else:
                pre = '\\begin{{pygments}}[numbers=left,firstnumber={0}]{{text}}'.format(firstnumber)
        else:
            if firstnumber is None:
                pre = '\\begin{{pygments}}{{{0}}}'.format(lexer)
            else:
                pre = '\\begin{{pygments}}[numbers=left,firstnumber={0}]{{{1}}}'.format(firstnumber, lexer)
        post = '\\end{pygments}'
    code_replacement = pre + code_replacement + post
    return (code_replacement, after)


# We will need to issue a warning every time that a substitution of printed
# content results in a forced double space.  We could just do this as we go,
# but it's easier for the user to read if we just collect all the warnings
# of this type, and print them once.
forced_double_space_list = list()


def replace_print_cmd(name, arglist, linenum,
                      print_replacement, print_replacement_mode, source,
                      after):
    '''
    Typeset printed content from a command.
    
    It is only ever called if there is indeed printed content to typeset.
    
    Args:
        name (str):  name of the command
        arglist (list, of str/None):  all arguments given to the original 
            command
        linenum (int):  line number in the original TeX document
        print_replacement (str):  printed content, read directly from file
            into a single string
        print_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX), inlineverb (or v) (as inline), 
            or verb (as environment)
        source (str/None):  source of the replacement content
        after (str):  text immediately following the command; important in
            some situations, because spacing can depend on what's next
    Returns:
        (replacement, after) (tuple, of str)
    
    '''    
    if print_replacement_mode == 'verb':
        if print_replacement.count('\n') > 1:
            print('* DePythonTeX error:')
            print('    Attempt to print multiple lines of content near line ' + str(linenum))
            print('    This is not possible in inline verbatim mode')
            sys.exit(1)
        print_replacement = print_replacement.rstrip('\n')
        for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$', 
                      '=', '+', '-', '^', '_', '?', ';'):
            if delim not in print_replacement:
                break
        print_replacement = r'\verb' + delim + print_replacement + delim
    elif print_replacement_mode == 'verbatim':
        if bool(match('\s*?\n', after)):
            # Usually, we would end the verbatim environment with a newline.
            # This is fine if there is content in `after` before the next 
            # newline---in fact, it's desirable, because the verbatim package
            # doesn't allow for content on the same line as the end of the 
            # environment.  But if `after` is an empty line, then adding a 
            # newline will throw off spacing and must be avoided
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}'
        else:
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}\n'
    else:
        # When printed content from a file is included as LaTeX code, we have 
        # to be particularly careful to ensure that the content produces the 
        # same output when substituted as when brought in by `\input`.  In 
        # particular, `\input` strips newlines from each line of content and 
        # adds a space at the end of each line.  This space is inside the
        # `\input`, so it will not merge with following spaces.  So when we 
        # substitute the content, sometimes we need to replace the final 
        # newline with a space that cannot be gobbled.
        #
        # It gets more complicated.  This final space is often not 
        # desirable.  It can be prevented by either printing an `\endinput` 
        # command, to terminate the `\input`, or printing a percent 
        # character % in the last line of the content, which comments out the
        # final newline.  So we must check for `\endinput` anywhere in 
        # printed content, and % in the final line, and remove any content 
        # after them.  It's also possible that the print is followed by 
        # an `\unskip` that eats the space, so we need to check for that too.
        #
        # It turns out that the same approach is needed when a command like 
        # `\py` brings in content ending in a newline
        if (print_replacement.endswith('\\endinput\n') and 
                not print_replacement.endswith('\\string\\endinput\n')):
            # If `\endinput` is present, everything from it on should be 
            # discarded, unless the `\endinput` is not actually a command
            # but rather a typeset name (for example, `\string\endinput` or 
            # `\verb|\endinput|`).  It's impossible to check for all cases in 
            # which `\endinput` is not a command (at least, without actually 
            # using LaTeX), and even checking for most of them would require 
            # a good bit of parsing.  We assume that `\endinput`, as a 
            # command, will only ever occur at the immediate end of the 
            # printed content.  Later, we issue a warning in case it appears 
            # anywhere else.
            print_replacement = print_replacement.rsplit(r'\endinput', 1)[0]
        elif (print_replacement.endswith('%\n') and 
                not print_replacement.endswith('\\%\n') and 
                not print_replacement.endswith('\\string%\n')):
            # Perform an analogous check for a terminating percent characer %.
            # This case would be a bit easier to parse fully, since a percent 
            # that comments out the last newline would have to be in the 
            # final line of the replacement.  But it would still be 
            # very difficult to perform a complete check.  Later, we issue a 
            # warning if there is reason to think that a percent character 
            # was active in the last line.
            print_replacement = print_replacement.rsplit(r'%', 1)[0]
        elif print_replacement.endswith('\n'):
            # We can't just use `else` because that would catch content
            # from `\py` and similar
            # By default, LaTeX strips newlines and adds a space at the end 
            # of each line of content that is brought in by `\input`.  This 
            # may or may not be desirable, but we replicate the effect here 
            # for consistency with the original document.  We use `\space{}` 
            # because plain `\space` would gobble a following space, which 
            # isn't consistent with the `\input` behavior being replicated.
            if bool(match(r'\\unskip\s+\S', after)):
                # If there's an `\unskip`, fix the spacing and remove the 
                # `\unskip`.  Since this is inline, the `\unskip` must 
                # immediately follow the command to do any good; otherwise,
                # it eliminates spaces that precede it, but doesn't get into
                # the `\input` content.
                print_replacement = print_replacement.rstrip(' \t\n')
                after = sub(r'^\\unskip\s+', '', after)
            elif bool(match('\S', after)):
                # If the next character is not whitespace, we can just leave
                # the `\n`, and it will yield a space.
                pass
            elif bool(match('\s*$', after)):
                # If the rest of the current line, and the next line, are 
                # whitespace, we will get the correct spacing without needing
                # `\space{}`.  We could leave `\n`, but it would be 
                # extraneous whitespace.
                print_replacement = print_replacement[:-1]
            else:
                # Otherwise, we do need to insert `\space{}`
                # We keep the newline at the end of printed content, in case
                # it's at the end of an environment, and thus is needed to
                # protect the following content
                print_replacement += '\\space{}'
                after = sub('^\s+', '', after)
                forced_double_space_list.append((name, linenum))
        else:
            if bool(match('\s+\S', after)):
                # If the following line starts with whitespace, replace it
                # with a newline, to protect in the event that the printed
                # content ended with an end-of-environment command
                after = sub('^\s+', '\n', after)
        # Issue warnings, if warranted
        # Warn about `\endinput`
        if (r'\endinput' in print_replacement and 
                print_replacement.count(r'\endinput') != print_replacement.count(r'\string\endinput')):
            print('* DePythonTeX warning:')
            print('    "\\endinput" was present in printed content near line ' + str(linenum))
            print('    If this "\\endinput" was verbatim, you have nothing to worry about')
            print('    If this "\\endinput" is to be active, it should be printed last')
            print('    If you need "\\endinput" elsewhere, customize depythontex.py')
        # Warn if it looks like there are active `%` that could comment
        # out part of the original document.  We only need to check the
        # last line of printed content, because only there could
        # percent characters escape from their original confines within 
        # `\input`, and comment out part of the document.
        if print_replacement.endswith('\n'):
            if print_replacement.count('\n') > 1:
                last_line = print_replacement.rsplit('\n', 2)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following newline')
        else:
            if '\n' in print_replacement:
                last_line = print_replacement.rsplit('\n', 1)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following text')
        # Warn if there were `\unskip`'s in the output, in case they weren't
        # positioned correctly
        if bool(match(r'\s*\\unskip', after)):
            print('* DePythonTeX warning:')
            print('    "\\unskip" survived substitution near line ' + str(linenum))
            print('    If it should have adjusted the spacing of printed content')
            print('    you should double-check the spacing')
    return (print_replacement, after)
    

def replace_print_env(name, arglist, linenum,
                      print_replacement, print_replacement_mode, source,
                      after):
    '''
    Typeset printed content from an environment.
    
    It is only ever called if there is indeed printed content to typeset.
    
    This should be similar to replace_print_cmd().  The main difference is
    that the environment context typically ends with a newline, so 
    substitution has to be a little different to ensure that spacing after
    the environment isn't modified.
    
    Args:
        name (str):  name of the environment
        arglist (list, of str/None):  all arguments given to the original 
            environment
        linenum (int):  line number in the original TeX document where the 
            environment began
        print_replacement (str):  printed content, read directly from file
            into a single string
        print_replacement_mode (str/None):  mode in which the replacement is 
            to be typeset; raw/None (as TeX), inlineverb (or v) (as inline), 
            or verb (as environment)
        source (str/None):  source of the replacement content
        after (str):  text immediately following the command; important in
            some situations, because spacing can depend on what's next
    Returns:
        (replacement, after) (tuple, of str)
    
    #### The inlineverb and verb modes should work, but haven't been tested
    since there are currently no environments that use them; they are only
    used by `\printpythontex`, which is a command.
    ''' 
    if print_replacement_mode == 'verb':
        if print_replacement.count('\n') > 1:
            print('* DePythonTeX error:')
            print('    Attempt to print multiple lines of content near line ' + str(linenum))
            print('    This is not possible in inline verbatim mode')
            sys.exit(1)
        print_replacement = print_replacement.rstrip('\n')
        for delim in ('|', '/', '`', '!', '&', '#', '@', ':', '%', '~', '$', 
                      '=', '+', '-', '^', '_', '?', ';'):
            if delim not in print_replacement:
                break
        print_replacement = r'\verb' + delim + print_replacement + delim
        if not bool(match('[ \t]+\S', after)):
            # If there is text on the same line as the end of the 
            # environment, we're fine (this is unusual).  Otherwise, 
            # we need to toss the newline at the end of the environment
            # and gobble leading spaces.  Leading spaces need to be 
            # gobbled because previously they were at the beginning of a 
            # line, where they would have been discarded.
            if not bool(match('\s*$', after)):
                after = sub('^\s*?\n\s*', '', after)
    elif print_replacement_mode == 'verbatim':
        if bool(match('\s*?\n', after)):
            # Usually, we would end the verbatim environment with a newline.
            # This is fine if there is content in `after` before the next 
            # newline---in fact, it's desirable, because the verbatim package
            # doesn't allow for content on the same line as the end of the 
            # environment.  But if `after` is an empty line, then adding a 
            # newline will throw off spacing and must be avoided
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}'
        else:
            print_replacement = '\\begin{verbatim}\n' + print_replacement + '\\end{verbatim}\n'
    else:
        # When printed content is included as LaTeX code, we have to be 
        # particularly careful to ensure that the content produces the same 
        # output when substituted as when brought in by `\input`.  In 
        # particular, `\input` strips newlines from each line of content and 
        # adds a space at the end of each line.  This space is inside the
        # `\input`, so it will not merge with following spaces.  So when we 
        # substitute the content, sometimes we need to replace the final 
        # newline with a space that cannot be gobbled.
        #
        # It gets more complicated.  This final space is often not 
        # desirable.  It can be prevented by either printing an `\endinput` 
        # command, to terminate the `\input`, or printing a percent 
        # character % in the last line of the content, which comments out the
        # final newline.  So we must check for `\endinput` anywhere in 
        # printed content, and % in the final line, and remove any content 
        # after them.  It's also possible that the print is followed by 
        # an `\unskip` that eats the space, so we need to check for that too.
        if (print_replacement.endswith('\\endinput\n') and 
                not print_replacement.endswith('\\string\\endinput\n')):
            # If `\endinput` is present, everything from it on should be 
            # discarded, unless the `\endinput` is not actually a command
            # but rather a typeset name (for example, `\string\endinput` or 
            # `\verb|\endinput|`).  It's impossible to check for all cases in 
            # which `\endinput` is not a command (at least, without actually 
            # using LaTeX), and even checking for most of them would require 
            # a good bit of parsing.  We assume that `\endinput`, as a 
            # command, will only ever occur at the immediate end of the 
            # printed content.  Later, we issue a warning in case it appears 
            # anywhere else.
            print_replacement = print_replacement.rsplit(r'\endinput', 1)[0]
            if not bool(match('[ \t]+\S', after)):
                # If there is text on the same line as the end of the 
                # environment, we're fine (this is unusual).  Otherwise, 
                # we need to toss the newline at the end of the environment
                # and gobble leading spaces.  Leading spaces need to be 
                # gobbled because previously they were at the beginning of a 
                # line, where they would have been discarded.
                if not bool(match('\s*$', after)):
                    after = sub('^\s*?\n\s*', '', after)
        elif (print_replacement.endswith('%\n') and 
                not print_replacement.endswith('\\%\n') and 
                not print_replacement.endswith('\\string%\n')):
            # Perform an analogous check for a terminating percent characer %.
            # This case would be a bit easier to parse fully, since a percent 
            # that comments out the last newline would have to be in the 
            # final line of the replacement.  But it would still be 
            # very difficult to perform a complete check.  Later, we issue a 
            # warning if there is reason to think that a percent character 
            # was active in the last line.
            print_replacement = print_replacement.rsplit(r'%', 1)[0]
            if not bool(match('[ \t]+\S', after)):
                # If there is text on the same line as the end of the 
                # environment, we're fine (this is unusual).  Otherwise, 
                # we need to toss the newline at the end of the environment
                # and gobble leading spaces.  Leading spaces need to be 
                # gobbled because previously they were at the beginning of a 
                # line, where they would have been discarded.
                if not bool(match('\s*$', after)):
                    after = sub('^\s*?\n\s*', '', after)
        else:
            # By default, LaTeX strips newlines and adds a space at the end 
            # of each line of content that is brought in by `\input`.  This 
            # may or may not be desirable, but we replicate the effect here 
            # for consistency with the original document.  We use `\space{}` 
            # because plain `\space` would gobble a following space, which 
            # isn't consistent with the `\input` behavior being replicated.
            if bool(match(r'\s*\\unskip\s+\S', after)):
                # If there's an `\unskip`, fix the spacing and remove the 
                # `\unskip`
                print_replacement = print_replacement.rstrip(' \t\n')
                after = sub(r'^\s*\\unskip\s+', '', after)
            elif bool(match('[ \t]+\S', after)):
                # If the next character after the end of the environment is 
                # not whitespace (usually not allowed), we can just leave
                # the `\n` in printed content, and it will yield a space.  
                # So we need do nothing.  But if there is text on that line 
                # we need `\space{}`.
                after = sub('^\s+', '\\space', after)
                forced_double_space_list.append((name, linenum))
            else:
                # If the line at the end of the environment is blank,
                # we can just discard it and keep the newline at the end of 
                # the printed content; the newline gives us the needed space
                after = after.split('\n', 1)[1]
        # Issue warnings, if warranted
        # Warn about `\endinput`
        if (r'\endinput' in print_replacement and 
                print_replacement.count(r'\endinput') != print_replacement.count(r'\string\endinput')):
            print('* DePythonTeX warning:')
            print('    "\\endinput" was present in printed content near line ' + str(linenum))
            print('    If this "\\endinput" was verbatim, you have nothing to worry about')
            print('    If this "\\endinput" is to be active, it should be printed last')
            print('    If you need "\\endinput" elsewhere, customize depythontex.py')
        # Warn if it looks like there are active `%` that could comment
        # out part of the original document.  We only need to check the
        # last line of printed content, because only there could
        # percent characters escape from their original confines within 
        # `\input`, and comment out part of the document.
        if print_replacement.endswith('\n'):
            if print_replacement.count('\n') > 1:
                last_line = print_replacement.rsplit('\n', 2)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following newline')
        else:
            if '\n' in print_replacement:
                last_line = print_replacement.rsplit('\n', 1)[1]
            else:
                last_line = print_replacement
            if last_line.count('%') != last_line.count(r'\%') + last_line.count(r'\string%'):
                print('* DePythonTeX warning:')
                print('    One or more percent characters are on the last line of ')
                print('    printed content near line ' + str(linenum))
                print('    If they are not verbatim, they could comment out the following text')
        # Warn if there were `\unskip`'s in the output, in case they weren't
        # positioned correctly
        if bool(match(r'\s*\\unskip', after)):
            print('* DePythonTeX warning:')
            print('    "\\unskip" survived substitution near line ' + str(linenum))
            print('    If it should have adjusted the spacing of printed content')
            print('    you should double-check the spacing')
    return (print_replacement, after)




# Deal with argv
# Parse argv
parser = argparse.ArgumentParser()
parser.add_argument('--version', action='version', 
                    version='DePythonTeX {0}'.format(version))
parser.add_argument('--encoding', default='utf-8', 
                    help='encoding for all text files (see codecs module for encodings)')
parser.add_argument('--overwrite', default=False, action='store_true',
                    help='overwrite existing output, if it exists (off by default)')
parser.add_argument('--listing', default='verbatim',
                    choices=('verbatim', 'fancyvrb', 'listings', 'minted', 'pythontex'),
                    help='style or package used for typesetting code')
parser.add_argument('--lexer-dict', default=None,
                    help='add mappings from Pygments lexer names to the language names of other highlighting packages; should be a comma-separated list of the form "<Pygments lexer>:<language>, <Pygments lexer>:<language>, ..."')
parser.add_argument('--preamble', default=None,
                    help='line of commands to add to output preamble')
parser.add_argument('--graphicspath', default=False, action='store_true',
                    help=r'Add the outputdir to the graphics path, by modifying an existing \graphicspath command or adding one.')
parser.add_argument('-o', '--output', default=None,
                    help='output file')
parser.add_argument('TEXNAME',
                    help='LaTeX file')
args = parser.parse_args()

# Process argv
encoding = args.encoding
listing = args.listing
if args.preamble is not None:
    preamble_additions.append(args.preamble)
if args.lexer_dict is not None:
    args.lexer_dict = args.lexer_dict.replace(' ', '').replace("'", "").replace('"','').strip('{}')
    for entry in args.lexer_dict.split(','):
        k, v = entry.split(':')
        lexer_dict[k] = v
if args.listing == 'verbatim':
    # In some contexts, the verbatim package might be desirable.
    # But we assume that the user wants minimal packages.
    # Also, the default verbatim environment doesn't allow text to follow the
    # end-of-environment command.
    # If the verbatim package is ever desired, simply uncomment the following:
    # preamble_additions.append('\\usepackage{verbatim}')
    pass
elif args.listing == 'fancyvrb':
    preamble_additions.append('\\usepackage{fancyvrb}')
elif args.listing == 'listings':
    preamble_additions.append('\\usepackage{listings}')
elif args.listing == 'minted':
    preamble_additions.append('\\usepackage{minted}')
elif args.listing == 'pythontex':
    preamble_additions.append('\\usepackage{pythontex}')




# Let the user know things have started
if args.output is not None:
    print('This is DePythonTeX {0}'.format(version))
    sys.stdout.flush()




# Make sure we have a valid texfile
texfile_name = os.path.expanduser(os.path.normcase(args.TEXNAME))
if not os.path.isfile(texfile_name):
    resolved = False
    if not texfile_name.endswith('.tex'):
        for ext in ('.tex', '.ltx', '.dtx'):
            if os.path.isfile(texfile_name + ext):
                texfile_name = texfile_name + ext
                resolved = True
                break
    if not resolved:
        print('* DePythonTeX error:')
        print('    Could not locate file "' + texfile_name + '"')
        sys.exit(1)
# Make sure we have a valid outfile
if args.output is not None:
    outfile_name = os.path.expanduser(os.path.normcase(args.output))
    if not args.overwrite and os.path.isfile(outfile_name):
        print('* DePythonTeX warning:')
        print('    Output file "' + outfile_name + '" already exists')
        ans = input('    Do you want to overwrite this file? [y,n]\n    ')
        if ans != 'y':
            sys.exit(1)
# Make sure the .depytx file exists    
depytxfile_name = texfile_name.rsplit('.')[0] + '.depytx'
if not os.path.isfile(depytxfile_name):
    print('* DePythonTeX error:')
    print('    Could not find DePythonTeX auxiliary file "' + depytxfile_name + '"')
    print('    Use package option depythontex to creat it')
    sys.exit(1)




# Start opening files and loading data
# Read in the LaTeX file
# We read into a list with an empty first entry, so that we don't have to 
# worry about zero indexing when comparing list index to file line number
f = open(texfile_name, 'r', encoding=encoding)
tex = ['']
tex.extend(f.readlines())
f.close()
# Load the .depytx
f = open(depytxfile_name, 'r', encoding=encoding)
depytx = f.readlines()
f.close()
# Process the .depytx by getting the settings contained in the last few lines
settings = dict()
n = len(depytx) - 1
while depytx[n].startswith('=>DEPYTHONTEX:SETTINGS#'):
    content = depytx[n].split('#', 1)[1].rsplit('#', 1)[0]
    k, v = content.split('=', 1)
    if v in ('true', 'True'):
        v = True
    elif v in ('false', 'False'):
        v = False
    settings[k] = v
    depytx[n] = ''
    n -= 1
# Check .depytx version to make sure it is compatible
if settings['version'] != version:
    print('* DePythonTeX warning:')
    print('    Version mismatch with DePythonTeX auxiliary file')
    print('    Do a complete compile cycle to update the auxiliary file')
    print('    Attempting to proceed')
# Go ahead and open the outfile, even though we don't need it until the end
# This lets us change working directories for convenience without worrying 
# about having to modify the outfile path
if args.output is not None:
    outfile = open(outfile_name, 'w', encoding=encoding)




# Change working directory to the document directory
# Technically, we could get by without this, but that would require a lot of 
# path modification.  This way, we can just use all paths straight out of the 
# .depytx without any modification, which is much simpler and less error-prone.
if os.path.split(texfile_name)[0] != '':
    os.chdir(os.path.split(texfile_name)[0])



  
# Open and process the file of macros
# Read in the macros
if os.path.isfile(settings['macrofile']):
    f = open(settings['macrofile'], 'r', encoding=encoding)
    macros = f.readlines()
    f.close()
else:
    print('* DePythonTeX error:')
    print('    The macro file could not be found:')
    print('      "' + settings['macrofile'] + '"')
    print('    Run PythonTeX to create it')
    sys.exit(1)
# Create a dict for storing macros
macrodict = defaultdict(list)
# Create variables for keeping track of whether we're inside a macro or 
# environment
# These must exist before we begin processing
inside_macro = False
inside_environment = False
# Loop through the macros, and extract everything
# We just extract content; we get content wrappers later, when we process all
# substituted content
for line in macros:
    if inside_macro:
        # If we're in a macro, look for the end-of-macro command
        if r'\endpytx@SVMCR' in line:
            # If the current line contains the end-of-macro command, split 
            # off any content that comes before it.  Also reset 
            # `inside_macro`.
            macrodict[current_macro].append(line.rsplit(r'\endpytx@SVMCR', 1)[0])
            inside_macro = False
        else:
            # If the current line doesn't end the macro, we add the whole 
            # line to the macro dict
            macrodict[current_macro].append(line)
    elif inside_environment:
        if line.startswith(end_environment):
            # If the environment is ending, we reset inside_environment
            inside_environment = False
        else:
            # If we're still in the environment, add the current line to the 
            # macro dict
            macrodict[current_macro].append(line)
    else:
        # If we're not in a macro or environment, we need to figure out which
        # we are dealing with (if either; there are blank lines in the macro
        # file to increase readability).  Once we've determined which one,
        # we need to get its name and extract any content.
        if line.startswith(r'\begin{'):
            # Any \begin will indicate a use of fancyvrb to save verbatim 
            # content, since that is the only time an environment is used in 
            # the macro file.  All other content is saved in a standard macro.
            # We extract the name of the macro in which the verbatim content 
            # is saved.
            current_macro = line.rsplit('{', 1)[1].rstrip('}\n')
            inside_environment = True
            # We assemble the end-of-environment string we will need to look
            # for.  We don't assume any particular name, for generality.
            end_environment = r'\end{' + line.split('}', 1)[0].split('{', 1)[1] + '}'
            # Code typset in an environment needs to have a leading newline,
            # because the content of a normal verbatim environment keeps its
            # leading newline.
            macrodict[current_macro].append('\n')
        elif line.startswith(r'\pytx@SVMCR{'):
            # Any regular macro will use `\pytx@SVMCR`
            current_macro = line.split('{', 1)[1].split('}', 1)[0]
            inside_macro = True
            # Any content will always be on the next line, so we don't need
            # to check for it




# Do the actual processing
# Create a variable for keeping track of the current line in the LaTeX file
# Start at 1, since the first entry in the tex list is `''`
texlinenum = 1
# Create a variable for storing the current line(s) we are processing.
# This contains all lines from immediately after the last successfully 
# processed line up to and including texlinenum.  We may have to process 
# multiple lines at once if a macro is split over multiple lines, etc.
texcontent = tex[texlinenum]
# Create a list for storing processed content.
texout = list()
# Loop through the depytx and process
for n, depytxline in enumerate(depytx):
    if depytxline.startswith('=>DEPYTHONTEX#'):
        # Process info
        depytxcontent = depytxline.split('#', 1)[1].rstrip('#\n')
        depy_type, depy_name, depy_args, depy_typeset, depy_linenum, depy_lexer = depytxcontent.split(':')
        if depy_lexer == '':
            depy_lexer = None
        
        # Do a quick check on validity of info
        # #### Eventually add 'cp' and 'pc'
        if not (depy_type in ('cmd', 'env') and
                all([letter in ('o', 'm', 'v', 'n', '|') for letter in depy_args]) and
                ('|' not in depy_args or (depy_args.count('|') == 1 and depy_args.endswith('|'))) and
                depy_typeset in ('c', 'p', 'n')):  
            print('* PythonTeX error:')
            print('    Invalid \\Depythontex string for operation on line ' + str(depy_linenum))
            print('    The offending string was ' + depytxcontent)
            sys.exit(1)
        # If depy_args contains a `|` to indicate `\obeylines`, strip it and 
        # store in a variable.  Create a bool to keep track of obeylines 
        # status, which governs whether we can look on the next line for 
        # arguments.  (If obeylines is active, a newline terminates the 
        # argument search.)
        if depy_args.endswith('|'):
            obeylines = True
            depy_args = depy_args.rstrip('|')
        else:
            obeylines = False
        # Get the line number as an integer
        # We don't have to adjust for zero indexing in tex
        depy_linenum = int(depy_linenum)
        
        
        # Check for information passed from LaTeX
        # This will be extra listings information, or replacements to plug in
        code_replacement = None
        code_replacement_mode = None
        print_replacement = None
        print_replacement_mode = None
        firstnumber = None
        source = None
        scan_ahead_line = n + 1
        nextdepytxline = depytx[scan_ahead_line]
        while not nextdepytxline.startswith('=>DEPYTHONTEX#'):
            if nextdepytxline.startswith('LISTING:'):
                listingcontent = nextdepytxline.split(':', 1)[1].rstrip('\n')
                if bool(match(r'firstnumber=\d+$', listingcontent)):
                    firstnumber = listingcontent.split('=', 1)[1]
                else:
                    print('* DePythonTeX error:')
                    print('    Unknown information in listings data on line ' + str(depy_linenum))
                    print('    The listings content was "' + listingcontent + '"')
                    sys.exit(1)
            elif nextdepytxline.startswith('MACRO:'):
                source = 'macro'
                try:
                    typeset, macro = nextdepytxline.rstrip('\n').split(':', 2)[1:]
                except:
                    print('* DePythonTeX error:')
                    print('    Improperly formatted macro information on line ' + str(depy_linenum))
                    print('    The macro information was "' + nextdepytxline + '"')
                    sys.exit(1)
                if macro not in macrodict:
                    print('* DePythonTeX error:')
                    print('    Could not find replacement content for macro "' + macro + '"')
                    print('    This is probably because the document needs to be recompiled')
                    sys.exit(1)
                if typeset == 'c':
                    if depy_type == 'cmd':
                        code_replacement = ''.join(macrodict[macro]).strip('\n')
                    else:
                        code_replacement = ''.join(macrodict[macro])
                elif typeset == 'p':
                    print_replacement = ''.join(macrodict[macro])
                else:
                    print('* DePythonTeX error:')
                    print('    Improper typesetting information for macro information on line ' + str(depy_linenum))
                    print('    The macro information was "' + nextdepytxline + '"')
                    sys.exit(1)
            elif nextdepytxline.startswith('FILE:'):
                source = 'file'
                try:
                    typeset, f_name = nextdepytxline.rstrip('\n').split(':', 2)[1:]    
                except:
                    print('* DePythonTeX error:')
                    print('    Improperly formatted file information on line ' + str(depy_linenum))
                    print('    The file information was "' + nextdepytxline + '"')
                    sys.exit(1)
                # Files that are brought in have an optional mode that 
                # determines if they need special handling (for example, verbatim)
                if ':mode=' in f_name:
                    f_name, mode = f_name.split(':mode=')
                else:
                    mode = None
                f = open(f_name, 'r', encoding=encoding)
                replacement = f.read()
                f.close()
                if typeset == 'c':
                    code_replacement_mode = mode
                    if depy_type == 'cmd' and code_replacement_mode != 'verbatim':
                        # Usually, code from commands is typeset with commands
                        # and code from environments is typeset in 
                        # environments.  The except is code from commands 
                        # that bring in external files, like `\inputpygments`
                        code_replacement = replacement
                    else:
                        # If we're replacing an environment of code with a
                        # file, then we lose the newline at the beginning
                        # of the environment, and need to get it back.
                        code_replacement = '\n' + replacement                    
                elif typeset == 'p':
                    print_replacement_mode = mode
                    print_replacement = replacement                    
                else:
                    print('* DePythonTeX error:')
                    print('    Improper typesetting information for file information on line ' + str(depy_linenum))
                    print('    The file information was "' + nextdepytxline + '"')
                    sys.exit(1)
            # Increment the line in depytx to check for more information 
            # from LaTeX
            scan_ahead_line += 1
            if scan_ahead_line == len(depytx):
                break
            else:
                nextdepytxline = depytx[scan_ahead_line]
        
        
        # If the line we're looking for is within the range currently held by
        # texcontent, do nothing.  Otherwise, transfer content from tex
        # to texout until we get to the line of tex that we're looking for
        if depy_linenum > texlinenum:
            texout.append(texcontent)
            texlinenum += 1
            while texlinenum < depy_linenum:
                texout.append(tex[texlinenum])
                texlinenum += 1
            texcontent = tex[texlinenum]

        
        # Deal with arguments
        # All arguments are parsed and stored in a list variables, even if 
        # they are not used, for completeness; this makes it easy to add 
        # functionality
        # Start by splitting the current line into what comes before the 
        # command or environment, and what is after it
        if depy_type == 'cmd':
            try:
                before, after = texcontent.split('\\' + depy_name, 1)
            except:
                print('* DePythonTeX error:')
                print('    Could not find command "' + depy_name + '" on line ' + str(depy_linenum))
                sys.exit(1)
        else:  # depy_type == 'env':
            try:
                before, after = texcontent.split(r'\begin{' + depy_name + '}', 1)
            except:
                print('* DePythonTeX error:')
                print('    Could not find environment "' + depy_name + '" on line ' + str(depy_linenum))
                sys.exit(1)
        # We won't need the content from before the command or environment 
        # again, so we go ahead and store it
        texout.append(before)
        
        # Parse the arguments
        # Create a list for storing the recovered arguments
        arglist = list()
        for argindex, arg in enumerate(depy_args):
            if arg == 'n':
                pass
            elif arg == 'o':
                if after[0] == '[':
                    # Account for possible line breaks before end of arg
                    while ']' not in after:
                        texlinenum += 1
                        after += tex[texlinenum]                  
                    optarg, after = after[1:].split(']', 1)
                else:
                    if obeylines:
                        # Take into account possible whitespace before arg
                        if bool(match('[ \t]*\[', after)):
                            after = after.split('[', 1)[1]
                            while ']' not in after:
                                texlinenum += 1
                                after += tex[texlinenum]               
                            optarg, after = after.split(']', 1)
                        else:
                            optarg = None
                            # If this is the last arg, and it wasn't found,
                            # the macro should eat all whitespace following it
                            if argindex == len(depy_args) - 1:
                                after = sub('^[ \t]*', '', after)
                    else:
                        # Allow peeking ahead a line for the argument
                        if bool(match('\s*$', after)) and after.count('\n') < 2:
                            texlinenum += 1
                            after += tex[texlinenum]
                        # Take into account possible whitespace before arg
                        if bool(match('\s*\[', after)):
                            after = after.split('[', 1)[1]
                            while ']' not in after:
                                texlinenum += 1
                                after += tex[texlinenum]               
                            optarg, after = after.split(']', 1)
                        else:
                            optarg = None
                            # Account for eating whitespace afterward, if arg not found
                            if argindex == len(depy_args) - 1:
                                if bool(match('\s*$', after)) and after.count('\n') < 2:
                                    texlinenum += 1
                                    after += tex[texlinenum]
                                if not bool(match('\s*$', after)):
                                    after = sub('^\s*', '', after)
                arglist.append(optarg)
            elif arg == 'm':
                # Account for possible line breaks or spaces before arg
                if after[0] == '{':
                    after = after[1:]
                else:
                    if obeylines:
                        # Account for possible leading whitespace
                        if bool(match('[ \t\f\v]*\{', after)):
                            after = after.split('{', 1)[1]
                        else:
                            print('* DePythonTeX error:')
                            print('    Flawed mandatory argument for "' + depy_name + '" on line ' + str(depy_linenum))
                            sys.exit(1)
                    else:
                        # Peek ahead a line if needed
                        if bool(match('\s*$', after)) and after.count('\n') < 2:
                            texlinenum += 1
                            after += tex[texlinenum]
                        if bool(match('\s*\{', after)):
                            after = after.split('{', 1)[1]
                        else:
                            print('* DePythonTeX error:')
                            print('    Flawed mandatory argument for "' + depy_name + '" on line ' + str(depy_linenum))
                            sys.exit(1)
                # Go through the argument character by character to find the
                # closing brace.
                # If possible, use a very simple approach
                if (r'\{' not in after and r'\}' not in after and 
                        r'\string' not in after and 
                        after.count('{') + 1 == after.count('}')):
                    pos = 0
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            lbraces += 1
                        elif after[pos] == '}':
                            rbraces += 1
                        if lbraces == rbraces:
                            break
                        pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                # If a simple parsing approach won't work, parse in much 
                # greater depth
                else:
                    pos = 0
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            # If the current character is a brace, we count it
                            lbraces += 1
                            if lbraces == rbraces:
                                break
                            pos += 1
                        elif after[pos] == '}':
                            # If the current character is a brace, we count it
                            rbraces += 1
                            if lbraces == rbraces:
                                break
                            pos += 1
                        elif after[pos:].startswith(r'\string'):
                            # If the current position marks the beginning of `\string`, we
                            # resolve the `\string` command
                            # First, jump ahead to after `\string`
                            pos += 7 #+= len(r'\string')
                            # See if `\string` is followed by a regular macro
                            # If so, jump past it; otherwise, figure out if a 
                            # single-character macro, or just a single character, is next,
                            # and jump past it
                            standard_macro = match(r'\\[a-zA-Z]+', line[pos:])
                            if bool(standard_macro):
                                pos += standard_macro.end()
                            elif line[pos] == '\\':
                                pos += 2
                            else:
                                pos += 1
                        elif line[pos] == '\\':
                            # If the current position is a backslash, figure out what 
                            # macro is used, and jump past it
                            # The macro must either be a standard alphabetic macro,
                            # or a single-character macro
                            standard_macro = match(r'\\[a-zA-Z]+', line[pos:])
                            if bool(standard_macro):
                                pos += standard_macro.end()
                            else:
                                pos += 2
                        else:
                            pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                mainarg = after[:pos]
                after = after[pos+1:]
                arglist.append(mainarg)
            elif arg == 'v':
                if after[0] == '{':
                    # Account for the possibility of matched brace delimiters
                    # Not all verbatim commands allow for these
                    pos = 1
                    lbraces = 1
                    rbraces = 0
                    while True:
                        if after[pos] == '{':
                            lbraces += 1
                        elif after[pos] == '}':
                            rbraces += 1
                        if lbraces == rbraces:
                            break
                        pos += 1
                        if pos == len(after):
                            texlinenum += 1
                            after += tex[texlinenum]
                    mainarg = after[1:pos]
                    after = after[pos+1:]
                else:
                    # Deal with matched character delims
                    delim = after[0]
                    while after.count(delim) < 2:
                        texlinenum += 1
                        after += tex[texlinenum]
                    mainarg, after = after[1:].split(delim, 1)
                arglist.append(mainarg)
            
        
        # Do substitution, depending on what is required
        # Need a variable for processed content to be added to texout
        processed = None
        if depy_typeset == 'c':
            if depy_type == 'cmd':
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_code_cmd(depy_name, arglist, 
                                                         depy_linenum, 
                                                         code_replacement,
                                                         code_replacement_mode,
                                                         after, depy_lexer,
                                                         firstnumber)
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if code_replacement is None:
                    if end_environment not in after:
                        while True:
                            texlinenum += 1
                            after += tex[texlinenum]
                            if end_environment in tex[texlinenum]:
                                break
                    code_replacement, after = after.split(end_environment, 1)
                    # If there's content on the line with the end-environment
                    # command, it should be discarded, to imitate TeX
                    if not code_replacement.endswith('\n'):
                        code_replacement = code_replacement.rsplit('\n', 1)[0] + '\n'
                    # Take care of `gobble`
                    if settings['gobble'] == 'auto':
                        code_replacement = textwrap.dedent(code_replacement)
                else:
                    if end_environment not in after:
                        while True:
                            texlinenum += 1
                            if end_environment in tex[texlinenum]:
                                after = tex[texlinenum]
                                break
                    after = after.split(end_environment, 1)[1]
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_code_env(depy_name, arglist,
                                                         depy_linenum,
                                                         code_replacement,
                                                         code_replacement_mode,
                                                         after, depy_lexer, 
                                                         firstnumber)
        elif depy_typeset == 'p' and print_replacement is not None:
            if depy_type == 'cmd':
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_print_cmd(depy_name, arglist, 
                                                          depy_linenum,
                                                          print_replacement,
                                                          print_replacement_mode,
                                                          source,
                                                          after)
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if end_environment not in after:
                    while True:
                        texlinenum += 1
                        if end_environment in tex[texlinenum]:
                            after = tex[texlinenum]
                            break
                after = after.split(end_environment, 1)[1]
                # Make sure that `after` contains two lines of content
                # This is needed for some replacements that need to look ahead
                if after.count('\n') < 2:
                    texlinenum += 1
                    after += tex[texlinenum]
                processed, texcontent = replace_print_env(depy_name, arglist, 
                                                          depy_linenum,
                                                          print_replacement, 
                                                          print_replacement_mode,
                                                          source,
                                                          after)
        else:  # depy_typeset == 'n' or (depy_typeset == 'p' and print_replacement is None):
            if depy_type == 'cmd':
                texcontent = after
            else:  # depy_type == 'env'
                end_environment = r'\end{' + depy_name + '}'
                if end_environment not in after:
                    while True:
                        texlinenum += 1
                        if end_environment in tex[texlinenum]:
                            after = tex[texlinenum]
                            break
                after = after.split(end_environment, 1)[1]
                if bool(match('\s*\n', after)):
                    # If the line following `after` is whitespace, it should
                    # be stripped, since most environments throw away
                    # anything after the end of the environment
                    after = after.split('\n')[1]
                texcontent = after
        # #### Once it's supported on the TeX side, need to add support for
        # pc and cp
        
        
        # Store any processed content
        if processed is not None:
            texout.append(processed)


# Transfer anything that's left in tex to texout
texout.append(texcontent)
texout.extend(tex[texlinenum+1:])




# Replace the `\usepackage{pythontex}`
for n, line in enumerate(texout):
    if '{pythontex}' in line:
        startline = n
        while '\\usepackage' not in texout[startline] and startline >= 0:
            startline -= 1
        if startline == n:
            if bool(search(r'\\usepackage(?:\[.*?\]){0,1}\{pythontex\}', line)):
                texout[n] = sub(r'\\usepackage(?:\[.*?\]){0,1}\{pythontex\}', '', line)
                if texout[n].isspace():
                    texout[n] = ''
                break
        else:
            content = ''.join(texout[startline:n+1])
            if bool(search(r'(?s)\\usepackage(?:\[.*?\]\s*){0,1}\{pythontex\}', content)):
                replacement = sub(r'(?s)\\usepackage(?:\[.*?\]\s*){0,1}\{pythontex\}', '', content)
                if replacement.isspace():
                    replacement = ''
                texout[startline] = replacement
                for l in range(startline+1, n+1):
                    texout[l] = ''
                break
    elif line.startswith(r'\begin{document}'):
        break
if preamble_additions:
    texout[n] += '\n'.join(preamble_additions) + '\n'
# Take care of graphicspath
if args.graphicspath and settings['graphicx']:
    for n, line in enumerate(texout):
        if '\\graphicspath' in line and not bool(match('\s*%', line)):
            texout[n] = line.replace('\\graphicspath{', '\\graphicspath{{' + settings['outputdir'] +'/}')
            break
        elif line.startswith(r'\begin{document}'):
            texout[n] = '\\graphicspath{{' + settings['outputdir'] + '/}}\n' + line
            break




# Print any final messages
if forced_double_space_list:
    print('* DePythonTeX warning:')
    print('    A trailing double space was forced with "\\space{}" for the following')
    print('    This can happen when printed content is included inline')
    print('    The forced double space is only an issue if it is not intentional')
    for name, linenum in forced_double_space_list:
        print('      "' + name + '" near line ' + str(linenum))




# Write output
if args.output is not None:
    for line in texout:
        outfile.write(line)
    outfile.close()
else:
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter(encoding)(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter(encoding)(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter(encoding)(sys.stderr.buffer, 'strict')
    for line in texout:
        sys.stdout.write(line)

########NEW FILE########
__FILENAME__ = pythontex
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This is the PythonTeX wrapper script.  It automatically detects the version
of Python, and then imports the correct code from pythontex2.py or 
pythontex3.py.  It is intended for use with the default Python installation 
on your system.  If you wish to use a different version of Python, you could 
launch pythontex2.py or pythontex3.py directly.  You should also consider the 
command-line option `--interpreter`.  This allows you to specify the command
that is actually used to execute the code from your LaTeX documents.  Except 
for Python console content, it doesn't matter which version of Python is used 
to launch pythontex.py; pythontex.py just manages the execution of code from
your LaTeX document.  The interpreter setting is what determines the version 
under which your code is actually executed.

Licensed under the BSD 3-Clause License:

Copyright (c) 2012-2014, Geoffrey M. Poore

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


import sys
if sys.version_info.major == 2:
    if sys.version_info.minor >= 7:
        import pythontex2 as pythontex
    else:
        sys.exit('PythonTeX require Python 2.7; you are using 2.{0}'.format(sys.version_info.minor))
elif sys.version_info.major == 3:
    if sys.version_info.minor >= 2:
        import pythontex3 as pythontex
    else:
        sys.exit('PythonTeX require Python 3.2+; you are using 3.{0}'.format(sys.version_info.minor))
 
# The "if" statement is needed for multiprocessing under Windows; see the 
# multiprocessing documentation.
if __name__ == '__main__':
    pythontex.main()

########NEW FILE########
__FILENAME__ = pythontex2
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

'''
This is the main PythonTeX script.  It should be launched via pythontex.py.

Two versions of this script are provided.  One, with name ending in "2", runs 
under Python 2.7.  The other, with name ending in "3", runs under Python 3.2+.

This script needs to be able to import pythontex_engines.py; in general it 
should be in the same directory.


Licensed under the BSD 3-Clause License:

Copyright (c) 2012-2014, Geoffrey M. Poore

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


# Imports
#// Python 2
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
#\\ End Python 2
import sys
import os
import argparse
import codecs
import time
from hashlib import sha1
from collections import defaultdict, OrderedDict, namedtuple
from re import match, sub, search
import subprocess
import multiprocessing
from pygments.styles import get_all_styles
from pythontex_engines import *
import textwrap
import platform

if sys.version_info[0] == 2:
    try:
        import cPickle as pickle
    except:
        import pickle
    from io import open
else:
    import pickle




# Script parameters
# Version
version = 'v0.13-beta'




class Pytxcode(object):
    def __init__(self, data, gobble):
        self.delims, self.code = data.split('#\n', 1)
        self.family, self.session, self.restart, self.instance, self.command, self.context, self.args_run, self.args_prettyprint, self.input_file, self.line = self.delims.split('#')
        self.instance_int = int(self.instance)        
        self.line_int = int(self.line)
        self.key_run = self.family + '#' + self.session + '#' + self.restart
        self.key_typeset = self.key_run + '#' + self.instance
        self.hashable_delims_run = self.key_typeset + '#' + self.command + '#' + self.context + '#' + self.args_run
        self.hashable_delims_typeset = self.key_typeset + '#' + self.command + '#' + self.context + '#' + self.args_run
        if len(self.command) > 1:
            self.is_inline = False
            # Environments start on the next line
            self.line_int += 1
            self.line = str(self.line_int)
        else:
            self.is_inline = True
        self.is_extfile = True if self.session.startswith('EXT:') else False
        if self.is_extfile:
            self.extfile = os.path.expanduser(os.path.normcase(self.session.replace('EXT:', '', 1)))
            self.key_typeset = self.key_typeset.replace('EXT:', '')
        self.is_cc = True if self.family.startswith('CC:') else False
        self.is_pyg = True if self.family.startswith('PYG') else False
        self.is_verb = True if self.restart.endswith('verb') else False
        if self.is_cc:
            self.instance += 'CC'
            self.cc_type, self.cc_pos = self.family.split(':')[1:]
        if self.is_verb or self.is_pyg or self.is_cc:
            self.is_cons = False
        else:
            self.is_cons = engine_dict[self.family].console
        self.is_code = False if self.is_verb or self.is_pyg or self.is_cc or self.is_cons else True
        if self.command in ('c', 'code') or (self.command == 'i' and not self.is_cons):
            self.is_typeset = False
        else:
            self.is_typeset = True
        
        if gobble == 'auto':
            self.code = textwrap.dedent(self.code)
            



def process_argv(data, temp_data):
    '''
    Process command line options using the argparse module.
    
    Most options are passed via the file of code, rather than via the command
    line.
    '''
    
    # Create a command line argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('TEXNAME',
                        help='LaTeX file, with or without .tex extension')
    parser.add_argument('--version', action='version', 
                        version='PythonTeX {0}'.format(data['version']))                    
    parser.add_argument('--encoding', default='UTF-8', 
                        help='encoding for all text files (see codecs module for encodings)')
    parser.add_argument('--error-exit-code', default='true', 
                        choices=('true', 'false'),                          
                        help='return exit code of 1 if there are errors (not desirable with some TeX editors and workflows)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--runall', nargs='?', default='false',
                       const='true', choices=('true', 'false'),
                       help='run ALL code; equivalent to package option')
    group.add_argument('--rerun', default='errors', 
                       choices=('never', 'modified', 'errors', 'warnings', 'always'),
                       help='set conditions for rerunning code; equivalent to package option')
    parser.add_argument('--hashdependencies', nargs='?', default='false', 
                        const='true', choices=('true', 'false'),                          
                        help='hash dependencies (such as external data) to check for modification, rather than using mtime; equivalent to package option')
    parser.add_argument('-j', '--jobs', metavar='N', default=None, type=int,
                        help='Allow N jobs at once; defaults to cpu_count().')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='verbose output')
    parser.add_argument('--interpreter', default=None, help='set a custom interpreter; argument should be in the form "<interpreter>:<command>, <interp>:<cmd>, ..." where <interpreter> is "python", "ruby", etc., and <command> is the command for invoking the interpreter; argument may also be in the form of a Python dictionary')
    args = parser.parse_args()
    
    # Store the parsed argv in data and temp_data          
    data['encoding'] = args.encoding
    if args.error_exit_code == 'true':
        temp_data['error_exit_code'] = True
    else:
        temp_data['error_exit_code'] = False
    # runall can be mapped onto rerun, so both are stored under rerun
    if args.runall == 'true':
        temp_data['rerun'] = 'always'
    else:
        temp_data['rerun'] = args.rerun
    # hashdependencies need only be in temp_data, since changing it would
    # change hashes (hashes of mtime vs. file contents)
    if args.hashdependencies == 'true':
        temp_data['hashdependencies'] = True
    else:
        temp_data['hashdependencies'] = False
    if args.jobs is None:
        try:
            jobs = multiprocessing.cpu_count()
        except NotImplementedError:
            jobs = 1
        temp_data['jobs'] = jobs
    else:
        temp_data['jobs'] = args.jobs
    temp_data['verbose'] = args.verbose
    # Update interpreter_dict based on interpreter
    set_python_interpreter = False
    if args.interpreter is not None:
        interp_list = args.interpreter.lstrip('{').rstrip('}').split(',')
        for interp in interp_list:
            if interp:
                try:
                    k, v = interp.split(':')
                    k = k.strip(' \'"')
                    v = v.strip(' \'"')
                    interpreter_dict[k] = v
                    if k == 'python':
                        set_python_interpreter = True
                except:
                    print('Invalid --interpreter argument')
                    return sys.exit(2)
    # If the Python interpreter wasn't set, then try to set an appropriate
    # default value, based on how PythonTeX was launched (pythontex.py, 
    # pythontex2.py, or pythontex3.py).
    if not set_python_interpreter:
        if temp_data['python'] == 2:
            if platform.system() == 'Windows':
                try:
                    subprocess.check_output(['py', '--version'])
                    interpreter_dict['python'] = 'py -2'
                except:
                    msg = '''
                          * PythonTeX error:
                              You have launched PythonTeX using pythontex{0}.py
                              directly.  This should only be done when you want
                              to use Python version {0}, but have a different
                              version installed as the default.  (Otherwise, you
                              should start PythonTeX with pythontex.py.)  For 
                              this to work correctly, you should install Python
                              version 3.3+, which has a Windows wrapper (py) that
                              PythonTeX can use to run the correct version of 
                              Python.  If you do not want to install Python 3.3+,
                              you can also use the --interpreter command-line 
                              option to tell PythonTeX how to access the version
                              of Python you wish to use.
                          '''.format(temp_data['python'])
                    print(textwrap.dedent(msg[1:]))
                    return sys.exit(2)
            else:
                interpreter_dict['python'] = 'python2'
        elif temp_data['python'] == 3:
            if platform.system() == 'Windows':
                try:
                    subprocess.check_output(['py', '--version'])
                    interpreter_dict['python'] = 'py -3'
                except:
                    msg = '''
                          * PythonTeX error:
                              You have launched PythonTeX using pythontex{0}.py
                              directly.  This should only be done when you want
                              to use Python version {0}, but have a different
                              version installed as the default.  (Otherwise, you
                              should start PythonTeX with pythontex.py.)  For 
                              this to work correctly, you should install Python
                              version 3.3+, which has a Windows wrapper (py) that
                              PythonTeX can use to run the correct version of 
                              Python.  If you do not want to install Python 3.3+,
                              you can also use the --interpreter command-line 
                              option to tell PythonTeX how to access the version
                              of Python you wish to use.
                          '''.format(temp_data['python'])
                    print(textwrap.dedent(msg[1:]))
                    return sys.exit(2)
            else:
                interpreter_dict['python'] = 'python3'
    
    if args.TEXNAME is not None:
        # Determine if we a dealing with just a filename, or a name plus 
        # path.  If there's a path, we need to make the document directory 
        # the current working directory.
        dir, raw_jobname = os.path.split(args.TEXNAME)
        dir = os.path.expanduser(os.path.normcase(dir))
        if dir:
            os.chdir(dir)
            sys.path.append(dir)
        # If necessary, strip off an extension to find the raw jobname that
        # corresponds to the .pytxcode.
        if not os.path.exists(raw_jobname + '.pytxcode'):
            raw_jobname = raw_jobname.rsplit('.', 1)[0]
            if not os.path.exists(raw_jobname + '.pytxcode'):
                print('* PythonTeX error')
                print('    Code file ' + raw_jobname + '.pytxcode does not exist.')
                print('    Run LaTeX to create it.')
                return sys.exit(1)
        
        # We need a "sanitized" version of the jobname, with spaces and 
        # asterisks replaced with hyphens.  This is done to avoid TeX issues 
        # with spaces in file names, paralleling the approach taken in 
        # pythontex.sty.  From now on, we will use the sanitized version every 
        # time we create a file that contains the jobname string.  The raw 
        # version will only be used in reference to pre-existing files created 
        # on the TeX side, such as the .pytxcode file.
        jobname = raw_jobname.replace(' ', '-').replace('"', '').replace('*', '-')
        # Store the results in data
        data['raw_jobname'] = raw_jobname
        data['jobname'] = jobname
        
        # We need to check to make sure that the "sanitized" jobname doesn't 
        # lead to a collision with a file that already has that name, so that 
        # two files attempt to use the same PythonTeX folder.
        # 
        # If <jobname>.<ext> and <raw_jobname>.<ext> both exist, where <ext>
        # is a common LaTeX extension, we exit.  We operate under the 
        # assumption that there should be only a single file <jobname> in the 
        # document root directory that has a common LaTeX extension.  That 
        # could be false, but if so, the user probably has worse things to 
        # worry about than a potential PythonTeX output collision.
        # If <jobname>* and <raw_jobname>* both exist, we issue a warning but 
        # attempt to proceed.
        if jobname != raw_jobname:
            resolved = False
            for ext in ('.tex', '.ltx', '.dtx'):
                if os.path.isfile(raw_jobname + ext):
                    if os.path.isfile(jobname + ext):
                        print('* PythonTeX error')
                        print('    Directory naming collision between the following files:')
                        print('      ' + raw_jobname + ext)
                        print('      ' + jobname + ext)
                        return sys.exit(1)
                    else:
                        resolved = True
                        break
            if not resolved:
                ls = os.listdir('.')
                for file in ls:
                    if file.startswith(jobname):
                        print('* PythonTeX warning')
                        print('    Potential directory naming collision between the following names:')
                        print('      ' + raw_jobname)
                        print('      ' + jobname + '*')
                        print('    Attempting to proceed.')
                        temp_data['warnings'] += 1
                        break            
        
        


def load_code_get_settings(data, temp_data):
    '''
    Load the code file, preprocess the code, and extract the settings.
    '''
    # Bring in the .pytxcode file as a single string
    raw_jobname = data['raw_jobname']
    encoding = data['encoding']
    # The error checking here is a little redundant
    if os.path.isfile(raw_jobname + '.pytxcode'):
        f = open(raw_jobname + '.pytxcode', 'r', encoding=encoding)
        pytxcode = f.read()
        f.close()
    else:
        print('* PythonTeX error')
        print('    Code file ' + raw_jobname + '.pytxcode does not exist.')
        print('    Run LaTeX to create it.')
        return sys.exit(1)
    
    # Split code and settings
    try:
        pytxcode, pytxsettings = pytxcode.rsplit('=>PYTHONTEX:SETTINGS#', 1)
    except:
        print('The .pytxcode file appears to have an outdated format or be invalid')
        print('Run LaTeX to make sure the file is current')
        return sys.exit(1)
    
    
    # Prepare to process settings
    #
    # Create a dict for storing settings.
    settings = {}
    # Create a dict for storing Pygments settings.
    # Each dict entry will itself be a dict.
    pygments_settings = defaultdict(dict)
    
    # Create a dict of processing functions, and generic processing functions
    settings_func = dict()
    def set_kv_data(k, v):
        if v == 'true':
            settings[k] = True
        elif v == 'false':
            settings[k] = False
        else:
            settings[k] = v
    # Need a function for when assignment is only needed if not default value
    def set_kv_temp_data_if_not_default(k, v):
        if v != 'default':
            if v == 'true':
                temp_data[k] = True
            elif v == 'false':
                temp_data[k] = False
            else:
                temp_data[k] = v
    def set_kv_data_fvextfile(k, v):
        # Error checking on TeX side should be enough, but be careful anyway
        try:
            v = int(v)                    
        except ValueError:
            print('* PythonTeX error')
            print('    Unable to parse package option fvextfile.')
            return sys.exit(1)
        if v < 0:
            settings[k] = sys.maxsize
        elif v == 0:
            settings[k] = 1
            print('* PythonTeX warning')
            print('    Invalid value for package option fvextfile.')
            temp_data['warnings'] += 1
        else:
            settings[k] = v
    def set_kv_pygments(k, v):
        family, lexer_opts, options = v.replace(' ','').split('|')
        lexer = None
        lex_dict = {}
        opt_dict = {}
        if lexer_opts:
            for l in lexer_opts.split(','):
                if '=' in l:
                    k, v = l.split('=', 1)
                    if k == 'lexer':
                        lexer = l
                    else:
                        lex_dict[k] = v
                else:
                    lexer = l
        if options:
            for o in options.split(','):
                if '=' in o:
                    k, v = o.split('=', 1)
                    if v in ('true', 'True'):
                        v = True
                    elif v in ('false', 'False'):
                        v = False
                else:
                    k = option
                    v = True
                opt_dict[k] = v
        if family != ':GLOBAL':
            if 'lexer' in pygments_settings[':GLOBAL']:
                lexer = pygments_settings[':GLOBAL']['lexer']
            lex_dict.update(pygments_settings[':GLOBAL']['lexer_options'])
            opt_dict.update(pygments_settings[':GLOBAL']['formatter_options'])
            if 'style' not in opt_dict:
                opt_dict['style'] = 'default'
            opt_dict['commandprefix'] = 'PYG' + opt_dict['style']
        if lexer is not None:
            pygments_settings[family]['lexer'] = lexer
        pygments_settings[family]['lexer_options'] = lex_dict
        pygments_settings[family]['formatter_options'] = opt_dict
    settings_func['version'] = set_kv_data
    settings_func['outputdir'] = set_kv_data
    settings_func['workingdir'] = set_kv_data
    settings_func['gobble'] = set_kv_data
    settings_func['rerun'] = set_kv_temp_data_if_not_default
    settings_func['hashdependencies'] = set_kv_temp_data_if_not_default
    settings_func['makestderr'] = set_kv_data
    settings_func['stderrfilename'] = set_kv_data
    settings_func['keeptemps'] = set_kv_data
    settings_func['pyfuture'] = set_kv_data
    settings_func['pyconfuture'] = set_kv_data
    settings_func['pygments'] = set_kv_data
    settings_func['fvextfile'] = set_kv_data_fvextfile
    settings_func['pygglobal'] = set_kv_pygments
    settings_func['pygfamily'] = set_kv_pygments
    settings_func['pyconbanner'] = set_kv_data
    settings_func['pyconfilename'] = set_kv_data
    settings_func['depythontex'] = set_kv_data
    
    # Process settings
    for line in pytxsettings.split('\n'):
        if line:
            key, val = line.split('=', 1)
            try:
                settings_func[key](key, val)
            except KeyError:
                print('* PythonTeX warning')
                print('    Unknown option "' + key + '"')
                temp_data['warnings'] += 1

    # Check for compatility between the .pytxcode and the script
    if 'version' not in settings or settings['version'] != data['version']:
        print('* PythonTeX warning')
        print('    The version of the PythonTeX scripts does not match')
        print('    the last code saved by the document--run LaTeX to create')
        print('    an updated version.  Attempting to proceed.')
        sys.stdout.flush()
    
    # Store all results that haven't already been stored.
    data['settings'] = settings
    data['pygments_settings'] = pygments_settings
    
    # Create a tuple of vital quantities that invalidate old saved data
    # Don't need to include outputdir, because if that changes, no old output
    # fvextfile could be checked on a case-by-case basis, which would result
    # in faster output, but that would involve a good bit of additional 
    # logic, which probably isn't worth it for a feature that will rarely be
    # changed.
    data['vitals'] = (data['version'], data['encoding'], 
                      settings['gobble'], settings['fvextfile'])
    
    # Create tuples of vital quantities
    data['code_vitals'] = (settings['workingdir'], settings['keeptemps'],
                           settings['makestderr'], settings['stderrfilename'])
    data['cons_vitals'] = (settings['workingdir'])
    data['typeset_vitals'] = ()
    
    # Pass any customizations to types
    for k in engine_dict:
        engine_dict[k].customize(pyfuture=settings['pyfuture'],
                                 pyconfuture=settings['pyconfuture'],
                                 pyconbanner=settings['pyconbanner'],
                                 pyconfilename=settings['pyconfilename'])
    
    # Store code
    # Do this last, so that Pygments settings are available
    if pytxcode.startswith('=>PYTHONTEX#'):
        gobble = settings['gobble']
        temp_data['pytxcode'] = [Pytxcode(c, gobble) for c in pytxcode.split('=>PYTHONTEX#')[1:]]
    else:
        temp_data['pytxcode'] = []




def get_old_data(data, old_data, temp_data):
    '''
    Load data from the last run, if it exists, into the dict old_data.  
    Determine the path to the PythonTeX scripts, either by using a previously 
    found, saved path or via kpsewhich.
    
    The old data is used for determining when PythonTeX has been upgraded, 
    when any settings have changed, when code has changed (via hashes), and 
    what files may need to be cleaned up.  The location of the PythonTeX 
    scripts is needed so that they can be imported by the scripts created by 
    PythonTeX.  The location of the scripts is confirmed even if they were 
    previously located, to make sure that the path is still valid.  Finding 
    the scripts depends on having a TeX installation that includes the 
    Kpathsea library (TeX Live and MiKTeX, possibly others).
    
    All code that relies on old_data is written based on the assumption that
    if old_data exists and has the current PythonTeX version, then it 
    contains all needed information.  Thus, all code relying on old_data must
    check that it was loaded and that it has the current version.  If not, 
    code should adapt gracefully.
    '''

    # Create a string containing the name of the data file
    pythontex_data_file = os.path.join(data['settings']['outputdir'], 'pythontex_data.pkl')
    
    # Load the old data if it exists (read as binary pickle)
    if os.path.isfile(pythontex_data_file):
        f = open(pythontex_data_file, 'rb')
        old = pickle.load(f)
        f.close()
        # Check for compabilility
        if 'vitals' in old and data['vitals'] == old['vitals']:
            temp_data['loaded_old_data'] = True
            old_data.update(old)
        else:
            temp_data['loaded_old_data'] = False
            # Clean up all old files
            if 'files' in old:
                for key in old['files']:
                    for f in old['files'][key]:
                        f = os.path.expanduser(os.path.normcase(f))
                        if os.path.isfile(f):
                            os.remove(f)
            if 'pygments_files' in old:
                for key in old['pygments_files']:
                    for f in old['pygments_files'][key]:
                        f = os.path.expanduser(os.path.normcase(f))
                        if os.path.isfile(f):
                            os.remove(f)
    else:
        temp_data['loaded_old_data'] = False
    
    # Set the utilspath
    # Assume that if the utils aren't in the same location as 
    # `pythontex.py`, then they are somewhere else on `sys.path` that
    # will always be available (for example, installed as a Python module),
    # and thus specifying a path isn't necessary.
    if os.path.isfile(os.path.join(sys.path[0], 'pythontex_utils.py')):
        # Need the path with forward slashes, so escaping isn't necessary
        data['utilspath'] = sys.path[0].replace('\\', '/')
    else:
        data['utilspath'] = ''




def modified_dependencies(key, data, old_data, temp_data):
    hashdependencies = temp_data['hashdependencies']
    if key not in old_data['dependencies']:
        return False
    else:
        old_dep_hash_dict = old_data['dependencies'][key]
        workingdir = data['settings']['workingdir']
        for dep in old_dep_hash_dict.keys():
            # We need to know if the path is relative (based off the 
            # working directory) or absolute.  We can't use 
            # os.path.isabs() alone for determining the distinction, 
            # because we must take into account the possibility of an
            # initial ~ (tilde) standing for the home directory.
            dep_file = os.path.expanduser(os.path.normcase(dep))
            if not os.path.isabs(dep_file):
                dep_file = os.path.join(workingdir, dep_file)
            if not os.path.isfile(dep_file):
                print('* PythonTeX error')
                print('    Cannot find dependency "' + dep + '"')
                print('    It belongs to ' + key.replace('#', ':'))
                print('    Relative paths to dependencies must be specified from the working directory.')
                temp_data['errors'] += 1
                # A removed dependency should trigger an error, but it 
                # shouldn't cause code to execute.  Running the code 
                # again would just give more errors when it can't find 
                # the dependency.  (There won't be issues when a 
                # dependency is added or removed, because that would 
                # involve modifying code, which would trigger 
                # re-execution.)
            elif hashdependencies:
                # Read and hash the file in binary.  Opening in text mode 
                # would require an unnecessary decoding and encoding cycle.
                f = open(dep_file, 'rb')
                hasher = sha1()
                hash = hasher(f.read()).hexdigest()
                f.close()
                if hash != old_dep_hash_dict[dep][1]:
                    return True
            else:
                mtime = os.path.getmtime(dep_file)
                if mtime != old_dep_hash_dict[dep][0]:
                    return True
        return False

def should_rerun(hash, old_hash, old_exit_status, key, rerun, data, old_data, temp_data):
    # #### Need to clean up arg passing here
    if rerun == 'never':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data)):
            print('* PythonTeX warning')
            print('    Session ' + key.replace('#', ':') + ' has rerun=never')
            print('    But its code or dependencies have been modified')
            temp_data['warnings'] += 1
        return False
    elif rerun == 'modified':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data)):
            return True
        else:
            return False
    elif rerun == 'errors':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data) or
                old_exit_status[0] != 0):
            return True
        else:
            return False
    elif rerun == 'warnings':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data) or
                old_exit_status != (0, 0)):
            return True
        else:
            return False
    elif rerun == 'always':
        return True




def hash_all(data, temp_data, old_data, engine_dict):
    '''
    Hash the code to see what has changed and needs to be updated.
    
    Save the hashes in hashdict.  Create update_code, a list of bools 
    regarding whether code should be executed.  Create update_pygments, a 
    list of bools determining what needs updated Pygments highlighting.  
    Update pygments_settings to account for Pygments (as opposed to PythonTeX) 
    commands and environments.
    '''

    # Note that the PythonTeX information that accompanies code must be 
    # hashed in addition to the code itself; the code could stay the same, 
    # but its context or args could change, which might require that code be 
    # executed.  All of the PythonTeX information is hashed except for the 
    # input line number.  Context-dependent code is going too far if 
    # it depends on that.
    
    # Create variables to more easily access parts of data
    pytxcode = temp_data['pytxcode']
    encoding = data['encoding']
    loaded_old_data = temp_data['loaded_old_data']
    rerun = temp_data['rerun']
    pygments_settings = data['pygments_settings']
    
    # Calculate cumulative hashes for all code that is executed
    # Calculate individual hashes for all code that will be typeset
    code_hasher = defaultdict(sha1)
    cons_hasher = defaultdict(sha1)
    cc_hasher = defaultdict(sha1)
    typeset_hasher = defaultdict(sha1)
    for c in pytxcode:
        if c.is_code:
            code_hasher[c.key_run].update(c.hashable_delims_run.encode(encoding))
            code_encoded = c.code.encode(encoding)
            code_hasher[c.key_run].update(code_encoded)
            if c.is_typeset:
                typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
                typeset_hasher[c.key_typeset].update(code_encoded)
                typeset_hasher[c.key_typeset].update(c.args_prettyprint.encode(encoding))
        elif c.is_cons:
            cons_hasher[c.key_run].update(c.hashable_delims_run.encode(encoding))
            code_encoded = c.code.encode(encoding)
            cons_hasher[c.key_run].update(code_encoded)
            if c.is_typeset:
                typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
                typeset_hasher[c.key_typeset].update(code_encoded)
                typeset_hasher[c.key_typeset].update(c.args_prettyprint.encode(encoding))
        elif c.is_cc:
            cc_hasher[c.cc_type].update(c.hashable_delims_run.encode(encoding))
            cc_hasher[c.cc_type].update(c.code.encode(encoding))
        elif c.is_typeset:
            typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
            typeset_hasher[c.key_typeset].update(c.code.encode(encoding))
            typeset_hasher[c.key_typeset].update(c.args_prettyprint.encode(encoding))
        

    # Store hashes
    code_hash_dict = {}
    for key in code_hasher:
        family = key.split('#', 1)[0]
        code_hash_dict[key] = (code_hasher[key].hexdigest(), 
                               cc_hasher[family].hexdigest(),
                               engine_dict[family].get_hash())
    data['code_hash_dict'] = code_hash_dict
    
    cons_hash_dict = {}
    for key in cons_hasher:
        family = key.split('#', 1)[0]
        cons_hash_dict[key] = (cons_hasher[key].hexdigest(), 
                               cc_hasher[family].hexdigest(),
                               engine_dict[family].get_hash())
    data['cons_hash_dict'] = cons_hash_dict
    
    typeset_hash_dict = {}
    for key in typeset_hasher:
        typeset_hash_dict[key] = typeset_hasher[key].hexdigest()
    data['typeset_hash_dict'] = typeset_hash_dict
    
    
    # See what needs to be updated.
    # In the process, copy over macros and files that may be reused.
    code_update = {}
    cons_update = {}
    pygments_update = {}
    macros = defaultdict(list)
    files = defaultdict(list)
    pygments_macros = {}
    pygments_files = {}
    typeset_cache = {}
    dependencies = defaultdict(dict)
    exit_status = {}
    pygments_settings_changed = {}
    if loaded_old_data:
        old_macros = old_data['macros']
        old_files = old_data['files']
        old_pygments_macros = old_data['pygments_macros']
        old_pygments_files = old_data['pygments_files']
        old_typeset_cache = old_data['typeset_cache']
        old_dependencies = old_data['dependencies']
        old_exit_status = old_data['exit_status']
        old_code_hash_dict = old_data['code_hash_dict']
        old_cons_hash_dict = old_data['cons_hash_dict']
        old_typeset_hash_dict = old_data['typeset_hash_dict']
        old_pygments_settings = old_data['pygments_settings']
        for s in pygments_settings:
            if (s in old_pygments_settings and 
                    pygments_settings[s] == old_pygments_settings[s]):
                pygments_settings_changed[s] = False
            else:
                pygments_settings_changed[s] = True

    # If old data was loaded (and thus is compatible) determine what has 
    # changed so that only 
    # modified code may be executed.  Otherwise, execute everything.
    # We don't have to worry about checking for changes in pyfuture, because
    # custom code and default code are hashed.  The treatment of keeptemps
    # could be made more efficient (if changed to 'none', just delete old temp
    # files rather than running everything again), but given that it is 
    # intended as a debugging aid, that probable isn't worth it.
    # We don't have to worry about hashdependencies changing, because if it 
    # does the hashes won't match (file contents vs. mtime) and thus code will
    # be re-executed.
    if loaded_old_data and data['code_vitals'] == old_data['code_vitals']:
        # Compare the hash values, and set which code needs to be run
        for key in code_hash_dict:
            if (key in old_code_hash_dict and 
                    not should_rerun(code_hash_dict[key], old_code_hash_dict[key], old_exit_status[key], key, rerun, data, old_data, temp_data)):
                code_update[key] = False
                macros[key] = old_macros[key]
                files[key] = old_files[key]
                dependencies[key] = old_dependencies[key]
                exit_status[key] = old_exit_status[key]
            else:
                code_update[key] = True        
    else:        
        for key in code_hash_dict:
            code_update[key] = True
    
    if loaded_old_data and data['cons_vitals'] == old_data['cons_vitals']:
        # Compare the hash values, and set which code needs to be run
        for key in cons_hash_dict:
            if (key in old_cons_hash_dict and 
                    not should_rerun(cons_hash_dict[key], old_cons_hash_dict[key], old_exit_status[key], key, rerun, data, old_data, temp_data)):
                cons_update[key] = False
                macros[key] = old_macros[key]
                files[key] = old_files[key]
                typeset_cache[key] = old_typeset_cache[key]
                dependencies[key] = old_dependencies[key]
                exit_status[key] = old_exit_status[key]
            else:
                cons_update[key] = True        
    else:        
        for key in cons_hash_dict:
            cons_update[key] = True
    
    if loaded_old_data and data['typeset_vitals'] == old_data['typeset_vitals']:
        for key in typeset_hash_dict:
            family = key.split('#', 1)[0]
            if family in pygments_settings:
                if (not pygments_settings_changed[family] and
                        key in old_typeset_hash_dict and 
                        typeset_hash_dict[key] == old_typeset_hash_dict[key]):
                    pygments_update[key] = False
                    if key in old_pygments_macros:
                        pygments_macros[key] = old_pygments_macros[key]
                    if key in old_pygments_files:
                        pygments_files[key] = old_pygments_files[key]
                else:
                    pygments_update[key] = True
            else:
                pygments_update[key] = False
        # Make sure Pygments styles are up-to-date
        pygments_style_list = list(get_all_styles())
        if pygments_style_list != old_data['pygments_style_list']:
            pygments_style_defs = {}
            # Lazy import
            from pygments.formatters import LatexFormatter
            for s in pygments_style_list:
                formatter = LatexFormatter(style=s, commandprefix='PYG'+s)
                pygments_style_defs[s] = formatter.get_style_defs()
        else:
            pygments_style_defs = old_data['pygments_style_defs']
    else:
        for key in typeset_hash_dict:
            family = key.split('#', 1)[0]
            if family in pygments_settings:
                pygments_update[key] = True
            else:
                pygments_update[key] = False
        # Create Pygments styles
        pygments_style_list = list(get_all_styles())
        pygments_style_defs = {}
        # Lazy import
        from pygments.formatters import LatexFormatter
        for s in pygments_style_list:
            formatter = LatexFormatter(style=s, commandprefix='PYG'+s)
            pygments_style_defs[s] = formatter.get_style_defs()
    
    # Save to data
    temp_data['code_update'] = code_update
    temp_data['cons_update'] = cons_update
    temp_data['pygments_update'] = pygments_update
    data['macros'] = macros
    data['files'] = files
    data['pygments_macros'] = pygments_macros
    data['pygments_style_list'] = pygments_style_list
    data['pygments_style_defs'] = pygments_style_defs
    data['pygments_files'] = pygments_files
    data['typeset_cache'] = typeset_cache
    data['dependencies'] = dependencies
    data['exit_status'] = exit_status
    
    
    # Clean up for code that will be run again, and for code that no longer 
    # exists.
    if loaded_old_data:
        # Take care of code files
        for key in code_hash_dict:
            if code_update[key] and key in old_files:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_code_hash_dict:
            if key not in code_hash_dict:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        # Take care of old console files
        for key in cons_hash_dict:
            if cons_update[key] and key in old_files:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_cons_hash_dict:
            if key not in cons_hash_dict:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        # Take care of old Pygments files
        # The approach here is a little different since there isn't a 
        # Pygments-specific hash dict, but there is a Pygments-specific 
        # dict of lists of files.
        for key in pygments_update:
            if pygments_update[key] and key in old_pygments_files:
                for f in old_pygments_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_pygments_files:
            if key not in pygments_update:
                for f in old_pygments_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)





def parse_code_write_scripts(data, temp_data, engine_dict):
    '''
    Parse the code file into separate scripts, and write them to file.
    '''
    code_dict = defaultdict(list)
    cc_dict_begin = defaultdict(list)
    cc_dict_end = defaultdict(list)
    cons_dict = defaultdict(list)
    pygments_list = []
    # Create variables to ease data access
    encoding = data['encoding']
    utilspath = data['utilspath']
    outputdir = data['settings']['outputdir']
    workingdir = data['settings']['workingdir']
    pytxcode = temp_data['pytxcode']
    code_update = temp_data['code_update']
    cons_update = temp_data['cons_update']
    pygments_update = temp_data['pygments_update']
    files = data['files']
    # We need to keep track of the last instance for each session, so 
    # that duplicates can be eliminated.  Some LaTeX environments process 
    # their content multiple times and thus will create duplicates.  We 
    # need to initialize everything at -1, since instances begin at zero.
    def negative_one():
        return -1
    last_instance = defaultdict(negative_one)
    for c in pytxcode:
        if c.instance_int > last_instance[c.key_run]:
            last_instance[c.key_run] = c.instance_int
            if c.is_code:
                if code_update[c.key_run]:
                    code_dict[c.key_run].append(c)
                if c.is_typeset and pygments_update[c.key_typeset]:
                    pygments_list.append(c)
            elif c.is_cons:
                # Only append to Pygments if not run, since Pygments is 
                # automatically taken care of during run for console content
                if cons_update[c.key_run]:
                    cons_dict[c.key_run].append(c)
                elif c.is_typeset and pygments_update[c.key_typeset]:
                    pygments_list.append(c)
            elif (c.is_pyg or c.is_verb) and pygments_update[c.key_typeset]:
                pygments_list.append(c)
            elif c.is_cc:
                if c.cc_pos == 'begin':
                    cc_dict_begin[c.cc_type].append(c)
                else:
                    cc_dict_end[c.cc_type].append(c)
    
    # Save
    temp_data['code_dict'] = code_dict
    temp_data['cc_dict_begin'] = cc_dict_begin
    temp_data['cc_dict_end'] = cc_dict_end
    temp_data['cons_dict'] = cons_dict
    temp_data['pygments_list'] = pygments_list

    # Save the code sessions that need to be updated
    # Keep track of the files that are created
    # Also accumulate error indices for handling stderr
    code_index_dict = {}
    for key in code_dict:
        family, session, restart = key.split('#')
        fname = os.path.join(outputdir, family + '_' + session + '_' + restart + '.' + engine_dict[family].extension)
        files[key].append(fname)
        sessionfile = open(fname, 'w', encoding=encoding)
        script, code_index = engine_dict[family].get_script(encoding,
                                                              utilspath,
                                                              workingdir,
                                                              cc_dict_begin[family],
                                                              code_dict[key],
                                                              cc_dict_end[family])
        for lines in script:
            sessionfile.write(lines)
        sessionfile.close()
        code_index_dict[key] = code_index
    temp_data['code_index_dict'] = code_index_dict




def do_multiprocessing(data, temp_data, old_data, engine_dict):
    jobname = data['jobname']
    encoding = data['encoding']
    outputdir = data['settings']['outputdir']
    workingdir = data['settings']['workingdir']
    keeptemps = data['settings']['keeptemps']
    fvextfile = data['settings']['fvextfile']
    pygments_settings = data['pygments_settings']
    jobs = temp_data['jobs']
    verbose = temp_data['verbose']
    
    code_dict = temp_data['code_dict']
    cons_dict = temp_data['cons_dict']
    cc_dict_begin = temp_data['cc_dict_begin']
    cc_dict_end = temp_data['cc_dict_end']
    pygments_list = temp_data['pygments_list']
    pygments_style_defs = data['pygments_style_defs']

    files = data['files']
    macros = data['macros']
    pygments_files = data['pygments_files']
    pygments_macros = data['pygments_macros']
    typeset_cache = data['typeset_cache']
    
    errors = temp_data['errors']
    warnings = temp_data['warnings']
    
    makestderr = data['settings']['makestderr']
    stderrfilename = data['settings']['stderrfilename']
    code_index_dict = temp_data['code_index_dict']
    
    hashdependencies = temp_data['hashdependencies']
    dependencies = data['dependencies']
    exit_status = data['exit_status']
    start_time = data['start_time']
    
    
    # Create a pool for multiprocessing.  Set the maximum number of 
    # concurrent processes to a user-specified value for jobs.  If the user
    # has not specified a value, then it will be None, and 
    # multiprocessing.Pool() will use cpu_count().
    pool = multiprocessing.Pool(jobs)
    tasks = []
    
    # If verbose, print a list of processes
    if verbose:
        print('\n* PythonTeX will run the following processes')
        print('  (maximum concurrent processes = {0})'.format(jobs))
    
    # Add code processes.  Note that everything placed in the codedict 
    # needs to be executed, based on previous testing, except for custom code.
    for key in code_dict:
        family = key.split('#')[0]
        # Uncomment the following for debugging, and comment out what follows
        '''run_code(encoding, outputdir, workingdir, code_dict[key],
                                                 engine_dict[family].language,
                                                 engine_dict[family].command,
                                                 engine_dict[family].created,
                                                 engine_dict[family].extension,
                                                 makestderr, stderrfilename,
                                                 code_index_dict[key],
                                                 engine_dict[family].errors,
                                                 engine_dict[family].warnings,
                                                 engine_dict[family].linenumbers,
                                                 engine_dict[family].lookbehind,
                                                 keeptemps, hashdependencies)'''
        tasks.append(pool.apply_async(run_code, [encoding, outputdir, 
                                                 workingdir, code_dict[key],
                                                 engine_dict[family].language,
                                                 engine_dict[family].command,
                                                 engine_dict[family].created,
                                                 engine_dict[family].extension,
                                                 makestderr, stderrfilename,
                                                 code_index_dict[key],
                                                 engine_dict[family].errors,
                                                 engine_dict[family].warnings,
                                                 engine_dict[family].linenumbers,
                                                 engine_dict[family].lookbehind,
                                                 keeptemps, hashdependencies]))
        if verbose:
            print('    - Code process ' + key.replace('#', ':'))
    
    # Add console processes
    for key in cons_dict:
        family = key.split('#')[0]
        if engine_dict[family].language.startswith('python'):
            if family in pygments_settings:
                # Uncomment the following for debugging
                '''python_console(jobname, encoding, outputdir, workingdir, 
                               fvextfile, pygments_settings[family],
                               cc_dict_begin[family], cons_dict[key],
                               cc_dict_end[family], engine_dict[family].startup,
                               engine_dict[family].banner, 
                               engine_dict[family].filename)'''
                tasks.append(pool.apply_async(python_console, [jobname, encoding,
                                                               outputdir, workingdir,
                                                               fvextfile,
                                                               pygments_settings[family],
                                                               cc_dict_begin[family],
                                                               cons_dict[key],
                                                               cc_dict_end[family],
                                                               engine_dict[family].startup,
                                                               engine_dict[family].banner,
                                                               engine_dict[family].filename]))
            else:
                tasks.append(pool.apply_async(python_console, [jobname, encoding,
                                                               outputdir, workingdir,
                                                               fvextfile,
                                                               None,
                                                               cc_dict_begin[family],
                                                               cons_dict[key],
                                                               cc_dict_end[family],
                                                               engine_dict[family].startup,
                                                               engine_dict[family].banner,
                                                               engine_dict[family].filename]))  
        else:
            print('* PythonTeX error')
            print('    Currently, non-Python consoles are not supported')
            errors += 1
        if verbose:
            print('    - Console process ' + key.replace('#', ':'))
    
    # Add a Pygments process
    if pygments_list:
        tasks.append(pool.apply_async(do_pygments, [encoding, outputdir, 
                                                    fvextfile,
                                                    pygments_list,
                                                    pygments_settings,
                                                    typeset_cache]))
        if verbose:
            print('    - Pygments process')
    
    # Execute the processes
    pool.close()
    pool.join()
    
    # Get the outputs of processes
    # Get the files and macros created.  Get the number of errors and warnings
    # produced.  Get any messages returned.  Get the exit_status, which is a 
    # dictionary of code that failed and thus must be run again (its hash is
    # set to a null string).  Keep track of whether there were any new files,
    # so that the last time of file creation in .pytxmcr can be updated.
    new_files = False
    messages = []
    for task in tasks:
        result = task.get()
        if result['process'] == 'code':
            key = result['key']
            files[key].extend(result['files'])
            if result['files']:
                new_files = True
            macros[key].extend(result['macros'])
            dependencies[key] = result['dependencies']
            errors += result['errors']
            warnings += result['warnings']
            exit_status[key] = (result['errors'], result['warnings'])
            messages.extend(result['messages'])            
        elif result['process'] == 'console':
            key = result['key']
            files[key].extend(result['files'])
            if result['files']:
                new_files = True
            macros[key].extend(result['macros'])
            pygments_files.update(result['pygments_files'])
            pygments_macros.update(result['pygments_macros'])
            dependencies[key] = result['dependencies']
            typeset_cache[key] = result['typeset_cache']
            errors += result['errors']
            warnings += result['warnings']
            exit_status[key] = (result['errors'], result['warnings'])
            messages.extend(result['messages'])
        elif result['process'] == 'pygments':
            pygments_files.update(result['pygments_files'])
            for k in result['pygments_files']:
                if result['pygments_files'][k]:
                    new_files = True
                    break
            pygments_macros.update(result['pygments_macros'])
            errors += result['errors']
            warnings += result['warnings']
            messages.extend(result['messages'])        
    
    # Do a quick check to see if any dependencies were modified since the
    # beginning of the run.  If so, reset them so they will run next time and
    # issue a warning
    unresolved_dependencies = False
    unresolved_sessions = []
    for key in dependencies:
        for dep, val in dependencies[key].items():
            if val[0] > start_time:
                unresolved_dependencies = True
                dependencies[key][dep] = (None, None)
                unresolved_sessions.append(key.replace('#', ':'))
    if unresolved_dependencies:
        print('* PythonTeX warning')
        print('    The following have dependencies that have been modified')
        print('    Run PythonTeX again to resolve dependencies')
        for s in set(unresolved_sessions):
            print('    - ' + s)
        warnings += 1
    
    
    # Save all content (only needs to be done if code was indeed run).
    # Save a commented-out time corresponding to the last time PythonTeX ran
    # and created files, so that tools like latexmk can easily detect when 
    # another run is needed.
    if tasks:
        if new_files or not temp_data['loaded_old_data']:
            last_new_file_time = start_time
        else:
            last_new_file_time = old_data['last_new_file_time']
        data['last_new_file_time'] = last_new_file_time
        
        macro_file = open(os.path.join(outputdir, jobname + '.pytxmcr'), 'w', encoding=encoding)
        macro_file.write('%Last time of file creation:  ' + str(last_new_file_time) + '\n\n')
        for key in macros:
            macro_file.write(''.join(macros[key]))
        macro_file.close()
        
        pygments_macro_file = open(os.path.join(outputdir, jobname + '.pytxpyg'), 'w', encoding=encoding)
        # Only save Pygments styles that are used
        style_set = set([pygments_settings[k]['formatter_options']['style'] for k in pygments_settings if k != ':GLOBAL'])
        for key in pygments_style_defs:
            if key in style_set:
                pygments_macro_file.write(''.join(pygments_style_defs[key]))
        for key in pygments_macros:
            pygments_macro_file.write(''.join(pygments_macros[key]))
        pygments_macro_file.close()
        
        pythontex_data_file = os.path.join(outputdir, 'pythontex_data.pkl')
        f = open(pythontex_data_file, 'wb')
        pickle.dump(data, f, -1)
        f.close()
    
    # Print any errors and warnings.
    if messages:
        print('\n'.join(messages))
    sys.stdout.flush()
    # Store errors and warnings back into temp_data
    # This is needed because they are ints and thus immutable
    temp_data['errors'] = errors
    temp_data['warnings'] = warnings




def run_code(encoding, outputdir, workingdir, code_list, language, command, 
             command_created, extension, makestderr, stderrfilename, 
             code_index, errorsig, warningsig, linesig, stderrlookbehind, 
             keeptemps, hashdependencies):
    '''
    Function for multiprocessing code files
    '''
    import shlex
    
    # Create what's needed for storing results
    family = code_list[0].family
    session = code_list[0].session
    key_run = code_list[0].key_run
    files = []
    macros = []
    dependencies = {}
    errors = 0
    warnings = 0
    unknowns = 0
    messages = []
    
    # Create message lists only for stderr, one for undelimited stderr and 
    # one for delimited, so it's easy to keep track of if there is any 
    # stderr.  These are added onto messages at the end.
    err_messages_ud = []
    err_messages_d = []
    
    # We need to let the user know we are switching code files
    # We check at the end to see if there were indeed any errors and warnings
    # and if not, clear messages.
    messages.append('\n----  Messages for ' + key_run.replace('#', ':') + '  ----')
    
    # Open files for stdout and stderr, run the code, then close the files
    basename = key_run.replace('#', '_')
    out_file_name = os.path.join(outputdir, basename + '.out')
    err_file_name = os.path.join(outputdir, basename + '.err')
    out_file = open(out_file_name, 'w', encoding=encoding)
    err_file = open(err_file_name, 'w', encoding=encoding)
    # Note that command is a string, which must be converted to list
    # Must double-escape any backslashes so that they survive `shlex.split()`
    script = os.path.expanduser(os.path.normcase(os.path.join(outputdir, basename)))
    if os.path.isabs(script):
        script_full = script
    else:
        script_full = os.path.expanduser(os.path.normcase(os.path.join(os.getcwd(), outputdir, basename)))
    # `shlex.split()` only works with Unicode after 2.7.2
    if (sys.version_info.major == 2 and sys.version_info.micro < 3):
        exec_cmd = shlex.split(bytes(command.format(file=script.replace('\\', '\\\\'), File=script_full.replace('\\', '\\\\'))))
        exec_cmd = [unicode(elem) for elem in exec_cmd]
    else:
        exec_cmd = shlex.split(command.format(file=script.replace('\\', '\\\\'), File=script_full.replace('\\', '\\\\')))
    # Add any created files due to the command
    # This needs to be done before attempts to execute, to prevent orphans
    for f in command_created:
        files.append(f.format(file=script))
    try:
        proc = subprocess.Popen(exec_cmd, stdout=out_file, stderr=err_file)
    except WindowsError as e:
        if e.errno == 2:
            # Batch files won't be found when called without extension. They
            # would be found if `shell=True`, but then getting the right
            # exit code is tricky.  So we perform some `cmd` trickery that
            # is essentially equivalent to `shell=True`, but gives correct 
            # exit codes.  Note that `subprocess.Popen()` works with strings
            # under Windows; a list is not required.
            exec_cmd_string = ' '.join(exec_cmd)
            exec_cmd_string = 'cmd /C "@echo off & call {0} & if errorlevel 1 exit 1"'.format(exec_cmd_string)
            proc = subprocess.Popen(exec_cmd_string, stdout=out_file, stderr=err_file)
        else:
            raise
        
    proc.wait()        
    out_file.close()
    err_file.close()
    
    # Process saved stdout into file(s) that are included in the TeX document.
    #
    # Go through the saved output line by line, and save any printed content 
    # to its own file, named based on instance.
    #
    # The very end of the stdout lists dependencies, if any, so we start by
    # removing and processing those.
    if not os.path.isfile(out_file_name):
        messages.append('* PythonTeX error')
        messages.append('    Missing output file for ' + key_run.replace('#', ':'))
        errors += 1
    else:
        f = open(out_file_name, 'r', encoding=encoding)
        out = f.read()
        f.close()
        try:
            out, created = out.rsplit('=>PYTHONTEX:CREATED#\n', 1)
            out, deps = out.rsplit('=>PYTHONTEX:DEPENDENCIES#\n', 1)
            valid_stdout = True
        except:
            valid_stdout = False
            if proc.returncode == 0:
                raise ValueError('Missing "created" and/or "dependencies" delims in stdout; invalid template?')
                    
        if valid_stdout:
            # Add created files to created list
            for c in created.splitlines():
                if os.path.isabs(os.path.expanduser(os.path.normcase(c))):
                    files.append(c)
                else:
                    files.append(os.path.join(workingdir, c))
            
            # Create a set of dependencies, to eliminate duplicates in the event
            # that there are any.  This is mainly useful when dependencies are
            # automatically determined (for example, through redefining open()), 
            # may be specified multiple times as a result, and are hashed (and 
            # of a large enough size that hashing time is non-negligible).
            deps = set([dep for dep in deps.splitlines()])
            # Process dependencies; get mtimes and (if specified) hashes
            for dep in deps:
                dep_file = os.path.expanduser(os.path.normcase(dep))
                if not os.path.isabs(dep_file):
                    dep_file = os.path.join(workingdir, dep_file)
                if not os.path.isfile(dep_file):
                    # If we can't find the file, we return a null hash and issue 
                    # an error.  We don't need to change the exit status.  If the 
                    # code does depend on the file, there will be a separate 
                    # error when the code attempts to use the file.  If the code 
                    # doesn't really depend on the file, then the error will be 
                    # raised again anyway the next time PythonTeX runs when the 
                    # dependency is listed but not found.
                    dependencies[dep] = (None, None)
                    messages.append('* PythonTeX error')
                    messages.append('    Cannot find dependency "' + dep + '"')
                    messages.append('    It belongs to ' + key_run.replace('#', ':'))
                    messages.append('    Relative paths to dependencies must be specified from the working directory.')
                    errors += 1                
                elif hashdependencies:
                    # Read and hash the file in binary.  Opening in text mode 
                    # would require an unnecessary decoding and encoding cycle.
                    hasher = sha1()
                    f = open(dep_file, 'rb')
                    hasher.update(f.read())
                    f.close()
                    dependencies[dep] = (os.path.getmtime(dep_file), hasher.hexdigest())
                else:
                    dependencies[dep] = (os.path.getmtime(dep_file), '')
            
            for block in out.split('=>PYTHONTEX:STDOUT#')[1:]:
                if block:
                    delims, content = block.split('#\n', 1)
                    if content:
                        instance, command = delims.split('#')
                        if instance.endswith('CC'):
                            messages.append('* PythonTeX warning')
                            messages.append('    Custom code for "' + family + '" attempted to print or write to stdout')
                            messages.append('    This is not supported; use a normal code command or environment')
                            messages.append('    The following content was written:')
                            messages.append('')
                            messages.extend(['    ' + l for l in content.splitlines()])
                            warnings += 1
                        elif command == 'i':
                            content = r'\pytx@SVMCR{pytx@MCR@' + key_run.replace('#', '@') + '@' + instance + '}\n' + content.rstrip('\n') + '\\endpytx@SVMCR\n\n'
                            macros.append(content)
                        else:
                            fname = os.path.join(outputdir, basename + '_' + instance + '.stdout')
                            f = open(fname, 'w', encoding=encoding)
                            f.write(content)
                            f.close()
                            files.append(fname)

    # Process stderr
    if not os.path.isfile(err_file_name):
        messages.append('* PythonTeX error')
        messages.append('    Missing stderr file for ' + key_run.replace('#', ':'))
        errors += 1
    else:
        # Open error and code files.
        f = open(err_file_name, encoding=encoding)
        err = f.readlines()
        f.close()
        # Divide stderr into an undelimited and a delimited portion
        found = False
        for n, line in enumerate(err):
            if line.startswith('=>PYTHONTEX:STDERR#'):
                found = True
                err_ud = err[:n]
                err_d = err[n:]
                break
        if not found:
            err_ud = err
            err_d = []
        # Create a dict for storing any stderr content that will be saved
        err_dict = defaultdict(list)
        # Create the full basename that will be replaced in stderr
        # We need two versions, one with the correct slashes for the OS,
        # and one with the opposite slashes.  This is needed when a language
        # doesn't obey the OS's slash convention in paths given in stderr.  
        # For example, Windows uses backslashes, but Ruby under Windows uses 
        # forward in paths given in stderr.
        fullbasename_correct = os.path.join(outputdir, basename)
        if '\\' in fullbasename_correct:
            fullbasename_reslashed = fullbasename_correct.replace('\\', '/')
        else:
            fullbasename_reslashed = fullbasename_correct.replace('/', '\\')
        
        if err_ud:
            it = iter(code_index.items())
            index_now = next(it)
            index_next = index_now
            start_errgobble = None
            for n, line in enumerate(err_ud):
                if basename in line:
                    # Get the gobbleation.  This is used to determine if 
                    # other lines containing the basename are a continuation,
                    # or separate messages.
                    errgobble = match('(\s*)', line).groups()[0]
                    if start_errgobble is None:
                        start_errgobble = errgobble
                    # Only issue a message and track down the line numer if
                    # this is indeed the start of a new message, rather than
                    # a continuation of an old message that happens to 
                    # contain the basename
                    if errgobble == start_errgobble:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            while index_next[1].lines_total < errlinenum:
                                try:
                                    index_now, index_next = index_next, next(it)
                                except:
                                    break
                            if errlinenum > index_now[1].lines_total + index_now[1].lines_input:
                                doclinenum = str(index_now[1].line_int + index_now[1].lines_input)
                            else:
                                doclinenum = str(index_now[1].line_int + errlinenum - index_now[1].lines_total - 1)
                            input_file = index_now[1].input_file
                        else:
                            doclinenum = '??'
                            input_file = '??'
                        
                        # Try to determine if we are dealing with an error or a 
                        # warning.
                        found = False
                        index = n
                        if stderrlookbehind:
                            while index >= 0:
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                past_line = err_ud[index]
                                if (index < n and basename in past_line):
                                    break
                                for pattern in warningsig:
                                    if pattern in past_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in past_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index -= 1
                        else:
                            while index < len(err_ud):
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                future_line = err_ud[index]
                                if (index > n and basename in future_line and 
                                        future_line.startswith(start_errgobble)):
                                    break
                                for pattern in warningsig:
                                    if pattern in future_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in future_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index += 1
                        # If an error or warning wasn't positively identified,
                        # increment unknowns.
                        if not found:
                            unknowns += 1
                            alert_type = 'unknown'
                        if input_file:
                            err_messages_ud.append('* PythonTeX stderr - {0} on line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                        else:
                            err_messages_ud.append('* PythonTeX stderr - {0} on line {1}:'.format(alert_type, doclinenum))
                    err_messages_ud.append('  ' + line.replace(outputdir, '<outputdir>').rstrip('\n'))
                else:
                    err_messages_ud.append('  ' + line.rstrip('\n'))
            
            # Create .stderr
            if makestderr and err_messages_ud:
                process = False
                it = iter(code_index.items())
                index_now = next(it)
                index_next = index_now
                it_last = it
                index_now_last = index_now
                index_next_last = index_next
                err_key_last_int = -1
                for n, line in enumerate(err_ud):
                    if basename in line:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            if index_next[1].lines_total >= errlinenum:
                                it = it_last
                                index_now = index_now_last
                                index_next = index_next_last
                            else:
                                it_last = it
                                index_now_last = index_now
                                index_next_last = index_next
                            while index_next[1].lines_total < errlinenum:
                                try:
                                    index_now, index_next = index_next, next(it)
                                except:
                                    index_now = index_next
                                    break
                            if index_now[0].endswith('CC'):
                                process = False
                            else:
                                process = True
                                if len(index_now[1].command) > 1:
                                    if errlinenum > index_now[1].lines_total + index_now[1].lines_input:
                                        codelinenum = str(index_now[1].lines_user + index_now[1].lines_input + 1)
                                    else:
                                        codelinenum = str(index_now[1].lines_user + errlinenum - index_now[1].lines_total - index_now[1].inline_count)
                                else:
                                    codelinenum = '1'
                        else:
                            codelinenum = '??'
                            messages.append('* PythonTeX error')
                            messages.append('    Line number ' + str(errlinenum) + ' could not be synced with the document')
                            messages.append('    Content from stderr is not delimited, and cannot be resolved')
                            errors += 1
                            process = False
                        
                        if process:
                            if int(index_now[0]) > err_key_last_int:
                                err_key = basename + '_' + index_now[0]
                                err_key_last_int = int(index_now[0])
                            line = line.replace(str(errlinenum), str(codelinenum), 1)
                            if fullbasename_correct in line:
                                fullbasename = fullbasename_correct
                            else:
                                fullbasename = fullbasename_reslashed
                            if stderrfilename == 'full':
                                line = line.replace(fullbasename, basename)
                            elif stderrfilename == 'session':
                                line = line.replace(fullbasename, session)
                            elif stderrfilename == 'genericfile':
                                line = line.replace(fullbasename + '.' + extension, '<file>')
                            elif stderrfilename == 'genericscript':
                                line = line.replace(fullbasename + '.' + extension, '<script>')
                            err_dict[err_key].append(line)
                    elif process:
                        err_dict[err_key].append(line)
        
        if err_d:
            start_errgobble = None
            msg = []
            found_basename = False
            for n, line in enumerate(err_d):
                if line.startswith('=>PYTHONTEX:STDERR#'):
                    # Store the last group of messages.  Messages
                    # can't be directly appended to the main list, because
                    # a PythonTeX message must be inserted at the beginning 
                    # of each chunk of stderr that never references
                    # the script that was executed.  If the script is never
                    # referenced, then line numbers aren't automatically 
                    # synced.  These types of situations are created by 
                    # warnings.warn() etc.
                    if msg:
                        if not found_basename:
                            # Get line number for command or beginning of
                            # environment
                            instance = last_delim.split('#')[1]
                            doclinenum = str(code_index[instance].line_int)
                            input_file = code_index[instance].input_file
                            # Try to identify alert.  We have to parse all
                            # lines for signs of errors and warnings.  This 
                            # may result in overcounting, but it's the best
                            # we can do--otherwise, we could easily 
                            # undercount, or, finding a warning, miss a 
                            # subsequent error.  When this code is actually
                            # used, it's already a sign that normal parsing
                            # has failed.
                            found_error = False
                            found_warning = False
                            for l in msg:
                                for pattern in warningsig:
                                    if pattern in l:
                                        warnings += 1
                                        found_warning = True
                                for pattern in errorsig:
                                    if pattern in l:
                                        errors += 1
                                        found_warning = True
                            if found_error:
                                alert_type = 'error'
                            elif found_warning:
                                alert_type = 'warning'
                            else:
                                unknowns += 1
                                alert_type = 'unknown'
                            if input_file:
                                err_messages_d.append('* PythonTeX stderr - {0} near line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                            else:
                                err_messages_d.append('* PythonTeX stderr - {0} near line {1}:'.format(alert_type, doclinenum))
                        err_messages_d.extend(msg)
                    msg = []
                    found_basename = False
                    # Never process delimiting info until it is used
                    # Rather, store the index of the last delimiter
                    last_delim = line
                elif basename in line:
                    found_basename = True
                    # Get the gobbleation.  This is used to determine if 
                    # other lines containing the basename are a continuation,
                    # or separate messages.
                    errgobble = match('(\s*)', line).groups()[0]
                    if start_errgobble is None:
                        start_errgobble = errgobble
                    # Only issue a message and track down the line numer if
                    # this is indeed the start of a new message, rather than
                    # a continuation of an old message that happens to 
                    # contain the basename
                    if errgobble == start_errgobble:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            # Get info from last delim
                            instance, command = last_delim.split('#')[1:-1]
                            # Calculate the line number in the document
                            ei = code_index[instance]
                            if errlinenum > ei.lines_total + ei.lines_input:
                                doclinenum = str(ei.line_int + ei.lines_input)
                            else:
                                doclinenum = str(ei.line_int + errlinenum - ei.lines_total - 1)
                            input_file = ei.input_file
                        else:
                            doclinenum = '??'
                            input_file = '??'
                        
                        # Try to determine if we are dealing with an error or a 
                        # warning.
                        found = False
                        index = n
                        if stderrlookbehind:
                            while index >= 0:
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                past_line = err_d[index]
                                if (past_line.startswith('=>PYTHONTEX:STDERR#') or 
                                        (index < n and basename in past_line)):
                                    break
                                for pattern in warningsig:
                                    if pattern in past_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in past_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index -= 1
                        else:
                            while index < len(err_d):
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                future_line = err_d[index]
                                if (future_line.startswith('=>PYTHONTEX:STDERR#') or 
                                        (index > n and basename in future_line and future_line.startswith(start_errgobble))):
                                    break
                                for pattern in warningsig:
                                    if pattern in future_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in future_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index += 1
                        # If an error or warning wasn't positively identified,
                        # assume error for safety but indicate uncertainty.
                        if not found:
                            unknowns += 1
                            alert_type = 'unknown'
                        if input_file:
                            msg.append('* PythonTeX stderr - {0} on line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                        else:
                            msg.append('* PythonTeX stderr - {0} on line {1}:'.format(alert_type, doclinenum))
                    # Clean up the stderr format a little, to keep it compact
                    line = line.replace(outputdir, '<outputdir>').rstrip('\n')
                    if '/<outputdir>' in line or '\\<outputdir>' in line:
                        line = sub(r'(?:(?:[A-Za-z]:\\)|(?:~?/)).*<outputdir>', '<outputdir>', line)
                    msg.append('  ' + line)
                else:
                    msg.append('  ' + line.rstrip('\n'))
            # Deal with any leftover messages
            if msg:
                if not found_basename:
                    # Get line number for command or beginning of
                    # environment
                    instance = last_delim.split('#')[1]
                    doclinenum = str(code_index[instance].line_int)
                    input_file = code_index[instance].input_file
                    # Try to identify alert.  We have to parse all
                    # lines for signs of errors and warnings.  This 
                    # may result in overcounting, but it's the best
                    # we can do--otherwise, we could easily 
                    # undercount, or, finding a warning, miss a 
                    # subsequent error.  When this code is actually
                    # used, it's already a sign that normal parsing
                    # has failed.
                    found_error = False
                    found_warning = False
                    for l in msg:
                        for pattern in warningsig:
                            if pattern in l:
                                warnings += 1
                                found_warning = True
                        for pattern in errorsig:
                            if pattern in l:
                                errors += 1
                                found_warning = True
                    if found_error:
                        alert_type = 'error'
                    elif found_warning:
                        alert_type = 'warning'
                    else:
                        unknowns += 1
                        alert_type = 'unknown'
                    if input_file:
                        err_messages_d.append('* PythonTeX stderr - {0} near line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                    else:
                        err_messages_d.append('* PythonTeX stderr - {0} near line {1}:'.format(alert_type, doclinenum))
                err_messages_d.extend(msg)
            
            # Create .stderr
            if makestderr and err_messages_d:
                process = False
                for n, line in enumerate(err_d):
                    if line.startswith('=>PYTHONTEX:STDERR#'):
                        instance, command = line.split('#')[1:-1]
                        if instance.endswith('CC'):
                            process = False
                        else:
                            process = True
                            err_key = basename + '_' + instance
                    elif process and basename in line:
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            # Calculate the line number in the document
                            # Account for inline
                            ei = code_index[instance]
                            # Store the `instance` in case it's 
                            # incremented later
                            last_instance = instance
                            # If the error or warning was actually triggered
                            # later on (for example, multiline string with
                            # missing final delimiter), look ahead and 
                            # determine the correct instance, so that
                            # we get the correct line number.  We don't
                            # associate the created stderr with this later
                            # instance, however, but rather with the instance
                            # in which the error began.  Doing that might 
                            # possibly be preferable in some cases, but would
                            # also require that the current stderr be split
                            # between multiple instances, requiring extra
                            # parsing.
                            while errlinenum > ei.lines_total + ei.lines_input:
                                next_instance = str(int(instance) + 1)
                                if next_instance in code_index:
                                    next_ei = code_index[next_instance]
                                    if errlinenum > next_ei.lines_total:
                                        instance = next_instance
                                        ei = next_ei
                                    else:
                                        break
                                else:
                                    break
                            if len(command) > 1:
                                if errlinenum > ei.lines_total + ei.lines_input:
                                    codelinenum = str(ei.lines_user + ei.lines_input + 1)
                                else:
                                    codelinenum = str(ei.lines_user + errlinenum - ei.lines_total - ei.inline_count)
                            else:
                                codelinenum = '1'
                            # Reset `instance`, in case incremented
                            instance = last_instance
                        else:
                            codelinenum = '??'
                            messages.append('* PythonTeX notice')
                            messages.append('    Line number ' + str(errlinenum) + ' could not be synced with the document')
                        
                        line = line.replace(str(errlinenum), str(codelinenum), 1)
                        if fullbasename_correct in line:
                            fullbasename = fullbasename_correct
                        else:
                            fullbasename = fullbasename_reslashed
                        if stderrfilename == 'full':
                            line = line.replace(fullbasename, basename)
                        elif stderrfilename == 'session':
                            line = line.replace(fullbasename, session)
                        elif stderrfilename == 'genericfile':
                            line = line.replace(fullbasename + '.' + extension, '<file>')
                        elif stderrfilename == 'genericscript':
                            line = line.replace(fullbasename + '.' + extension, '<script>')
                        err_dict[err_key].append(line)
                    elif process:
                        err_dict[err_key].append(line)
        if err_dict:
            for err_key in err_dict:
                stderr_file_name = os.path.join(outputdir, err_key + '.stderr')
                f = open(stderr_file_name, 'w', encoding=encoding)
                f.write(''.join(err_dict[err_key]))
                f.close()
                files.append(stderr_file_name)
    
    # Clean up temp files, and update the list of existing files
    if keeptemps == 'none':
        for ext in [extension, 'pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
    elif keeptemps == 'code':
        for ext in ['pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
        files.append(os.path.join(outputdir, basename + '.' + extension))
    elif keeptemps == 'all':
        for ext in [extension, 'pytxmcr', 'out', 'err']:
            files.append(os.path.join(outputdir, basename + '.' + ext))

    # Take care of any unknowns, based on exit code
    # Interpret the exit code as an indicator of whether there were errors,
    # and treat unknowns accordingly.  This will cause all warnings to be 
    # misinterpreted as errors if warnings trigger a nonzero exit code.
    # It will also cause all warnings to be misinterpreted as errors if there
    # is a single error that causes a nonzero exit code.  That isn't ideal,
    # but shouldn't be a problem, because as soon as the error(s) are fixed,
    # the exit code will be zero, and then all unknowns will be interpreted
    # as warnings.
    if unknowns:
        if proc.returncode == 0:
            unknowns_type = 'warnings'
            warnings += unknowns
        else:
            unknowns_type = 'errors'
            errors += unknowns
        unknowns_message = '''
                * PythonTeX notice
                    {0} message(s) could not be classified
                    Interpreted as {1}, based on the return code(s)'''
        messages[0] += textwrap.dedent(unknowns_message.format(unknowns, unknowns_type))
    
    # Take care of anything that has escaped detection thus far.
    if proc.returncode == 1 and not errors:
        errors += 1
        command_message = '''
                * PythonTeX error
                    An error occurred but no error messages were identified.
                    This may indicate a bad command or missing program.
                    The following command was executed:
                        "{0}"'''
        messages[0] += textwrap.dedent(command_message.format(' '.join(exec_cmd)))
    
    # Add any stderr messages; otherwise, clear the default message header
    if err_messages_ud:
        messages.extend(err_messages_ud)
    if err_messages_d:
        messages.extend(err_messages_d)
    if len(messages) == 1:
        messages = []
    
    # Return a dict of dicts of results
    return {'process': 'code',
            'key': key_run,
            'files': files,
            'macros': macros,
            'dependencies': dependencies,
            'errors': errors,
            'warnings': warnings,
            'messages': messages}




def do_pygments(encoding, outputdir, fvextfile, pygments_list, 
                pygments_settings, typeset_cache):
    '''
    Create Pygments content.
    
    To be run during multiprocessing.
    '''
    # Lazy import
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import LatexFormatter
    
    # Create what's needed for storing results
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    errors = 0
    warnings = 0
    messages = []
    messages.append('\n----  Messages for Pygments  ----')
    
    # Create dicts of formatters and lexers.
    formatter = dict()
    lexer = dict()
    for codetype in pygments_settings:
        if codetype != ':GLOBAL':
            formatter[codetype] = LatexFormatter(**pygments_settings[codetype]['formatter_options'])
            lexer[codetype] = get_lexer_by_name(pygments_settings[codetype]['lexer'], 
                                                **pygments_settings[codetype]['lexer_options'])
    
    # Actually parse and highlight the code.
    for c in pygments_list:
        if c.is_cons:
            content = typeset_cache[c.key_run][c.instance]
        elif c.is_extfile:
            if os.path.isfile(c.extfile):
                f = open(c.extfile, encoding=encoding)
                content = f.read()
                f.close()
            else:
                content = None
                messages.append('* PythonTeX error')
                messages.append('    Could not find external file ' + c.extfile)
                messages.append('    The file was not pygmentized')
        else:
            content = c.code
        processed = highlight(content, lexer[c.family], formatter[c.family])
        if c.is_inline or content.count('\n') < fvextfile:
            # Highlighted code brought in via macros needs SaveVerbatim
            if c.args_prettyprint:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@SaveVerbatim}}[\1, {4}]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance, c.args_prettyprint), processed, count=1)
            else:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance), processed, count=1)
            processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@SaveVerbatim}\n\n'
            pygments_macros[c.key_typeset].append(processed)
        else:
            if c.args_prettyprint:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@Verbatim}}[\1, {4}]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance, c.args_prettyprint), processed, count=1)
            else:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@Verbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance), processed, count=1)
            processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@Verbatim}\n\n'
            fname = os.path.join(outputdir, c.key_typeset.replace('#', '_') + '.pygtex')
            f = open(fname, 'w', encoding=encoding)
            f.write(processed)
            f.close()
            pygments_files[c.key_typeset].append(fname)
    
    if len(messages) == 1:
        messages = []
    # Return a dict of dicts of results
    return {'process': 'pygments',
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages} 




def python_console(jobname, encoding, outputdir, workingdir, fvextfile,
                   pygments_settings, cc_begin_list, cons_list, cc_end_list,
                   startup, banner, filename):
    '''
    Use Python's ``code`` module to typeset emulated Python interactive 
    sessions, optionally highlighting with Pygments.
    '''
    # Create what's needed for storing results
    key_run = cons_list[0].key_run
    files = []
    macros = []
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    typeset_cache = {}
    dependencies = {}
    errors = 0
    warnings = 0
    messages = []
    messages.append('\n----  Messages for ' + key_run.replace('#', ':') + '  ----')
    
    # Lazy import what's needed
    import code
    from collections import deque
    if sys.version_info[0] == 2:
        # Need a Python 2 interface to io.StringIO that can accept bytes
        import io
        class StringIO(io.StringIO):
            _orig_write = io.StringIO.write
            def write(self, s):
                self._orig_write(unicode(s))
    else:
        from io import StringIO
    
    # Create a custom console class
    class Console(code.InteractiveConsole):
        '''
        A subclass of code.InteractiveConsole that takes a list and treats it
        as a series of console input.
        '''
        
        def __init__(self, banner, filename):
            if banner == 'none':
                self.banner = 'NULL BANNER'
            elif banner == 'standard':
                cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
                self.banner = 'Python {0} on {1}\n{2}'.format(sys.version, sys.platform, cprt)
            elif banner == 'pyversion':
                self.banner = 'Python ' + '.'.join(str(sys.version_info[n]) for n in (0, 1, 2))
            else:
                self.banner = None
            if filename == 'console':
                self.filename = '<console>'
            elif filename == 'stdin':
                self.filename = '<stdin>'
            else:
                self.filename = None
            code.InteractiveConsole.__init__(self, filename=self.filename)
            self.iostdout = StringIO()
    
        def consolize(self, startup, cons_list):
            self.console_code = deque()
            # Delimiters are passed straight through and need newlines
            self.console_code.append('=>PYTHONTEX#STARTUP##\n')
            cons_config = '''
                    import os
                    import sys
                    docdir = os.getcwd()
                    if os.path.isdir('{workingdir}'):
                        os.chdir('{workingdir}')
                        if os.getcwd() not in sys.path:
                            sys.path.append(os.getcwd())
                    else:
                        sys.exit('Cannot find directory {workingdir}')
                    
                    if docdir not in sys.path:
                        sys.path.append(docdir)
                    
                    del docdir
                    '''
            cons_config = cons_config.format(workingdir=workingdir)[1:]
            self.console_code.extend(textwrap.dedent(cons_config).splitlines())
            # Code is processed and doesn't need newlines
            self.console_code.extend(startup.splitlines())
            for c in cons_list:
                self.console_code.append('=>PYTHONTEX#{0}#{1}#\n'.format(c.instance, c.command))
                self.console_code.extend(c.code.splitlines())
            old_stdout = sys.stdout
            sys.stdout = self.iostdout
            self.interact(self.banner)
            sys.stdout = old_stdout
            self.session_log = self.iostdout.getvalue()
    
        def raw_input(self, prompt):
            # Have to do a lot of looping and trying to make sure we get 
            # something valid to execute
            try:
                line = self.console_code.popleft()
            except IndexError:
                raise EOFError
            while line.startswith('=>PYTHONTEX#'):
                # Get new lines until we get one that doesn't begin with a 
                # delimiter.  Then write the last delimited line.
                old_line = line
                try:
                    line = self.console_code.popleft()
                    self.write(old_line)
                except IndexError:
                    raise EOFError
            if line or prompt == sys.ps2:
                self.write('{0}{1}\n'.format(prompt, line))
            else:
                self.write('\n')
            return line
        
        def write(self, data):
            self.iostdout.write(data)
    
    # Need to combine all custom code and user code to pass to consolize
    cons_list = cc_begin_list + cons_list + cc_end_list
    # Create a dict for looking up exceptions.  This is needed for startup 
    # commands and for code commands and environments, since their output
    # isn't typeset
    cons_index = {}
    for c in cons_list:
        cons_index[c.instance] = c.line    
    
    # Consolize the code
    # If the working directory is changed as part of the console code,
    # then we need to get back to where we were.
    con = Console(banner, filename)
    cwd = os.getcwd()
    con.consolize(startup, cons_list)
    os.chdir(cwd)
    
    # Set up Pygments, if applicable
    if pygments_settings is not None:
        pygmentize = True
        # Lazy import
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import LatexFormatter
        formatter = LatexFormatter(**pygments_settings['formatter_options'])
        lexer = get_lexer_by_name(pygments_settings['lexer'], 
                                  **pygments_settings['lexer_options'])
    else:
        pygmentize = False
    
    # Process the console output
    output = con.session_log.split('=>PYTHONTEX#')
    # Extract banner
    if banner == 'none':
        banner_text = ''
    else:
        banner_text = output[0]
    # Ignore the beginning, because it's the banner
    for block in output[1:]:
        delims, console_content = block.split('#\n', 1)
        if console_content:
            instance, command = delims.split('#')
            if instance == 'STARTUP':
                exception = False
                console_content_lines = console_content.splitlines()
                for line in console_content_lines:
                    if (not line.startswith(sys.ps1) and 
                            not line.startswith(sys.ps2) and 
                            line and not line.isspace()):
                        exception = True
                        break
                if exception:
                    if 'Error:' in console_content:
                        errors += 1
                        alert_type = 'error'
                    elif 'Warning:' in console_content:
                        warnings += 1
                        alert_type = 'warning'
                    else:
                        errors += 1
                        alert_type = 'error (?)'
                    messages.append('* PythonTeX stderr - {0} in console startup code:'.format(alert_type))
                    for line in console_content_lines:
                        messages.append('  ' + line)
            elif command in ('c', 'code'):
                exception = False
                console_content_lines = console_content.splitlines()
                for line in console_content_lines:
                    if (line and not line.startswith(sys.ps1) and 
                            not line.startswith(sys.ps2) and 
                            not line.isspace()):
                        exception = True
                        break
                if exception:
                    if 'Error:' in console_content:
                        errors += 1
                        alert_type = 'error'
                    elif 'Warning:' in console_content:
                        warnings += 1
                        alert_type = 'warning'
                    else:
                        errors += 1
                        alert_type = 'error (?)'
                    if instance.endswith('CC'):
                        messages.append('* PythonTeX stderr - {0} near line {1} in custom code for console:'.format(alert_type, cons_index[instance]))
                    else:
                        messages.append('* PythonTeX stderr - {0} near line {1} in console code:'.format(alert_type, cons_index[instance]))
                    messages.append('    Console code is not typeset, and should have no output')
                    for line in console_content_lines:
                        messages.append('  ' + line)
            else:
                if command == 'i':
                    # Currently, there isn't any error checking for invalid
                    # content; it is assumed that a single line of commands 
                    # was entered, producing one or more lines of output.
                    # Given that the current ``\pycon`` command doesn't
                    # allow line breaks to be written to the .pytxcode, that
                    # should be a reasonable assumption.
                    console_content = console_content.split('\n', 1)[1]
                elif console_content.endswith('\n\n'):
                    # Trim unwanted trailing newlines
                    console_content = console_content[:-1]
                if banner_text is not None and command == 'console':
                    # Append banner to first appropriate environment
                    console_content = banner_text + console_content
                    banner_text = None
                # Cache
                key_typeset = key_run + '#' + instance
                typeset_cache[instance] = console_content
                # Process for LaTeX
                if pygmentize:
                    processed = highlight(console_content, lexer, formatter)
                    if console_content.count('\n') < fvextfile:                            
                        processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                        r'\\begin{{pytx@SaveVerbatim}}[\1]{{pytx@{0}}}'.format(key_typeset.replace('#', '@')),
                                        processed, count=1)
                        processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@SaveVerbatim}\n\n'
                        pygments_macros[key_typeset].append(processed)
                    else:
                        processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                        r'\\begin{{pytx@Verbatim}}[\1]{{pytx@{0}}}'.format(key_typeset.replace('#', '@')),
                                        processed, count=1)
                        processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@Verbatim}\n\n'
                        fname = os.path.join(outputdir, key_typeset.replace('#', '_') + '.pygtex')
                        f = open(fname, 'w', encoding=encoding)
                        f.write(processed)
                        f.close()
                        pygments_files[key_typeset].append(fname)  
                else:
                    if console_content.count('\n') < fvextfile:
                        processed = ('\\begin{{pytx@SaveVerbatim}}{{pytx@{0}}}\n'.format(key_typeset.replace('#', '@')) + 
                                     console_content + '\\end{pytx@SaveVerbatim}\n\n')
                        macros.append(processed)
                    else:
                        processed = ('\\begin{pytx@Verbatim}\n' + console_content +
                                     '\\end{pytx@Verbatim}\n\n')
                        fname = os.path.join(outputdir, key_typeset.replace('#', '_') + '.tex')
                        f = open(fname, 'w', encoding=encoding)
                        f.write(processed)
                        f.close()
                        files.append(fname)
    
    if len(messages) == 1:
        messages = []
    
    # Return a dict of dicts of results
    return {'process': 'console',
            'key': key_run,
            'files': files,
            'macros': macros,
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'typeset_cache': typeset_cache,
            'dependencies': dependencies,
            'errors': errors,
            'warnings': warnings,
            'messages': messages} 




def main(python=None):
    # Create dictionaries for storing data.
    #
    # All data that must be saved for subsequent runs is stored in "data".
    # (We start off by saving the script version, a global var, in this dict.)
    # All data that is only created for this run is stored in "temp_data".
    # (We start off by creating keys for keeping track of errors and warnings.)
    # All old data will eventually be loaded into "old_data".
    # Since dicts are mutable data types, these dicts can be modified
    # from within functions, as long as the dicts are passed to the functions.
    # For simplicity, variables will often be created within functions to
    # refer to dictionary values.
    data = {'version': version, 'start_time': time.time()}
    temp_data = {'errors': 0, 'warnings': 0, 'python': python}
    old_data = dict()

    
    # Process command-line options.
    #
    # This gets the raw_jobname (actual job name), jobname (a sanitized job 
    # name, used for creating files named after the jobname), and any options.
    process_argv(data, temp_data)
    # If there aren't errors in argv, and the program is going to run 
    # (rather than just exit due to --version or --help command-line options), 
    # print PythonTeX version.  Flush to make the message go out immediately,  
    # so that the user knows PythonTeX has started.
    print('This is PythonTeX ' + version)
    sys.stdout.flush()
    # Once we have the encoding (from argv), we set stdout and stderr to use 
    # this encoding.  Later, we will parse the saved stderr of scripts 
    # executed via multiprocessing subprocesses, and print the parsed results 
    # to stdout.  The saved stderr uses the same encoding that was used 
    # for the files that created it (this is important for code containing 
    # unicode characters), so we also need stdout for the main PythonTeX
    # script to support this encoding.  Setting stderr encoding is primarily 
    # a matter of symmetry.  Ideally, pythontex*.py will be bug-free,
    # and stderr won't be needed!
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr.buffer, 'strict')


    # Load the code and process the settings it passes from the TeX side.
    #
    # This gets a list containing the code (the part of the code file 
    # containing the settings is removed) and the processed settings.
    load_code_get_settings(data, temp_data)
    # Now that the settings are loaded, check if outputdir exits.
    # If not, create it.
    if not os.path.isdir(data['settings']['outputdir']):
        os.mkdir(data['settings']['outputdir'])


    # Load/create old_data
    get_old_data(data, old_data, temp_data)
    
    
    # Hash the code.  Determine what needs to be executed.  Determine whether
    # Pygments should be used.  Update pygments_settings to account for 
    # Pygments commands and environments (as opposed to PythonTeX commands 
    # and environments).
    hash_all(data, temp_data, old_data, engine_dict)
    
    
    # Parse the code and write scripts for execution.
    parse_code_write_scripts(data, temp_data, engine_dict)
    
    
    # Execute the code and perform Pygments highlighting via multiprocessing.
    do_multiprocessing(data, temp_data, old_data, engine_dict)

        
    # Print exit message
    print('\n--------------------------------------------------')
    # If some rerun settings are used, there may be unresolved errors or 
    # warnings; if so, print a summary of those along with the current 
    # error and warning summary
    unresolved_errors = 0
    unresolved_warnings = 0
    if temp_data['rerun'] in ('errors', 'modified', 'never'):
        global_update = {}
        global_update.update(temp_data['code_update'])
        global_update.update(temp_data['cons_update'])
        for key in data['exit_status']:
            if not global_update[key]:
                unresolved_errors += data['exit_status'][key][0]
                unresolved_warnings += data['exit_status'][key][1]
    if unresolved_warnings != 0 or unresolved_errors != 0:
        print('PythonTeX:  {0}'.format(data['raw_jobname']))
        print('    - Old:      {0} error(s), {1} warnings(s)'.format(unresolved_errors, unresolved_warnings))
        print('    - Current:  {0} error(s), {1} warnings(s)'.format(temp_data['errors'], temp_data['warnings']))        
    else:
        print('PythonTeX:  {0} - {1} error(s), {2} warning(s)\n'.format(data['raw_jobname'], temp_data['errors'], temp_data['warnings']))

    # Exit with appropriate exit code based on user settings.
    if temp_data['error_exit_code'] and temp_data['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit()



# The "if" statement is needed for multiprocessing under Windows; see the 
# multiprocessing documentation.  It is also needed in this case when the 
# script is invoked via the wrapper.
if __name__ == '__main__':
    #// Python 2
    if sys.version_info.major != 2:
        sys.exit('This version of the PythonTeX script requires Python 2.')
    #\\ End Python 2
    #// Python 3
    #if sys.version_info.major != 3:
    #    sys.exit('This version of the PythonTeX script requires Python 3.')
    #\\ End Python 3
    main(python=sys.version_info.major)

########NEW FILE########
__FILENAME__ = pythontex3
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
This is the main PythonTeX script.  It should be launched via pythontex.py.

Two versions of this script are provided.  One, with name ending in "2", runs 
under Python 2.7.  The other, with name ending in "3", runs under Python 3.2+.

This script needs to be able to import pythontex_engines.py; in general it 
should be in the same directory.


Licensed under the BSD 3-Clause License:

Copyright (c) 2012-2014, Geoffrey M. Poore

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the <organization> nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


# Imports
#// Python 2
#from __future__ import absolute_import
#from __future__ import division
#from __future__ import print_function
#from __future__ import unicode_literals
#\\ End Python 2
import sys
import os
import argparse
import codecs
import time
from hashlib import sha1
from collections import defaultdict, OrderedDict, namedtuple
from re import match, sub, search
import subprocess
import multiprocessing
from pygments.styles import get_all_styles
from pythontex_engines import *
import textwrap
import platform

if sys.version_info[0] == 2:
    try:
        import cPickle as pickle
    except:
        import pickle
    from io import open
else:
    import pickle




# Script parameters
# Version
version = 'v0.13-beta'




class Pytxcode(object):
    def __init__(self, data, gobble):
        self.delims, self.code = data.split('#\n', 1)
        self.family, self.session, self.restart, self.instance, self.command, self.context, self.args_run, self.args_prettyprint, self.input_file, self.line = self.delims.split('#')
        self.instance_int = int(self.instance)        
        self.line_int = int(self.line)
        self.key_run = self.family + '#' + self.session + '#' + self.restart
        self.key_typeset = self.key_run + '#' + self.instance
        self.hashable_delims_run = self.key_typeset + '#' + self.command + '#' + self.context + '#' + self.args_run
        self.hashable_delims_typeset = self.key_typeset + '#' + self.command + '#' + self.context + '#' + self.args_run
        if len(self.command) > 1:
            self.is_inline = False
            # Environments start on the next line
            self.line_int += 1
            self.line = str(self.line_int)
        else:
            self.is_inline = True
        self.is_extfile = True if self.session.startswith('EXT:') else False
        if self.is_extfile:
            self.extfile = os.path.expanduser(os.path.normcase(self.session.replace('EXT:', '', 1)))
            self.key_typeset = self.key_typeset.replace('EXT:', '')
        self.is_cc = True if self.family.startswith('CC:') else False
        self.is_pyg = True if self.family.startswith('PYG') else False
        self.is_verb = True if self.restart.endswith('verb') else False
        if self.is_cc:
            self.instance += 'CC'
            self.cc_type, self.cc_pos = self.family.split(':')[1:]
        if self.is_verb or self.is_pyg or self.is_cc:
            self.is_cons = False
        else:
            self.is_cons = engine_dict[self.family].console
        self.is_code = False if self.is_verb or self.is_pyg or self.is_cc or self.is_cons else True
        if self.command in ('c', 'code') or (self.command == 'i' and not self.is_cons):
            self.is_typeset = False
        else:
            self.is_typeset = True
        
        if gobble == 'auto':
            self.code = textwrap.dedent(self.code)
            



def process_argv(data, temp_data):
    '''
    Process command line options using the argparse module.
    
    Most options are passed via the file of code, rather than via the command
    line.
    '''
    
    # Create a command line argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument('TEXNAME',
                        help='LaTeX file, with or without .tex extension')
    parser.add_argument('--version', action='version', 
                        version='PythonTeX {0}'.format(data['version']))                    
    parser.add_argument('--encoding', default='UTF-8', 
                        help='encoding for all text files (see codecs module for encodings)')
    parser.add_argument('--error-exit-code', default='true', 
                        choices=('true', 'false'),                          
                        help='return exit code of 1 if there are errors (not desirable with some TeX editors and workflows)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--runall', nargs='?', default='false',
                       const='true', choices=('true', 'false'),
                       help='run ALL code; equivalent to package option')
    group.add_argument('--rerun', default='errors', 
                       choices=('never', 'modified', 'errors', 'warnings', 'always'),
                       help='set conditions for rerunning code; equivalent to package option')
    parser.add_argument('--hashdependencies', nargs='?', default='false', 
                        const='true', choices=('true', 'false'),                          
                        help='hash dependencies (such as external data) to check for modification, rather than using mtime; equivalent to package option')
    parser.add_argument('-j', '--jobs', metavar='N', default=None, type=int,
                        help='Allow N jobs at once; defaults to cpu_count().')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
                        help='verbose output')
    parser.add_argument('--interpreter', default=None, help='set a custom interpreter; argument should be in the form "<interpreter>:<command>, <interp>:<cmd>, ..." where <interpreter> is "python", "ruby", etc., and <command> is the command for invoking the interpreter; argument may also be in the form of a Python dictionary')
    args = parser.parse_args()
    
    # Store the parsed argv in data and temp_data          
    data['encoding'] = args.encoding
    if args.error_exit_code == 'true':
        temp_data['error_exit_code'] = True
    else:
        temp_data['error_exit_code'] = False
    # runall can be mapped onto rerun, so both are stored under rerun
    if args.runall == 'true':
        temp_data['rerun'] = 'always'
    else:
        temp_data['rerun'] = args.rerun
    # hashdependencies need only be in temp_data, since changing it would
    # change hashes (hashes of mtime vs. file contents)
    if args.hashdependencies == 'true':
        temp_data['hashdependencies'] = True
    else:
        temp_data['hashdependencies'] = False
    if args.jobs is None:
        try:
            jobs = multiprocessing.cpu_count()
        except NotImplementedError:
            jobs = 1
        temp_data['jobs'] = jobs
    else:
        temp_data['jobs'] = args.jobs
    temp_data['verbose'] = args.verbose
    # Update interpreter_dict based on interpreter
    set_python_interpreter = False
    if args.interpreter is not None:
        interp_list = args.interpreter.lstrip('{').rstrip('}').split(',')
        for interp in interp_list:
            if interp:
                try:
                    k, v = interp.split(':')
                    k = k.strip(' \'"')
                    v = v.strip(' \'"')
                    interpreter_dict[k] = v
                    if k == 'python':
                        set_python_interpreter = True
                except:
                    print('Invalid --interpreter argument')
                    return sys.exit(2)
    # If the Python interpreter wasn't set, then try to set an appropriate
    # default value, based on how PythonTeX was launched (pythontex.py, 
    # pythontex2.py, or pythontex3.py).
    if not set_python_interpreter:
        if temp_data['python'] == 2:
            if platform.system() == 'Windows':
                try:
                    subprocess.check_output(['py', '--version'])
                    interpreter_dict['python'] = 'py -2'
                except:
                    msg = '''
                          * PythonTeX error:
                              You have launched PythonTeX using pythontex{0}.py
                              directly.  This should only be done when you want
                              to use Python version {0}, but have a different
                              version installed as the default.  (Otherwise, you
                              should start PythonTeX with pythontex.py.)  For 
                              this to work correctly, you should install Python
                              version 3.3+, which has a Windows wrapper (py) that
                              PythonTeX can use to run the correct version of 
                              Python.  If you do not want to install Python 3.3+,
                              you can also use the --interpreter command-line 
                              option to tell PythonTeX how to access the version
                              of Python you wish to use.
                          '''.format(temp_data['python'])
                    print(textwrap.dedent(msg[1:]))
                    return sys.exit(2)
            else:
                interpreter_dict['python'] = 'python2'
        elif temp_data['python'] == 3:
            if platform.system() == 'Windows':
                try:
                    subprocess.check_output(['py', '--version'])
                    interpreter_dict['python'] = 'py -3'
                except:
                    msg = '''
                          * PythonTeX error:
                              You have launched PythonTeX using pythontex{0}.py
                              directly.  This should only be done when you want
                              to use Python version {0}, but have a different
                              version installed as the default.  (Otherwise, you
                              should start PythonTeX with pythontex.py.)  For 
                              this to work correctly, you should install Python
                              version 3.3+, which has a Windows wrapper (py) that
                              PythonTeX can use to run the correct version of 
                              Python.  If you do not want to install Python 3.3+,
                              you can also use the --interpreter command-line 
                              option to tell PythonTeX how to access the version
                              of Python you wish to use.
                          '''.format(temp_data['python'])
                    print(textwrap.dedent(msg[1:]))
                    return sys.exit(2)
            else:
                interpreter_dict['python'] = 'python3'
    
    if args.TEXNAME is not None:
        # Determine if we a dealing with just a filename, or a name plus 
        # path.  If there's a path, we need to make the document directory 
        # the current working directory.
        dir, raw_jobname = os.path.split(args.TEXNAME)
        dir = os.path.expanduser(os.path.normcase(dir))
        if dir:
            os.chdir(dir)
            sys.path.append(dir)
        # If necessary, strip off an extension to find the raw jobname that
        # corresponds to the .pytxcode.
        if not os.path.exists(raw_jobname + '.pytxcode'):
            raw_jobname = raw_jobname.rsplit('.', 1)[0]
            if not os.path.exists(raw_jobname + '.pytxcode'):
                print('* PythonTeX error')
                print('    Code file ' + raw_jobname + '.pytxcode does not exist.')
                print('    Run LaTeX to create it.')
                return sys.exit(1)
        
        # We need a "sanitized" version of the jobname, with spaces and 
        # asterisks replaced with hyphens.  This is done to avoid TeX issues 
        # with spaces in file names, paralleling the approach taken in 
        # pythontex.sty.  From now on, we will use the sanitized version every 
        # time we create a file that contains the jobname string.  The raw 
        # version will only be used in reference to pre-existing files created 
        # on the TeX side, such as the .pytxcode file.
        jobname = raw_jobname.replace(' ', '-').replace('"', '').replace('*', '-')
        # Store the results in data
        data['raw_jobname'] = raw_jobname
        data['jobname'] = jobname
        
        # We need to check to make sure that the "sanitized" jobname doesn't 
        # lead to a collision with a file that already has that name, so that 
        # two files attempt to use the same PythonTeX folder.
        # 
        # If <jobname>.<ext> and <raw_jobname>.<ext> both exist, where <ext>
        # is a common LaTeX extension, we exit.  We operate under the 
        # assumption that there should be only a single file <jobname> in the 
        # document root directory that has a common LaTeX extension.  That 
        # could be false, but if so, the user probably has worse things to 
        # worry about than a potential PythonTeX output collision.
        # If <jobname>* and <raw_jobname>* both exist, we issue a warning but 
        # attempt to proceed.
        if jobname != raw_jobname:
            resolved = False
            for ext in ('.tex', '.ltx', '.dtx'):
                if os.path.isfile(raw_jobname + ext):
                    if os.path.isfile(jobname + ext):
                        print('* PythonTeX error')
                        print('    Directory naming collision between the following files:')
                        print('      ' + raw_jobname + ext)
                        print('      ' + jobname + ext)
                        return sys.exit(1)
                    else:
                        resolved = True
                        break
            if not resolved:
                ls = os.listdir('.')
                for file in ls:
                    if file.startswith(jobname):
                        print('* PythonTeX warning')
                        print('    Potential directory naming collision between the following names:')
                        print('      ' + raw_jobname)
                        print('      ' + jobname + '*')
                        print('    Attempting to proceed.')
                        temp_data['warnings'] += 1
                        break            
        
        


def load_code_get_settings(data, temp_data):
    '''
    Load the code file, preprocess the code, and extract the settings.
    '''
    # Bring in the .pytxcode file as a single string
    raw_jobname = data['raw_jobname']
    encoding = data['encoding']
    # The error checking here is a little redundant
    if os.path.isfile(raw_jobname + '.pytxcode'):
        f = open(raw_jobname + '.pytxcode', 'r', encoding=encoding)
        pytxcode = f.read()
        f.close()
    else:
        print('* PythonTeX error')
        print('    Code file ' + raw_jobname + '.pytxcode does not exist.')
        print('    Run LaTeX to create it.')
        return sys.exit(1)
    
    # Split code and settings
    try:
        pytxcode, pytxsettings = pytxcode.rsplit('=>PYTHONTEX:SETTINGS#', 1)
    except:
        print('The .pytxcode file appears to have an outdated format or be invalid')
        print('Run LaTeX to make sure the file is current')
        return sys.exit(1)
    
    
    # Prepare to process settings
    #
    # Create a dict for storing settings.
    settings = {}
    # Create a dict for storing Pygments settings.
    # Each dict entry will itself be a dict.
    pygments_settings = defaultdict(dict)
    
    # Create a dict of processing functions, and generic processing functions
    settings_func = dict()
    def set_kv_data(k, v):
        if v == 'true':
            settings[k] = True
        elif v == 'false':
            settings[k] = False
        else:
            settings[k] = v
    # Need a function for when assignment is only needed if not default value
    def set_kv_temp_data_if_not_default(k, v):
        if v != 'default':
            if v == 'true':
                temp_data[k] = True
            elif v == 'false':
                temp_data[k] = False
            else:
                temp_data[k] = v
    def set_kv_data_fvextfile(k, v):
        # Error checking on TeX side should be enough, but be careful anyway
        try:
            v = int(v)                    
        except ValueError:
            print('* PythonTeX error')
            print('    Unable to parse package option fvextfile.')
            return sys.exit(1)
        if v < 0:
            settings[k] = sys.maxsize
        elif v == 0:
            settings[k] = 1
            print('* PythonTeX warning')
            print('    Invalid value for package option fvextfile.')
            temp_data['warnings'] += 1
        else:
            settings[k] = v
    def set_kv_pygments(k, v):
        family, lexer_opts, options = v.replace(' ','').split('|')
        lexer = None
        lex_dict = {}
        opt_dict = {}
        if lexer_opts:
            for l in lexer_opts.split(','):
                if '=' in l:
                    k, v = l.split('=', 1)
                    if k == 'lexer':
                        lexer = l
                    else:
                        lex_dict[k] = v
                else:
                    lexer = l
        if options:
            for o in options.split(','):
                if '=' in o:
                    k, v = o.split('=', 1)
                    if v in ('true', 'True'):
                        v = True
                    elif v in ('false', 'False'):
                        v = False
                else:
                    k = option
                    v = True
                opt_dict[k] = v
        if family != ':GLOBAL':
            if 'lexer' in pygments_settings[':GLOBAL']:
                lexer = pygments_settings[':GLOBAL']['lexer']
            lex_dict.update(pygments_settings[':GLOBAL']['lexer_options'])
            opt_dict.update(pygments_settings[':GLOBAL']['formatter_options'])
            if 'style' not in opt_dict:
                opt_dict['style'] = 'default'
            opt_dict['commandprefix'] = 'PYG' + opt_dict['style']
        if lexer is not None:
            pygments_settings[family]['lexer'] = lexer
        pygments_settings[family]['lexer_options'] = lex_dict
        pygments_settings[family]['formatter_options'] = opt_dict
    settings_func['version'] = set_kv_data
    settings_func['outputdir'] = set_kv_data
    settings_func['workingdir'] = set_kv_data
    settings_func['gobble'] = set_kv_data
    settings_func['rerun'] = set_kv_temp_data_if_not_default
    settings_func['hashdependencies'] = set_kv_temp_data_if_not_default
    settings_func['makestderr'] = set_kv_data
    settings_func['stderrfilename'] = set_kv_data
    settings_func['keeptemps'] = set_kv_data
    settings_func['pyfuture'] = set_kv_data
    settings_func['pyconfuture'] = set_kv_data
    settings_func['pygments'] = set_kv_data
    settings_func['fvextfile'] = set_kv_data_fvextfile
    settings_func['pygglobal'] = set_kv_pygments
    settings_func['pygfamily'] = set_kv_pygments
    settings_func['pyconbanner'] = set_kv_data
    settings_func['pyconfilename'] = set_kv_data
    settings_func['depythontex'] = set_kv_data
    
    # Process settings
    for line in pytxsettings.split('\n'):
        if line:
            key, val = line.split('=', 1)
            try:
                settings_func[key](key, val)
            except KeyError:
                print('* PythonTeX warning')
                print('    Unknown option "' + key + '"')
                temp_data['warnings'] += 1

    # Check for compatility between the .pytxcode and the script
    if 'version' not in settings or settings['version'] != data['version']:
        print('* PythonTeX warning')
        print('    The version of the PythonTeX scripts does not match')
        print('    the last code saved by the document--run LaTeX to create')
        print('    an updated version.  Attempting to proceed.')
        sys.stdout.flush()
    
    # Store all results that haven't already been stored.
    data['settings'] = settings
    data['pygments_settings'] = pygments_settings
    
    # Create a tuple of vital quantities that invalidate old saved data
    # Don't need to include outputdir, because if that changes, no old output
    # fvextfile could be checked on a case-by-case basis, which would result
    # in faster output, but that would involve a good bit of additional 
    # logic, which probably isn't worth it for a feature that will rarely be
    # changed.
    data['vitals'] = (data['version'], data['encoding'], 
                      settings['gobble'], settings['fvextfile'])
    
    # Create tuples of vital quantities
    data['code_vitals'] = (settings['workingdir'], settings['keeptemps'],
                           settings['makestderr'], settings['stderrfilename'])
    data['cons_vitals'] = (settings['workingdir'])
    data['typeset_vitals'] = ()
    
    # Pass any customizations to types
    for k in engine_dict:
        engine_dict[k].customize(pyfuture=settings['pyfuture'],
                                 pyconfuture=settings['pyconfuture'],
                                 pyconbanner=settings['pyconbanner'],
                                 pyconfilename=settings['pyconfilename'])
    
    # Store code
    # Do this last, so that Pygments settings are available
    if pytxcode.startswith('=>PYTHONTEX#'):
        gobble = settings['gobble']
        temp_data['pytxcode'] = [Pytxcode(c, gobble) for c in pytxcode.split('=>PYTHONTEX#')[1:]]
    else:
        temp_data['pytxcode'] = []




def get_old_data(data, old_data, temp_data):
    '''
    Load data from the last run, if it exists, into the dict old_data.  
    Determine the path to the PythonTeX scripts, either by using a previously 
    found, saved path or via kpsewhich.
    
    The old data is used for determining when PythonTeX has been upgraded, 
    when any settings have changed, when code has changed (via hashes), and 
    what files may need to be cleaned up.  The location of the PythonTeX 
    scripts is needed so that they can be imported by the scripts created by 
    PythonTeX.  The location of the scripts is confirmed even if they were 
    previously located, to make sure that the path is still valid.  Finding 
    the scripts depends on having a TeX installation that includes the 
    Kpathsea library (TeX Live and MiKTeX, possibly others).
    
    All code that relies on old_data is written based on the assumption that
    if old_data exists and has the current PythonTeX version, then it 
    contains all needed information.  Thus, all code relying on old_data must
    check that it was loaded and that it has the current version.  If not, 
    code should adapt gracefully.
    '''

    # Create a string containing the name of the data file
    pythontex_data_file = os.path.join(data['settings']['outputdir'], 'pythontex_data.pkl')
    
    # Load the old data if it exists (read as binary pickle)
    if os.path.isfile(pythontex_data_file):
        f = open(pythontex_data_file, 'rb')
        old = pickle.load(f)
        f.close()
        # Check for compabilility
        if 'vitals' in old and data['vitals'] == old['vitals']:
            temp_data['loaded_old_data'] = True
            old_data.update(old)
        else:
            temp_data['loaded_old_data'] = False
            # Clean up all old files
            if 'files' in old:
                for key in old['files']:
                    for f in old['files'][key]:
                        f = os.path.expanduser(os.path.normcase(f))
                        if os.path.isfile(f):
                            os.remove(f)
            if 'pygments_files' in old:
                for key in old['pygments_files']:
                    for f in old['pygments_files'][key]:
                        f = os.path.expanduser(os.path.normcase(f))
                        if os.path.isfile(f):
                            os.remove(f)
    else:
        temp_data['loaded_old_data'] = False
    
    # Set the utilspath
    # Assume that if the utils aren't in the same location as 
    # `pythontex.py`, then they are somewhere else on `sys.path` that
    # will always be available (for example, installed as a Python module),
    # and thus specifying a path isn't necessary.
    if os.path.isfile(os.path.join(sys.path[0], 'pythontex_utils.py')):
        # Need the path with forward slashes, so escaping isn't necessary
        data['utilspath'] = sys.path[0].replace('\\', '/')
    else:
        data['utilspath'] = ''




def modified_dependencies(key, data, old_data, temp_data):
    hashdependencies = temp_data['hashdependencies']
    if key not in old_data['dependencies']:
        return False
    else:
        old_dep_hash_dict = old_data['dependencies'][key]
        workingdir = data['settings']['workingdir']
        for dep in old_dep_hash_dict.keys():
            # We need to know if the path is relative (based off the 
            # working directory) or absolute.  We can't use 
            # os.path.isabs() alone for determining the distinction, 
            # because we must take into account the possibility of an
            # initial ~ (tilde) standing for the home directory.
            dep_file = os.path.expanduser(os.path.normcase(dep))
            if not os.path.isabs(dep_file):
                dep_file = os.path.join(workingdir, dep_file)
            if not os.path.isfile(dep_file):
                print('* PythonTeX error')
                print('    Cannot find dependency "' + dep + '"')
                print('    It belongs to ' + key.replace('#', ':'))
                print('    Relative paths to dependencies must be specified from the working directory.')
                temp_data['errors'] += 1
                # A removed dependency should trigger an error, but it 
                # shouldn't cause code to execute.  Running the code 
                # again would just give more errors when it can't find 
                # the dependency.  (There won't be issues when a 
                # dependency is added or removed, because that would 
                # involve modifying code, which would trigger 
                # re-execution.)
            elif hashdependencies:
                # Read and hash the file in binary.  Opening in text mode 
                # would require an unnecessary decoding and encoding cycle.
                f = open(dep_file, 'rb')
                hasher = sha1()
                hash = hasher(f.read()).hexdigest()
                f.close()
                if hash != old_dep_hash_dict[dep][1]:
                    return True
            else:
                mtime = os.path.getmtime(dep_file)
                if mtime != old_dep_hash_dict[dep][0]:
                    return True
        return False

def should_rerun(hash, old_hash, old_exit_status, key, rerun, data, old_data, temp_data):
    # #### Need to clean up arg passing here
    if rerun == 'never':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data)):
            print('* PythonTeX warning')
            print('    Session ' + key.replace('#', ':') + ' has rerun=never')
            print('    But its code or dependencies have been modified')
            temp_data['warnings'] += 1
        return False
    elif rerun == 'modified':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data)):
            return True
        else:
            return False
    elif rerun == 'errors':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data) or
                old_exit_status[0] != 0):
            return True
        else:
            return False
    elif rerun == 'warnings':
        if (hash != old_hash or modified_dependencies(key, data, old_data, temp_data) or
                old_exit_status != (0, 0)):
            return True
        else:
            return False
    elif rerun == 'always':
        return True




def hash_all(data, temp_data, old_data, engine_dict):
    '''
    Hash the code to see what has changed and needs to be updated.
    
    Save the hashes in hashdict.  Create update_code, a list of bools 
    regarding whether code should be executed.  Create update_pygments, a 
    list of bools determining what needs updated Pygments highlighting.  
    Update pygments_settings to account for Pygments (as opposed to PythonTeX) 
    commands and environments.
    '''

    # Note that the PythonTeX information that accompanies code must be 
    # hashed in addition to the code itself; the code could stay the same, 
    # but its context or args could change, which might require that code be 
    # executed.  All of the PythonTeX information is hashed except for the 
    # input line number.  Context-dependent code is going too far if 
    # it depends on that.
    
    # Create variables to more easily access parts of data
    pytxcode = temp_data['pytxcode']
    encoding = data['encoding']
    loaded_old_data = temp_data['loaded_old_data']
    rerun = temp_data['rerun']
    pygments_settings = data['pygments_settings']
    
    # Calculate cumulative hashes for all code that is executed
    # Calculate individual hashes for all code that will be typeset
    code_hasher = defaultdict(sha1)
    cons_hasher = defaultdict(sha1)
    cc_hasher = defaultdict(sha1)
    typeset_hasher = defaultdict(sha1)
    for c in pytxcode:
        if c.is_code:
            code_hasher[c.key_run].update(c.hashable_delims_run.encode(encoding))
            code_encoded = c.code.encode(encoding)
            code_hasher[c.key_run].update(code_encoded)
            if c.is_typeset:
                typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
                typeset_hasher[c.key_typeset].update(code_encoded)
                typeset_hasher[c.key_typeset].update(c.args_prettyprint.encode(encoding))
        elif c.is_cons:
            cons_hasher[c.key_run].update(c.hashable_delims_run.encode(encoding))
            code_encoded = c.code.encode(encoding)
            cons_hasher[c.key_run].update(code_encoded)
            if c.is_typeset:
                typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
                typeset_hasher[c.key_typeset].update(code_encoded)
                typeset_hasher[c.key_typeset].update(c.args_prettyprint.encode(encoding))
        elif c.is_cc:
            cc_hasher[c.cc_type].update(c.hashable_delims_run.encode(encoding))
            cc_hasher[c.cc_type].update(c.code.encode(encoding))
        elif c.is_typeset:
            typeset_hasher[c.key_typeset].update(c.hashable_delims_typeset.encode(encoding))
            typeset_hasher[c.key_typeset].update(c.code.encode(encoding))
            typeset_hasher[c.key_typeset].update(c.args_prettyprint.encode(encoding))
        

    # Store hashes
    code_hash_dict = {}
    for key in code_hasher:
        family = key.split('#', 1)[0]
        code_hash_dict[key] = (code_hasher[key].hexdigest(), 
                               cc_hasher[family].hexdigest(),
                               engine_dict[family].get_hash())
    data['code_hash_dict'] = code_hash_dict
    
    cons_hash_dict = {}
    for key in cons_hasher:
        family = key.split('#', 1)[0]
        cons_hash_dict[key] = (cons_hasher[key].hexdigest(), 
                               cc_hasher[family].hexdigest(),
                               engine_dict[family].get_hash())
    data['cons_hash_dict'] = cons_hash_dict
    
    typeset_hash_dict = {}
    for key in typeset_hasher:
        typeset_hash_dict[key] = typeset_hasher[key].hexdigest()
    data['typeset_hash_dict'] = typeset_hash_dict
    
    
    # See what needs to be updated.
    # In the process, copy over macros and files that may be reused.
    code_update = {}
    cons_update = {}
    pygments_update = {}
    macros = defaultdict(list)
    files = defaultdict(list)
    pygments_macros = {}
    pygments_files = {}
    typeset_cache = {}
    dependencies = defaultdict(dict)
    exit_status = {}
    pygments_settings_changed = {}
    if loaded_old_data:
        old_macros = old_data['macros']
        old_files = old_data['files']
        old_pygments_macros = old_data['pygments_macros']
        old_pygments_files = old_data['pygments_files']
        old_typeset_cache = old_data['typeset_cache']
        old_dependencies = old_data['dependencies']
        old_exit_status = old_data['exit_status']
        old_code_hash_dict = old_data['code_hash_dict']
        old_cons_hash_dict = old_data['cons_hash_dict']
        old_typeset_hash_dict = old_data['typeset_hash_dict']
        old_pygments_settings = old_data['pygments_settings']
        for s in pygments_settings:
            if (s in old_pygments_settings and 
                    pygments_settings[s] == old_pygments_settings[s]):
                pygments_settings_changed[s] = False
            else:
                pygments_settings_changed[s] = True

    # If old data was loaded (and thus is compatible) determine what has 
    # changed so that only 
    # modified code may be executed.  Otherwise, execute everything.
    # We don't have to worry about checking for changes in pyfuture, because
    # custom code and default code are hashed.  The treatment of keeptemps
    # could be made more efficient (if changed to 'none', just delete old temp
    # files rather than running everything again), but given that it is 
    # intended as a debugging aid, that probable isn't worth it.
    # We don't have to worry about hashdependencies changing, because if it 
    # does the hashes won't match (file contents vs. mtime) and thus code will
    # be re-executed.
    if loaded_old_data and data['code_vitals'] == old_data['code_vitals']:
        # Compare the hash values, and set which code needs to be run
        for key in code_hash_dict:
            if (key in old_code_hash_dict and 
                    not should_rerun(code_hash_dict[key], old_code_hash_dict[key], old_exit_status[key], key, rerun, data, old_data, temp_data)):
                code_update[key] = False
                macros[key] = old_macros[key]
                files[key] = old_files[key]
                dependencies[key] = old_dependencies[key]
                exit_status[key] = old_exit_status[key]
            else:
                code_update[key] = True        
    else:        
        for key in code_hash_dict:
            code_update[key] = True
    
    if loaded_old_data and data['cons_vitals'] == old_data['cons_vitals']:
        # Compare the hash values, and set which code needs to be run
        for key in cons_hash_dict:
            if (key in old_cons_hash_dict and 
                    not should_rerun(cons_hash_dict[key], old_cons_hash_dict[key], old_exit_status[key], key, rerun, data, old_data, temp_data)):
                cons_update[key] = False
                macros[key] = old_macros[key]
                files[key] = old_files[key]
                typeset_cache[key] = old_typeset_cache[key]
                dependencies[key] = old_dependencies[key]
                exit_status[key] = old_exit_status[key]
            else:
                cons_update[key] = True        
    else:        
        for key in cons_hash_dict:
            cons_update[key] = True
    
    if loaded_old_data and data['typeset_vitals'] == old_data['typeset_vitals']:
        for key in typeset_hash_dict:
            family = key.split('#', 1)[0]
            if family in pygments_settings:
                if (not pygments_settings_changed[family] and
                        key in old_typeset_hash_dict and 
                        typeset_hash_dict[key] == old_typeset_hash_dict[key]):
                    pygments_update[key] = False
                    if key in old_pygments_macros:
                        pygments_macros[key] = old_pygments_macros[key]
                    if key in old_pygments_files:
                        pygments_files[key] = old_pygments_files[key]
                else:
                    pygments_update[key] = True
            else:
                pygments_update[key] = False
        # Make sure Pygments styles are up-to-date
        pygments_style_list = list(get_all_styles())
        if pygments_style_list != old_data['pygments_style_list']:
            pygments_style_defs = {}
            # Lazy import
            from pygments.formatters import LatexFormatter
            for s in pygments_style_list:
                formatter = LatexFormatter(style=s, commandprefix='PYG'+s)
                pygments_style_defs[s] = formatter.get_style_defs()
        else:
            pygments_style_defs = old_data['pygments_style_defs']
    else:
        for key in typeset_hash_dict:
            family = key.split('#', 1)[0]
            if family in pygments_settings:
                pygments_update[key] = True
            else:
                pygments_update[key] = False
        # Create Pygments styles
        pygments_style_list = list(get_all_styles())
        pygments_style_defs = {}
        # Lazy import
        from pygments.formatters import LatexFormatter
        for s in pygments_style_list:
            formatter = LatexFormatter(style=s, commandprefix='PYG'+s)
            pygments_style_defs[s] = formatter.get_style_defs()
    
    # Save to data
    temp_data['code_update'] = code_update
    temp_data['cons_update'] = cons_update
    temp_data['pygments_update'] = pygments_update
    data['macros'] = macros
    data['files'] = files
    data['pygments_macros'] = pygments_macros
    data['pygments_style_list'] = pygments_style_list
    data['pygments_style_defs'] = pygments_style_defs
    data['pygments_files'] = pygments_files
    data['typeset_cache'] = typeset_cache
    data['dependencies'] = dependencies
    data['exit_status'] = exit_status
    
    
    # Clean up for code that will be run again, and for code that no longer 
    # exists.
    if loaded_old_data:
        # Take care of code files
        for key in code_hash_dict:
            if code_update[key] and key in old_files:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_code_hash_dict:
            if key not in code_hash_dict:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        # Take care of old console files
        for key in cons_hash_dict:
            if cons_update[key] and key in old_files:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_cons_hash_dict:
            if key not in cons_hash_dict:
                for f in old_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        # Take care of old Pygments files
        # The approach here is a little different since there isn't a 
        # Pygments-specific hash dict, but there is a Pygments-specific 
        # dict of lists of files.
        for key in pygments_update:
            if pygments_update[key] and key in old_pygments_files:
                for f in old_pygments_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)
        for key in old_pygments_files:
            if key not in pygments_update:
                for f in old_pygments_files[key]:
                    f = os.path.expanduser(os.path.normcase(f))
                    if os.path.isfile(f):
                        os.remove(f)





def parse_code_write_scripts(data, temp_data, engine_dict):
    '''
    Parse the code file into separate scripts, and write them to file.
    '''
    code_dict = defaultdict(list)
    cc_dict_begin = defaultdict(list)
    cc_dict_end = defaultdict(list)
    cons_dict = defaultdict(list)
    pygments_list = []
    # Create variables to ease data access
    encoding = data['encoding']
    utilspath = data['utilspath']
    outputdir = data['settings']['outputdir']
    workingdir = data['settings']['workingdir']
    pytxcode = temp_data['pytxcode']
    code_update = temp_data['code_update']
    cons_update = temp_data['cons_update']
    pygments_update = temp_data['pygments_update']
    files = data['files']
    # We need to keep track of the last instance for each session, so 
    # that duplicates can be eliminated.  Some LaTeX environments process 
    # their content multiple times and thus will create duplicates.  We 
    # need to initialize everything at -1, since instances begin at zero.
    def negative_one():
        return -1
    last_instance = defaultdict(negative_one)
    for c in pytxcode:
        if c.instance_int > last_instance[c.key_run]:
            last_instance[c.key_run] = c.instance_int
            if c.is_code:
                if code_update[c.key_run]:
                    code_dict[c.key_run].append(c)
                if c.is_typeset and pygments_update[c.key_typeset]:
                    pygments_list.append(c)
            elif c.is_cons:
                # Only append to Pygments if not run, since Pygments is 
                # automatically taken care of during run for console content
                if cons_update[c.key_run]:
                    cons_dict[c.key_run].append(c)
                elif c.is_typeset and pygments_update[c.key_typeset]:
                    pygments_list.append(c)
            elif (c.is_pyg or c.is_verb) and pygments_update[c.key_typeset]:
                pygments_list.append(c)
            elif c.is_cc:
                if c.cc_pos == 'begin':
                    cc_dict_begin[c.cc_type].append(c)
                else:
                    cc_dict_end[c.cc_type].append(c)
    
    # Save
    temp_data['code_dict'] = code_dict
    temp_data['cc_dict_begin'] = cc_dict_begin
    temp_data['cc_dict_end'] = cc_dict_end
    temp_data['cons_dict'] = cons_dict
    temp_data['pygments_list'] = pygments_list

    # Save the code sessions that need to be updated
    # Keep track of the files that are created
    # Also accumulate error indices for handling stderr
    code_index_dict = {}
    for key in code_dict:
        family, session, restart = key.split('#')
        fname = os.path.join(outputdir, family + '_' + session + '_' + restart + '.' + engine_dict[family].extension)
        files[key].append(fname)
        sessionfile = open(fname, 'w', encoding=encoding)
        script, code_index = engine_dict[family].get_script(encoding,
                                                              utilspath,
                                                              workingdir,
                                                              cc_dict_begin[family],
                                                              code_dict[key],
                                                              cc_dict_end[family])
        for lines in script:
            sessionfile.write(lines)
        sessionfile.close()
        code_index_dict[key] = code_index
    temp_data['code_index_dict'] = code_index_dict




def do_multiprocessing(data, temp_data, old_data, engine_dict):
    jobname = data['jobname']
    encoding = data['encoding']
    outputdir = data['settings']['outputdir']
    workingdir = data['settings']['workingdir']
    keeptemps = data['settings']['keeptemps']
    fvextfile = data['settings']['fvextfile']
    pygments_settings = data['pygments_settings']
    jobs = temp_data['jobs']
    verbose = temp_data['verbose']
    
    code_dict = temp_data['code_dict']
    cons_dict = temp_data['cons_dict']
    cc_dict_begin = temp_data['cc_dict_begin']
    cc_dict_end = temp_data['cc_dict_end']
    pygments_list = temp_data['pygments_list']
    pygments_style_defs = data['pygments_style_defs']

    files = data['files']
    macros = data['macros']
    pygments_files = data['pygments_files']
    pygments_macros = data['pygments_macros']
    typeset_cache = data['typeset_cache']
    
    errors = temp_data['errors']
    warnings = temp_data['warnings']
    
    makestderr = data['settings']['makestderr']
    stderrfilename = data['settings']['stderrfilename']
    code_index_dict = temp_data['code_index_dict']
    
    hashdependencies = temp_data['hashdependencies']
    dependencies = data['dependencies']
    exit_status = data['exit_status']
    start_time = data['start_time']
    
    
    # Create a pool for multiprocessing.  Set the maximum number of 
    # concurrent processes to a user-specified value for jobs.  If the user
    # has not specified a value, then it will be None, and 
    # multiprocessing.Pool() will use cpu_count().
    pool = multiprocessing.Pool(jobs)
    tasks = []
    
    # If verbose, print a list of processes
    if verbose:
        print('\n* PythonTeX will run the following processes')
        print('  (maximum concurrent processes = {0})'.format(jobs))
    
    # Add code processes.  Note that everything placed in the codedict 
    # needs to be executed, based on previous testing, except for custom code.
    for key in code_dict:
        family = key.split('#')[0]
        # Uncomment the following for debugging, and comment out what follows
        '''run_code(encoding, outputdir, workingdir, code_dict[key],
                                                 engine_dict[family].language,
                                                 engine_dict[family].command,
                                                 engine_dict[family].created,
                                                 engine_dict[family].extension,
                                                 makestderr, stderrfilename,
                                                 code_index_dict[key],
                                                 engine_dict[family].errors,
                                                 engine_dict[family].warnings,
                                                 engine_dict[family].linenumbers,
                                                 engine_dict[family].lookbehind,
                                                 keeptemps, hashdependencies)'''
        tasks.append(pool.apply_async(run_code, [encoding, outputdir, 
                                                 workingdir, code_dict[key],
                                                 engine_dict[family].language,
                                                 engine_dict[family].command,
                                                 engine_dict[family].created,
                                                 engine_dict[family].extension,
                                                 makestderr, stderrfilename,
                                                 code_index_dict[key],
                                                 engine_dict[family].errors,
                                                 engine_dict[family].warnings,
                                                 engine_dict[family].linenumbers,
                                                 engine_dict[family].lookbehind,
                                                 keeptemps, hashdependencies]))
        if verbose:
            print('    - Code process ' + key.replace('#', ':'))
    
    # Add console processes
    for key in cons_dict:
        family = key.split('#')[0]
        if engine_dict[family].language.startswith('python'):
            if family in pygments_settings:
                # Uncomment the following for debugging
                '''python_console(jobname, encoding, outputdir, workingdir, 
                               fvextfile, pygments_settings[family],
                               cc_dict_begin[family], cons_dict[key],
                               cc_dict_end[family], engine_dict[family].startup,
                               engine_dict[family].banner, 
                               engine_dict[family].filename)'''
                tasks.append(pool.apply_async(python_console, [jobname, encoding,
                                                               outputdir, workingdir,
                                                               fvextfile,
                                                               pygments_settings[family],
                                                               cc_dict_begin[family],
                                                               cons_dict[key],
                                                               cc_dict_end[family],
                                                               engine_dict[family].startup,
                                                               engine_dict[family].banner,
                                                               engine_dict[family].filename]))
            else:
                tasks.append(pool.apply_async(python_console, [jobname, encoding,
                                                               outputdir, workingdir,
                                                               fvextfile,
                                                               None,
                                                               cc_dict_begin[family],
                                                               cons_dict[key],
                                                               cc_dict_end[family],
                                                               engine_dict[family].startup,
                                                               engine_dict[family].banner,
                                                               engine_dict[family].filename]))  
        else:
            print('* PythonTeX error')
            print('    Currently, non-Python consoles are not supported')
            errors += 1
        if verbose:
            print('    - Console process ' + key.replace('#', ':'))
    
    # Add a Pygments process
    if pygments_list:
        tasks.append(pool.apply_async(do_pygments, [encoding, outputdir, 
                                                    fvextfile,
                                                    pygments_list,
                                                    pygments_settings,
                                                    typeset_cache]))
        if verbose:
            print('    - Pygments process')
    
    # Execute the processes
    pool.close()
    pool.join()
    
    # Get the outputs of processes
    # Get the files and macros created.  Get the number of errors and warnings
    # produced.  Get any messages returned.  Get the exit_status, which is a 
    # dictionary of code that failed and thus must be run again (its hash is
    # set to a null string).  Keep track of whether there were any new files,
    # so that the last time of file creation in .pytxmcr can be updated.
    new_files = False
    messages = []
    for task in tasks:
        result = task.get()
        if result['process'] == 'code':
            key = result['key']
            files[key].extend(result['files'])
            if result['files']:
                new_files = True
            macros[key].extend(result['macros'])
            dependencies[key] = result['dependencies']
            errors += result['errors']
            warnings += result['warnings']
            exit_status[key] = (result['errors'], result['warnings'])
            messages.extend(result['messages'])            
        elif result['process'] == 'console':
            key = result['key']
            files[key].extend(result['files'])
            if result['files']:
                new_files = True
            macros[key].extend(result['macros'])
            pygments_files.update(result['pygments_files'])
            pygments_macros.update(result['pygments_macros'])
            dependencies[key] = result['dependencies']
            typeset_cache[key] = result['typeset_cache']
            errors += result['errors']
            warnings += result['warnings']
            exit_status[key] = (result['errors'], result['warnings'])
            messages.extend(result['messages'])
        elif result['process'] == 'pygments':
            pygments_files.update(result['pygments_files'])
            for k in result['pygments_files']:
                if result['pygments_files'][k]:
                    new_files = True
                    break
            pygments_macros.update(result['pygments_macros'])
            errors += result['errors']
            warnings += result['warnings']
            messages.extend(result['messages'])        
    
    # Do a quick check to see if any dependencies were modified since the
    # beginning of the run.  If so, reset them so they will run next time and
    # issue a warning
    unresolved_dependencies = False
    unresolved_sessions = []
    for key in dependencies:
        for dep, val in dependencies[key].items():
            if val[0] > start_time:
                unresolved_dependencies = True
                dependencies[key][dep] = (None, None)
                unresolved_sessions.append(key.replace('#', ':'))
    if unresolved_dependencies:
        print('* PythonTeX warning')
        print('    The following have dependencies that have been modified')
        print('    Run PythonTeX again to resolve dependencies')
        for s in set(unresolved_sessions):
            print('    - ' + s)
        warnings += 1
    
    
    # Save all content (only needs to be done if code was indeed run).
    # Save a commented-out time corresponding to the last time PythonTeX ran
    # and created files, so that tools like latexmk can easily detect when 
    # another run is needed.
    if tasks:
        if new_files or not temp_data['loaded_old_data']:
            last_new_file_time = start_time
        else:
            last_new_file_time = old_data['last_new_file_time']
        data['last_new_file_time'] = last_new_file_time
        
        macro_file = open(os.path.join(outputdir, jobname + '.pytxmcr'), 'w', encoding=encoding)
        macro_file.write('%Last time of file creation:  ' + str(last_new_file_time) + '\n\n')
        for key in macros:
            macro_file.write(''.join(macros[key]))
        macro_file.close()
        
        pygments_macro_file = open(os.path.join(outputdir, jobname + '.pytxpyg'), 'w', encoding=encoding)
        # Only save Pygments styles that are used
        style_set = set([pygments_settings[k]['formatter_options']['style'] for k in pygments_settings if k != ':GLOBAL'])
        for key in pygments_style_defs:
            if key in style_set:
                pygments_macro_file.write(''.join(pygments_style_defs[key]))
        for key in pygments_macros:
            pygments_macro_file.write(''.join(pygments_macros[key]))
        pygments_macro_file.close()
        
        pythontex_data_file = os.path.join(outputdir, 'pythontex_data.pkl')
        f = open(pythontex_data_file, 'wb')
        pickle.dump(data, f, -1)
        f.close()
    
    # Print any errors and warnings.
    if messages:
        print('\n'.join(messages))
    sys.stdout.flush()
    # Store errors and warnings back into temp_data
    # This is needed because they are ints and thus immutable
    temp_data['errors'] = errors
    temp_data['warnings'] = warnings




def run_code(encoding, outputdir, workingdir, code_list, language, command, 
             command_created, extension, makestderr, stderrfilename, 
             code_index, errorsig, warningsig, linesig, stderrlookbehind, 
             keeptemps, hashdependencies):
    '''
    Function for multiprocessing code files
    '''
    import shlex
    
    # Create what's needed for storing results
    family = code_list[0].family
    session = code_list[0].session
    key_run = code_list[0].key_run
    files = []
    macros = []
    dependencies = {}
    errors = 0
    warnings = 0
    unknowns = 0
    messages = []
    
    # Create message lists only for stderr, one for undelimited stderr and 
    # one for delimited, so it's easy to keep track of if there is any 
    # stderr.  These are added onto messages at the end.
    err_messages_ud = []
    err_messages_d = []
    
    # We need to let the user know we are switching code files
    # We check at the end to see if there were indeed any errors and warnings
    # and if not, clear messages.
    messages.append('\n----  Messages for ' + key_run.replace('#', ':') + '  ----')
    
    # Open files for stdout and stderr, run the code, then close the files
    basename = key_run.replace('#', '_')
    out_file_name = os.path.join(outputdir, basename + '.out')
    err_file_name = os.path.join(outputdir, basename + '.err')
    out_file = open(out_file_name, 'w', encoding=encoding)
    err_file = open(err_file_name, 'w', encoding=encoding)
    # Note that command is a string, which must be converted to list
    # Must double-escape any backslashes so that they survive `shlex.split()`
    script = os.path.expanduser(os.path.normcase(os.path.join(outputdir, basename)))
    if os.path.isabs(script):
        script_full = script
    else:
        script_full = os.path.expanduser(os.path.normcase(os.path.join(os.getcwd(), outputdir, basename)))
    # `shlex.split()` only works with Unicode after 2.7.2
    if (sys.version_info.major == 2 and sys.version_info.micro < 3):
        exec_cmd = shlex.split(bytes(command.format(file=script.replace('\\', '\\\\'), File=script_full.replace('\\', '\\\\'))))
        exec_cmd = [unicode(elem) for elem in exec_cmd]
    else:
        exec_cmd = shlex.split(command.format(file=script.replace('\\', '\\\\'), File=script_full.replace('\\', '\\\\')))
    # Add any created files due to the command
    # This needs to be done before attempts to execute, to prevent orphans
    for f in command_created:
        files.append(f.format(file=script))
    try:
        proc = subprocess.Popen(exec_cmd, stdout=out_file, stderr=err_file)
    except WindowsError as e:
        if e.errno == 2:
            # Batch files won't be found when called without extension. They
            # would be found if `shell=True`, but then getting the right
            # exit code is tricky.  So we perform some `cmd` trickery that
            # is essentially equivalent to `shell=True`, but gives correct 
            # exit codes.  Note that `subprocess.Popen()` works with strings
            # under Windows; a list is not required.
            exec_cmd_string = ' '.join(exec_cmd)
            exec_cmd_string = 'cmd /C "@echo off & call {0} & if errorlevel 1 exit 1"'.format(exec_cmd_string)
            proc = subprocess.Popen(exec_cmd_string, stdout=out_file, stderr=err_file)
        else:
            raise
        
    proc.wait()        
    out_file.close()
    err_file.close()
    
    # Process saved stdout into file(s) that are included in the TeX document.
    #
    # Go through the saved output line by line, and save any printed content 
    # to its own file, named based on instance.
    #
    # The very end of the stdout lists dependencies, if any, so we start by
    # removing and processing those.
    if not os.path.isfile(out_file_name):
        messages.append('* PythonTeX error')
        messages.append('    Missing output file for ' + key_run.replace('#', ':'))
        errors += 1
    else:
        f = open(out_file_name, 'r', encoding=encoding)
        out = f.read()
        f.close()
        try:
            out, created = out.rsplit('=>PYTHONTEX:CREATED#\n', 1)
            out, deps = out.rsplit('=>PYTHONTEX:DEPENDENCIES#\n', 1)
            valid_stdout = True
        except:
            valid_stdout = False
            if proc.returncode == 0:
                raise ValueError('Missing "created" and/or "dependencies" delims in stdout; invalid template?')
                    
        if valid_stdout:
            # Add created files to created list
            for c in created.splitlines():
                if os.path.isabs(os.path.expanduser(os.path.normcase(c))):
                    files.append(c)
                else:
                    files.append(os.path.join(workingdir, c))
            
            # Create a set of dependencies, to eliminate duplicates in the event
            # that there are any.  This is mainly useful when dependencies are
            # automatically determined (for example, through redefining open()), 
            # may be specified multiple times as a result, and are hashed (and 
            # of a large enough size that hashing time is non-negligible).
            deps = set([dep for dep in deps.splitlines()])
            # Process dependencies; get mtimes and (if specified) hashes
            for dep in deps:
                dep_file = os.path.expanduser(os.path.normcase(dep))
                if not os.path.isabs(dep_file):
                    dep_file = os.path.join(workingdir, dep_file)
                if not os.path.isfile(dep_file):
                    # If we can't find the file, we return a null hash and issue 
                    # an error.  We don't need to change the exit status.  If the 
                    # code does depend on the file, there will be a separate 
                    # error when the code attempts to use the file.  If the code 
                    # doesn't really depend on the file, then the error will be 
                    # raised again anyway the next time PythonTeX runs when the 
                    # dependency is listed but not found.
                    dependencies[dep] = (None, None)
                    messages.append('* PythonTeX error')
                    messages.append('    Cannot find dependency "' + dep + '"')
                    messages.append('    It belongs to ' + key_run.replace('#', ':'))
                    messages.append('    Relative paths to dependencies must be specified from the working directory.')
                    errors += 1                
                elif hashdependencies:
                    # Read and hash the file in binary.  Opening in text mode 
                    # would require an unnecessary decoding and encoding cycle.
                    hasher = sha1()
                    f = open(dep_file, 'rb')
                    hasher.update(f.read())
                    f.close()
                    dependencies[dep] = (os.path.getmtime(dep_file), hasher.hexdigest())
                else:
                    dependencies[dep] = (os.path.getmtime(dep_file), '')
            
            for block in out.split('=>PYTHONTEX:STDOUT#')[1:]:
                if block:
                    delims, content = block.split('#\n', 1)
                    if content:
                        instance, command = delims.split('#')
                        if instance.endswith('CC'):
                            messages.append('* PythonTeX warning')
                            messages.append('    Custom code for "' + family + '" attempted to print or write to stdout')
                            messages.append('    This is not supported; use a normal code command or environment')
                            messages.append('    The following content was written:')
                            messages.append('')
                            messages.extend(['    ' + l for l in content.splitlines()])
                            warnings += 1
                        elif command == 'i':
                            content = r'\pytx@SVMCR{pytx@MCR@' + key_run.replace('#', '@') + '@' + instance + '}\n' + content.rstrip('\n') + '\\endpytx@SVMCR\n\n'
                            macros.append(content)
                        else:
                            fname = os.path.join(outputdir, basename + '_' + instance + '.stdout')
                            f = open(fname, 'w', encoding=encoding)
                            f.write(content)
                            f.close()
                            files.append(fname)

    # Process stderr
    if not os.path.isfile(err_file_name):
        messages.append('* PythonTeX error')
        messages.append('    Missing stderr file for ' + key_run.replace('#', ':'))
        errors += 1
    else:
        # Open error and code files.
        f = open(err_file_name, encoding=encoding)
        err = f.readlines()
        f.close()
        # Divide stderr into an undelimited and a delimited portion
        found = False
        for n, line in enumerate(err):
            if line.startswith('=>PYTHONTEX:STDERR#'):
                found = True
                err_ud = err[:n]
                err_d = err[n:]
                break
        if not found:
            err_ud = err
            err_d = []
        # Create a dict for storing any stderr content that will be saved
        err_dict = defaultdict(list)
        # Create the full basename that will be replaced in stderr
        # We need two versions, one with the correct slashes for the OS,
        # and one with the opposite slashes.  This is needed when a language
        # doesn't obey the OS's slash convention in paths given in stderr.  
        # For example, Windows uses backslashes, but Ruby under Windows uses 
        # forward in paths given in stderr.
        fullbasename_correct = os.path.join(outputdir, basename)
        if '\\' in fullbasename_correct:
            fullbasename_reslashed = fullbasename_correct.replace('\\', '/')
        else:
            fullbasename_reslashed = fullbasename_correct.replace('/', '\\')
        
        if err_ud:
            it = iter(code_index.items())
            index_now = next(it)
            index_next = index_now
            start_errgobble = None
            for n, line in enumerate(err_ud):
                if basename in line:
                    # Get the gobbleation.  This is used to determine if 
                    # other lines containing the basename are a continuation,
                    # or separate messages.
                    errgobble = match('(\s*)', line).groups()[0]
                    if start_errgobble is None:
                        start_errgobble = errgobble
                    # Only issue a message and track down the line numer if
                    # this is indeed the start of a new message, rather than
                    # a continuation of an old message that happens to 
                    # contain the basename
                    if errgobble == start_errgobble:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            while index_next[1].lines_total < errlinenum:
                                try:
                                    index_now, index_next = index_next, next(it)
                                except:
                                    break
                            if errlinenum > index_now[1].lines_total + index_now[1].lines_input:
                                doclinenum = str(index_now[1].line_int + index_now[1].lines_input)
                            else:
                                doclinenum = str(index_now[1].line_int + errlinenum - index_now[1].lines_total - 1)
                            input_file = index_now[1].input_file
                        else:
                            doclinenum = '??'
                            input_file = '??'
                        
                        # Try to determine if we are dealing with an error or a 
                        # warning.
                        found = False
                        index = n
                        if stderrlookbehind:
                            while index >= 0:
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                past_line = err_ud[index]
                                if (index < n and basename in past_line):
                                    break
                                for pattern in warningsig:
                                    if pattern in past_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in past_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index -= 1
                        else:
                            while index < len(err_ud):
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                future_line = err_ud[index]
                                if (index > n and basename in future_line and 
                                        future_line.startswith(start_errgobble)):
                                    break
                                for pattern in warningsig:
                                    if pattern in future_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in future_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index += 1
                        # If an error or warning wasn't positively identified,
                        # increment unknowns.
                        if not found:
                            unknowns += 1
                            alert_type = 'unknown'
                        if input_file:
                            err_messages_ud.append('* PythonTeX stderr - {0} on line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                        else:
                            err_messages_ud.append('* PythonTeX stderr - {0} on line {1}:'.format(alert_type, doclinenum))
                    err_messages_ud.append('  ' + line.replace(outputdir, '<outputdir>').rstrip('\n'))
                else:
                    err_messages_ud.append('  ' + line.rstrip('\n'))
            
            # Create .stderr
            if makestderr and err_messages_ud:
                process = False
                it = iter(code_index.items())
                index_now = next(it)
                index_next = index_now
                it_last = it
                index_now_last = index_now
                index_next_last = index_next
                err_key_last_int = -1
                for n, line in enumerate(err_ud):
                    if basename in line:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            if index_next[1].lines_total >= errlinenum:
                                it = it_last
                                index_now = index_now_last
                                index_next = index_next_last
                            else:
                                it_last = it
                                index_now_last = index_now
                                index_next_last = index_next
                            while index_next[1].lines_total < errlinenum:
                                try:
                                    index_now, index_next = index_next, next(it)
                                except:
                                    index_now = index_next
                                    break
                            if index_now[0].endswith('CC'):
                                process = False
                            else:
                                process = True
                                if len(index_now[1].command) > 1:
                                    if errlinenum > index_now[1].lines_total + index_now[1].lines_input:
                                        codelinenum = str(index_now[1].lines_user + index_now[1].lines_input + 1)
                                    else:
                                        codelinenum = str(index_now[1].lines_user + errlinenum - index_now[1].lines_total - index_now[1].inline_count)
                                else:
                                    codelinenum = '1'
                        else:
                            codelinenum = '??'
                            messages.append('* PythonTeX error')
                            messages.append('    Line number ' + str(errlinenum) + ' could not be synced with the document')
                            messages.append('    Content from stderr is not delimited, and cannot be resolved')
                            errors += 1
                            process = False
                        
                        if process:
                            if int(index_now[0]) > err_key_last_int:
                                err_key = basename + '_' + index_now[0]
                                err_key_last_int = int(index_now[0])
                            line = line.replace(str(errlinenum), str(codelinenum), 1)
                            if fullbasename_correct in line:
                                fullbasename = fullbasename_correct
                            else:
                                fullbasename = fullbasename_reslashed
                            if stderrfilename == 'full':
                                line = line.replace(fullbasename, basename)
                            elif stderrfilename == 'session':
                                line = line.replace(fullbasename, session)
                            elif stderrfilename == 'genericfile':
                                line = line.replace(fullbasename + '.' + extension, '<file>')
                            elif stderrfilename == 'genericscript':
                                line = line.replace(fullbasename + '.' + extension, '<script>')
                            err_dict[err_key].append(line)
                    elif process:
                        err_dict[err_key].append(line)
        
        if err_d:
            start_errgobble = None
            msg = []
            found_basename = False
            for n, line in enumerate(err_d):
                if line.startswith('=>PYTHONTEX:STDERR#'):
                    # Store the last group of messages.  Messages
                    # can't be directly appended to the main list, because
                    # a PythonTeX message must be inserted at the beginning 
                    # of each chunk of stderr that never references
                    # the script that was executed.  If the script is never
                    # referenced, then line numbers aren't automatically 
                    # synced.  These types of situations are created by 
                    # warnings.warn() etc.
                    if msg:
                        if not found_basename:
                            # Get line number for command or beginning of
                            # environment
                            instance = last_delim.split('#')[1]
                            doclinenum = str(code_index[instance].line_int)
                            input_file = code_index[instance].input_file
                            # Try to identify alert.  We have to parse all
                            # lines for signs of errors and warnings.  This 
                            # may result in overcounting, but it's the best
                            # we can do--otherwise, we could easily 
                            # undercount, or, finding a warning, miss a 
                            # subsequent error.  When this code is actually
                            # used, it's already a sign that normal parsing
                            # has failed.
                            found_error = False
                            found_warning = False
                            for l in msg:
                                for pattern in warningsig:
                                    if pattern in l:
                                        warnings += 1
                                        found_warning = True
                                for pattern in errorsig:
                                    if pattern in l:
                                        errors += 1
                                        found_warning = True
                            if found_error:
                                alert_type = 'error'
                            elif found_warning:
                                alert_type = 'warning'
                            else:
                                unknowns += 1
                                alert_type = 'unknown'
                            if input_file:
                                err_messages_d.append('* PythonTeX stderr - {0} near line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                            else:
                                err_messages_d.append('* PythonTeX stderr - {0} near line {1}:'.format(alert_type, doclinenum))
                        err_messages_d.extend(msg)
                    msg = []
                    found_basename = False
                    # Never process delimiting info until it is used
                    # Rather, store the index of the last delimiter
                    last_delim = line
                elif basename in line:
                    found_basename = True
                    # Get the gobbleation.  This is used to determine if 
                    # other lines containing the basename are a continuation,
                    # or separate messages.
                    errgobble = match('(\s*)', line).groups()[0]
                    if start_errgobble is None:
                        start_errgobble = errgobble
                    # Only issue a message and track down the line numer if
                    # this is indeed the start of a new message, rather than
                    # a continuation of an old message that happens to 
                    # contain the basename
                    if errgobble == start_errgobble:
                        # Determine the corresponding line number in the document
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            # Get info from last delim
                            instance, command = last_delim.split('#')[1:-1]
                            # Calculate the line number in the document
                            ei = code_index[instance]
                            if errlinenum > ei.lines_total + ei.lines_input:
                                doclinenum = str(ei.line_int + ei.lines_input)
                            else:
                                doclinenum = str(ei.line_int + errlinenum - ei.lines_total - 1)
                            input_file = ei.input_file
                        else:
                            doclinenum = '??'
                            input_file = '??'
                        
                        # Try to determine if we are dealing with an error or a 
                        # warning.
                        found = False
                        index = n
                        if stderrlookbehind:
                            while index >= 0:
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                past_line = err_d[index]
                                if (past_line.startswith('=>PYTHONTEX:STDERR#') or 
                                        (index < n and basename in past_line)):
                                    break
                                for pattern in warningsig:
                                    if pattern in past_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in past_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index -= 1
                        else:
                            while index < len(err_d):
                                # The order here is important.  If a line matches 
                                # both the error and warning patterns, default to 
                                # error.
                                future_line = err_d[index]
                                if (future_line.startswith('=>PYTHONTEX:STDERR#') or 
                                        (index > n and basename in future_line and future_line.startswith(start_errgobble))):
                                    break
                                for pattern in warningsig:
                                    if pattern in future_line:
                                        warnings += 1
                                        alert_type = 'warning'
                                        found = True
                                        break
                                for pattern in errorsig:
                                    if pattern in future_line:
                                        errors += 1
                                        alert_type = 'error'
                                        found = True
                                        break
                                if found:
                                    break
                                index += 1
                        # If an error or warning wasn't positively identified,
                        # assume error for safety but indicate uncertainty.
                        if not found:
                            unknowns += 1
                            alert_type = 'unknown'
                        if input_file:
                            msg.append('* PythonTeX stderr - {0} on line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                        else:
                            msg.append('* PythonTeX stderr - {0} on line {1}:'.format(alert_type, doclinenum))
                    # Clean up the stderr format a little, to keep it compact
                    line = line.replace(outputdir, '<outputdir>').rstrip('\n')
                    if '/<outputdir>' in line or '\\<outputdir>' in line:
                        line = sub(r'(?:(?:[A-Za-z]:\\)|(?:~?/)).*<outputdir>', '<outputdir>', line)
                    msg.append('  ' + line)
                else:
                    msg.append('  ' + line.rstrip('\n'))
            # Deal with any leftover messages
            if msg:
                if not found_basename:
                    # Get line number for command or beginning of
                    # environment
                    instance = last_delim.split('#')[1]
                    doclinenum = str(code_index[instance].line_int)
                    input_file = code_index[instance].input_file
                    # Try to identify alert.  We have to parse all
                    # lines for signs of errors and warnings.  This 
                    # may result in overcounting, but it's the best
                    # we can do--otherwise, we could easily 
                    # undercount, or, finding a warning, miss a 
                    # subsequent error.  When this code is actually
                    # used, it's already a sign that normal parsing
                    # has failed.
                    found_error = False
                    found_warning = False
                    for l in msg:
                        for pattern in warningsig:
                            if pattern in l:
                                warnings += 1
                                found_warning = True
                        for pattern in errorsig:
                            if pattern in l:
                                errors += 1
                                found_warning = True
                    if found_error:
                        alert_type = 'error'
                    elif found_warning:
                        alert_type = 'warning'
                    else:
                        unknowns += 1
                        alert_type = 'unknown'
                    if input_file:
                        err_messages_d.append('* PythonTeX stderr - {0} near line {1} in "{2}":'.format(alert_type, doclinenum, input_file))
                    else:
                        err_messages_d.append('* PythonTeX stderr - {0} near line {1}:'.format(alert_type, doclinenum))
                err_messages_d.extend(msg)
            
            # Create .stderr
            if makestderr and err_messages_d:
                process = False
                for n, line in enumerate(err_d):
                    if line.startswith('=>PYTHONTEX:STDERR#'):
                        instance, command = line.split('#')[1:-1]
                        if instance.endswith('CC'):
                            process = False
                        else:
                            process = True
                            err_key = basename + '_' + instance
                    elif process and basename in line:
                        found = False
                        for pattern in linesig:
                            try:
                                errlinenum = int(search(pattern, line).groups()[0])
                                found = True
                                break
                            except:
                                pass
                        if found:
                            # Calculate the line number in the document
                            # Account for inline
                            ei = code_index[instance]
                            # Store the `instance` in case it's 
                            # incremented later
                            last_instance = instance
                            # If the error or warning was actually triggered
                            # later on (for example, multiline string with
                            # missing final delimiter), look ahead and 
                            # determine the correct instance, so that
                            # we get the correct line number.  We don't
                            # associate the created stderr with this later
                            # instance, however, but rather with the instance
                            # in which the error began.  Doing that might 
                            # possibly be preferable in some cases, but would
                            # also require that the current stderr be split
                            # between multiple instances, requiring extra
                            # parsing.
                            while errlinenum > ei.lines_total + ei.lines_input:
                                next_instance = str(int(instance) + 1)
                                if next_instance in code_index:
                                    next_ei = code_index[next_instance]
                                    if errlinenum > next_ei.lines_total:
                                        instance = next_instance
                                        ei = next_ei
                                    else:
                                        break
                                else:
                                    break
                            if len(command) > 1:
                                if errlinenum > ei.lines_total + ei.lines_input:
                                    codelinenum = str(ei.lines_user + ei.lines_input + 1)
                                else:
                                    codelinenum = str(ei.lines_user + errlinenum - ei.lines_total - ei.inline_count)
                            else:
                                codelinenum = '1'
                            # Reset `instance`, in case incremented
                            instance = last_instance
                        else:
                            codelinenum = '??'
                            messages.append('* PythonTeX notice')
                            messages.append('    Line number ' + str(errlinenum) + ' could not be synced with the document')
                        
                        line = line.replace(str(errlinenum), str(codelinenum), 1)
                        if fullbasename_correct in line:
                            fullbasename = fullbasename_correct
                        else:
                            fullbasename = fullbasename_reslashed
                        if stderrfilename == 'full':
                            line = line.replace(fullbasename, basename)
                        elif stderrfilename == 'session':
                            line = line.replace(fullbasename, session)
                        elif stderrfilename == 'genericfile':
                            line = line.replace(fullbasename + '.' + extension, '<file>')
                        elif stderrfilename == 'genericscript':
                            line = line.replace(fullbasename + '.' + extension, '<script>')
                        err_dict[err_key].append(line)
                    elif process:
                        err_dict[err_key].append(line)
        if err_dict:
            for err_key in err_dict:
                stderr_file_name = os.path.join(outputdir, err_key + '.stderr')
                f = open(stderr_file_name, 'w', encoding=encoding)
                f.write(''.join(err_dict[err_key]))
                f.close()
                files.append(stderr_file_name)
    
    # Clean up temp files, and update the list of existing files
    if keeptemps == 'none':
        for ext in [extension, 'pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
    elif keeptemps == 'code':
        for ext in ['pytxmcr', 'out', 'err']:
            fname = os.path.join(outputdir, basename + '.' + ext)
            if os.path.isfile(fname):
                os.remove(fname)
        files.append(os.path.join(outputdir, basename + '.' + extension))
    elif keeptemps == 'all':
        for ext in [extension, 'pytxmcr', 'out', 'err']:
            files.append(os.path.join(outputdir, basename + '.' + ext))

    # Take care of any unknowns, based on exit code
    # Interpret the exit code as an indicator of whether there were errors,
    # and treat unknowns accordingly.  This will cause all warnings to be 
    # misinterpreted as errors if warnings trigger a nonzero exit code.
    # It will also cause all warnings to be misinterpreted as errors if there
    # is a single error that causes a nonzero exit code.  That isn't ideal,
    # but shouldn't be a problem, because as soon as the error(s) are fixed,
    # the exit code will be zero, and then all unknowns will be interpreted
    # as warnings.
    if unknowns:
        if proc.returncode == 0:
            unknowns_type = 'warnings'
            warnings += unknowns
        else:
            unknowns_type = 'errors'
            errors += unknowns
        unknowns_message = '''
                * PythonTeX notice
                    {0} message(s) could not be classified
                    Interpreted as {1}, based on the return code(s)'''
        messages[0] += textwrap.dedent(unknowns_message.format(unknowns, unknowns_type))
    
    # Take care of anything that has escaped detection thus far.
    if proc.returncode == 1 and not errors:
        errors += 1
        command_message = '''
                * PythonTeX error
                    An error occurred but no error messages were identified.
                    This may indicate a bad command or missing program.
                    The following command was executed:
                        "{0}"'''
        messages[0] += textwrap.dedent(command_message.format(' '.join(exec_cmd)))
    
    # Add any stderr messages; otherwise, clear the default message header
    if err_messages_ud:
        messages.extend(err_messages_ud)
    if err_messages_d:
        messages.extend(err_messages_d)
    if len(messages) == 1:
        messages = []
    
    # Return a dict of dicts of results
    return {'process': 'code',
            'key': key_run,
            'files': files,
            'macros': macros,
            'dependencies': dependencies,
            'errors': errors,
            'warnings': warnings,
            'messages': messages}




def do_pygments(encoding, outputdir, fvextfile, pygments_list, 
                pygments_settings, typeset_cache):
    '''
    Create Pygments content.
    
    To be run during multiprocessing.
    '''
    # Lazy import
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import LatexFormatter
    
    # Create what's needed for storing results
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    errors = 0
    warnings = 0
    messages = []
    messages.append('\n----  Messages for Pygments  ----')
    
    # Create dicts of formatters and lexers.
    formatter = dict()
    lexer = dict()
    for codetype in pygments_settings:
        if codetype != ':GLOBAL':
            formatter[codetype] = LatexFormatter(**pygments_settings[codetype]['formatter_options'])
            lexer[codetype] = get_lexer_by_name(pygments_settings[codetype]['lexer'], 
                                                **pygments_settings[codetype]['lexer_options'])
    
    # Actually parse and highlight the code.
    for c in pygments_list:
        if c.is_cons:
            content = typeset_cache[c.key_run][c.instance]
        elif c.is_extfile:
            if os.path.isfile(c.extfile):
                f = open(c.extfile, encoding=encoding)
                content = f.read()
                f.close()
            else:
                content = None
                messages.append('* PythonTeX error')
                messages.append('    Could not find external file ' + c.extfile)
                messages.append('    The file was not pygmentized')
        else:
            content = c.code
        processed = highlight(content, lexer[c.family], formatter[c.family])
        if c.is_inline or content.count('\n') < fvextfile:
            # Highlighted code brought in via macros needs SaveVerbatim
            if c.args_prettyprint:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@SaveVerbatim}}[\1, {4}]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance, c.args_prettyprint), processed, count=1)
            else:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@SaveVerbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance), processed, count=1)
            processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@SaveVerbatim}\n\n'
            pygments_macros[c.key_typeset].append(processed)
        else:
            if c.args_prettyprint:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@Verbatim}}[\1, {4}]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance, c.args_prettyprint), processed, count=1)
            else:
                processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                r'\\begin{{pytx@Verbatim}}[\1]{{pytx@{0}@{1}@{2}@{3}}}'.format(c.family, c.session, c.restart, c.instance), processed, count=1)
            processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@Verbatim}\n\n'
            fname = os.path.join(outputdir, c.key_typeset.replace('#', '_') + '.pygtex')
            f = open(fname, 'w', encoding=encoding)
            f.write(processed)
            f.close()
            pygments_files[c.key_typeset].append(fname)
    
    if len(messages) == 1:
        messages = []
    # Return a dict of dicts of results
    return {'process': 'pygments',
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'errors': errors,
            'warnings': warnings,
            'messages': messages} 




def python_console(jobname, encoding, outputdir, workingdir, fvextfile,
                   pygments_settings, cc_begin_list, cons_list, cc_end_list,
                   startup, banner, filename):
    '''
    Use Python's ``code`` module to typeset emulated Python interactive 
    sessions, optionally highlighting with Pygments.
    '''
    # Create what's needed for storing results
    key_run = cons_list[0].key_run
    files = []
    macros = []
    pygments_files = defaultdict(list)
    pygments_macros = defaultdict(list)
    typeset_cache = {}
    dependencies = {}
    errors = 0
    warnings = 0
    messages = []
    messages.append('\n----  Messages for ' + key_run.replace('#', ':') + '  ----')
    
    # Lazy import what's needed
    import code
    from collections import deque
    if sys.version_info[0] == 2:
        # Need a Python 2 interface to io.StringIO that can accept bytes
        import io
        class StringIO(io.StringIO):
            _orig_write = io.StringIO.write
            def write(self, s):
                self._orig_write(unicode(s))
    else:
        from io import StringIO
    
    # Create a custom console class
    class Console(code.InteractiveConsole):
        '''
        A subclass of code.InteractiveConsole that takes a list and treats it
        as a series of console input.
        '''
        
        def __init__(self, banner, filename):
            if banner == 'none':
                self.banner = 'NULL BANNER'
            elif banner == 'standard':
                cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
                self.banner = 'Python {0} on {1}\n{2}'.format(sys.version, sys.platform, cprt)
            elif banner == 'pyversion':
                self.banner = 'Python ' + '.'.join(str(sys.version_info[n]) for n in (0, 1, 2))
            else:
                self.banner = None
            if filename == 'console':
                self.filename = '<console>'
            elif filename == 'stdin':
                self.filename = '<stdin>'
            else:
                self.filename = None
            code.InteractiveConsole.__init__(self, filename=self.filename)
            self.iostdout = StringIO()
    
        def consolize(self, startup, cons_list):
            self.console_code = deque()
            # Delimiters are passed straight through and need newlines
            self.console_code.append('=>PYTHONTEX#STARTUP##\n')
            cons_config = '''
                    import os
                    import sys
                    docdir = os.getcwd()
                    if os.path.isdir('{workingdir}'):
                        os.chdir('{workingdir}')
                        if os.getcwd() not in sys.path:
                            sys.path.append(os.getcwd())
                    else:
                        sys.exit('Cannot find directory {workingdir}')
                    
                    if docdir not in sys.path:
                        sys.path.append(docdir)
                    
                    del docdir
                    '''
            cons_config = cons_config.format(workingdir=workingdir)[1:]
            self.console_code.extend(textwrap.dedent(cons_config).splitlines())
            # Code is processed and doesn't need newlines
            self.console_code.extend(startup.splitlines())
            for c in cons_list:
                self.console_code.append('=>PYTHONTEX#{0}#{1}#\n'.format(c.instance, c.command))
                self.console_code.extend(c.code.splitlines())
            old_stdout = sys.stdout
            sys.stdout = self.iostdout
            self.interact(self.banner)
            sys.stdout = old_stdout
            self.session_log = self.iostdout.getvalue()
    
        def raw_input(self, prompt):
            # Have to do a lot of looping and trying to make sure we get 
            # something valid to execute
            try:
                line = self.console_code.popleft()
            except IndexError:
                raise EOFError
            while line.startswith('=>PYTHONTEX#'):
                # Get new lines until we get one that doesn't begin with a 
                # delimiter.  Then write the last delimited line.
                old_line = line
                try:
                    line = self.console_code.popleft()
                    self.write(old_line)
                except IndexError:
                    raise EOFError
            if line or prompt == sys.ps2:
                self.write('{0}{1}\n'.format(prompt, line))
            else:
                self.write('\n')
            return line
        
        def write(self, data):
            self.iostdout.write(data)
    
    # Need to combine all custom code and user code to pass to consolize
    cons_list = cc_begin_list + cons_list + cc_end_list
    # Create a dict for looking up exceptions.  This is needed for startup 
    # commands and for code commands and environments, since their output
    # isn't typeset
    cons_index = {}
    for c in cons_list:
        cons_index[c.instance] = c.line    
    
    # Consolize the code
    # If the working directory is changed as part of the console code,
    # then we need to get back to where we were.
    con = Console(banner, filename)
    cwd = os.getcwd()
    con.consolize(startup, cons_list)
    os.chdir(cwd)
    
    # Set up Pygments, if applicable
    if pygments_settings is not None:
        pygmentize = True
        # Lazy import
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import LatexFormatter
        formatter = LatexFormatter(**pygments_settings['formatter_options'])
        lexer = get_lexer_by_name(pygments_settings['lexer'], 
                                  **pygments_settings['lexer_options'])
    else:
        pygmentize = False
    
    # Process the console output
    output = con.session_log.split('=>PYTHONTEX#')
    # Extract banner
    if banner == 'none':
        banner_text = ''
    else:
        banner_text = output[0]
    # Ignore the beginning, because it's the banner
    for block in output[1:]:
        delims, console_content = block.split('#\n', 1)
        if console_content:
            instance, command = delims.split('#')
            if instance == 'STARTUP':
                exception = False
                console_content_lines = console_content.splitlines()
                for line in console_content_lines:
                    if (not line.startswith(sys.ps1) and 
                            not line.startswith(sys.ps2) and 
                            line and not line.isspace()):
                        exception = True
                        break
                if exception:
                    if 'Error:' in console_content:
                        errors += 1
                        alert_type = 'error'
                    elif 'Warning:' in console_content:
                        warnings += 1
                        alert_type = 'warning'
                    else:
                        errors += 1
                        alert_type = 'error (?)'
                    messages.append('* PythonTeX stderr - {0} in console startup code:'.format(alert_type))
                    for line in console_content_lines:
                        messages.append('  ' + line)
            elif command in ('c', 'code'):
                exception = False
                console_content_lines = console_content.splitlines()
                for line in console_content_lines:
                    if (line and not line.startswith(sys.ps1) and 
                            not line.startswith(sys.ps2) and 
                            not line.isspace()):
                        exception = True
                        break
                if exception:
                    if 'Error:' in console_content:
                        errors += 1
                        alert_type = 'error'
                    elif 'Warning:' in console_content:
                        warnings += 1
                        alert_type = 'warning'
                    else:
                        errors += 1
                        alert_type = 'error (?)'
                    if instance.endswith('CC'):
                        messages.append('* PythonTeX stderr - {0} near line {1} in custom code for console:'.format(alert_type, cons_index[instance]))
                    else:
                        messages.append('* PythonTeX stderr - {0} near line {1} in console code:'.format(alert_type, cons_index[instance]))
                    messages.append('    Console code is not typeset, and should have no output')
                    for line in console_content_lines:
                        messages.append('  ' + line)
            else:
                if command == 'i':
                    # Currently, there isn't any error checking for invalid
                    # content; it is assumed that a single line of commands 
                    # was entered, producing one or more lines of output.
                    # Given that the current ``\pycon`` command doesn't
                    # allow line breaks to be written to the .pytxcode, that
                    # should be a reasonable assumption.
                    console_content = console_content.split('\n', 1)[1]
                elif console_content.endswith('\n\n'):
                    # Trim unwanted trailing newlines
                    console_content = console_content[:-1]
                if banner_text is not None and command == 'console':
                    # Append banner to first appropriate environment
                    console_content = banner_text + console_content
                    banner_text = None
                # Cache
                key_typeset = key_run + '#' + instance
                typeset_cache[instance] = console_content
                # Process for LaTeX
                if pygmentize:
                    processed = highlight(console_content, lexer, formatter)
                    if console_content.count('\n') < fvextfile:                            
                        processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                        r'\\begin{{pytx@SaveVerbatim}}[\1]{{pytx@{0}}}'.format(key_typeset.replace('#', '@')),
                                        processed, count=1)
                        processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@SaveVerbatim}\n\n'
                        pygments_macros[key_typeset].append(processed)
                    else:
                        processed = sub(r'\\begin{Verbatim}\[(.+)\]', 
                                        r'\\begin{{pytx@Verbatim}}[\1]{{pytx@{0}}}'.format(key_typeset.replace('#', '@')),
                                        processed, count=1)
                        processed = processed.rsplit('\\', 1)[0] + '\\end{pytx@Verbatim}\n\n'
                        fname = os.path.join(outputdir, key_typeset.replace('#', '_') + '.pygtex')
                        f = open(fname, 'w', encoding=encoding)
                        f.write(processed)
                        f.close()
                        pygments_files[key_typeset].append(fname)  
                else:
                    if console_content.count('\n') < fvextfile:
                        processed = ('\\begin{{pytx@SaveVerbatim}}{{pytx@{0}}}\n'.format(key_typeset.replace('#', '@')) + 
                                     console_content + '\\end{pytx@SaveVerbatim}\n\n')
                        macros.append(processed)
                    else:
                        processed = ('\\begin{pytx@Verbatim}\n' + console_content +
                                     '\\end{pytx@Verbatim}\n\n')
                        fname = os.path.join(outputdir, key_typeset.replace('#', '_') + '.tex')
                        f = open(fname, 'w', encoding=encoding)
                        f.write(processed)
                        f.close()
                        files.append(fname)
    
    if len(messages) == 1:
        messages = []
    
    # Return a dict of dicts of results
    return {'process': 'console',
            'key': key_run,
            'files': files,
            'macros': macros,
            'pygments_files': pygments_files,
            'pygments_macros': pygments_macros,
            'typeset_cache': typeset_cache,
            'dependencies': dependencies,
            'errors': errors,
            'warnings': warnings,
            'messages': messages} 




def main(python=None):
    # Create dictionaries for storing data.
    #
    # All data that must be saved for subsequent runs is stored in "data".
    # (We start off by saving the script version, a global var, in this dict.)
    # All data that is only created for this run is stored in "temp_data".
    # (We start off by creating keys for keeping track of errors and warnings.)
    # All old data will eventually be loaded into "old_data".
    # Since dicts are mutable data types, these dicts can be modified
    # from within functions, as long as the dicts are passed to the functions.
    # For simplicity, variables will often be created within functions to
    # refer to dictionary values.
    data = {'version': version, 'start_time': time.time()}
    temp_data = {'errors': 0, 'warnings': 0, 'python': python}
    old_data = dict()

    
    # Process command-line options.
    #
    # This gets the raw_jobname (actual job name), jobname (a sanitized job 
    # name, used for creating files named after the jobname), and any options.
    process_argv(data, temp_data)
    # If there aren't errors in argv, and the program is going to run 
    # (rather than just exit due to --version or --help command-line options), 
    # print PythonTeX version.  Flush to make the message go out immediately,  
    # so that the user knows PythonTeX has started.
    print('This is PythonTeX ' + version)
    sys.stdout.flush()
    # Once we have the encoding (from argv), we set stdout and stderr to use 
    # this encoding.  Later, we will parse the saved stderr of scripts 
    # executed via multiprocessing subprocesses, and print the parsed results 
    # to stdout.  The saved stderr uses the same encoding that was used 
    # for the files that created it (this is important for code containing 
    # unicode characters), so we also need stdout for the main PythonTeX
    # script to support this encoding.  Setting stderr encoding is primarily 
    # a matter of symmetry.  Ideally, pythontex*.py will be bug-free,
    # and stderr won't be needed!
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter(data['encoding'])(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter(data['encoding'])(sys.stderr.buffer, 'strict')


    # Load the code and process the settings it passes from the TeX side.
    #
    # This gets a list containing the code (the part of the code file 
    # containing the settings is removed) and the processed settings.
    load_code_get_settings(data, temp_data)
    # Now that the settings are loaded, check if outputdir exits.
    # If not, create it.
    if not os.path.isdir(data['settings']['outputdir']):
        os.mkdir(data['settings']['outputdir'])


    # Load/create old_data
    get_old_data(data, old_data, temp_data)
    
    
    # Hash the code.  Determine what needs to be executed.  Determine whether
    # Pygments should be used.  Update pygments_settings to account for 
    # Pygments commands and environments (as opposed to PythonTeX commands 
    # and environments).
    hash_all(data, temp_data, old_data, engine_dict)
    
    
    # Parse the code and write scripts for execution.
    parse_code_write_scripts(data, temp_data, engine_dict)
    
    
    # Execute the code and perform Pygments highlighting via multiprocessing.
    do_multiprocessing(data, temp_data, old_data, engine_dict)

        
    # Print exit message
    print('\n--------------------------------------------------')
    # If some rerun settings are used, there may be unresolved errors or 
    # warnings; if so, print a summary of those along with the current 
    # error and warning summary
    unresolved_errors = 0
    unresolved_warnings = 0
    if temp_data['rerun'] in ('errors', 'modified', 'never'):
        global_update = {}
        global_update.update(temp_data['code_update'])
        global_update.update(temp_data['cons_update'])
        for key in data['exit_status']:
            if not global_update[key]:
                unresolved_errors += data['exit_status'][key][0]
                unresolved_warnings += data['exit_status'][key][1]
    if unresolved_warnings != 0 or unresolved_errors != 0:
        print('PythonTeX:  {0}'.format(data['raw_jobname']))
        print('    - Old:      {0} error(s), {1} warnings(s)'.format(unresolved_errors, unresolved_warnings))
        print('    - Current:  {0} error(s), {1} warnings(s)'.format(temp_data['errors'], temp_data['warnings']))        
    else:
        print('PythonTeX:  {0} - {1} error(s), {2} warning(s)\n'.format(data['raw_jobname'], temp_data['errors'], temp_data['warnings']))

    # Exit with appropriate exit code based on user settings.
    if temp_data['error_exit_code'] and temp_data['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit()



# The "if" statement is needed for multiprocessing under Windows; see the 
# multiprocessing documentation.  It is also needed in this case when the 
# script is invoked via the wrapper.
if __name__ == '__main__':
    #// Python 2
    #if sys.version_info.major != 2:
    #    sys.exit('This version of the PythonTeX script requires Python 2.')
    #\\ End Python 2
    #// Python 3
    if sys.version_info.major != 3:
        sys.exit('This version of the PythonTeX script requires Python 3.')
    #\\ End Python 3
    main(python=sys.version_info.major)

########NEW FILE########
__FILENAME__ = pythontex_2to3
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Convert PythonTeX scripts from Python 2 to Python 3

It isn't possible to have a single PythonTeX code base, since unicode text 
needs to be supported.  Under Python 2, this means importing unicode_literals 
from __future__, or using the unicode function or "u" prefix.  Under Python 3,
all strings are automatically unicode.

At the same time, the differences between the Python 2 and 3 versions are 
usually very small, involving only a few lines of code.  To keep the code base
unified, while simultaneously fully supporting both Python 2 and 3, the 
following scheme was devised.  The code is written for Python 2.  Whenever 
code is not compatible with Python 3, it is enclosed with the tags 
"#// Python 2" and "#\\ End Python 2" (each on its own line, by itself).  If 
a Python 3 version of the code is needed, it is included between analogous 
tags "#// Python 3" and "#\\ End Python 2".  The Python 3 code is commented 
out with "#", at the same indentation level as the Python 3 tags.

This script creates Python 3 scripts from the original Python 2 scripts 
by commenting out everything between the Python 2 tags, and uncommenting 
everything between the Python 3 tags.  In this way, full compatibility is 
maintained with both Python 2 and 3 while keeping the code base essentially 
unified.  This approach also allows greater customization of version-specific 
code than would be possible if automatic translation with a tool like 2to3 
was required.

Copyright (c) 2012-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
from __future__ import unicode_literals
from io import open
import re


files_to_process = ('pythontex2.py', 'depythontex2.py')
encoding = 'utf-8'


def from2to3(list_of_code):
    fixed = []
    in_2 = False
    in_3 = False
    indent = ''
    
    for line in list_of_code:
        if r'#// Python 2' in line:
            in_2 = True
            indent = line.split('#', 1)[0]
        elif r'#\\ End Python 2' in line:
            in_2 = False
        elif r'#// Python 3' in line:
            in_3 = True
            indent = line.split('#', 1)[0]
        elif r'#\\ End Python 3' in line:
            in_3 = False
        elif in_2:
            line = re.sub(indent, indent + '#', line, count=1)
        elif in_3:
            line = re.sub(indent + '#', indent, line, count=1)
        fixed.append(line)
    if fixed[0].startswith('#!/usr/bin/env python2'):
        fixed[0] = fixed[0].replace('python2', 'python3')
    return fixed
        
        
for file in files_to_process:
    f = open(file, 'r', encoding=encoding)
    converted_code = from2to3(f.readlines())
    f.close()
    f = open(re.sub('2', '3', file), 'w', encoding=encoding)
    f.write(''.join(converted_code))
    f.close()



########NEW FILE########
__FILENAME__ = pythontex_engines
# -*- coding: utf-8 -*-
'''
PythonTeX code engines.

Provides a class for managing the different languages/types of code
that may be executed.  A class instance is created for each language/type of
code.  The class provides a method for assembling the scripts that are 
executed, combining user code with templates.  It also creates the records 
needed to synchronize `stderr` with the document.

Each instance of the class is automatically added to the `engines_dict` upon
creation.  Instances are typically accessed via this dictionary.

The class is called `*CodeEngine` by analogy with a template engine, since it
combines user text (code) with existing templates to produce an output
document (script for execution).



Copyright (c) 2012-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''

# Imports
import os
import sys
import textwrap
from hashlib import sha1
from collections import OrderedDict, namedtuple


interpreter_dict = {k:k for k in ('python', 'ruby', 'julia', 'octave')}
# The {file} field needs to be replaced by itself, since the actual 
# substitution of the real file can only be done at runtime, whereas the
# substitution for the interpreter should be done when the engine is 
# initialized.
interpreter_dict['file'] = '{file}'
interpreter_dict['File'] = '{File}'


engine_dict = {}


CodeIndex = namedtuple('CodeIndex', ['input_file', 'command', 
                                     'line_int', 'lines_total', 
                                     'lines_user', 'lines_input',
                                     'inline_count'])


class CodeEngine(object):
    '''
    The base class that is used for defining language engines.  Each command 
    and environment family is based on an engine.
    
    The class assembles the individual scripts that PythonTeX executes, using
    templates and user code.  It also creates the records needed for 
    synchronizing `stderr` with the document.
    '''
    def __init__(self, name, language, extension, command, template, wrapper, 
                 formatter, errors=None, warnings=None,
                 linenumbers=None, lookbehind=False, 
                 console=False, startup=None, created=None):

        # Save raw arguments so that they may be reused by subtypes
        self._rawargs = (name, language, extension, command, template, wrapper, 
                         formatter, errors, warnings,
                         linenumbers, lookbehind, console, startup, created)
        
        # Type check all strings, and make sure everything is Unicode
        if sys.version_info[0] == 2:
            if (not isinstance(name, basestring) or 
                    not isinstance(language, basestring) or 
                    not isinstance(extension, basestring) or 
                    not isinstance(command, basestring) or 
                    not isinstance(template, basestring) or
                    not isinstance(wrapper, basestring) or
                    not isinstance(formatter, basestring)):
                raise TypeError('CodeEngine needs string in initialization')
            self.name = unicode(name)
            self.language = unicode(language)
            self.extension = unicode(extension)
            self.command = unicode(command)
            self.template = unicode(template)
            self.wrapper = unicode(wrapper)
            self.formatter = unicode(formatter)
        else:
            if (not isinstance(name, str) or 
                    not isinstance(language, str) or 
                    not isinstance(extension, str) or 
                    not isinstance(command, str) or 
                    not isinstance(template, str) or
                    not isinstance(wrapper, str) or
                    not isinstance(formatter, str)):    
                raise TypeError('CodeEngine needs string in initialization')
            self.name = name
            self.language = language
            self.extension = extension
            self.command = command
            self.template = template
            self.wrapper = wrapper
            self.formatter = formatter
        # Perform some additional formatting on some strings.
        self.extension = self.extension.lstrip('.')
        self.template = self._dedent(self.template)
        self.wrapper = self._dedent(self.wrapper)
        # Make sure formatter string ends with a newline
        if not self.formatter.endswith('\n'):
            self.formatter = self.formatter + '\n'
        
        # Type check errors, warnings, and linenumbers
        if errors is None:
            errors = []
        else:
            if sys.version_info[0] == 2:
                if isinstance(errors, basestring):
                    errors = [errors]
                elif not isinstance(errors, list) and not isinstance(errors, tuple):
                    raise TypeError('CodeEngine needs "errors" to be a string, list, or tuple')
                for e in errors:
                    if not isinstance(e, basestring):
                        raise TypeError('CodeEngine needs "errors" to contain strings')
                errors = [unicode(e) for e in errors]
            else:
                if isinstance(errors, str):
                    errors = [errors]
                elif not isinstance(errors, list) and not isinstance(errors, tuple):
                    raise TypeError('CodeEngine needs "errors" to be a string, list, or tuple')
                for e in errors:
                    if not isinstance(e, str):
                        raise TypeError('CodeEngine needs "errors" to contain strings')
            self.errors = errors
        if warnings is None:
            warnings = []
        else:
            if sys.version_info[0] == 2:
                if isinstance(warnings, basestring):
                    warnings = [warnings]
                elif not isinstance(warnings, list) and not isinstance(warnings, tuple):
                    raise TypeError('CodeEngine needs "warnings" to be a string, list, or tuple')
                for w in warnings:
                    if not isinstance(w, basestring):
                        raise TypeError('CodeEngine needs "warnings" to contain strings')
                warnings = [unicode(w) for w in warnings]
            else:
                if isinstance(warnings, str):
                    warnings = [warnings]
                elif not isinstance(warnings, list) and not isinstance(warnings, tuple):
                    raise TypeError('CodeEngine needs "warnings" to be a string, list, or tuple')
                for w in warnings:
                    if not isinstance(w, str):
                        raise TypeError('CodeEngine needs "warnings" to contain strings')
            self.warnings = warnings
        if linenumbers is None:
            linenumbers = 'line {number}'
        if sys.version_info[0] == 2:
            if isinstance(linenumbers, basestring):
                linenumbers = [linenumbers]
            elif not isinstance(linenumbers, list) and not isinstance(linenumbers, tuple):
                raise TypeError('CodeEngine needs "linenumbers" to be a string, list, or tuple')
            for l in linenumbers:
                if not isinstance(l, basestring):
                    raise TypeError('CodeEngine needs "linenumbers" to contain strings')
            linenumbers = [unicode(l) for l in linenumbers]
        else:
            if isinstance(linenumbers, str):
                linenumbers = [linenumbers]
            elif not isinstance(linenumbers, list) and not isinstance(linenumbers, tuple):
                raise TypeError('CodeEngine needs "linenumbers" to be a string, list, or tuple')
            for l in linenumbers:
                if not isinstance(l, str):
                    raise TypeError('CodeEngine needs "linenumbers" to contain strings')
        # Need to replace tags
        linenumbers = [l.replace('{number}', r'(\d+)') for l in linenumbers]
        self.linenumbers = linenumbers

        # Type check lookbehind
        if not isinstance(lookbehind, bool):
            raise TypeError('CodeEngine needs "lookbehind" to be bool')
        self.lookbehind = lookbehind
        
        # Type check console
        if not isinstance(console, bool):
            raise TypeError('CodeEngine needs "console" to be bool')
        self.console = console
        
        # Type check startup
        if startup is None:
            startup = ''
        if startup and not self.console:
            raise TypeError('PythonTeX can only use "startup" for console types')
        else:
            if sys.version_info[0] == 2:
                if isinstance(startup, basestring):
                    startup = unicode(startup)
                else:
                    raise TypeError('CodeEngine needs "startup" to be a string')
            else:
                if not isinstance(startup, str):
                    raise TypeError('CodeEngine needs "startup" to be a string')
            if not startup.endswith('\n'):
                startup += '\n'
        self.startup = self._dedent(startup)
        
        # Type check created; make sure it is an iterable and contains Unicode
        if created is None:
            created = []
        else:
            if sys.version_info[0] == 2:
                if isinstance(created, basestring):
                    created = [created]
                elif not isinstance(created, list) and not isinstance(created, tuple):
                    raise TypeError('CodeEngine needs "created" to be a string, list, or tuple')
                for f in created:
                    if not isinstance(f, basestring):
                        raise TypeError('CodeEngine "created" to contain strings')
                created = [unicode(f) for f in created]
            else:
                if isinstance(created, str):
                    created = [created]
                elif not isinstance(created, list) and not isinstance(created, tuple):
                    raise TypeError('CodeEngine needs "created" to be a string, list, or tuple')
                for f in created:
                    if not isinstance(f, str):
                        raise TypeError('CodeEngine needs "created" to contain strings')
        self.created = created
        
        # The base PythonTeX type does not support extend; it is used in 
        # subtyping.  But a dummy extend is needed to fill the extend field
        # in templates, if it is provided.
        self.extend = ''
        
        # Create dummy variables for console
        self.banner = ''
        self.filename = ''
        
        # Each type needs to add itself to a dict, for later access by name
        self._register()
    
    def _dedent(self, s):
        '''
        Dedent and strip leading newlines
        '''
        s = textwrap.dedent(s)
        while s.startswith('\n'):
            s = s[1:]
        return s
        
    def _register(self):
        '''
        Add instance to a dict for later access by name
        '''
        engine_dict[self.name] = self
        
    def customize(self, **kwargs):
        '''
        Customize the template on the fly.
        
        This provides customization based on command line arguments 
        (`--interpreter`) and customization from the TeX side (imports from
        `__future__`).  Ideally, this function should be restricted to this 
        and similar cases.  The custom code command and environment are 
        insufficient for such cases, because the command is at a level above
        that of code and because of the requirement that imports from 
        `__future__` be at the very beginning of a script.
        '''
        # Take care of `--interpreter`
        # The `interpreter_dict` has entries that allow `{file}` and
        # `{outputdir}` fields to be replaced with themselves
        self.command = self.command.format(**interpreter_dict)
        # Take care of `__future__`
        if self.language.startswith('python'):
            if sys.version_info[0] == 2 and 'pyfuture' in kwargs:
                pyfuture = kwargs['pyfuture']
                future_imports = None
                if pyfuture == 'all':
                    future_imports = '''
                            from __future__ import absolute_import
                            from __future__ import division
                            from __future__ import print_function
                            from __future__ import unicode_literals
                            {future}'''
                elif pyfuture == 'default':
                    future_imports = '''
                            from __future__ import absolute_import
                            from __future__ import division
                            from __future__ import print_function
                            {future}'''
                if future_imports is not None:
                    future_imports = self._dedent(future_imports)
                    self.template = self.template.replace('{future}', future_imports)
            if self.console:
                if sys.version_info[0] == 2 and 'pyconfuture' in kwargs:
                    pyconfuture = kwargs['pyconfuture']
                    future_imports = None
                    if pyconfuture == 'all':
                        future_imports = '''
                                from __future__ import absolute_import
                                from __future__ import division
                                from __future__ import print_function
                                from __future__ import unicode_literals
                                '''
                    elif pyconfuture == 'default':
                        future_imports = '''
                                from __future__ import absolute_import
                                from __future__ import division
                                from __future__ import print_function
                                '''
                    if future_imports is not None:
                        future_imports = self._dedent(future_imports)
                        self.startup = future_imports + self.startup
                if 'pyconbanner' in kwargs:
                    self.banner = kwargs['pyconbanner']
                if 'pyconfilename' in kwargs:
                    self.filename = kwargs['pyconfilename']

    _hash = None
            
    def get_hash(self):
        '''
        Return a hash of all vital type information (template, etc.).  Create
        the hash if it doesn't exist, otherwise return a stored hash.
        '''
        # This file is encoded in UTF-8, so everything can be encoded in UTF-8.
        # It's not important that this encoding be the same as that given by
        # the user, since a unique hash is all that's needed.
        if self._hash is None:
            hasher = sha1()
            hasher.update(self.command.encode('utf8'))
            hasher.update(self.template.encode('utf8'))
            hasher.update(self.wrapper.encode('utf8'))
            hasher.update(self.formatter.encode('utf8'))
            if self.console:
                hasher.update(self.startup.encode('utf8'))
                hasher.update(self.banner.encode('utf8'))
                hasher.update(self.filename.encode('utf8'))
            self._hash = hasher.hexdigest()
        return self._hash
    
    def _process_future(self, code_list):
        '''
        Go through a given list of code and extract all imports from 
        `__future__`, so that they can be relocated to the beginning of the 
        script.
        
        The approach isn't foolproof and doesn't support compound statements.
        '''
        done = False
        future_imports = []
        for n, c in enumerate(code_list):
            in_triplequote = False
            changed = False
            code = c.code.split('\n')
            for l, line in enumerate(code):
                # Detect __future__ imports
                if (line.startswith('from __future__') or 
                        line.startswith('import __future__') and 
                        not in_triplequote):
                    changed = True
                    if ';' in line:
                        raise ValueError('Imports from __future__ should be simple statements; semicolons are not supported')
                    else:
                        future_imports.append(line)
                        code[l] = ''
                # Ignore comments, empty lines, and lines with complete docstrings
                elif (line.startswith('\n') or line.startswith('#') or 
                        line.isspace() or
                        ('"""' in line and line.count('"""')%2 == 0) or 
                        ("'''" in line and line.count("'''")%2 == 0)):
                    pass
                # Detect if entering or leaving a docstring
                elif line.count('"""')%2 == 1 or line.count("'''")%2 == 1:
                    in_triplequote = not in_triplequote
                # Stop looking for future imports as soon as a non-comment, 
                # non-empty, non-docstring, non-future import line is found
                elif not in_triplequote:
                    done = True
                    break
            if changed:
                code_list[n].code = '\n'.join(code)
            if done:
                break
        if future_imports:
            return '\n'.join(future_imports)
        else:
            return ''
            
    def _get_future(self, cc_list_begin, code_list):
        '''
        Process custom code and user code for imports from `__future__`
        '''
        cc_future = self._process_future(cc_list_begin)
        code_future = self._process_future(code_list)
        if cc_future and code_future:
            return cc_future + '\n' + code_future
        else:
            return cc_future + code_future
    
    def get_script(self, encoding, utilspath, workingdir, 
                   cc_list_begin, code_list, cc_list_end):
        '''
        Assemble the script that will be executed.  In the process, assemble
        an index of line numbers that may be used to correlate script line
        numbers with document line numbers and user code line numbers in the 
        event of errors or warnings.
        '''
        lines_total = 0
        script = []
        code_index = OrderedDict()
        
        # Take care of future
        if self.language.startswith('python'):
            future = self._get_future(cc_list_begin, code_list)
        else:
            future = ''
        
        # Split template into beginning and ending segments
        try:
            script_begin, script_end = self.template.split('{body}')
        except:
            raise ValueError('Template for ' + self.name + ' is missing {body}')
        
        # Add beginning to script
        if os.path.isabs(os.path.expanduser(os.path.normcase(workingdir))):
            workingdir_full = workingdir
        else:
            workingdir_full = os.path.join(os.getcwd(), workingdir).replace('\\', '/')
        script_begin = script_begin.format(encoding=encoding, future=future, 
                                           utilspath=utilspath, workingdir=workingdir,
                                           Workingdir=workingdir_full,
                                           extend=self.extend,
                                           family=code_list[0].family,
                                           session=code_list[0].session,
                                           restart=code_list[0].restart,
                                           dependencies_delim='=>PYTHONTEX:DEPENDENCIES#',
                                           created_delim='=>PYTHONTEX:CREATED#')
        script.append(script_begin)
        lines_total += script_begin.count('\n')
        
        # Prep wrapper
        try:
            wrapper_begin, wrapper_end = self.wrapper.split('{code}')
        except:
            raise ValueError('Wrapper for ' + self.name + ' is missing {code}')
        if not self.language.startswith('python'):
            # In the event of a syntax error at the end of user code, Ruby
            # (and perhaps others) will use the line number from the NEXT
            # line of code that is non-empty, not from the line of code where
            # the error started.  In these cases, it's important
            # to make sure that the line number is triggered immediately 
            # after user code, so that the line number makes sense.  Hence,
            # we need to strip all whitespace from the part of the wrapper
            # that follows user code.  For symetry, we do the same for both
            # parts of the wrapper.
            wrapper_begin = wrapper_begin.rstrip(' \t\n') + '\n'
            wrapper_end = wrapper_end.lstrip(' \t\n')
        stdoutdelim = '=>PYTHONTEX:STDOUT#{instance}#{command}#'
        stderrdelim = '=>PYTHONTEX:STDERR#{instance}#{command}#'
        wrapper_begin = wrapper_begin.replace('{stdoutdelim}', stdoutdelim).replace('{stderrdelim}', stderrdelim)
        wrapper_begin_offset = wrapper_begin.count('\n')
        wrapper_end_offset = wrapper_end.count('\n')
        
        # Take care of custom code
        # Line counters must be reset for cc begin, code, and cc end, since 
        # all three are separate
        lines_user = 0
        inline_count = 0
        for c in cc_list_begin:
            # Wrapper before
            lines_total += wrapper_begin_offset
            script.append(wrapper_begin.format(command=c.command,
                                               context=c.context,
                                               args=c.args_run,
                                               instance=c.instance,
                                               line=c.line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.instance] = CodeIndex(c.input_file, c.command, c.line_int, lines_total, lines_user, lines_input, inline_count)
            script.append(c.code)
            if c.is_inline:
                inline_count += 1
            lines_total += lines_input
            lines_user += lines_input
            
            # Wrapper after
            script.append(wrapper_end)
            lines_total += wrapper_end_offset
        
        # Take care of user code
        lines_user = 0
        inline_count = 0
        for c in code_list:
            # Wrapper before
            lines_total += wrapper_begin_offset
            script.append(wrapper_begin.format(command=c.command,
                                               context=c.context,
                                               args=c.args_run,
                                               instance=c.instance,
                                               line=c.line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.instance] = CodeIndex(c.input_file, c.command, c.line_int, lines_total, lines_user, lines_input, inline_count)
            if c.command == 'i':
                script.append(self.formatter.format(code=c.code.rstrip('\n')))
                inline_count += 1
            else:
                script.append(c.code)
            lines_total += lines_input
            lines_user += lines_input                
            
            # Wrapper after
            script.append(wrapper_end)
            lines_total += wrapper_end_offset
        
        # Take care of custom code
        lines_user = 0
        inline_count = 0
        for c in cc_list_end:
            # Wrapper before
            lines_total += wrapper_begin_offset
            script.append(wrapper_begin.format(command=c.command,
                                               context=c.context,
                                               args=c.args_run,
                                               instance=c.instance,
                                               line=c.line))
            
            # Actual code
            lines_input = c.code.count('\n')
            code_index[c.instance] = CodeIndex(c.input_file, c.command, c.line_int, lines_total, lines_user, lines_input, inline_count)
            script.append(c.code)
            if c.is_inline:
                inline_count += 1
            lines_total += lines_input
            lines_user += lines_input
            
            # Wrapper after
            script.append(wrapper_end)
            lines_total += wrapper_end_offset
        
        # Finish script
        script.append(script_end.format(dependencies_delim='=>PYTHONTEX:DEPENDENCIES#', created_delim='=>PYTHONTEX:CREATED#'))
        
        return script, code_index


        

class SubCodeEngine(CodeEngine):
    '''
    Create Engine instances that inherit from existing instances.
    '''
    def __init__(self, base, name, language=None, extension=None, command=None, 
                 template=None, wrapper=None, formatter=None, errors=None,
                 warnings=None, linenumbers=None, lookbehind=False,
                 console=None, created=None, startup=None, extend=None):
        
        self._rawargs = (name, language, extension, command, template, wrapper, 
                         formatter, errors, warnings,
                         linenumbers, lookbehind, console, startup, created)
                         
        base_rawargs = engine_dict[base]._rawargs
        args = []
        for n, arg in enumerate(self._rawargs):
            if arg is None:
                args.append(base_rawargs[n])
            else:
                args.append(arg)
        
        CodeEngine.__init__(self, *args)
        
        self.extend = engine_dict[base].extend
        
        if extend is not None:
            if sys.version_info[0] == 2:
                if not isinstance(extend, basestring):
                    raise TypeError('PythonTeXSubtype needs a string for "extend"')
                extend = unicode(extend)
            else:
                if not isinstance(extend, str):
                    raise TypeError('PythonTeXSubtype needs a string for "extend"')
            if not extend.endswith('\n'):
                extend = extend + '\n'
            self.extend += self._dedent(extend)




class PythonConsoleEngine(CodeEngine):
    '''
    This uses the Engine class to store information needed for emulating
    Python interactive consoles.
    
    In the current form, it isn't used as a real engine, but rather as a 
    convenient storage class that keeps the treatment of all languages/code 
    types uniform.
    '''
    def __init__(self, name, startup=None):
        CodeEngine.__init__(self, name=name, language='python', 
                            extension='', command='', template='', 
                            wrapper='', formatter='', errors=None, 
                            warnings=None, linenumbers=None, lookbehind=False,
                            console=True, startup=startup, created=None)




python_template = '''
    # -*- coding: {encoding} -*-
    
    {future}
    
    import os
    import sys
    import codecs
    
    if sys.version_info[0] == 2:
        sys.stdout = codecs.getwriter('{encoding}')(sys.stdout, 'strict')
        sys.stderr = codecs.getwriter('{encoding}')(sys.stderr, 'strict')
    else:
        sys.stdout = codecs.getwriter('{encoding}')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('{encoding}')(sys.stderr.buffer, 'strict')
    
    if '{utilspath}' and '{utilspath}' not in sys.path:
        sys.path.append('{utilspath}')    
    from pythontex_utils import PythonTeXUtils
    pytex = PythonTeXUtils()
    
    pytex.docdir = os.getcwd()
    if os.path.isdir('{workingdir}'):
        os.chdir('{workingdir}')
        if os.getcwd() not in sys.path:
            sys.path.append(os.getcwd())
    else:
        if len(sys.argv) < 2 or sys.argv[1] != '--manual':
            sys.exit('Cannot find directory {workingdir}')
    if pytex.docdir not in sys.path:
        sys.path.append(pytex.docdir)
    
    {extend}
    
    pytex.id = '{family}_{session}_{restart}'
    pytex.family = '{family}'
    pytex.session = '{session}'
    pytex.restart = '{restart}'
    
    {body}

    pytex.cleanup()
    '''

python_wrapper = '''
    pytex.command = '{command}'
    pytex.set_context('{context}')
    pytex.args = '{args}'
    pytex.instance = '{instance}'
    pytex.line = '{line}'
    
    print('{stdoutdelim}')
    sys.stderr.write('{stderrdelim}\\n')
    pytex.before()
    
    {code}
    
    pytex.after()
    '''


CodeEngine('python', 'python', '.py', '{python} {file}.py',
              python_template, python_wrapper, 'print(pytex.formatter({code}))',
              'Error:', 'Warning:', ['line {number}', ':{number}:'])

SubCodeEngine('python', 'py')

SubCodeEngine('python', 'pylab', extend='from pylab import *')

sympy_extend = '''
    from sympy import *
    pytex.set_formatter('sympy_latex')
    '''

SubCodeEngine('python', 'sympy', extend=sympy_extend)




PythonConsoleEngine('pycon')

PythonConsoleEngine('pylabcon', startup='from pylab import *')

PythonConsoleEngine('sympycon', startup='from sympy import *')




ruby_template = '''
    # -*- coding: {encoding} -*-
    
    $stdout.set_encoding('{encoding}')
    $stderr.set_encoding('{encoding}')
    
    class RubyTeXUtils
        attr_accessor :id, :family, :session, :restart, 
                :command, :context, :args, 
                :instance, :line, :dependencies, :created,
                :docdir, :_context_raw
        def initialize
            @dependencies = Array.new
            @created = Array.new
            @_context_raw = nil
        end
        def formatter(expr)
            return expr.to_s
        end
        def before
        end
        def after
        end
        def add_dependencies(*expr)
            self.dependencies.push(*expr)
        end
        def add_created(*expr)
            self.created.push(*expr)
        end
        def set_context(expr)
            if expr != "" and expr != @_context_raw
                @context = expr.split(',').map{{|x| x1,x2 = x.split('='); {{x1.strip() => x2.strip()}}}}.reduce(:merge)
                @_context_raw = expr
            end
        end
        def pt_to_in(expr)
            if expr.is_a?String
                if expr.end_with?'pt'
                    expr = expr[0..-3]
                end
                return expr.to_f/72.27
            else
                return expr/72.27
            end
        end
        def pt_to_cm(expr)
            return pt_to_in(expr)*2.54
        end
        def pt_to_mm(expr)
            return pt_to_in(expr)*25.4
        end
        def pt_to_bp(expr)
            return pt_to_in(expr)*72
        end
        def cleanup
            puts '{dependencies_delim}'
            if @dependencies
                @dependencies.each {{ |x| puts x }}
            end
            puts '{created_delim}'
            if @created
                @created.each {{ |x| puts x }}
            end
        end        
    end
            
    rbtex = RubyTeXUtils.new
    
    rbtex.docdir = Dir.pwd
    if File.directory?('{workingdir}')
        Dir.chdir('{workingdir}')
        $LOAD_PATH.push(Dir.pwd) unless $LOAD_PATH.include?(Dir.pwd)
    elsif ARGV[0] != '--manual'
        abort('Cannot change to directory {workingdir}')
    end
    $LOAD_PATH.push(rbtex.docdir) unless $LOAD_PATH.include?(rbtex.docdir)
    
    {extend}
    
    rbtex.id = '{family}_{session}_{restart}'
    rbtex.family = '{family}'
    rbtex.session = '{session}'
    rbtex.restart = '{restart}'
    
    {body}

    rbtex.cleanup
    '''

ruby_wrapper = '''
    rbtex.command = '{command}'
    rbtex.set_context('{context}')
    rbtex.args = '{args}'
    rbtex.instance = '{instance}'
    rbtex.line = '{line}'
    
    puts '{stdoutdelim}'
    $stderr.puts '{stderrdelim}'
    rbtex.before
    
    {code}
    
    rbtex.after
    '''

CodeEngine('ruby', 'ruby', '.rb', '{ruby} {file}.rb', ruby_template, 
              ruby_wrapper, 'puts rbtex.formatter({code})', 
              ['Error)', '(Errno', 'error'], 'warning:', ':{number}:')

SubCodeEngine('ruby', 'rb')




julia_template = '''
    # -*- coding: UTF-8 -*-
    
    # Currently, Julia only supports UTF-8
    # So can't set stdout and stderr encoding
    
    type JuliaTeXUtils
        id::String
        family::String
        session::String
        restart::String
        command::String
        context::Dict
        args::String
        instance::String
        line::String
        
        _dependencies::Array{{String}}
        _created::Array{{String}}
        docdir::String
        _context_raw::String
        
        formatter::Function
        before::Function
        after::Function
        add_dependencies::Function
        add_created::Function
        set_context::Function
        pt_to_in::Function
        pt_to_cm::Function
        pt_to_mm::Function
        pt_to_bp::Function
        cleanup::Function
        
        self::JuliaTeXUtils
        
        function JuliaTeXUtils()
            self = new()
            self.self = self
            self._dependencies = Array(String, 0)
            self._created = Array(String, 0)
            self._context_raw = ""
            
            function formatter(expr)
                string(expr)
            end
            self.formatter = formatter
            
            function null()
            end
            self.before = null
            self.after = null
            
            function add_dependencies(files...)
                for file in files
                    push!(self._dependencies, file)
                end
            end
            self.add_dependencies = add_dependencies
            function add_created(files...)
                for file in files
                    push!(self._created, file)
                end
            end
            self.add_created = add_created
            
            function set_context(expr)
                if expr != "" && expr != self._context_raw
                    self.context = {{strip(x[1]) => strip(x[2]) for x in map(x -> split(x, "="), split(expr, ","))}}
                    self._context_raw = expr
                end
            end
            self.set_context = set_context
            
            function pt_to_in(expr)
                if isa(expr, String)
                    if sizeof(expr) > 2 && expr[end-1:end] == "pt"
                        expr = expr[1:end-2]
                    end
                    return float(expr)/72.27
                else
                    return expr/72.27
                end
            end
            self.pt_to_in = pt_to_in
            
            function pt_to_cm(expr)
                return self.pt_to_in(expr)*2.54
            end
            self.pt_to_cm = pt_to_cm
            
            function pt_to_mm(expr)
                return self.pt_to_in(expr)*25.4
            end
            self.pt_to_mm = pt_to_mm
            
            function pt_to_bp(expr)
                return self.pt_to_in(expr)*72
            end
            self.pt_to_bp = pt_to_bp
                        
            function cleanup()
                println("{dependencies_delim}")
                for f in self._dependencies
                    println(f)
                end
                println("{created_delim}")
                for f in self._created
                    println(f)
                end
            end
            self.cleanup = cleanup
            
            return self
        end
    end
    
    jltex = JuliaTeXUtils()
    
    jltex.docdir = pwd()
    println(jltex.docdir)
    try
        cd("{workingdir}")
        if !(in(pwd(), LOAD_PATH))
            push!(LOAD_PATH, pwd())
        end
    catch
        if !(length(ARGS) > 0 && ARGS[1] == "--manual")
            error("Could not find directory {workingdir}")
        end
    end
    if !(in(jltex.docdir, LOAD_PATH))
        push!(LOAD_PATH, jltex.docdir)
    end 
    
    {extend}
    
    jltex.id = "{family}_{session}_{restart}"
    jltex.family = "{family}"
    jltex.session = "{session}"
    jltex.restart = "{restart}"
    
    {body}
    
    jltex.cleanup()
    '''

julia_wrapper = '''
    jltex.command = "{command}"
    jltex.set_context("{context}")
    jltex.args = "{args}"
    jltex.instance = "{instance}"   
    jltex.line = "{line}"
    
    println("{stdoutdelim}")
    write(STDERR, "{stderrdelim}\\n")
    jltex.before()   
    
    {code}
    
    jltex.after()
    '''

CodeEngine('julia', 'julia', '.jl', '{julia} "{file}.jl"', julia_template, 
              julia_wrapper, 'println(jltex.formatter({code}))', 
              'ERROR:', 'WARNING:', ':{number}', True)

SubCodeEngine('julia', 'jl')


octave_template = '''
    cd '{Workingdir}';
    
    {extend}
    
    global octavetex = struct();
    octavetex.dependencies = {{}};
    octavetex.created = {{}};
    octavetex._context_raw = '';
    
    function octavetex_formatter(argin)
        disp(argin);
    end
    
    function octavetex_before()
    end
    
    function octavetex_after()
    end
    
    function octavetex_add_dependencies(varargin)
        global octavetex;
        for i = 1:length(varargin)
            octavetex.dependencies{{end+1}} = varargin{{i}};
        end
    end
    
    function octavetex_add_created(varargin)
        global octavetex;
        for i = 1:length(varargin)
            octavetex.created{{end+1}} = varargin{{i}};
        end
    end
    
    function octavetex_set_context(argin)
        global octavetex;
        if ~strcmp(argin, octavetex._context_raw)
            octavetex._context_raw = argin;
            hash = struct;
            argin_kv = strsplit(argin, ',');
            for i = 1:length(argin_kv)
                kv = strsplit(argin_kv{{i}}, '=');
                k = strtrim(kv{{1}});
                v = strtrim(kv{{2}});
                hash = setfield(hash, k, v);
            end
            octavetex.context = hash;
        end
    end
    
    function out = octavetex_pt_to_in(argin)
        if ischar(argin)
            if length(argin) > 2 && argin(end-1:end) == 'pt'
                out = str2num(argin(1:end-2))/72.27;
            else
                out = str2num(argin)/72.27;
            end
        else
            out = argin/72.27;
        end
    end
    
    function out = octavetex_pt_to_cm(argin)
        out = octavetex_pt_to_in(argin)*2.54;
    end
    
    function out = octavetex_pt_to_mm(argin)
        out = octavetex_pt_to_in(argin)*25.4;
    end
    
    function out = octavetex_pt_to_bp(argin)
        out = octavetex_pt_to_in(argin)*72;
    end
    
    function octavetex_cleanup()
        global octavetex;
        fprintf(strcat('{dependencies_delim}', "\\n"));
        for i = 1:length(octavetex.dependencies)
            fprintf(strcat(octavetex.dependencies{{i}}, "\\n"));
        end
        fprintf(strcat('{created_delim}', "\\n"));
        for i = 1:length(octavetex.created)
            fprintf(strcat(octavetex.created{{i}}, "\\n"));
        end        
    end
    
    octavetex.id = '{family}_{session}_{restart}';
    octavetex.family = '{family}';
    octavetex.session = '{session}';
    octavetex.restart = '{restart}';
    
    {body}

    octavetex_cleanup()    
    '''

octave_wrapper = '''
    octavetex.command = '{command}';
    octavetex_set_context('{context}');
    octavetex.args = '{args}';
    octavetex.instance = '{instance}';
    octavetex.line = '{line}';
    
    octavetex_before()   
    
    fprintf(strcat('{stdoutdelim}', "\\n"));
    fprintf(stderr, strcat('{stderrdelim}', "\\n"));
    {code}
    
    octavetex_after()
    '''

CodeEngine('octave', 'octave', '.m',
           '{octave} -q "{File}.m"', 
           octave_template, octave_wrapper, 'disp({code})',
           'error', 'warning', 'line {number}')

########NEW FILE########
__FILENAME__ = pythontex_install_texlive
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Install PythonTeX

This installation script should work with most TeX distributions.  It is 
primarily written for TeX Live.  It should work with other TeX distributions 
that use the Kpathsea library (such as MiKTeX), though with reduced 
functionality in some cases.  It will require manual input when used with a 
distribution that does not include Kpathsea.

The script will overwrite (and thus update) all previously installed PythonTeX 
files.  When Kpathsea is available, files may be installed in TEXMFDIST,
TEXMFHOME, or a manually specified location.  Otherwise, the installation 
location must be specified manually.  Installing in TEXMFDIST is useful if
you want to install PythonTeX and then update it in the future from CTAN.
The mktexlsr command is executed at the end of the script, to make the system 
aware of any new files.

The script attempts to create a binary wrapper (Windows) or symlink 
(Linux and OS X) for launching the main PythonTeX scripts, pythontex*.py and
depythontex*.py.


Copyright (c) 2012-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
import sys
import platform
from os import path, mkdir, makedirs
if platform.system() != 'Windows':
    # Only create symlinks if not under Windows 
    # (os.symlink doesn't exist under Windows)
    from os import symlink, chmod, unlink
from subprocess import call, check_call, check_output
from shutil import copy
import textwrap


# We need a version of input that works under both Python 2 and 3
try:
    input = raw_input
except:
    pass


# Print startup messages and warnings
print('Preparing to install PythonTeX')
if platform.system() != 'Windows':
    message = '''
              You may need to run this script with elevated permissions
              and/or specify the environment.  For example, you may need
              "sudo env PATH=$PATH".  That is typically necessary when your
              system includes a TeX distribution, and you have manually
              installed another distribution (common with Ubuntu etc.).  If 
              the installation path you want is not automatically detected, 
              it may indicate a permissions issue.              
              '''
    print(textwrap.dedent(message))


# Make sure all necessary files are present
# The pythontex_gallery and pythontex_quickstart are optional; we check for them when installing doc
needed_files = ['pythontex.py', 'pythontex2.py', 'pythontex3.py',
                'pythontex_engines.py', 'pythontex_utils.py',
                'depythontex.py', 'depythontex2.py', 'depythontex3.py',
                'pythontex.sty', 'pythontex.ins', 'pythontex.dtx', 
                'pythontex.pdf', 'README']
missing_files = False
# Print a list of all files that are missing, and exit if any are
for eachfile in needed_files:
    if not path.exists(eachfile):
        print('Could not find file ' + eachfile)
        missing_files = True
if missing_files:
    print('Exiting.')
    sys.exit(1)


# Retrieve the location of valid TeX trees
# Attempt to use kpsewhich; otherwise, resort to manual input 
should_exit = False  # Can't use sys.exit() in try; will trigger except
try:
    if sys.version_info[0] == 2:
        texmf_dist = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).rstrip('\r\n')
        texmf_local = check_output(['kpsewhich', '-var-value', 'TEXMFLOCAL']).rstrip('\r\n')
        texmf_home = check_output(['kpsewhich', '-var-value', 'TEXMFHOME']).rstrip('\r\n')
    else:
        texmf_dist = check_output(['kpsewhich', '-var-value', 'TEXMFDIST']).decode('utf-8').rstrip('\r\n')
        texmf_local = check_output(['kpsewhich', '-var-value', 'TEXMFLOCAL']).decode('utf-8').rstrip('\r\n')
        texmf_home = check_output(['kpsewhich', '-var-value', 'TEXMFHOME']).decode('utf-8').rstrip('\r\n')
    message = '''
              Choose an installation location.
              
              TEXMFDIST is a good choice if you want to update PythonTeX 
              in the future using your TeX distribution's package manager.
              
                1. TEXMFDIST
                     {0}
                2. TEXMFLOCAL
                     {1}
                3. TEXMFHOME
                     {2}
                4. Manual location
              '''.format(texmf_dist, texmf_local, texmf_home)
    print(textwrap.dedent(message))
    path_choice = input('Installation location (number):  ')
    if path_choice not in ('1', '2', '3', '4'):
        should_exit = True
    else:
        if path_choice == '1':
            texmf_path = texmf_dist
        elif path_choice == '2':
            texmf_path = texmf_local
        elif path_choice == '3':
            texmf_path = texmf_home
        else:
            texmf_path = input('Enter a path:\n')
except:
    print('Cannot automatically find TEXMF paths.')
    print('kpsewhich does not exist or could not be used.')
    # Need to create the variable that tracks the type of installation
    path_choice = '4'
    texmf_path = input('Please enter a valid installation path:\n')
if should_exit:
    sys.exit()
# Make sure path slashes are compatible with the operating system
# Kpathsea returns forward slashes, but Windows needs back slashes
texmf_path = path.expandvars(path.expanduser(path.normcase(texmf_path)))

# Check to make sure the path is valid 
# This is only really needed for manual input 
# The '' check is for empty manual input
if texmf_path == '' or not path.exists(texmf_path):
    print('Invalid installation path.  Exiting.')
    sys.exit(1)
    

# Now check that all other needed paths are present
if path_choice != '2':
    doc_path = path.join(texmf_path, 'doc', 'latex')
    package_path = path.join(texmf_path, 'tex', 'latex')
    scripts_path = path.join(texmf_path, 'scripts')
    source_path = path.join(texmf_path, 'source', 'latex')
else:
    doc_path = path.join(texmf_path, 'doc', 'latex', 'local')
    package_path = path.join(texmf_path, 'tex', 'latex', 'local')
    scripts_path = path.join(texmf_path, 'scripts', 'local')
    source_path = path.join(texmf_path, 'source', 'latex', 'local')
make_paths = False
for eachpath in [doc_path, package_path, scripts_path, source_path]:
    if not path.exists(eachpath):
        if make_paths:
            makedirs(eachpath)
            print('  * Created ' + eachpath)
        else:
            choice = input('Some directories do not exist.  Create them? [y/n]\n')
            if choice not in ('y', 'n'):
                sys.exit('Invalid choice')
            elif choice == 'y':
                make_paths = True
                makedirs(eachpath)
                print('  * Created ' + eachpath)
            else:
                message = '''
                          Paths were not created.  The following will be needed.
                            * {0}
                            * {1}
                            * {2}
                            * {3}
                          
                          Exiting.
                          '''.format(doc_path, package_path, scripts_path, source_path)
                print(textwrap.dedent(message))
                sys.exit()
# Modify the paths by adding the pythontex directory, which will be created
doc_path = path.join(doc_path, 'pythontex')
package_path = path.join(package_path, 'pythontex')
scripts_path = path.join(scripts_path, 'pythontex')
source_path = path.join(source_path, 'pythontex')


# Install files
# Use a try/except in case elevated permissions are needed (Linux and OS X)
print('\nPythonTeX will be installed in \n  ' + texmf_path)
try:
    # Install docs
    if not path.exists(doc_path):
        mkdir(doc_path)
    copy('pythontex.pdf', doc_path)
    copy('README', doc_path)
    for doc in ('pythontex_quickstart.tex', 'pythontex_quickstart.pdf', 
                'pythontex_gallery.tex', 'pythontex_gallery.pdf'):
        if path.isfile(doc):
            copy(doc, doc_path)
        else:
            doc = path.join('..', doc.rsplit('.', 1)[0], doc)
            if path.isfile(doc):
                copy(doc, doc_path)
    # Install package
    if not path.exists(package_path):
        mkdir(package_path)
    copy('pythontex.sty', package_path)
    # Install scripts
    if not path.exists(scripts_path):
        mkdir(scripts_path)
    copy('pythontex.py', scripts_path)
    copy('depythontex.py', scripts_path)
    copy('pythontex_utils.py', scripts_path)
    copy('pythontex_engines.py', scripts_path)
    for ver in [2, 3]:
        copy('pythontex{0}.py'.format(ver), scripts_path)
        copy('depythontex{0}.py'.format(ver), scripts_path)
    # Install source
    if not path.exists(source_path):
        mkdir(source_path)
    copy('pythontex.ins', source_path)
    copy('pythontex.dtx', source_path)
except OSError as e:
    if e.errno == 13:
        print('Insufficient permission to install PythonTeX')
        print('(For example, you may need "sudo", or possibly "sudo env PATH=$PATH")\n')
        sys.exit(1)
    else:
        raise        


# Install binary wrappers, create symlinks, or suggest the creation of 
# wrappers/batch files/symlinks.  This part is operating system dependent.
if platform.system() == 'Windows':
    # If under Windows, we create a binary wrapper if under TeX Live and 
    # otherwise alert the user regarding the need for a wrapper or batch file.
    
    # Assemble the binary path, assuming TeX Live
    # The directory bin/ should be at the same level as texmf
    bin_path = path.join(path.split(texmf_path)[0], 'bin', 'win32') 
    if path.exists(path.join(bin_path, 'runscript.exe')):
        for f in ('pythontex.py', 'depythontex.py'):
            copy(path.join(bin_path, 'runscript.exe'), path.join(bin_path, '{0}.exe'.format(f.rsplit('.')[0])))
        print('\nCreated binary wrapper...')
    else:
        message = '''
                  Could not create a wrapper for launching pythontex.py and 
                  depythontex.py; did not find runscript.exe.  You will need 
                  to create a wrapper manually, or use a batch file.  Sample 
                  batch files are included with the main PythonTeX files.  
                  The wrapper or batch file should be in a location on the 
                  Windows PATH.  The bin/ directory in your TeX distribution 
                  may be a good location.
                  
                  The scripts pythontex.py and depythontex.py are located in 
                  the following directory:
                    {0}
                  '''.format(scripts_path)
        print(textwrap.dedent(message))
else:
    # Optimistically proceed as if every system other than Windows can share
    # one set of code.
    root_path = path.split(texmf_path)[0]
    # Create a list of all possible subdirectories of bin/ for TeX Live
    # Source:  http://www.tug.org/texlive/doc/texlive-en/texlive-en.html#x1-250003.2.1
    texlive_platforms = ['alpha-linux', 'amd64-freebsd', 'amd64-kfreebsd',
                         'armel-linux', 'i386-cygwin', 'i386-freebsd',
                         'i386-kfreebsd', 'i386-linux', 'i386-solaris',
                         'mips-irix', 'mipsel-linux', 'powerpc-aix', 
                         'powerpc-linux', 'sparc-solaris', 'universal-darwin',
                         'x86_64-darwin', 'x86_64-linux', 'x86_64-solaris']
    symlink_created = False
    # Try to create a symlink in the standard TeX Live locations
    for pltfrm in texlive_platforms:
        bin_path = path.join(root_path, 'bin', pltfrm)
        if path.exists(bin_path):
            # Unlink any old symlinks if they exist, and create new ones
            # Not doing this gave permissions errors under Ubuntu
            for f in ('pythontex.py', 'pythontex2.py', 'pythontex3.py',
                      'depythontex.py', 'depythontex2.py', 'depythontex3.py'):
                link = path.join(bin_path, f)
                if path.exists(link):
                    unlink(link)
                symlink(path.join(scripts_path, f), link)
                chmod(link, 0o775)
            symlink_created = True
    
    # If the standard TeX Live bin/ locations didn't work, try the typical 
    # location for MacPorts TeX Live.  This should typically be 
    # /opt/local/bin, but instead of assuming that location, we just climb 
    # two levels up from texmf-dist and then look for a bin/ directory that
    # contains a tex executable.  (For MacPorts, texmf-dist should be at 
    # /opt/local/share/texmf-dist.)
    if not symlink_created and platform.system() == 'Darwin':
        bin_path = path.join(path.split(root_path)[0], 'bin')
        if path.exists(bin_path):
            try:
                # Make sure this bin/ is the bin/ we're looking for, by
                # seeing if pdftex exists
                check_output([path.join(bin_path, 'pdftex'), '--version'])
                # Create symlinks
                for f in ('pythontex.py', 'pythontex2.py', 'pythontex3.py',
                          'depythontex.py', 'depythontex2.py', 'depythontex3.py'):
                    link = path.join(bin_path, f)
                    if path.exists(link):
                        unlink(link)
                    symlink(path.join(scripts_path, f), link)
                    chmod(link, 0o775)
                symlink_created = True
            except:
                pass
    if symlink_created:
        print("\nCreated symlink in Tex's bin/ directory...")
    else:
        print('\nCould not automatically create a symlink to pythontex*.py and depythontex*.py.')
        print('You may wish to create one manually, and make it executable via chmod.')
        print('The scripts pythontex*.py and depythontex*.py are located in the following directory:')
        print('    ' + scripts_path)


# Alert TeX to the existence of the package via mktexlsr
try:
    print('\nRunning mktexlsr to make TeX aware of new files...')
    check_call(['mktexlsr'])
except: 
    print('Could not run mktexlsr.')
    print('Your system may not be aware of newly installed files.')


if platform.system() == 'Windows':
    # Pause so that the user can see any errors or other messages
    # input('\n[Press ENTER to exit]')
    print('\n')
    call(['pause'], shell=True)

########NEW FILE########
__FILENAME__ = pythontex_utils
# -*- coding: utf-8 -*-
'''
PythonTeX utilities class for Python scripts.

The utilities class provides variables and methods for the individual 
Python scripts created and executed by PythonTeX.  An instance of the class 
named "pytex" is automatically created in each individual script.

Copyright (c) 2012-2014, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
import sys
import warnings

# Most imports are only needed for SymPy; these are brought in via 
# "lazy import."  Importing unicode_literals here shouldn't ever be necessary 
# under Python 2.  If unicode_literals is imported in the main script, then 
# all strings in this script will be treated as bytes, and the main script 
# will try to decode the strings from this script as necessary.  The decoding 
# shouldn't cause any problems, since all strings in this file may be decoded 
# as valid ASCII. (The actual file is encoded in utf-8, but only characters 
# within the ASCII subset are actually used).


class PythonTeXUtils(object):
    '''
    A class of PythonTeX utilities.
    
    Provides variables for keeping track of TeX-side information, and methods
    for formatting and saving data.
    
    The following variables and methods will be created within instances 
    of the class during execution.
    
    String variables for keeping track of TeX information.  Most are 
    actually needed; the rest are included for completeness.
        * family
        * session
        * restart
        * command
        * context
        * args
        * instance
        * line
    
    Future file handle for output that is saved via macros
        * macrofile
    
    Future formatter function that is used to format output
        * formatter
    '''
    
    def __init__(self, fmtr='str'):
        '''
        Initialize
        '''
        self.set_formatter(fmtr)
    
    # We need a function that will process the raw `context` into a 
    # dictionary with attributes
    _context_raw = None
    class _DictWithAttr(dict):
        pass
    def set_context(self, expr):
        '''
        Convert the string `{context}` into a dict with attributes
        '''
        if not expr or expr == self._context_raw:
            pass
        else:
            self._context_raw = expr
            self.context = self._DictWithAttr()
            k_and_v = [map(lambda x: x.strip(), kv.split('=')) for kv in expr.split(',')]
            for k, v in k_and_v:
                if v.startswith('!!int '):
                    v = int(float(v[6:]))
                elif v.startswith('!!float '):
                    v = float(v[8:])
                elif v.startswith('!!str '):
                    v = v[6:]
                self.context[k] = v
                setattr(self.context, k, v)
    
    # A primary use for contextual information is to pass dimensions from the
    # TeX side to the Python side.  To make that as convenient as possible,
    # we need some length conversion functions.
    # Conversion reference:  http://tex.stackexchange.com/questions/41370/what-are-the-possible-dimensions-sizes-units-latex-understands
    def pt_to_in(self, expr):
        '''
        Convert points to inches.  Accepts numbers, strings of digits, and 
        strings of digits that end with `pt`.
        '''
        try:
            ans = expr/72.27
        except:
            if expr.endswith('pt'):
                expr = expr[:-2]
            ans = float(expr)/72.27
        return ans
    def pt_to_cm(self, expr):
        '''
        Convert points to centimeters.
        '''
        return self.pt_to_in(expr)*2.54
    def pt_to_mm(self, expr):
        '''
        Convert points to millimeters.
        '''
        return self.pt_to_in(expr)*25.4
    def pt_to_bp(self, expr):
        '''
        Convert points to big (DTP or PostScript) points.
        '''
        return self.pt_to_in(expr)*72
        
    
    # We need a context-aware interface to SymPy's latex printer.  The 
    # appearance of typeset math should depend on where it appears in a 
    # document.  (We will refer to the latex printer, rather than the LaTeX 
    # printer, because the two are separate.  Compare sympy.printing.latex 
    # and sympy.galgebra.latex_ex.)  
    #
    # Creating this interface takes some work.  We don't want to import 
    # anything from SymPy unless it is actually used, to keep things clean and 
    # fast.
    
    # First we create a tuple containing all LaTeX math styles.  These are 
    # the contexts that SymPy's latex printer must adapt to.
    # The style order doesn't matter, but it corresponds to that of \mathchoice
    _sympy_latex_styles = ('display', 'text', 'script', 'scriptscript')
    
    # Create the public functions for the user, and private functions that 
    # they call.  Two layers are necessary, because we need to be able to 
    # redefine the functions that do the actual work, once things are 
    # initialized.  But we don't want to redefine the public functions, since 
    # that could cause problems if the user defines a new function to be one 
    # of the public functions--the user's function would not change when
    # the method was redefined.
    def _sympy_latex(self, expr, **settings):
        self._init_sympy_latex()
        return self._sympy_latex(expr, **settings)
    
    def sympy_latex(self, expr, **settings):
        return self._sympy_latex(expr, **settings)
    
    def _set_sympy_latex(self, style, **kwargs):
        self._init_sympy_latex()
        self._set_sympy_latex(style, **kwargs)
    
    def set_sympy_latex(self, style, **kwargs):
        self._set_sympy_latex(style, **kwargs)
    # Temporary compatibility with deprecated methods
    def init_sympy_latex(self):
        warnings.warn('Method init_sympy_latex() is deprecated; init is now automatic.')
        self._init_sympy_latex()
    
    # Next we create a method that initializes the actual context-aware 
    # interface to SymPy's latex printer.
    def _init_sympy_latex(self):
        '''
        Initialize a context-aware interface to SymPy's latex printer.
        
        This consists of creating the dictionary of settings and creating the 
        sympy_latex method that serves as an interface to SymPy's 
        LatexPrinter.  This last step is actually performed by calling 
        self._make_sympy_latex().
        '''
        # Create dictionaries of settings for different contexts.
        # 
        # Currently, the main goal is to use pmatrix (or an equivalent) 
        # in \displaystyle contexts, and smallmatrix in \textstyle, 
        # \scriptstyle (superscript or subscript), and \scriptscriptstyle
        # (superscript or subscript of a superscript or subscript) 
        # contexts.  Basically, we want matrix size to automatically 
        # scale based on context.  It is expected that additional 
        # customization may prove useful as SymPy's LatexPrinter is 
        # further developed.
        #
        # The 'fold_frac_powers' option is probably the main other 
        # setting that might sometimes be nice to invoke in a 
        # context-dependent manner.
        #
        # In the default settings below, all matrices are set to use 
        # parentheses rather than square brackets.  This is largely a 
        # matter of personal preference.  The use of parentheses is based 
        # on the rationale that parentheses are less easily confused with 
        # the determinant and are easier to write by hand than are square 
        # brackets.  The settings for 'script' and 'scriptscript' are set
        # to those of 'text', since all of these should in general 
        # require a more compact representation of things.
        self._sympy_latex_settings = {'display': {'mat_str': 'pmatrix', 'mat_delim': None},
                                      'text': {'mat_str': 'smallmatrix', 'mat_delim': '('},
                                      'script': {'mat_str': 'smallmatrix', 'mat_delim': '('},
                                      'scriptscript': {'mat_str': 'smallmatrix', 'mat_delim': '('} }
        # Now we create a function for updating the settings.
        #
        # Note that EVERY time the settings are changed, we must call 
        # self._make_sympy_latex().  This is because the _sympy_latex() 
        # method is defined based on the settings, and every time the 
        # settings change, it may need to be redefined.  It would be 
        # possible to define _sympy_latex() so that its definition remained 
        # constant, simply drawing on the settings.  But most common 
        # combinations of settings allow more efficient versions of 
        # _sympy_latex() to be defined.
        def _set_sympy_latex(style, **kwargs):
            if style in self._sympy_latex_styles:
                self._sympy_latex_settings[style].update(kwargs)
            elif style == 'all':
                for s in self._sympy_latex_styles:
                    self._sympy_latex_settings[s].update(kwargs)
            else:
                warnings.warn('Unknown LaTeX math style ' + str(style))
            self._make_sympy_latex()
        self._set_sympy_latex = _set_sympy_latex
        
        # Now that the dictionaries of settings have been created, and 
        # the function for modifying the settings is in place, we are ready 
        # to create the actual interface.
        self._make_sympy_latex()
            
    # Finally, create the actual interface to SymPy's LatexPrinter
    def _make_sympy_latex(self):
        '''
        Create a context-aware interface to SymPy's LatexPrinter class.
        
        This is an interface to the LatexPrinter class, rather than 
        to the latex function, because the function is simply a 
        wrapper for accessing the class and because settings may be 
        passed to the class more easily.
        
        Context dependence is accomplished via LaTeX's \mathchoice macro.  
        This macros takes four arguments:
            \mathchoice{<display>}{<text>}{<script>}{<scriptscript>}
        All four arguments are typeset by LaTeX, and then the appropriate one 
        is actually typeset in the document based on the current style.  This 
        may seem like a very inefficient way of doing things, but this 
        approach is necessary because LaTeX doesn't know the math style at a 
        given point until after ALL mathematics have been typeset.  This is 
        because macros such as \over and \atop change the math style of things 
        that PRECEDE them.  See the following discussion for more information:
            http://tex.stackexchange.com/questions/1223/is-there-a-test-for-the-different-styles-inside-maths-mode
        
        The interface takes optional settings.  These optional 
        settings override the default context-dependent settings.  
        Accomplishing this mixture of settings requires (deep)copying 
        the default settings, then updating the copies with the optional 
        settings.  This leaves the default settings intact, with their 
        original values, for the next usage.
        
        The interface is created in various ways depending on the specific
        combination of context-specific settings.  While a general, static 
        interface could be created, that would involve invoking LatexPrinter 
        four times, once for each math style.  It would also require that 
        LaTeX process a \mathchoice macro for everything returned by 
        _sympy_latex(), which would add more inefficiency.  In practice, there 
        will generally be enough overlap between the different settings, and 
        the settings will be focused enough, that more efficient 
        implementations of _sympy_latex() are possible.
        
        Note that we perform a "lazy import" here.  We don't want to import
        the LatexPrinter unless we are sure to use it, since the import brings
        along a number of other dependencies from SymPy.  We don't want 
        unnecessary overhead from SymPy imports.
        '''
        # sys has already been imported        
        import copy
        try:
            from sympy.printing.latex import LatexPrinter
        except ImportError:
            sys.exit('Could not import from SymPy')
        
        # Go through a number of possible scenarios, to create an efficient 
        # implementation of sympy_latex()
        if all(self._sympy_latex_settings[style] == {} for style in self._sympy_latex_styles):
            def _sympy_latex(expr, **settings):
                '''            
                Deal with the case where there are no context-specific 
                settings.
                '''
                return LatexPrinter(settings).doprint(expr)
        elif all(self._sympy_latex_settings[style] == self._sympy_latex_settings['display'] for style in self._sympy_latex_styles):
            def _sympy_latex(expr, **settings):
                '''
                Deal with the case where all settings are identical, and thus 
                the settings are really only being used to set defaults, 
                rather than context-specific behavior.
                
                Check for empty settings, so as to avoid deepcopy
                '''
                if not settings:
                    return LatexPrinter(self._sympy_latex_settings['display']).doprint(expr)
                else:
                    final_settings = copy.deepcopy(self._sympy_latex_settings['display'])
                    final_settings.update(settings)
                    return LatexPrinter(final_settings).doprint(expr)
        elif all(self._sympy_latex_settings[style] == self._sympy_latex_settings['text'] for style in ('script', 'scriptscript')):
            def _sympy_latex(expr, **settings):
                '''
                Deal with the case where only 'display' has different settings.
                
                This should be the most common case.
                '''
                if not settings:
                    display = LatexPrinter(self._sympy_latex_settings['display']).doprint(expr)
                    text = LatexPrinter(self._sympy_latex_settings['text']).doprint(expr)
                else:
                    display_settings = copy.deepcopy(self._sympy_latex_settings['display'])
                    display_settings.update(settings)
                    display = LatexPrinter(display_settings).doprint(expr)
                    text_settings = copy.deepcopy(self._sympy_latex_settings['text'])
                    text_settings.update(settings)
                    text = LatexPrinter(text_settings).doprint(expr)
                if display == text:
                    return display
                else:
                    return r'\mathchoice{' + display + '}{' + text + '}{' + text + '}{' + text + '}'
        else:
            def _sympy_latex(expr, **settings):
                '''
                If all attempts at simplification fail, create the most 
                general interface.
                
                The main disadvantage here is that LatexPrinter is invoked 
                four times and we must create many temporary variables.
                '''
                if not settings:
                    display = LatexPrinter(self._sympy_latex_settings['display']).doprint(expr)
                    text = LatexPrinter(self._sympy_latex_settings['text']).doprint(expr)
                    script = LatexPrinter(self._sympy_latex_settings['script']).doprint(expr)
                    scriptscript = LatexPrinter(self._sympy_latex_settings['scriptscript']).doprint(expr)
                else:
                    display_settings = copy.deepcopy(self._sympy_latex_settings['display'])
                    display_settings.update(settings)
                    display = LatexPrinter(display_settings).doprint(expr)
                    text_settings = copy.deepcopy(self._sympy_latex_settings['text'])
                    text_settings.update(settings)
                    text = LatexPrinter(text_settings).doprint(expr)
                    script_settings = copy.deepcopy(self._sympy_latex_settings['script'])
                    script_settings.update(settings)
                    script = LatexPrinter(script_settings).doprint(expr)
                    scriptscript_settings = copy.deepcopy(self._sympy_latex_settings['scripscript'])
                    scriptscript_settings.update(settings)
                    scriptscript = LatexPrinter(scriptscript_settings).doprint(expr)
                if display == text and display == script and display == scriptscript:
                    return display
                else:
                    return r'\mathchoice{' + display + '}{' + text + '}{' + script + '}{' + scriptscript+ '}'
        self._sympy_latex = _sympy_latex
    
    # Now we are ready to create non-SymPy formatters and a method for 
    # setting formatters
    def identity_formatter(self, expr):
        '''
        For generality, we need an identity formatter, a formatter that does
        nothing to its argument and simply returns it unchanged.
        '''
        return expr
    
    def set_formatter(self, fmtr='str'):
        '''
        Set the formatter method.
        
        This is used to process output that is brought in via macros.  It is 
        also available for the user in formatting printed or saved output.
        '''
        if fmtr == 'str':
            if sys.version_info[0] == 2:
                self.formatter = unicode
            else:
                self.formatter = str
        elif fmtr == 'sympy_latex':
            self.formatter = self.sympy_latex
        elif fmtr in ('None', 'none', 'identity') or fmtr is None:
            self.formatter = self.identity_formatter
        else:
            raise ValueError('Unsupported formatter type')
    
    # We need functions that can be executed immediately before and after
    # each chunk of code.  By default, these should do nothing; they are for
    # user customization, or customization via packages.
    def before(self):
        pass
    def after(self):
        pass
    
    
    # We need a way to keep track of dependencies
    # We create a list that stores specified dependencies, and a method that
    # adds dependencies to the list.  The contents of this list must be 
    # written to stdout at the end of the file, to be transmitted back to the 
    # main script.  So we create a method that prints them to stdout.  This is
    # called via a generic cleanup method that is always invoked at the end of 
    # the script.
    _dependencies = list()
    def add_dependencies(self, *args):
        self._dependencies.extend(list(args))
    def _save_dependencies(self):
        print('=>PYTHONTEX:DEPENDENCIES#')
        if self._dependencies:
            for dep in self._dependencies:
                print(dep)
    
    # We need a way to keep track of created files, so that they can be 
    # automatically cleaned up.  By default, all files are created within the
    # pythontex-files_<jobname> folder, and are thus contained.  If a custom
    # working directory is used, or files are otherwise created in a custom
    # location, it may be desirable to track them and keep them cleaned up.
    # Furthermore, even when files are contained in the default directory, it
    # may be desirable to delete files when they are no longer needed due to
    # program changes, renaming, etc.
    _created = list()
    def add_created(self, *args):
        self._created.extend(list(args))
    def _save_created(self):
        print('=>PYTHONTEX:CREATED#')
        if self._created:
            for creation in self._created:
                print(creation)
    
    def cleanup(self):
        self._save_dependencies()
        self._save_created()
        

########NEW FILE########
__FILENAME__ = make_pythontex_gallery_html2
# -*- coding: utf8 -*-

'''
This script creates an HTML version of pythontex_gallery.tex, using 
depythontex.  This task could be accomplished manually with little effort,
but that would involve directly modifying pythontex_gallery.tex, which is 
undesirable.

The conversion process involves a few tricks for dealing with image formats
and paths.  These could be unnecessary in a document that is specifically 
written with HTML conversion in mind.  For example, all images could be 
saved in the main document directory (or have their full path specified 
explicitly), all images could be saved in PNG format, and all images could 
have their extension specified in the `\includegraphics` command.

Pandoc doesn't currently deal with all the LaTeX in the gallery file 
correctly, so a few special tweaks are required.
'''

# Imports
#// Python 2
from __future__ import unicode_literals
from io import open
#\\ End Python 2
import os
import re
import subprocess
import shutil


# Script params
encoding = 'utf-8'

# Read in the gallery
f = open('pythontex_gallery.tex', encoding=encoding)
gallery = f.readlines()
f.close()


# Add depythontex package option
# This assumes that the pythontex `\usepackage` is alone
for n, line in enumerate(gallery):
    if re.search(r'\\usepackage.*\{pythontex\}', line):
        if re.search(r'\\usepackage\[', line):
            gallery[n] = re.sub(r'\[(.*)\]', r'[\1, depythontex]', line)
        else:
            gallery[n] = re.sub(r'\\usepackage.*\{pythontex\}', '\\usepackage[depythontex]{pythontex}', line)
        break
# Change the save location and extension of any graphics
# This assumes `\includegraphics` doesn't use explicit extensions
# Also get rid of mdframed frames, because Pandoc can't currently handle their optional arguments
for n, line in enumerate(gallery):
    if 'savefig' in line and re.search(r"savefig\('\w+\.pdf'", line):
        gallery[n] = re.sub(r"savefig\('(\w+)\.pdf'", r"savefig('\1.png'", line)
    if r'\includegraphics' in line and re.search(r'\includegraphics(?:\[.*\])?\{\w+\.pdf\}', line):
        gallery[n] = re.sub(r'\\includegraphics(?:\[.*\])?\{(\w+)\.pdf\}', r'\includegraphics{\1.png}', line)
    if r'\begin{mdframed}' in line:
        gallery[n] = re.sub(r'\\begin\{mdframed\}(?:\[.*\])?', '', line)
    if r'\end{mdframed}' in line:
        gallery[n] = re.sub(r'\\end\{mdframed\}', '', line)


# Create a temp directory and switch to it
os.mkdir('depy_temp')
os.chdir('depy_temp')


# Save the modified version of the gallery
f = open('pythontex_gallery.tex', 'w', encoding=encoding)
f.write(''.join(gallery))
f.close()


# Compile the document with depythontex, and create html
subprocess.call(['pdflatex', '-interaction=nonstopmode', 'pythontex_gallery.tex'])
try:
    subprocess.call(['pythontex', 'pythontex_gallery.tex'])
except:
    subprocess.call(['pythontex.py', 'pythontex_gallery.tex'])
subprocess.call(['pdflatex', '-interaction=nonstopmode', 'pythontex_gallery.tex'])
# Use minted-style listings, because Pandoc currently doesn't support some features of listings' `\lstinline`
try:
    subprocess.call(['depythontex', '-o', 'depythontex_pythontex_gallery.tex', 'pythontex_gallery.tex', '--listing=minted'])
except:
    subprocess.call(['depythontex.py', '-o', 'depythontex_pythontex_gallery.tex', 'pythontex_gallery.tex', '--listing=minted'])
subprocess.call(['pandoc', '--standalone', '--mathjax', 'depythontex_pythontex_gallery.tex', '-o', 'pythontex_gallery.html'])


# Move html and graphics to the main document directory
if os.path.isfile(os.path.join('..', 'pythontex_gallery.html')):
    os.remove(os.path.join('..', 'pythontex_gallery.html'))
shutil.move('pythontex_gallery.html', '..')
graphics_files = os.listdir('pythontex-files-pythontex_gallery')
for file in graphics_files:
    if file.endswith('.png'):
        if os.path.isfile(os.path.join('..', file)):
            os.remove(os.path.join('..', file))
        shutil.move(os.path.join('pythontex-files-pythontex_gallery', file), '..')


# Clean up
os.chdir('..')
shutil.rmtree('depy_temp')

########NEW FILE########
__FILENAME__ = make_pythontex_gallery_html3
# -*- coding: utf8 -*-

'''
This script creates an HTML version of pythontex_gallery.tex, using 
depythontex.  This task could be accomplished manually with little effort,
but that would involve directly modifying pythontex_gallery.tex, which is 
undesirable.

The conversion process involves a few tricks for dealing with image formats
and paths.  These could be unnecessary in a document that is specifically 
written with HTML conversion in mind.  For example, all images could be 
saved in the main document directory (or have their full path specified 
explicitly), all images could be saved in PNG format, and all images could 
have their extension specified in the `\includegraphics` command.

Pandoc doesn't currently deal with all the LaTeX in the gallery file 
correctly, so a few special tweaks are required.
'''

# Imports
#// Python 2
#from __future__ import unicode_literals
#from io import open
#\\ End Python 2
import os
import re
import subprocess
import shutil


# Script params
encoding = 'utf-8'

# Read in the gallery
f = open('pythontex_gallery.tex', encoding=encoding)
gallery = f.readlines()
f.close()


# Add depythontex package option
# This assumes that the pythontex `\usepackage` is alone
for n, line in enumerate(gallery):
    if re.search(r'\\usepackage.*\{pythontex\}', line):
        if re.search(r'\\usepackage\[', line):
            gallery[n] = re.sub(r'\[(.*)\]', r'[\1, depythontex]', line)
        else:
            gallery[n] = re.sub(r'\\usepackage.*\{pythontex\}', '\\usepackage[depythontex]{pythontex}', line)
        break
# Change the save location and extension of any graphics
# This assumes `\includegraphics` doesn't use explicit extensions
# Also get rid of mdframed frames, because Pandoc can't currently handle their optional arguments
for n, line in enumerate(gallery):
    if 'savefig' in line and re.search(r"savefig\('\w+\.pdf'", line):
        gallery[n] = re.sub(r"savefig\('(\w+)\.pdf'", r"savefig('\1.png'", line)
    if r'\includegraphics' in line and re.search(r'\includegraphics(?:\[.*\])?\{\w+\.pdf\}', line):
        gallery[n] = re.sub(r'\\includegraphics(?:\[.*\])?\{(\w+)\.pdf\}', r'\includegraphics{\1.png}', line)
    if r'\begin{mdframed}' in line:
        gallery[n] = re.sub(r'\\begin\{mdframed\}(?:\[.*\])?', '', line)
    if r'\end{mdframed}' in line:
        gallery[n] = re.sub(r'\\end\{mdframed\}', '', line)


# Create a temp directory and switch to it
os.mkdir('depy_temp')
os.chdir('depy_temp')


# Save the modified version of the gallery
f = open('pythontex_gallery.tex', 'w', encoding=encoding)
f.write(''.join(gallery))
f.close()


# Compile the document with depythontex, and create html
subprocess.call(['pdflatex', '-interaction=nonstopmode', 'pythontex_gallery.tex'])
try:
    subprocess.call(['pythontex', 'pythontex_gallery.tex'])
except:
    subprocess.call(['pythontex.py', 'pythontex_gallery.tex'])
subprocess.call(['pdflatex', '-interaction=nonstopmode', 'pythontex_gallery.tex'])
# Use minted-style listings, because Pandoc currently doesn't support some features of listings' `\lstinline`
try:
    subprocess.call(['depythontex', '-o', 'depythontex_pythontex_gallery.tex', 'pythontex_gallery.tex', '--listing=minted'])
except:
    subprocess.call(['depythontex.py', '-o', 'depythontex_pythontex_gallery.tex', 'pythontex_gallery.tex', '--listing=minted'])
subprocess.call(['pandoc', '--standalone', '--mathjax', 'depythontex_pythontex_gallery.tex', '-o', 'pythontex_gallery.html'])


# Move html and graphics to the main document directory
if os.path.isfile(os.path.join('..', 'pythontex_gallery.html')):
    os.remove(os.path.join('..', 'pythontex_gallery.html'))
shutil.move('pythontex_gallery.html', '..')
graphics_files = os.listdir('pythontex-files-pythontex_gallery')
for file in graphics_files:
    if file.endswith('.png'):
        if os.path.isfile(os.path.join('..', file)):
            os.remove(os.path.join('..', file))
        shutil.move(os.path.join('pythontex-files-pythontex_gallery', file), '..')


# Clean up
os.chdir('..')
shutil.rmtree('depy_temp')

########NEW FILE########
__FILENAME__ = pythontex_gallery_2to3
#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Convert PythonTeX scripts from Python 2 to Python 3

It isn't possible to have a single PythonTeX code base, since unicode text 
needs to be supported.  Under Python 2, this means importing unicode_literals 
from __future__, or using the unicode function or "u" prefix.  Under Python 3,
all strings are automatically unicode.

At the same time, the differences between the Python 2 and 3 versions are 
usually very small, involving only a few lines of code.  To keep the code base
unified, while simultaneously fully supporting both Python 2 and 3, the 
following scheme was devised.  The code is written for Python 2.  Whenever 
code is not compatible with Python 3, it is enclosed with the tags 
"#// Python 2" and "#\\ End Python 2" (each on its own line, by itself).  If 
a Python 3 version of the code is needed, it is included between analogous 
tags "#// Python 3" and "#\\ End Python 2".  The Python 3 code is commented 
out with "#", at the same indentation level as the Python 3 tags.

This script creates Python 3 scripts from the original Python 2 scripts 
by commenting out everything between the Python 2 tags, and uncommenting 
everything between the Python 3 tags.  In this way, full compatibility is 
maintained with both Python 2 and 3 while keeping the code base essentially 
unified.  This approach also allows greater customization of version-specific 
code than would be possible if automatic translation with a tool like 2to3 
was required.

Copyright (c) 2012-2013, Geoffrey M. Poore
All rights reserved.
Licensed under the BSD 3-Clause License:
    http://www.opensource.org/licenses/BSD-3-Clause

'''


# Imports
from __future__ import unicode_literals
from io import open
import re


files_to_process = ('make_pythontex_gallery_html2.py', )
encoding = 'utf-8'


def from2to3(list_of_code):
    fixed = []
    in_2 = False
    in_3 = False
    indent = ''
    
    for line in list_of_code:
        if r'#// Python 2' in line:
            in_2 = True
            indent = line.split('#', 1)[0]
        elif r'#\\ End Python 2' in line:
            in_2 = False
        elif r'#// Python 3' in line:
            in_3 = True
            indent = line.split('#', 1)[0]
        elif r'#\\ End Python 3' in line:
            in_3 = False
        elif in_2:
            line = re.sub(indent, indent + '#', line, count=1)
        elif in_3:
            line = re.sub(indent + '#', indent, line, count=1)
        fixed.append(line)
    return fixed
        
        
for file in files_to_process:
    f = open(file, 'r', encoding=encoding)
    converted_code = from2to3(f.readlines())
    f.close()
    f = open(re.sub('2', '3', file), 'w', encoding=encoding)
    f.write(''.join(converted_code))
    f.close()



########NEW FILE########
