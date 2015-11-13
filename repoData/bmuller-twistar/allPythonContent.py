__FILENAME__ = Inflector
#!/usr/bin/env python

# Copyright (c) 2006 Bermi Ferrer Martinez
#
# bermi a-t bermilabs - com
# See the end of this file for the free software, open source license (BSD-style).

import re
from Rules.English import English
from Rules.Spanish import Spanish

class Inflector :
    """
    Inflector for pluralizing and singularizing nouns.
    
    It provides methods for helping on creating programs
    based on naming conventions like on Ruby on Rails.
    """
    
    def __init__( self, Inflector = English ) :
        assert callable(Inflector), "Inflector should be a callable obj"
        self.Inflector = apply(Inflector);
        
    def pluralize(self, word) :
        '''Pluralizes nouns.'''
        return self.Inflector.pluralize(word)
    
    def singularize(self, word) :
        '''Singularizes nouns.'''
        return self.Inflector.singularize(word)
    
    def conditionalPlural(self, numer_of_records, word) :
        '''Returns the plural form of a word if first parameter is greater than 1'''
        return self.Inflector.conditionalPlural(numer_of_records, word)

    def titleize(self, word, uppercase = '') :
        '''Converts an underscored or CamelCase word into a sentence.
            The titleize function converts text like "WelcomePage",
            "welcome_page" or  "welcome page" to this "Welcome Page".
            If the "uppercase" parameter is set to 'first' it will only
            capitalize the first character of the title.'''
        return self.Inflector.titleize(word, uppercase)

    def camelize(self, word):
        ''' Returns given word as CamelCased
        Converts a word like "send_email" to "SendEmail". It
        will remove non alphanumeric character from the word, so
        "who's online" will be converted to "WhoSOnline"'''
        return self.Inflector.camelize(word)
    
    def underscore(self, word) :
        ''' Converts a word "into_it_s_underscored_version"
        Convert any "CamelCased" or "ordinary Word" into an
        "underscored_word".
        This can be really useful for creating friendly URLs.'''
        return self.Inflector.underscore(word)
    
    def humanize(self, word, uppercase = '') :
        '''Returns a human-readable string from word
        Returns a human-readable string from word, by replacing
        underscores with a space, and by upper-casing the initial
        character by default.
        If you need to uppercase all the words you just have to
        pass 'all' as a second parameter.'''
        return self.Inflector.humanize(word, uppercase)
    
    
    def variablize(self, word) :
        '''Same as camelize but first char is lowercased
        Converts a word like "send_email" to "sendEmail". It
        will remove non alphanumeric character from the word, so
        "who's online" will be converted to "whoSOnline"'''
        return self.Inflector.variablize(word)
    
    def tableize(self, class_name) :
        ''' Converts a class name to its table name according to rails
        naming conventions. Example. Converts "Person" to "people" '''
        return self.Inflector.tableize(class_name)
    
    def classify(self, table_name) :
        '''Converts a table name to its class name according to rails
        naming conventions. Example: Converts "people" to "Person" '''
        return self.Inflector.classify(table_name)
    
    def ordinalize(self, number) :
        '''Converts number to its ordinal form.
        This method converts 13 to 13th, 2 to 2nd ...'''
        return self.Inflector.ordinalize(number)
    
    
    def unaccent(self, text) :
        '''Transforms a string to its unaccented version. 
        This might be useful for generating "friendly" URLs'''
        return self.Inflector.unaccent(text)
    
    def urlize(self, text) :
        '''Transform a string its unaccented and underscored
        version ready to be inserted in friendly URLs'''
        return self.Inflector.urlize(text)
    
    
    def demodulize(self, module_name) :
        return self.Inflector.demodulize(module_name)
    
    def modulize(self, module_description) :
        return self.Inflector.modulize(module_description)
    
    def foreignKey(self, class_name, separate_class_name_and_id_with_underscore = 1) :
        ''' Returns class_name in underscored form, with "_id" tacked on at the end. 
        This is for use in dealing with the database.'''
        return self.Inflector.foreignKey(class_name, separate_class_name_and_id_with_underscore)
    



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
__FILENAME__ = Base
#!/usr/bin/env python

# Copyright (c) 2006 Bermi Ferrer Martinez
# bermi a-t bermilabs - com
# See the end of this file for the free software, open source license (BSD-style).

import re

class Base:
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
__FILENAME__ = English
#!/usr/bin/env python

# Copyright (c) 2006 Bermi Ferrer Martinez
# bermi a-t bermilabs - com
#
# See the end of this file for the free software, open source license (BSD-style).

import re
from Base import Base

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
__FILENAME__ = Spanish
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2006 Bermi Ferrer Martinez
# Copyright (c) 2006 Carles Sadurní Anguita
#
# bermi a-t bermilabs - com
#
# See the end of this file for the free software, open source license (BSD-style).

import re
from Base import Base

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
__FILENAME__ = tests
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2006 Bermi Ferrer Martinez
#
# bermi a-t bermilabs - com
#
import unittest
from Inflector import Inflector, English, Spanish

class EnglishInflectorTestCase(unittest.TestCase):
    singular_to_plural = {
        "search"      : "searches",
        "switch"      : "switches",
        "fix"         : "fixes",
        "box"         : "boxes",
        "process"     : "processes",
        "address"     : "addresses",
        "case"        : "cases",
        "stack"       : "stacks",
        "wish"        : "wishes",
        "fish"        : "fish",
    
        "category"    : "categories",
        "query"       : "queries",
        "ability"     : "abilities",
        "agency"      : "agencies",
        "movie"       : "movies",
    
        "archive"     : "archives",
    
        "index"       : "indices",
    
        "wife"        : "wives",
        "safe"        : "saves",
        "half"        : "halves",
    
        "move"        : "moves",
    
        "salesperson" : "salespeople",
        "person"      : "people",
    
        "spokesman"   : "spokesmen",
        "man"         : "men",
        "woman"       : "women",
    
        "basis"       : "bases",
        "diagnosis"   : "diagnoses",
    
        "datum"       : "data",
        "medium"      : "media",
        "analysis"    : "analyses",
    
        "node_child"  : "node_children",
        "child"       : "children",
    
        "experience"  : "experiences",
        "day"         : "days",
    
        "comment"     : "comments",
        "foobar"      : "foobars",
        "newsletter"  : "newsletters",
    
        "old_news"    : "old_news",
        "news"        : "news",
    
        "series"      : "series",
        "species"     : "species",
    
        "quiz"        : "quizzes",
    
        "perspective" : "perspectives",
    
        "ox" : "oxen",
        "photo" : "photos",
        "buffalo" : "buffaloes",
        "tomato" : "tomatoes",
        "dwarf" : "dwarves",
        "elf" : "elves",
        "information" : "information",
        "equipment" : "equipment",
        "bus" : "buses",
        "status" : "statuses",
        "mouse" : "mice",
    
        "louse" : "lice",
        "house" : "houses",
        "octopus" : "octopi",
        "virus" : "viri",
        "alias" : "aliases",
        "portfolio" : "portfolios",
    
        "vertex" : "vertices",
        "matrix" : "matrices",
    
        "axis" : "axes",
        "testis" : "testes",
        "crisis" : "crises",
    
        "rice" : "rice",
        "shoe" : "shoes",
    
        "horse" : "horses",
        "prize" : "prizes",
        "edge" : "edges"
    }
    def setUp(self):
        self.inflector = Inflector(English)
    
    def tearDown(self):
        self.inflector = None

    def test_pluralize(self) :
        for singular in self.singular_to_plural.keys() :
            assert self.inflector.pluralize(singular) == self.singular_to_plural[singular], \
            'English Inlector pluralize(%s) should produce "%s" and NOT "%s"' % (singular, self.singular_to_plural[singular], self.inflector.pluralize(singular))
            
    def test_singularize(self) :
        for singular in self.singular_to_plural.keys() :
            assert self.inflector.singularize(self.singular_to_plural[singular]) == singular, \
            'English Inlector singularize(%s) should produce "%s" and NOT "%s"' % (self.singular_to_plural[singular], singular, self.inflector.singularize(self.singular_to_plural[singular]))



InflectorTestSuite = unittest.TestSuite()
InflectorTestSuite.addTest(EnglishInflectorTestCase("test_pluralize"))
InflectorTestSuite.addTest(EnglishInflectorTestCase("test_singularize"))
runner = unittest.TextTestRunner()
runner.run(InflectorTestSuite)

########NEW FILE########
__FILENAME__ = base
"""
Base module for interfacing with databases.
"""

from twisted.python import log
from twisted.internet import defer

from twistar.registry import Registry        
from twistar.exceptions import ImaginaryTableError, CannotRefreshError

