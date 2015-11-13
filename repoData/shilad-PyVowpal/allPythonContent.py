__FILENAME__ = test_examples
from vowpal import *

"""

Examples and test functions for py-vowpal

"""

# fake input data about running speed
DATA = [
    [0.4, {'body' : {'height' : 0.8, 'weight' : 0.3}, 'age' : {'age' : 0.4}, 'sports' : { 'football' : None }}],
    [0.7, {'body' : {'height' : 0.8, 'weight' : 0.3}, 'age' : {'age' : 0.3}, 'sports' : { 'soccer' : None }}],
    [0.2, {'body' : {'height' : 0.8, 'weight' : 0.5}, 'age' : {'age' : 0.7}, 'sports' : { 'soccer' : None }}],
    [0.7, {'body' : {'height' : 0.9, 'weight' : 0.3}, 'age' : {'age' : 0.2}, 'sports' : { 'track' : None }}],
    [0.9, {'body' : {'height' : 0.7, 'weight' : 0.3}, 'age' : {'age' : 0.3}, 'sports' : { 'track' : None }}],
    [0.6, {'body' : {'height' : 0.7, 'weight' : 0.7}, 'age' : {'age' : 0.2}, 'sports' : { 'track' : None }}],
    [None, {'body' : {'height' : 0.7, 'weight' : 0.2}, 'age' : {'age' : 0.3}, 'sports' : { 'track' : None }}],
    [None, {'body' : {'height' : 0.7, 'weight' : 0.2}, 'age' : {'age' : 0.3}, 'sports' : { 'soccer' : None }}],
]

PATH_VW = '/home/theja/local/vowpal_wabbit/vowpalwabbit/vw'

def test_predict_from_examples():
    """
        Predicting directly from VowpalExample objects.
        Easiest, but requires that the input data fit in memory.
    """
    examples = []
    for i in xrange(len(DATA)):
        (value, all_sections) = DATA[i]
        ex = VowpalExample(i, value)
        for (namespace, section) in all_sections.items():
            ex.add_section(namespace, section)
        examples.append(ex)
    train = examples[:-2]
    test = examples[-2:]
    vw = Vowpal(PATH_VW, './vw.%s', {'--passes' : '10' })
    preds = vw.predict_from_examples(train, test)
    for (id, value) in preds:
        print 'prediction for %s is %s' % (id, value)

def test_predict_from_example_stream():
    """
        Predicting from an ExampleStream.  An ExampleStream basically
        writes an input file for you from VowpalExample objects.
        All training examples (value != None) must appear before test examples.
    """
    stream = ExampleStream('vw.stream.txt')
    examples = []
    for i in xrange(len(DATA)):
        (value, all_sections) = DATA[i]
        ex = VowpalExample(i, value)
        for (namespace, section) in all_sections.items():
            ex.add_section(namespace, section)
        stream.add_example(ex)
    train = examples[:-2]
    test = examples[-2:]
    vw = Vowpal(PATH_VW, './vw.%s', {'--passes' : '10' })
    preds = vw.predict_from_example_stream(stream)
    for (id, value) in preds:
        print 'prediction for %s is %s' % (id, value)

def test_predict_from_file():
    """
        Predicting directly from a file. 
        All training examples (value != None) must appear before test examples.
    """
    f = open('vw.file.txt', 'w')
    examples = []
    for i in xrange(len(DATA)):
        (value, all_sections) = DATA[i]
        ex = VowpalExample(i, value)
        for (namespace, section) in all_sections.items():
            ex.add_section(namespace, section)
        f.write(str(ex) + '\n')
    f.close()
    vw = Vowpal(PATH_VW, './vw.%s', {'--passes' : '10' })
    preds = vw.predict_from_file('vw.file.txt')
    for (id, value) in preds:
        print 'prediction for %s is %s' % (id, value)

if __name__ == '__main__':
    test_predict_from_examples()
    test_predict_from_example_stream()
    test_predict_from_file()

########NEW FILE########
__FILENAME__ = vowpal
import os
import string
import subprocess
import collections


class VowpalExample:
    '''A single example that Vowpal predicts or learns.'''

    __slots__ = ('value', 'id', 'sections', 'SECTION_NAME_KEY')

    def __init__(self, id, value=None):
        self.SECTION_NAME_KEY = '__section_name__'
        self.value = value
        self.id = id
        self.sections = []     # list of dictionaries

    def add_section(self, name, section):
        '''
            Adds a new section of features for the example.
            Name is the namespace of the section.
            Section is a dictionary:
                Keys are feature names.
                Values are feature values or None for unary features.
            Namespaces are useful for creating interactions (see vowpal wiki).
        '''
        section[self.SECTION_NAME_KEY] = name
        self.sections.append(section)

    def __str__(self):
        '''Converts the example to Vowpal's input format.'''
        section_strs = []
        if self.value in (None, ''):
            section_strs.append('%s %s' % (1.0, self.id))
        else:
            section_strs.append('%s %s %s' % (self.value, 1.0, self.id))
        for s in self.sections:
            tokens = [s[self.SECTION_NAME_KEY]]
            for (key, value) in s.items():
                if key == self.SECTION_NAME_KEY:
                    pass
                elif value in (None, ''):
                    tokens.append(str(key))
                else:
                    tokens.append('%s:%s' % (key, value))
            section_strs.append(string.join(tokens))
        return string.join(section_strs, '|')


