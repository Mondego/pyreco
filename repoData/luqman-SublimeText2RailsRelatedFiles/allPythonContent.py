__FILENAME__ = Rails
import sublime, sublime_plugin, os, glob, re
from vendor.inflector import *

# @author Luqman Amjad http://luqmanamjad.com

# Taken from Git Plugin (Changed to detected Rails root)
def rails_root(directory):
  while directory:
    if os.path.exists(os.path.join(directory, 'Rakefile')):
      return directory
    parent = os.path.realpath(os.path.join(directory, os.path.pardir))
    if parent == directory:
      # /.. == /
      return False
    directory = parent
  return False

class RailsRelatedFilesHelper:

  @staticmethod
  def get_directory_listing_without_folders(path):

    files = []
    result = glob.glob(path)

    for _file in result:

      if not os.path.isdir(_file):
        files.append(_file)

    return files

  @staticmethod
  def for_controllers(app_folder, working_directory, base_file_name):

    controller = base_file_name.replace('_controller', '')
    model = Inflector(English).singularize(controller).lower()

    namespace_directory    = RailsRelatedFilesHelper.get_namespace_directory(working_directory)
    working_directory_base = os.path.basename(working_directory)

    if namespace_directory:

      controller = os.path.join(working_directory_base, controller)

    walkers = [
      'app/models/'          + model      + '*',
      'app/models/**/'       + model      + '*',
      'app/helpers/'         + controller + '**',
      'app/helpers/**/'      + controller + '**',
      'app/views/'           + controller + '/**',
      'app/views/**/'        + controller + '/**',
      'test/'                + controller + '**',
      'test/**/'             + controller + '**',
      'spec/'                + controller + '**',
      'spec/**/'             + controller + '**'
    ]

    return RailsRelatedFilesHelper.get_files_while_walking(app_folder, walkers)
  
  @staticmethod
  def for_helpers(app_folder, working_directory, base_file_name):

    helper = base_file_name.replace('_helper', '')
    model = Inflector(English).singularize(helper).lower()

    namespace_directory    = RailsRelatedFilesHelper.get_namespace_directory(working_directory)
    working_directory_base = os.path.basename(working_directory)

    if namespace_directory:

      helper = os.path.join(working_directory_base, helper)

    walkers = [
      'app/models/'         + model  + '*',
      'app/models/**/'      + model  + '*',
      'app/controllers/'    + helper + '**',
      'app/controllers/**/' + helper + '**',
      'app/views/'          + helper + '/**',
      'app/views/**/'       + helper + '/**',
      'test/'               + helper + '**',
      'test/**/'            + helper + '**',
      'spec/'               + helper + '**',
      'spec/**/'            + helper + '**'
    ]

    return RailsRelatedFilesHelper.get_files_while_walking(app_folder, walkers)

  @staticmethod
  def for_views(app_folder, working_directory):

    working_directory_base = os.path.basename(working_directory) #if app/views/posts it should return "posts"
    model                  = Inflector(English).singularize(os.path.basename(working_directory_base)).lower() # should return "post"
    namespace_directory    = RailsRelatedFilesHelper.get_namespace_directory(working_directory) #should return none
    controller = model

    if namespace_directory:
      working_directory_base = namespace_directory

      controller = os.path.join(os.path.split(working_directory_base)[0], controller)

    walkers = [
      'app/models/'             + model      + '**',
      'app/models/**/'          + model      + '**',
      'app/views/'              + working_directory_base + '/**',
      'app/helpers/'            + controller + '**',
      'app/helpers/**/'         + controller + '**',
      'app/assets/javascripts/' + model      + '**',
      'app/assets/stylesheets/' + model      + '**',
      'app/controllers/'        + controller + '**',
      'app/controllers/**/'     + controller + '**',
      'test/'                   + controller + '**',
      'test/**/'                + controller + '**',
      'spec/'                   + controller + '**',
      'spec/**/'                + controller + '**'
    ]

    return RailsRelatedFilesHelper.get_files_while_walking(app_folder, walkers)

  @staticmethod
  def for_models(app_folder, working_directory, file_name_base_no_ext):

    model = Inflector(English).singularize(file_name_base_no_ext).lower()
    controller = Inflector(English).pluralize(file_name_base_no_ext).lower()

    walkers = [
      'app/models/'         + model      + '**',
      'app/models/**/'      + model      + '**',
      'app/helpers/'        + controller + '**',
      'app/helpers/**/'     + controller + '**',
      'app/views/'          + controller + '/**',
      'app/views/**/'       + controller + '/**',
      'app/controllers/'    + controller + '**',
      'app/controllers/**/' + controller + '**',
      'test/'               + model      + '**',
      'test/**/'            + model      + '**',
      'spec/'               + model      + '**',
      'spec/**/'            + model      + '**'
    ]

    return RailsRelatedFilesHelper.get_files_while_walking(app_folder, walkers)

  @staticmethod
  def for_tests(app_folder, working_directory, base_file_name):

    if '_controller' in base_file_name:
      controller = base_file_name.replace('_controller', '').replace('_spec', '').replace('_test', '').replace('test_', '')
      model = Inflector(English).singularize(controller).lower()
    else:
      model = base_file_name.replace('_spec', '').replace('test_', '')
      controller = Inflector(English).pluralize(model).lower()

    walkers = [
      'app/controllers/'    + controller + '**',
      'app/controllers/**/' + controller + '**',
      'app/models/'         + model      + '**',
      'app/models/**/'      + model      + '**',
      'app/helpers/'        + controller + '**',
      'app/helpers/**/'     + controller + '**',
      'app/views/'          + controller + '/**',
      'app/views/**/'       + controller + '/**'
    ]

    return RailsRelatedFilesHelper.get_files_while_walking(app_folder, walkers)


  @staticmethod
  def get_app_sub_directory(filename):

    regex = re.compile('(app\/views|app\/controllers|app\/helpers|app\/models|app\/assets|test|spec)')
    match = regex.findall(filename)

    if match:

      return match[0]

    else:

      return

  @staticmethod
  def get_namespace_directory(directory):

    regex = re.compile('(\/app\/views|controllers|helpers|test|spec)\/(.*)') #amazing regex skills...
    match = regex.findall(directory)

    if match:

      return match[0][1]

    else:

      return

  @staticmethod
  def get_files_while_walking(app_folder, walkers):

    files = []

    for walker in walkers:

      files += (
        RailsRelatedFilesHelper().get_directory_listing_without_folders(app_folder + '/' + walker)
      )

    files_without_full_path = []
    for _file in files:

      files_without_full_path += [_file.replace(app_folder + '/', '')]

    return files_without_full_path