class InteractionBase:
    """
    Class that specific database implementations extend.

    @cvar LOG: If True, then all queries are logged using C{twisted.python.log.msg}.

    @cvar includeBlankInInsert: If True, then insert/update queries will include
    setting object properties that have not be set to null in their respective columns.
    """
    
    LOG = False
    includeBlankInInsert = True


    def __init__(self):
        self.txn = None


    def logEncode(self, s, encoding='utf-8'):
        """
        Encode the given string if necessary for printing to logs.
        """
        if isinstance(s, unicode):
            return s.encode(encoding)
        return str(s)

    
    def log(self, query, args, kwargs):
        """
        Log the query and any args or kwargs using C{twisted.python.log.msg} if
        C{InteractionBase.LOG} is True.
        """
        if not InteractionBase.LOG:
            return
        log.msg("TWISTAR query: %s" % query)
        if len(args) > 0:
            log.msg("TWISTAR args: %s" % ",".join(map(self.logEncode, *args)))
        elif len(kwargs) > 0:
            log.msg("TWISTAR kargs: %s" % str(kwargs))        


    def executeOperation(self, query, *args, **kwargs):
        """
        Simply makes same C{twisted.enterprise.dbapi.ConnectionPool.runOperation} call, but
        with call to L{log} function.
        """
        self.log(query, args, kwargs)
        return Registry.DBPOOL.runOperation(query, *args, **kwargs)


    def execute(self, query, *args, **kwargs):
        """
        Simply makes same C{twisted.enterprise.dbapi.ConnectionPool.runQuery} call, but
        with call to L{log} function.
        """        
        self.log(query, args, kwargs)
        return Registry.DBPOOL.runQuery(query, *args, **kwargs)


    def executeTxn(self, txn, query, *args, **kwargs):
        """
        Execute given query within the given transaction.  Also, makes call
        to L{log} function.
        """        
        self.log(query, args, kwargs)
        return txn.execute(query, *args, **kwargs)


    def select(self, tablename, id=None, where=None, group=None, limit=None, orderby=None, select=None):
        """
        Select rows from a table.

        @param tablename: The tablename to select rows from.

        @param id: If given, only the row with the given id will be returned (or C{None} if not found).

        @param where: Conditional of the same form as the C{where} parameter in L{DBObject.find}.

        @param group: String describing how to group results.

        @param limit: Integer limit on the number of results.  If this value is 1, then the result
        will be a single dictionary.  Otherwise, if C{id} is not specified, an array will be returned.
        This can also be a tuple, where the first value is the integer limit and the second value is
        an integer offset.  In the case that an offset is specified, an array will always be returned.

        @param orderby: String describing how to order the results.

        @param select: Columns to select.  Default is C{*}.

        @return: If C{limit} is 1 or id is set, then the result is one dictionary or None if not found.
        Otherwise, an array of dictionaries are returned.
        """
        one = False
        cacheTableStructure = select is None
        select = select or "*"
        
        if id is not None:
            where = ["id = ?", id]
            one = True

        if not isinstance(limit, tuple) and limit is not None and int(limit) == 1:
            one = True
            
        q = "SELECT %s FROM %s" % (select, tablename)
        args = []
        if where is not None:
            wherestr, args = self.whereToString(where)
            q += " WHERE " + wherestr
        if group is not None:
            q += " GROUP BY " + group
        if orderby is not None:
            q += " ORDER BY " + orderby
            
        if isinstance(limit, tuple):
            q += " LIMIT %s OFFSET %s" % (limit[0], limit[1])
        elif limit is not None:
            q += " LIMIT " + str(limit)
            
        return self.runInteraction(self._doselect, q, args, tablename, one, cacheTableStructure)


    def _doselect(self, txn, q, args, tablename, one=False, cacheable=True):
        """
        Private callback for actual select query call.

        @param cacheable Denotes whether or not we can use the results of this
        query to keep the structure of a table on hand.
        """
        self.executeTxn(txn, q, args)

        if one:
            result = txn.fetchone()
            if not result:
                return None
            vals = self.valuesToHash(txn, result, tablename, cacheable)
            return vals

        results = []
        for result in txn.fetchall():
            vals = self.valuesToHash(txn, result, tablename, cacheable)
            results.append(vals)            
        return results
    

    def insertArgsToString(self, vals):
        """
        Convert C{{'name': value}} to an insert "values" string like C{"(%s,%s,%s)"}.
        """
        return "(" + ",".join(["%s" for _ in vals.items()]) + ")"


    def insert(self, tablename, vals, txn=None):
        """
        Insert a row into the given table.

        @param tablename: Table to insert a row into.
        
        @param vals: Values to insert.  Should be a dictionary in the form of
        C{{'name': value, 'othername': value}}.

        @param txn: If txn is given it will be used for the query,
        otherwise a typical runQuery will be used

        @return: A C{Deferred} that calls a callback with the id of new row.
        """
        params = self.insertArgsToString(vals)
        colnames = ""
        if len(vals) > 0:
            ecolnames = self.escapeColNames(vals.keys())
            colnames = "(" + ",".join(ecolnames) + ")"
            params = "VALUES %s" % params
        q = "INSERT INTO %s %s %s" % (tablename, colnames, params)
        if not txn is None:
            return self.executeTxn(txn, q, vals.values())
        return self.executeOperation(q, vals.values())


    def escapeColNames(self, colnames):
        """
        Escape column names for insertion into SQL statement.

        @param colnames: A C{List} of string column names.

        @return: A C{List} of string escaped column names.
        """
        return map(lambda x: "`%s`" % x, colnames)


    def insertMany(self, tablename, vals):
        """
        Insert many values into a table.

        @param tablename: Table to insert a row into.
        
        @param vals: Values to insert.  Should be a list of dictionaries in the form of
        C{{'name': value, 'othername': value}}.

        @return: A C{Deferred}.
        """
        colnames = ",".join(self.escapeColNames(vals[0].keys()))
        params = ",".join([self.insertArgsToString(val) for val in vals])
        args = []
        for val in vals:
            args = args + val.values()
        q = "INSERT INTO %s (%s) VALUES %s" % (tablename, colnames, params)
        return self.executeOperation(q, args)
        

    def getLastInsertID(self, txn):
        """
        Using the given txn, get the id of the last inserted row.

        @return: The integer id of the last inserted row.
        """
        q = "SELECT LAST_INSERT_ID()"
        self.executeTxn(txn, q)            
        result = txn.fetchall()
        return result[0][0]
    

    def delete(self, tablename, where=None):
        """
        Delete from the given tablename.

        @param where: Conditional of the same form as the C{where} parameter in L{DBObject.find}.
        If given, the rows deleted will be restricted to ones matching this conditional.

        @return: A C{Deferred}.        
        """
        q = "DELETE FROM %s" % tablename
        args = []
        if where is not None:
            wherestr, args = self.whereToString(where)
            q += " WHERE " + wherestr
        return self.executeOperation(q, args)


    def update(self, tablename, args, where=None, txn=None, limit=None):
        """
        Update a row into the given table.

        @param tablename: Table to insert a row into.
        
        @param args: Values to insert.  Should be a dictionary in the form of
        C{{'name': value, 'othername': value}}.

        @param where: Conditional of the same form as the C{where} parameter in L{DBObject.find}.
        If given, the rows updated will be restricted to ones matching this conditional.        

        @param txn: If txn is given it will be used for the query,
        otherwise a typical runQuery will be used

        @param limit: If limit is given it will limit the number of rows that are updated.

        @return: A C{Deferred}
        """
        setstring, args = self.updateArgsToString(args)
        q = "UPDATE %s " % tablename + " SET " + setstring
        if where is not None:
            wherestr, whereargs = self.whereToString(where)
            q += " WHERE " + wherestr
            args += whereargs
        if limit is not None:
            q += " LIMIT " + str(limit)
            
        if txn is not None:
            return self.executeTxn(txn, q, args)
        return self.executeOperation(q, args)


    def valuesToHash(self, txn, values, tablename, cacheable=True):
        """
        Given a row from a database query (values), create
        a hash using keys from the table schema and values from
        the given values;

        @param txn: The transaction to use for the schema update query.

        @param values: A row from a db (as a C{list}).

        @param tablename: Name of the table to fetch the schema for.

        @param cacheable: Can the resulting table structure be cached for
        future reference?
        """
        cols = [row[0] for row in txn.description]
        if cacheable and not Registry.SCHEMAS.has_key(tablename):
            Registry.SCHEMAS[tablename] = cols
        h = {}
        for index in range(len(values)):
            colname = cols[index]
            h[colname] = values[index]
        return h


    def getSchema(self, tablename, txn=None):
        """
        Get the schema (in the form of a list of column names) for
        a given tablename.  Use the given transaction if specified.
        """
        if not Registry.SCHEMAS.has_key(tablename) and txn is not None:
            try:
                self.executeTxn(txn, "SELECT * FROM %s LIMIT 1" % tablename)
            except Exception, e:
                raise ImaginaryTableError, "Table %s does not exist." % tablename
            Registry.SCHEMAS[tablename] = [row[0] for row in txn.description]
        return Registry.SCHEMAS.get(tablename, [])


    def runInteraction(self, interaction, *args, **kwargs):
        if self.txn is not None:
            return defer.succeed(interaction(self.txn, *args, **kwargs))
        return Registry.DBPOOL.runInteraction(interaction, *args, **kwargs)


    def insertObj(self, obj):
        """
        Insert the given object into its table.

        @return: A C{Deferred} that sends a callback the inserted object.
        """
        def _doinsert(txn):
            klass = obj.__class__
            tablename = klass.tablename()
            cols = self.getSchema(tablename, txn)
            if len(cols) == 0:
                raise ImaginaryTableError, "Table %s does not exist." % tablename
            vals = obj.toHash(cols, includeBlank=self.__class__.includeBlankInInsert, exclude=['id'])
            self.insert(tablename, vals, txn)
            obj.id = self.getLastInsertID(txn)
            return obj

        return self.runInteraction(_doinsert)


    def updateObj(self, obj):
        """
        Update the given object's row in the object's table.

        @return: A C{Deferred} that sends a callback the updated object.
        """        
        def _doupdate(txn):
            klass = obj.__class__
            tablename = klass.tablename()
            cols = self.getSchema(tablename, txn)
            
            vals = obj.toHash(cols, includeBlank=True, exclude=['id'])
            return self.update(tablename, vals, where=['id = ?', obj.id], txn=txn)
        # We don't want to return the cursor - so add a blank callback returning the obj
        return self.runInteraction(_doupdate).addCallback(lambda _: obj)


    def refreshObj(self, obj):
        """
        Update the given object based on the information in the object's table.

        @return: A C{Deferred} that sends a callback the updated object.
        """                
        def _dorefreshObj(newobj):
            if obj is None:
                raise CannotRefreshError, "Can't refresh object if id not longer exists."
            for key in newobj.keys():
                setattr(obj, key, newobj[key])
        return self.select(obj.tablename(), obj.id).addCallback(_dorefreshObj)


    def whereToString(self, where):
        """
        Convert a conditional to the form needed for a query using the DBAPI.  For instance,
        for most DB's question marks in the query string have to be converted to C{%s}.  This
        will vary by database.

        @param where: Conditional of the same form as the C{where} parameter in L{DBObject.find}.

        @return: A conditional in the same form as the C{where} parameter in L{DBObject.find}.
        """
        assert(type(where) is list)
        query = where[0].replace("?", "%s")
        args = where[1:]
        return (query, args)


    def updateArgsToString(self, args):
        """
        Convert dictionary of arguments to form needed for DB update query.  This method will
        vary by database driver.
        
        @param args: Values to insert.  Should be a dictionary in the form of
        C{{'name': value, 'othername': value}}.

        @return: A tuple of the form C{('name = %s, othername = %s, ...', argvalues)}.
        """
        colnames = self.escapeColNames(args.keys())
        setstring = ",".join([key + " = %s" for key in colnames])
        return (setstring, args.values())


    def count(self, tablename, where=None):
        """
        Get the number of rows in the given table (optionally, that meet the given where criteria).

        @param tablename: The tablename to count rows from.

        @param where: Conditional of the same form as the C{where} parameter in L{DBObject.find}.

        @return: A C{Deferred} that returns the number of rows.
        """
        d = self.select(tablename, where=where, select='count(*)')
        d.addCallback(lambda res: res[0]['count(*)'])
        return d

########NEW FILE########
__FILENAME__ = mysql
import MySQLdb

from twisted.enterprise import adbapi
from twisted.python import log

from twistar.dbconfig.base import InteractionBase


class MySQLDBConfig(InteractionBase):
    includeBlankInInsert = False

    def insertArgsToString(self, vals):
        if len(vals) > 0:
            return "(" + ",".join(["%s" for _ in vals.items()]) + ")"            
        return "VALUES ()"
    

class ReconnectingMySQLConnectionPool(adbapi.ConnectionPool):
    """
    This connection pool will reconnect if the server goes away.  This idea was taken from:
    http://www.gelens.org/2009/09/13/twisted-connectionpool-revisited/
    """
    def _runInteraction(self, interaction, *args, **kw):
        try:
            return adbapi.ConnectionPool._runInteraction(self, interaction, *args, **kw)
        except MySQLdb.OperationalError, e:
            if e[0] not in (2006, 2013):
                raise
            log.err("Lost connection to MySQL, retrying operation.  If no errors follow, retry was successful.")
            conn = self.connections.get(self.threadID())
            self.disconnect(conn)
            return adbapi.ConnectionPool._runInteraction(self, interaction, *args, **kw)

########NEW FILE########
__FILENAME__ = postgres
from twistar.dbconfig.base import InteractionBase


class PostgreSQLDBConfig(InteractionBase):
    includeBlankInInsert = False

    def getLastInsertID(self, txn):
        q = "SELECT lastval()"
        self.executeTxn(txn, q)
        result = txn.fetchall()
        return result[0][0]


    def insertArgsToString(self, vals):
        if len(vals) > 0:
            return "(" + ",".join(["%s" for _ in vals.items()]) + ")"
        return "DEFAULT VALUES"


    def escapeColNames(self, colnames):
        return map(lambda x: '"%s"' % x, colnames)


    def count(self, tablename, where=None):
        d = self.select(tablename, where=where, select='count(*)')
        d.addCallback(lambda res: res[0]['count'])
        return d

########NEW FILE########
__FILENAME__ = pyodbc
from twistar.registry import Registry
from twistar.dbconfig.base import InteractionBase

class PyODBCDBConfig(InteractionBase):

    def whereToString(self, where):
        assert(type(where) is list)
        query = where[0] #? will be correct
        args = where[1:]
        return (query, args)


    def updateArgsToString(self, args):
        colnames = self.escapeColNames(args.keys())
        setstring = ",".join([key + " = ?" for key in colnames])
        return (setstring, args.values())


    def insertArgsToString(self, vals):
        return "(" + ",".join(["?" for _ in vals.items()]) + ")"

########NEW FILE########
__FILENAME__ = sqlite
from twistar.registry import Registry
from twistar.dbconfig.base import InteractionBase

class SQLiteDBConfig(InteractionBase):
    
    def whereToString(self, where):
        assert(type(where) is list)
        query = where[0] #? will be correct
        args = where[1:]
        return (query, args)


    def getLastInsertID(self, txn):
        q = "SELECT last_insert_rowid()"
        self.executeTxn(txn, q)
        result = txn.fetchall()
        return result[0][0]
                            

    def updateArgsToString(self, args):
        colnames = self.escapeColNames(args.keys())
        setstring = ",".join([key + " = ?" for key in colnames])
        return (setstring, args.values())


    def insertArgsToString(self, vals):
        return "(" + ",".join(["?" for _ in vals.items()]) + ")"

    
    ## retarded sqlite can't handle multiple row inserts
    def insertMany(self, tablename, vals):
        def _insertMany(txn):
            for val in vals:
                self.insert(tablename, val, txn)
        return Registry.DBPOOL.runInteraction(_insertMany)




        

########NEW FILE########
__FILENAME__ = dbobject
"""
Code relating to the base L{DBObject} object.
"""

from twisted.python import log
from twisted.internet import defer

from twistar.registry import Registry
from twistar.relationships import Relationship
from twistar.exceptions import InvalidRelationshipError, DBObjectSaveError, ReferenceNotSavedError
from twistar.utils import createInstances, deferredDict, dictToWhere, transaction
from twistar.validation import Validator, Errors

from BermiInflector.Inflector import Inflector


