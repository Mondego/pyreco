__FILENAME__ = alg
'''
Created on Aug 19, 2011

@author: alexpak
'''

class Vector:
	def __init__(self, iterable):
		self.setData(iterable)
		
	def setData(self, iterable):
		self._data = list(iterable)

	def __getitem__(self, i):
		return self._data[i]
	
	def __len__(self):
		return len(self._data)
		
	def __add__(self, term):
		data = self._data[:]
		if type(term) in (int, float):
			for i in range(0, len(data)):
				data[i] += term
		elif isinstance(term, Vector):
			for i in range(0, len(self._data)):
				data[i] += term[i]
				
		return Vector(data)
	
	def __sub__(self, term):
		data = self._data[:]
		if type(term) in (int, float):
			for i in range(0, len(data)):
				data[i] -= term
		elif isinstance(term, Vector):
			for i in range(0, len(self._data)):
				data[i] -= term[i]
				
		return Vector(data)
	
	def __iadd__(self, term):
		self.setData(self.__add__(term)) 
		return self
	
	def __repr__(self):
		return '[{0}]'.format(', '.join([str(i) for i in self._data]))
			

class Matrix:
	def __init__(self):
		self._data = None
		
	def __radd__(self, term):
		pass
########NEW FILE########
__FILENAME__ = aot
#!/usr/bin/env python3
import sqlite3
import re
import os
import memcache

class Morphology:
	conn = None
	db = None
	cache = {}
	
	def __init__(self, db, lexicon = None):
		load = False
		if not os.path.exists(db):
			load = True
			
		self.conn = sqlite3.connect(db, check_same_thread = False)
		self.mc = memcache.Client(['127.0.0.1:11211'], debug=0)

#		def re_match(a, b):
#			return re.match(a, b) is not None
#		
#		def concat(a, b):
#			return a + b
#			
#		self.conn.create_function('re_match', 2, re_match)
#		self.conn.create_function('concat', 2, concat)
		
		self.db = self.conn.cursor()

		if load:
			self.load(lexicon)
			
	def close(self):
		self.db.close()
		self.conn.close()
			
	def skip_lines(self, handle):
		line = handle.readline()
		if not len(line):
			return False
		
		line = line.strip()
		if re.search('^\d+$', line):
			for i in range(0, int(line)):
				line = handle.readline()
				if not len(line):
					return False
		else:
			print(line)
			return False 
		
		return True

	def load(self, file):
		handle = open(file, 'r', encoding='cp1251')
		
		# load rules
		self.load_rules(handle)
		
		# skip accents
		if not self.skip_lines(handle):
			return False
		
		# skip logs
		if not self.skip_lines(handle):
			return False
		
		# skip prefixes
		if not self.skip_lines(handle):
			return False
		
		print(self.load_lemmas(handle), 'lemmas loaded')
		
		handle.close()
		
	def load_rules(self, handle):
		# create table
		self.db.execute('''create table rules(
							id integer,
							prefix text,
							suffix text)''')
		
		lines = handle.readline().strip()
		reg_split = re.compile('\\%');
		alf = '\w';
		reg_rule = re.compile('^(?P<suffix>' + alf + '*)\\*(?P<ancode>' + alf + '+)(?:\\*(?P<prefix>' + alf + '+))?$')
		
		for i in range(0, int(lines)):
			line = handle.readline()
			if not len(line):
				break
			
			rules = reg_split.split(line.strip())
			
			for rule in rules:
				match = reg_rule.search(rule)
				if match is not None:
					record = match.groupdict()				  
					if 'prefix' not in record or record['prefix'] is None:
						record['prefix'] = ''
						
					suffix = record['suffix'].lower()
					prefix = record['prefix'].lower()
					
					self.db.execute('insert into rules (id, prefix, suffix) values (?, ?, ?)', (i, prefix, suffix))

		self.db.execute('create index rules_id on rules(id)')
		return i
	
	def load_lemmas(self, handle):
		# create table
		self.db.execute('''create table lemmas(
							base text,
							rule integer)''')

		lines = int(handle.readline().strip())
		reg_split = re.compile('\s+')
		
		for i in range(0, lines):
			line = handle.readline()
			if not len(line):
				break
			
			record = reg_split.split(line)
			self.db.execute('insert into lemmas values(?, ?)', (record[0].lower() + '%', int(record[1])))
			
		self.db.execute('create index lemmas_base on lemmas(base)')
		
		return i
	
	def make_forms(self, lemma):
		self.db.execute('select prefix, suffix from rules where id = ?', (lemma['rule'],))

		forms = []
		for rule in self.db.fetchall():
			forms.append({
						  'base': lemma['base'],
						  'form': rule[0] + lemma['base'] + rule[1],
						  })
		return forms

	def normalize(self, word):
		word = word.lower()

		lemmas = self.mc.get(word)
		if lemmas is None:
#		if word not in self.cache:
			self.db.execute('select base, rule from lemmas where ? like base', (word,))
			
			lemmas = []
			for lemma in self.db.fetchall():
				base = lemma[0][0:-1]
				forms = self.make_forms({'base': base, 'rule': lemma[1]})
				for form in forms:
#					print(word, form['form'])
					if word == form['form']:
						init_form = forms[0]['form']
						lemmas.append(init_form)
						
#			self.cache[word] = set(lemmas)
			lemmas = set(lemmas)
			self.mc.set(word, lemmas)
					
		return lemmas

if __name__ == '__main__':
	from optparse import OptionParser
	parser = OptionParser()
	parser.usage = '%prog [options]'
	parser.add_option('-i', '--index', action='store_const', const=True, dest='index')
	parser.add_option('-d', '--database', action='store', type='string', dest='database')
	
	(options, args) = parser.parse_args()
	if options.index:
		morphology = Morphology(options.database, args[0])
		print('Done')
	else:
		morphology = Morphology(options.database)
		print(morphology.normalize(args[0]))
########NEW FILE########
__FILENAME__ = config
'''
Created on Aug 5, 2011

@author: alexpak <irokez@gmail.com>
'''
import sys
sys.path.append('/home/alexpak/tools/liblinear-1.8/python/')

########NEW FILE########
__FILENAME__ = convert-rnc
#!/usr/bin/env python3
'''
Created on Aug 5, 2011

@author: alexpak <irokez@gmail.com>
'''

import sys
import re

if len(sys.argv) < 2:
	print('Usage: convert-rnc.py inputfile > outputfile')
	exit()
	
skip_lines = [
	'<\?xml version="1.0" encoding="windows-1251"\?><html><head>',
	'</head>',
	'<body>'
]
re_skip = re.compile('|'.join(skip_lines))
re_del = re.compile('<p[^>]+>|</td><td>|</td></tr><tr><td>')
re_fix1 = re.compile('</se>\s?<se>')
re_fix2 = re.compile('<se><se>')
	
print('<?xml version="1.0" encoding="utf-8" ?>')
print('<corpus>')
f = open(sys.argv[1], 'rb')
for line in f:
	line = line.decode('cp1251')

	if re_skip.search(line):
		continue
	
	line = re_del.sub('', line)
	line = re_fix1.sub('</se>', line)
	line = re_fix2.sub('<se>', line)
	
	print(line, end = '')
f.close()
print('</corpus>')
########NEW FILE########
__FILENAME__ = create-lexicon
#!/usr/bin/env python3
'''
Created on Aug 6, 2011

@author: alexpak
'''

import sys
import os
import rnc
import sqlite3

if len(sys.argv) < 3:
	exit('Usage: create-lexicon.py filename dbname')
	
dbname = sys.argv[2]
db_exists = os.path.isfile(dbname)
con = sqlite3.connect(dbname)
cur = con.cursor()

def create_db():
	sql = '''
	create table words(
		id integer primary key autoincrement,
		lemma text,
		form text,
		accent integer,
		info text,
		freq integer
	);
	create index words_lemma_form_info_accent on words(lemma, form, info, accent);
	'''
	[cur.execute(st) for st in sql.split(';') if len(st.strip())]

if not db_exists:
	create_db()

sentences = rnc.Reader().read(sys.argv[1])
for sentence in sentences:
	for word in sentence:
		accent = word[0].index('`') + 1 if '`' in word[0] else 0 
		form = word[0].replace('`', '')
		lemma = word[1]['lex']
		info = word[1]['gr']
		
		cur.execute('select id from words where lemma = ? and form = ? and info = ? and accent = ?', (lemma, form, info, accent))
		row = cur.fetchone()
		if row is None:
			cur.execute('insert into words (lemma, form, info, accent, freq) values (?, ?, ?, ?, 1)', (lemma, form, info, accent))
		else:
			cur.execute('update words set freq = freq + 1 where id = ?', row)
		
con.commit()
con.close()
########NEW FILE########
__FILENAME__ = dep
#!/usr/bin/env python3
'''
Created on Nov 22, 2011

@author: alexpak
'''

import sys
import ml
import math
from ml.svm import SVM as Classifier
#from ml.nb import NaiveBayes as Classifier
from collections import Counter, OrderedDict
import sqlite3
import os
import syntagrus

features = {'m', 'f', 'n', 'nom', 'gen', 'gen2', 'dat', 'acc', 'ins', 'prep', 'loc', 'sg', 'pl', 'real', 'inf', 'advp', 'adjp', 'imp', 'pass', '1p', '2p', '3p'}

class Linker:
	def __init__(self):
		self._cl = Classifier()
	
	def traverse(self, sentences):
		x = []
		y = []
		for sentence in sentences:
			for w in range(0, len(sentence)):
				word_from = sentence[w]
				feats = {}

#				meta1 = word_from[1].pos + '_'.join(sorted(word_from[1].feat & features))
#				feats['f:' + meta1] = 1
				
				for feat in word_from[1].feat & features:
					feats['f:' + feat] = 1
				feats['fp:' + word_from[1].pos] = 1
				feats['fw:' + word_from[0]] = 1
				
				for v in range(0, len(sentence)):
					if v == w:
						continue
					
					word_to = sentence[v]
						
					feats2 = feats.copy()
#					meta2 = word_to[1].pos + '_'.join(sorted(word_to[1].feat & features))
#					feats['t:' + meta2] = 1
					
					for feat in word_to[1].feat & features:
						feats2['t:' + feat] = 1
					for feat in word_from[1].feat & word_to[1].feat:
						feats2['c:' + feat] = 1
					feats2['tp:' + word_to[1].pos] = 1
					feats2['tw:' + word_to[0]] = 1
					feats2['dst'] = float(w - v)
					
					'''
					for i in range(1, 3):
						u = v - i
						if u > 0 or u != w:
							continue
						word_prev = sentence[u]
						for feat in word_prev[1].feat:
							feats2[str(i) + 'p:' + feat] = 1
#						for feat in word_from[1].feat & word_prev[1].feat:
#							feats2[str(i) + 'pfc:' + feat] = 1
#						for feat in word_to[1].feat & word_prev[1].feat:
#							feats2[str(i) + 'ptc:' + feat] = 1
						feats2[str(i) + 'pp:' + word_prev[1].pos] = 1
						#feats2[str(i) + 'pw:' + word_prev[0]] = 1
					'''
						
					
#					if word_from[1].dom != word_to[1].id:
#						continue
					
					x.append(feats2)