class RailsRelatedFilesCommand(sublime_plugin.TextCommand):

  APP_FOLDERS = ['app/controllers', 'app/helpers', 'app/models', 'app/views', 'test', 'spec'] #assets

  def run(self, edit, index):

    if index >= 0:

      self.open_file(index)

    else:

      try:

        self.build_files()
        sublime.active_window().show_quick_panel(self.files, self.open_file)

      except:

        return False

  def is_visible(self, index):

    #return True

    try:

      return self.files[index] and self.show_context_menu

    except: # This should catch all exceptions and return false

      return False

  def open_file(self, index):

    if index >= 0:

      sublime.active_window().open_file(os.path.join(self.rails_root_directory, self.files[index]))

  def build_files(self):

    self.files = []
    self.rails_root_directory = rails_root(self.get_working_dir())

    if self.rails_root_directory:

      self.show_context_menu = sublime.load_settings("Rails.sublime-settings").get('show_context_menu')

      current_file_name      = self._active_file_name()
      working_directory      = self.get_working_dir().replace("\\",'/')
      working_directory_base = os.path.basename(working_directory)

      file_name_base         = os.path.basename(current_file_name)
      file_name_base_no_ext  = os.path.splitext(file_name_base)[0]

      app_sub_directory      = RailsRelatedFilesHelper.get_app_sub_directory(working_directory)

      if app_sub_directory in self.APP_FOLDERS:

        func, args = {
          'app/controllers': (RailsRelatedFilesHelper.for_controllers, (self.rails_root_directory, working_directory, file_name_base_no_ext,)),
          'app/helpers'    : (RailsRelatedFilesHelper.for_helpers,     (self.rails_root_directory, working_directory, file_name_base_no_ext,)),
          'app/views'      : (RailsRelatedFilesHelper.for_views,       (self.rails_root_directory, working_directory,)),
          'app/models'     : (RailsRelatedFilesHelper.for_models,      (self.rails_root_directory, working_directory, file_name_base_no_ext,)),
          'test'           : (RailsRelatedFilesHelper.for_tests,       (self.rails_root_directory, working_directory, file_name_base_no_ext,)),
          'spec'           : (RailsRelatedFilesHelper.for_tests,       (self.rails_root_directory, working_directory, file_name_base_no_ext,))
        }.get(app_sub_directory)

        self.files = func(*args)

        if not self.files:
          self.files = ['Rails Related Files: Nothing found...']


  def description(self, index):
    self.build_files()
    try:
      return self.files[index]
    except IndexError, e:
      return

  # Taken from Git Plugin (Changed .active_view() to .view)
  def _active_file_name(self):
    view = self.view;
    if view and view.file_name() and len(view.file_name()) > 0:
      return view.file_name()

  # Taken from Git Plugin
  def get_working_dir(self):
    file_name = self._active_file_name()
    if file_name:
      return os.path.dirname(file_name)
    else:
      return self.window.folders()[0]