class DBObject(Validator):
    """
    A base class for representing objects stored in a RDBMS.

    @cvar HASMANY: A C{list} made up of some number of strings and C{dict}s.  If an element is a string,
    it represents what the class has many of, for instance C{'users'}.  If an element is a C{dict}, then
    it should minimally have a C{name} attribute (with a value the same as if the element were a string)
    and then any additional options.  See L{Relationship} and L{HasMany} for more information.

    @cvar HASONE: A C{list} made up of some number of strings and C{dict}s.  If an element is a string,
    it represents what the class has one of, for instance C{'location'}.  If an element is a C{dict}, then
    it should minimally have a C{name} attribute (with a value the same as if the element were a string)
    and then any additional options.  See L{Relationship} and L{HasOne} for more information.

    @cvar HABTM: A C{list} made up of some number of strings and C{dict}s.  If an element is a string,
    it represents what the class has many of (and which in turn has many of this current object type),
    for instance a teacher has and belongs to many students.  Both the C{Student} and C{Teacher} classes
    should have a class variable that is C{HABTM = ['teachers']} and C{HABTM = ['students']}, respectively.
    If an element is a C{dict}, then
    it should minimally have a C{name} attribute (with a value the same as if the element were a string)
    and then any additional options.  See L{Relationship} and L{HABTM} for more information.    

    @cvar BELONGSTO: A C{list} made up of some number of strings and C{dict}s.  If an element is a string,
    it represents what the class belongs to, for instance C{'user'}.  If an element is a C{dict}, then
    it should minimally have a C{name} attribute (with a value the same as if the element were a string)
    and then any additional options.  See L{Relationship} and L{BelongsTo} for more information.

    @cvar TABLENAME: If specified, use the given tablename as the one for this object.  Otherwise,
    use the lowercase, plural version of this class's name.  See the L{DBObject.tablename}
    method.

    @see: L{Relationship}, L{HasMany}, L{HasOne}, L{HABTM}, L{BelongsTo}
    """
    
    HASMANY = []
    HASONE = []
    HABTM = []
    BELONGSTO = []
    
    # this will just be a hash of relationships for faster property resolution
    # the keys are the name and the values are classes representing the relationship
    # it will be of the form {'othername': <BelongsTo instance>, 'anothername': <HasMany instance>}
    RELATIONSHIP_CACHE = None

    def __init__(self, **kwargs):
        """
        Constructor.  DO NOT OVERWRITE.  Use the L{DBObject.afterInit} method.
        
        @param kwargs: An optional dictionary containing the properties that
        should be initially set for this object.

        @see: L{DBObject.afterInit}
        """
        self.id = None
        self._deleted = False
        self.errors = Errors()
        self.updateAttrs(kwargs)
        self._config = Registry.getConfig()

        if self.__class__.RELATIONSHIP_CACHE is None:
            self.__class__.initRelationshipCache()


    def updateAttrs(self, kwargs):
        """
        Set the attributes of this object based on the given C{dict}.

        @param kwargs: A C{dict} whose keys will be turned into properties and whose values
        will then be assigned to those properties.
        """
        for k, v in kwargs.iteritems():
            setattr(self, k, v)


    def save(self):
        """
        Save this object to the database.  Validation is performed first; if the
        validation fails (that is, if C{obj.errors.isEmpty()} is False) then the
        object will not be saved.  To test for errors, use C{obj.errors.isEmpty()}.

        @return: A C{Deferred} object.  If a callback is added to that deferred
        the value of the saved (or unsaved if there are errors) object will be returned.

        @see: L{Validator}, L{Errors}
        """
        if self._deleted:
            raise DBObjectSaveError, "Cannot save a previously deleted object."

        def _save(isValid):
            if self.id is None and isValid:
                return self._create()
            elif isValid:
                return self._update()
            return self
        return self.isValid().addCallback(_save)


    def validate(self):
        """
        Run all validations associated with this object's class.  This will return a deferred
        (actually a C{DeferredList}).  When this deferred is finished, this object's errors
        dictionary property will either be empty or will contain the errors from this object
        (keys are property names, values are the error messages describing the error).
        """
        return self.__class__._validate(self)


    def isValid(self):
        """
        This method first calls L{validate} and then returns a deferred that returns True if
        there were no errors and False otherwise.
        """
        def _isValid(obj):
            return obj.errors.isEmpty()
        return self.validate().addCallback(_isValid)


    def beforeCreate(self):
        """
        Method called before a new object is created.  Classes can overwrite this method.
        If False is returned, then the object is not saved in the database.  This method
        may return a C{Deferred}.
        """


    def beforeUpdate(self):
        """
        Method called before an existing object is updated.  Classes can overwrite this method.
        If False is returned, then the object is not saved in the database.  This method
        may return a C{Deferred}.
        """


    def beforeSave(self):
        """
        Method called before an object is saved.  Classes can overwrite this method.
        If False is returned, then the object is not saved in the database.  This method
        may return a C{Deferred}.

        This method is called after L{beforeCreate} when an object is being created, and after
        L{beforeUpdate} when an existing object (whose C{id} is not C{None}) is being saved.
        """
        

    def afterInit(self):
        """
        Method called when a new L{DBObject} is instantiated as a result of DB queries. If you
        create an instance of this class on your own, you will need to call the method yourself.
        Classes can overwrite this method.  This method may return a C{Deferred}.
        """


    def beforeDelete(self):
        """
        Method called before a L{DBObject} is deleted.  Classes can overwrite this method.
        If False is returned, then the L{DBObject} is not deleted from database.
        This method may return a C{Deferred}.
        """


    def _create(self):
        """
        Method to actually create an object in the DB.  Handles calling this class's
        L{beforeCreate} followed by it's L{beforeSave} method.

        @return: A C{Deferred} object.  If a callback is added to that deferred
        the value of the saved object will be returned (unless the L{beforeCreate}
        or L{beforeSave} methods returns C{False}, in which case the unsaved object
        will be returned).
        """
        def _createOnSuccess(result):
            if result == False:
                return defer.succeed(self)
            return self._config.insertObj(self)

        def _beforeSave(result):
            if result == False:
                return defer.succeed(self)
            return defer.maybeDeferred(self.beforeSave).addCallback(_createOnSuccess)

        return defer.maybeDeferred(self.beforeCreate).addCallback(_beforeSave)


    def _update(self):
        """
        Method to actually save an existing object in the DB.  Handles calling this class's
        L{beforeUpdate} and L{beforeSave} methods.

        @return: A C{Deferred} object.  If a callback is added to that deferred
        the value of the saved object will be returned (unless the L{beforeUpdate}
        or L{beforeSave} methods returns C{False}, in which case the unsaved
        object will be returned).
        """        
        def _saveOnSuccess(result):
            if result == False:
                return defer.succeed(self)
            return self._config.updateObj(self)
        
        def _beforeSave(result):
            if result == False:
                return defer.succeed(self)
            return defer.maybeDeferred(self.beforeSave).addCallback(_saveOnSuccess)
        
        return defer.maybeDeferred(self.beforeUpdate).addCallback(_beforeSave)


    def refresh(self):
        """
        Update the properties for this object from the database.

        @return: A C{Deferred} object.
        """        
        return self._config.refreshObj(self)

               
    def toHash(self, cols, includeBlank=False, exclude=None, base=None):
        """
        Convert this object to a dictionary.

        @param includeBlank: Boolean representing whether or not properties that
        have not been set should be included (the initial property list is retrieved
        from the schema of the database for the given class's schema).

        @param exclue: A C{list} of properties to ignore when creating the C{dict} to
        return.

        @param base: An initial base C{dict} to add this objects properties to.

        @return: A C{dict} formed from the properties and values of this object.
        """
        exclude = exclude or []
        h = base or {}
        for col in cols:
            if col in exclude:
                continue
            value = getattr(self, col, None)
            if (value != None or includeBlank):
                h[col] = value
        return h


    def delete(self):
        """
        Delete this instance from the database.  Calls L{beforeDelete} before deleting from
        the database.

        @return: A C{Deferred}.        
        """

        def _delete(result):
            oldid = self.id
            self.id = None
            self._deleted = True
            return self.__class__.deleteAll(where=["id = ?", oldid])

        def _deleteOnSuccess(result):
            if result == False:
                return defer.succeed(self)
            else:
                ds = []
                for relation in self.HABTM:
                    name = relation['name'] if isinstance(relation, dict) else relation
                    ds.append(getattr(self, name).clear())
                return defer.DeferredList(ds).addCallback(_delete)

        return defer.maybeDeferred(self.beforeDelete).addCallback(_deleteOnSuccess)


    def loadRelations(self, *relations):
        """
        Preload a a list of relationships.  For instance, if you have an instance of an
        object C{User} (named C{user}) that has many C{Address}es and has one C{Avatar},
        you could call C{user.loadRelations('addresses', 'avatar').addCallback('handleUser')}
        instead of having to call C{user.addresses.get()} and C{user.avatar.get()} and assign
        callbacks to the results of those calls.  In the first case, the function C{handleUser}
        would accept one argument, which will be a dictionary whose keys are the property names
        and whose values are the results of the C{get()} calls.  This just makes it easier to
        load multiple properties at once, without having to create a long list of callbacks.

        If the method is called without any arguments, then all relations will loaded.

        @return: A C{Deferred}.
        """
        if len(relations) == 0:
            klass = object.__getattribute__(self, "__class__")
            allrelations = klass.RELATIONSHIP_CACHE.keys()
            if len(allrelations) == 0:
                return defer.succeed({})
            return self.loadRelations(*allrelations)

        ds = {}
        for relation in relations:
            ds[relation] = getattr(self, relation).get()
        return deferredDict(ds)


    @classmethod
    def addRelation(klass, relation, rtype):
        """
        Add a relationship to the given Class.
        
        @param klass: The class extending this one.
        
        @param relation: Either a string with the name of property to create
        for this class or a dictionary decribing the relationship.  For instance,
        if a User L{HasMany} Pictures then the relation could either by 'pictures'
        or a dictionary with at least one "name" key, as in
        C{{'name': 'pictures', ...}} along with other options.

        @param rtype: The relationship type.  It should be a key value from
        the C{TYPES} class variable in the class L{Relationship}.
        """
        if type(relation) is dict:
            if not relation.has_key('name'):
                msg = "No key 'name' in the relation %s in class %s" % (relation, klass.__name__)
                raise InvalidRelationshipError, msg
            name = relation['name']
            args = relation
        else:
            name = relation
            args = {}
        relationshipKlass = Relationship.TYPES[rtype]
        klass.RELATIONSHIP_CACHE[name] = (relationshipKlass, args)


    @classmethod
    def initRelationshipCache(klass):
        """
        Initialize the cache of relationship objects for this class.
        """
        klass.RELATIONSHIP_CACHE = {}        
        for rtype in Relationship.TYPES.keys():
            for relation in getattr(klass, rtype):
                klass.addRelation(relation, rtype)
        

    @classmethod
    def tablename(klass):
        """
        Get the tablename for the given class.  If the class has a C{TABLENAME}
        variable then that will be used - otherwise, it is is inferred from the
        class name.

        @param klass: The class to get the tablename for.
        """
        if not hasattr(klass, 'TABLENAME'):
            inf = Inflector()
            klass.TABLENAME = inf.tableize(klass.__name__)
        return klass.TABLENAME


    @classmethod
    def findOrCreate(klass, **attrs):
        """
        Find all instances of a given class based on the attributes given (just like C{findBy}).

        If a match isn't found, create a new instance and return that.
        """
        @transaction
        def _findOrCreate(trans):
            def handle(result):
                if len(result) == 0:
                    return klass(**attrs).save()
                return result[0]
            return klass.findBy(**attrs).addCallback(handle)
        return _findOrCreate()


    @classmethod
    def findBy(klass, **attrs):
        """
        Find all instances of the given class based on an exact match of attributes.

        For instance:
        C{User.find(first_name='Bob', last_name='Smith')}

        Will return all matches.
        """
        where = dictToWhere(attrs)
        return klass.find(where = where)


    @classmethod
    def find(klass, id=None, where=None, group=None, limit=None, orderby=None):
        """
        Find instances of a given class.

        @param id: The integer of the C{klass} to find.  For instance, C{Klass.find(1)}
        will return an instance of Klass from the row with an id of 1 (unless it isn't
        found, in which case C{None} is returned).

        @param where: A C{list} whose first element is the string version of the
        condition with question marks in place of any parameters.  Further elements
        of the C{list} should be the values of any parameters specified.  For instance,
        C{['first_name = ? AND age > ?', 'Bob', 21]}.

        @param group: A C{str} describing the grouping, like C{group='first_name'}.

        @param limit: An C{int} specifying the limit of the results.  If this is 1,
        then the return value will be either an instance of C{klass} or C{None}.

        @param orderby: A C{str} describing the ordering, like C{orderby='first_name DESC'}.        

        @return: A C{Deferred} which returns the following to a callback:
        If id is specified (or C{limit} is 1) then a single
        instance of C{klass} will be returned if one is found that fits the criteria, C{None}
        otherwise.  If id is not specified and C{limit} is not 1, then a C{list} will
        be returned with all matching results.
        """
        config = Registry.getConfig()
        d = config.select(klass.tablename(), id, where, group, limit, orderby)
        return d.addCallback(createInstances, klass)


    @classmethod
    def count(klass, where=None):
        """
        Count instances of a given class.

        @param where: An optional C{list} whose first element is the string version of the
        condition with question marks in place of any parameters.  Further elements
        of the C{list} should be the values of any parameters specified.  For instance,
        C{['first_name = ? AND age > ?', 'Bob', 21]}.

        @return: A C{Deferred} which returns the total number of db records to a callback.
        """
        config = Registry.getConfig()
        return config.count(klass.tablename(), where=where)


    @classmethod
    def all(klass):
        """
        Get all instances of the given class in the database.  Note that this is the
        equivalent of calling L{find} with no arguments.

        @return: A C{Deferred} which returns the following to a callback:
        A C{list} containing all of the instances in the database.
        """
        return klass.find()


    @classmethod
    def deleteAll(klass, where=None):
        """
        Delete all instances of C{klass} in the database without instantiating the records
        first or invoking callbacks (L{beforeDelete} is not called). This will run a single
        SQL DELETE statement in the database.

        @param where: Conditionally delete instances.  This parameter is of the same form
        found in L{find}.

        @return: A C{Deferred}.        
        """
        config = Registry.getConfig()
        tablename = klass.tablename()
        return config.delete(tablename, where)


    @classmethod
    def exists(klass, where=None):
        """
        Find whether or not at least one instance of the given C{klass} exists, optionally
        with specific conditions specified in C{where}.
        
        @param where: Conditionally find instances.  This parameter is of the same form
        found in L{find}.
        
        @return: A C{Deferred} which returns the following to a callback:
        A boolean as to whether or not at least one object was found.
        """
        def _exists(result):
            return result is not None
        return klass.find(where=where, limit=1).addCallback(_exists)


    def __str__(self):
        """
        Get the string version of this object.
        """
        tablename = self.tablename()
        attrs = {}
        if Registry.SCHEMAS.has_key(tablename):
            for key in Registry.SCHEMAS[tablename]:
                attrs[key] = getattr(self, key, None)
        return "<%s object: %s>" % (self.__class__.__name__, str(attrs))

    
    def __getattribute__(self, name):
        """
        Get the given attribute.

        @param name: The name of the property to get.

        @return: If the name is a relationship based property, then a
        L{Relationship} instance will be returned.  Otherwise the set property
        of the class will be returned.
        """
        klass = object.__getattribute__(self, "__class__")
        if not klass.RELATIONSHIP_CACHE is None and klass.RELATIONSHIP_CACHE.has_key(name):
            if object.__getattribute__(self, 'id') is None:
                raise ReferenceNotSavedError, "Cannot get/set relationship on unsaved object"
            relationshipKlass, args = klass.RELATIONSHIP_CACHE[name]
            return relationshipKlass(self, name, args)
        return object.__getattribute__(self, name)        


    def __eq__(self, other):
        """
        Determine if this object is the same as another (only taking
        the type of the other class and it's C{id} into account).

        @param other: The other object to compare this one to.

        @return: A boolean.
        """
        eqclass = self.__class__.__name__ == other.__class__.__name__
        eqid = hasattr(other, 'id') and self.id == other.id
        return eqclass and eqid


    def __neq__(self, other):
        """
        Determine if this object is not the same as another (only taking
        the type of the other class and it's C{id} into account).

        @param other: The other object to compare this one to.

        @return: A boolean.
        """        
        return not self == other


    def __hash__(self):
        return hash('%s.%d' % (type(self).__name__, self.id))


    __repr__ = __str__