#					y.append(word_from[1].link if word_from[1].dom == word_to[1].id else 'none')
					y.append(int(word_from[1].dom == word_to[1].id))
					
			#endfor w
		#endfor sentence
		return (x, y)
	
	def train(self, sentences):
		x, y = self.traverse(sentences)
		self._cl.train_regression(x, y)

	def predict(self, sentences):
		(test_x, test_y) = self.traverse(sentences)
		return (self._cl.predict(test_x), test_y)
	
	def evaluate_bin(self, gold, test):
		tp = 0; fp = 0; tn = 0; fn = 0
		
		for i in range(0, len(gold)):
			if gold[i] != 'none':
				if test[i] == gold[i]:
					tp += 1
				else:
					fn += 1
			else:
				if test[i] == gold[i]:
					tn += 1
				else:
					fp += 1
				
		
		acc = (tp + tn) / (tp + fp + tn + fn) if tp + fp + tn + fn else 0
		pr = tp / (tp + fp) if tp + fp else 0
		rec = tp / (tp + fn) if tp + fn else 0
		f1 = 2 * (pr * rec) / (pr + rec) if pr + rec else 0
		
		return (acc, pr, rec, f1)
	
	def evaluate_mul(self, gold, test):
		tp = 0; fp = 0; tn = 0; fn = 0; cl = 0
		
		for i in range(0, len(gold)):
			if gold[i] != 'none':
				if test[i] != 'none':
					tp += 1
				else:
					fn += 1
					
				if test[i] == gold[i]:
					cl += 1
					
			else:
				if test[i] == 'none':
					tn += 1
				else:
					fp += 1
		
		acc = cl / (tp + fn) if tp + fn else 0
		pr = tp / (tp + fp) if tp + fp else 0
		rec = tp / (tp + fn) if tp + fn else 0
		f1 = 2 * (pr * rec) / (pr + rec) if pr + rec else 0
		
		return (acc, pr, rec, f1)
	
	def test(self, sentences):
		(estim_y, test_y) = self.predict(sentences)
		print(Counter(test_y))
		print(Counter(estim_y))
		return self.evaluate_mul(test_y, estim_y)
	
	def save(self, path):
		self._cl.save(path)
		
	@staticmethod
	def load(path):
		obj = Linker()
		obj._cl = ml.Classifier.load(path)
		return obj
	
def print_table(data, outfile = sys.stdout, maxlen = {}):
	vsep = '|'
	endl = '\n'
	s = ''
	
	keys = []
	maxkey = 0
	for rowkey, row in data.items():
		l = len(str(rowkey))
		if l > maxkey:
			maxkey = l
		for key in row:
			if key not in keys:
				keys.append(key)
			l = len(str(row[key]))
			if key not in maxlen or l > maxlen[key]:
				maxlen[key] = l
		
	for key in keys:
		l = len(str(key))
		if l > maxlen[key]:
			maxlen[key] = l
		if maxlen[key] < 3:
			maxlen[key] = 3
			
	hline = '+' + '-' * maxkey + '+' + '+'.join(['-' * maxlen[key] for key in keys]) + '+'

	s += endl + hline + endl
	s += vsep
	s += ' ' * maxkey
	s += vsep
	s += vsep.join([str(key).ljust(maxlen[key]) for key in keys])
	s += vsep
	s += endl + hline + endl
	
	for rowkey, row in data.items():
		s += vsep
		s += str(rowkey).ljust(maxkey)
		s += vsep
		s += vsep.join([str(row[key] if key in row else '').rjust(maxlen[key]) for key in keys])
		s += vsep
		s += endl + hline + endl
			
	print(s, file=outfile)
	return maxlen
	
class Parser:
	def __init__(self, linker):
		self._linker = linker
		
	def parse(self, sentence):
		table_estim = OrderedDict()
		table_true = OrderedDict()
		rowwords = set()
		
		con = sqlite3.connect('tmp/links')
		cur = con.cursor()
		
		prep = False
		for w in range(0, len(sentence)):
			source = sentence[w]
			source_word = source[0]
			
			if source_word in rowwords:
				source_word += '-' + str(source[1].id)
			else:
				rowwords.add(source_word)
				
			table_estim[source_word] = OrderedDict()
			table_true[source_word] = OrderedDict()
			
			source_feat = ' '.join([source[1].pos] + sorted(source[1].feat))
			
			# root
			target_word = '_root'
			if source[1].pos == 'PR':
				prep = True
				cur.execute('select sum(freq) from links where ffeat = ? and fword = ? and root', (source_feat, source_word))
			else:
				cur.execute('select sum(freq) from links where ffeat = ? and root', (source_feat, ))
				
			table_estim[source_word][target_word] = cur.fetchone()[0] or 0
			table_true[source_word][target_word] = 'root' if source[1].dom == 0 else ''
			
			colwords = set()
			no = False
			for v in range(0, len(sentence)):
				target = sentence[v]
				target_word = target[0]
				if target_word in colwords:
					target_word += '-' + str(target[1].id)
				else:
					colwords.add(target_word)
					
				target_feat = ' '.join([target[1].pos] + sorted(target[1].feat))
				if target[1].pos == 'CONJ' or (target[1].pos == 'PR' and source[1].pos in {'S', 'ADV', 'ADJ'}):
					cur.execute('select sum(freq) from links where ffeat = ? and tfeat = ? and tword = ?', (source_feat, target_feat, target_word))
				elif source[1].pos == 'CONJ' or (source[1].pos == 'PR' and target[1].pos in {'S', 'ADV', 'ADJ'}):
					cur.execute('select sum(freq) from links where ffeat = ? and fword = ? and tfeat = ?', (source_feat, source_word, target_feat))
				else:
					cur.execute('select sum(freq) from links where ffeat = ? and tfeat = ?', (source_feat, target_feat))
#				table_estim[word_from][word_to] = '.' if v == w else round((cur.fetchone()[0] or 0) / (math.log(abs(v - w) + 2)))
				freq = cur.fetchone()[0] or 0
					
				if source[1].pos == 'S' and target[1].pos == 'PR' and w > v and prep:
					freq = 9999
					prep = False

				if source_word == 'не' and w < v and not no:
					freq = 9999
					no = True

				table_estim[source_word][target_word] = '.' if v == w else freq
				table_true[source_word][target_word] = '.' if v == w else source[1].link if source[1].dom == target[1].id else ''
#				table_estim[word_from][word_to] = '.' if v == w else 'x' if estim_y[i] else ''
#				table_true[word_from][word_to] = '.' if v == w else 'x' if test_y[i] else ''

		maxlen = print_table(table_true)
		print_table(table_estim, maxlen = maxlen)
#		'''
		for rowkey, row in table_estim.items():
			maxval = max([int(val) if val != '.' else 0 for val in list(row.values())[1:]])
			for key, val in row.items():
				if key == '_root':
					continue
				if val == '.':
					continue
				if val < maxval:
					table_estim[rowkey][key] = ''
#		'''	
		print_table(table_estim, maxlen = maxlen)
		
	def parse0(self, sentence):
		estim_y, test_y = self._linker.predict([sentence])
		i = 0
		table_estim = OrderedDict()
		table_true = OrderedDict()
		rowwords = set()
		for w in range(0, len(sentence)):
			word_from = sentence[w][0]
			if word_from in rowwords:
				word_from += '-' + str(sentence[w][1].id)
			else:
				rowwords.add(word_from)
				
			table_estim[word_from] = OrderedDict()
			table_true[word_from] = OrderedDict()
			colwords = set()

			for v in range(0, len(sentence)):
				word_to = sentence[v][0]
				if word_to in colwords:
					word_to += '-' + str(sentence[v][1].id)
				else:
					colwords.add(word_to)
#				table_estim[word_from][word_to] = '.' if v == w else round(estim_y[i], 5) if estim_y[i] != 'none' else ''
#				table_true[word_from][word_to] = '.' if v == w else test_y[i] if test_y[i] != 'none' else ''
				table_estim[word_from][word_to] = '.' if v == w else estim_y[i] if estim_y[i] else ''
				table_true[word_from][word_to] = '.' if v == w else 'x' if test_y[i] else ''
				i += v != w
				
		maxlen = print_table(table_true)
		print_table(table_estim, maxlen = maxlen)
		
genders = {'m', 'f', 'n'}
cases = {'nom', 'gen', 'dat', 'acc', 'ins', 'prep', 'gen2', 'loc'}
animacy = {'anim', 'inan'}
number = {'sg', 'pl'}
person = {'1p', '2p', '3p'}
vtypes = {'perf', 'imperf'}
vmood = {'real', 'imp', 'pass'}
vform = {'inf', 'advj', 'advp'}
tenses = {'pst', 'npst', 'prs'}
degree = {'comp', 'supl'}

class Links:
	def __init__(self, dbname):
		self.dbname = dbname
		db_exists = os.path.isfile(dbname)
		self.con = sqlite3.connect(dbname)
		self.cur = self.con.cursor()
		
		if not db_exists:
			self.create_db()		
	
	def create_db(self):
		sql = '''
        create table links(
        	id integer primary key autoincrement,
        	name text,

			fword text,
			ffeat text,
        	fpos text,
			fnum text,
        	fgen text,
			fcase text,
			fpers text,
        	fanim text,
        	ftype text,
        	fmood text,
        	ftens text,
        	fdegr text,

			tword text,
			tfeat text,
			tpos text,
			tnum text,
			tgen text,
			tcase text,
			tpers text,
			tanim text,
			ttype text,
			tmood text,
			ttens text,
			tdegr text,

			root integer,
        	freq integer,
        	dist integer
        );
        create index links_info on links(name, fword, tword, root, ffeat, tfeat, dist);
        create index links_info2 on links(ffeat, tfeat);
        create index links_info3 on links(ffeat, root);
        create index links_info4 on links(ffeat, fword, root);
        create index links_info5 on links(ffeat, fword, tfeat);
        create index links_info6 on links(ffeat, tfeat, tword);
        '''
        
		sql0 = '''
        create table links(
        	id integer primary key autoincrement,
        	name text,

			fword text,
			ffeat text,

			tword text,
			tfeat text,

			root integer,
        	freq integer
        );
        create index links_info on links(name, fword, tword, root, ffeat, tfeat);
        '''
		[self.cur.execute(st) for st in sql.split(';') if len(st.strip())]
		
	def index(self, sentences):
		for sentence in sentences:
			for word_from in sentence:
				is_root = 0
				if word_from[1].dom:
					word_to = sentence[word_from[1].dom - 1]
				else:
					word_to = ('', syntagrus.word_t(lemma='', pos='', dom='', link='root', id=0, feat=set()))
					is_root = 1
				from_feat = ' '.join([word_from[1].pos] + sorted(word_from[1].feat))
				to_feat = ' '.join([word_to[1].pos] + sorted(word_to[1].feat))
			
				fpos = word_from[1].pos
				fnum = (number & word_from[1].feat or {None}).pop()
				fgen = (genders & word_from[1].feat or {None}).pop()
				fcase = (cases & word_from[1].feat or {None}).pop()
				fpers = (person & word_from[1].feat or {None}).pop()
				fanim = (animacy & word_from[1].feat or {None}).pop()
				ftype = (vtypes & word_from[1].feat or {None}).pop()
				fmood = (vmood & word_from[1].feat or {None}).pop()
				ftens = (tenses & word_from[1].feat or {None}).pop()
				fdegr = (degree & word_from[1].feat or {None}).pop()
				
				tpos = word_to[1].pos
				tnum = (number & word_to[1].feat or {None}).pop()
				tgen = (genders & word_to[1].feat or {None}).pop()
				tcase = (cases & word_to[1].feat or {None}).pop()
				tpers = (person & word_to[1].feat or {None}).pop()
				tanim = (animacy & word_to[1].feat or {None}).pop()
				ttype = (vtypes & word_to[1].feat or {None}).pop()
				tmood = (vmood & word_to[1].feat or {None}).pop()
				ttens = (tenses & word_to[1].feat or {None}).pop()
				tdegr = (degree & word_to[1].feat or {None}).pop()
				
				dist = word_to[1].id - word_from[1].id
				
				self.cur.execute('select id from links where name = ? and fword = ? and tword = ? and root = ? and ffeat = ? and tfeat = ? and dist = ?', (word_from[1].link, word_from[0].lower(), word_to[0].lower(), is_root, from_feat, to_feat, dist))
				row = self.cur.fetchone()
				if row is None:
					sql = '''
					insert into links (name, fword, tword, root, ffeat, tfeat, freq, dist,
					fpos, fnum, fgen, fcase, fpers, fanim, ftype, fmood, ftens, fdegr, 
					tpos, tnum, tgen, tcase, tpers, tanim, ttype, tmood, ttens, tdegr
					) values (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
					'''
					self.cur.execute(sql, (word_from[1].link, word_from[0].lower(), word_to[0].lower(), is_root, from_feat, to_feat, dist, fpos, fnum, fgen, fcase, fpers, fanim, ftype, fmood, ftens, fdegr, tpos, tnum, tgen, tcase, tpers, tanim, ttype, tmood, ttens, tdegr))
				else:
					self.cur.execute('update links set freq = freq + 1 where id = ?', row)
					
	def close(self):
		self.con.commit()
		self.con.close()
		
