__FILENAME__ = base
#!/usr/bin/env python

# Copyright (c) 2006 Bermi Ferrer Martinez
# bermi a-t bermilabs - com
# See the end of this file for the free software, open source license (BSD-style).

import re

class Base(object):
    '''Locale inflectors must inherit from this base class inorder to provide
    the basic Inflector functionality'''
    
    def conditionalPlural(self, numer_of_records, word) :
        '''Returns the plural form of a word if first parameter is greater than 1'''
        
        if numer_of_records > 1 :
            return self.pluralize(word)
        else :
            return word


    def titleize(self, word, uppercase = '') :
        '''Converts an underscored or CamelCase word into a English sentence.
            The titleize function converts text like "WelcomePage",
            "welcome_page" or  "welcome page" to this "Welcome Page".
            If second parameter is set to 'first' it will only
            capitalize the first character of the title.'''
    
        if(uppercase == 'first'):
            return self.humanize(self.underscore(word)).capitalize()
        else :
            return self.humanize(self.underscore(word)).title()


    def camelize(self, word):
        ''' Returns given word as CamelCased
        Converts a word like "send_email" to "SendEmail". It
        will remove non alphanumeric character from the word, so
        "who's online" will be converted to "WhoSOnline"'''
        return ''.join(w[0].upper() + w[1:] for w in re.sub('[^A-Z^a-z^0-9^:]+', ' ', word).split(' '))
    
    def underscore(self, word) :
        ''' Converts a word "into_it_s_underscored_version"
        Convert any "CamelCased" or "ordinary Word" into an
        "underscored_word".
        This can be really useful for creating friendly URLs.'''
        
        return  re.sub('[^A-Z^a-z^0-9^\/]+','_', \
                re.sub('([a-z\d])([A-Z])','\\1_\\2', \
                re.sub('([A-Z]+)([A-Z][a-z])','\\1_\\2', re.sub('::', '/',word)))).lower()
    
    
    def humanize(self, word, uppercase = '') :
        '''Returns a human-readable string from word
        Returns a human-readable string from word, by replacing
        underscores with a space, and by upper-casing the initial
        character by default.
        If you need to uppercase all the words you just have to
        pass 'all' as a second parameter.'''
        
        if(uppercase == 'first'):
            return re.sub('_id$', '', word).replace('_',' ').capitalize()
        else :
            return re.sub('_id$', '', word).replace('_',' ').title()
    
    
    def variablize(self, word) :
        '''Same as camelize but first char is lowercased
        Converts a word like "send_email" to "sendEmail". It
        will remove non alphanumeric character from the word, so
        "who's online" will be converted to "whoSOnline"'''
        word = self.camelize(word)
        return word[0].lower()+word[1:]
    
    def tableize(self, class_name) :
        ''' Converts a class name to its table name according to rails
        naming conventions. Example. Converts "Person" to "people" '''
        return self.pluralize(self.underscore(class_name))
    
    
    def classify(self, table_name) :
        '''Converts a table name to its class name according to rails
        naming conventions. Example: Converts "people" to "Person" '''
        return self.camelize(self.singularize(table_name))
    
    
    def ordinalize(self, number) :
        '''Converts number to its ordinal English form.
        This method converts 13 to 13th, 2 to 2nd ...'''
        tail = 'th'
        if number % 100 == 11 or number % 100 == 12 or number % 100 == 13:
            tail = 'th'
        elif number % 10 == 1 :
            tail = 'st'
        elif number % 10 == 2 :
            tail = 'nd'
        elif number % 10 == 3 :
            tail = 'rd'
        
        return str(number)+tail
    
    
    def unaccent(self, text) :
        '''Transforms a string to its unaccented version. 
        This might be useful for generating "friendly" URLs'''
        find = u'\u00C0\u00C1\u00C2\u00C3\u00C4\u00C5\u00C6\u00C7\u00C8\u00C9\u00CA\u00CB\u00CC\u00CD\u00CE\u00CF\u00D0\u00D1\u00D2\u00D3\u00D4\u00D5\u00D6\u00D8\u00D9\u00DA\u00DB\u00DC\u00DD\u00DE\u00DF\u00E0\u00E1\u00E2\u00E3\u00E4\u00E5\u00E6\u00E7\u00E8\u00E9\u00EA\u00EB\u00EC\u00ED\u00EE\u00EF\u00F0\u00F1\u00F2\u00F3\u00F4\u00F5\u00F6\u00F8\u00F9\u00FA\u00FB\u00FC\u00FD\u00FE\u00FF'
        replace = u'AAAAAAACEEEEIIIIDNOOOOOOUUUUYTsaaaaaaaceeeeiiiienoooooouuuuyty'
        return self.string_replace(text, find, replace)
    
    def string_replace (self, word, find, replace) :
        '''This function returns a copy of word, translating
        all occurrences of each character in find to the
        corresponding character in replace'''
        for k in range(0,len(find)) :
            word = re.sub(find[k], replace[k], word)
            
        return word
    
    def urlize(self, text) :
        '''Transform a string its unaccented and underscored
        version ready to be inserted in friendly URLs'''
        return re.sub('^_|_$','',self.underscore(self.unaccent(text)))
    
    
    def demodulize(self, module_name) :
        return self.humanize(self.underscore(re.sub('^.*::','',module_name)))
    
    def modulize(self, module_description) :
        return self.camelize(self.singularize(module_description))
    
    def foreignKey(self, class_name, separate_class_name_and_id_with_underscore = 1) :
        ''' Returns class_name in underscored form, with "_id" tacked on at the end. 
        This is for use in dealing with the database.'''
        if separate_class_name_and_id_with_underscore :
            tail = '_id'
        else :
            tail = 'id'
        return self.underscore(self.demodulize(class_name))+tail;