Registry.register(DBObject)

########NEW FILE########
__FILENAME__ = exceptions
"""
All C{Exception} classes.
"""


class TransactionError(Exception):
    """
    Error while running a transaction.
    """


class ClassNotRegisteredError(Exception):
    """
    Error resulting from the attempted fetching of a class from the L{Registry} that was
    never registered.
    """


class ImaginaryTableError(Exception):
    """
    Error resulting from the attempted use of a table that doesn't exist.
    """


class ReferenceNotSavedError(Exception):
    """
    Error resulting from the attempted use of an object as a reference that hasn't been
    saved yet.
    """    


class CannotRefreshError(Exception):
    """
    Error resulting from the attempted refreshing of an object that hasn't been
    saved yet.
    """
    

class InvalidRelationshipError(Exception):
    """
    Error resulting from the misspecification of a relationship dictionary.
    """    


class DBObjectSaveError(Exception):
    """
    Error saving a DBObject.
    """

########NEW FILE########
__FILENAME__ = registry
"""
Module handling global registration of variables and classes.
"""

from twisted.python import reflect

from BermiInflector.Inflector import Inflector

from twistar.exceptions import ClassNotRegisteredError

class Registry:
    """
    A data store containing mostly class variables that act as constants.

    @cvar DBPOOL: This should be set to the C{twisted.enterprise.dbapi.ConnectionPool} to
    use for all database interaction.
    """
    SCHEMAS = {}
    REGISTRATION = {}
    IMPL = None
    DBPOOL = None


    @classmethod
    def register(_, *klasses):
        """
        Register some number of classes in the registy.  This is necessary so that when objects
        are created on the fly (specifically, as a result of relationship C{get}s) the package
        knows how to find them.

        @param klasses: Any number of parameters, each of which is a class.
        """        
        for klass in klasses:
            Registry.REGISTRATION[klass.__name__] = klass


    @classmethod
    def getClass(klass, name):
        """
        Get a registered class by the given name.
        """        
        if not Registry.REGISTRATION.has_key(name):
            raise ClassNotRegisteredError, "You never registered the class named %s" % name
        return Registry.REGISTRATION[name]

    
    @classmethod
    def getDBAPIClass(klass, name):
        """
        Per U{http://www.python.org/dev/peps/pep-0249/} each DBAPI driver must implement it's
        own Date/Time/Timestamp/etc classes.  This method provides a generalized way to get them
        from whatever DB driver is being used.
        """        
        driver = Registry.DBPOOL.dbapi.__name__
        path = "%s.%s" % (driver, name)
        return reflect.namedAny(path)

    
    @classmethod
    def getConfig(klass):
        """
        Get the current DB config object being used for DB interaction.  This is one of the classes
        that extends L{base.InteractionBase}.
        """
        if Registry.IMPL is not None:
            return Registry.IMPL
        
        if Registry.DBPOOL is None:
            msg = "You must set Registry.DBPOOL to a adbapi.ConnectionPool before calling this method."
            raise RuntimeError, msg
        dbapi = Registry.DBPOOL.dbapi
        if dbapi.__name__ == "MySQLdb":
            from twistar.dbconfig.mysql import MySQLDBConfig                        
            Registry.IMPL = MySQLDBConfig()
        elif dbapi.__name__ == "sqlite3":
            from twistar.dbconfig.sqlite import SQLiteDBConfig                        
            Registry.IMPL = SQLiteDBConfig()
        elif dbapi.__name__ == "psycopg2":
            from twistar.dbconfig.postgres import PostgreSQLDBConfig            
            Registry.IMPL = PostgreSQLDBConfig()
        elif dbapi.__name__ == "pyodbc":
            from twistar.dbconfig.pyodbc import PyODBCDBConfig
            Registry.IMPL = PyODBCDBConfig()
        else:
            raise NotImplementedError, "twisteddb does not support the %s driver" % dbapi.__name__
        
        return Registry.IMPL



########NEW FILE########
__FILENAME__ = relationships
"""
Module descripting different types of object relationships.
"""

from twisted.internet import defer

from BermiInflector.Inflector import Inflector

from twistar.registry import Registry
from twistar.utils import createInstances, joinWheres
from twistar.exceptions import ReferenceNotSavedError


class Relationship:
    """
    Base class that all specific relationship type classes extend.

    @see: L{HABTM}, L{HasOne}, L{HasMany}, L{BelongsTo}
    """
    
    def __init__(self, inst, propname, givenargs):
        """
        Constructor.

        @param inst: The L{DBObject} instance.
        
        @param propname: The property name in the L{DBObject} instance that
        results in this class being created.

        @param givenargs: Any arguments given (through the use of a C{dict}
        in the class variable in L{DBObject} rather than a string to describe
        the relationship).  The given args can include, for all relationships,
        a C{class_name}.  Depending on the relationship, C{association_foreign_key}
        and C{foreign_key} might also be used.
        """
        self.infl = Inflector()
        self.inst = inst
        self.dbconfig = Registry.getConfig()

        ## Set args
        self.args = {
            'class_name': propname,
            'association_foreign_key': self.infl.foreignKey(self.infl.singularize(propname)),
            'foreign_key': self.infl.foreignKey(self.inst.__class__.__name__),
            'polymorphic': False
        }
        self.args.update(givenargs)

        otherklassname = self.infl.classify(self.args['class_name'])
        if not self.args['polymorphic']:
            self.otherklass = Registry.getClass(otherklassname)
        self.othername = self.args['association_foreign_key']
        self.thisclass = self.inst.__class__
        self.thisname = self.args['foreign_key']


class BelongsTo(Relationship):
    """
    Class representing a belongs-to relationship.
    """
    
    def get(self):
        """
        Get the object that belong to the caller.

        @return: A C{Deferred} with a callback value of either the matching class or
        None (if not set).
        """
        def get_polymorphic(row):
            kid = getattr(row, "%s_id" % self.args['class_name'])
            kname = getattr(row, "%s_type" % self.args['class_name'])
            return Registry.getClass(kname).find(kid)

        if self.args['polymorphic']:
            return self.inst.find(where=["id = ?", self.inst.id], limit=1).addCallback(get_polymorphic)

        return self.otherklass.find(where=["id = ?", getattr(self.inst, self.othername)], limit=1)


    def set(self, other):
        """
        Set the object that belongs to the caller.

        @return: A C{Deferred} with a callback value of the caller.
        """
        if self.args['polymorphic']:
            setattr(self.inst, "%s_type" % self.args['class_name'], other.__class__.__name__)
        setattr(self.inst, self.othername, other.id)
        return self.inst.save()


    def clear(self):
        """
        Remove the relationship linking the object that belongs to the caller.

        @return: A C{Deferred} with a callback value of the caller.
        """                
        setattr(self.inst, self.othername, None)
        return self.inst.save()



class HasMany(Relationship):
    """
    A class representing the has many relationship.
    """
    
    def get(self, **kwargs):
        """
        Get the objects that caller has.

        @param kwargs: These could include C{limit}, C{orderby}, or any others included in
        C{DBObject.find}.  If a C{where} parameter is included, the conditions will
        be added to the ones already imposed by default in this method.

        @return: A C{Deferred} with a callback value of a list of objects.
        """
        kwargs = self._generateGetArgs(kwargs)
        return self.otherklass.find(**kwargs)


    def count(self, **kwargs):
        """
        Get the number of objects that caller has.

        @param kwargs: These could include C{limit}, C{orderby}, or any others included in
        C{DBObject.find}.  If a C{where} parameter is included, the conditions will
        be added to the ones already imposed by default in this method.

        @return: A C{Deferred} with the number of objects.
        """
        kwargs = self._generateGetArgs(kwargs)
        return self.otherklass.count(**kwargs)


    def _generateGetArgs(self, kwargs):
        if self.args.has_key('as'):
            w = "%s_id = ? AND %s_type = ?" % (self.args['as'], self.args['as'])
            where = [w, self.inst.id, self.thisclass.__name__]
        else:
            where = ["%s = ?" % self.thisname, self.inst.id]

        if kwargs.has_key('where'):
            kwargs['where'] = joinWheres(where, kwargs['where'])
        else:
            kwargs['where'] = where

        return kwargs


    def _set_polymorphic(self, others):
        ds = []
        for other in others:
            if other.id is None:
                msg = "You must save all other instances before defining a relationship"
                raise ReferenceNotSavedError, msg
            setattr(other, "%s_id" % self.args['as'], self.inst.id)
            setattr(other, "%s_type" % self.args['as'], self.thisclass.__name__)
            ds.append(other.save())
        return defer.DeferredList(ds)        


    def _update(self, _, others):
        tablename = self.otherklass.tablename()
        args = {self.thisname: self.inst.id}
        ids = []
        for other in others:
            if other.id is None:
                msg = "You must save all other instances before defining a relationship"
                raise ReferenceNotSavedError, msg
            ids.append(str(other.id))
        where = ["id IN (%s)" % ",".join(ids)]                
        return self.dbconfig.update(tablename, args, where)


    def set(self, others):
        """
        Set the objects that caller has.

        @return: A C{Deferred}.
        """
        if self.args.has_key('as'):
            return self._set_polymorphic(others)
        
        tablename = self.otherklass.tablename()
        args = {self.thisname: None}
        where = ["%s = ?" % self.thisname, self.inst.id]        
        d = self.dbconfig.update(tablename, args, where)
        if len(others) > 0:
            d.addCallback(self._update, others)
        return d


    def clear(self):
        """
        Clear the list of all of the objects that this one has.
        """
        return self.set([])
        

class HasOne(Relationship):
    """
    A class representing the has one relationship.
    """
    
    def get(self):
        """
        Get the object that caller has.

        @return: A C{Deferred} with a callback value of the object this one has (or c{None}).
        """                
        return self.otherklass.find(where=["%s = ?" % self.thisname, self.inst.id], limit=1)


    def set(self, other):
        """
        Set the object that caller has.

        @return: A C{Deferred}.
        """                        
        tablename = self.otherklass.tablename()
        args = {self.thisname: self.inst.id}
        where = ["id = ?", other.id]        
        return self.dbconfig.update(tablename, args, where)