if __name__ == '__main__':
	import glob
	from optparse import OptionParser
	import syntagrus
	
	parser = OptionParser()
	parser.usage = '%prog [options]'
	
	(options, args) = parser.parse_args()
	
	if not len(args):
		files = glob.glob('res/*/*/*.tgt')
		corpus = []
		for file in files[0:10]:
			R = syntagrus.Reader()
			sentences = R.read(file)
			corpus.extend(sentences)
			del(R)

		fold_size = round(len(corpus) / 10)
		
		train_set = corpus[0:-fold_size]
		test_set = corpus[-fold_size:]
		
		print('{0} sentences'.format(len(corpus)))
		
		del(corpus)

		'''
				
		L = Links('tmp/links')
		L.index(train_set)
		L.close()
		exit()
		'''
		
		'''
		
		L = Linker()
		L.train(train_set)	
#		results = L.test(test_set)
#		print('Accuracy = {0[0]:.3f}, precision = {0[1]:.3f}, recall = {0[2]:.3f}, F1 = {0[3]:.3f}'.format(results))
		'''
		L = None

		P = Parser(L)
		example = test_set[6] #6
		for word in example:
			print(word)
		P.parse(example)

########NEW FILE########
__FILENAME__ = nb
'''
Created on Aug 17, 2011

@author: alexpak
'''

import math
from collections import defaultdict
from .. import ml

class NaiveBayes(ml.Classifier):
	def __init__(self):
		pass
	
	def __repr__(self):
		return 'NaiveBayes'
	
	def _gaus(self, i, mean, var):
		return (1 / math.sqrt(2 * math.pi * var) * math.exp(- (i - mean) ** 2 / (2 * var))) if var > 0 else float(1 if i == mean else 0)
			

	def _prob(self, C, dim, val):
		p = 0
		if dim in self._P[C]:
			p = self._P[C][dim]
		elif dim in self._F[C]:
			p = self._gaus(val, self._F[C][dim][0], self._F[C][dim][1])
			
		return p
	
	def train(self, x, y):
		data = defaultdict(list)
		labels = set()
		discrete_features = set()
		numeric_features = set()
		i = 0
		for C in y:
			labels.add(C)
			data[C].append(x[i])
			for dim in x[i]:
				if isinstance(x[i][dim], float): 
					numeric_features.add(dim)
				else:
					discrete_features.add(dim)
			i += 1
		
		ndim = len(discrete_features)

		# train discrete features
		P = {}
		for C in data:
			count = defaultdict(int)
			total = 0
			for sample in data[C]:
				for dim, val in sample.items():
					if dim in discrete_features:
						count[dim] += val
						total += val
			
			P[C] = {}
			for dim in discrete_features:
				P[C][dim] = (1 + count[dim]) / (ndim + total)
		self._P = P
				
		# train numeric features
		F = {}
		for C in data:
			F[C] = {}
			n = 0
			for dim in numeric_features:
				n += 1
				mean = 0; var = 0; N = 0
				
				# calculate mean and length
				for sample in data[C]:
					mean += sample[dim] if dim in sample else 0
					N += 1
				mean /= N
				
				# calculate variance
				for sample in data[C]:
					var += (mean - (sample[dim] if dim in sample else 0)) ** 2
				var /= (N - 1) if N > 1 else N
				
				F[C][dim] = (mean, var)
								
		self._F = F
	
	def predict(self, x, return_likelihood = False):
		y = []
		for sample in x:
			L = defaultdict(float)
			for C in self._P:
				for dim in sample:
					L[C] += math.log(self._prob(C, dim, sample[dim]) or 1)
					
#			y.append(max(L.keys(), key = lambda i: L[i]) if len(L) else next(iter(self._P)))
			if return_likelihood:
				y.append(L)
			else:
				y.append(max(L.keys(), key = lambda i: L[i]) if len(L) else None)
			
		return y
	

########NEW FILE########
__FILENAME__ = nn
'''
Created on Aug 18, 2011

@author: alexpak
'''

import ml
import math
import random
from collections import defaultdict

random.seed()

class Perceptron(ml.Classifier):
	def __init__(self, Nh):
		self.Nh = Nh
		
		self._labels = ml.Autoincrement()
		self._features = ml.Autoincrement()
		
	def _init(self, Ni, Nh, No):
		self.momentum = 0.9
		self.learn_rate = 0.5
		
		self._Wh = [[self._seed() for _ in range(0, Ni)] for __ in range(0, Nh)]
		self._Wo = [[self._seed() for _ in range(0, Nh)] for __ in range(0, No)]
		
		self._dWh = [[0] * Ni] * Nh
		self._dWo = [[0] * Nh] * No

	def get_class_id(self, C):
		if C not in self._class_ids:
			self._class_ids[C] = len(self._class_ids)
		
	def _seed(self):
		return (random.random() - 0.5)
		
	def _sigmod(self, x):
		return x
		return 1 / (1 + math.exp(-x))
	
	def _calc_layer(self, input, W):
		output = []
		for i in range(0, len(W)):
			s = 0
			for j in range(0, len(W[i])):
				s += W[i][j] * input[j]
			output.append(self._sigmod(s))
			
		return output

	def _propagate(self, input):
		self._pi = input
		self._ph = self._calc_layer(self._pi, self._Wh)
		self._po = self._calc_layer(self._ph, self._Wo)
		return self._po
	
	def _backpropagate(self, output):
		# delta's for output layer 
		do = []
		for i in range(0, len(self._Wo)):
			print(output[i], self._po[i])
			do.append(self._po[i] * (1 - self._po[i]) * (output[i] - self._po[i]))
#		print(do)
			
		# correct output layer weights
		for i in range(0, len(self._Wo)):
			for j in range(0, len(self._Wo[i])):
				self._dWo[i][j] = self.momentum * self._dWo[i][j] + (1 - self.momentum) * self.learn_rate * do[i] * self._ph[j]
				self._Wo[i][j] += self._dWo[i][j]
				
		# delta's for hidden layer
		dh = []
		for i in range(0, len(self._Wh)):
			d = 0
			for j in range(0, len(self._Wo)):
				d += do[j] * self._Wo[j][i]
			d *= self._ph[i] * (1 - self._ph[i])
			dh.append(d)
#		print(dh)
			
		# correct hidden layer weights
		for i in range(0, len(self._Wh)):
			for j in range(0, len(self._Wh[i])):
				self._dWh[i][j] = self.momentum * self._dWh[i][j] + (1 - self.momentum) * self.learn_rate * dh[i] * self._pi[j]
				self._Wh[i][j] += self._dWh[i][j]

		print(self._Wo)
		print(self._Wh)
		print()
	
	def train(self, x, y):
		labels = [self._labels.setId(C) for C in y]
		data = []
		for sample in x:
			data.append(defaultdict(float, [(self._features.setId(d), sample[d]) for d in sample]))
			
		self._init(self._features.count(), self.Nh, self._labels.count())

		epsilon = 1e-3
		for epoch in range(1, 10):
			i = 0
			error = 0
			for sample in data:
				output = self._propagate(sample)
				target = defaultdict(float)
				target[labels[i] - 1] = 1
				self._backpropagate(target)
				for j in range(0, len(output)):
					error += (output[j] - target[j]) ** 2
					
				i += 1
			
			print(error)
			print()
			if error < epsilon:
				break
			
	def predict(self, x):
		y = []
		for sample in x:
			output = self._propagate(defaultdict(float, [(self._features.getId(d), sample[d]) for d in sample]))
			which_max = max(range(0, len(output)), key = lambda i: output[i])
			y.append(self._labels.getVal(which_max + 1))
			
		return y
########NEW FILE########
__FILENAME__ = svm
'''
Created on Aug 18, 2011

@author: alexpak
'''
import sys
sys.path.append('/home/alexpak/tools/liblinear-1.8/python/')

import liblinearutil as liblinear
from .. import ml
import pickle

class SVM(ml.Classifier):
	def __init__(self):
		self._labels = ml.Autoincrement()
		self._features = ml.Autoincrement()
		self._regression = False

	def __repr__(self):
		return 'SVM'
	
	def save(self, path):
		liblinear.save_model(path + '-model', self._model)
		del(self._model)
		ml.Classifier.save(self, path)
		
	@staticmethod
	def load(path):
		obj = ml.Classifier.load(path)
		obj._model = liblinear.load_model(path + '-model')
		return obj
	
	def train(self, x, y, biased = False):
		data = []
		for sample in x:
			data.append(dict([(self._features.setId(d), sample[d]) for d in sample]))
			
		labels = [self._labels.setId(C) for C in y]
		if self._labels.count() == 2:
			labels = [1 if label == 1 else -1 for label in labels]
			param = liblinear.parameter('-c 1 -s 2 -q' + (' -B {0}'.format(biased) if biased else ''))
		else:
			param = liblinear.parameter('-c 1 -s 4 -q' + (' -B {0}'.format(biased) if biased else ''))
		prob = liblinear.problem(labels, data)
		self._model = liblinear.train(prob, param)
		
	def train_regression(self, x, y):
		data = []
		for sample in x:
			data.append(dict([(self._features.setId(d), sample[d]) for d in sample]))
			
		self._regression = True
		param = liblinear.parameter('-c 1 -s 0')
		prob = liblinear.problem(y, data)
		self._model = liblinear.train(prob, param)

	def predict(self, x):
		y = []
		for sample in x:
			data = dict([(self._features.getId(d), sample[d]) for d in sample if self._features.getId(d)])
			label, _, _ = liblinear.predict([0], [data], self._model, '')
			if self._regression:
				y.append(label[0])
			else:
				if self._labels.count() == 2:
					label[0] = 1 if label[0] == 1 else 2
				y.append(self._labels.getVal(label[0]))
			
		return y
