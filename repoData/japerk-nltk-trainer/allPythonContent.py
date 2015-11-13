__FILENAME__ = analyze_chunked_corpus
#!/usr/bin/env python
import argparse, collections
import nltk.corpus
from nltk.tree import Tree
from nltk.corpus.util import LazyCorpusLoader
from nltk_trainer import load_corpus_reader, simplify_wsj_tag
from nltk_trainer.chunking.transforms import node_label

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Analyze a chunked corpus',
	formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('corpus',
	help='''The name of a chunked corpus included with NLTK, such as
treebank_chunk or conll2002, or the root path to a corpus directory,
which can be either an absolute path or relative to a nltk_data directory.''')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to %(default)d. 0 is no trace output.')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader', default=None,
	help='''Full module path to a corpus reader class, such as
nltk.corpus.reader.chunked.ChunkedCorpusReader''')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')

if simplify_wsj_tag:
	corpus_group.add_argument('--simplify_tags', action='store_true', default=False,
		help='Use simplified tags')

sort_group = parser.add_argument_group('Tag Count Sorting Options')
sort_group.add_argument('--sort', default='tag', choices=['tag', 'count'],
	help='Sort key, defaults to %(default)s')
sort_group.add_argument('--reverse', action='store_true', default=False,
	help='Sort in revere order')

args = parser.parse_args()

###################
## corpus reader ##
###################

chunked_corpus = load_corpus_reader(args.corpus, reader=args.reader, fileids=args.fileids)

if not chunked_corpus:
	raise ValueError('%s is an unknown corpus')

if args.trace:
	print('loading %s' % args.corpus)

##############
## counting ##
##############

wc = 0
tag_counts = collections.defaultdict(int)
iob_counts = collections.defaultdict(int)
tag_iob_counts = collections.defaultdict(lambda: collections.defaultdict(int))
word_set = set()

for obj in chunked_corpus.chunked_words():
	if isinstance(obj, Tree):
		label = node_label(obj)
		iob_counts[label] += 1
		
		for word, tag in obj.leaves():
			wc += 1
			word_set.add(word)
			tag_counts[tag] += 1
			tag_iob_counts[tag][label] += 1
	else:
		word, tag = obj
		wc += 1
		word_set.add(word)
		tag_counts[tag] += 1

############
## output ##
############

print('%d total words' % wc)
print('%d unique words' % len(word_set))
print('%d tags' % len(tag_counts))
print('%d IOBs\n' % len(iob_counts))

if args.sort == 'tag':
	sort_key = lambda tc: tc[0]
elif args.sort == 'count':
	sort_key = lambda tc: tc[1]
else:
	raise ValueError('%s is not a valid sort option' % args.sort)

line1 = '  Tag      Count  '
line2 = '=======  ========='

iobs = sorted(iob_counts.keys())

for iob in iobs:
	line1 += '    %s  ' % iob
	line2 += '  ==%s==' % ('=' * len(iob))

print(line1)
print(line2)

for tag, count in sorted(tag_counts.items(), key=sort_key, reverse=args.reverse):
	iob_counts = [str(tag_iob_counts[tag][iob]).rjust(4+len(iob)) for iob in iobs]
	print('  '.join([tag.ljust(7), str(count).rjust(9)] + iob_counts))

print(line2)
########NEW FILE########
__FILENAME__ = analyze_chunker_coverage
#!/usr/bin/env python
import argparse, collections, math
import nltk.corpus, nltk.corpus.reader, nltk.data, nltk.tag, nltk.metrics
from nltk.corpus.util import LazyCorpusLoader
from nltk_trainer import load_corpus_reader, load_model, simplify_wsj_tag
from nltk_trainer.chunking import chunkers
from nltk_trainer.chunking.transforms import node_label
from nltk_trainer.tagging import taggers

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Analyze a part-of-speech tagged corpus',
	formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('corpus',
	help='''The name of a tagged corpus included with NLTK, such as treebank,
brown, cess_esp, floresta, or the root path to a corpus directory,
which can be either an absolute path or relative to a nltk_data directory.''')
parser.add_argument('--tagger', default=nltk.tag._POS_TAGGER,
	help='''pickled tagger filename/path relative to an nltk_data directory
default is NLTK's default tagger''')
parser.add_argument('--chunker', default=nltk.chunk._MULTICLASS_NE_CHUNKER,
	help='''pickled chunker filename/path relative to an nltk_data directory
default is NLTK's default multiclass chunker''')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')
parser.add_argument('--score', action='store_true', default=False,
	help='Evaluate chunk score of chunker using corpus.chunked_sents()')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader', default=None,
	help='''Full module path to a corpus reader class, such as
nltk.corpus.reader.chunked.ChunkedCorpusReader''')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')
corpus_group.add_argument('--fraction', default=1.0, type=float,
	help='''The fraction of the corpus to use for testing coverage''')

if simplify_wsj_tag:
	corpus_group.add_argument('--simplify_tags', action='store_true', default=False,
		help='Use simplified tags')

args = parser.parse_args()

###################
## corpus reader ##
###################

corpus = load_corpus_reader(args.corpus, reader=args.reader, fileids=args.fileids)

if args.score and not hasattr(corpus, 'chunked_sents'):
	raise ValueError('%s does not support scoring' % args.corpus)

############
## tagger ##
############

if args.trace:
	print('loading tagger %s' % args.tagger)

if args.tagger == 'pattern':
	tagger = taggers.PatternTagger()
else:
	tagger = load_model(args.tagger)

if args.trace:
	print('loading chunker %s' % args.chunker)

if args.chunker == 'pattern':
	chunker = chunkers.PatternChunker()
else:
	chunker = load_model(args.chunker)

#######################
## coverage analysis ##
#######################

if args.score:
	if args.trace:
		print('evaluating chunker score\n')
	
	chunked_sents = corpus.chunked_sents()
	
	if args.fraction != 1.0:
		cutoff = int(math.ceil(len(chunked_sents) * args.fraction))
		chunked_sents = chunked_sents[:cutoff]
	
	print(chunker.evaluate(chunked_sents))
	print('\n')

if args.trace:
	print('analyzing chunker coverage of %s with %s\n' % (args.corpus, chunker.__class__.__name__))

iobs_found = collections.defaultdict(int)
sents = corpus.sents()

if args.fraction != 1.0:
	cutoff = int(math.ceil(len(sents) * args.fraction))
	sents = sents[:cutoff]

for sent in sents:
	tree = chunker.parse(tagger.tag(sent))
	
	for child in tree.subtrees(lambda t: node_label(t) != 'S'):
		iobs_found[node_label(child)] += 1

iobs = iobs_found.keys()
justify = max(7, *[len(iob) for iob in iobs])

print('IOB'.center(justify) + '    Found  ')
print('='*justify + '  =========')

for iob in sorted(iobs):
	print('  '.join([iob.ljust(justify), str(iobs_found[iob]).rjust(9)]))

print('='*justify + '  =========')
########NEW FILE########
__FILENAME__ = analyze_classifier_coverage
#!/usr/bin/env python
import argparse, collections, itertools, operator, re, string, time
import nltk.data
from nltk.classify.util import accuracy
from nltk.corpus import stopwords
from nltk.metrics import f_measure, precision, recall
from nltk.util import ngrams
from nltk_trainer import load_corpus_reader, pickle, simplify_wsj_tag
from nltk_trainer.classification import corpus, scoring
from nltk_trainer.classification.featx import bag_of_words

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Analyze a classifier on a classified corpus')
parser.add_argument('corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('--classifier', required=True,
	help='pickled classifier name/path relative to an nltk_data directory')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')
parser.add_argument('--metrics', action='store_true', default=False,
	help='Use classified instances to determine classifier accuracy, precision & recall')
parser.add_argument('--speed', action='store_true', default=False,
	help='Determine average instance classification speed.')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader',
	default='nltk.corpus.reader.CategorizedPlaintextCorpusReader',
	help='Full module path to a corpus reader class, such as %(default)s')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')
corpus_group.add_argument('--cat_pattern', default='(.+)/.+',
	help='''A regular expression pattern to identify categories based on file paths.
	If cat_file is also given, this pattern is used to identify corpus file ids.
	The default is '(.+)/+', which uses sub-directories as categories.''')
corpus_group.add_argument('--cat_file',
	help='relative path to a file containing category listings')
corpus_group.add_argument('--delimiter', default=' ',
	help='category delimiter for category file, defaults to space')
corpus_group.add_argument('--instances', default='paras',
	choices=('sents', 'paras', 'files'),
	help='''the group of words that represents a single training instance,
	the default is to use entire files''')
corpus_group.add_argument('--fraction', default=1.0, type=float,
	help='''The fraction of the corpus to use for testing coverage''')

feat_group = parser.add_argument_group('Feature Extraction',
	'The default is to lowercase every word, strip punctuation, and use stopwords')
feat_group.add_argument('--ngrams', nargs='+', type=int,
	help='use n-grams as features.')
feat_group.add_argument('--no-lowercase', action='store_true', default=False,
	help="don't lowercase every word")
feat_group.add_argument('--filter-stopwords', default='no',
	choices=['no']+stopwords.fileids(),
	help='language stopwords to filter, defaults to "no" to keep stopwords')
feat_group.add_argument('--punctuation', action='store_true', default=False,
	help="don't strip punctuation")

args = parser.parse_args()

###################
## corpus reader ##
###################

reader_args = []
reader_kwargs = {}

if args.cat_pattern:
	reader_args.append(args.cat_pattern)
	reader_kwargs['cat_pattern'] = re.compile(args.cat_pattern)

if args.cat_file:
	reader_kwargs['cat_file'] = args.cat_file
	
	if args.delimiter:
		reader_kwargs['delimiter'] = args.delimiter

categorized_corpus = load_corpus_reader(args.corpus, args.reader, *reader_args, **reader_kwargs)

if args.metrics and not hasattr(categorized_corpus, 'categories'):
	raise ValueError('%s does not support metrics' % args.corpus)

labels = categorized_corpus.categories()

########################
## text normalization ##
########################

if args.filter_stopwords == 'no':
	stopset = set()
else:
	stopset = set(stopwords.words(args.filter_stopwords))

if not args.punctuation:
	stopset |= set(string.punctuation)

def norm_words(words):
	if not args.no_lowercase:
		words = [w.lower() for w in words]
	
	if not args.punctuation:
		words = [w.strip(string.punctuation) for w in words]
		words = [w for w in words if w]
	
	if stopset:
		words = [w for w in words if w.lower() not in stopset]

	if args.ngrams:
		return reduce(operator.add, [words if n == 1 else ngrams(words, n) for n in args.ngrams])
	else:
		return words

#####################
## text extraction ##
#####################

if args.speed:
	load_start = time.time()

try:
	classifier = nltk.data.load(args.classifier)
except LookupError:
	classifier = pickle.load(open(args.classifier))

if args.speed:
	load_secs = time.time() - load_start
	print('loading time: %dsecs' % load_secs)

if args.metrics:
	label_instance_function = {
		'sents': corpus.category_sent_words,
		'paras': corpus.category_para_words,
		'files': corpus.category_file_words
	}
	
	lif = label_instance_function[args.instances]
	feats = []
	test_feats = []
	
	for label in labels:
		texts = lif(categorized_corpus, label)
		
		if args.instances == 'files':
			# don't get list(texts) here since might have tons of files
			stop = int(len(categorized_corpus.fileids())*args.fraction)
		else:
			texts = list(texts)
			stop = int(len(texts)*args.fraction)
		
		for t in itertools.islice(texts, stop):
			feat = bag_of_words(norm_words(t))
			feats.append(feat)
			test_feats.append((feat, label))
	
	print('accuracy:', accuracy(classifier, test_feats))
	refsets, testsets = scoring.ref_test_sets(classifier, test_feats)
	
	for label in labels:
		ref = refsets[label]
		test = testsets[label]
		print('%s precision: %f' % (label, precision(ref, test) or 0))
		print('%s recall: %f' % (label, recall(ref, test) or 0))
		print('%s f-measure: %f' % (label, f_measure(ref, test) or 0))
else:
	if args.instances == 'sents':
		texts = categorized_corpus.sents()
		total = len(texts)
	elif args.instances == 'paras':
		texts = (itertools.chain(*para) for para in categorized_corpus.paras())
		total = len(categorized_corpus.paras())
	elif args.instances == 'files':
		texts = (categorized_corpus.words(fileids=[fid]) for fid in categorized_corpus.fileids())
		total = len(categorized_corpus.fileids())
	
	stop = int(total * args.fraction)
	feats = (bag_of_words(norm_words(i)) for i in itertools.islice(texts, stop))

label_counts = collections.defaultdict(int)

if args.speed:
	time_start = time.time()

for feat in feats:
	label = classifier.classify(feat)
	label_counts[label] += 1

if args.speed:
	time_end = time.time()

for label in sorted(label_counts.keys()):
	print(label, label_counts[label])

if args.speed:
	secs = (time_end - time_start)
	nfeats = sum(label_counts.values())
	print('average time per classify: %dsecs / %d feats = %f ms/feat' % (secs, nfeats, (float(secs) / nfeats) * 1000))

########NEW FILE########
__FILENAME__ = analyze_tagged_corpus
#!/usr/bin/env python
import argparse
import collections
import nltk.corpus
from nltk.corpus.util import LazyCorpusLoader
from nltk_trainer import basestring, load_corpus_reader, simplify_wsj_tag

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Analyze a part-of-speech tagged corpus',
	formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('corpus',
	help='''The name of a tagged corpus included with NLTK, such as treebank,
brown, cess_esp, floresta, or the root path to a corpus directory,
which can be either an absolute path or relative to a nltk_data directory.''')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to %(default)d. 0 is no trace output.')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader', default=None,
	help='''Full module path to a corpus reader class, such as
nltk.corpus.reader.tagged.TaggedCorpusReader''')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')

if simplify_wsj_tag:
	corpus_group.add_argument('--simplify_tags', action='store_true', default=False,
		help='Use simplified tags')
else:
	corpus_group.add_argument('--tagset', default=None,
		help='Map tags to a given tagset, such as "universal"')

sort_group = parser.add_argument_group('Tag Count Sorting Options')
sort_group.add_argument('--sort', default='tag', choices=['tag', 'count'],
	help='Sort key, defaults to %(default)s')
sort_group.add_argument('--reverse', action='store_true', default=False,
	help='Sort in revere order')

args = parser.parse_args()

###################
## corpus reader ##
###################

tagged_corpus = load_corpus_reader(args.corpus, reader=args.reader, fileids=args.fileids)

if not tagged_corpus:
	raise ValueError('%s is an unknown corpus')

if args.trace:
	print('loading %s' % args.corpus)

##############
## counting ##
##############

wc = 0
tag_counts = collections.defaultdict(int)
taglen = 7
word_set = set()

if simplify_wsj_tag and args.simplify_tags and args.corpus not in ['conll2000', 'switchboard']:
	kwargs = {'simplify_tags': True}
elif not simplify_wsj_tag and args.tagset:
	kwargs = {'tagset': args.tagset}
else:
	kwargs = {}

for word, tag in tagged_corpus.tagged_words(fileids=args.fileids, **kwargs):
	if not tag:
		continue
	
	if len(tag) > taglen:
		taglen = len(tag)
	
	if args.corpus in ['conll2000', 'switchboard'] and simplify_wsj_tag and args.simplify_tags:
		tag = simplify_wsj_tag(tag)
	
	wc += 1
	# loading corpora/treebank/tagged with ChunkedCorpusReader produces None tags
	if not isinstance(tag, basestring): tag = str(tag)
	tag_counts[tag] += 1
	word_set.add(word)

############
## output ##
############

print('%d total words\n%d unique words\n%d tags\n' % (wc, len(word_set), len(tag_counts)))

if args.sort == 'tag':
	sort_key = lambda tc: tc[0]
elif args.sort == 'count':
	sort_key = lambda tc: tc[1]
else:
	raise ValueError('%s is not a valid sort option' % args.sort)

sorted_tag_counts = sorted(tag_counts.items(), key=sort_key, reverse=args.reverse)
countlen = max(len(str(sorted_tag_counts[0][1])) + 2, 9)
# simple reSt table format
print('  '.join(['Tag'.center(taglen), 'Count'.center(countlen)]))
print('  '.join(['='*taglen, '='*(countlen)]))

for tag, count in sorted_tag_counts:
	print('  '.join([tag.ljust(taglen), str(count).rjust(countlen)]))

print('  '.join(['='*taglen, '='*(countlen)]))
########NEW FILE########
__FILENAME__ = analyze_tagger_coverage
#!/usr/bin/env python
import argparse, collections, math, os.path
import nltk.corpus, nltk.corpus.reader, nltk.data, nltk.tag, nltk.metrics
from nltk.corpus.util import LazyCorpusLoader
from nltk_trainer import load_corpus_reader, load_model, simplify_wsj_tag
from nltk_trainer.tagging import taggers

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Analyze a part-of-speech tagger on a tagged corpus',
	formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('corpus',
	help='''The name of a tagged corpus included with NLTK, such as treebank,
brown, cess_esp, floresta, or the root path to a corpus directory,
which can be either an absolute path or relative to a nltk_data directory.''')
parser.add_argument('--tagger', default=nltk.tag._POS_TAGGER,
	help='''pickled tagger filename/path relative to an nltk_data directory
default is NLTK's default tagger''')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')
parser.add_argument('--metrics', action='store_true', default=False,
	help='Use tagged sentences to determine tagger accuracy and tag precision & recall')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader', default=None,
	help='''Full module path to a corpus reader class, such as
nltk.corpus.reader.tagged.TaggedCorpusReader''')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')
corpus_group.add_argument('--fraction', default=1.0, type=float,
	help='''The fraction of the corpus to use for testing coverage''')

if simplify_wsj_tag:
	corpus_group.add_argument('--simplify_tags', action='store_true', default=False,
		help='Use simplified tags')