class HABTM(Relationship):
    """
    A class representing the "has and bleongs to many" relationship.  One additional argument
    this class uses in the L{Relationship.__init__} argument list is C{join_table}.
    """
    
    def tablename(self):
        """
        Get the tablename (specified either in the C{join_table} relationship property
        or by calculating the tablename).  If not specified, the table name is calculated
        by sorting the table name versions of the two class names and joining them with a '_').
        For instance, given the classes C{Teacher} and C{Student}, the resulting table name would
        be C{student_teacher}.
        """
        # if specified by user
        if self.args.has_key('join_table'):
            return self.args['join_table']

        # otherwise, create and cache
        if not hasattr(self, '_tablename'):
            thistable = self.infl.tableize(self.thisclass.__name__)
            othertable = self.infl.tableize(self.otherklass.__name__)
            tables = [thistable, othertable]
            tables.sort()
            self._tablename = "_".join(tables)
        return self._tablename
    
    
    def get(self, **kwargs):
        """
        Get the objects that caller has.

        @param kwargs: These could include C{limit}, C{orderby}, or any others included in
        C{InteractionBase.select}.  If a C{where} parameter is included, the conditions will
        be added to the ones already imposed by default in this method.  The argument
        C{join_where} will be applied to the join table, if provided.

        @return: A C{Deferred} with a callback value of a list of objects.
        """
        def _get(rows):
            if len(rows) == 0:
                return defer.succeed([])
            ids = [str(row[self.othername]) for row in rows]
            where = ["id IN (%s)" % ",".join(ids)]
            if kwargs.has_key('where'):
                kwargs['where'] = joinWheres(where, kwargs['where'])
            else:
                kwargs['where'] = where
            d = self.dbconfig.select(self.otherklass.tablename(), **kwargs)
            return d.addCallback(createInstances, self.otherklass)

        tablename = self.tablename()
        where = ["%s = ?" % self.thisname, self.inst.id]
        if kwargs.has_key('join_where'):
            where = joinWheres(where, kwargs.pop('join_where'))
        return self.dbconfig.select(tablename, where=where).addCallback(_get)


    def count(self, **kwargs):
        """
        Get the number of objects that caller has.

        @param kwargs: These could include C{limit}, C{orderby}, or any others included in
        C{InteractionBase.select}.  If a C{where} parameter is included, the conditions will
        be added to the ones already imposed by default in this method.

        @return: A C{Deferred} with the number of objects.
        """
        def _get(rows):
            if len(rows) == 0:
                return defer.succeed(0)
            if not kwargs.has_key('where'):
                return defer.succeed(len(rows))
            ids = [str(row[self.othername]) for row in rows]
            where = ["id IN (%s)" % ",".join(ids)]
            if kwargs.has_key('where'):
                where = joinWheres(where, kwargs['where'])
            return self.dbconfig.count(self.otherklass.tablename(), where=where)

        tablename = self.tablename()
        where = ["%s = ?" % self.thisname, self.inst.id]
        return self.dbconfig.select(tablename, where=where).addCallback(_get)


    def _set(self, _, others):
        args = []
        for other in others:
            if other.id is None:
                msg = "You must save all other instances before defining a relationship"
                raise ReferenceNotSavedError, msg                
            args.append({self.thisname: self.inst.id, self.othername: other.id})
        return self.dbconfig.insertMany(self.tablename(), args)
        

    def set(self, others):
        """
        Set the objects that caller has.

        @return: A C{Deferred}.
        """                        
        where = ["%s = ?" % self.thisname, self.inst.id]
        d = self.dbconfig.delete(self.tablename(), where=where)
        if len(others) > 0:
            d.addCallback(self._set, others)
        return d


    def clear(self):
        """
        Clear the list of all of the objects that this one has.
        """        
        return self.set([])


Relationship.TYPES = {'HASMANY': HasMany, 'HASONE': HasOne, 'BELONGSTO': BelongsTo, 'HABTM': HABTM}

########NEW FILE########
__FILENAME__ = mysql_config
from twisted.enterprise import adbapi
from twisted.internet import defer

from twistar.registry import Registry

CONNECTION = Registry.DBPOOL = adbapi.ConnectionPool('MySQLdb', user="", passwd="", host="localhost", db="twistar")

def initDB(testKlass):
    def runInitTxn(txn):
        txn.execute("""CREATE TABLE users (id INT AUTO_INCREMENT,
                       first_name VARCHAR(255), last_name VARCHAR(255), age INT, dob DATE, PRIMARY KEY (id))""")
        txn.execute("""CREATE TABLE avatars (id INT AUTO_INCREMENT, name VARCHAR(255),
                       color VARCHAR(255), user_id INT, PRIMARY KEY (id))""")        
        txn.execute("""CREATE TABLE pictures (id INT AUTO_INCREMENT, name VARCHAR(255),
                       size INT, user_id INT, PRIMARY KEY (id))""") 
        txn.execute("""CREATE TABLE comments (id INT AUTO_INCREMENT, subject VARCHAR(255),
                       body TEXT, user_id INT, PRIMARY KEY (id))""") 
        txn.execute("""CREATE TABLE favorite_colors (id INT AUTO_INCREMENT, name VARCHAR(255), PRIMARY KEY (id))""")
        txn.execute("""CREATE TABLE favorite_colors_users (favorite_color_id INT, user_id INT, palette_id INT)""")
        txn.execute("""CREATE TABLE coltests (id INT AUTO_INCREMENT, `select` VARCHAR(255), `where` VARCHAR(255), PRIMARY KEY (id))""")

        txn.execute("""CREATE TABLE boys (id INT AUTO_INCREMENT, `name` VARCHAR(255), PRIMARY KEY (id))""")
        txn.execute("""CREATE TABLE girls (id INT AUTO_INCREMENT, `name` VARCHAR(255), PRIMARY KEY (id))""")
        txn.execute("""CREATE TABLE nicknames (id INT AUTO_INCREMENT, `value` VARCHAR(255), `nicknameable_id` INT,
                       `nicknameable_type` VARCHAR(255), PRIMARY KEY(id))""")
        txn.execute("""CREATE TABLE blogposts (id INT AUTO_INCREMENT,
                       title VARCHAR(255), text VARCHAR(255), PRIMARY KEY (id))""")
        txn.execute("""CREATE TABLE categories (id INT AUTO_INCREMENT,
                       name VARCHAR(255), PRIMARY KEY (id))""")
        txn.execute("""CREATE TABLE posts_categories (category_id INT, blogpost_id INT)""")
        txn.execute("""CREATE TABLE transactions (id INT AUTO_INCREMENT, name VARCHAR(255), PRIMARY KEY (id), UNIQUE(name))""")

    return CONNECTION.runInteraction(runInitTxn)


def tearDownDB(self):
    def runTearDownDB(txn):
        txn.execute("DROP TABLE users")
        txn.execute("DROP TABLE avatars")
        txn.execute("DROP TABLE pictures")
        txn.execute("DROP TABLE comments")
        txn.execute("DROP TABLE favorite_colors")
        txn.execute("DROP TABLE favorite_colors_users")
        txn.execute("DROP TABLE coltests")
        txn.execute("DROP TABLE boys")
        txn.execute("DROP TABLE girls")
        txn.execute("DROP TABLE nicknames")
        txn.execute("DROP TABLE blogposts")
        txn.execute("DROP TABLE categories")
        txn.execute("DROP TABLE posts_categories")
        txn.execute("DROP TABLE transactions")
    return CONNECTION.runInteraction(runTearDownDB)
                

########NEW FILE########
__FILENAME__ = postgres_config
from twisted.enterprise import adbapi
from twisted.internet import defer

from twistar.registry import Registry

CONNECTION = Registry.DBPOOL = adbapi.ConnectionPool('psycopg2', "dbname=twistar")

def initDB(testKlass):
    def runInitTxn(txn):
        txn.execute("""CREATE TABLE users (id SERIAL PRIMARY KEY,
                       first_name VARCHAR(255), last_name VARCHAR(255), age INT, dob DATE)""")
        txn.execute("""CREATE TABLE avatars (id SERIAL PRIMARY KEY, name VARCHAR(255),
                       color VARCHAR(255), user_id INT)""")        
        txn.execute("""CREATE TABLE pictures (id SERIAL PRIMARY KEY, name VARCHAR(255),
                       size INT, user_id INT)""") 
        txn.execute("""CREATE TABLE comments (id SERIAL PRIMARY KEY, subject VARCHAR(255),
                       body TEXT, user_id INT)""") 
        txn.execute("""CREATE TABLE favorite_colors (id SERIAL PRIMARY KEY, name VARCHAR(255))""")
        txn.execute("""CREATE TABLE favorite_colors_users (favorite_color_id INT, user_id INT, palette_id INT)""")
        txn.execute("""CREATE TABLE coltests (id SERIAL PRIMARY KEY, "select" VARCHAR(255), "where" VARCHAR(255))""")

        txn.execute("""CREATE TABLE boys (id SERIAL PRIMARY KEY, "name" VARCHAR(255))""")
        txn.execute("""CREATE TABLE girls (id SERIAL PRIMARY KEY, "name" VARCHAR(255))""")
        txn.execute("""CREATE TABLE nicknames (id SERIAL PRIMARY KEY, "value" VARCHAR(255), "nicknameable_id" INT,
                       "nicknameable_type" VARCHAR(255))""")
        txn.execute("""CREATE TABLE blogposts (id SERIAL PRIMARY KEY,
                       title VARCHAR(255), text VARCHAR(255))""")
        txn.execute("""CREATE TABLE categories (id SERIAL PRIMARY KEY,
                       name VARCHAR(255))""")
        txn.execute("""CREATE TABLE posts_categories (category_id INT, blogpost_id INT)""")
        txn.execute("""CREATE TABLE transactions (id SERIAL PRIMARY KEY, name VARCHAR(255) UNIQUE""")

    return CONNECTION.runInteraction(runInitTxn)


def tearDownDB(self):
    def runTearDownDB(txn):
        txn.execute("DROP SEQUENCE users_id_seq CASCADE")        
        txn.execute("DROP TABLE users")

        txn.execute("DROP SEQUENCE avatars_id_seq CASCADE")        
        txn.execute("DROP TABLE avatars")

        txn.execute("DROP SEQUENCE pictures_id_seq CASCADE")        
        txn.execute("DROP TABLE pictures")

        txn.execute("DROP SEQUENCE comments_id_seq CASCADE")
        txn.execute("DROP TABLE comments")

        txn.execute("DROP SEQUENCE favorite_colors_id_seq CASCADE")        
        txn.execute("DROP TABLE favorite_colors")

        txn.execute("DROP TABLE favorite_colors_users")

        txn.execute("DROP SEQUENCE coltests_id_seq CASCADE")
        txn.execute("DROP TABLE coltests")

        txn.execute("DROP SEQUENCE boys_id_seq CASCADE")
        txn.execute("DROP TABLE boys")

        txn.execute("DROP SEQUENCE girls_id_seq CASCADE")
        txn.execute("DROP TABLE girls")

        txn.execute("DROP SEQUENCE nicknames_id_seq CASCADE")
        txn.execute("DROP TABLE nicknames")

        txn.execute("DROP SEQUENCE blogposts_id_seq CASCADE")
        txn.execute("DROP TABLE blogposts")

        txn.execute("DROP SEQUENCE categories_id_seq CASCADE")
        txn.execute("DROP TABLE categories")

        txn.execute("DROP TABLE posts_categories")

        txn.execute("DROP SEQUENCE transactions_id_seq CASCADE")
        txn.execute("DROP TABLE transactions")
        
    return CONNECTION.runInteraction(runTearDownDB)
                

########NEW FILE########
__FILENAME__ = sqlite_config
from twisted.enterprise import adbapi
from twisted.internet import defer

from twistar.registry import Registry

def initDB(testKlass):
    location = testKlass.mktemp()
    Registry.DBPOOL = adbapi.ConnectionPool('sqlite3', location, check_same_thread=False)
    def runInitTxn(txn):
        txn.execute("""CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       first_name TEXT, last_name TEXT, age INTEGER, dob DATE)""")
        txn.execute("""CREATE TABLE avatars (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
                       color TEXT, user_id INTEGER)""")        
        txn.execute("""CREATE TABLE pictures (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
                       size INTEGER, user_id INTEGER)""") 
        txn.execute("""CREATE TABLE comments (id INTEGER PRIMARY KEY AUTOINCREMENT, subject TEXT,
                       body TEXT, user_id INTEGER)""") 
        txn.execute("""CREATE TABLE favorite_colors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)""")
        txn.execute("""CREATE TABLE favorite_colors_users (favorite_color_id INTEGER, user_id INTEGER, palette_id INTEGER)""")
        txn.execute("""CREATE TABLE coltests (id INTEGER PRIMARY KEY AUTOINCREMENT, `select` TEXT, `where` TEXT)""")

        txn.execute("""CREATE TABLE boys (id INTEGER PRIMARY KEY AUTOINCREMENT, `name` TEXT)""")
        txn.execute("""CREATE TABLE girls (id INTEGER PRIMARY KEY AUTOINCREMENT, `name` TEXT)""")        
        txn.execute("""CREATE TABLE nicknames (id INTEGER PRIMARY KEY AUTOINCREMENT, `value` TEXT, `nicknameable_id` INTEGER,
                       `nicknameable_type` TEXT)""")
        txn.execute("""CREATE TABLE blogposts (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       title TEXT, text TEXT)""")
        txn.execute("""CREATE TABLE categories (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT)""")
        txn.execute("""CREATE TABLE posts_categories (category_id INTEGER, blogpost_id INTEGER)""")
        txn.execute("""CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, UNIQUE (name))""")
    return Registry.DBPOOL.runInteraction(runInitTxn)


def tearDownDB(self):
    return defer.succeed(True)

########NEW FILE########
__FILENAME__ = test_dbconfig
from twisted.trial import unittest
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks

from twistar.registry import Registry
from twistar.dbconfig.base import InteractionBase

from utils import *