########NEW FILE########
__FILENAME__ = morph
#!/usr/bin/env python3
'''
Created on Nov 21, 2011

@author: alexpak
'''

import sys

from yatk import ml
from yatk.ml import svm
from yatk.ml.svm import SVM as Classifier
from collections import Counter

sys.modules['ml'] = ml
sys.modules['ml.svm'] = svm

def intersects_classes(classes):
	return lambda w: (w[1].feat & classes).pop()

def intersects_classes_or_none(classes, none):
	return lambda w: (w[1].feat & classes or {none}).pop()

def has_classes(pos, classes):
	return lambda w: w[1].pos == pos and w[1].feat & classes

def pos_equals(pos):
	return lambda w: w[1].pos == pos

def has_class(a_class):
	return lambda w: int(a_class in w[1].feat)
	
pos = {'S', 'A', 'V', 'ADV', 'NID', 'NUM', 'PR', 'PART', 'CONJ', 'COM', 'INTJ', 'P', 'UNK'}

genders = {'m', 'f', 'n'}
cases = {'nom', 'gen', 'dat', 'acc', 'ins', 'prep', 'gen2', 'loc'}
animacy = {'anim', 'inan'}
number = {'sg', 'pl'}
person = {'1p', '2p', '3p'}
vtypes = {'perf', 'imperf'}
vmood = {'real', 'imp', 'pass'}
vform = {'inf', 'advj', 'advp'}
tenses = {'pst', 'npst', 'prs'}
degree = {'comp', 'supl'}

cats = [
	('pos', lambda w: True, lambda w: w[1].pos),
	
	('s-gender', has_classes('S', genders), intersects_classes(genders)),
	('s-case', has_classes('S', cases), intersects_classes(cases)),
	('s-animacy', has_classes('S', animacy), intersects_classes(animacy)),
	('s-number', has_classes('S', number), intersects_classes(number)),

	('v-form', pos_equals('V'), intersects_classes_or_none(vform, 'pers')),
	('v-person', has_classes('V', person), intersects_classes(person)),
	('v-number', has_classes('V', number), intersects_classes(number)),
	('v-gender', has_classes('V', genders), intersects_classes(genders)),
	('v-type', has_classes('V', vtypes), intersects_classes(vtypes)),
	('v-tense', has_classes('V', tenses), intersects_classes(tenses)),
	('v-mood', has_classes('V', vmood), intersects_classes(vmood)),

	('vadj-number', has_classes('VADJ', number), intersects_classes(number)),
	('vadj-gender', has_classes('VADJ', genders), intersects_classes(genders)),
	('vadj-type', has_classes('VADJ', vtypes), intersects_classes(vtypes)),
	('vadj-tense', has_classes('VADJ', tenses), intersects_classes(tenses)),
	('vadj-mood', has_classes('VADJ', vmood), intersects_classes(vmood)),
	('vadj-case', has_classes('VADJ', cases), intersects_classes(cases)),
	
	('a-gender', has_classes('A', genders), intersects_classes(genders)),
	('a-case', has_classes('A', cases), intersects_classes(cases)),
	('a-number', has_classes('A', number), intersects_classes(number)),
	('a-degree', pos_equals('A'), intersects_classes_or_none(degree, 'ncomp')),
	('a-short', pos_equals('A'), has_class('shrt')),
	('a-animacy', has_classes('A', animacy), intersects_classes(animacy)),

	('adv-comp', pos_equals('ADV'), intersects_classes_or_none(degree, 'ncomp')),
	
	('num-gender', has_classes('NUM', genders), intersects_classes(genders)),
	('num-case', has_classes('NUM', cases), intersects_classes(cases)),
	('num-number', has_classes('NUM', number), intersects_classes(number)),
	('num-degree', pos_equals('NUM'), intersects_classes_or_none(degree, 'ncomp')),
]

class Guesser:
	def __init__(self):
		self._cl = Classifier()
		
	def is_candidate(self, word):
		return True
		
	def make_class(self, word):
		pass
		
	def traverse(self, sentences):
		x = []
		y = []
		for sentence in sentences:
			for w in range(0, len(sentence)):
				word = sentence[w]
				
				if not self.is_candidate(word):
					continue
				
				x.append(self.gen_features(sentence, w))
				y.append(self.make_class(word))
				
		return (x, y)
	
	def train(self, sentences):
		(train_x, train_y) = self.traverse(sentences)
		self._cl.train(train_x, train_y)
	
	def predict(self, sentences):
		(test_x, test_y) = self.traverse(sentences)
		return (self._cl.predict(test_x), test_y)
	
	def test(self, sentences):
		(estim_y, test_y) = self.predict(sentences)
		return self._cl.evaluate(test_y, estim_y)
	
	def guess(self, word):
		return self._cl.predict([self.gen_features([(word,)], 0)])[0]
	
	def gen_features(self, sentence, w):
		word = sentence[w][0]
		x = {}
		
		x['p3:' + word[0:3]] = 1
		x['p4:' + word[0:4]] = 1
		x['p5:' + word[0:5]] = 1
		x['p6:' + word[0:6]] = 1
#		x['s1:' + word[-1:]] = 1
		x['s2:' + word[-2:]] = 1
		x['s3:' + word[-3:]] = 1
		x['s4:' + word[-4:]] = 1
		x['s5:' + word[-5:]] = 1
		x['w:' + word] = 1
		
		for i in range(1, 4):
			if w > i - 1:
				word = sentence[w - i][0]
#				x[str(i) + 'p3:' + prev[0:3]] = 1
#				x[str(i) + 'p4:' + prev[0:4]] = 1
#				x[str(i) + 'p5:' + prev[0:5]] = 1
#				x[str(i) + 'p6:' + prev[0:6]] = 1
		#		x['s1:' + word[-1:]] = 1
				x[str(i) + 's2:' + word[-2:]] = 1
				x[str(i) + 's3:' + word[-3:]] = 1
				x[str(i) + 's4:' + word[-4:]] = 1
#				x[str(i) + 's5:' + prev[-5:]] = 1
				x[str(i) + 'w:' + word] = 1
				
		for i in range(1, 2):
			if w + i < len(sentence) - 1:
				word = sentence[w + i][0]
#				x[str(i) + 'p3:' + prev[0:3]] = 1
#				x[str(i) + 'p4:' + prev[0:4]] = 1
#				x[str(i) + 'p5:' + prev[0:5]] = 1
#				x[str(i) + 'p6:' + prev[0:6]] = 1
		#		x['s1:' + word[-1:]] = 1
				x[str(i) + '+s2:' + word[-2:]] = 1
				x[str(i) + '+s3:' + word[-3:]] = 1
				x[str(i) + '+s4:' + word[-4:]] = 1
#				x[str(i) + 's5:' + prev[-5:]] = 1
				x[str(i) + '+w:' + word] = 1
		
		return x
	
	def save(self, path):
		self._cl.save(path)
		
	@staticmethod
	def load(path):
		obj = Guesser()
		obj._cl = Classifier.load(path)
		return obj
	
class Tagger:
	def __init__(self):
		self._pos = Guesser.load('res/model/pos')
		self._guesser = {}
		for cat in cats:
			self._guesser[cat[0]] = Guesser.load('res/model/' + cat[0])
	
	def label(self, sentence):
		tagged = self._pos.predict([sentence])[0]
		feats = {}
		for cat, guesser in self._guesser.items():
			feats[cat] = guesser.predict([sentence])[0]
			
		labeled = []
		for w in range(0, len(sentence)):
			pos = tagged[w]
			feat = []
			cats = []
			if pos == 'S':
				cats = ['s-number', 's-case', 's-animacy']
				if True or feats['s-number'][w] == 'sg':
					feat.append(feats['s-gender'][w])
			elif pos == 'A':
				cats = ['a-number', 'a-degree']
				if feats['a-short'][w]:
					feat.append('shrt')
				else:
					feat.append(feats['a-case'][w])
				if feats['a-number'][w] == 'sg':
					feat.append(feats['a-gender'][w])
			elif pos == 'NUM':
				cats = ['num-gender', 'num-number', 'num-case', 'num-degree']
			elif pos == 'V':
				cats = ['v-number', 'v-tense', 'v-mood', 'v-type']
				if feats['v-tense'][w] == 'pst':
					if feats['v-number'][w] == 'sg':
						feat.append(feats['v-gender'][w])
				else:
					feat.append(feats['v-person'][w])
					
			elif pos == 'VINF':
				cats = ['v-type']
			elif pos == 'VADV':
				cats = ['v-type', 'v-tense']
			elif pos == 'VADJ':
				cats = ['vadj-number', 'vadj-gender', 'vadj-tense', 'vadj-type', 'vadj-mood']
				if feats['a-short'][w]:
					feat.append('shrt')
				else:
					feat.append(feats['vadj-case'][w])
					feat.append(feats['a-degree'][w])
				if feats['vadj-number'][w] == 'sg':
					feat.append(feats['vadj-gender'][w])
			elif pos == 'ADV':
				cats = ['adv-comp']
					
			for cat in cats:
				feat.append(feats[cat][w])
				
			featset = set(feat) - {'ncomp'}
				
			labeled.append((sentence[w][0], pos, featset))

		return labeled
	
if __name__ == '__main__':
	import glob
	from optparse import OptionParser
	import syntagrus
	
	parser = OptionParser()
	parser.usage = '%prog [options]'
	
	(options, args) = parser.parse_args()
	
	if not len(args):
		files = glob.glob('res/*/*/*.tgt')
		corpus = []
		for file in files:
			R = syntagrus.Reader()
			sentences = R.read(file)
			corpus.extend(sentences)
			del(R)
			
		print(len(corpus))
		
		fold_size = round(len(corpus) / 2)
		
		train_set = corpus[0:-fold_size]
		test_set = corpus[-fold_size:]
		del(corpus)
		
		for cat in cats:
			G = Guesser()
			G.is_candidate = cat[1]
			G.make_class = cat[2]
			G.train(train_set)
			results = G.test(test_set)
			G.save('res/model/' + cat[0])
			del(G)
			print('{0}\t\t{1:.3f}%'.format(cat[0], results[0] * 100))
		
	else:
		T = Tagger()
		print('Loaded')
		words = args[0].split(' ')
		sentence = []
		for word in words:
			sentence.append((word, tuple()))
			
		labeled = T.label(sentence)
		for word in labeled:
			print(word)

########NEW FILE########
__FILENAME__ = mstparser
#!/usr/bin/env python3
'''
Created on Nov 29, 2011

@author: alexpak
'''