else:
	corpus_group.add_argument('--tagset', default=None,
		help='Map tags to a given tagset, such as "universal"')

args = parser.parse_args()

###################
## corpus reader ##
###################

corpus = load_corpus_reader(args.corpus, reader=args.reader, fileids=args.fileids)

kwargs = {'fileids': args.fileids}

if simplify_wsj_tag and args.simplify_tags and not args.metrics:
	raise ValueError('simplify_tags can only be used with the --metrics option')
elif simplify_wsj_tag and args.simplify_tags and args.corpus not in ['conll2000', 'switchboard']:
	kwargs['simplify_tags'] = True
elif not simplify_wsj_tag and args.tagset and not args.metrics:
	raise ValueError('tagset can only be used with the --metrics option')
elif not simplify_wsj_tag and args.tagset:
	kwargs['tagset'] = args.tagset

# TODO: support corpora with alternatives to tagged_sents that work just as well
if args.metrics and not hasattr(corpus, 'tagged_sents'):
	raise ValueError('%s does not support metrics' % args.corpus)

############
## tagger ##
############

if args.trace:
	print('loading tagger %s' % args.tagger)

if args.tagger == 'pattern':
	tagger = taggers.PatternTagger()
else:
	tagger = load_model(args.tagger)

#######################
## coverage analysis ##
#######################

if args.trace:
	print('analyzing tag coverage of %s with %s\n' % (args.corpus, tagger.__class__.__name__))

tags_found = collections.defaultdict(int)
unknown_words = set()

if args.metrics:
	tags_actual = collections.defaultdict(int)
	tag_refs = []
	tag_test = []
	tag_word_refs = collections.defaultdict(set)
	tag_word_test = collections.defaultdict(set)
	tagged_sents = corpus.tagged_sents(**kwargs)
	taglen = 7
	
	if args.fraction != 1.0:
		cutoff = int(math.ceil(len(tagged_sents) * args.fraction))
		tagged_sents = tagged_sents[:cutoff]
	
	for tagged_sent in tagged_sents:
		for word, tag in tagged_sent:
			tags_actual[tag] += 1
			tag_refs.append(tag)
			tag_word_refs[tag].add(word)
			
			if len(tag) > taglen:
				taglen = len(tag)
		
		for word, tag in tagger.tag(nltk.tag.untag(tagged_sent)):
			tags_found[tag] += 1
			tag_test.append(tag)
			tag_word_test[tag].add(word)
			
			if tag == '-NONE-':
				unknown_words.add(word)
	
	print('Accuracy: %f' % nltk.metrics.accuracy(tag_refs, tag_test))
	print('Unknown words: %d' % len(unknown_words))
	
	if args.trace and unknown_words:
		print(', '.join(sorted(unknown_words)))
	
	print('')
	print('  '.join(['Tag'.center(taglen), 'Found'.center(9), 'Actual'.center(10),
					'Precision'.center(13), 'Recall'.center(13)]))
	print('  '.join(['='*taglen, '='*9, '='*10, '='*13, '='*13]))
	
	for tag in sorted(set(tags_found.keys()) | set(tags_actual.keys())):
		found = tags_found[tag]
		actual = tags_actual[tag]
		precision = nltk.metrics.precision(tag_word_refs[tag], tag_word_test[tag])
		recall = nltk.metrics.recall(tag_word_refs[tag], tag_word_test[tag])
		print('  '.join([tag.ljust(taglen), str(found).rjust(9), str(actual).rjust(10),
			str(precision).ljust(13)[:13], str(recall).ljust(13)[:13]]))
	
	print('  '.join(['='*taglen, '='*9, '='*10, '='*13, '='*13]))
else:
	sents = corpus.sents(**kwargs)
	taglen = 7
	
	if args.fraction != 1.0:
		cutoff = int(math.ceil(len(sents) * args.fraction))
		sents = sents[:cutoff]
	
	for sent in sents:
		for word, tag in tagger.tag(sent):
			tags_found[tag] += 1
			
			if len(tag) > taglen:
				taglen = len(tag)
	
	print('  '.join(['Tag'.center(taglen), 'Count'.center(9)]))
	print('  '.join(['='*taglen, '='*9]))
	
	for tag in sorted(tags_found.keys()):
		print('  '.join([tag.ljust(taglen), str(tags_found[tag]).rjust(9)]))
	
	print('  '.join(['='*taglen, '='*9]))
########NEW FILE########
__FILENAME__ = categorized_corpus2csv
#!/usr/bin/env python
import argparse, csv, os.path
import nltk_trainer.classification.corpus
from nltk_trainer import load_corpus_reader

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Dump a classified corpus to CSV')