class DBConfigTest(unittest.TestCase):
    
    @inlineCallbacks
    def setUp(self):
        yield initDB(self)
        self.user = yield User(first_name="First", last_name="Last", age=10).save()
        self.avatar = yield Avatar(name="an avatar name", user_id=self.user.id).save()
        self.picture = yield Picture(name="a pic", size=10, user_id=self.user.id).save()        
        self.dbconfig = Registry.getConfig()


    @inlineCallbacks
    def tearDown(self):
        yield tearDownDB(self)


    @inlineCallbacks
    def test_select(self):
        # make a fake user
        user = yield User(first_name="Another First").save()
        tablename = User.tablename()
        
        where = ['first_name = ?', "First"]
        result = yield self.dbconfig.select(tablename, where=where, limit=1, orderby="first_name ASC")
        self.assertTrue(result is not None)
        self.assertEqual(result['id'], self.user.id)

        result = yield self.dbconfig.select(tablename, limit=100, orderby="first_name ASC" )       
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]['id'] == user.id and result[1]['id'] == self.user.id)


    @inlineCallbacks
    def test_delete(self):
        tablename = User.tablename()
        
        yield User(first_name="Another First").save()
        yield self.dbconfig.delete(tablename, ['first_name like ?', "%nother Fir%"])
        
        result = yield self.dbconfig.select(tablename)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]['id'] == self.user.id)
        

    @inlineCallbacks
    def test_update(self):
        tablename = User.tablename()        
        user = yield User(first_name="Another First").save()

        args = {'first_name': "test", "last_name": "foo", "age": 91}
        yield self.dbconfig.update(tablename, args, ['id = ?', user.id])
        yield user.refresh()
        for key, value in args.items():
            self.assertEqual(value, getattr(user, key))


    @inlineCallbacks
    def test_insert(self):
        tablename = User.tablename()
        args = {'first_name': "test", "last_name": "foo", "age": 91}        
        yield self.dbconfig.insert(tablename, args)

        where = ['first_name = ? AND last_name = ? AND age = ?']
        where = where + ["test", "foo", 91]
        users = yield User.find(where=where)
        
        self.assertEqual(len(users), 1)
        for key, value in args.items():
            self.assertEqual(value, getattr(users[0], key))

 
    @inlineCallbacks
    def test_insert_many(self):   
        tablename = User.tablename()

        args = []
        for counter in range(10):
            args.append({'first_name': "test_insert_many", "last_name": "foo", "age": counter})
        yield self.dbconfig.insertMany(tablename, args)

        users = yield User.find(where=['first_name = ?', "test_insert_many"], orderby="age ASC")

        for counter in range(10):
            for key, value in args[counter].items():
                self.assertEqual(value, getattr(users[counter], key))


    @inlineCallbacks
    def test_insert_obj(self):
        args = {'first_name': "test_insert_obj", "last_name": "foo", "age": 91}
        user = User(**args)

        yield self.dbconfig.insertObj(user)
        user = yield User.find(where=['first_name = ?', "test_insert_obj"], limit=1)

        for key, value in args.items():
            self.assertEqual(value, getattr(user, key))        


    @inlineCallbacks
    def test_update_obj(self):
        args = {'first_name': "test_insert_obj", "last_name": "foo", "age": 91}
        user = yield User(**args).save()

        args = {'first_name': "test_insert_obj_foo", "last_name": "bar", "age": 191}
        for key, value in args.items():
            setattr(user, key, value)

        yield self.dbconfig.updateObj(user)
        user = yield User.find(user.id)

        for key, value in args.items():
            self.assertEqual(value, getattr(user, key))                


    @inlineCallbacks
    def test_colname_escaping(self):
        args = {'select': "some text", 'where': "other text"}
        coltest = Coltest(**args)
        yield self.dbconfig.insertObj(coltest)

        args = {'select': "other text", 'where': "some text"}
        for key, value in args.items():
            setattr(coltest, key, value)
        yield self.dbconfig.updateObj(coltest)

        tablename = Coltest.tablename()
        colnames = self.dbconfig.escapeColNames(["select"])
        ctest = yield self.dbconfig.select(tablename, where=['%s = ?' % colnames[0], args['select']], limit=1)

        for key, value in args.items():
            self.assertEqual(value, ctest[key])


    def test_unicode_logging(self):
        InteractionBase.LOG = True
        
        ustr = u'\N{SNOWMAN}'
        InteractionBase().log(ustr, [ustr], {ustr: ustr})
        
        ustr = '\xc3\xa8'
        InteractionBase().log(ustr, [ustr], {ustr: ustr})
        
        InteractionBase.LOG = False



########NEW FILE########
__FILENAME__ = test_dbobject
from twisted.trial import unittest
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks

from twistar.exceptions import ImaginaryTableError
from twistar.registry import Registry

from utils import *

class DBObjectTest(unittest.TestCase):
    
    @inlineCallbacks
    def setUp(self):
        yield initDB(self)
        self.user = yield User(first_name="First", last_name="Last", age=10).save()
        self.avatar = yield Avatar(name="an avatar name", user_id=self.user.id).save()
        self.picture = yield Picture(name="a pic", size=10, user_id=self.user.id).save()        


    @inlineCallbacks
    def tearDown(self):
        yield tearDownDB(self)        


    @inlineCallbacks
    def test_findBy(self):
        r = yield User.findBy(first_name="Non", last_name="Existant")
        self.assertEqual(r, [])

        r = yield User.findBy(first_name="First", last_name="Last", age=11)
        self.assertEqual(r, [])

        r = yield User.findBy(first_name="First", last_name="Last", age=10)
        self.assertEqual(r[0], self.user)

        r = yield User.findBy(first_name="First", last_name="Last")
        self.assertEqual(r[0], self.user)

        u = yield User(first_name="Bob").save()
        r = yield User.findBy()
        self.assertEqual(len(r), 2)


    @inlineCallbacks
    def test_findOrCreate(self):
        # make sure we didn't create a new user
        r = yield User.findOrCreate(first_name="First")
        self.assertEqual(r.id, self.user.id)

        # make sure we do create a new user
        r = yield User.findOrCreate(first_name="First", last_name="Non")
        self.assertTrue(r.id != self.user.id)


    @inlineCallbacks
    def test_creation(self):
        # test creating blank object 
        u = yield User().save()
        self.assertTrue(type(u.id) == int or type(u.id) == long)

        # test creating object with props that don't correspond to columns
        u = yield User(a_fake_column="blech").save()
        self.assertTrue(type(u.id) == int or type(u.id) == long)        

        # Test table doesn't exist
        f = FakeObject(blah = "something")
        self.failUnlessFailure(f.save(), ImaginaryTableError)

        dateklass = Registry.getDBAPIClass("Date")
        args = {'first_name': "a", "last_name": "b", "age": 10, "dob": dateklass(2000, 1, 1)}
        u = yield User(**args).save()
        for key, value in args.items():
            self.assertEqual(getattr(u, key), value)
        

    @inlineCallbacks
    def test_find(self):
        ids = []
        for _ in range(3):
            user = yield User(first_name="blah").save()
            ids.append(user.id)
        yield User(first_name="not blah").save()
        results = yield User.find(where=["first_name = ?", "blah"])
        resultids = [result.id for result in results]
        self.assertEqual(ids, resultids)


    @inlineCallbacks
    def test_count(self):
        ids = []
        for _ in range(3):
            user = yield User(first_name="blah").save()
            ids.append(user.id)
        yield User(first_name="not blah").save()
        results = yield User.count(where=["first_name = ?", "blah"])
        self.assertEqual(3, results)


    @inlineCallbacks
    def test_all(self):
        ids = [self.user.id]
        for _ in range(3):
            user = yield User(first_name="blah").save()
            ids.append(user.id)
        results = yield User.all()
        resultids = [result.id for result in results]
        self.assertEqual(ids, resultids)


    @inlineCallbacks
    def test_count_all(self):
        ids = [self.user.id]
        for _ in range(3):
            user = yield User(first_name="blah").save()
            ids.append(user.id)
        results = yield User.count()
        self.assertEqual(4, results)

    
    @inlineCallbacks
    def test_delete(self):
        u = yield User().save()
        oldid = u.id
        yield u.delete()
        result = yield User.find(oldid)
        self.assertEqual(result, None)


    @inlineCallbacks
    def test_delete_all(self):
        users = yield User.all()
        ids = [user.id for user in users]
        for _ in range(3):
            yield User(first_name="blah").save()
        yield User.deleteAll(["first_name = ?", "blah"])
        users = yield User.all()        
        resultids = [user.id for user in users]
        self.assertEqual(resultids, ids)


    @inlineCallbacks
    def test_update(self):
        dateklass = Registry.getDBAPIClass("Date")
        args = {'first_name': "a", "last_name": "b", "age": 10}
        u = yield User(**args).save()

        args = {'first_name': "b", "last_name": "a", "age": 100}
        for key, value in args.items():
            setattr(u, key, value)
        yield u.save()

        u = yield User.find(u.id)
        for key, value in args.items():
            self.assertEqual(getattr(u, key), value)


    @inlineCallbacks
    def test_refresh(self):
        dateklass = Registry.getDBAPIClass("Date")
        args = {'first_name': "a", "last_name": "b", "age": 10}
        u = yield User(**args).save()

        # mess up the props, then refresh
        u.first_name = "something different"
        u.last_name = "another thing"
        yield u.refresh()
        
        for key, value in args.items():
            self.assertEqual(getattr(u, key), value)


    @inlineCallbacks
    def test_validation(self):
        User.validatesPresenceOf('first_name', message='cannot be blank, fool.')
        User.validatesLengthOf('last_name', range=xrange(1,101))
        User.validatesUniquenessOf('first_name')

        u = User()
        yield u.validate()
        self.assertEqual(len(u.errors), 2)

        first = yield User(first_name="not unique", last_name="not unique").save()
        u = yield User(first_name="not unique", last_name="not unique").save()
        self.assertEqual(len(u.errors), 1)
        self.assertEqual(u.id, None)

        # make sure first can be updated
        yield first.save()
        self.assertEqual(len(first.errors), 0)
        User.clearValidations()
        

    @inlineCallbacks
    def test_validation_function(self):
        def adult(user):
            if user.age < 18:
                user.errors.add('age', "must be over 18.")
        User.addValidator(adult)

        u = User(age=10)
        valid = yield u.isValid()
        self.assertEqual(valid, False)
        yield u.save()
        self.assertEqual(len(u.errors), 1)
        self.assertEqual(len(u.errors.errorsFor('age')), 1)
        self.assertEqual(len(u.errors.errorsFor('first_name')), 0)
        User.clearValidations()

        u = User(age=10)
        valid = yield u.isValid()
        self.assertEqual(valid, True)
        User.clearValidations()        


    @inlineCallbacks
    def test_afterInit(self):
        def afterInit(user):
            user.blah = "foobar"
        User.afterInit = afterInit
        u = yield User.find(limit=1)
        self.assertTrue(hasattr(u, 'blah'))
        self.assertEqual(u.blah, 'foobar')

        # restore user's afterInit
        User.afterInit = DBObject.afterInit


    @inlineCallbacks
    def test_beforeDelete(self):
        User.beforeDelete = lambda user: False
        u = yield User().save()
        oldid = u.id
        yield u.delete()
        result = yield User.find(oldid)
        self.assertEqual(result, u)

        User.beforeDelete = lambda user: True
        yield u.delete()
        result = yield User.find(oldid)
        self.assertEqual(result, None)

        # restore user's beforeDelete
        User.beforeDelete = DBObject.beforeDelete

    @inlineCallbacks
    def test_loadRelations(self):
        user = yield User.find(limit=1)
        all = yield user.loadRelations()

        pictures = yield user.pictures.get()
        self.assertEqual(pictures, all['pictures'])

        avatar = yield user.avatar.get()
        self.assertEqual(avatar, all['avatar'])

        suball = yield user.loadRelations('pictures')
        self.assertTrue(not suball.has_key('avatar'))
        self.assertEqual(pictures, suball['pictures'])

########NEW FILE########
__FILENAME__ = test_relationships
from twisted.trial import unittest
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks

from twistar.exceptions import ReferenceNotSavedError

from utils import *