if __name__ == '__main__':
	import glob
	from optparse import OptionParser
	import syntagrus
	import sys
	import morph
	
	parser = OptionParser()
	parser.usage = '%prog [options]'
	parser.add_option('-t', '--train', action='store_const', const=True, dest='train', help='generate train file')
	parser.add_option('-T', '--test', action='store_const', const=True, dest='test', help='generate test file')
	parser.add_option('-n', '--number', action='store', dest='number', type='int', help='number of files to process')
	parser.add_option('-f', '--format', action='store', dest='format', type='string', help='output format')
	parser.add_option('-M', '--nomorph', action='store_const', const=True, dest='nomorph', help='do not use morphology from annotations')

	(options, args) = parser.parse_args()

	if not options.train and not options.test:
		print('Specify --train or --test', file=sys.stderr)
		exit()

	if not options.number:
		print('Specify number of files -n', file=sys.stderr)
		exit()

	if not len(args):
		files = glob.glob('res/*/*/*.tgt')
		corpus = []
		for file in files[0:options.number]:
			R = syntagrus.Reader()
			sentences = R.read(file)
			corpus.extend(sentences)
			del(R)

		fold_size = round(len(corpus) / 10)
		
		train_set = corpus[0:-fold_size]
		test_set = corpus[-fold_size:]
		
		print('{0} sentences'.format(len(corpus)), file=sys.stderr)
		
		del(corpus)
		
		a_set = test_set if options.test else train_set
		
		if options.nomorph:
			Tagger = morph.Tagger()
			for sentence in a_set:
				labeled = Tagger.label(sentence)
				for w in range(0, len(sentence)):
					sentence[w] = (sentence[w][0], sentence[w][1]._replace(pos=labeled[w][1], feat=labeled[w][2]))
			
		selected_feat = {'m', 'f', 'n', 'sg', 'pl', '1p', '2p', '3p', 'nom', 'gen', 'gen2', 'dat', 'acc', 'ins', 'prep', 'loc', 'real', 'imp', 'pass', 'comp', 'shrt'}		
		#selected_feat = {'nom', 'gen', 'gen2', 'dat', 'acc', 'ins', 'prep', 'loc', 'real', 'imp', 'pass', 'comp', 'shrt'}		
		
		if options.format == 'malt':
			# Malt TAB format
			for sentence in a_set:
				for word in sentence:
					w = word[0] or 'FANTOM'
					p = '.'.join([word[1].pos] + sorted(word[1].feat & selected_feat))
					l = word[1].link if word[1].dom else 'ROOT'
					d = str(word[1].dom)
					print('\t'.join([w, p, d, l]))
				print('')
					
		else:
			# MSTParser format
			for sentence in a_set:
				wn = []
				pn = []
				ln = []
				dn = []
				for word in sentence:
					wn.append(word[0] or 'FANTOM')
					pn.append('-'.join([word[1].pos] + sorted(word[1].feat & selected_feat)))
					ln.append(word[1].link if word[1].dom else 'ROOT')
					dn.append(str(word[1].dom))
					
				print('\t'.join(wn))
				print('\t'.join(pn))
				print('\t'.join(ln))
				print('\t'.join(dn))
				print('')

########NEW FILE########
__FILENAME__ = cyk
'''
Created on Sep 6, 2011

@author: alexpak
'''

from collections import defaultdict

class CYK:
    literals = set()
    nonterminal = set()
    rules = []
    
    index = defaultdict(set)
    rindex = defaultdict(set)
    
    def __init__(self, grammar):
        candidates = set()
        for rule in grammar:
            self.rules.append(rule)
            self.nonterminal.add(rule[0])
            
            if len(rule) == 2:
                candidates.add(rule[1])
                
        self.literals = candidates - self.nonterminal
        
        for n in range(0, len(self.rules)):
            rule = self.rules[n]
            if len(rule) == 2:
                self.rindex[rule[1]].add(n)
                
            self.index[rule[0]].add(n)
            
    def tokenize(self, str):
        return str.split(' ')

    def parse(self, str):
        tokens = self.tokenize(str)
        
        P = {};
        len_tokens = len(tokens)
        
        # returns positions of matching components or empty list
        def match(rule, start, length):
            if len(rule) == 1:
                result = [length] if rule[0] in P[start][length] else []
            else:
                result = []
                for l in range(1, length):
                    if start + l > len_tokens:
                        break

                    if rule[0] not in P[start][l]:
                        continue
                    
                    tail = match(rule[1:], start + l, length - l)
                    if not len(tail):
                        continue
                    result = [l] + tail
                    break
                    
            return result
        
        # start at the leafs
        for p in range(0, len_tokens):
            tokenset = set(tokens[p])
            P[p] = {1: defaultdict(set)}
            while len(tokenset):
                new_tokenset = set()
                for token in tokenset:
                    for n in self.rindex[token]:
                        rule = self.rules[n]
                        P[p][1][rule[0]].add(n)
                        new_tokenset.add(rule[0])
                        
                tokenset = new_tokenset
                    
        for l in range(2, len_tokens + 1): # length
            for p in range(0, len_tokens): # position
                P[p][l] = defaultdict(set)
                for n in range(0, len(self.rules)):
                    rule = self.rules[n]
                    matching = match(rule[1:], p, l)
                    if matching:
                        P[p][l][rule[0]].add((n, tuple(matching)))
        
        self.P = P
        self.tokens = tokens
        
        return len(P[0][len_tokens])
    
    def build_tree(self):
        def build(head, start, length):
            for matching in self.P[start][length][head]:
                if type(matching) == tuple:
                    rule_n, lengths = matching
                    rule = self.rules[rule_n]
                    root = [head]
                    start = start
                    for i in range(0, len(rule) - 1):
                        root.append(build(rule[i + 1], start, lengths[i]))
                        start += lengths[i]
                else:
                    rule = self.rules[matching]
                    if rule[1] in self.literals:
                        root = [head, rule[1]]
                    else:
                        root = [head, build(rule[1], start, length)]
                    
                return tuple(root)
            
        return build('EX', 0, len(self.tokens))
    
    def print_tree(self, tree, padding = '', pad_with = '\t'):
        if len(tree) == 2 and tree[1] in self.literals:
            print('{0}({1} "{2}")'.format(padding, tree[0], tree[1]))
        else:
            print('{0}({1}'.format(padding, tree[0]))
            for branch in tree[1:]:
                self.print_tree(branch, padding + pad_with, pad_with)
            print('{0})'.format(padding))
########NEW FILE########
__FILENAME__ = pos
'''
Created on Aug 4, 2011

@author: alexpak <irokez@gmail.com>
'''
import config
import liblinearutil as svm

tagset = ['S', 'A', 'NUM', 'A-NUM', 'V', 'ADV', 'PRAEDIC', 'PARENTH', 'S-PRO', 'A-PRO', 'ADV-PRO', 'PRAEDIC-PRO', 'PR', 'CONJ', 'PART', 'INTJ', 'INIT', 'NONLEX']
tag_id = {}
tag_inv = {}
for i in range(0, len(tagset)):
	tag_id[tagset[i]] = i + 1
	tag_inv[i + 1] = tagset[i]

class Tagger:
	def __init__(self):
		self.chain_len = 3
		self._features = TaggerFeatures()
		pass
	
	def load(self, modelname, featuresname):
		self._svm_model = svm.load_model(modelname)
		self._features.load(open(featuresname, 'rb'))
		
	def save(self, modelname, featuresname):
		svm.save_model(modelname, self._svm_model)
		self._features.save(open(featuresname, 'wb'))
		
	def get_label_id(self, pos):
		return tag_id[pos] if pos in tag_id else 0
	
	def get_label(self, id):
		return tag_inv[id] if id in tag_inv else '?'
		
	def train(self, sentences, labels, cross_validation = False):
		x = []
		y = []
		
		for i in range(0, len(sentences)):
			sentence = sentences[i]
			prev = []
			
			j = 0
			for word in sentence:
				body = word.lower()
				
				featurespace = self._construct_featurespace(body, prev)
				
				prev.append((body, labels[i][j]))
				if len(prev) > self.chain_len:
					del(prev[0])
					
				x.append(featurespace.featureset)
				j += 1

			y.extend(labels[i])

		prob = svm.problem(y, x)
		
		if cross_validation:
			param = svm.parameter('-c 1 -v 4 -s 4')
			svm.train(prob, param)
		else:
			param = svm.parameter('-c 1 -s 4')
			self._svm_model = svm.train(prob, param)
	
	def label(self, sentence):
		labeled = []
		prev = []
		for word in sentence:
			body = word.lower()
			
			featurespace = self._construct_featurespace(body, prev)
			
			p_label, _, _ = svm.predict([0], [featurespace.featureset], self._svm_model, '')
			label = p_label[0]
			
			prev.append((body, label))
			if len(prev) > self.chain_len:
				del(prev[0])
				
			labeled.append((word, label))
			
		return labeled
				
	def _construct_featurespace(self, word, prev):
		featurespace = ml.FeatureSpace()
			
		featurespace.add({1: len(word)}, 10)
		featurespace.add(self._features.from_suffix(word))
		featurespace.add(self._features.from_prefix(word))
		featurespace.add(self._features.from_body(word))
		
		for item in prev:
			featurespace.add({1: item[1]}, 100)
#			featurespace.add(features.from_suffix(item[0]))
#			featurespace.add(features.from_prefix(item[0]))
#			featurespace.add(features.from_body(item[0]))
	
		return featurespace
	
				
import pickle
import ml
class TaggerFeatures:
	def __init__(self):
		self._body_id = {}
		self._suffix_id = {}
		self._prefix_id = {}
		
		self._train = True
		self._featurespace = ml.FeatureSpace()
		
	def load(self, fp):
		(self._body_id, self._suffix_id, self._prefix_id) = pickle.load(fp)
		self._train = False
		
	def save(self, fp):
		pickle.dump((self._body_id, self._suffix_id, self._prefix_id), fp)

	def from_body(self, body):
		featureset = {}
		if self._train:
			if body not in self._body_id:
				self._body_id[body] = len(self._body_id) + 1
					
			featureset[self._body_id[body]] = 1
		else:
			if body in self._body_id:
				featureset[self._body_id[body]] = 1
				
		return featureset
	
	def from_suffix(self, body):
		featureset = {}
		
		suffix2 = body[-2:]
		if suffix2 not in self._suffix_id:
			self._suffix_id[suffix2] = len(self._suffix_id) + 1
		featureset[self._suffix_id[suffix2]] = 1
		
		suffix3 = body[-3:]
		if suffix3 not in self._suffix_id:
			self._suffix_id[suffix3] = len(self._suffix_id) + 1
		featureset[self._suffix_id[suffix3]] = 1
		
		return featureset
	
	def from_prefix(self, body):
		featureset = {}
		
		prefix2 = body[:2]
		if prefix2 not in self._prefix_id:
			self._prefix_id[prefix2] = len(self._prefix_id) + 1
		featureset[self._prefix_id[prefix2]] = 1
		
		prefix3 = body[:3]
		if prefix3 not in self._prefix_id:
			self._prefix_id[prefix3] = len(self._prefix_id) + 1
		featureset[self._prefix_id[prefix3]] = 1
		
		return featureset
########NEW FILE########
__FILENAME__ = rnc
'''
Created on Aug 5, 2011

@author: alexpak <irokez@gmail.com>
'''
import xml.parsers.expat