parser.add_argument('corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('--filename', default='', help='''filename/path for where to
	store the CSV. The default is the "basename_instances.csv" where basename is
	the corpus name or the basename of the corpus path, and instances is one of
	sents, paras, or file, as given by the --instances argument.''')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')

corpus_group = parser.add_argument_group('Classified Corpus')
corpus_group.add_argument('--instances', default='paras',
	choices=('sents', 'paras', 'files'),
	help='''the group of words that represents a single training instance,
	the default is to use entire files''')
corpus_group.add_argument('--fraction', default=1.0, type=float,
	help='''The fraction of the corpus to use for training a binary or
	multi-class classifier, the rest will be used for evaulation.
	The default is to use the entire corpus, and to test the classifier
	against the same training data. Any number < 1 will test against
	the remaining fraction.''')

args = parser.parse_args()

###################
## corpus reader ##
###################

if args.trace:
	print 'loading corpus %s' % args.corpus

corpus = load_corpus_reader(args.corpus)

methods = {
	'sents': nltk_trainer.classification.corpus.category_sent_strings,
	'paras': nltk_trainer.classification.corpus.category_para_strings,
	'files': nltk_trainer.classification.corpus.category_file_strings
}

cat_instances = methods[args.instances](corpus)

################
## CSV output ##
################

filename = args.filename

if not filename:
	filename = '%s_%s.csv' % (os.path.basename(args.corpus), args.instances)

if args.trace:
	print 'writing to %s' % filename

with open(filename, 'w') as f:
	w = csv.writer(f, quoting=csv.QUOTE_ALL)
	
	for cat, text in cat_instances:
		w.writerow([cat, text])

########NEW FILE########
__FILENAME__ = classify_corpus
#!/usr/bin/env python
import argparse, itertools, operator, os, os.path, string
import nltk.data
from nltk.corpus import stopwords
from nltk.misc import babelfish
from nltk.tokenize import wordpunct_tokenize
from nltk.util import ngrams
from nltk_trainer import load_corpus_reader, join_words, translate
from nltk_trainer.classification.featx import bag_of_words

langs = [l.lower() for l in babelfish.available_languages]

########################################
## command options & argument parsing ##
########################################

# TODO: many of the args are shared with analyze_classifier_coverage, so abstract

parser = argparse.ArgumentParser(description='Classify a plaintext corpus to a classified corpus')
# TODO: make sure source_corpus can be a single file
parser.add_argument('source_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('target_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')

classifier_group = parser.add_argument_group('Classification Options')
parser.add_argument('--classifier', default=None,
	help='pickled classifier name/path relative to an nltk_data directory')
parser.add_argument('--wordlist', default=None,
	help='classified word list corpus for word/phrase classification')
parser.add_argument('--threshold', type=float, default=0.9,
	help='Minimum probability required to write classified instance')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader',
	default='nltk.corpus.reader.CategorizedPlaintextCorpusReader',
	help='Full module path to a corpus reader class, such as %(default)s')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')
corpus_group.add_argument('--instances', default='paras', choices=('sents', 'paras'),
	help='''the group of words that represents a single training instance,
	the default is to use entire files''')

feat_group = parser.add_argument_group('Feature Extraction',
	'The default is to lowercase every word, strip punctuation, and use stopwords')
feat_group.add_argument('--ngrams', action='append', type=int,
	help='use n-grams as features.')
feat_group.add_argument('--no-lowercase', action='store_true', default=False,
	help="don't lowercase every word")
feat_group.add_argument('--filter-stopwords', default='no',
	choices=['no']+stopwords.fileids(),
	help='language stopwords to filter, defaults to "no" to keep stopwords')
feat_group.add_argument('--punctuation', action='store_true', default=False,
	help="don't strip punctuation")

trans_group = parser.add_argument_group('Language Translation')
trans_group.add_argument('--source', default='english', choices=langs, help='source language')
trans_group.add_argument('--target', default=None, choices=langs, help='target language')
trans_group.add_argument('--retries', default=3, type=int,
	help='Number of babelfish retries before quiting')
trans_group.add_argument('--sleep', default=3, type=int,
	help='Sleep time between retries')

args = parser.parse_args()

###################
## corpus reader ##
###################

source_corpus = load_corpus_reader(args.source_corpus, args.reader)

if not source_corpus:
	raise ValueError('%s is an unknown corpus')

if args.trace:
	print 'loaded %s' % args.source_corpus

########################
## text normalization ##
########################

# TODO: copied from analyze_classifier_coverage, so abstract

if args.filter_stopwords == 'no':
	stopset = set()
else:
	stopset = set(stopwords.words(args.filter_stopwords))

if not args.punctuation:
	stopset |= set(string.punctuation)

def norm_words(words):
	if not args.no_lowercase:
		words = [w.lower() for w in words]
	
	if not args.punctuation:
		words = [w.strip(string.punctuation) for w in words]
		words = [w for w in words if w]
	
	if stopset:
		words = [w for w in words if w.lower() not in stopset]

	if args.ngrams:
		return reduce(operator.add, [words if n == 1 else ngrams(words, n) for n in args.ngrams])
	else:
		return words

##############
## classify ##
##############

if args.wordlist:
	classifier = WordListClassifier(load_corpus_reader(args.wordlist))
elif args.classifier:
	if args.trace:
		print 'loading %s' % args.classifier
	
	classifier = nltk.data.load(args.classifier)
else:
	raise ValueError('one of wordlist or classifier is needed')

def label_filename(label):
	# TODO: better file path based on args.target_corpus & label
	path = os.path.join(args.target_corpus, '%s.txt' % label)
	
	if not os.path.exists(args.target_corpus):
		os.makedirs(args.target_corpus)
	
	if args.trace:
		print 'filename for category %s: %s' % (label, path)
	
	return path

labels = classifier.labels()
label_files = dict([(l, open(label_filename(l), 'a')) for l in labels])

# TODO: create a nltk.corpus.writer framework with some initial CorpusWriter classes

if args.target:
	if args.trace:
		print 'translating all text from %s to %s' % (args.source, args.target)
	
	featx = lambda words: bag_of_words(norm_words(wordpunct_tokenize(translate(join_words(words),
		args.source, args.target, trace=args.trace, sleep=args.sleep, retries=args.retries))))
else:
	featx = lambda words: bag_of_words(norm_words(words))

def classify_write(words):
	feats = featx(words)
	probs = classifier.prob_classify(feats)
	label = probs.max()
	
	if probs.prob(label) >= args.threshold:
		label_files[label].write(join_words(words) + u'\n\n')

if args.trace:
	print 'classifying %s' % args.instances

if args.instances == 'paras':
	for para in source_corpus.paras():
		classify_write(list(itertools.chain(*para)))
else: # args.instances == 'sents'
	for sent in source_corpus.sents():
		classify_write(sent)


# TODO: arg(s) to specify categorized word list corpus instead of classifier pickle
# can have additional arguments for decision threshold. this will create a
# KeywordClassifier that can be used just like any other NLTK classifier

# TODO: if new corpus files already exist, append to them, and make sure the
# first append example is separate (enough) from the last example in the file
# (we don't want to append a paragraph right next to another paragraph, creating a single paragraph)
########NEW FILE########
__FILENAME__ = combine_classifiers
#!/usr/bin/env python
import argparse, os.path
import nltk.data
from nltk_trainer import dump_object
from nltk_trainer.classification import multi

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Combine NLTK Classifiers')
parser.add_argument('classifiers', nargs='+',
	help='one or more pickled classifiers to load and combine')
parser.add_argument('filename', default='~/nltk_data/classifiers/combined.pickle',
	help='Filename to pickle combined classifier, defaults to %(default)s')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')
parser.add_argument('--hierarchy', nargs='+', default=[],
	help='''Mapping of labels to classifier pickle paths to specify a classification hierarchy, such as
	"-h neutral:classifiers/movie_reviews.pickle"
	''')

args = parser.parse_args()

#####################
## AvgProb combine ##
#####################

# TODO: support MaxVote combining

classifiers = []

for name in args.classifiers:
	if args.trace:
		print 'loading %s' % name
	
	classifiers.append(nltk.data.load(name))

combined = multi.AvgProbClassifier(classifiers)

##########################
## Hierarchical combine ##
##########################

labels = combined.labels()
label_classifiers = {}

for h in args.hierarchy:
	label, path = h.split(':')
	
	if label not in labels:
		raise ValueError('%s is not in root labels: %s' % (label, labels))
	
	label_classifiers[label] = nltk.data.load(path)
	
	if args.trace:
		print 'mapping %s to %s from %s' % (label, label_classifiers[label], path)

if label_classifiers:
	if args.trace:
		'combining %d label classifiers for root %s' % (len(label_classifiers), combined)
	
	combined = multi.HierarchicalClassifier(combined, label_classifiers)

##############################
## dump combined classifier ##
##############################

fname = os.path.expanduser(args.filename)
dump_object(combined, fname, trace=args.trace)
########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# NLTK-Trainer documentation build configuration file, created by
# sphinx-quickstart on Sun Jul 31 12:24:48 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'NLTK-Trainer'
copyright = u'2011, Jacob Perkins'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '1.0'
# The full version, including alpha/beta/rc tags.
release = '1.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'NLTK-Trainerdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'NLTK-Trainer.tex', u'NLTK-Trainer Documentation',
   u'Jacob Perkins', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = chunkers
import nltk.tag
from nltk.chunk import ChunkParserI
from nltk.chunk.util import conlltags2tree, tree2conlltags
from nltk.tag import UnigramTagger, BigramTagger, ClassifierBasedTagger
from .transforms import node_label

#####################
## tree conversion ##
#####################

def chunk_trees2train_chunks(chunk_sents):
	tag_sents = [tree2conlltags(sent) for sent in chunk_sents]
	return [[((w,t),c) for (w,t,c) in sent] for sent in tag_sents]

def conll_tag_chunks(chunk_sents):
	'''Convert each chunked sentence to list of (tag, chunk_tag) tuples,
	so the final result is a list of lists of (tag, chunk_tag) tuples.
	>>> from nltk.tree import Tree
	>>> t = Tree('S', [Tree('NP', [('the', 'DT'), ('book', 'NN')])])
	>>> conll_tag_chunks([t])
	[[('DT', 'B-NP'), ('NN', 'I-NP')]]
	'''
	tagged_sents = [tree2conlltags(tree) for tree in chunk_sents]
	return [[(t, c) for (w, t, c) in sent] for sent in tagged_sents]

def ieertree2conlltags(tree, tag=nltk.tag.pos_tag):
	# tree.pos() flattens the tree and produces [(word, label)] where label is
	# from the word's parent tree label. words in a chunk therefore get the
	# chunk tag, while words outside a chunk get the same tag as the tree's
	# top label
	words, ents = zip(*tree.pos())
	iobs = []
	prev = None
	# construct iob tags from entity names
	for ent in ents:
		# any entity that is the same as the tree's top label is outside a chunk
		if ent == node_label(tree):
			iobs.append('O')
			prev = None
		# have a previous entity that is equal so this is inside the chunk
		elif prev == ent:
			iobs.append('I-%s' % ent)
		# no previous equal entity in the sequence, so this is the beginning of
		# an entity chunk
		else:
			iobs.append('B-%s' % ent)
			prev = ent
	# get tags for each word, then construct 3-tuple for conll tags
	words, tags = zip(*tag(words))
	return zip(words, tags, iobs)

#################
## tag chunker ##
#################

class TagChunker(ChunkParserI):
	'''Chunks tagged tokens using Ngram Tagging.'''
	def __init__(self, train_chunks, tagger_classes=[UnigramTagger, BigramTagger]):
		'''Train Ngram taggers on chunked sentences'''
		train_sents = conll_tag_chunks(train_chunks)
		self.tagger = None
		
		for cls in tagger_classes:
			self.tagger = cls(train_sents, backoff=self.tagger)
	
	def parse(self, tagged_sent):
		'''Parsed tagged tokens into parse Tree of chunks'''
		if not tagged_sent: return None
		(words, tags) = zip(*tagged_sent)
		chunks = self.tagger.tag(tags)
		# create conll str for tree parsing
		return conlltags2tree([(w,t,c) for (w,(t,c)) in zip(words, chunks)])

########################
## classifier chunker ##
########################

def prev_next_pos_iob(tokens, index, history):
	word, pos = tokens[index]
	
	if index == 0:
		prevword, prevpos, previob = ('<START>',)*3
	else:
		prevword, prevpos = tokens[index-1]
		previob = history[index-1]
	
	if index == len(tokens) - 1:
		nextword, nextpos = ('<END>',)*2
	else:
		nextword, nextpos = tokens[index+1]
	
	feats = {
		'word': word,
		'pos': pos,
		'nextword': nextword,
		'nextpos': nextpos,
		'prevword': prevword,
		'prevpos': prevpos,
		'previob': previob
	}
	
	return feats

class ClassifierChunker(ChunkParserI):
	def __init__(self, train_sents, feature_detector=prev_next_pos_iob, **kwargs):
		if not feature_detector:
			feature_detector = self.feature_detector
		
		train_chunks = chunk_trees2train_chunks(train_sents)
		self.tagger = ClassifierBasedTagger(train=train_chunks,
			feature_detector=feature_detector, **kwargs)
	
	def parse(self, tagged_sent):
		if not tagged_sent: return None
		chunks = self.tagger.tag(tagged_sent)
		return conlltags2tree([(w,t,c) for ((w,t),c) in chunks])

#############
## pattern ##
#############

class PatternChunker(ChunkParserI):
	def parse(self, tagged_sent):
		# don't import at top since don't want to fail if not installed
		from pattern.en import parse
		s = ' '.join([word for word, tag in tagged_sent])
		# not tokenizing ensures that the number of tagged tokens returned is
		# the same as the number of input tokens
		sents = parse(s, tokenize=False).split()
		if not sents: return None
		return conlltags2tree([(w, t, c) for w, t, c, p in sents[0]])

########NEW FILE########
__FILENAME__ = transforms
from nltk.tree import Tree

if hasattr(Tree, 'label'):
	def node_label(node):
		return node.label()
else:
	def node_label(node):
		return node.node

def flatten_deeptree(tree):
	'''
	>>> flatten_deeptree(Tree('S', [Tree('NP-SBJ', [Tree('NP', [Tree('NNP', ['Pierre']), Tree('NNP', ['Vinken'])]), Tree(',', [',']), Tree('ADJP', [Tree('NP', [Tree('CD', ['61']), Tree('NNS', ['years'])]), Tree('JJ', ['old'])]), Tree(',', [','])]), Tree('VP', [Tree('MD', ['will']), Tree('VP', [Tree('VB', ['join']), Tree('NP', [Tree('DT', ['the']), Tree('NN', ['board'])]), Tree('PP-CLR', [Tree('IN', ['as']), Tree('NP', [Tree('DT', ['a']), Tree('JJ', ['nonexecutive']), Tree('NN', ['director'])])]), Tree('NP-TMP', [Tree('NNP', ['Nov.']), Tree('CD', ['29'])])])]), Tree('.', ['.'])]))
	Tree('S', [Tree('NP', [('Pierre', 'NNP'), ('Vinken', 'NNP')]), (',', ','), Tree('NP', [('61', 'CD'), ('years', 'NNS')]), ('old', 'JJ'), (',', ','), ('will', 'MD'), ('join', 'VB'), Tree('NP', [('the', 'DT'), ('board', 'NN')]), ('as', 'IN'), Tree('NP', [('a', 'DT'), ('nonexecutive', 'JJ'), ('director', 'NN')]), Tree('NP-TMP', [('Nov.', 'NNP'), ('29', 'CD')]), ('.', '.')])
	'''
	return Tree(node_label(tree), flatten_childtrees([c for c in tree]))

def flatten_childtrees(trees):
	children = []
	
	for t in trees:
		if t.height() < 3:
			children.extend(t.pos())
		elif t.height() == 3:
			children.append(Tree(node_label(t), t.pos()))
		else:
			children.extend(flatten_childtrees([c for c in t]))
	
	return children

def shallow_tree(tree):
	'''
	>>> shallow_tree(Tree('S', [Tree('NP-SBJ', [Tree('NP', [Tree('NNP', ['Pierre']), Tree('NNP', ['Vinken'])]), Tree(',', [',']), Tree('ADJP', [Tree('NP', [Tree('CD', ['61']), Tree('NNS', ['years'])]), Tree('JJ', ['old'])]), Tree(',', [','])]), Tree('VP', [Tree('MD', ['will']), Tree('VP', [Tree('VB', ['join']), Tree('NP', [Tree('DT', ['the']), Tree('NN', ['board'])]), Tree('PP-CLR', [Tree('IN', ['as']), Tree('NP', [Tree('DT', ['a']), Tree('JJ', ['nonexecutive']), Tree('NN', ['director'])])]), Tree('NP-TMP', [Tree('NNP', ['Nov.']), Tree('CD', ['29'])])])]), Tree('.', ['.'])]))
	Tree('S', [Tree('NP-SBJ', [('Pierre', 'NNP'), ('Vinken', 'NNP'), (',', ','), ('61', 'CD'), ('years', 'NNS'), ('old', 'JJ'), (',', ',')]), Tree('VP', [('will', 'MD'), ('join', 'VB'), ('the', 'DT'), ('board', 'NN'), ('as', 'IN'), ('a', 'DT'), ('nonexecutive', 'JJ'), ('director', 'NN'), ('Nov.', 'NNP'), ('29', 'CD')]), ('.', '.')])
	'''
	children = []
	
	for t in tree:
		if t.height() < 3:
			children.extend(t.pos())
		else:
			children.append(Tree(node_label(t), t.pos()))
	
	return Tree(node_label(tree), children)
########NEW FILE########
__FILENAME__ = args
from nltk.classify import DecisionTreeClassifier, MaxentClassifier, NaiveBayesClassifier, megam
from nltk_trainer import basestring
from nltk_trainer.classification.multi import AvgProbClassifier

classifier_choices = ['NaiveBayes', 'DecisionTree', 'Maxent'] + MaxentClassifier.ALGORITHMS

dense_classifiers = set(['ExtraTreesClassifier', 'GradientBoostingClassifier',
		'RandomForestClassifier', 'GaussianNB', 'DecisionTreeClassifier'])
verbose_classifiers = set(['RandomForestClassifier', 'SVC'])

try:
	import svmlight # do this first since svm module makes ugly errors
	from nltk.classify.svm import SvmClassifier
	classifier_choices.append('Svm')
except:
	pass

try:
	from nltk.classify import scikitlearn
	from sklearn.feature_extraction.text import TfidfTransformer
	from sklearn.pipeline import Pipeline
	from sklearn import ensemble, feature_selection, linear_model, naive_bayes, neighbors, svm, tree
	
	classifiers = [
		ensemble.ExtraTreesClassifier,
		ensemble.GradientBoostingClassifier,
		ensemble.RandomForestClassifier,
		linear_model.LogisticRegression,
		#linear_model.SGDClassifier, # NOTE: this seems terrible, but could just be the options
		naive_bayes.BernoulliNB,
		naive_bayes.GaussianNB,
		naive_bayes.MultinomialNB,
		neighbors.KNeighborsClassifier, # TODO: options for nearest neighbors
		svm.LinearSVC,
		svm.NuSVC,
		svm.SVC,
		tree.DecisionTreeClassifier,
	]
	sklearn_classifiers = {}
	
	for classifier in classifiers:
		sklearn_classifiers[classifier.__name__] = classifier
	
	classifier_choices.extend(sorted(['sklearn.%s' % c.__name__ for c in classifiers]))
except ImportError as exc:
	sklearn_classifiers = {}

def add_maxent_args(parser):
	maxent_group = parser.add_argument_group('Maxent Classifier',
		'These options only apply when a Maxent classifier is chosen.')
	maxent_group.add_argument('--max_iter', default=10, type=int,
		help='maximum number of training iterations, defaults to %(default)d')
	maxent_group.add_argument('--min_ll', default=0, type=float,
		help='stop classification when average log-likelihood is less than this, default is %(default)d')
	maxent_group.add_argument('--min_lldelta', default=0.1, type=float,
		help='''stop classification when the change in average log-likelihood is less than this.
	default is %(default)f''')

def add_decision_tree_args(parser):
	decisiontree_group = parser.add_argument_group('Decision Tree Classifier',
		'These options only apply when the DecisionTree classifier is chosen')
	decisiontree_group.add_argument('--entropy_cutoff', default=0.05, type=float,
		help='default is 0.05')
	decisiontree_group.add_argument('--depth_cutoff', default=100, type=int,
		help='default is 100')
	decisiontree_group.add_argument('--support_cutoff', default=10, type=int,
		help='default is 10')

sklearn_kwargs = {
	# ensemble
	'ExtraTreesClassifier': ['criterion', 'max_feats', 'depth_cutoff', 'n_estimators'],
	'GradientBoostingClassifier': ['learning_rate', 'max_feats', 'depth_cutoff', 'n_estimators'],
	'RandomForestClassifier': ['criterion', 'max_feats', 'depth_cutoff', 'n_estimators'],
	# linear_model
	'LogisticRegression': ['C','penalty'],
	# naive_bayes
	'BernoulliNB': ['alpha'],
	'MultinomialNB': ['alpha'],
	# svm
	'LinearSVC': ['C', 'loss', 'penalty'],
	'NuSVC': ['nu', 'kernel'],
	'SVC': ['C', 'kernel'],
	# tree
	'DecisionTreeClassifier': ['criterion', 'max_feats', 'depth_cutoff'],
}

def add_sklearn_args(parser):
	if not sklearn_classifiers: return
	
	sklearn_group = parser.add_argument_group('sklearn Classifiers',
		'These options are used by one or more sklearn classification algorithms.')
	sklearn_group.add_argument('--alpha', type=float, default=1.0,
		help='smoothing parameter for naive bayes classifiers, default is %(default)s')
	sklearn_group.add_argument('--C', type=float, default=1.0,
		help='penalty parameter, default is %(default)s')
	sklearn_group.add_argument('--criterion', choices=['gini', 'entropy'],
		default='gini', help='Split quality function, default is %(default)s')
	sklearn_group.add_argument('--kernel', default='rbf',
		choices=['linear', 'poly', 'rbf', 'sigmoid', 'precomputed'],
		help='kernel type for support vector machine classifiers, default is %(default)s')
	sklearn_group.add_argument('--learning_rate', type=float, default=0.1,
		help='learning rate, default is %(default)s')
	sklearn_group.add_argument('--loss', choices=['l1', 'l2'],
		default='l2', help='loss function, default is %(default)s')
	sklearn_group.add_argument('--n_estimators', type=int, default=10,
		help='Number of trees for Decision Tree ensembles, default is %(default)s')
	sklearn_group.add_argument('--nu', type=float, default=0.5,
		help='upper bound on fraction of training errors & lower bound on fraction of support vectors, default is %(default)s')
	sklearn_group.add_argument('--penalty', choices=['l1', 'l2'],
		default='l2', help='norm for penalization, default is %(default)s')
	sklearn_group.add_argument('--tfidf', default=False, action='store_true',
		help='Use TfidfTransformer')

# for mapping existing args to sklearn args
sklearn_keys = {
	'max_feats': 'max_features',
	'depth_cutoff': 'max_depth'
}

def make_sklearn_classifier(algo, args):
	name = algo.split('.', 1)[1]
	kwargs = {}
	
	for key in sklearn_kwargs.get(name, []):
		val = getattr(args, key, None)
		if val: kwargs[sklearn_keys.get(key, key)] = val
	
	if args.trace and kwargs:
		print('training %s with %s' % (algo, kwargs))
	
	if args.trace and name in verbose_classifiers:
		kwargs['verbose'] = True
	
	return sklearn_classifiers[name](**kwargs)

def make_classifier_builder(args):
	if isinstance(args.classifier, basestring):
		algos = [args.classifier]
	else:
		algos = args.classifier
	
	for algo in algos:
		if algo not in classifier_choices:
			raise ValueError('classifier %s is not supported' % algo)
	
	classifier_train_args = []
	
	for algo in algos:
		classifier_train_kwargs = {}
		
		if algo == 'DecisionTree':
			classifier_train = DecisionTreeClassifier.train
			classifier_train_kwargs['binary'] = False
			classifier_train_kwargs['entropy_cutoff'] = args.entropy_cutoff
			classifier_train_kwargs['depth_cutoff'] = args.depth_cutoff
			classifier_train_kwargs['support_cutoff'] = args.support_cutoff
			classifier_train_kwargs['verbose'] = args.trace
		elif algo == 'NaiveBayes':
			classifier_train = NaiveBayesClassifier.train
		elif algo == 'Svm':
			classifier_train = SvmClassifier.train
		elif algo.startswith('sklearn.'):
			# TODO: support many options for building an estimator pipeline
			pipe = [('classifier', make_sklearn_classifier(algo, args))]
			tfidf = getattr(args, 'tfidf', None)
			penalty = getattr(args, 'penalty', None)
			
			if tfidf and penalty:
				if args.trace:
					print('using tfidf transformer with norm %s' % penalty)
				
				pipe.insert(0, ('tfidf', TfidfTransformer(norm=penalty)))
			
			sparse = pipe[-1][1].__class__.__name__ not in dense_classifiers
			
			if not sparse and args.trace:
				print('using dense matrix')
			
			value_type = getattr(args, 'value_type', 'bool')
			
			if value_type == 'bool' and not tfidf:
				dtype = bool
			elif value_type == 'int' and not tfidf:
				dtype = int
			else:
				dtype = float
			
			if args.trace:
				print('using dtype %s' % dtype.__name__)
			
			classifier_train = scikitlearn.SklearnClassifier(Pipeline(pipe), dtype=dtype, sparse=sparse).train
		else:
			if algo != 'Maxent':
				classifier_train_kwargs['algorithm'] = algo
				
				if algo == 'MEGAM':
					megam.config_megam()
			
			classifier_train = MaxentClassifier.train
			classifier_train_kwargs['max_iter'] = args.max_iter
			classifier_train_kwargs['min_ll'] = args.min_ll
			classifier_train_kwargs['min_lldelta'] = args.min_lldelta
			classifier_train_kwargs['trace'] = args.trace
		
		classifier_train_args.append((algo, classifier_train, classifier_train_kwargs))
	
	def trainf(train_feats):
		classifiers = []
		
		for algo, classifier_train, train_kwargs in classifier_train_args:
			if args.trace:
				print('training %s classifier' % algo)
			
			classifiers.append(classifier_train(train_feats, **train_kwargs))
		
		if len(classifiers) == 1:
			return classifiers[0]
		else:
			return AvgProbClassifier(classifiers)
	
	return trainf
	#return lambda(train_feats): classifier_train(train_feats, **classifier_train_kwargs)

########NEW FILE########
__FILENAME__ = corpus
import itertools

def category_words(categorized_corpus):
	for category in categorized_corpus.categories():
		yield category, categorized_corpus.words(categories=[category])

def category_fileidset(categorized_corpus, category):
	return set(categorized_corpus.fileids(categories=[category]))

def category_sent_words(categorized_corpus, category):
	return categorized_corpus.sents(categories=[category])

def category_para_words(categorized_corpus, category):
	for para in categorized_corpus.paras(categories=[category]):
		yield itertools.chain(*para)

def category_file_words(categorized_corpus, category):
	for fileid in category_fileidset(categorized_corpus, category):
		yield categorized_corpus.words(fileids=[fileid])

## multi category corpus ##

def corpus_fileid_categories(categorized_corpus, prefix):
	for fileid in categorized_corpus.fileids():
		if not prefix or fileid.startswith(prefix):
			yield fileid, set(categorized_corpus.categories(fileids=[fileid]))
	
def multi_category_sent_words(categorized_corpus, fileid_prefix=''):
	for fileid, categories in corpus_fileid_categories(categorized_corpus, fileid_prefix):
		for sent in categorized_corpus.sents(fileids=[fileid]):
			yield sent, categories

def multi_category_para_words(categorized_corpus, fileid_prefix=''):
	for fileid, categories in corpus_fileid_categories(categorized_corpus, fileid_prefix):
		for para in categorized_corpus.paras(fileids=[fileid]):
			yield itertools.chain(*para), categories

def multi_category_file_words(categorized_corpus, fileid_prefix=''):
	for fileid, categories in corpus_fileid_categories(categorized_corpus, fileid_prefix):
		yield categorized_corpus.words(fileids=[fileid]), categories

################
## csv output ##
################

def category_sent_strings(corpus):
	for cat in corpus.categories():
		for sent in corpus.sents(categories=[cat]):
			yield cat, ' '.join(sent)

def category_para_strings(corpus):
	for cat in corpus.categories():
		for para in corpus.paras(categories=[cat]):
			yield cat, ' '.join([' '.join(sent) for sent in para])

def category_file_strings(corpus):
	for cat in corpus.categories():
		for fileid in corpus.fileids(categories=[cat]):
			yield cat, corpus.raw(fileids=[fileid])
########NEW FILE########
__FILENAME__ = featx
import math
from nltk import probability

def bag_of_words(words):
	return dict([(word, True) for word in words])

def bag_of_words_in_set(words, wordset):
	return bag_of_words(set(words) & wordset)

def word_counts(words):
	return dict(probability.FreqDist((w for w in words)))

def word_counts_in_set(words, wordset):
	return word_counts((w for w in words if w in wordset))

def train_test_feats(label, instances, featx=bag_of_words, fraction=0.75):
	labeled_instances = [(featx(i), label) for i in instances]
	
	if fraction != 1.0:
		l = len(instances)
		cutoff = int(math.ceil(l * fraction))
		return labeled_instances[:cutoff], labeled_instances[cutoff:]
	else:
		return labeled_instances, labeled_instances
########NEW FILE########
__FILENAME__ = multi
import collections, copy, itertools
from nltk.classify import ClassifierI, MultiClassifierI
from nltk.probability import DictionaryProbDist, MutableProbDist
from nltk_trainer import iteritems

class HierarchicalClassifier(ClassifierI):
	def __init__(self, root, label_classifiers):
		self.root = root
		self.label_classifiers = label_classifiers
		self._labels = copy.copy(self.root.labels())
		
		for label, classifier in self.label_classifiers.items():
			# label will never be returned from self.classify()
			self._labels.remove(label)
			self._labels.extend(classifier.labels())
	
	def labels(self):
		return self._labels
	
	def classify(self, feat):
		label = self.root.classify(feat)
		
		if label in self.label_classifiers:
			return self.label_classifiers[label].classify(feat)
		else:
			return label
	
	def prob_classify(self, feat):
		probs = self.root.prob_classify(feat)
		# passing in self.labels() ensures it doesn't have any of label_classifiers.keys()
		mult = MutableProbDist(probs, self.labels(), store_logs=False)
		
		for classifier in self.label_classifiers.values():
			pd = classifier.prob_classify(feat)
			
			for sample in pd.samples():
				mult.update(sample, pd.prob(sample), log=False)
		
		return mult

class AvgProbClassifier(ClassifierI):
	def __init__(self, classifiers):
		self._classifiers = classifiers
		self._labels = sorted(set(itertools.chain(*[c.labels() for c in classifiers])))
	
	def labels(self):
		return self._labels
	
	def classify(self, feat):
		'''Return the label with the most agreement among classifiers'''
		label_freqs = collections.Counter()
		
		for classifier in self._classifiers:
			label_freqs[classifier.classify(feat)] += 1
		
		return label_freqs.most_common(1)[0][0]
	
	def prob_classify(self, feat):
		'''Return ProbDistI of averaged label probabilities.'''
		label_probs = collections.defaultdict(list)
		
		for classifier in self._classifiers:
			try:
				cprobs = classifier.prob_classify(feat)
				
				for label in cprobs.samples():
					label_probs[label].append(cprobs.prob(label))
			except NotImplementedError:
				# if we can't do prob_classify (like for DecisionTree)
				# assume 100% probability from classify
				label_probs[classifier.classify(feat)].append(1)
		
		avg_probs = {}
		
		for label, probs in label_probs.items():
			avg_probs[label] = float(sum(probs)) / len(probs)
		
		return DictionaryProbDist(avg_probs)

class MultiBinaryClassifier(MultiClassifierI):
	def __init__(self, label_classifiers):
		self._label_classifiers = label_classifiers
		self._labels = sorted(label_classifiers.keys())
	
	def labels(self):
		return self._labels
	
	def classify(self, feats):
		lbls = set()
		
		for label, classifier in iteritems(self._label_classifiers):
			if classifier.classify(feats) is True:
				lbls.add(label)
		
		return lbls
	
	@classmethod
	def train(cls, labels, multi_label_feats, trainf, **train_kwargs):
		labelset = set(labels)
		label_feats = collections.defaultdict(list)
		pos_label_feats = collections.defaultdict(set)
		
		for feat, multi_labels in multi_label_feats:
			for label in multi_labels:
				label_feats[label].append((feat, True))
				# dicts are unhashable, so use a normalized tuple of key-values
				pos_label_feats[label].add(tuple(sorted(feat.items())))
			
			for label in labelset - set(multi_labels):
				label_feats[label].append((feat, False))
		
		for label in label_feats.keys():
			feats = []
			# this re-creates the feats list by ignoring any negative feat dicts
			# that are also in pos_label_feats[label] so we don't create
			# training conflicts
			for feat, l in label_feats[label]:
				if l or tuple(sorted(feat.items())) not in pos_label_feats[label]:
					feats.append((feat, l))
			
			label_feats[label] = feats
		
		label_classifiers = {}
		
		for label, feats in iteritems(label_feats):
			label_classifiers[label] = trainf(feats, **train_kwargs)
		
		return cls(label_classifiers)
########NEW FILE########
__FILENAME__ = sci
import scipy.sparse
from scikits.learn.base import BaseEstimator
from scikits.learn.feature_extraction.text.dense import BaseCountVectorizer
from scikits.learn.svm.sparse import LinearSVC
from scikits.learn.pipeline import Pipeline
from nltk.classify import ClassifierI

class BagOfWordsAnalyzer(BaseEstimator):
	def analyze(self, feats):
		# this will work for feat dicts and lists of tokens
		return feats

BOWAnalyzer = BagOfWordsAnalyzer()

class BagOfWordsVectorizer(BaseCountVectorizer):
	def __init__(self, analyzer=BOWAnalyzer, max_df=None):
		BaseCountVectorizer.__init__(self, analyzer=analyzer, max_df=max_df)
	
	def _term_count_dicts_to_matrix(self, term_count_dicts, vocabulary):
		i_indices, j_indices, values = [], [], []
		
		for i, term_count_dict in enumerate(term_count_dicts):
			for term in term_count_dict.iterkeys(): # ignore counts
				j = vocabulary.get(term)
				
				if j is not None:
					i_indices.append(i)
					j_indices.append(j)
					values.append(1)
			
			term_count_dict.clear()
		
		shape = (len(term_count_dicts), max(vocabulary.itervalues()) + 1)
		return scipy.sparse.coo_matrix((values, (i_indices, j_indices)),
			shape=shape, dtype=self.dtype)

class ScikitsClassifier(ClassifierI):
	def __init__(self, pipeline, target_names):
		self.pipeline = pipeline
		self.target_names = target_names
	
	def labels(self):
		return self.target_names
	
	def classify(self, featureset):
		return self.target_names[self.pipeline.predict([featureset])[0]]
	
	@classmethod
	def train(cls, labeled_featuresets):
		train, target_labels = zip(*labeled_featuresets)
		target_names = sorted(set(target_labels))
		targets = [target_names.index(l) for l in target_labels]
		
		pipeline = Pipeline([
			('bow', BagOfWordsVectorizer()),
			('clf', LinearSVC(C=1000)),
		])
		
		pipeline.fit(train, targets)
		return cls(pipeline, target_names)
########NEW FILE########
__FILENAME__ = scoring
import collections, itertools, random
from numpy import array
from nltk.metrics import masi_distance, f_measure, precision, recall
from nltk_trainer import iteritems

def sum_category_word_scores(categorized_words, score_fn):
	word_fd = collections.Counter()
	category_word_fd = collections.defaultdict(collections.Counter)
	
	for category, words in categorized_words:
		for word in words:
			word_fd[word] += 1
			category_word_fd[category][word] += 1
	
	scores = collections.defaultdict(int)
	n_xx = sum(itertools.chain(*[fd.values() for fd in category_word_fd.values()]))
	
	for category in category_word_fd.keys():
		n_xi = sum(category_word_fd[category].values())
		
		for word, n_ii in iteritems(category_word_fd[category]):
			n_ix = word_fd[word]
			scores[word] += score_fn(n_ii, (n_ix, n_xi), n_xx)
	
	return scores

def sorted_word_scores(wsdict):
	return sorted(wsdict.items(), key=lambda ws: ws[1], reverse=True)

def ref_test_sets(classifier, test_feats):
	refsets = collections.defaultdict(set)
	testsets = collections.defaultdict(set)
	
	for i, (feat, label) in enumerate(test_feats):
		refsets[label].add(i)
		observed = classifier.classify(feat)
		testsets[observed].add(i)
	
	return refsets, testsets

def multi_ref_test_sets(multi_classifier, multi_label_feats):
	refsets = collections.defaultdict(set)
	testsets = collections.defaultdict(set)
	
	for i, (feat, labels) in enumerate(multi_label_feats):
		for label in labels:
			refsets[label].add(i)
		
		for label in multi_classifier.classify(feat):
			testsets[label].add(i)
	
	return refsets, testsets

def avg_masi_distance(multi_classifier, multi_label_feats):
	mds = []
	
	for feat, labels in multi_label_feats:
		mds.append(masi_distance(labels, multi_classifier.classify(feat)))
	
	if mds:
		return float(sum(mds)) / len(mds)
	else:
		return 0.0

def cross_fold(instances, trainf, testf, folds=10, trace=1, metrics=True, informative=0):
	if folds < 2:
		raise ValueError('must have at least 3 folds')
	# ensure isn't an exhaustible iterable
	instances = list(instances)
	# randomize so get an even distribution, in case labeled instances are
	# ordered by label
	random.shuffle(instances)
	l = len(instances)
	step = int(l / folds)
	
	if trace:
		print('step %d over %d folds of %d instances' % (step, folds, l))
	
	accuracies = []
	precisions = collections.defaultdict(list)
	recalls = collections.defaultdict(list)
	f_measures = collections.defaultdict(list)
	
	for f in range(folds):
		if trace:
			print('\nfold %d' % (f+1))
			print('-----%s' % ('-'*len('%s' % (f+1))))
		
		start = f * step
		end = start + step
		train_instances = instances[:start] + instances[end:]
		test_instances = instances[start:end]
		
		if trace:
			print('training on %d:%d + %d:%d' % (0, start, end, l))
		
		obj = trainf(train_instances)
		
		if trace:
			print('testing on %d:%d' % (start, end))
		
		if metrics:
			refsets, testsets = ref_test_sets(obj, test_instances)
			
			for key in set(refsets.keys()) | set(testsets.keys()):
				ref = refsets[key]
				test = testsets[key]
				p = precision(ref, test) or 0
				r = recall(ref, test) or 0
				f = f_measure(ref, test) or 0
				precisions[key].append(p)
				recalls[key].append(r)
				f_measures[key].append(f)
				
				if trace:
					print('%s precision: %f' % (key, p))
					print('%s recall: %f' % (key, r))
					print('%s f-measure: %f' % (key, f))
		
		accuracy = testf(obj, test_instances)
		
		if trace:
			print('accuracy: %f' % accuracy)
		
		accuracies.append(accuracy)
		
		if trace and informative and hasattr(obj, 'show_most_informative_features'):
			obj.show_most_informative_features(informative)
	
	if trace:
		print('\nmean and variance across folds')
		print('------------------------------')
		print('accuracy mean: %f' % (sum(accuracies) / folds))
		print('accuracy variance: %f' % array(accuracies).var())
		
		for key, ps in iteritems(precisions):
			print('%s precision mean: %f' % (key, sum(ps) / folds))
			print('%s precision variance: %f' % (key, array(ps).var()))
		
		for key, rs in iteritems(recalls):
			print('%s recall mean: %f' % (key, sum(rs) / folds))
			print('%s recall variance: %f' % (key, array(rs).var()))
		
		for key, fs in iteritems(f_measures):
			print('%s f_measure mean: %f' % (key, sum(fs) / folds))
			print('%s f_measure variance: %f' % (key, array(fs).var()))
	
	return accuracies, precisions, recalls, f_measures
########NEW FILE########
__FILENAME__ = metaphone
#!python
#coding= utf-8
# This script implements the Double Metaphone algorithm (c) 1998, 1999 by Lawrence Philips
# it was translated to Python from the C source written by Kevin Atkinson (http://aspell.net/metaphone/)
# By Andrew Collins - January 12, 2007 who claims no rights to this work
# http://atomboy.isa-geek.com/plone/Members/acoil/programing/double-metaphone
# Tested with Python 2.4.3
# Updated Feb 14, 2007 - Found a typo in the 'gh' section
# Updated Dec 17, 2007 - Bugs fixed in 'S', 'Z', and 'J' sections. Thanks Chris Leong!
# Updated 2009-03-05 by Matthew Somerville - Various bug fixes against the reference C++ implementation.

"""
>>> dm(u'aubrey')
('APR', '')
>>> dm(u'richard')
('RXRT', 'RKRT')
>>> dm(u'katherine') == dm(u'catherine')
True
>>> dm(u'Bartoš'), dm(u'Bartosz'), dm(u'Bartosch'), dm(u'Bartos')
(('PRT', ''), ('PRTS', 'PRTX'), ('PRTX', ''), ('PRTS', ''))
"""

import unicodedata


def dm(st):
    """dm(string) -> (string, string or '')
    returns the double metaphone codes for given string - always a tuple
    there are no checks done on the input string, but it should be a single word or name."""
    vowels = ['A', 'E', 'I', 'O', 'U', 'Y']
    st = ''.join((c for c in unicodedata.normalize('NFD', st) if unicodedata.category(c) != 'Mn'))
    st = st.upper()  # st is short for string. I usually prefer descriptive over short, but this var is used a lot!
    is_slavo_germanic = (st.find('W') > -1 or st.find('K') > -1 or st.find('CZ') > -1 or st.find('WITZ') > -1)
    length = len(st)
    first = 2
    st = '-' * first + st + '------'  # so we can index beyond the begining and end of the input string
    last = first + length - 1
    pos = first     # pos is short for position
    pri = sec = ''  # primary and secondary metaphone codes
    # skip these silent letters when at start of word
    if st[first:first + 2] in ["GN", "KN", "PN", "WR", "PS"]:
        pos += 1
    # Initial 'X' is pronounced 'Z' e.g. 'Xavier'
    if st[first] == 'X':
        pri = sec = 'S'  # 'Z' maps to 'S'
        pos += 1
    # main loop through chars in st
    while pos <= last:
        #print str(pos) + '\t' + st[pos]
        ch = st[pos]  # ch is short for character
        # nxt (short for next characters in metaphone code) is set to  a tuple of the next characters in
        # the primary and secondary codes and how many characters to move forward in the string.
        # the secondary code letter is given only when it is different than the primary.
        # This is just a trick to make the code easier to write and read.
        nxt = (None, 1)  # default action is to add nothing and move to next char
        if ch in vowels:
            nxt = (None, 1)
            if pos == first:  # all init vowels now map to 'A'
                nxt = ('A', 1)
        elif ch == 'B':
            #"-mb", e.g", "dumb", already skipped over... see 'M' below
            if st[pos + 1] == 'B':
                nxt = ('P', 2)
            else:
                nxt = ('P', 1)
        elif ch == 'C':
            # various germanic
            if pos > first + 1 and st[pos - 2] not in vowels and st[pos - 1:pos + 2] == 'ACH' and \
               st[pos + 2] not in ['I'] and (st[pos + 2] not in ['E'] or st[pos - 2:pos + 4] in ['BACHER', 'MACHER']):
                nxt = ('K', 2)
            # special case 'CAESAR'
            elif pos == first and st[first:first + 6] == 'CAESAR':
                nxt = ('S', 2)
            elif st[pos:pos + 4] == 'CHIA':  # italian 'chianti'
                nxt = ('K', 2)
            elif st[pos:pos + 2] == 'CH':
                # find 'michael'
                if pos > first and st[pos:pos + 4] == 'CHAE':
                    nxt = ('K', 'X', 2)
                elif pos == first and (st[pos + 1:pos + 6] in ['HARAC', 'HARIS'] or \
                   st[pos + 1:pos + 4] in ["HOR", "HYM", "HIA", "HEM"]) and st[first:first + 5] != 'CHORE':
                    nxt = ('K', 2)
                #germanic, greek, or otherwise 'ch' for 'kh' sound
                elif st[first:first + 4] in ['VAN ', 'VON '] or st[first:first + 3] == 'SCH' \
                   or st[pos - 2:pos + 4] in ["ORCHES", "ARCHIT", "ORCHID"] \
                   or st[pos + 2] in ['T', 'S'] \
                   or ((st[pos - 1] in ["A", "O", "U", "E"] or pos == first) \
                   and st[pos + 2] in ["L", "R", "N", "M", "B", "H", "F", "V", "W"]):
                    nxt = ('K', 2)
                else:
                    if pos > first:
                        if st[first:first + 2] == 'MC':
                            nxt = ('K', 2)
                        else:
                            nxt = ('X', 'K', 2)
                    else:
                        nxt = ('X', 2)
            # e.g, 'czerny'
            elif st[pos:pos + 2] == 'CZ' and st[pos - 2:pos + 2] != 'WICZ':
                nxt = ('S', 'X', 2)
            # e.g., 'focaccia'
            elif st[pos + 1:pos + 4] == 'CIA':
                nxt = ('X', 3)
            # double 'C', but not if e.g. 'McClellan'
            elif st[pos:pos + 2] == 'CC' and not (pos == (first + 1) and st[first] == 'M'):
                #'bellocchio' but not 'bacchus'
                if st[pos + 2] in ["I", "E", "H"] and st[pos + 2:pos + 4] != 'HU':
                    # 'accident', 'accede' 'succeed'
                    if (pos == (first + 1) and st[first] == 'A') or \
                       st[pos - 1:pos + 4] in ['UCCEE', 'UCCES']:
                        nxt = ('KS', 3)
                    # 'bacci', 'bertucci', other italian
                    else:
                        nxt = ('X', 3)
                else:
                    nxt = ('K', 2)
            elif st[pos:pos + 2] in ["CK", "CG", "CQ"]:
                nxt = ('K', 2)
            elif st[pos:pos + 2] in ["CI", "CE", "CY"]:
                # italian vs. english
                if st[pos:pos + 3] in ["CIO", "CIE", "CIA"]:
                    nxt = ('S', 'X', 2)
                else:
                    nxt = ('S', 2)
            else:
                # name sent in 'mac caffrey', 'mac gregor
                if st[pos + 1:pos + 3] in [" C", " Q", " G"]:
                    nxt = ('K', 3)
                else:
                    if st[pos + 1] in ["C", "K", "Q"] and st[pos + 1:pos + 3] not in ["CE", "CI"]:
                        nxt = ('K', 2)
                    else:  # default for 'C'
                        nxt = ('K', 1)
        elif ch == u'\xc7':  # will never get here with st.encode('ascii', 'replace') above
            # \xc7 is UTF-8 encoding of Ç
            nxt = ('S', 1)
        elif ch == 'D':
            if st[pos:pos + 2] == 'DG':
                if st[pos + 2] in ['I', 'E', 'Y']:  # e.g. 'edge'
                    nxt = ('J', 3)
                else:
                    nxt = ('TK', 2)
            elif st[pos:pos + 2] in ['DT', 'DD']:
                nxt = ('T', 2)
            else:
                nxt = ('T', 1)
        elif ch == 'F':
            if st[pos + 1] == 'F':
                nxt = ('F', 2)
            else:
                nxt = ('F', 1)
        elif ch == 'G':
            if st[pos + 1] == 'H':
                if pos > first and st[pos - 1] not in vowels:
                    nxt = ('K', 2)
                elif pos < (first + 3):
                    if pos == first:  # 'ghislane', ghiradelli
                        if st[pos + 2] == 'I':
                            nxt = ('J', 2)
                        else:
                            nxt = ('K', 2)
                # Parker's rule (with some further refinements) - e.g., 'hugh'
                elif (pos > (first + 1) and st[pos - 2] in ['B', 'H', 'D']) \
                   or (pos > (first + 2) and st[pos - 3] in ['B', 'H', 'D']) \
                   or (pos > (first + 3) and st[pos - 3] in ['B', 'H']):
                    nxt = (None, 2)
                else:
                    # e.g., 'laugh', 'McLaughlin', 'cough', 'gough', 'rough', 'tough'
                    if pos > (first + 2) and st[pos - 1] == 'U' \
                       and st[pos - 3] in ["C", "G", "L", "R", "T"]:
                        nxt = ('F', 2)
                    else:
                        if pos > first and st[pos - 1] != 'I':
                            nxt = ('K', 2)
            elif st[pos + 1] == 'N':
                if pos == (first + 1) and st[first] in vowels and not is_slavo_germanic:
                    nxt = ('KN', 'N', 2)
                else:
                    # not e.g. 'cagney'
                    if st[pos + 2:pos + 4] != 'EY' and st[pos + 1] != 'Y' and not is_slavo_germanic:
                        nxt = ('N', 'KN', 2)
                    else:
                        nxt = ('KN', 2)
            # 'tagliaro'
            elif st[pos + 1:pos + 3] == 'LI' and not is_slavo_germanic:
                nxt = ('KL', 'L', 2)
            # -ges-,-gep-,-gel-, -gie- at beginning
            elif pos == first and (st[pos + 1] == 'Y' \
               or st[pos + 1:pos + 3] in ["ES", "EP", "EB", "EL", "EY", "IB", "IL", "IN", "IE", "EI", "ER"]):
                nxt = ('K', 'J', 2)
            # -ger-,  -gy-
            elif (st[pos + 1:pos + 3] == 'ER' or st[pos + 1] == 'Y') \
               and st[first:first + 6] not in ["DANGER", "RANGER", "MANGER"] \
               and st[pos - 1] not in ['E', 'I'] and st[pos - 1:pos + 2] not in ['RGY', 'OGY']:
                nxt = ('K', 'J', 2)
            # italian e.g, 'biaggi'
            elif st[pos + 1] in ['E', 'I', 'Y'] or st[pos - 1:pos + 3] in ["AGGI", "OGGI"]:
                # obvious germanic
                if st[first:first + 4] in ['VON ', 'VAN '] or st[first:first + 3] == 'SCH' \
                   or st[pos + 1:pos + 3] == 'ET':
                    nxt = ('K', 2)
                else:
                    # always soft if french ending
                    if st[pos + 1:pos + 5] == 'IER ':
                        nxt = ('J', 2)
                    else:
                        nxt = ('J', 'K', 2)
            elif st[pos + 1] == 'G':
                nxt = ('K', 2)
            else:
                nxt = ('K', 1)
        elif ch == 'H':
            # only keep if first & before vowel or btw. 2 vowels
            if (pos == first or st[pos - 1] in vowels) and st[pos + 1] in vowels:
                nxt = ('H', 2)
            else:  # (also takes care of 'HH')
                nxt = (None, 1)
        elif ch == 'J':
            # obvious spanish, 'jose', 'san jacinto'
            if st[pos:pos + 4] == 'JOSE' or st[first:first + 4] == 'SAN ':
                if (pos == first and st[pos + 4] == ' ') or st[first:first + 4] == 'SAN ':
                    nxt = ('H', )
                else:
                    nxt = ('J', 'H')
            elif pos == first and st[pos:pos + 4] != 'JOSE':
                nxt = ('J', 'A')  # Yankelovich/Jankelowicz
            else:
                # spanish pron. of e.g. 'bajador'
                if st[pos - 1] in vowels and not is_slavo_germanic \
                   and st[pos + 1] in ['A', 'O']:
                    nxt = ('J', 'H')
                else:
                    if pos == last:
                        nxt = ('J', ' ')
                    else:
                        if st[pos + 1] not in ["L", "T", "K", "S", "N", "M", "B", "Z"] \
                           and st[pos - 1] not in ["S", "K", "L"]:
                            nxt = ('J', )
                        else:
                            nxt = (None, )
            if st[pos + 1] == 'J':
                nxt = nxt + (2, )
            else:
                nxt = nxt + (1, )
        elif ch == 'K':
            if st[pos + 1] == 'K':
                nxt = ('K', 2)
            else:
                nxt = ('K', 1)
        elif ch == 'L':
            if st[pos + 1] == 'L':
                # spanish e.g. 'cabrillo', 'gallegos'
                if (pos == (last - 2) and st[pos - 1:pos + 3] in ["ILLO", "ILLA", "ALLE"]) \
                   or ((st[last - 1:last + 1] in ["AS", "OS"] or st[last] in ["A", "O"]) \
                   and st[pos - 1:pos + 3] == 'ALLE'):
                    nxt = ('L', ' ', 2)
                else:
                    nxt = ('L', 2)
            else:
                nxt = ('L', 1)
        elif ch == 'M':
            if (st[pos + 1:pos + 4] == 'UMB' \
               and (pos + 1 == last or st[pos + 2:pos + 4] == 'ER')) \
               or st[pos + 1] == 'M':
                nxt = ('M', 2)
            else:
                nxt = ('M', 1)
        elif ch == 'N':
            if st[pos + 1] == 'N':
                nxt = ('N', 2)
            else:
                nxt = ('N', 1)
        elif ch == u'\xd1':  # UTF-8 encoding of ﾄ
            nxt = ('N', 1)
        elif ch == 'P':
            if st[pos + 1] == 'H':
                nxt = ('F', 2)
            elif st[pos + 1] in ['P', 'B']:  # also account for "campbell", "raspberry"
                nxt = ('P', 2)
            else:
                nxt = ('P', 1)
        elif ch == 'Q':
            if st[pos + 1] == 'Q':
                nxt = ('K', 2)
            else:
                nxt = ('K', 1)
        elif ch == 'R':
            # french e.g. 'rogier', but exclude 'hochmeier'
            if pos == last and not is_slavo_germanic \
               and st[pos - 2:pos] == 'IE' and st[pos - 4:pos - 2] not in ['ME', 'MA']:
                nxt = ('', 'R')
            else:
                nxt = ('R', )
            if st[pos + 1] == 'R':
                nxt = nxt + (2, )
            else:
                nxt = nxt + (1, )
        elif ch == 'S':
            # special cases 'island', 'isle', 'carlisle', 'carlysle'
            if st[pos - 1:pos + 2] in ['ISL', 'YSL']:
                nxt = (None, 1)
            # special case 'sugar-'
            elif pos == first and st[first:first + 5] == 'SUGAR':
                nxt = ('X', 'S', 1)
            elif st[pos:pos + 2] == 'SH':
                # germanic
                if st[pos + 1:pos + 5] in ["HEIM", "HOEK", "HOLM", "HOLZ"]:
                    nxt = ('S', 2)
                else:
                    nxt = ('X', 2)
            # italian & armenian
            elif st[pos:pos + 3] in ["SIO", "SIA"] or st[pos:pos + 4] == 'SIAN':
                if not is_slavo_germanic:
                    nxt = ('S', 'X', 3)
                else:
                    nxt = ('S', 3)
            # german & anglicisations, e.g. 'smith' match 'schmidt', 'snider' match 'schneider'
            # also, -sz- in slavic language altho in hungarian it is pronounced 's'
            elif (pos == first and st[pos + 1] in ["M", "N", "L", "W"]) or st[pos + 1] == 'Z':
                nxt = ('S', 'X')
                if st[pos + 1] == 'Z':
                    nxt = nxt + (2, )
                else:
                    nxt = nxt + (1, )
            elif st[pos:pos + 2] == 'SC':
                # Schlesinger's rule
                if st[pos + 2] == 'H':
                    # dutch origin, e.g. 'school', 'schooner'
                    if st[pos + 3:pos + 5] in ["OO", "ER", "EN", "UY", "ED", "EM"]:
                        # 'schermerhorn', 'schenker'
                        if st[pos + 3:pos + 5] in ['ER', 'EN']:
                            nxt = ('X', 'SK', 3)
                        else:
                            nxt = ('SK', 3)
                    else:
                        if pos == first and st[first + 3] not in vowels and st[first + 3] != 'W':
                            nxt = ('X', 'S', 3)
                        else:
                            nxt = ('X', 3)
                elif st[pos + 2] in ['I', 'E', 'Y']:
                    nxt = ('S', 3)
                else:
                    nxt = ('SK', 3)
            # french e.g. 'resnais', 'artois'
            elif pos == last and st[pos - 2:pos] in ['AI', 'OI']:
                nxt = ('', 'S', 1)
            else:
                nxt = ('S', )
                if st[pos + 1] in ['S', 'Z']:
                    nxt = nxt + (2, )
                else:
                    nxt = nxt + (1, )
        elif ch == 'T':
            if st[pos:pos + 4] == 'TION':
                nxt = ('X', 3)
            elif st[pos:pos + 3] in ['TIA', 'TCH']:
                nxt = ('X', 3)
            elif st[pos:pos + 2] == 'TH' or st[pos:pos + 3] == 'TTH':
                # special case 'thomas', 'thames' or germanic
                if st[pos + 2:pos + 4] in ['OM', 'AM'] or st[first:first + 4] in ['VON ', 'VAN '] \
                   or st[first:first + 3] == 'SCH':
                    nxt = ('T', 2)
                else:
                    nxt = ('0', 'T', 2)
            elif st[pos + 1] in ['T', 'D']:
                nxt = ('T', 2)
            else:
                nxt = ('T', 1)
        elif ch == 'V':
            if st[pos + 1] == 'V':
                nxt = ('F', 2)
            else:
                nxt = ('F', 1)
        elif ch == 'W':
            # can also be in middle of word
            if st[pos:pos + 2] == 'WR':
                nxt = ('R', 2)
            elif pos == first and (st[pos + 1] in vowels or st[pos:pos + 2] == 'WH'):
                # Wasserman should match Vasserman
                if st[pos + 1] in vowels:
                    nxt = ('A', 'F', 1)
                else:
                    nxt = ('A', 1)
            # Arnow should match Arnoff
            elif (pos == last and st[pos - 1] in vowels) \
               or st[pos - 1:pos + 4] in ["EWSKI", "EWSKY", "OWSKI", "OWSKY"] \
               or st[first:first + 3] == 'SCH':
                nxt = ('', 'F', 1)
            # polish e.g. 'filipowicz'
            elif st[pos:pos + 4] in ["WICZ", "WITZ"]:
                nxt = ('TS', 'FX', 4)
            else:  # default is to skip it
                nxt = (None, 1)
        elif ch == 'X':
            # french e.g. breaux
            nxt = (None, )
            if not(pos == last and (st[pos - 3:pos] in ["IAU", "EAU"] \
               or st[pos - 2:pos] in ['AU', 'OU'])):
                nxt = ('KS', )
            if st[pos + 1] in ['C', 'X']:
                nxt = nxt + (2, )
            else:
                nxt = nxt + (1, )
        elif ch == 'Z':
            # chinese pinyin e.g. 'zhao'
            if st[pos + 1] == 'H':
                nxt = ('J', )
            elif st[pos + 1:pos + 3] in ["ZO", "ZI", "ZA"] \
               or (is_slavo_germanic and pos > first and st[pos - 1] != 'T'):
                nxt = ('S', 'TS')
            else:
                nxt = ('S', )
            if st[pos + 1] == 'Z' or st[pos + 1] == 'H':
                nxt = nxt + (2, )
            else:
                nxt = nxt + (1, )
        # ----------------------------------
        # --- end checking letters------
        # ----------------------------------
        #print str(nxt)
        if len(nxt) == 2:
            if nxt[0]:
                pri += nxt[0]
                sec += nxt[0]
            pos += nxt[1]
        elif len(nxt) == 3:
            if nxt[0]:
                pri += nxt[0]
            if nxt[1]:
                sec += nxt[1]
            pos += nxt[2]
    if pri == sec:
        return (pri, '')
    else:
        return (pri, sec)

if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = phonetics
# ----------------------------------------------------------
# AdvaS Advanced Search 
# module for phonetic algorithms
#
# (C) 2002 - 2005 Frank Hofmann, Chemnitz, Germany
# email fh@efho.de
# ----------------------------------------------------------

# changed 2005-01-24

import string
import re

def soundex (term):
	"Return the soundex value to a string argument."

	# Create and compare soundex codes of English words.
	#
	# Soundex is an algorithm that hashes English strings into
	# alpha-numerical value that represents what the word sounds
	# like. For more information on soundex and some notes on the
	# differences in implemenations visit:
	# http://www.bluepoof.com/Soundex/info.html
	#
	# This version modified by Nathan Heagy at Front Logic Inc., to be
	# compatible with php's soundexing and much faster.
	#
	# eAndroid / Nathan Heagy / Jul 29 2000
	# changes by Frank Hofmann / Jan 02 2005

	# generate translation table only once. used to translate into soundex numbers
	#table = string.maketrans('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', '0123012002245501262301020201230120022455012623010202')
	table = string.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', '01230120022455012623010202')

	# check parameter
	if not term:
		return "0000" # could be Z000 for compatibility with other implementations
	# end if

		# convert into uppercase letters
	term = string.upper(term)
	first_char = term[0]

	# translate the string into soundex code according to the table above
	term = string.translate(term[1:], table)
	
	# remove all 0s
	term = string.replace(term, "0", "")
	# remove duplicate numbers in-a-row
	str2 = first_char
	for x in term:
		if x != str2[-1]:
			str2 = str2 + x
		# end if
	# end for

	# pad with zeros
	str2 = str2+"0"*len(str2)

	# take the first four letters
	return_value = str2[:4]

	# return value
	return return_value

def metaphone (term):
	"returns metaphone code for a given string"

	# implementation of the original algorithm from Lawrence Philips
	# extended/rewritten by M. Kuhn
	# improvements with thanks to John Machin <sjmachin@lexicon.net>

	# define return value
	code = ""

	i = 0
	term_length = len(term)

	if (term_length == 0):
		# empty string ?
		return code
	# end if

	# extension #1 (added 2005-01-28)
	# convert to lowercase
	term = string.lower(term)
	
	# extension #2 (added 2005-01-28)
	# remove all non-english characters, first
	term = re.sub(r'[^a-z]', '', term)
	if len(term) == 0:
		# nothing left
		return code
	# end if
		
	# extension #3 (added 2005-01-24)
	# conflate repeated letters
	firstChar = term[0]
	str2 = firstChar
	for x in term:
		if x != str2[-1]:
			str2 = str2 + x
		# end if
	# end for
	
	# extension #4 (added 2005-01-24)
	# remove any vowels unless a vowel is the first letter
	firstChar = str2[0]
	str3 = firstChar
	for x in str2[1:]:
		if (re.search(r'[^aeiou]', x)):
			str3 = str3 + x
		# end if
	# end for
	
	term = str3
	term_length = len(term)
	if term_length == 0:
		# nothing left
		return code
	# end if
	
	# check for exceptions
	if (term_length > 1):
		# get first two characters
		first_chars = term[0:2]

		# build translation table
		table = {
			"ae":"e",
			"gn":"n",
			"kn":"n",
			"pn":"n",
			"wr":"n",
			"wh":"w"
		}
		
		if first_chars in table.keys():
			term = term[2:]
			code = table[first_chars]
			term_length = len(term)
		# end if
		
	elif (term[0] == "x"):
		term = ""
		code = "s"
		term_length = 0
	# end if

	# define standard translation table
	st_trans = {
		"b":"b",
		"c":"k",
		"d":"t",
		"g":"k",
		"h":"h",
		"k":"k",
		"p":"p",
		"q":"k",
		"s":"s",
		"t":"t",
		"v":"f",
		"w":"w",
		"x":"ks",
		"y":"y",
		"z":"s"
	}

	i = 0
	while (i<term_length):
		# init character to add, init basic patterns
		add_char = ""
		part_n_2 = ""
		part_n_3 = ""
		part_n_4 = ""
		part_c_2 = ""
		part_c_3 = ""

		# extract a number of patterns, if possible
		if (i < (term_length - 1)):
			part_n_2 = term[i:i+2]

			if (i>0):
				part_c_2 = term[i-1:i+1]
				part_c_3 = term[i-1:i+2]
			# end if
		# end if

		if (i < (term_length - 2)):
			part_n_3 = term[i:i+3]
		# end if

		if (i < (term_length - 3)):
			part_n_4 = term[i:i+4]
		# end if

		# use table with conditions for translations
		if (term[i] == "b"):
			add_char = st_trans["b"]
			if (i == (term_length - 1)):
				if (i>0):
					if (term[i-1] == "m"):
						add_char = ""
					# end if
				# end if
			# end if
		elif (term[i] == "c"):
			add_char = st_trans["c"]
			if (part_n_2 == "ch"):
				add_char = "x"
			elif (re.search(r'c[iey]', part_n_2)):
				add_char = "s"
			# end if

			if (part_n_3 == "cia"):
				add_char = "x"
			# end if

			if (re.search(r'sc[iey]', part_c_3)):
				add_char = ""
			# end if

		elif (term[i] == "d"):
			add_char = st_trans["d"]
			if (re.search(r'dg[eyi]', part_n_3)):
				add_char = "j"
			# end if

		elif (term[i] == "g"):
			add_char = st_trans["g"]

			if (part_n_2 == "gh"):
				if (i == (term_length - 2)):
					add_char = ""
				# end if
			elif (re.search(r'gh[aeiouy]', part_n_3)):
				add_char = ""
			elif (part_n_2 == "gn"):
				add_char = ""
			elif (part_n_4 == "gned"):
				add_char = ""
			elif (re.search(r'dg[eyi]',part_c_3)):
				add_char = ""
			elif (part_n_2 == "gi"):
				if (part_c_3 != "ggi"):
					add_char = "j"
				# end if
			elif (part_n_2 == "ge"):
				if (part_c_3 != "gge"):
					add_char = "j"
				# end if
			elif (part_n_2 == "gy"):
				if (part_c_3 != "ggy"):
					add_char = "j"
				# end if
			elif (part_n_2 == "gg"):
				add_char = ""
			# end if
		elif (term[i] == "h"):
			add_char = st_trans["h"]
			if (re.search(r'[aeiouy]h[^aeiouy]', part_c_3)):
				add_char = ""
			elif (re.search(r'[csptg]h', part_c_2)):
				add_char = ""
			# end if
		elif (term[i] == "k"):
			add_char = st_trans["k"]
			if (part_c_2 == "ck"):
				add_char = ""
			# end if
		elif (term[i] == "p"):
			add_char = st_trans["p"]
			if (part_n_2 == "ph"):
				add_char = "f"
			# end if
		elif (term[i] == "q"):
			add_char = st_trans["q"]
		elif (term[i] == "s"):
			add_char = st_trans["s"]
			if (part_n_2 == "sh"):
				add_char = "x"
			# end if

			if (re.search(r'si[ao]', part_n_3)):
				add_char = "x"
			# end if
		elif (term[i] == "t"):
			add_char = st_trans["t"]
			if (part_n_2 == "th"):
				add_char = "0"
			# end if

			if (re.search(r'ti[ao]', part_n_3)):
				add_char = "x"
			# end if
		elif (term[i] == "v"):
			add_char = st_trans["v"]
		elif (term[i] == "w"):
			add_char = st_trans["w"]
			if (re.search(r'w[^aeiouy]', part_n_2)):
				add_char = ""
			# end if
		elif (term[i] == "x"):
			add_char = st_trans["x"]
		elif (term[i] == "y"):
			add_char = st_trans["y"]
		elif (term[i] == "z"):
			add_char = st_trans["z"]
		else:
			# alternative
			add_char = term[i]
		# end if

		code = code + add_char
		i += 1
	# end while

	# return metaphone code
	return code

def nysiis (term):
	"returns New York State Identification and Intelligence Algorithm (NYSIIS) code for the given term"

	code = ""

	i = 0
	term_length = len(term)

	if (term_length == 0):
		# empty string ?
		return code
	# end if

	# build translation table for the first characters
	table = {
		"mac":"mcc",
		"ph":"ff",
		"kn":"nn",
		"pf":"ff",
		"k":"c",
		"sch":"sss"
	}

	for table_entry in table.keys():
		table_value = table[table_entry]	# get table value
		table_value_len = len(table_value)	# calculate its length
		first_chars = term[0:table_value_len]
		if (first_chars == table_entry):
			term = table_value + term[table_value_len:]
			break
		# end if
	# end for

	# build translation table for the last characters
	table = {
		"ee":"y",
		"ie":"y",
		"dt":"d",
		"rt":"d",
		"rd":"d",
		"nt":"d",
		"nd":"d",
	}

	for table_entry in table.keys():
		table_value = table[table_entry]	# get table value
		table_entry_len = len(table_entry)	# calculate its length
		last_chars = term[(0 - table_entry_len):]
		#print last_chars, ", ", table_entry, ", ", table_value
		if (last_chars == table_entry):
			term = term[:(0 - table_value_len + 1)] + table_value
			break
		# end if
	# end for

	# initialize code
	code = term

	# transform ev->af
	code = re.sub(r'ev', r'af', code)

	# transform a,e,i,o,u->a
	code = re.sub(r'[aeiouy]', r'a', code)
	
	# transform q->g
	code = re.sub(r'q', r'g', code)
	
	# transform z->s
	code = re.sub(r'z', r's', code)

	# transform m->n
	code = re.sub(r'm', r'n', code)

	# transform kn->n
	code = re.sub(r'kn', r'n', code)

	# transform k->c
	code = re.sub(r'k', r'c', code)

	# transform sch->sss
	code = re.sub(r'sch', r'sss', code)

	# transform ph->ff
	code = re.sub(r'ph', r'ff', code)

	# transform h-> if previous or next is nonvowel -> previous
	occur = re.findall(r'([a-z]{0,1}?)h([a-z]{0,1}?)', code)
	#print occur
	for occur_group in occur:
		occur_item_previous = occur_group[0]
		occur_item_next = occur_group[1]

		if ((re.match(r'[^aeiouy]', occur_item_previous)) or (re.match(r'[^aeiouy]', occur_item_next))):
			if (occur_item_previous != ""):
				# make substitution
				code = re.sub (occur_item_previous + "h", occur_item_previous * 2, code, 1)
			# end if
		# end if
	# end for
	
	# transform w-> if previous is vowel -> previous
	occur = re.findall(r'([aeiouy]{1}?)w', code)
	#print occur
	for occur_group in occur:
		occur_item_previous = occur_group[0]
		# make substitution
		code = re.sub (occur_item_previous + "w", occur_item_previous * 2, code, 1)
	# end for
	
	# check last character
	# -s, remove
	code = re.sub (r's$', r'', code)
	# -ay, replace by -y
	code = re.sub (r'ay$', r'y', code)
	# -a, remove
	code = re.sub (r'a$', r'', code)
	
	# return nysiis code
	return code

def caverphone (term):
	"returns the language key using the caverphone algorithm 2.0"

	# Developed at the University of Otago, New Zealand.
	# Project: Caversham Project (http://caversham.otago.ac.nz)
	# Developer: David Hood, University of Otago, New Zealand
	# Contact: caversham@otago.ac.nz
	# Project Technical Paper: http://caversham.otago.ac.nz/files/working/ctp150804.pdf
	# Version 2.0 (2004-08-15)

	code = ""

	i = 0
	term_length = len(term)

	if (term_length == 0):
		# empty string ?
		return code
	# end if

	# convert to lowercase
	code = string.lower(term)

	# remove anything not in the standard alphabet (a-z)
	code = re.sub(r'[^a-z]', '', code)

	# remove final e
	if code.endswith("e"):
		code = code[:-1]

	# if the name starts with cough, rough, tough, enough or trough -> cou2f (rou2f, tou2f, enou2f, trough)
	code = re.sub(r'^([crt]|(en)|(tr))ough', r'\1ou2f', code)

	# if the name starts with gn -> 2n
	code = re.sub(r'^gn', r'2n', code)

	# if the name ends with mb -> m2
	code = re.sub(r'mb$', r'm2', code)

	# replace cq -> 2q
	code = re.sub(r'cq', r'2q', code)
	
	# replace c[i,e,y] -> s[i,e,y]
	code = re.sub(r'c([iey])', r's\1', code)
	
	# replace tch -> 2ch
	code = re.sub(r'tch', r'2ch', code)
	
	# replace c,q,x -> k
	code = re.sub(r'[cqx]', r'k', code)
	
	# replace v -> f
	code = re.sub(r'v', r'f', code)
	
	# replace dg -> 2g
	code = re.sub(r'dg', r'2g', code)
	
	# replace ti[o,a] -> si[o,a]
	code = re.sub(r'ti([oa])', r'si\1', code)
	
	# replace d -> t
	code = re.sub(r'd', r't', code)
	
	# replace ph -> fh
	code = re.sub(r'ph', r'fh', code)

	# replace b -> p
	code = re.sub(r'b', r'p', code)
	
	# replace sh -> s2
	code = re.sub(r'sh', r's2', code)
	
	# replace z -> s
	code = re.sub(r'z', r's', code)

	# replace initial vowel [aeiou] -> A
	code = re.sub(r'^[aeiou]', r'A', code)

	# replace all other vowels [aeiou] -> 3
	code = re.sub(r'[aeiou]', r'3', code)

	# replace j -> y
	code = re.sub(r'j', r'y', code)

	# replace an initial y3 -> Y3
	code = re.sub(r'^y3', r'Y3', code)
	
	# replace an initial y -> A
	code = re.sub(r'^y', r'A', code)

	# replace y -> 3
	code = re.sub(r'y', r'3', code)
	
	# replace 3gh3 -> 3kh3
	code = re.sub(r'3gh3', r'3kh3', code)
	
	# replace gh -> 22
	code = re.sub(r'gh', r'22', code)

	# replace g -> k
	code = re.sub(r'g', r'k', code)

	# replace groups of s,t,p,k,f,m,n by its single, upper-case equivalent
	for single_letter in ["s", "t", "p", "k", "f", "m", "n"]:
		otherParts = re.split(single_letter + "+", code)
		code = string.join(otherParts, string.upper(single_letter))
	
	# replace w[3,h3] by W[3,h3]
	code = re.sub(r'w(h?3)', r'W\1', code)

	# replace final w with 3
	code = re.sub(r'w$', r'3', code)

	# replace w -> 2
	code = re.sub(r'w', r'2', code)

	# replace h at the beginning with an A
	code = re.sub(r'^h', r'A', code)

	# replace all other occurrences of h with a 2
	code = re.sub(r'h', r'2', code)

	# replace r3 with R3
	code = re.sub(r'r3', r'R3', code)

	# replace final r -> 3
	code = re.sub(r'r$', r'3', code)

	# replace r with 2
	code = re.sub(r'r', r'2', code)

	# replace l3 with L3
	code = re.sub(r'l3', r'L3', code)
	
	# replace final l -> 3
	code = re.sub(r'l$', r'3', code)
	
	# replace l with 2
	code = re.sub(r'l', r'2', code)

	# remove all 2's
	code = re.sub(r'2', r'', code)

	# replace the final 3 -> A
	code = re.sub(r'3$', r'A', code)
	
	# remove all 3's
	code = re.sub(r'3', r'', code)

	# extend the code by 10 '1' (one)
	code += '1' * 10
	
	# take the first 10 characters
	caverphoneCode = code[:10]
	
	# return caverphone code
	return caverphoneCode


########NEW FILE########
__FILENAME__ = readers
from nltk.corpus.reader import TaggedCorpusReader

def numbered_sent_block_reader(stream):
	line = stream.readline()
	
	if not line:
		return []
	
	n, sent = line.split(' ', 1)
	return [sent]

class NumberedTaggedSentCorpusReader(TaggedCorpusReader):
	def __init__(self, *args, **kwargs):
		super(NumberedTaggedSentCorpusReader, self).__init__(
			para_block_reader=numbered_sent_block_reader, *args, **kwargs)
	
	def paras(self):
		raise NotImplementedError('use sents()')
	
	def tagged_paras(self):
		raise NotImplementedError('use tagged_sents()')
########NEW FILE########
__FILENAME__ = taggers
from nltk.tag.sequential import SequentialBackoffTagger
from nltk.probability import FreqDist
from nltk.tag import ClassifierBasedPOSTagger, TaggerI, str2tuple
from nltk_trainer import iteritems
from nltk_trainer.featx import phonetics
from nltk_trainer.featx.metaphone import dm

class PhoneticClassifierBasedPOSTagger(ClassifierBasedPOSTagger):
	def __init__(self, double_metaphone=False, metaphone=False, soundex=False, nysiis=False, caverphone=False, *args, **kwargs):
		self.funs = {}
		
		if double_metaphone:
			self.funs['double-metaphone'] = lambda s: dm(unicode(s))
		
		if metaphone:
			self.funs['metaphone'] = phonetics.metaphone
		
		if soundex:
			self.funs['soundex'] = phonetics.soundex
		
		if nysiis:
			self.funs['nysiis'] = phonetics.nysiis
		
		if caverphone:
			self.funs['caverphone'] = phonetics.caverphone
		# for some reason don't get self.funs if this is done first, but works if done last
		ClassifierBasedPOSTagger.__init__(self, *args, **kwargs)
	
	def feature_detector(self, tokens, index, history):
		feats = ClassifierBasedPOSTagger.feature_detector(self, tokens, index, history)
		s = tokens[index]
		
		for key, fun in iteritems(self.funs):
			feats[key] = fun(s)
		
		return feats

class MaxVoteBackoffTagger(SequentialBackoffTagger):
	def __init__(self, *taggers):
		self._taggers = taggers
	
	def choose_tag(self, tokens, index, history):
		tags = FreqDist()
		
		for tagger in self._taggers:
			tags.inc(tagger.choose_tag(tokens, index, history))
		
		return tags.max()

class PatternTagger(TaggerI):
	def tag(self, tokens):
		# don't import at top since don't want to fail if not installed
		from pattern.en import tag
		# not tokenizing ensures that the number of tagged tokens returned is
		# the same as the number of input tokens
		return tag(u' '.join(tokens), tokenize=False)
########NEW FILE########
__FILENAME__ = training
from nltk.tag import brill

def train_brill_tagger(initial_tagger, train_sents, end, trace=0, **kwargs):
	bounds = [(1, end)]
	
	templates = [
		brill.SymmetricProximateTokensTemplate(brill.ProximateTagsRule, *bounds),
		brill.SymmetricProximateTokensTemplate(brill.ProximateWordsRule, *bounds),
	]
	
	trainer = brill.FastBrillTaggerTrainer(initial_tagger, templates,
		deterministic=True, trace=trace)
	return trainer.train(train_sents, **kwargs)
########NEW FILE########
__FILENAME__ = chunked
from nltk.tag.util import tuple2str
from nltk_trainer.writer import CorpusWriter

class ChunkedCorpusWriter(CorpusWriter):
	def chunked_sent_string(self, sent):
		parts = []
		
		for word, tag in sent:
			try:
				brack = word in u'[]'
			except:
				brack = False
			
			if brack:
				# brackets don't get a tag
				parts.append(word)
			else:
				# make sure no brackets or slashes in tag
				tag = tag.replace(u'[', u'(').replace(u']', u')').replace(u'/', '|')
				parts.append(tuple2str((word, tag)))
		
		return ' '.join(parts)
	
	def write_sents(self, sents, *args, **kwargs):
		first = True
		
		for sent in sents:
			if not first:
				self.write(' ', *args, **kwargs)
			else:
				first = False
			
			self.write(self.chunked_sent_string(sent), *args, **kwargs)
	
	def write_paras(self, paras, *args, **kwargs):
		first = True
		
		for para in paras:
			if not first:
				self.write('\n\n', *args, **kwargs)
			else:
				first = False
			
			self.write_sents(para, *args, **kwargs)
########NEW FILE########
__FILENAME__ = classified

class ClassifiedCorpusWriter(CorpusWriter):
	def __init__(self, path, labels):
		self.path = path
		self.labels = labels
	# TODO: make sure works with with keyword
	def __enter__(self):
		self._files = dict([(l, self.open(os.path.join(path, l), 'a')) for l in labels])
	
	def __exit__(self):
		for f in self._files.values():
			f.close()
	
	def write(self, text, label):
		self._files[label].write(text + u'\n\n')
########NEW FILE########
__FILENAME__ = tag_phrases
#!/usr/bin/env python
import argparse, os.path
import cPickle as pickle
import nltk.data, nltk.tag
from nltk_trainer import load_corpus_reader
from nltk_trainer.writer.chunked import ChunkedCorpusWriter

########################################
## command options & argument parsing ##
########################################

# TODO: many of the args are shared with analyze_classifier_coverage, so abstract

parser = argparse.ArgumentParser(description='Classify a plaintext corpus to a classified corpus')
# TODO: make sure source_corpus can be a single file
parser.add_argument('source_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('target_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')
parser.add_argument('--tagger', default=nltk.tag._POS_TAGGER,
	help='''pickled tagger filename/path relative to an nltk_data directory
default is NLTK's default tagger''')