class RelationshipTest(unittest.TestCase):    
    @inlineCallbacks
    def setUp(self):
        yield initDB(self)
        self.user = yield User(first_name="First", last_name="Last", age=10).save()
        self.avatar = yield Avatar(name="an avatar name", user_id=self.user.id).save()
        self.picture = yield Picture(name="a pic", size=10, user_id=self.user.id).save()
        self.favcolor = yield FavoriteColor(name="blue").save()
        self.boy = yield Boy(name="Robert").save()
        self.girl = yield Girl(name="Susan").save()
        self.config = Registry.getConfig()


    @inlineCallbacks
    def tearDown(self):
        yield tearDownDB(self)            


    @inlineCallbacks
    def test_polymorphic_get(self):
        bob = yield Nickname(value="Bob", nicknameable_id=self.boy.id, nicknameable_type="Boy").save()
        sue = yield Nickname(value="Sue", nicknameable_id=self.girl.id, nicknameable_type="Girl").save()        
        
        nicknames = yield self.boy.nicknames.get()
        self.assertEqual(len(nicknames), 1)
        self.assertEqual(nicknames[0], bob)
        self.assertEqual(nicknames[0].value, bob.value)

        nicknames = yield self.girl.nicknames.get()
        self.assertEqual(len(nicknames), 1)
        self.assertEqual(nicknames[0], sue)
        self.assertEqual(nicknames[0].value, sue.value)

        boy = yield bob.nicknameable.get()
        self.assertEqual(boy, self.boy)

        girl = yield sue.nicknameable.get()
        self.assertEqual(girl, self.girl)


    @inlineCallbacks
    def test_polymorphic_set(self):
        nicknameone = yield Nickname(value="Bob").save()
        nicknametwo = yield Nickname(value="Bobby").save()        
        yield self.boy.nicknames.set([nicknametwo, nicknameone])

        nicknames = yield self.boy.nicknames.get()
        self.assertEqual(len(nicknames), 2)
        # since the insert is asynchronous - two may have been inserted
        # before one
        if not nicknames[0] == nicknametwo:
            self.assertEqual(nicknames[0], nicknameone)
        if not nicknames[1] == nicknameone:
            self.assertEqual(nicknames[1], nicknametwo)

        boy = yield nicknameone.nicknameable.get()
        self.assertEqual(boy, self.boy)

        nickname = yield Nickname(value="Suzzy").save()
        yield nickname.nicknameable.set(self.girl)
        nicknames = yield self.girl.nicknames.get()
        self.assertEqual(len(nicknames), 1)
        self.assertEqual(nicknames[0], nickname)
        self.assertEqual(nicknames[0].value, nickname.value)
        

    @inlineCallbacks
    def test_belongs_to(self):
        user = yield self.picture.user.get()
        self.assertEqual(user, self.user)


    @inlineCallbacks
    def test_set_belongs_to(self):
        user = yield User(first_name="new one").save()
        yield self.picture.user.set(user)
        self.assertEqual(user.id, self.picture.user_id)


    @inlineCallbacks
    def test_set_on_unsaved(self):
        user = yield User(first_name="new one").save()
        picture = Picture(name="a pic")
        self.assertRaises(ReferenceNotSavedError, getattr, picture, 'user')


    @inlineCallbacks
    def test_clear_belongs_to(self):
        picture = yield Picture(name="a pic", size=10, user_id=self.user.id).save()
        yield picture.user.clear()
        user = yield picture.user.get()
        self.assertEqual(user, None)
        yield picture.refresh()
        user = yield picture.user.get()
        self.assertEqual(user, None)


    @inlineCallbacks
    def test_has_many(self):
        # First, make a few pics
        ids = [self.picture.id]
        for _ in range(3):
            pic = yield Picture(user_id=self.user.id).save()
            ids.append(pic.id)
            
        pics = yield self.user.pictures.get()
        picids = [pic.id for pic in pics]
        self.assertEqual(ids, picids)


    @inlineCallbacks
    def test_has_many_count(self):
        # First, make a few pics
        ids = [self.picture.id]
        for _ in range(3):
            pic = yield Picture(user_id=self.user.id).save()
            ids.append(pic.id)

        totalnum = yield self.user.pictures.count()
        self.assertEqual(totalnum, 4)


    @inlineCallbacks
    def test_has_many_count_nocache(self):
        # First, count comments
        totalnum = yield self.user.comments.count()
        self.assertEqual(totalnum, 0)

        for _ in range(3):
            pic = yield Comment(user_id=self.user.id).save()

        totalnum = yield self.user.comments.count()
        self.assertEqual(totalnum, 3)


    @inlineCallbacks
    def test_has_many_get_with_args(self):
        # First, make a few pics
        ids = [self.picture.id]
        for _ in range(3):
            pic = yield Picture(user_id=self.user.id).save()
            ids.append(pic.id)
            
        pics = yield self.user.pictures.get(where=['name = ?','a pic'])
        self.assertEqual(len(pics),1)
        self.assertEqual(pics[0].name,'a pic')


    @inlineCallbacks
    def test_has_many_count_with_args(self):
        # First, make a few pics
        ids = [self.picture.id]
        for _ in range(3):
            pic = yield Picture(user_id=self.user.id).save()
            ids.append(pic.id)

        picsnum = yield self.user.pictures.count(where=['name = ?','a pic'])
        self.assertEqual(picsnum,1)


    @inlineCallbacks
    def test_set_has_many(self):
        # First, make a few pics
        pics = [self.picture]
        for _ in range(3):
            pic = yield Picture(name="a pic").save()
            pics.append(pic)
        picids = [int(pic.id) for pic in pics]

        yield self.user.pictures.set(pics)
        results = yield self.user.pictures.get()
        resultids = [int(pic.id) for pic in results]
        picids.sort()
        resultids.sort()
        self.assertEqual(picids, resultids)

        # now try resetting
        pics = []
        for _ in range(3):
            pic = yield Picture(name="a pic").save()
            pics.append(pic)
        picids = [pic.id for pic in pics]
        
        yield self.user.pictures.set(pics)
        results = yield self.user.pictures.get()
        resultids = [pic.id for pic in results]
        self.assertEqual(picids, resultids)        


    @inlineCallbacks
    def test_clear_has_many(self):
        pics = [self.picture]
        for _ in range(3):
            pic = yield Picture(name="a pic").save()
            pics.append(pic)

        yield self.user.pictures.set(pics)
        yield self.user.pictures.clear()
        
        userpics = yield self.user.pictures.get()
        self.assertEqual(userpics, [])

        # even go so far as to refetch user
        user = yield User.find(self.user.id)
        userpics = yield self.user.pictures.get()
        self.assertEqual(userpics, [])

        allpics = Picture.all()
        self.assertEqual(userpics, [])
        

    @inlineCallbacks
    def test_has_one(self):
        avatar = yield self.user.avatar.get()
        self.assertEqual(avatar, self.avatar)


    @inlineCallbacks
    def test_set_has_one(self):
        avatar = yield Avatar(name="another").save()
        yield self.user.avatar.set(avatar)
        yield avatar.refresh()
        self.assertEqual(avatar.user_id, self.user.id)


    @inlineCallbacks
    def test_habtm(self):
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]
        colorids = [color.id for color in colors]
        yield FavoriteColor(name="green").save()

        args = {'user_id': self.user.id, 'favorite_color_id': colors[0].id}
        yield self.config.insert('favorite_colors_users', args)
        args = {'user_id': self.user.id, 'favorite_color_id': colors[1].id}
        yield self.config.insert('favorite_colors_users', args)
        
        newcolors = yield self.user.favorite_colors.get()
        newcolorids = [color.id for color in newcolors]        
        self.assertEqual(newcolorids, colorids)


    @inlineCallbacks
    def test_habtm_with_joinwhere(self):
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]
        colorids = [color.id for color in colors]
        yield FavoriteColor(name="green").save()

        args = {'user_id': self.user.id, 'favorite_color_id': colors[0].id, 'palette_id': 1}
        yield self.config.insert('favorite_colors_users', args)
        args = {'user_id': self.user.id, 'favorite_color_id': colors[1].id, 'palette_id': 2}
        yield self.config.insert('favorite_colors_users', args)

        newcolors = yield self.user.favorite_colors.get(join_where=['palette_id = ?', 2])
        newcolorids = [color.id for color in newcolors]
        self.assertEqual(newcolorids, [colors[1].id])


    @inlineCallbacks
    def test_habtm_count(self):
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]
        colorids = [color.id for color in colors]
        yield FavoriteColor(name="green").save()

        args = {'user_id': self.user.id, 'favorite_color_id': colors[0].id}
        yield self.config.insert('favorite_colors_users', args)
        args = {'user_id': self.user.id, 'favorite_color_id': colors[1].id}
        yield self.config.insert('favorite_colors_users', args)

        newcolorsnum = yield self.user.favorite_colors.count()
        self.assertEqual(newcolorsnum, 2)


    @inlineCallbacks
    def test_habtm_get_with_args(self):
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]
        colorids = [color.id for color in colors]

        args = {'user_id': self.user.id, 'favorite_color_id': colors[0].id}
        yield self.config.insert('favorite_colors_users', args)
        args = {'user_id': self.user.id, 'favorite_color_id': colors[1].id}
        yield self.config.insert('favorite_colors_users', args)
        
        newcolor = yield self.user.favorite_colors.get(where=['name = ?','red'], limit=1)
        self.assertEqual(newcolor.id, color.id)


    @inlineCallbacks
    def test_habtm_count_with_args(self):
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]
        colorids = [color.id for color in colors]

        args = {'user_id': self.user.id, 'favorite_color_id': colors[0].id}
        yield self.config.insert('favorite_colors_users', args)
        args = {'user_id': self.user.id, 'favorite_color_id': colors[1].id}
        yield self.config.insert('favorite_colors_users', args)

        newcolorsnum = yield self.user.favorite_colors.count(where=['name = ?','red'])
        self.assertEqual(newcolorsnum, 1)


    @inlineCallbacks
    def test_set_habtm(self):
        user = yield User().save()
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]
        colorids = [color.id for color in colors]

        yield user.favorite_colors.set(colors)
        newcolors = yield user.favorite_colors.get()
        newcolorids = [color.id for color in newcolors]        
        self.assertEqual(newcolorids, colorids)        


    @inlineCallbacks
    def test_clear_habtm(self):
        user = yield User().save()
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]

        yield user.favorite_colors.set(colors)
        yield user.favorite_colors.clear()
        colors = yield user.favorite_colors.get()        
        self.assertEqual(colors, [])


    @inlineCallbacks
    def test_clear_jointable_on_delete_habtm(self):
        user = yield User().save()
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]

        yield user.favorite_colors.set(colors)
        old_id = color.id
        yield color.delete()
        result = yield self.config.select('favorite_colors_users', where=['favorite_color_id = ?', old_id], limit=1)
        self.assertTrue(result is None)


    @inlineCallbacks
    def test_clear_jointable_on_delete_habtm_with_custom_args(self):
        join_tablename = 'posts_categories'
        post = yield Blogpost(title='headline').save()
        category = yield Category(name="personal").save()

        yield post.categories.set([category])
        cat_id = category.id
        yield category.delete()
        res = yield self.config.select(join_tablename, where=['category_id = ?', cat_id], limit=1)
        self.assertIsNone(res)


    @inlineCallbacks
    def test_set_habtm_blank(self):
        user = yield User().save()
        color = yield FavoriteColor(name="red").save()
        colors = [self.favcolor, color]
        colorids = [color.id for color in colors]

        yield user.favorite_colors.set(colors)
        # now blank out
        yield user.favorite_colors.set([])
        newcolors = yield user.favorite_colors.get()
        self.assertEqual(len(newcolors), 0)

########NEW FILE########
__FILENAME__ = test_transactions
from twisted.trial import unittest
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks

from twistar.exceptions import ReferenceNotSavedError
from twistar.utils import transaction
from twistar.exceptions import TransactionError

from utils import *

class TransactionTest(unittest.TestCase):    
    @inlineCallbacks
    def setUp(self):
        yield initDB(self)
        self.config = Registry.getConfig()


    @inlineCallbacks
    def tearDown(self):
        yield tearDownDB(self)            


    @inlineCallbacks
    def test_findOrCreate(self):
        @transaction
        @inlineCallbacks
        def interaction(txn):
            yield Transaction.findOrCreate(name="a name")
            yield Transaction.findOrCreate(name="a name")

        yield interaction()
        count = yield Transaction.count()
        self.assertEqual(count, 1)


    @inlineCallbacks
    def test_doubleInsert(self):

        @transaction
        def interaction(txn):
            def finish(trans):
                return Transaction(name="unique name").save()
            return Transaction(name="unique name").save().addCallback(finish)
        
        try:
            yield interaction()
        except TransactionError:
            pass

        # there should be no transaction records stored at all
        count = yield Transaction.count()
        self.assertEqual(count, 0)


    @inlineCallbacks
    def test_success(self):

        @transaction
        def interaction(txn):
            def finish(trans):
                return Transaction(name="unique name two").save()
            return Transaction(name="unique name").save().addCallback(finish)

        result = yield interaction()
        self.assertEqual(result.id, 2)

        count = yield Transaction.count()
        self.assertEqual(count, 2)

########NEW FILE########
__FILENAME__ = test_utils
from twisted.trial import unittest
from twisted.enterprise import adbapi
from twisted.internet.defer import inlineCallbacks

from twistar import utils
from twistar.registry import Registry

from utils import *

class UtilsTest(unittest.TestCase):
    
    @inlineCallbacks
    def setUp(self):
        yield initDB(self)
        self.user = yield User(first_name="First", last_name="Last", age=10).save()


    @inlineCallbacks
    def test_joinWheres_precedence(self):
        yield User(first_name="Second").save()
        
        first = ['first_name = ?', "First"]
        last = ['last_name = ?', "Last"]
        second = ['first_name = ?', "Second"]

        last_or_second = utils.joinWheres(last, second, joiner='OR')
        where = utils.joinWheres(first, last_or_second, joiner='AND')

        results = yield User.count(where=where)
        self.assertEqual(1, results)


    def test_joinMultipleWheres_empty_arg(self):
        where = utils.joinMultipleWheres([], joiner='AND')
        self.assertEqual(where, [])
    

    def test_joinMultipleWheres_single_where(self):
        where = ['first_name = ?', "First"]
        joined_where = utils.joinMultipleWheres([where], joiner='AND')
        self.assertEqual(where, joined_where)


    @inlineCallbacks
    def test_joinMultipleWheres(self):
        yield User(first_name="First", last_name="Last", age=20).save()

        first = ['first_name = ?', "First"]
        last = ['last_name = ?', "Last"]
        age = ['age <> ?', 20]

        where = utils.joinMultipleWheres([first, last, age], joiner='AND')

        results = yield User.count(where=where)
        self.assertEqual(1, results)


    @inlineCallbacks
    def tearDown(self):
        yield tearDownDB(self)