class Reader:
	def __init__(self):
		self._parser = xml.parsers.expat.ParserCreate()
		self._parser.StartElementHandler = self.start_element
		self._parser.EndElementHandler = self.end_element
		self._parser.CharacterDataHandler = self.char_data		
	
	def start_element(self, name, attr):
		if name == 'ana':
			self._info = attr
	
	def end_element(self, name):
		if name == 'se':
			self._sentences.append(self._sentence)
			self._sentence = []
		elif name == 'w':
			self._sentence.append((self._cdata, self._info))
		elif name == 'ana':
			self._cdata = ''
	
	def char_data(self, content):
		self._cdata += content
		
	def read(self, filename):
		f = open(filename)
		content = f.read()
		f.close()
		
		self._sentences = []
		self._sentence = []
		self._cdata = ''
		self._info = ''
		
		self._parser.Parse(content)		
		
		return self._sentences
########NEW FILE########
__FILENAME__ = demo
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Aug 7, 2011

@author: alexpak
'''

import cherrypy
import sys
import time
import cgi
import os
import requests
import json

path = os.path.dirname(os.path.abspath(__file__)) + '/'

f = open(path + 'demo.html', 'rb')
content = f.read().decode()
f.close()

from pyrus.src import template
from yatk import ir
from yatk.ml.svm import SVM as Classifier
from red import pie

TTL = 60

r = pie.Redis()
cl = Classifier.load('test.svm')
index = ir.SentimentIndex.load('test.index', 'delta', 'bogram')
index.get_text = lambda x: x['text']

class HelloWorld:
	@cherrypy.expose
	def index(self, q = ''):
		start = time.time()
		q = q.strip()
		error = ''

		T = template.Template()

		if len(q):
			cached = r.get(q)

			if not cached:
				url = 'http://search.twitter.com/search.json'
				req = requests.get(url, params={'q': q})
				data = json.loads(req.text)

				if 'results' not in data:
					print('Error')
					print(data)
					exit()

				cached = json.dumps(data['results'])
				r.setex(q, TTL, cached)

			results = json.loads(cached)

			docs = []

			for msg in results:
				feats = index.weight(index.features(msg))
				docs.append(feats)

			labels = cl.predict(docs)
			output = []
			for n in range(len(results)):
				output.append((labels[n], results[n]['text']))

			end = time.time()

			T.q = cgi.escape(q)
			T.output = output			
			T.time_total = round(end - start, 1)
			T.msgs = len(output)
			T.msgs_per_sec = round(len(output) / (end - start), 1)

		T.error = error


		return T.transform(content)
	
	@cherrypy.expose
	def test(self):
		return content

cherrypy.server.socket_host = '0.0.0.0'
config = {
	'/': {
		'tools.staticdir.on': True,
		'tools.staticdir.dir': path + 'public/',
		'tools.encode.encoding': 'utf8'
	}
}

cherrypy.quickstart(HelloWorld(), config = config)

########NEW FILE########
__FILENAME__ = download-kinopoisk
#!/usr/bin/env python3

import requests
import time
import sqlite3
from bs4 import BeautifulSoup as soup

def download(cl, limit):
	url = 'http://www.kinopoisk.ru/review/type/comment/status/{0}/period/year/perpage/100/page/{1}/'

	texts = []
	p = 1

	while True:
		r = requests.get(url.format(cl, p))
		s = soup(r.text)
		for div in s.find_all('div', {'class': 'userReview'}):
			div_resp = div.find('div', {'class': 'response'})
			div_text = div.find('div', {'class': 'brand_words'})

			texts.append((div_text.text,))

		print('Processed page {0}, {1} texts'.format(p, len(texts)))
		if len(texts) >= limit:
			break

		p += 1
		time.sleep(1)

	return texts[:limit]

con = sqlite3.connect('test.db')
cur = con.cursor()

cur.execute('''
	create table docs(
		id integer primary key autoincrement,
		text text,
		class text
	)
	''')

limit = 500

texts_pos = download('good', limit)
texts_neg = download('bad', limit)

cur.executemany('insert into docs (class, text) values ("pos", ?)', texts_pos)
cur.executemany('insert into docs (class, text) values ("neg", ?)', texts_neg)

con.commit()
con.close()
########NEW FILE########
__FILENAME__ = index
#!/usr/bin/env python3

import sqlite3
import re
from yatk import ir
from collections import defaultdict

con = sqlite3.connect('test.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

cur.execute('''
	create table if not exists ngrams (
		id integer primary key autoincrement,
		body text,
		n_pos integer,
		n_neg integer
	)
	''')

count = defaultdict(lambda: {'pos': 0, 'neg': 0})

cur.execute('select class, text from docs')
for row in cur.fetchall():
	words = ir.tokenize(row['text'].lower())
	ngrams = set(words + ir.ngrams(words, 2))
	for ngram in ngrams:
		count[ngram]['pos'] += row['class'] == 'pos'
		count[ngram]['neg'] += row['class'] == 'neg'

for ngram_id, ngram_count in count.items():
	cur.execute('insert into ngrams (body, n_pos, n_neg) values (?, ?, ?)', (ngram_id, ngram_count['pos'], ngram_count['neg']))

cur.execute('create index ngrams_body on ngrams(body)')

con.commit()
con.close()
########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python3

import sys
import requests
import json
from yatk import ir
from yatk.ml.svm import SVM as Classifier
# from yatk.ml.nb import NaiveBayes as Classifier
from red import pie

if len(sys.argv) < 2:
	print('Enter query')
	exit()

TTL = 60

r = pie.Redis()
q = sys.argv[1]
cached = r.get(q)

if not cached:
	url = 'http://search.twitter.com/search.json'
	req = requests.get(url, params={'q': sys.argv[1]})
	data = json.loads(req.text)

	if 'results' not in data:
		print('Error')
		print(data)
		exit()

	cached = json.dumps(data['results'])
	r.setex(q, TTL, cached)

results = json.loads(cached)

cl = Classifier.load('test.svm')
index = ir.SentimentIndex.load('test.index', 'delta', 'bogram')
index.get_text = lambda x: x['text']

docs = []

for msg in results:
	feats = index.weight(index.features(msg))
	docs.append(feats)

labels = cl.predict(docs)
for n in range(len(results)):
	print('{0}.\t{1}\t{2}'.format(n + 1, labels[n], results[n]['text']))
########NEW FILE########
__FILENAME__ = train
#!/usr/bin/env python3

import sqlite3
from yatk import ir
from yatk.ml.svm import SVM as Classifier
# from yatk.ml.nb import NaiveBayes as Classifier

con = sqlite3.connect('test.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

docs = []
cur.execute('select class, text from docs')
for row in cur.fetchall():
	docs.append((row['class'], row['text']))

index = ir.SentimentIndex('delta', 'bogram')
index.get_class = lambda x: x[0]
index.get_text = lambda x: x[1]
index.build(docs)

x = []
y = []
for doc in docs:
	x.append(index.weight(index.features(doc)))
	y.append(doc[0])

cl = Classifier()
cl.train(x, y)
cl.save('test.svm')

index.save('test.index')

con.close()
########NEW FILE########
__FILENAME__ = validate
#!/usr/bin/env python3

import sqlite3
from yatk import ir
from yatk import ml
from yatk.ml.svm import SVM
from yatk.ml.nb import NaiveBayes

con = sqlite3.connect('test.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

docs = []
cur.execute('select class, text from docs')
for row in cur.fetchall():
	docs.append((row['class'], row['text']))

con.close()

docs_even = []
N = int(len(docs) / 2)
for i in range(N):
	docs_even.append(docs[i])
	docs_even.append(docs[N + i])

def	test(classifier, features, weight):
	p = []
	for fold in range(1, 6):
		train_docs, test_docs = ml.folds(docs_even, 5, fold)

		index = ir.SentimentIndex(weight, features)
		index.get_class = lambda x: x[0]
		index.get_text = lambda x: x[1]
		index.build(train_docs)

		train_x = []
		train_y = []
		for doc in train_docs:
			train_x.append(index.weight(index.features(doc)))
			train_y.append(doc[0])

		test_x = []
		test_y = []
		for doc in test_docs:
			test_x.append(index.weight(index.features(doc)))
			test_y.append(doc[0])


		cl = classifier()
		cl.train(train_x, train_y)
		labels = cl.predict(test_x)
		mic, mac = cl.evaluate(test_y, labels)
		p.append(mic)

	print('{0} {1} {2}: {3:.1f}%'.format(classifier, features, weight, ir.avg(p) * 100))

test(NaiveBayes, 'unigram', 'bin')
test(NaiveBayes, 'bigram', 'bin')
test(NaiveBayes, 'bogram', 'bin')
test(SVM, 'unigram', 'bin')
test(SVM, 'bigram', 'bin')
test(SVM, 'bogram', 'bin')
test(SVM, 'unigram', 'delta')
test(SVM, 'bigram', 'delta')
test(SVM, 'bogram', 'delta')
########NEW FILE########
__FILENAME__ = syntagrus
#!/usr/bin/env python3
'''
Created on Nov 21, 2011