# Copyright (c) 2006 Bermi Ferrer Martinez
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software to deal in this software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of this software, and to permit
# persons to whom this software is furnished to do so, subject to the following
# condition:
#
# THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THIS SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THIS SOFTWARE.

########NEW FILE########
__FILENAME__ = english
#!/usr/bin/env python

# Copyright (c) 2006 Bermi Ferrer Martinez
# bermi a-t bermilabs - com
#
# See the end of this file for the free software, open source license (BSD-style).

import re
from base import Base

class English (Base):
    """
    Inflector for pluralize and singularize English nouns.

    This is the default Inflector for the Inflector obj
    """

    def pluralize(self, word) :
        '''Pluralizes English nouns.'''

        rules = [
            ['(?i)(quiz)$' , '\\1zes'],
            ['^(?i)(ox)$' , '\\1en'],
            ['(?i)([m|l])ouse$' , '\\1ice'],
            ['(?i)(matr|vert|ind)ix|ex$' , '\\1ices'],
            ['(?i)(x|ch|ss|sh)$' , '\\1es'],
            ['(?i)([^aeiouy]|qu)ies$' , '\\1y'],
            ['(?i)([^aeiouy]|qu)y$' , '\\1ies'],
            ['(?i)(hive)$' , '\\1s'],
            ['(?i)(?:([^f])fe|([lr])f)$' , '\\1\\2ves'],
            ['(?i)sis$' , 'ses'],
            ['(?i)([ti])um$' , '\\1a'],
            ['(?i)(buffal|tomat)o$' , '\\1oes'],
            ['(?i)(bu)s$' , '\\1ses'],
            ['(?i)(alias|status)' , '\\1es'],
            ['(?i)(octop|vir)us$' , '\\1i'],
            ['(?i)(ax|test)is$' , '\\1es'],
            ['(?i)s$' , 's'],
            ['(?i)$' , 's']
        ]

        uncountable_words = ['equipment', 'information', 'rice', 'money', 'species', 'series', 'fish', 'sheep']

        irregular_words = {
            'person' : 'people',
            'man' : 'men',
            'child' : 'children',
            'sex' : 'sexes',
            'move' : 'moves'
        }

        lower_cased_word = word.lower();

        for uncountable_word in uncountable_words:
            if lower_cased_word[-1*len(uncountable_word):] == uncountable_word :
                return word

        for irregular in irregular_words.keys():
            match = re.search('('+irregular+')$',word, re.IGNORECASE)
            if match:
                return re.sub('(?i)'+irregular+'$', match.expand('\\1')[0]+irregular_words[irregular][1:], word)

        for rule in range(len(rules)):
            match = re.search(rules[rule][0], word, re.IGNORECASE)
            if match :
                groups = match.groups()
                for k in range(0,len(groups)) :
                    if groups[k] == None :
                        rules[rule][1] = rules[rule][1].replace('\\'+str(k+1), '')

                return re.sub(rules[rule][0], rules[rule][1], word)

        return word


    def singularize (self, word) :
        '''Singularizes English nouns.'''

        rules = [
            ['(?i)(quiz)zes$' , '\\1'],
            ['(?i)(matr)ices$' , '\\1ix'],
            ['(?i)(vert|ind)ices$' , '\\1ex'],
            ['(?i)^(ox)en' , '\\1'],
            ['(?i)(alias|status)es$' , '\\1'],
            ['(?i)([octop|vir])i$' , '\\1us'],
            ['(?i)(cris|ax|test)es$' , '\\1is'],
            ['(?i)(shoe)s$' , '\\1'],
            ['(?i)(o)es$' , '\\1'],
            ['(?i)(bus)es$' , '\\1'],
            ['(?i)([m|l])ice$' , '\\1ouse'],
            ['(?i)(x|ch|ss|sh)es$' , '\\1'],
            ['(?i)(m)ovies$' , '\\1ovie'],
            ['(?i)(s)eries$' , '\\1eries'],
            ['(?i)([^aeiouy]|qu)ies$' , '\\1y'],
            ['(?i)([lr])ves$' , '\\1f'],
            ['(?i)(tive)s$' , '\\1'],
            ['(?i)(hive)s$' , '\\1'],
            ['(?i)([^f])ves$' , '\\1fe'],
            ['(?i)(^analy)ses$' , '\\1sis'],
            ['(?i)((a)naly|(b)a|(d)iagno|(p)arenthe|(p)rogno|(s)ynop|(t)he)ses$' , '\\1\\2sis'],
            ['(?i)([ti])a$' , '\\1um'],
            ['(?i)(n)ews$' , '\\1ews'],
            ['(?i)s$' , ''],
        ];

        uncountable_words = ['equipment', 'information', 'rice', 'money', 'species', 'series', 'fish', 'sheep','sms'];

        irregular_words = {
            'people' : 'person',
            'men' : 'man',
            'children' : 'child',
            'sexes' : 'sex',
            'moves' : 'move'
        }

        lower_cased_word = word.lower();

        for uncountable_word in uncountable_words:
            if lower_cased_word[-1*len(uncountable_word):] == uncountable_word :
                return word

        for irregular in irregular_words.keys():
            match = re.search('('+irregular+')$',word, re.IGNORECASE)
            if match:
                return re.sub('(?i)'+irregular+'$', match.expand('\\1')[0]+irregular_words[irregular][1:], word)


        for rule in range(len(rules)):
            match = re.search(rules[rule][0], word, re.IGNORECASE)
            if match :
                groups = match.groups()
                for k in range(0,len(groups)) :
                    if groups[k] == None :
                        rules[rule][1] = rules[rule][1].replace('\\'+str(k+1), '')

                return re.sub(rules[rule][0], rules[rule][1], word)

        return word