# TODO: from analyze_tagged_corpus.py
corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader',
	default='nltk.corpus.reader.plaintext.PlaintextCorpusReader',
	help='Full module path to a corpus reader class, defaults to %(default)s.')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')
corpus_group.add_argument('--sent-tokenizer', default='tokenizers/punkt/english.pickle',
	help='Path to pickled sentence tokenizer')
corpus_group.add_argument('--word-tokenizer', default='nltk.tokenize.WordPunctTokenizer',
	help='Full module path to a tokenizer class, defaults to %(default)s.')

args = parser.parse_args()

###################
## corpus reader ##
###################

source_corpus = load_corpus_reader(args.source_corpus, reader=args.reader,
	fileids=args.fileids, encoding='utf-8', sent_tokenizer=args.sent_tokenizer,
	word_tokenizer=args.word_tokenizer)

if not source_corpus:
	raise ValueError('%s is an unknown corpus')

if args.trace:
	print 'loaded %s' % args.source_corpus

############
## tagger ##
############

# TODO: from analyze_tagger_coverage.py
if args.trace:
	print 'loading tagger %s' % args.tagger

try:
	tagger = nltk.data.load(args.tagger)
except LookupError:
	try:
		import cPickle as pickle
	except ImportError:
		import pickle
	
	tagger = pickle.load(open(os.path.expanduser(args.tagger)))