class ExampleStream:
    '''
        Input examples streamed to Vowpal.
        Examples with a value must appear before examples without.
    '''

    __slots__ = ('path', 'file', 'writing_train', 'n_test_examples', 'is_finalized')

    def __init__(self, path):
        self.path = path
        self.file = open(self.path, 'w')
        self.writing_train = True
        self.n_test_examples = 0
        self.is_finalized = False

    def add_example(self, example):
        '''Adds an example to the stream.'''
        if self.writing_train and example.value == None:
            self.writing_train = False
        elif self.writing_train:
            pass    # things are okay
        elif example.value != None:
            raise AttributeError('Examples with value must appear before examples without.')
        self.file.write(str(example)) 
        self.file.write('\n')
        if not self.writing_train:
            self.n_test_examples += 1

    def finalize(self):
        '''Closes the stream. Called by Vowpal.'''
        if not self.is_finalized:
            self.file.close()
            self.is_finalized = True


class Vowpal:
    '''Wrapper for Vowpal Wabbit machine learning classifier'''

    __slots__ = (
        'path_vw', 'path_models', 'path_cache', 'path_preds', 'path_data',
        'vowpal_args', 'n_test_examples'
    )

    def __init__(self, path_vw='vw', file_prefix='vw.%s', vowpal_args={}):
        self.path_vw = path_vw
        self.path_cache = file_prefix % 'cache'
        self.path_preds = file_prefix % 'preds'
        self.path_data = file_prefix % 'data'
        self.path_log = file_prefix % 'log'
        self.n_test_examples = -1
        self.vowpal_args = vowpal_args

        for p in [self.path_cache, self.path_preds, self.path_data, self.path_log]: 
                if os.path.isfile(p):
                        os.remove(p)

    def predict_from_examples(self, training_examples, testing_examples):
        '''
            Train on a list of VowpalExample train objects.
            Predict values for the VowpalExample test objects.
            All VowpalExample objects must fit in memory.
        '''
        for i in xrange(len(training_examples)):
            if training_examples[i].value == None:
                raise AttributeError('training example %s has no value' % i)
        for i in xrange(len(testing_examples)):
            if testing_examples[i].value != None:
                raise AttributeError( 'testing example %s has a value' % i)
        f = open(self.path_data, 'a')
        for example in training_examples:
                f.write(str(example) + '\n')
        for example in testing_examples:
                f.write(str(example) + '\n')
        f.close()
        self.n_test_examples = len(testing_examples)
        return self._predict()

    def predict_from_example_stream(self, example_stream):
        ''' Predict using examples recorded by an ExampleStream. '''
        example_stream.finalize()
        self.n_test_examples = example_stream.n_test_examples
        self.path_data = example_stream.path
        return self._predict()

    def predict_from_file(self, path_data):
        ''' Predict using examples recorded in a data file. '''
        self.path_data = path_data
        self.count_test_examples_in_input()
        return self._predict()

    def count_test_examples_in_input(self):
        ''' Count the number of test (unlabeled) examples in a file.'''
        in_train = True
        n_test = 0
        for line in open(self.path_data):
            i = line.find('|')
            if i < 0:
                raise Exception('no pipe found in input file.')
            header_length = len(string.split(line[:i]))
            if header_length == 3 and not in_train:
                raise Exception('all train examples must appear before test examples.')
            elif header_length == 3:
                pass    # do nothing
            elif header_length == 2:
                in_train = False
                n_test += 1
            else:
                raise Exception('invalid header in %s: %s' % (`path_data`, `line[:i]`))
        self.n_test_examples = n_test

    def _predict(self):
        ''' Predict values for the test examples in the input file.'''
        self.run_vowpal()
        return self.read_preds()

    def run_vowpal(self):
        ''' Execute the vowpal binary. '''
        # these can be overriden using the vowpal_args constructor parameter
        argd = {
            '--conjugate_gradient' : None,
            '--passes' : '100', 
            '--l2' : '.001',
            '--cache_file' : self.path_cache,
            '--predictions' : self.path_preds,
            '--data' : self.path_data
        }
        for (name, val) in self.vowpal_args.items():
            argd[name] = val
        argl = [self.path_vw]
        for (name, val) in argd.items():
            argl.append(str(name))
            if val != None:
                argl.append(str(val))
        log = open(self.path_log, 'w')
        p = subprocess.Popen(argl, stderr=subprocess.STDOUT, stdout=log)
        r = p.wait()
        log.close()
        if r != 0:
            raise Exception, ('Vowpal error occurred: check log file `%s`' % self.path_log)

    def read_preds(self):
        ''' Reads the Vowpal prediction results. '''
        preds = collections.deque()
        for line in open(self.path_preds):
            (pred, id) = line.split()
            preds.append([id, float(pred)])
            if len(preds) > self.n_test_examples:
                preds.popleft()
        return list(preds)

########NEW FILE########