@author: alexpak
'''
import os
import sqlite3
import xml.parsers.expat
import glob
from optparse import OptionParser
from collections import namedtuple

word_t = namedtuple('word_t', ['lemma', 'pos', 'feat', 'id', 'dom', 'link'])
feat_ru_en = {
	'ЕД': 'sg',
	'МН': 'pl',
	'ЖЕН': 'f',
	'МУЖ': 'm',
	'СРЕД': 'n',
	'ИМ': 'nom',
	'РОД': 'gen',
	'ДАТ': 'dat',
	'ВИН': 'acc',
	'ТВОР': 'ins',
	'ПР': 'prep',
	'ПАРТ': 'gen2',
	'МЕСТН': 'loc',
	'ОД': 'anim',
	'НЕОД': 'inan',
	'ИНФ': 'inf',
	'ПРИЧ': 'adjp',
	'ДЕЕПР': 'advp',
	'ПРОШ': 'pst',
	'НЕПРОШ': 'npst',
	'НАСТ': 'prs',
	'1-Л': '1p',
	'2-Л': '2p',
	'3-Л': '3p',
	'ИЗЪЯВ': 'real',
	'ПОВ': 'imp',
	'КР': 'shrt',
	'НЕСОВ': 'imperf',
	'СОВ': 'perf',
	'СТРАД': 'pass',
	'СЛ': 'compl',
	'СМЯГ': 'soft',
	'СРАВ': 'comp',
	'ПРЕВ': 'supl',
}

link_ru_en = {
	'предик': 'subj',
	'1-компл': 'obj',
	'2-компл': 'obj',
	'3-компл': 'obj',
	'4-компл': 'obj',
	'5-компл': 'obj',
	'опред': 'amod',
	'предл': 'prep',
	'обст': 'pobj',
}
{
	'огранич': '',      
	'квазиагент': '',       
	'сочин': '',      
	'соч-союзн': '',      
	'атриб': '',      
	'аппоз': '',      
	'подч-союзн': '',      
	'вводн': '',      
	'сент-соч': '',      
	'количест': '',      
	'разъяснит': '',       
	'присвяз': '',      
	'релят': '',      
	'сравн-союзн': '',      
	'примыкат': '',      
	'сравнит': '',      
	'соотнос': '',      
	'эксплет': '',      
	'аналит': '',      
	'пасс-анал': '',      
	'вспом': '',      
	'агент': '',      
	'кратн': '',      
	'инф-союзн': '',      
	'электив': '',      
	'композ': '',      
	'колич-огран': '',      
	'неакт-компл': '',      
	'пролепт': '',       
	'суб-копр': '',       
	'дат-субъект': '',      
	'длительн': '',      
	'об-аппоз': '',      
	'изъясн': '',      
	'компл-аппоз': '',      
	'оп-опред': '',      
	'1-несобст-компл': '',      
	'распред': '',      
	'уточн': '',      
	'нум-аппоз': '',      
	'ном-аппоз': '',      
	'2-несобст-компл': '',      
	'аппрокс-колич': '',      
	'колич-вспом': '',      
	'колич-копред': '',      
	'кратно-длительн': '',      
	'об-копр': '',      
	'эллипт': '',      
	'3-несобст-компл': '',       
	'4-несобст-компл': '',       
	'fictit': '',       
	'авт-аппоз': '',       
	'аддит': '',       
	'адр-присв': '',       
	'дистанц': '',       
	'несобст-агент': '',       
	'об-обст': '',       
	'обст-тавт': '',       
	'презентат': '',       
	'сент-предик': '',       
	'суб-обст': '',       
}

class Reader:
	def __init__(self):
		self._parser = xml.parsers.expat.ParserCreate()
		self._parser.StartElementHandler = self.start_element
		self._parser.EndElementHandler = self.end_element
		self._parser.CharacterDataHandler = self.char_data		
	
	def start_element(self, name, attr):
		if name == 'W':
			features = attr['FEAT'].split(' ') if 'FEAT' in attr else ['UNK']
			for i in range(0, len(features)):
				if features[i] in feat_ru_en:
					features[i] = feat_ru_en[features[i]]
					
			lemma = lemma=attr['LEMMA'].lower() if 'LEMMA' in attr else ''
			link = attr['LINK'] if 'LINK' in attr else None
#			if link in link_ru_en:
#				link = link_ru_en[link]
				
			dom = int(attr['DOM']) if attr['DOM'] != '_root' else 0
			pos = features[0]
			feat = set(features[1:])
			
			if 'adjp' in feat:
				pos = 'VADJ'
				feat -= {'adjp'}
				
			if 'advp' in feat:
				pos = 'VADV'
				feat -= {'advp'}
			
			if 'inf' in feat:
				pos = 'VINF'
				feat -= {'inf'}
			
			self._info = word_t(lemma=lemma, pos=pos, feat=feat, id=int(attr['ID']), dom=dom, link=link)
			self._cdata = ''
	
	def end_element(self, name):
		if name == 'S':
			self._sentences.append(self._sentence)
			self._sentence = []
		elif name == 'W':
			self._sentence.append((self._cdata, self._info))
			self._cdata = ''
	
	def char_data(self, content):
		self._cdata += content
		
	def read(self, filename):
		f = open(filename, encoding='windows-1251')
		content = f.read()
		f.close()
		content = content.replace('encoding="windows-1251"', 'encoding="utf-8"')
		
		self._sentences = []
		self._sentence = []
		self._cdata = ''
		self._info = ''
		
		self._parser.Parse(content)		
		
		return self._sentences

class Lexicon:
	def __init__(self, dbname):
		self.dbname = dbname
		db_exists = os.path.isfile(dbname)
		self.con = sqlite3.connect(dbname)
		self.cur = self.con.cursor()
		
		if not db_exists:
			self.create_db()		
	
	def create_db(self):
		sql = '''
        create table words(
        	id integer primary key autoincrement,
        	lemma text,
        	pos text,
        	form text,
        	info text,
        	freq integer
        );
        create index words_lemma_form_info on words(lemma, form, info);
        '''
		[self.cur.execute(st) for st in sql.split(';') if len(st.strip())]
		
	def index(self, filename):
		sentences = Reader().read(filename)
		for sentence in sentences:
			for word in sentence:
				feat = ' '.join(word[1].feat)
				self.cur.execute('select id from words where lemma = ? and form = ? and pos = ? and info = ?', (word[1].lemma, word[0], word[1].pos, feat))
				row = self.cur.fetchone()
				if row is None:
					self.cur.execute('insert into words (lemma, pos, form, info, freq) values (?, ?, ?, ?, 1)', (word[1].lemma, word[1].pos, word[0], feat))
				else:
					self.cur.execute('update words set freq = freq + 1 where id = ?', row)
					
	def close(self):
		self.con.commit()
		self.con.close()
	
if __name__ == '__main__':
	parser = OptionParser()
	parser.usage = '%prog [options] inputfile'
	parser.add_option('-L', '--construct-lexicon', action = 'store_const', const = True	, dest = 'lexicon', help = 'construct lexicon')

	(options, args) = parser.parse_args()
	
	if options.lexicon:
		L = Lexicon('tmp/lexicon')
		files = glob.glob('res/*/*/*.tgt')
		for file in files:
			L.index(file)
		
		L.close()

	#R = Reader()
	#sentences = R.read(args[0])
	#print(len(sentences))
	#print(sentences[0])
	
########NEW FILE########
__FILENAME__ = template
#!/usr/bin/env python3
'''
Created on Aug 7, 2011

@author: alexpak
'''
def print_stack(stack, padding = '\n', pad_with = '\t'):
	s = ''
	for expr in stack:
		if isinstance(expr, str):
			s += padding + '__s__ +="""' + expr.replace('"', '\\"') + '"""'
		else:
			if expr[0] == 'if':
				s += padding + 'if ' + expr[1] + ':'
				s += print_stack(expr[2], padding + pad_with, pad_with) or padding + pad_with + 'pass'
				s += padding + 'else:'
				s += print_stack(expr[3], padding + pad_with, pad_with) or padding + pad_with + 'pass'
			elif expr[0] == 'for':
				s += padding + 'for ' + expr[1] + ':'
				s += print_stack(expr[2], padding + pad_with, pad_with) or padding + pad_with + 'pass'
			elif expr[0] == 'print':
				s += padding + '__s__+=str(' + expr[1] + ')'
	return s

class Template:
	vars = {}
	
	def assign(self, key, val):
		self.vars[key] = val
	
	def __setattr__(self, key, val):
		self.assign(key, val)
		
	def __setitem__(self, key, val):
		self.assign(key, val)
	
	def transform(self, template):
		buffer = ''
		
		stack = []
		current_stack = stack
		stack_chain = []
		stack_chain.append(current_stack)
		expr = tuple()
		last_if = tuple()
		open_bracket = False
		for ch in template:
			if ch == '{':
				if open_bracket:
					current_stack.append('{')
					
				open_bracket = True
				current_stack.append(buffer)
				buffer = ''
			elif ch == '}' and len(buffer):
				if buffer[0:3] == 'if ':
					expr = ('if', buffer[3:], [], [])
					current_stack.append(expr)
					stack_chain.append(current_stack)
					current_stack = expr[2]
					last_if = expr
					
				elif buffer == 'else':
					if last_if[0] != 'if':
						exit('Expected IF for ELSE')

					current_stack = last_if[3]
					
				elif buffer[0:4] == 'for ':
					expr = ('for', buffer[4:], [])
					current_stack.append(expr)
					stack_chain.append(current_stack)
					current_stack = expr[2]
					
				elif buffer[0] == '$':
					expr = ('print', buffer[1:])
					current_stack.append(expr)

				elif buffer == 'end':
					current_stack = stack_chain.pop()
				
				else:
					if open_bracket:
						current_stack.append('{')

					current_stack.append(buffer + '}')
				
				open_bracket = False
				buffer = ''
			else:
				buffer += ch
		
		if buffer:		
			if open_bracket:
				current_stack.append('{')
			current_stack.append(buffer)

		source = '__s__ = ""' + print_stack(stack)
		
		exec(source, self.vars)
		return self.vars['__s__']

########NEW FILE########
__FILENAME__ = train
#!/usr/bin/env python3
'''
Created on Aug 3, 2011

@author: alexpak <irokez@gmail.com>
'''
import sys
import re

import rnc
import pos

sentences = []
#sentences.extend(rnc.Reader().read('tmp/fiction.xml'))
#sentences.extend(rnc.Reader().read('tmp/science.xml'))
#sentences.extend(rnc.Reader().read('tmp/laws.xml'))
sentences.extend(rnc.Reader().read('tmp/media1.xml'))
sentences.extend(rnc.Reader().read('tmp/media2.xml'))
sentences.extend(rnc.Reader().read('tmp/media3.xml'))

re_pos = re.compile('([\w-]+)(?:[^\w-]|$)'.format('|'.join(pos.tagset)))

tagger = pos.Tagger()

sentence_labels = []
sentence_words = []
for sentence in sentences:
	labels = []
	words = []
	for word in sentence:
		gr = word[1]['gr']
		m = re_pos.match(gr)
		if not m:
			print(gr, file = sys.stderr)
			
		pos = m.group(1)
		if pos == 'ANUM':
			pos = 'A-NUM'
			
		label = tagger.get_label_id(pos)
		if not label:
			print(gr, file = sys.stderr)
			
		labels.append(label)
		
		body = word[0].replace('`', '')
		words.append(body)
		
	sentence_labels.append(labels)
	sentence_words.append(words)
			
tagger.train(sentence_words, sentence_labels, True)
tagger.train(sentence_words, sentence_labels)
tagger.save('tmp/svm.model', 'tmp/ids.pickle')
########NEW FILE########
__FILENAME__ = pos-test
#!/usr/bin/env python3
'''
Created on Aug 3, 2011

@author: alexpak <irokez@gmail.com>
'''
import sys
import pos

sentence = sys.argv[1].split(' ')

tagger = pos.Tagger()
tagger.load('tmp/svm.model', 'tmp/ids.pickle')

rus = {
	'S': 'сущ.', 
	'A': 'прил.', 
	'NUM': 'числ.', 
	'A-NUM': 'числ.-прил.', 
	'V': 'глаг.', 
	'ADV': 'нареч.', 
	'PRAEDIC': 'предикатив', 
	'PARENTH': 'вводное', 
	'S-PRO': 'местоим. сущ.', 
	'A-PRO': 'местоим. прил.', 
	'ADV-PRO': 'местоим. нареч.', 
	'PRAEDIC-PRO': 'местоим. предик.', 
	'PR': 'предлог', 
	'CONJ': 'союз', 
	'PART': 'частица', 
	'INTJ': 'межд.', 
	'INIT': 'инит', 
	'NONLEX': 'нонлекс'
}

tagged = []
for word, label in tagger.label(sentence):
	tagged.append((word, rus[tagger.get_label(label)]))
	
print(tagged)
########NEW FILE########
__FILENAME__ = test-alg
#!/usr/bin/env python3
'''
Created on Aug 19, 2011

@author: alexpak
'''

import sys
sys.path.append('src')

from alg import Vector as V

a = V([1, 2, 3, 4])
b = a + 3
c = b + 4
d = c - a
f = V([1, 1, 1, 1])
f += a
print(a)
print(b)
print(c)
print(d)
print(f)
########NEW FILE########
__FILENAME__ = test-cyk
#!/usr/bin/env python3

'''
Created on Sep 6, 2011