#############
## tagging ##
#############

with ChunkedCorpusWriter(fileids=source_corpus.fileids(), path=args.target_corpus) as writer:
	for fileid in source_corpus.fileids():
		paras = source_corpus.paras(fileids=[fileid])
		tagged_paras = ((tagger.tag(sent) for sent in para) for para in paras)
		writer.write_paras(tagged_paras, fileid=fileid)
########NEW FILE########
__FILENAME__ = train_chunker
#!/usr/bin/env python
import argparse, math, itertools, os.path
import nltk.tag, nltk.chunk, nltk.chunk.util
import nltk_trainer.classification.args
from nltk.corpus.reader import IEERCorpusReader
from nltk_trainer import dump_object, load_corpus_reader, simplify_wsj_tag
from nltk_trainer.chunking import chunkers, transforms

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Train a NLTK Classifier',
	formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('corpus',
	help='''The name of a chunked corpus included with NLTK, such as treebank_chunk or
conll2000, or the root path to a corpus directory, which can be either an
absolute path or relative to a nltk_data directory.''')
parser.add_argument('--filename',
	help='''filename/path for where to store the pickled tagger.
The default is {corpus}_{algorithm}.pickle in ~/nltk_data/chunkers''')
parser.add_argument('--no-pickle', action='store_true', default=False,
	help="Don't pickle and save the tagger")
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to %(default)d. 0 is no trace output.')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader', default=None,
	help='''Full module path to a corpus reader class, such as
nltk.corpus.reader.chunked.ChunkedCorpusReader''')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')
corpus_group.add_argument('--fraction', default=1.0, type=float,
	help='Fraction of corpus to use for training, defaults to %(default)f')