# Copyright (c) 2006 Bermi Ferrer Martinez
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software to deal in this software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of this software, and to permit
# persons to whom this software is furnished to do so, subject to the following
# condition:
#
# THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THIS SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THIS SOFTWARE.

########NEW FILE########
__FILENAME__ = spanish
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2006 Bermi Ferrer Martinez
# Copyright (c) 2006 Carles Sadurní Anguita
#
# bermi a-t bermilabs - com
#
# See the end of this file for the free software, open source license (BSD-style).

import re
from base import Base

class Spanish (Base):
    '''
    Inflector for pluralize and singularize Spanish nouns.
    '''

    def pluralize(self, word) :
        '''Pluralizes Spanish nouns.'''
        rules = [
            ['(?i)([aeiou])x$', '\\1x'], # This could fail if the word is oxytone.
            ['(?i)([áéíóú])([ns])$', '|1\\2es'],
            ['(?i)(^[bcdfghjklmnñpqrstvwxyz]*)an$', '\\1anes'], # clan->clanes
            ['(?i)([áéíóú])s$', '|1ses'],
            ['(?i)(^[bcdfghjklmnñpqrstvwxyz]*)([aeiou])([ns])$', '\\1\\2\\3es'], # tren->trenes
            ['(?i)([aeiouáéó])$', '\\1s'], # casa->casas, padre->padres, papá->papás
            ['(?i)([aeiou])s$', '\\1s'], # atlas->atlas, virus->virus, etc.
            ['(?i)([éí])(s)$', '|1\\2es'], # inglés->ingleses
            ['(?i)z$', 'ces'],  # luz->luces
            ['(?i)([íú])$', '\\1es'], # ceutí->ceutíes, tabú->tabúes
            ['(?i)(ng|[wckgtp])$', '\\1s'], # Anglicismos como puenting, frac, crack, show (En que casos podría fallar esto?)
            ['(?i)$', 'es']	# ELSE +es (v.g. árbol->árboles)
        ]

        uncountable_words = ['tijeras','gafas', 'vacaciones','víveres','déficit']
        ''' In fact these words have no singular form: you cannot say neither
        "una gafa" nor "un vívere". So we should change the variable name to
        onlyplural or something alike.'''

        irregular_words = {
            'país' : 'países',
            'champú' : 'champús',
            'jersey' : 'jerséis',
            'carácter' : 'caracteres',
            'espécimen' : 'especímenes',
            'menú' : 'menús',
            'régimen' : 'regímenes',
            'curriculum'  :  'currículos',
            'ultimátum'  :  'ultimatos',
            'memorándum'  :  'memorandos',
            'referéndum'  :  'referendos'
        }

        lower_cased_word = word.lower();

        for uncountable_word in uncountable_words:
            if lower_cased_word[-1*len(uncountable_word):] == uncountable_word :
                return word

        for irregular in irregular_words.keys():
            match = re.search('(?i)('+irregular+')$',word, re.IGNORECASE)
            if match:
                return re.sub('(?i)'+irregular+'$', match.expand('\\1')[0]+irregular_words[irregular][1:], word)


        for rule in range(len(rules)):
            match = re.search(rules[rule][0], word, re.IGNORECASE)

            if match :
                groups = match.groups()
                replacement = rules[rule][1]
                if re.match('\|', replacement) :
                    for k in range(1, len(groups)) :
                        replacement = replacement.replace('|'+str(k), self.string_replace(groups[k-1], 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'))

                result = re.sub(rules[rule][0], replacement, word)
                # Esto acentua los sustantivos que al pluralizarse se convierten en esdrújulos como esmóquines, jóvenes...
                match = re.search('(?i)([aeiou]).{1,3}([aeiou])nes$',result)

                if match and len(match.groups()) > 1 and not re.search('(?i)[áéíóú]', word) :
                    result = result.replace(match.group(0), self.string_replace(match.group(1), 'AEIOUaeiou', 'ÁÉÍÓÚáéíóú') + match.group(0)[1:])

                return result

        return word


    def singularize (self, word) :
        '''Singularizes Spanish nouns.'''

        rules = [
            ['(?i)^([bcdfghjklmnñpqrstvwxyz]*)([aeiou])([ns])es$', '\\1\\2\\3'],
            ['(?i)([aeiou])([ns])es$',  '~1\\2'],
            ['(?i)oides$',  'oide'], # androides->androide
            ['(?i)(ces)$/i', 'z'],
            ['(?i)(sis|tis|xis)+$',  '\\1'], # crisis, apendicitis, praxis
            ['(?i)(é)s$',  '\\1'], # bebés->bebé
            ['(?i)([^e])s$',  '\\1'], # casas->casa
            ['(?i)([bcdfghjklmnñprstvwxyz]{2,}e)s$', '\\1'], # cofres->cofre
            ['(?i)([ghñpv]e)s$', '\\1'], # 24-01 llaves->llave
            ['(?i)es$', ''] # ELSE remove _es_  monitores->monitor
        ];

        uncountable_words = ['paraguas','tijeras', 'gafas', 'vacaciones', 'víveres','lunes','martes','miércoles','jueves','viernes','cumpleaños','virus','atlas','sms']

        irregular_words = {
            'jersey':'jerséis',
            'espécimen':'especímenes',
            'carácter':'caracteres',
            'régimen':'regímenes',
            'menú':'menús',
            'régimen':'regímenes',
            'curriculum' : 'currículos',
            'ultimátum' : 'ultimatos',
            'memorándum' : 'memorandos',
            'referéndum' : 'referendos',
            'sándwich' : 'sándwiches'
        }

        lower_cased_word = word.lower();

        for uncountable_word in uncountable_words:
            if lower_cased_word[-1*len(uncountable_word):] == uncountable_word :
                return word

        for irregular in irregular_words.keys():
            match = re.search('('+irregular+')$',word, re.IGNORECASE)
            if match:
                return re.sub('(?i)'+irregular+'$', match.expand('\\1')[0]+irregular_words[irregular][1:], word)

        for rule in range(len(rules)):
            match = re.search(rules[rule][0], word, re.IGNORECASE)
            if match :
                groups = match.groups()
                replacement = rules[rule][1]
                if re.match('~', replacement) :
                    for k in range(1, len(groups)) :
                        replacement = replacement.replace('~'+str(k), self.string_replace(groups[k-1], 'AEIOUaeiou', 'ÁÉÍÓÚáéíóú'))

                result = re.sub(rules[rule][0], replacement, word)
                # Esta es una posible solución para el problema de dobles acentos. Un poco guarrillo pero funciona
                match = re.search('(?i)([áéíóú]).*([áéíóú])',result)

                if match and len(match.groups()) > 1 and not re.search('(?i)[áéíóú]', word) :
                    result = self.string_replace(result, 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')

                return result

        return word


# Copyright (c) 2006 Bermi Ferrer Martinez
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software to deal in this software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of this software, and to permit
# persons to whom this software is furnished to do so, subject to the following
# condition:
#
# THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THIS SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THIS SOFTWARE.

########NEW FILE########
__FILENAME__ = recursive_glob
# Inspired by http://stackoverflow.com/a/2186639

import os
import re


def rglob(treeroot, pattern):
    results = []
    for base, dirs, files in os.walk(treeroot):
        goodfiles = filter(lambda x: re.search(pattern, x), files)
        results.extend(os.path.join(base, f) for f in goodfiles)
    return results

########NEW FILE########
__FILENAME__ = SublimeRailsNav
import os
import re
import sublime
import sublime_plugin
from recursive_glob import rglob
from lib.inflector import *


class RailsMixin:
    def get_setting(self, key):
        settings = None
        view = self.window.active_view()

        if view:
            settings = self.window.active_view().settings()

        if settings and settings.has('SublimeRailsNav') and key in settings.get('SublimeRailsNav'):
            # Get project-specific setting
            dirs = settings.get('SublimeRailsNav')[key]
        else:
            # Get user-specific or default setting
            settings = sublime.load_settings('SublimeRailsNav.sublime-settings')
            dirs = settings.get(key)
        return dirs

    def show_files(self, dirs, file_pattern='\.rb$'):
        paths = self.construct_glob_paths(dirs)
        self.find_files(paths, file_pattern)

        view = self.window.active_view()
        if view:
            current_file = view.file_name()
            if self.is_listing_current_file_group(current_file):
                self.remove_from_list(current_file)
            else:
                self.move_related_files_to_top(current_file)

        start_index = len(self.root) + 1
        # Need to add a couple of spaces to avoid getting the file names cut off
        relative_paths = map(lambda x: x[start_index:] + '  ', self.files)

        self.window.show_quick_panel(relative_paths, self.file_selected)

    def rails_root(self):
        # Look for a Gemfile first, since that should always be found in the
        # root directory of a Rails 3 project. If no Gemfile is found, we
        # might have a Rails 2 (or earlier) project, so look for a Rakefile
        # instead. However, since Rakefiles may be found in subdirectories as
        # well, in that case we also check for a number for additional
        # standard Rails directories.
        for root_indicator in ['Gemfile', 'Rakefile']:
            folders = self.window.folders()
            if len(folders) == 0:
                return False

            directory = folders[0]
            while directory:
                if os.path.exists(os.path.join(directory, root_indicator)):
                    if root_indicator == 'Gemfile':
                        return directory
                    else:
                        looks_like_root = True
                        for additional_dir in ['app', 'config', 'lib', 'vendor']:
                            if not (os.path.exists(os.path.join(directory, additional_dir))):
                                looks_like_root = False
                                break
                        if looks_like_root:
                            return directory

                parent = os.path.realpath(os.path.join(directory, os.path.pardir))
                if parent == directory:
                    # /.. == /
                    break
                directory = parent
        return False

    def construct_glob_paths(self, dirs):
        paths = []
        for dir in dirs:
            paths.append(os.path.join(self.root, *dir))
        return paths

    def file_selected(self, selected_index):
        if selected_index != -1:
            if self.window.num_groups() > 1:
                self.window.focus_group((self.window.active_group() + 1) % self.window.num_groups())
            self.window.open_file(self.files[selected_index])

    def find_files(self, paths, file_pattern):
        self.files = []
        for path in paths:
            self.files.extend(rglob(path, file_pattern))

    def remove_from_list(self, current_file):
        # First check to see if the current file is in the list. For instance,
        # if the current file is under vendor/assets/javascripts and we did
        # not include that among the javascript locations that we list,
        # the current file will not in fact be there.
        if current_file in self.files:
            self.files.remove(current_file)
            pass

    def move_related_files_to_top(self, current_file):
        related_file_name_pattern = self.construct_related_file_name_pattern(current_file)

        if related_file_name_pattern:
            for file in self.files:
                if re.search(related_file_name_pattern, file):
                    i = self.files.index(file)
                    self.files.insert(0, self.files.pop(i))


class RailsCommandBase(sublime_plugin.WindowCommand, RailsMixin):
    MODEL_DIR = os.path.join('app', 'models')
    CONTROLLER_DIR = os.path.join('app', 'controllers')
    VIEW_DIR = os.path.join('app', 'views')
    HELPER_DIR = os.path.join('app', 'helpers')
    FIXTURE_DIR = os.path.join('test', 'fixtures')

    def setup(self):
        self.root = self.rails_root()
        if not self.root:
            sublime.error_message('No Rails root directory found. Not a Rails application?')
            return False

        if os.path.isdir(os.path.join(self.root, 'spec')):
            # RSpec seems to be installed, so ignore the 'test' dir and search for specs
            self.test_type = 'spec'
            self.model_test_dir = os.path.join('spec', 'models')
            self.controller_test_dir = os.path.join('spec', 'controllers')
            self.view_test_dir = os.path.join('spec', 'views')
            self.helper_test_dir = os.path.join('spec', 'helpers')
        else:
            # No RSpec, so use the standard 'test' dir
            self.test_type = 'test'
            self.model_test_dir = os.path.join('test', 'unit')
            self.controller_test_dir = os.path.join('test', 'functional')
            self.helper_test_dir = os.path.join('test', 'unit', 'helpers')
        return True

    def construct_related_file_name_pattern(self, current_file):
        pass


class ListRailsModelsCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return
        self.show_files([['app', 'models']])

    def construct_related_file_name_pattern(self, current_file):
        if self.CONTROLLER_DIR in current_file:
            m = re.search(r'(\w+)_controller\.\w+$', current_file)
            singular = Inflector().singularize(m.group(1))

            pattern = re.sub(self.CONTROLLER_DIR, self.MODEL_DIR, current_file)
            pattern = re.sub(r'\w+_controller(\.\w+$)', '%s\g<1>' % singular, pattern)
            return pattern
        elif self.FIXTURE_DIR in current_file:
            m = re.search(r'(\w+)\.yml$', current_file)
            singular = Inflector().singularize(m.group(1))

            pattern = re.sub(self.FIXTURE_DIR, self.MODEL_DIR, current_file)
            pattern = re.sub(r'\w+.yml$', '%s.rb' % singular, pattern)
            return pattern
        elif self.model_test_dir in current_file:
            pattern = re.sub(self.model_test_dir, self.MODEL_DIR, current_file)
            pattern = re.sub(r'(_%s)(.\w+)$' % self.test_type, '\g<2>', pattern)
            return pattern
        else:
            return None

    def is_listing_current_file_group(self, current_file):
        return os.path.join('app', 'models') in current_file


class ListRailsControllersCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return
        self.show_files([['app', 'controllers']])

    def construct_related_file_name_pattern(self, current_file):
        if self.MODEL_DIR in current_file:
            m = re.search(r'(\w+)\.\w+$', current_file)
            plural = Inflector().pluralize(m.group(1))

            pattern = re.sub(self.MODEL_DIR, self.CONTROLLER_DIR, current_file)
            pattern = re.sub(r'\w+(\.\w+)$', '%s_controller\g<1>' % plural, pattern)
            return pattern
        elif self.VIEW_DIR in current_file:
            pattern = re.sub(self.VIEW_DIR, self.CONTROLLER_DIR, current_file)
            pattern = re.sub(os.path.join('', r'(\w+)', r'[\w\.]+$'), '\g<1>_controller', pattern)
            return pattern
        if self.HELPER_DIR in current_file:
            pattern = re.sub(self.HELPER_DIR, self.CONTROLLER_DIR, current_file)
            pattern = re.sub(r'_helper\.rb$', '_controller\.rb', pattern)
            return pattern
        elif self.controller_test_dir in current_file:
            pattern = re.sub(self.controller_test_dir, self.CONTROLLER_DIR, current_file)
            pattern = re.sub(r'(_%s)(.\w+)$' % self.test_type, '\g<2>', pattern)
            return pattern
        else:
            return None

    def is_listing_current_file_group(self, current_file):
        return os.path.join('app', 'controllers') in current_file


class ListRailsViewsCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return
        self.show_files([['app', 'views']], '\.(?:erb|haml|slim)$')

    def construct_related_file_name_pattern(self, current_file):
        if self.CONTROLLER_DIR in current_file:
            pattern = re.sub(self.CONTROLLER_DIR, self.VIEW_DIR, current_file)
            pattern = re.sub(r'(\w+)_controller\.\w+$', '\g<1>' + os.sep, pattern)
            return pattern
        elif self.test_type == 'test' and self.controller_test_dir in current_file:
            # With Test::Unit, view tests are found in the controller test
            # file, so the best we can do is to show all views for the
            # controller associated with the currently active controller test
            # at the top of the list.
            pattern = re.sub(self.controller_test_dir, self.VIEW_DIR, current_file)
            pattern = re.sub(r'(\w+)_controller_test\.rb$', '\g<1>' + os.sep, pattern)
            return pattern
        elif self.test_type == 'spec' and self.view_test_dir in current_file:
            # RSpec uses separate view specs, so here we can show the
            # particular view associated with the currently active spec at the
            # top of the list.
            pattern = re.sub(self.view_test_dir, self.VIEW_DIR, current_file)
            pattern = re.sub(r'(\w+)\.[\w\.]+$', '\g<1>\.', pattern)
            return pattern
        else:
            return None

    def is_listing_current_file_group(self, current_file):
        return os.path.join('app', 'views') in current_file


class ListRailsHelpersCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return
        self.show_files([['app', 'helpers']])

    def construct_related_file_name_pattern(self, current_file):
        if self.CONTROLLER_DIR in current_file:
            pattern = re.sub(self.CONTROLLER_DIR, self.HELPER_DIR, current_file)
            pattern = re.sub(r'_controller\.rb$', '_helper\.rb', pattern)
            return pattern
        elif self.helper_test_dir in current_file:
            pattern = re.sub(self.helper_test_dir, self.HELPER_DIR, current_file)
            pattern = re.sub(r'(_%s)(.\w+)$' % self.test_type, '\g<2>', pattern)
            return pattern
        else:
            return None

    def is_listing_current_file_group(self, current_file):
        return os.path.join('app', 'helpers') in current_file


class ListRailsFixturesCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return
        self.show_files([['test', 'fixtures']], '\.yml$')

    def construct_related_file_name_pattern(self, current_file):
        if self.MODEL_DIR in current_file:
            m = re.search(r'(\w+)\.rb$', current_file)
            plural = Inflector().pluralize(m.group(1))

            pattern = re.sub(self.MODEL_DIR, self.FIXTURE_DIR, current_file)
            pattern = re.sub(r'\w+\.rb$', r'%s\.yml' % plural, pattern)
            return pattern
        elif self.model_test_dir in current_file:
            m = re.search(r'(\w+)_%s\.rb$' % self.test_type, current_file)
            plural = Inflector().pluralize(m.group(1))

            pattern = re.sub(self.model_test_dir, self.FIXTURE_DIR, current_file)
            pattern = re.sub(r'(\w+)_%s\.rb$' % self.test_type, r'%s\.yml' % plural, pattern)
            return pattern
        elif self.controller_test_dir in current_file:
            m = re.search(r'(\w+)_controller_%s\.rb$' % self.test_type, current_file)
            plural = Inflector().pluralize(m.group(1))

            pattern = re.sub(self.controller_test_dir, self.FIXTURE_DIR, current_file)
            pattern = re.sub(r'(\w+)_controller_%s\.rb$' % self.test_type, r'%s\.yml' % plural, pattern)
            return pattern
        else:
            return None

    def is_listing_current_file_group(self, current_file):
        return os.path.join('test', 'fixtures') in current_file


class ListRailsTestsCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return

        self.show_files([[self.test_type]])

    def construct_related_file_name_pattern(self, current_file):
        if self.MODEL_DIR in current_file:
            pattern = re.sub(self.MODEL_DIR, self.model_test_dir, current_file)
            pattern = re.sub(r'(\.\w+)$', '_%s\g<1>' % self.test_type, pattern)
            return pattern
        elif self.CONTROLLER_DIR in current_file:
            pattern = re.sub(self.CONTROLLER_DIR, self.controller_test_dir, current_file)
            pattern = re.sub(r'(\.\w+)$', '_%s\g<1>' % self.test_type, pattern)
            return pattern
        elif self.VIEW_DIR in current_file:
            if self.test_type == 'spec':
                # RSpec uses separate view specs
                pattern = re.sub(self.VIEW_DIR, self.view_test_dir, current_file)
                pattern = re.sub(r'(\w+)\.[\w\.]+$', r'\g<1>[\w\.]*_spec\.rb', pattern)
            else:
                # Test::Unit puts view tests in the controller test file
                pattern = re.sub(self.VIEW_DIR, self.controller_test_dir, current_file)
                pattern = re.sub(r'(\w+)%s[\w\.]+$' % os.sep, '\g<1>_controller_test.rb', pattern)
            return pattern
        elif self.HELPER_DIR in current_file:
            pattern = re.sub(self.HELPER_DIR, self.helper_test_dir, current_file)
            pattern = re.sub(r'\.rb$', r'_%s\.rb' % self.test_type, pattern)
            return pattern
        elif self.FIXTURE_DIR in current_file:
            m = re.search(r'(\w+)\.yml$', current_file)
            singular = Inflector().singularize(m.group(1))

            pattern = re.sub(self.FIXTURE_DIR, r'(?:%s|%s)' % (self.model_test_dir, self.controller_test_dir), current_file)
            pattern = re.sub(r'(\w+)\.yml$', r'(?:\g<1>_controller|%s)_%s\.rb' % (singular, self.test_type), pattern)
            return pattern
        elif 'config/routes.rb' in current_file and self.test_type == 'spec':
            pattern = os.path.join(self.root, 'spec', 'routing', '.+_routing_spec.rb')
            return pattern
        else:
            return None

    def is_listing_current_file_group(self, current_file):
        return os.path.join(self.root, self.test_type) in current_file and not self.FIXTURE_DIR in current_file


class ListRailsJavascriptsCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return
        dirs = self.get_setting('javascript_locations')
        self.show_files(dirs, '\.(?:js|coffee|erb)$')

    def is_listing_current_file_group(self, current_file):
        return 'javascripts' in current_file


class ListRailsStylesheetsCommand(RailsCommandBase):
    def run(self):
        if not self.setup():
            return
        dirs = self.get_setting('stylesheet_locations')
        self.show_files(dirs, '\.(?:s?css|less|sass)$')

    def is_listing_current_file_group(self, current_file):
        return 'stylesheets' in current_file

########NEW FILE########