@author: alexpak
'''
import sys
sys.path.append('src')

import parsers
from parsers.cyk import CYK

rules = '''
    EX  = B1 EX B2 | N
    B1  = "("
    B2  = ")"
    EX  = EX OP2 EX | OP1 EX
    N   = "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "0"
    OP2 = "+" | "-" | "/" | "*"
    OP1 = "+" | "-"
'''

#rules = '''
#    EX  = EX OP EX | N
#    N   = "1" | "2" | "3"
#    OP = "+" | "-"
#'''

grammar = parsers.read_rules(rules)

parser = CYK(grammar)
#result = parser.parse('1 + 2 * ( 3 - 6 ) + 9 + 0 / 2')
result = parser.parse('1 + 2 + 3')
#parser.parse('1 + 2')
tree = parser.build_tree()
parser.print_tree(tree)

'''
(EX (EX 1)
    (OP +)
    (N 2))
'''
########NEW FILE########
__FILENAME__ = test-iris
#!/usr/bin/env python3
'''
Created on Aug 17, 2011

@author: alexpak
'''

import sys
sys.path.append('src')

f = open('res/iris.data')
data = []; x = []; y =[]
for line in f:
	rows = line.strip().split(',')
	if len(rows) == 5:
		x.append([float(i) for i in rows[0:4]])
		y.append(rows[4])
f.close()

def list_to_dict(l):
#	return dict(zip(l, [1 for _ in range(0, len(l))]))
	return dict(zip(range(0, len(l)), l))

# divide into training and test sets
test_x = []; test_y = []; train_x = []; train_y = [];
for i in range(0, len(x)):
	if i % 3:
		train_x.append(list_to_dict(x[i]))
		train_y.append(y[i])
	else:
		test_x.append(list_to_dict(x[i]))
		test_y.append(y[i])
	
from ml.nb import NaiveBayes

classifier = NaiveBayes()
classifier.train(train_x, train_y)
estim_y = classifier.predict(test_x)
(acc, ) = classifier.evaluate(test_y, estim_y)

print('Naive Bayes accuracy = {0:.2f}%'.format(acc * 100))

from ml.svm import SVM

classifier = SVM()
classifier.train(train_x, train_y)
estim_y = classifier.predict(test_x)
(acc, ) = classifier.evaluate(test_y, estim_y)

print('SVM accuracy = {0:.2f}%'.format(acc * 100))
########NEW FILE########
__FILENAME__ = test-names
#!/usr/bin/env python3
'''
Created on Aug 17, 2011

@author: alexpak
'''
import sys
sys.path.append('src')

f = open('res/names.txt')

x = []; y = []

for line in f:
	(name, sex) = line.strip().split(' ')
	x.append({name[-1:]: 1, name[-2:]: 1, name[-3:]: 1, name[-4:]: 1})
	y.append(sex)
	
fold = -100

f.close()

import os

from ml.nb import NaiveBayes

filename = 'tmp/nb.pickle'
exists = os.path.isfile(filename)
if exists:
	classifier = NaiveBayes.load(filename)
else:
	classifier = NaiveBayes()
	
classifier.train(x[0:fold], y[0:fold])
estim_y = classifier.predict(x[fold:])
(acc, ) = classifier.evaluate(y[fold:], estim_y)

if not exists:
	classifier.save(filename)

print('Naive Bayes accuracy = {0:.2f}%'.format(acc * 100))

from ml.svm import SVM

filename = 'tmp/svm.pickle'
exists = os.path.isfile(filename)
if exists:
	classifier = SVM.load(filename)
else:
	classifier = SVM()
	
classifier.train(x[0:fold], y[0:fold])
estim_y = classifier.predict(x[fold:])
(acc, ) = classifier.evaluate(y[fold:], estim_y)

if not exists:
	classifier.save(filename)
	
print('SVM accuracy = {0:.2f}%'.format(acc * 100))
########NEW FILE########
__FILENAME__ = test-nn
#!/usr/bin/env python3
'''
Created on Aug 18, 2011

@author: alexpak
'''
import sys
sys.path.append('src')

def list_to_dict(l):
	return dict(zip(range(0, len(l)), l))

from ml.nn import Perceptron

classifier = Perceptron(2)
x = [
	list_to_dict([0, 0]),
	list_to_dict([0, 1]),
	list_to_dict([1, 0]),
	list_to_dict([1, 1])
]
y = [0, 1, 1, 0]
#y = [1]

classifier.train(x, y)
y = classifier.predict(x)
print(y)
########NEW FILE########
__FILENAME__ = test-polarity
#!/usr/bin/env python3
'''
Created on Aug 17, 2011

@author: alexpak
'''
import sys
sys.path.append('src')

from collections import defaultdict

f_pos = open('res/rt-polaritydata/rt-polaritydata/rt-polarity.pos', 'rb')
f_neg = open('res/rt-polaritydata/rt-polaritydata/rt-polarity.neg', 'rb')

def count_words(line):
	count = defaultdict(bool)
	for word in line.strip().split(' '):
		if len(word) > 1:
			count[word] += 1

	return count

x = []; y = []

i = 0
eof = False
while not eof:
	line = f_pos.readline()
	eof = not len(line)
	x.append(count_words(line.decode('utf-8', 'ignore')))
	y.append(+1)
	x.append(count_words(f_neg.readline().decode('utf-8', 'ignore')))
	y.append(-1)
	i += 1
	
fold = int(i * 0.9)

f_pos.close()
f_neg.close()

from ml.nb import NaiveBayes

classifier = NaiveBayes()
classifier.train(x[0:fold], y[0:fold])
estim_y = classifier.predict(x[fold:])
(acc, ) = classifier.evaluate(y[fold:], estim_y)

print('Naive Bayes accuracy = {0:.2f}%'.format(acc * 100))

from ml.svm import SVM

classifier = SVM()
classifier.train(x[0:fold], y[0:fold])
estim_y = classifier.predict(x[fold:])
(acc, ) = classifier.evaluate(y[fold:], estim_y)

print('SVM accuracy = {0:.2f}%'.format(acc * 100))
########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Aug 7, 2011

@author: alexpak
'''

import cherrypy
import sys
import time
import cgi
import os

path = os.path.dirname(os.path.abspath(__file__)) + '/'

sys.path.append(path + '../src')

f = open(path + 'html/tagging.html', 'rb')
content = f.read().decode()
f.close()

import re
import template
import socket
import time

def recvall(sock):
	output = ''
	while True:
		data = sock.recv(4096)
		if not data:
			break
		output += data.decode('utf-8')
	return output

import morph
import re

Tagger = morph.Tagger()

def get_color(pos):
	if pos[0] == 'S':
		return 'blue'
	elif pos[0] == 'V':
		return 'green'
	elif pos[0] == 'A':
		return 'orange'
	else:
		return 'gray'

categories = {
	'S': 'сущ.',
	'A': 'прил.',
	'V': 'глагол',
	'VINF': 'инф.',
	'VADJ': 'прич.',
	'VADV': 'дееп.',
	'ADV': 'нар.',
	'NID': 'инoстр.',
	'NUM': 'числ.',
	'PR': 'предлог',
	'PART': 'част.',
	'CONJ': 'союз',
	'COM': 'ком.',
	'INTJ': 'межд.',
	'P': 'P',
	'UNK': '???',
	'm': 'муж. род',
	'f': 'жен. род',
	'n': 'ср. род',
	'sg': 'ед. число',
	'pl': 'мн. число',
	'nom': 'им. падеж',
	'gen': 'род. падеж',
	'dat': 'дат. падеж',
	'acc': 'вин. падеж',
	'ins': 'твор. падеж',
	'prep': 'пред. падеж',
	'gen2': '2й род. падеж',
	'loc': 'мест. падеж',
	'anim': 'одуш.',
	'inan': 'неодуш.',
	'1p': '1е лицо',
	'2p': '2е лицо',
	'3p': '3е лицо',
	'perf': 'соверш.',
	'imperf': 'несоверш.',
	'real': 'действ.',
	'imp': 'повелит.',
	'pass': 'страд.',
	'pst': 'прош. время',
	'npst': 'непрош. время',
	'prs': 'наст. время',
	'comp': 'сравн. степень',
	'supl': 'превосх. степень',
	'shrt': 'кратк.'
}
def pos_to_human(pos):
	loc = []
	for feat in pos.split('.'):
		if feat in categories:
			loc.append(categories[feat])
		else:
			loc.append(feat)

	return loc

class HelloWorld:
	@cherrypy.expose
	def index(self, text = ''):

		start = time.time()
		text = text.strip()
		T = template.Template()
		T.text = cgi.escape(text)
		error = ''
		
		sentence = [[w] for w in re.split('\W+', text) if len(w)] if len(text) else []
		
		if 0 < len(sentence) < 25:
				
			labeled = Tagger.label(sentence)
			for w in range(0, len(sentence)):
				sentence[w] = (sentence[w][0], labeled[w][1], labeled[w][2])
				
			selected_feat = {'m', 'f', 'n', 'sg', 'pl', '1p', '2p', '3p', 'nom', 'gen', 'gen2', 'dat', 'acc', 'ins', 'prep', 'loc', 'real', 'imp', 'pass', 'comp', 'shrt'}		
			
			parser_input = []
			for word in sentence:
				w = word[0] or 'FANTOM'
				p = '.'.join([word[1]] + sorted(word[2] & selected_feat))
				parser_input.append('{0}\t{1}\n'.format(w, p))

			client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			client_socket.connect(("localhost", 5000))
			for word in parser_input:
				client_socket.send(bytes(word, 'utf-8'))
			
			client_socket.send(bytes('\n', 'utf-8'))
			data = recvall(client_socket).strip()
			client_socket.close()
				
			time_total = time.time() - start
			words = len(sentence)
			words_per_sec = words / time_total
			
			edges = []
			nodes = [(0, 'ROOT', 'red')]
			
			tagged = [tuple(row.split('\t')) for row in data.split('\n')]
			n = 0
			for word in tagged:
				n += 1
				if len(word) < 4:
					continue
				
				nodes.append((n, word[0], get_color(word[1])))
				
			n = 0
			for word in tagged:
				n += 1
				if len(word) < 4:
					continue
				head = int(word[2])
				if len(tagged) < head:
					head = 0
				
				try:
					edges.append((n, head, word[3]))
				finally:
					pass

			print(tagged, file=sys.stderr)
			T.tagged = [(word[0], ', '.join(pos_to_human(word[1]))) for word in tagged]
			T.edges = edges
			T.nodes = nodes
			T.time_total = round(time_total, 2)
			T.words_per_sec = round(words_per_sec)
			T.words = words
		elif len(sentence) > 25:
			error = 'Sentence is too long, looks like "War and Peace"'

		T.error = error
		
		return T.transform(content)
	
	@cherrypy.expose
	def test(self):
		return content

cherrypy.server.socket_host = '0.0.0.0'
config = {
	'/': {
		'tools.staticdir.on': True,
		'tools.staticdir.dir': path + 'public/',
		'tools.encode.encoding': 'utf8'
	}
}

cherrypy.quickstart(HelloWorld(), config = config)

########NEW FILE########