corpus_group.add_argument('--flatten-deep-tree', action='store_true', default=False,
	help='''Flatten deep trees from parsed_sents() instead of chunked_sents().
Cannot be combined with --shallow-tree.''')
corpus_group.add_argument('--shallow-tree', action='store_true', default=False,
	help='''Use shallow trees from parsed_sents() instead of chunked_sents().
Cannot be combined with --flatten-deep-tree.''')

if simplify_wsj_tag:
	corpus_group.add_argument('--simplify_tags', action='store_true', default=False,
		help='Use simplified tags')

chunker_group = parser.add_argument_group('Chunker Options')
chunker_group.add_argument('--sequential', default='ub',
	help='''Sequential Backoff Algorithm for a Tagger based Chunker.
This can be any combination of the following letters:
	u: UnigramTagger
	b: BigramTagger
	t: TrigramTagger
The default is "%(default)s". If you specify a classifier, this option will be ignored.''')
chunker_group.add_argument('--classifier', nargs='*',
	choices=nltk_trainer.classification.args.classifier_choices,
	help='''ClassifierChunker algorithm to use instead of a sequential Tagger based Chunker.
Maxent uses the default Maxent training algorithm, either CG or iis.''')

nltk_trainer.classification.args.add_maxent_args(parser)
nltk_trainer.classification.args.add_decision_tree_args(parser)