########NEW FILE########
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
# Copyright (c) 2006 Carles SadurnÌ Anguita
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
            ['(?i)([·ÈÌÛ˙])([ns])$', '|1\\2es'],
            ['(?i)(^[bcdfghjklmnÒpqrstvwxyz]*)an$', '\\1anes'], # clan->clanes
            ['(?i)([·ÈÌÛ˙])s$', '|1ses'],
            ['(?i)(^[bcdfghjklmnÒpqrstvwxyz]*)([aeiou])([ns])$', '\\1\\2\\3es'], # tren->trenes
            ['(?i)([aeiou·ÈÛ])$', '\\1s'], # casa->casas, padre->padres, pap·->pap·s
            ['(?i)([aeiou])s$', '\\1s'], # atlas->atlas, virus->virus, etc.
            ['(?i)([ÈÌ])(s)$', '|1\\2es'], # inglÈs->ingleses
            ['(?i)z$', 'ces'],  # luz->luces
            ['(?i)([Ì˙])$', '\\1es'], # ceutÌ->ceutÌes, tab˙->tab˙es
            ['(?i)(ng|[wckgtp])$', '\\1s'], # Anglicismos como puenting, frac, crack, show (En que casos podrÌa fallar esto?)
            ['(?i)$', 'es']	# ELSE +es (v.g. ·rbol->·rboles)
        ]
        
        uncountable_words = ['tijeras','gafas', 'vacaciones','vÌveres','dÈficit']
        ''' In fact these words have no singular form: you cannot say neither
        "una gafa" nor "un vÌvere". So we should change the variable name to
        onlyplural or something alike.'''
        
        irregular_words = {
            'paÌs' : 'paÌses',
            'champ˙' : 'champ˙s',
            'jersey' : 'jersÈis',
            'car·cter' : 'caracteres',
            'espÈcimen' : 'especÌmenes',
            'men˙' : 'men˙s',
            'rÈgimen' : 'regÌmenes',
            'curriculum'  :  'currÌculos',
            'ultim·tum'  :  'ultimatos',
            'memor·ndum'  :  'memorandos',
            'referÈndum'  :  'referendos'
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
                        replacement = replacement.replace('|'+str(k), self.string_replace(groups[k-1], '¡…Õ”⁄·ÈÌÛ˙', 'AEIOUaeiou'))
                
                result = re.sub(rules[rule][0], replacement, word)
                # Esto acentua los sustantivos que al pluralizarse se convierten en esdr˙julos como esmÛquines, jÛvenes...
                match = re.search('(?i)([aeiou]).{1,3}([aeiou])nes$',result)
                
                if match and len(match.groups()) > 1 and not re.search('(?i)[·ÈÌÛ˙]', word) :
                    result = result.replace(match.group(0), self.string_replace(match.group(1), 'AEIOUaeiou', '¡…Õ”⁄·ÈÌÛ˙') + match.group(0)[1:])
                    
                return result
        
        return word


    def singularize (self, word) :
        '''Singularizes Spanish nouns.'''
        
        rules = [
            ['(?i)^([bcdfghjklmnÒpqrstvwxyz]*)([aeiou])([ns])es$', '\\1\\2\\3'],
            ['(?i)([aeiou])([ns])es$',  '~1\\2'],
            ['(?i)oides$',  'oide'], # androides->androide
            ['(?i)(ces)$/i', 'z'],
            ['(?i)(sis|tis|xis)+$',  '\\1'], # crisis, apendicitis, praxis
            ['(?i)(È)s$',  '\\1'], # bebÈs->bebÈ
            ['(?i)([^e])s$',  '\\1'], # casas->casa
            ['(?i)([bcdfghjklmnÒprstvwxyz]{2,}e)s$', '\\1'], # cofres->cofre
            ['(?i)([ghÒpv]e)s$', '\\1'], # 24-01 llaves->llave
            ['(?i)es$', ''] # ELSE remove _es_  monitores->monitor
        ];
    
        uncountable_words = ['paraguas','tijeras', 'gafas', 'vacaciones', 'vÌveres','lunes','martes','miÈrcoles','jueves','viernes','cumpleaÒos','virus','atlas','sms']
        
        irregular_words = {
            'jersey':'jersÈis',
            'espÈcimen':'especÌmenes',
            'car·cter':'caracteres',
            'rÈgimen':'regÌmenes',
            'men˙':'men˙s',
            'rÈgimen':'regÌmenes',
            'curriculum' : 'currÌculos',
            'ultim·tum' : 'ultimatos',
            'memor·ndum' : 'memorandos',
            'referÈndum' : 'referendos',
            's·ndwich' : 's·ndwiches'
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
                        replacement = replacement.replace('~'+str(k), self.string_replace(groups[k-1], 'AEIOUaeiou', '¡…Õ”⁄·ÈÌÛ˙'))
                
                result = re.sub(rules[rule][0], replacement, word)
                # Esta es una posible soluciÛn para el problema de dobles acentos. Un poco guarrillo pero funciona
                match = re.search('(?i)([·ÈÌÛ˙]).*([·ÈÌÛ˙])',result)
                
                if match and len(match.groups()) > 1 and not re.search('(?i)[·ÈÌÛ˙]', word) :
                    result = self.string_replace(result, '¡…Õ”⁄·ÈÌÛ˙', 'AEIOUaeiou')
                
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