########NEW FILE########
__FILENAME__ = utils
from twisted.enterprise import adbapi
from twisted.internet import defer

from twistar.dbobject import DBObject
from twistar.registry import Registry

from sqlite_config import initDB, tearDownDB
#from mysql_config import initDB, tearDownDB
#from postgres_config import initDB, tearDownDB

class User(DBObject):
    HASMANY = ['pictures', 'comments']
    HASONE = ['avatar']
    HABTM = ['favorite_colors']

class Picture(DBObject):
    BELONGSTO = ['user']

class Comment(DBObject):
    BELONGSTO = ['user']

class Avatar(DBObject):
    pass

class FavoriteColor(DBObject):
    HABTM = ['users']    

class Blogpost(DBObject):
    HABTM = [dict(name='categories', join_table='posts_categories')]

class Category(DBObject):
    HABTM = [dict(name='blogposts', join_table='posts_categories')]

class FakeObject(DBObject):
    pass

class Coltest(DBObject):
    pass

class Transaction(DBObject):
    pass

class Boy(DBObject):
    HASMANY = [{'name': 'nicknames', 'as': 'nicknameable'}]

class Girl(DBObject):
    HASMANY = [{'name': 'nicknames', 'as': 'nicknameable'}]    

class Nickname(DBObject):
    BELONGSTO = [{'name': 'nicknameable', 'polymorphic': True}]


Registry.register(Picture, User, Comment, Avatar, FakeObject, FavoriteColor)
Registry.register(Boy, Girl, Nickname)
Registry.register(Blogpost, Category)

########NEW FILE########
__FILENAME__ = utils
"""
General catchall for functions that don't make sense as methods.
"""

from twisted.internet import defer, threads, reactor

from twistar.registry import Registry
from twistar.exceptions import TransactionError


def transaction(interaction):
    """
    A decorator to wrap any code in a transaction.  If any exceptions are raised, all modifications
    are rolled back.  The function that is decorated should accept at least one argument, which is
    the transaction (in case you want to operate directly on it).
    """
    def _transaction(txn, args, kwargs):
        config = Registry.getConfig()
        config.txn = txn
        # get the result of the functions *synchronously*, since this is in a transaction
        try:
            result = threads.blockingCallFromThread(reactor, interaction, txn, *args, **kwargs)
            config.txn = None
            return result
        except Exception, e:
            config.txn = None
            raise TransactionError, str(e)

    def wrapper(*args, **kwargs):
        return Registry.DBPOOL.runInteraction(_transaction, args, kwargs)

    return wrapper


def createInstances(props, klass):
    """
    Create an instance of C{list} of instances of a given class
    using the given properties.
    
    @param props: One of:
      1. A dict, in which case return an instance of klass
      2. A list of dicts, in which case return a list of klass instances

    @return: A C{Deferred} that will pass the result to a callback
    """
    if type(props) is list:
        ks = [klass(**prop) for prop in props]
        ds = [defer.maybeDeferred(k.afterInit) for k in ks]
        return defer.DeferredList(ds).addCallback(lambda _: ks)
    
    if props is not None:
        k = klass(**props)
        return defer.maybeDeferred(k.afterInit).addCallback(lambda _: k)

    return defer.succeed(None)


def dictToWhere(attrs, joiner="AND"):
    """
    Convert a dictionary of attribute: value to a where statement.

    For instance, dictToWhere({'one': 'two', 'three': 'four'}) returns:
    ['(one = ?) AND (three = ?)', 'two', 'four']

    @return: Expression above if len(attrs) > 0, None otherwise
    """
    if len(attrs) == 0:
        return None

    wheres = map(lambda name: "(%s = ?)" % name, attrs.keys())
    return [(" %s " % joiner).join(wheres)] + attrs.values()


def joinWheres(wone, wtwo, joiner="AND"):
    """
    Take two wheres (of the same format as the C{where} parameter in the function
    L{DBObject.find}) and join them.

    @param wone: First where C{list}

    @param wone: Second where C{list}

    @param joiner: Optional text for joining the two wheres.

    @return: A joined version of the two given wheres.
    """
    statement = ["(%s) %s (%s)" % (wone[0], joiner, wtwo[0])]
    args = wone[1:] + wtwo[1:]
    return statement + args


def joinMultipleWheres(wheres, joiner="AND"):
    """
    Take a list of wheres (of the same format as the C{where} parameter in the
    function L{DBObject.find}) and join them.

    @param wheres: List of where clauses to join C{list}

    @param joiner: Optional text for joining the two wheres.

    @return: A joined version of the list of the given wheres.
    """
    wheres = [w for w in wheres if w]   # discard empty wheres
    if not wheres:
        return []

    f = lambda x, y: joinWheres(x, y, joiner)
    return reduce(f, wheres)


def deferredDict(d):
    """
    Just like a C{defer.DeferredList} but instead accepts and returns a C{dict}.

    @param d: A C{dict} whose values are all C{Deferred} objects.

    @return: A C{DeferredList} whose callback will be given a dictionary whose
    keys are the same as the parameter C{d}'s and whose values are the results
    of each individual deferred call.
    """
    if len(d) == 0:
        return defer.succeed({})

    def handle(results, names):
        rvalue = {}
        for index in range(len(results)):
            rvalue[names[index]] = results[index][1]
        return rvalue
    
    dl = defer.DeferredList(d.values())
    return dl.addCallback(handle, d.keys())

########NEW FILE########
__FILENAME__ = validation
"""
Package providing validation support for L{DBObject}s.
"""

from twisted.internet import defer
from BermiInflector.Inflector import Inflector
from twistar.utils import joinWheres, deferredDict

def presenceOf(obj, names, kwargs):
    """
    A validator to test whether or not some named properties are set.
    For those named properties that are not set, an error will
    be recorded in C{obj.errors}.

    @param obj: The object whose properties need to be tested.
    @param names: The names of the properties to test.
    @param kwargs: Keyword arguments.  Right now, all but a
    C{message} value are ignored.
    """
    message = kwargs.get('message', "cannot be blank.")
    for name in names:
        if getattr(obj, name, "") in ("", None):
            obj.errors.add(name, message)


def lengthOf(obj, names, kwargs):
    """
    A validator to test whether or not some named properties have a
    specific length.  The length is specified in one of two ways: either
    a C{range} keyword set with a C{range} / C{xrange} / C{list} object
    containing valid values, or a C{length} keyword with the exact length
    allowed.

    For those named properties that do not have the specified length
    (or that are C{None}), an error will be recorded in C{obj.errors}.

    @param obj: The object whose properties need to be tested.
    @param names: The names of the properties to test.
    @param kwargs: Keyword arguments.  Right now, all but 
    C{message}, C{range}, and C{length} values are ignored.
    """
    # create a range object representing acceptable values.  If
    # no range is given (which could be an xrange, range, or list)
    # then length is used.  If length is not given, a length of 1 is
    # assumed
    xr = kwargs.get('range', [kwargs.get('length', 1)])
    minmax = (str(min(xr)), str(max(xr)))
    if minmax[0] == minmax[1]:
        message = kwargs.get('message', "must have a length of %s." % minmax[0])
    else:
        message = kwargs.get('message', "must have a length between %s and %s (inclusive)." % minmax)
    for name in names:
        val = getattr(obj, name, "")
        if val is None or not len(val) in xr:
            obj.errors.add(name, message)


def uniquenessOf(obj, names, kwargs):
    """
    A validator to test whether or not some named properties are unique.
    For those named properties that are not unique, an error will
    be recorded in C{obj.errors}.

    @param obj: The object whose properties need to be tested.
    @param names: The names of the properties to test.
    @param kwargs: Keyword arguments.  Right now, all but a
    C{message} value are ignored.
    """
    message = kwargs.get('message', "is not unique.")    
    def handle(results):
        for propname, value in results.items():
            if value is not None:
                obj.errors.add(propname, message)
    ds = {}
    for name in names:
        where = ["%s = ?" % name, getattr(obj, name, "")]            
        if obj.id is not None:
            where = joinWheres(where, ["id != ?", obj.id])
        d = obj.__class__.find(where=where, limit=1)
        ds[name] = d
    return deferredDict(ds).addCallback(handle)



class Validator(object):
    """
    A mixin class to handle validating objects before they are saved.

    @cvar VALIDATIONS: A C{list} of functions to call when testing whether or
    not a particular instance is valid.
    """
    # list of validation methods to call for this class 
    VALIDATIONS = []

    @classmethod
    def clearValidations(klass):
        """
        Clear the given class's validations.
        """
        klass.VALIDATIONS = []


    @classmethod
    def addValidator(klass, func):
        """
        Add a function to the given classes validation list.

        @param klass: The Class to add the validator to.
        @param func: A function that accepts a single parameter that is the object
        to test for validity.  If the object is invalid, then this function should
        add errors to it's C{errors} property.

        @see: L{Errors}
        """
        # Why do this instead of append? you ask.  Because, I want a new
        # array to be created and assigned (otherwise, all classes will have
        # this validator added).
        klass.VALIDATIONS = klass.VALIDATIONS + [func]


    @classmethod
    def validatesPresenceOf(klass, *names, **kwargs):
        """
        A validator to test whether or not some named properties are set.
        For those named properties that are not set, an error will
        be recorded in C{obj.errors}.
        
        @param klass: The klass whose properties need to be tested.
        @param names: The names of the properties to test.
        @param kwargs: Keyword arguments.  Right now, all but a
        C{message} value are ignored.
        """        
        func = lambda obj: presenceOf(obj, names, kwargs)
        klass.addValidator(func)


    @classmethod
    def validatesUniquenessOf(klass, *names, **kwargs):
        """
        A validator to test whether or not some named properties are unique.
        For those named properties that are not unique, an error will
        be recorded in C{obj.errors}.
        
        @param klass: The klass whose properties need to be tested.
        @param names: The names of the properties to test.
        @param kwargs: Keyword arguments.  Right now, all but a
        C{message} value are ignored.
        """            
        func = lambda obj: uniquenessOf(obj, names, kwargs)
        klass.addValidator(func)


    @classmethod
    def validatesLengthOf(klass, *names, **kwargs):
        """
        A validator to test whether or not some named properties have a
        specific length.  The length is specified in one of two ways: either
        a C{range} keyword set with a C{range} / C{xrange} / C{list} object
        containing valid values, or a C{length} keyword with the exact length
        allowed.

        For those named properties that do not have
        the specified length, an error will be recorded in the instance of C{klass}'s
        C{errors} parameter.

        @param klass: The klass whose properties need to be tested.
        @param names: The names of the properties to test.
        @param kwargs: Keyword arguments.  Right now, all but 
        C{message}, C{range}, and C{length} values are ignored.
        """        
        func = lambda obj: lengthOf(obj, names, kwargs)
        klass.addValidator(func)


    @classmethod
    def _validate(klass, obj):
        """
        Validate a given object using all of the set validators for the objects class.
        If errors are found, they will be recorded in the objects C{errors} property.

        @return: A C{Deferred} whose callback will receive the given object.

        @see: L{Errors}
        """
        ds = [defer.maybeDeferred(func, obj) for func in klass.VALIDATIONS]
        # Return the object when finished
        return defer.DeferredList(ds).addCallback(lambda results: obj)



class Errors(dict):
    """
    A class to hold errors found during validation of a L{DBObject}.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.infl = Inflector()
        
    
    def add(self, prop, error):
        """
        Add an error to a property.  The error message stored for this property will be formed
        from the humanized name of the property followed by the error message given.  For instance,
        C{errors.add('first_name', 'cannot be empty')} will result in an error message of
        "First Name cannot be empty" being stored for this property.

        @param prop: The name of a property to add an error to.
        @param error: A string error to associate with the given property.  
        """
        self[prop] = self.get(prop, [])
        msg = "%s %s" % (self.infl.humanize(prop), str(error))
        if not msg in self[prop]:
            self[prop].append(msg)


    def isEmpty(self):
        """
        Returns C{True} if there are any errors associated with any properties,
        C{False} otherwise.
        """
        for value in self.itervalues():
            if len(value) > 0:
                return False
        return True


    def errorsFor(self, prop):
        """
        Get the errors for a specific property.
        
        @param prop: The property to fetch errors for.
        
        @return: A C{list} of errors for the given property.  If there are none,
        then the returned C{list} will have a length of 0.
        """
        return self.get(prop, [])


    def __str__(self):
        """
        Return all errors as a single string.
        """
        s = []
        for values in self.itervalues():
            for value in values:
                s.append(value)
        if len(s) == 0:
            return "No errors."
        return "  ".join(s)


    def __len__(self):
        """
        Get the sum of all errors for all properties.
        """
        return sum([len(value) for value in self.itervalues()])

########NEW FILE########