eval_group = parser.add_argument_group('Chunker Evaluation',
	'Evaluation metrics for chunkers')
eval_group.add_argument('--no-eval', action='store_true', default=False,
	help="don't do any evaluation")

args = parser.parse_args()

###################
## corpus reader ##
###################

if args.trace:
	print('loading %s' % args.corpus)

chunked_corpus = load_corpus_reader(args.corpus, reader=args.reader, fileids=args.fileids)
chunked_corpus.fileids()
fileids = args.fileids
kwargs = {}
	
if fileids and fileids in chunked_corpus.fileids():
	kwargs['fileids'] = [fileids]

	if args.trace:
		print('using chunked sentences from %s' % fileids)

if simplify_wsj_tag and args.simplify_tags:
	kwargs['simplify_tags'] = True

if isinstance(chunked_corpus, IEERCorpusReader):
	chunk_trees = []
	
	if args.trace:
		print('converting ieer parsed docs to chunked sentences')
	
	for doc in chunked_corpus.parsed_docs(**kwargs):
		tagged = chunkers.ieertree2conlltags(doc.text)
		chunk_trees.append(nltk.chunk.util.conlltags2tree(tagged))
elif args.flatten_deep_tree and args.shallow_tree:
	raise ValueError('only one of --flatten-deep-tree or --shallow-tree can be used')
elif (args.flatten_deep_tree or args.shallow_tree) and not hasattr(chunked_corpus, 'parsed_sents'):
	raise ValueError('%s does not have parsed sents' % args.corpus)
elif args.flatten_deep_tree:
	if args.trace:
		print('flattening deep trees from %s' % args.corpus)
	
	chunk_trees = []
	
	for i, tree in enumerate(chunked_corpus.parsed_sents(**kwargs)):
		try:
			chunk_trees.append(transforms.flatten_deeptree(tree))
		except AttributeError as exc:
			if args.trace > 1:
				print('skipping bad tree %d: %s' % (i, exc))
elif args.shallow_tree:
	if args.trace:
		print('creating shallow trees from %s' % args.corpus)
	
	chunk_trees = []
	
	for i, tree in enumerate(chunked_corpus.parsed_sents(**kwargs)):
		try:
			chunk_trees.append(transforms.shallow_tree(tree))
		except AttributeError as exc:
			if args.trace > 1:
				print('skipping bad tree %d: %s' % (i, exc))
elif not hasattr(chunked_corpus, 'chunked_sents'):
	raise ValueError('%s does not have chunked sents' % args.corpus)
else:
	chunk_trees = chunked_corpus.chunked_sents(**kwargs)

##################
## train chunks ##
##################

nchunks = len(chunk_trees)

if args.fraction == 1.0:
	train_chunks = test_chunks = chunk_trees
else:
	cutoff = int(math.ceil(nchunks * args.fraction))
	train_chunks = chunk_trees[:cutoff]
	test_chunks = chunk_trees[cutoff:]

if args.trace:
	print('%d chunks, training on %d' % (nchunks, len(train_chunks)))

##########################
## tagger based chunker ##
##########################

sequential_classes = {
	'u': nltk.tag.UnigramTagger,
	'b': nltk.tag.BigramTagger,
	't': nltk.tag.TrigramTagger
}

if args.sequential and not args.classifier:
	tagger_classes = []
	
	for c in args.sequential:
		if c not in sequential_classes:
			raise NotImplementedError('%s is not a valid tagger' % c)
		
		tagger_classes.append(sequential_classes[c])
	
	if args.trace:
		print('training %s TagChunker' % args.sequential)
	
	chunker = chunkers.TagChunker(train_chunks, tagger_classes)

##############################
## classifier based chunker ##
##############################

if args.classifier:
	if args.trace:
		print('training ClassifierChunker with %s classifier' % args.classifier)
	# TODO: feature extraction options
	chunker = chunkers.ClassifierChunker(train_chunks, verbose=args.trace,
		classifier_builder=nltk_trainer.classification.args.make_classifier_builder(args))

################
## evaluation ##
################

if not args.no_eval:
	if args.trace:
		print('evaluating %s' % chunker.__class__.__name__)
	
	print(chunker.evaluate(test_chunks))

##############
## pickling ##
##############

if not args.no_pickle:
	if args.filename:
		fname = os.path.expanduser(args.filename)
	else:
		# use the last part of the corpus name/path as the prefix
		parts = [os.path.split(args.corpus.rstrip('/'))[-1]]
		
		if args.classifier:
			parts.append('_'.join(args.classifier))
		elif args.sequential:
			parts.append(args.sequential)
		
		name = '%s.pickle' % '_'.join(parts)
		fname = os.path.join(os.path.expanduser('~/nltk_data/chunkers'), name)
	
	dump_object(chunker, fname, trace=args.trace)
########NEW FILE########
__FILENAME__ = train_classifier
#!/usr/bin/env python
import argparse, collections, functools, itertools, math, operator, os.path, re, string, sys
import nltk.data
import nltk_trainer.classification.args
from nltk.classify import DecisionTreeClassifier, MaxentClassifier, NaiveBayesClassifier
from nltk.classify.util import accuracy
from nltk.corpus import stopwords
from nltk.corpus.reader import CategorizedPlaintextCorpusReader, CategorizedTaggedCorpusReader
from nltk.corpus.util import LazyCorpusLoader
from nltk.metrics import BigramAssocMeasures, f_measure, masi_distance, precision, recall
from nltk.probability import FreqDist, ConditionalFreqDist
from nltk.util import ngrams
from nltk_trainer import dump_object, import_attr, iteritems, load_corpus_reader
from nltk_trainer.classification import corpus, scoring
from nltk_trainer.classification.featx import (bag_of_words, bag_of_words_in_set,
	word_counts, train_test_feats, word_counts_in_set)
from nltk_trainer.classification.multi import MultiBinaryClassifier

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Train a NLTK Classifier')

parser.add_argument('corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('--filename', help='''filename/path for where to store the
	pickled classifier, the default is {corpus}_{algorithm}.pickle in
	~/nltk_data/classifiers''')
parser.add_argument('--no-pickle', action='store_true', default=False,
	help="don't pickle and save the classifier")
parser.add_argument('--classifier', '--algorithm', default=['NaiveBayes'], nargs='+',
	choices=nltk_trainer.classification.args.classifier_choices,
	help='''Classifier algorithm to use, defaults to %(default)s. Maxent uses the
	default Maxent training algorithm, either CG or iis.''')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')
parser.add_argument('--show-most-informative', default=0, type=int,
	help='number of most informative features to show, works for all algorithms except DecisionTree')

corpus_group = parser.add_argument_group('Training Corpus')
corpus_group.add_argument('--reader',
	default='nltk.corpus.reader.CategorizedPlaintextCorpusReader',
	help='Full module path to a corpus reader class, such as %(default)s')
corpus_group.add_argument('--cat_pattern', default='(.+)/.+',
	help='''A regular expression pattern to identify categories based on file paths.
	If cat_file is also given, this pattern is used to identify corpus file ids.
	The default is '(.+)/+', which uses sub-directories as categories.''')
corpus_group.add_argument('--cat_file',
	help='relative path to a file containing category listings')
corpus_group.add_argument('--delimiter', default=' ',
	help='category delimiter for category file, defaults to space')
corpus_group.add_argument('--instances', default='files',
	choices=('sents', 'paras', 'files'),
	help='''the group of words that represents a single training instance,
	the default is to use entire files''')
corpus_group.add_argument('--fraction', default=1.0, type=float,
	help='''The fraction of the corpus to use for training a binary or
	multi-class classifier, the rest will be used for evaulation.
	The default is to use the entire corpus, and to test the classifier
	against the same training data. Any number < 1 will test against
	the remaining fraction.''')
corpus_group.add_argument('--train-prefix', default=None,
	help='optional training fileid prefix for multi classifiers')
corpus_group.add_argument('--test-prefix', default=None,
	help='optional testing fileid prefix for multi classifiers')
corpus_group.add_argument('--word-tokenizer', default='', help='Word Tokenizer class path')
corpus_group.add_argument('--sent-tokenizer', default='', help='Sent Tokenizer data.pickle path')
corpus_group.add_argument('--para-block-reader', default='', help='Block reader function path')
corpus_group.add_argument('--labels', default=[],
	help='''If given a list of labels, default categories by corpus are omitted''')

classifier_group = parser.add_argument_group('Classifier Type',
	'''A binary classifier has only 2 labels, and is the default classifier type.
	A multi-class classifier chooses one of many possible labels.
	A multi-binary classifier choose zero or more labels by combining multiple
	binary classifiers, 1 for each label.''')
classifier_group.add_argument('--binary', action='store_true', default=False,
	help='train a binary classifier, or a multi-binary classifier if --multi is also given')
classifier_group.add_argument('--multi', action='store_true', default=False,
	help='train a multi-class classifier, or a multi-binary classifier if --binary is also given')

feat_group = parser.add_argument_group('Feature Extraction',
	'The default is to lowercase every word, strip punctuation, and use stopwords')
feat_group.add_argument('--ngrams', nargs='+', type=int,
	help='use n-grams as features.')
feat_group.add_argument('--no-lowercase', action='store_true', default=False,
	help="don't lowercase every word")
feat_group.add_argument('--filter-stopwords', default='no',
	choices=['no']+stopwords.fileids(),
	help='language stopwords to filter, defaults to "no" to keep stopwords')
feat_group.add_argument('--punctuation', action='store_true', default=False,
	help="don't strip punctuation")
feat_group.add_argument('--value-type', default='bool', choices=('bool', 'int', 'float'),
	help='''Data type of values in featuresets. The default is bool, which ignores word counts.
	Use int to get word and/or ngram counts.''')

score_group = parser.add_argument_group('Feature Scoring',
	'The default is no scoring, all words are included as features')
score_group.add_argument('--score_fn', default='chi_sq',
	choices=[f for f in dir(BigramAssocMeasures) if not f.startswith('_')],
	help='scoring function for information gain and bigram collocations, defaults to chi_sq')
score_group.add_argument('--min_score', default=0, type=int,
	help='minimum score for a word to be included, default is 0 to include all words')
score_group.add_argument('--max_feats', default=0, type=int,
	help='maximum number of words to include, ordered by highest score, defaults is 0 to include all words')

eval_group = parser.add_argument_group('Classifier Evaluation',
	'''The default is to test the classifier against the unused fraction of the
	corpus, or against the entire corpus if the whole corpus is used for training.''')
eval_group.add_argument('--no-eval', action='store_true', default=False,
	help="don't do any evaluation")
eval_group.add_argument('--no-accuracy', action='store_true', default=False,
	help="don't evaluate accuracy")
eval_group.add_argument('--no-precision', action='store_true', default=False,
	help="don't evaluate precision")
eval_group.add_argument('--no-recall', action='store_true', default=False,
	help="don't evaluate recall")
eval_group.add_argument('--no-fmeasure', action='store_true', default=False,
	help="don't evaluate f-measure")
eval_group.add_argument('--no-masi-distance', action='store_true', default=False,
	help="don't evaluate masi distance (only applies to a multi binary classifier)")
eval_group.add_argument('--cross-fold', type=int, default=0,
	help='''If given a number greater than 2, will do cross fold validation
	instead of normal training and testing. This option implies --no-pickle,
	is useless with --trace 0 and/or --no-eval, and currently does not work
	with --multi --binary.
	''')

nltk_trainer.classification.args.add_maxent_args(parser)
nltk_trainer.classification.args.add_decision_tree_args(parser)
nltk_trainer.classification.args.add_sklearn_args(parser)

args = parser.parse_args()

###################
## corpus reader ##
###################

reader_args = []
reader_kwargs = {}

if args.cat_file:
	reader_kwargs['cat_file'] = args.cat_file
	
	if args.delimiter and args.delimiter != ' ':
		reader_kwargs['delimiter'] = args.delimiter
	
	if args.cat_pattern:
		reader_args.append(args.cat_pattern)
	else:
		reader_args.append('.+/.+')
elif args.cat_pattern:
	reader_args.append(args.cat_pattern)
	reader_kwargs['cat_pattern'] = re.compile(args.cat_pattern)

if args.word_tokenizer:
	reader_kwargs['word_tokenizer'] = import_attr(args.word_tokenizer)()

if args.sent_tokenizer:
	reader_kwargs['sent_tokenizer'] = nltk.data.LazyLoader(args.sent_tokenizer)

if args.para_block_reader:
	reader_kwargs['para_block_reader'] = import_attr(args.para_block_reader)

if args.trace:
	print('loading %s' % args.corpus)

categorized_corpus = load_corpus_reader(args.corpus, args.reader,
	*reader_args, **reader_kwargs)

if not hasattr(categorized_corpus, 'categories'):
	raise ValueError('%s is does not have categories for classification')

if len(args.labels) > 0:
	labels = args.labels.split(",")
else:
	labels = categorized_corpus.categories()
nlabels = len(labels)

if args.trace:
	print('%d labels: %s' % (nlabels, labels))

if not nlabels:
	raise ValueError('corpus does not have any categories')
elif nlabels == 1:
	raise ValueError('corpus must have more than 1 category')
elif nlabels == 2 and args.multi:
	raise ValueError('corpus must have more than 2 categories if --multi is specified')

########################
## text normalization ##
########################

if args.filter_stopwords == 'no':
	stopset = set()
else:
	stopset = set(stopwords.words(args.filter_stopwords))

def norm_words(words):
	if not args.no_lowercase:
		words = (w.lower() for w in words)
	
	if not args.punctuation:
		words = (w.strip(string.punctuation) for w in words)
		words = (w for w in words if w)
	
	if stopset:
		words = (w for w in words if w.lower() not in stopset)
	
	# in case we modified words in a generator, ensure it's a list so we can add together
	if not isinstance(words, list):
		words = list(words)
	
	if args.ngrams:
		return functools.reduce(operator.add, [words if n == 1 else list(ngrams(words, n)) for n in args.ngrams])
	else:
		return words


#####################
## text extraction ##
#####################
if args.multi and args.binary:
	label_instance_function = {
		'sents': corpus.multi_category_sent_words,
		'paras': corpus.multi_category_para_words,
		'files': corpus.multi_category_file_words
	}
	
	lif = label_instance_function[args.instances]
	train_instances = lif(categorized_corpus, args.train_prefix)
	test_instances = lif(categorized_corpus, args.test_prefix)

	# if we need all the words by category for score_fn, use this method
	def category_words():
		'''
		return an iteration of tuples of category and list of all words in instances of that category.
		Used if we are scoring the words for correlation to categories for feature selection (i.e.,
		score_fn and max_feats are set)
		'''
		cat_words = defaultdict([])
		for (words, cats) in train_instances:
			if isinstance(cats, collections.Iterable):
				for cat in cats:
					cat_words[cat].extend(words)
			else:
				cat_words[cats].extend(words)
		return iteritems(cat_words)

else:
	def split_list(lis, fraction):
		'''split a list into 2 lists based on the fraction provided. Used to break the instances into 
		   train and test sets'''
		if fraction != 1.0:
			l = len(lis)
			cutoff = int(math.ceil(l * fraction))
			return lis[0:cutoff], lis[cutoff:]
		else:
			return lis, []

	label_instance_function = {
		'sents': corpus.category_sent_words,
		'paras': corpus.category_para_words,
		'files': corpus.category_file_words
	}
	
	lif = label_instance_function[args.instances]
	train_instances = {}
	test_instances = {}
	
	for label in labels:
		instances = (norm_words(i) for i in lif(categorized_corpus, label))
		instances = [i for i in instances if i]
		train_instances[label], test_instances[label] = split_list(instances, args.fraction)
		if args.trace > 1:
			info = (label, len(train_instances[label]), len(test_instances[label]))
			print('%s: %d training instances, %d testing instances' % info)
	# if we need all the words by category for score_fn, use this method
	def category_words():
		'''
		return an iteration of tuples of category and list of all words in instances of that category.
		Used if we are scoring the words for correlation to categories for feature selection (i.e.,
		score_fn and max_feats are set)
		'''
		return ((cat, (word for i in instance_list for word in i)) for cat, instance_list in iteritems(train_instances))					

##################
## word scoring ##
##################

score_fn = getattr(BigramAssocMeasures, args.score_fn)

if args.min_score or args.max_feats:
	if args.trace:
		print('calculating word scores')
	
	# flatten the list of instances to a single iteration of all the words 
	cat_words = category_words()
	ws = scoring.sorted_word_scores(scoring.sum_category_word_scores(cat_words, score_fn))
	
	if args.min_score:
		ws = [(w, s) for (w, s) in ws if s >= args.min_score]
	
	if args.max_feats:
		ws = ws[:args.max_feats]
	
	bestwords = set([w for (w, s) in ws])
	
	if args.value_type == 'bool':
		if args.trace:
			print('using bag of words from known set feature extraction')
		
		featx = lambda words: bag_of_words_in_set(words, bestwords)
	else:
		if args.trace:
			print('using word counts from known set feature extraction')
		
		featx = lambda words: word_counts_in_set(words, bestwords)
	
	if args.trace:
		print('%d words meet min_score and/or max_feats' % len(bestwords))
elif args.value_type == 'bool':
	if args.trace:
		print('using bag of words feature extraction')
	
	featx = bag_of_words
else:
	if args.trace:
		print('using word counts feature extraction')
	
	featx = word_counts

		
#########################
## extracting features ##
#########################
def extract_features(label_instances, featx):
	if isinstance(label_instances, dict):
		# for not (args.multi and args.binary)
        # e.g., li = { 'spam': [ ['hello','world',...], ... ], 'ham': [ ['lorem','ipsum'...], ... ] }
		feats = []
		for label, instances in iteritems(label_instances):
			feats.extend([(featx(i), label) for i in instances])
	else:
		# for arg.multi and args.binary
		# e.g., li = [ (['hello','world',...],label1), (['lorem','ipsum'],label2) ]
		feats = [(featx(i), label) for i, label in label_instances ]
	return feats

	
train_feats = extract_features(train_instances, featx)
test_feats = extract_features(test_instances, featx)
# if there were no instances reserved for testing, test over the whole training set
if not test_feats:
	test_feats = train_feats

if args.trace:
       print('%d training feats, %d testing feats' % (len(train_feats), len(test_feats)))

##############
## training ##
##############
trainf = nltk_trainer.classification.args.make_classifier_builder(args)

if args.cross_fold:
	if args.multi and args.binary:
		raise NotImplementedError ("cross-fold is not supported for multi-binary classifiers")
	scoring.cross_fold(train_feats, trainf, accuracy, folds=args.cross_fold,
		trace=args.trace, metrics=not args.no_eval, informative=args.show_most_informative)
	sys.exit(0)

if args.multi and args.binary:
	if args.trace:
		print('training multi-binary %s classifier' % args.classifier)
	classifier = MultiBinaryClassifier.train(labels, train_feats, trainf)
else:
	classifier = trainf(train_feats)

################
## evaluation ##
################
if not args.no_eval:
	if not args.no_accuracy:
		try:
			print('accuracy: %f' % accuracy(classifier, test_feats))
		except ZeroDivisionError:
			print('accuracy: 0')

	if args.multi and args.binary and not args.no_masi_distance:
		print('average masi distance: %f' % (scoring.avg_masi_distance(classifier, test_feats)))
	
	if not args.no_precision or not args.no_recall or not args.no_fmeasure:
		if args.multi and args.binary:
			refsets, testsets = scoring.multi_ref_test_sets(classifier, test_feats)
		else:
			refsets, testsets = scoring.ref_test_sets(classifier, test_feats)
		
		for label in labels:
			ref = refsets[label]
			test = testsets[label]
			
			if not args.no_precision:
				print('%s precision: %f' % (label, precision(ref, test) or 0))
			
			if not args.no_recall:
				print('%s recall: %f' % (label, recall(ref, test) or 0))
			
			if not args.no_fmeasure:
				print('%s f-measure: %f' % (label, f_measure(ref, test) or 0))

if args.show_most_informative and hasattr(classifier, 'show_most_informative_features') and not (args.multi and args.binary) and not args.cross_fold:
	print('%d most informative features' % args.show_most_informative)
	classifier.show_most_informative_features(args.show_most_informative)

##############
## pickling ##
##############
if not args.no_pickle:
	if args.filename:
		fname = os.path.expanduser(args.filename)
	else:
		name = '%s_%s.pickle' % (args.corpus, '_'.join(args.classifier))
		fname = os.path.join(os.path.expanduser('~/nltk_data/classifiers'), name)
	
	dump_object(classifier, fname, trace=args.trace)

########NEW FILE########
__FILENAME__ = train_tagger
#!/usr/bin/env python
import argparse, math, itertools, os.path
import nltk.corpus, nltk.data
import nltk_trainer.classification.args
from nltk.classify import DecisionTreeClassifier, MaxentClassifier, NaiveBayesClassifier
# special case corpus readers
from nltk.corpus.reader import SwitchboardCorpusReader, NPSChatCorpusReader, IndianCorpusReader
from nltk.corpus.util import LazyCorpusLoader
from nltk.tag import ClassifierBasedPOSTagger
from nltk_trainer import dump_object, load_corpus_reader, simplify_wsj_tag
from nltk_trainer.tagging import readers
from nltk_trainer.tagging.training import train_brill_tagger
from nltk_trainer.tagging.taggers import PhoneticClassifierBasedPOSTagger

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Train a NLTK Classifier',
	formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('corpus',
	help='''The name of a tagged corpus included with NLTK, such as treebank,
brown, cess_esp, floresta, or the root path to a corpus directory,
which can be either an absolute path or relative to a nltk_data directory.''')
parser.add_argument('--filename',
	help='''filename/path for where to store the pickled tagger.
The default is {corpus}_{algorithm}.pickle in ~/nltk_data/taggers''')
parser.add_argument('--no-pickle', action='store_true', default=False,
	help="Don't pickle and save the tagger")
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to %(default)d. 0 is no trace output.')

corpus_group = parser.add_argument_group('Corpus Reader Options')
corpus_group.add_argument('--reader', default=None,
	help='''Full module path to a corpus reader class, such as
nltk.corpus.reader.tagged.TaggedCorpusReader''')
corpus_group.add_argument('--fileids', default=None,
	help='Specify fileids to load from corpus')
corpus_group.add_argument('--fraction', default=1.0, type=float,
	help='Fraction of corpus to use for training, defaults to %(default)f')

tagger_group = parser.add_argument_group('Tagger Choices')
tagger_group.add_argument('--default', default='-None-',
	help='''The default tag "%(default)s". Set this to a different tag, such as "NN",
to change the default tag.''')
tagger_group.add_argument('--backoff', default=None,
	help='Path to pickled backoff tagger. If given, replaces default tagger.')

if simplify_wsj_tag:
	tagger_group.add_argument('--simplify_tags', action='store_true', default=False,
		help='Use simplified tags')
else:
	tagger_group.add_argument('--tagset', default=None,
		help='Map tags to a given tagset, such as "universal"')

sequential_group = parser.add_argument_group('Sequential Tagger')
sequential_group.add_argument('--sequential', default='aubt',
	help='''Sequential Backoff Algorithm. This can be any combination of the following letters:
	a: AffixTagger
	u: UnigramTagger
	b: BigramTagger
	t: TrigramTagger
The default is "%(default)s", but you can set this to the empty string
to not train a sequential backoff tagger.''')
sequential_group.add_argument('-a', '--affix', action='append', type=int,
	help='''Add affixes to use for one or more AffixTaggers.
Negative numbers are suffixes, positive numbers are prefixes.
You can use this option multiple times to create multiple AffixTaggers with different affixes.
The affixes will be used in the order given.''')

brill_group = parser.add_argument_group('Brill Tagger Options')
brill_group.add_argument('--brill', action='store_true', default=False,
	help='Train a Brill Tagger in front of the other tagger.')
brill_group.add_argument('--template_bounds', type=int, default=1,
	help='''Choose the max bounds for Brill Templates to train a Brill Tagger.
The default is %(default)d.''')
brill_group.add_argument('--max_rules', type=int, default=200)
brill_group.add_argument('--min_score', type=int, default=2)

classifier_group = parser.add_argument_group('Classifier Based Tagger')
classifier_group.add_argument('--classifier', nargs='*',
	choices=nltk_trainer.classification.args.classifier_choices,
	help='''ClassifierBasedPOSTagger algorithm to use, default is %(default)s.
Maxent uses the default Maxent training algorithm, either CG or iis.''')
classifier_group.add_argument('--cutoff_prob', default=0, type=float,
	help='Cutoff probability for classifier tagger to backoff to previous tagger')

phonetic_group = parser.add_argument_group('Phonetic Feature Options for a Classifier Based Tagger')
phonetic_group.add_argument('--metaphone', action='store_true',
	default=False, help='Use metaphone feature')
phonetic_group.add_argument('--double-metaphone', action='store_true',
	default=False, help='Use double metaphone feature')
phonetic_group.add_argument('--soundex', action='store_true',
	default=False, help='Use soundex feature')
phonetic_group.add_argument('--nysiis', action='store_true',
	default=False, help='Use NYSIIS feature')
phonetic_group.add_argument('--caverphone', action='store_true',
	default=False, help='Use caverphone feature')

nltk_trainer.classification.args.add_maxent_args(parser)
nltk_trainer.classification.args.add_decision_tree_args(parser)

eval_group = parser.add_argument_group('Tagger Evaluation',
	'Evaluation metrics for part-of-speech taggers')
eval_group.add_argument('--no-eval', action='store_true', default=False,
	help="don't do any evaluation")
# TODO: word coverage of test words, how many get a tag != '-NONE-'

args = parser.parse_args()

###################
## corpus reader ##
###################

if args.trace:
	print('loading %s' % args.corpus)

tagged_corpus = load_corpus_reader(args.corpus, reader=args.reader, fileids=args.fileids)
fileids = args.fileids
kwargs = {}

# all other corpora are assumed to support simplify_tags kwarg
if simplify_wsj_tag and args.simplify_tags and args.corpus not in ['conll2000', 'switchboard', 'pl196x']:
	kwargs['simplify_tags'] = True
# these corpora do not support simplify_tags, and have no known workaround
elif simplify_wsj_tag and args.simplify_tags and args.corpus in ['pl196x']:
	raise ValueError('%s does not support simplify_tags' % args.corpus)
elif not simplify_wsj_tag and args.tagset:
	kwargs['tagset'] = args.tagset
	
	if args.trace:
		print('using %s tagset' % args.tagset)

if isinstance(tagged_corpus, SwitchboardCorpusReader):
	if fileids:
		raise ValueError('fileids cannot be used with switchboard')
	
	tagged_sents = list(itertools.chain(*[[list(s) for s in d if s] for d in tagged_corpus.tagged_discourses(**kwargs)]))
elif isinstance(tagged_corpus, NPSChatCorpusReader):
	tagged_sents = tagged_corpus.tagged_posts(**kwargs)
else:
	if isinstance(tagged_corpus, IndianCorpusReader) and not fileids:
		fileids = 'hindi.pos'
	
	if fileids and fileids in tagged_corpus.fileids():
		kwargs['fileids'] = [fileids]
	
		if args.trace:
			print('using tagged sentences from %s' % fileids)
	
	tagged_sents = tagged_corpus.tagged_sents(**kwargs)

# manual simplification is needed for these corpora
if simplify_wsj_tag and args.simplify_tags and args.corpus in ['conll2000', 'switchboard']:
	tagged_sents = [[(word, simplify_wsj_tag(tag)) for (word, tag) in sent] for sent in tagged_sents]

##################
## tagged sents ##
##################

# can't trust corpus to provide valid list of sents (indian)
tagged_sents = [sent for sent in tagged_sents if sent]
nsents = len(tagged_sents)

if args.fraction == 1.0:
	train_sents = test_sents = tagged_sents
else:
	cutoff = int(math.ceil(nsents * args.fraction))
	train_sents = tagged_sents[:cutoff]
	test_sents = tagged_sents[cutoff:]

if args.trace:
	print('%d tagged sents, training on %d' % (nsents, len(train_sents)))

####################
## default tagger ##
####################

if args.backoff:
	if args.trace:
		print('loading backoff tagger %s' % args.backoff)
	
	tagger = nltk.data.load(args.backoff)
else:
	tagger = nltk.tag.DefaultTagger(args.default)

################################
## sequential backoff taggers ##
################################

# NOTE: passing in verbose=args.trace doesn't produce useful printouts

def affix_constructor(train_sents, backoff=None):
	affixes = args.affix or [-3]
	
	for affix in affixes:
		if args.trace:
			print('training AffixTagger with affix %d and backoff %s' % (affix, backoff))
		
		backoff = nltk.tag.AffixTagger(train_sents, affix_length=affix,
			min_stem_length=min(affix, 2), backoff=backoff)
	
	return backoff

def ngram_constructor(cls):
	def f(train_sents, backoff=None):
		if args.trace:
			print('training %s tagger with backoff %s' % (cls, backoff))
		# TODO: args.cutoff option
		return cls(train_sents, backoff=backoff)
	
	return f

sequential_constructors = {
	'a': affix_constructor,
	'u': ngram_constructor(nltk.tag.UnigramTagger),
	'b': ngram_constructor(nltk.tag.BigramTagger),
	't': ngram_constructor(nltk.tag.TrigramTagger)
}

if args.sequential:
	for c in args.sequential:
		if c not in sequential_constructors:
			raise NotImplementedError('%s is not a valid sequential backoff tagger' % c)
		
		constructor = sequential_constructors[c]
		tagger = constructor(train_sents, backoff=tagger)

#######################
## classifier tagger ##
#######################

if args.classifier:
	kwargs = {
		'train': train_sents,
		'verbose': args.trace,
		'backoff': tagger,
		'cutoff_prob': args.cutoff_prob,
		'classifier_builder': nltk_trainer.classification.args.make_classifier_builder(args)
	}
	
	phonetic_keys = ['metaphone', 'double_metaphone', 'soundex', 'nysiis', 'caverphone']
	
	if any([getattr(args, key) for key in phonetic_keys]):
		cls = PhoneticClassifierBasedPOSTagger
		
		for key in phonetic_keys:
			kwargs[key] = getattr(args, key)
	else:
		cls = ClassifierBasedPOSTagger
	
	if args.trace:
		print('training %s %s' % (args.classifier, cls.__name__))
	
	tagger = cls(**kwargs)

##################
## brill tagger ##
##################

if args.brill:
	tagger = train_brill_tagger(tagger, train_sents, args.template_bounds,
		trace=args.trace, max_rules=args.max_rules, min_score=args.min_score)

################
## evaluation ##
################

if not args.no_eval:
	print('evaluating %s' % tagger.__class__.__name__)
	print('accuracy: %f' % tagger.evaluate(test_sents))

##############
## pickling ##
##############

if not args.no_pickle:
	if args.filename:
		fname = os.path.expanduser(args.filename)
	else:
		# use the last part of the corpus name/path as the prefix
		parts = [os.path.split(args.corpus.rstrip('/'))[-1]]
		
		if args.brill:
			parts.append('brill')
		
		if args.classifier:
			parts.append('_'.join(args.classifier))
		
		if args.sequential:
			parts.append(args.sequential)
		
		name = '%s.pickle' % '_'.join(parts)
		fname = os.path.join(os.path.expanduser('~/nltk_data/taggers'), name)
	
	dump_object(tagger, fname, trace=args.trace)
########NEW FILE########
__FILENAME__ = translate_corpus
#!/usr/bin/env python
import argparse, os, os.path
import nltk.data
from nltk.misc import babelfish
from nltk_trainer import import_attr, load_corpus_reader, join_words, translate

langs = [l.lower() for l in babelfish.available_languages]

########################################
## command options & argument parsing ##
########################################

parser = argparse.ArgumentParser(description='Translate a corpus')

parser.add_argument('source_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('target_corpus', help='corpus name/path relative to an nltk_data directory')
parser.add_argument('-s', '--source', default='english', choices=langs, help='source language')
parser.add_argument('-t', '--target', choices=langs, help='target language')
parser.add_argument('--trace', default=1, type=int,
	help='How much trace output you want, defaults to 1. 0 is no trace output.')
parser.add_argument('--retries', default=3, type=int,
	help='Number of babelfish retries before quiting')
parser.add_argument('--sleep', default=3, type=int,
	help='Sleep time between retries')

# TODO: these are all shared with train_classifier.py and probably others, so abstract
corpus_group = parser.add_argument_group('Input Corpus')
corpus_group.add_argument('--reader',
	default='nltk.corpus.reader.PlaintextCorpusReader',
	help='Full module path to a corpus reader class, such as %(default)s')
corpus_group.add_argument('--word-tokenizer', default='', help='Word Tokenizer class path')
corpus_group.add_argument('--sent-tokenizer', default='', help='Sent Tokenizer data.pickle path')
corpus_group.add_argument('--para-block-reader', default='', help='Block reader function path')

args = parser.parse_args()

###################
## corpus reader ##
###################

reader_args = []
reader_kwargs = {}

if args.word_tokenizer:
	reader_kwargs['word_tokenizer'] = import_attr(args.word_tokenizer)()

if args.sent_tokenizer:
	reader_kwargs['sent_tokenizer'] = nltk.data.LazyLoader(args.sent_tokenizer)

if args.para_block_reader:
	reader_kwargs['para_block_reader'] = import_attr(args.para_block_reader)

if args.trace:
	print 'loading %s' % args.source_corpus

input_corpus = load_corpus_reader(args.source_corpus, args.reader,
	*reader_args, **reader_kwargs)

#################
## translation ##
#################

for fileid in input_corpus.fileids():
	# TODO: use ~/nltk_data/corpora as dir prefix?
	path = os.path.join(args.target_corpus, fileid)
	dirname = os.path.dirname(path)
	
	if not os.path.exists(dirname):
		if args.trace:
			print 'making directory %s' % dirname
		
		os.makedirs(dirname)
	
	with open(path, 'w') as outf:
		if args.trace:
			print 'translating file %s to %s' % (fileid, path)
		
		for para in input_corpus.paras(fileids=[fileid]):
			for sent in para:
				# TODO: use intelligent joining (with punctuation)
				text = join_words(sent)
				if not text: continue
				trans = translate(text, args.source, args.corpus, trace=args.trace,
					sleep=args.sleep, retries=args.retries)
				if not trans: continue
				
				if args.trace > 1:
					print text, '-->>', trans
				
				outf.write(trans + ' ')
			
			outf.write('\n\n')
########NEW FILE########
