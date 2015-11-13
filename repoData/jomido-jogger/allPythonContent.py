__FILENAME__ = catalogue

from jogger import Jogger as _Jogger, jog as json_log

from functools import partial
from collections import OrderedDict
import re


def regex_parser(regex, field_map, chunks):

	dictionaries = []

	fields = OrderedDict(field_map)

	for chunk in chunks:

		result = re.match(regex, chunk.strip())

		if result:

			r = result.groups()
			d = {}

			for i, (k, v) in enumerate(fields.items()):

				try:
					value = r[i]
				except IndexError:
					value = None

				d[k] = v(value)

			extra_fields = r[len(field_map):]
			for i, field in enumerate(extra_fields):
				d['field_{}'.format(len(field_map) + i)] = extra_fields[i]

			dictionaries.append(d)

		else:

			dictionaries.append({
				'unparsed': chunk
			})

	return dictionaries


def common_jog():

	"""
	Common Log Format
	"""

	def static_reader():

		return """

			127.0.0.1 abc frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 404 82

			asdasd
			127.0.0.1 abc susie [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326
			127.0.0.2 ghi frank [12/Oct/2000:13:55:36 -0700] "GET /apache_pb.jpg HTTP/1.0" 200 1326

		"""

	import datetime

	regex = '([(\d\.)]+) (.*) (.*) \[(.*?)\] "(.*?)" (\d+) (\d+)'
	strptime = datetime.datetime.strptime
	value = lambda x: x
	int_value = lambda x: int(x)
	date_value = lambda x: strptime(x.split(' ')[0], '%d/%b/%Y:%H:%M:%S')

	field_map = [
		('address', 	  value),
		('identifier', 	  value),
		('userid', 		  value),
		('timestamp', 	  date_value),
		('request', 	  value),
		('response_code', int_value),
		('response_size', int_value)
	]

	parser = partial(regex_parser, regex, field_map)

	class Log(object):

		address = identifier = userid = request = 'UNPARSED'
		response_code = -1
		# response_size = -1
		timestamp = datetime.datetime(year=datetime.MINYEAR, month=1, day=1)

	def tests():

		test_log = _Jogger(reader=static_reader, parser=parser, log=Log).jog()

		assert len(test_log) == 4
		assert len(test_log(lambda line: line.unparsed)) == 1

		line = test_log[0]
		assert line.address == "127.0.0.1"
		assert line.identifier == 'abc'
		assert line.userid == 'frank'
		assert line.timestamp == datetime.datetime(2000, 10, 10, 13, 55, 36)
		assert line.request == "GET /apache_pb.gif HTTP/1.0"
		assert line.response_code == 404
		assert line.response_size == 82

	return (_Jogger(parser=parser, log=Log).jog, tests)


common_jog, _common_jog_tests = common_jog()


def combined_jog():

	"""
	Combined Log Format
	"""

	def static_reader():

		return """

			123.65.150.10 - - [23/Aug/2010:03:50:59 +0000] "POST /wordpress3/wp-admin/admin-ajax.php HTTP/1.1" 200 2 "http://www.example.com/wordpress3/wp-admin/post-new.php" "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.3 (KHTML, like Gecko) Chrome/6.0.472.25 Safari/534.3"

			asdasd
			123.65.150.10 - - [23/Aug/2010:03:50:59 +0000] "POST /wordpress3/wp-admin/admin-ajax.php HTTP/1.1" 200 2 "http://www.example.com/wordpress3/wp-admin/post-new.php" "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.3 (KHTML, like Gecko) Chrome/6.0.472.25 Safari/534.3"
			123.65.150.10 - - [23/Aug/2010:03:50:59 +0000] "POST /wordpress3/wp-admin/admin-ajax.php HTTP/1.1" 200 2 "http://www.example.com/wordpress3/wp-admin/post-new.php" "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.3 (KHTML, like Gecko) Chrome/6.0.472.25 Safari/534.3"

		"""

	import datetime

	regex = '([(\d\.)]+) (.*) (.*) \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)"'
	strptime = datetime.datetime.strptime
	value = lambda x: x
	int_value = lambda x: int(x)
	date_value = lambda x: strptime(x.split(' ')[0], '%d/%b/%Y:%H:%M:%S')

	field_map = [
		('address', 	  value),
		('identifier', 	  value),
		('userid', 		  value),
		('timestamp', 	  date_value),
		('request', 	  value),
		('response_code', int_value),
		('response_size', int_value),
		('referer', 	  value),
		('user_agent', 	  value),
	]

	parser = partial(regex_parser, regex, field_map)

	class Log(object):

		address = identifier = userid = request = referer = user_agent = 'UNPARSED'
		response_code = -1
		response_size = -1
		timestamp = datetime.datetime(year=datetime.MINYEAR, month=1, day=1)

	def tests():

		test_log = _Jogger(reader=static_reader, parser=parser, log=Log).jog()

		assert len(test_log) == 4
		assert len(test_log(lambda line: line.unparsed)) == 1

		line = test_log[0]
		assert line.address == "123.65.150.10"
		assert line.identifier == '-'
		assert line.userid == '-'
		assert line.timestamp == datetime.datetime(2010, 8, 23, 3, 50, 59)
		assert line.request == "POST /wordpress3/wp-admin/admin-ajax.php HTTP/1.1"
		assert line.response_code == 200
		assert line.response_size == 2
		assert line.referer == "http://www.example.com/wordpress3/wp-admin/post-new.php"
		assert line.user_agent == "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.3 (KHTML, like Gecko) Chrome/6.0.472.25 Safari/534.3"

	return (_Jogger(parser=parser, log=Log).jog, tests)


combined_jog, _combined_jog_tests = combined_jog()


def _tests():

	_common_jog_tests()
	_combined_jog_tests()


if __name__ == "__main__":

	_tests()


########NEW FILE########
__FILENAME__ = jogger
import collections
import json
import re
import types
from collections import defaultdict
from functools import partial


try:

    unicode = unicode

except NameError:

    unicode = str
    basestring = (str, bytes)


def reader(file_name):
    """
    Get a blob of data from somewhere
    """

    with open(file_name, 'r') as f:
        return f.read()


def chunker(blob):
    """
    Chunk a blob of data into an iterable of smaller chunks
    """

    return [chunk for chunk in blob.split('\n') if chunk.strip()]


def parser(chunks):
    """
    Parse a data chunk into a dictionary; catch failures and return suitable
    defaults
    """

    dictionaries = []
    for chunk in chunks:
        try:
            dictionaries.append(json.loads(chunk))
        except ValueError:
            dictionaries.append({
                'unparsed': chunk
            })

    return dictionaries


def buncher(line_class, dictionaries):
    """
    Turn an iterable of dictionaries into an iterable of Python objects that
    represent log lines.
    """

    return [line_class(dictionary) for dictionary in dictionaries]


def inspector(objects):

    api = {
        'attributes': set(),
        'scalars': set(),
        'vectors': set(),
        'defaults': {}
    }

    attributes = defaultdict(set)
    for line in objects:
        for attribute in dir(line):
            if not attribute.startswith('_') and not callable(
                    getattr(line, attribute)
            ):
                kind = type(getattr(line, attribute))
                if kind in (unicode, basestring, bytes) or issubclass(
                        kind, basestring):
                    kind = str
                attributes[attribute].add(kind)

    api['attributes'] = set(attributes.keys())

    for attribute in attributes.keys():
        kinds = set(attributes[attribute])

        if len(kinds) == 1:

            kind = kinds.pop()
            try:
                api['defaults'][attribute] = kind()
            except:
                api['defaults'][attribute] = NoValue

            if not issubclass(kind, collections.Iterable) or kind in (
                    str, unicode, basestring, bytes):
                api['scalars'].add(attribute)
            else:
                api['vectors'].add(attribute)
        else:
            # this is a heterogenous attribute! hmm....
            api['defaults'][attribute] = NoValue

            has_scalars = False
            has_vectors = False

            for kind in kinds:

                if not issubclass(kind, collections.Iterable) or kind in (
                        str, unicode, basestring, bytes):
                    has_scalars = True
                else:
                    has_vectors = True

            if has_scalars:
                api['scalars'].add(attribute)
            else:
                api['vectors'].add(attribute)

    return api


def patcher(APIMixin, LogKlass, api):
    """
    Merge the api mixin class with a user Log class and patch in an api; also
    set defaults
    """

    class Log(APIMixin, LogKlass):

        def __init__(self, lines, *args, **kwargs):

            APIMixin.__init__(self, lines, *args, **kwargs)
            LogKlass.__init__(self, lines, *args, **kwargs)

            for a in dir(LogKlass):
                if not a.startswith('_') and not callable(getattr(LogKlass, a)):
                    api['attributes'].add(a)
                    default_value = getattr(LogKlass, a)
                    api['defaults'][a] = default_value
                    kind = type(default_value)
                    if kind in (unicode, basestring, bytes) or issubclass(
                            kind, basestring):
                        kind = str
                    if not issubclass(kind, collections.Iterable) or kind in (
                            str, unicode, basestring):
                        api['scalars'].add(a)
                    else:
                        api['vectors'].add(a)

            self.attributes = sorted(api['attributes'])

            for scalar in api['scalars']:

                value = partial(
                    lambda self, scalar, *args, **kwargs: self._scalar(
                        scalar, *args, **kwargs), self, scalar)
                setattr(self, scalar, value)

                value.any = value

                value.all = partial(
                    lambda self, scalar, *args: self._scalar(
                        scalar, *args, mode='all'), self, scalar)

                value.none = partial(
                    lambda self, scalar, *args: self._scalar(
                        scalar, *args, mode='none'), self, scalar)

                value.only = partial(
                    lambda self, vector, *args: self._scalar(
                        scalar, *args, mode='only'), self, scalar)

            for vector in api['vectors']:

                value = partial(
                    lambda self, vector, *args, **kwargs: self._vector(
                        vector, *args, **kwargs), self, vector)
                setattr(self, vector, value)

                value.any = value

                value.all = partial(
                    lambda self, vector, *args: self._vector(
                        vector, *args, mode='all'), self, vector)

                value.none = partial(
                    lambda self, vector, *args: self._vector(
                        vector, *args, mode='none'), self, vector)

                value.only = partial(
                    lambda self, vector, *args: self._vector(
                        vector, *args, mode='only'), self, vector)

            for line in self:
                for attribute, default in api['defaults'].items():
                    if not hasattr(line, attribute):
                        try:
                            klass_default = getattr(LogKlass, attribute)
                            setattr(line, attribute, klass_default)
                        except:
                            setattr(line, attribute, default)

    return Log


class MetaNoValue(type):

    def __bool__(cls):
        return False

    def __nonzero__(cls):
        return False

    def __getattr__(cls, attr):
        return cls


class NoValue(object):
    __metaclass__ = MetaNoValue


class Line(object):

    """
    The default user-defined "bunch" class, for lines in a log
    """

    def __init__(self, dictionary):

        for k, v in dictionary.items():
            if isinstance(v, collections.Mapping):
                dictionary[k] = self.__class__(v)
        self.__dict__.update(dictionary)


class Log(object):

    """
    The default user-defined log class

    def __init__(self, lines, *args, **kwargs):
        pass

    """


PATTERN_TYPE = type(re.compile('a'))


class APIMixin(list):

    """
    The base API we're striving for on the Log instance goes here
    """

    def __init__(self, lines, *args, **kwargs):

        self.extend(lines)
        self._args = args
        self._kwargs = kwargs

    def _where(self, *comparators, **comparator):

        def by_schema(self, schema):

            log = self[:]
            to_remove = set()

            for line in log:

                if not isinstance(line, collections.Mapping):
                    try:
                        d = line.__dict__
                    except AttributeError:
                        continue
                else:
                    d = line

                for k, t in schema.items():

                    if k.startswith('~'):
                        notted = True
                        k = k[1:]
                    else:
                        notted = False

                    if k not in d:
                        to_remove.add(line)
                    else:

                        v = d[k]

                        if (isinstance(v, collections.Iterable) and
                                not isinstance(v, (str, unicode))):
                            method = self._vector_match
                        else:
                            method = self._scalar_match

                        if notted:
                            if method(v, t):
                                to_remove.add(line)
                        else:
                            if not method(v, t):
                                to_remove.add(line)

            for line in to_remove:
                log.remove(line)

            return log

        log = self.__class__(self)
        if comparator:
            comparators += (comparator,)

        for comparator in comparators:

            if isinstance(comparator, collections.Mapping):
                log = by_schema(log, comparator)
                continue

            if callable(comparator):
                log = self.__class__(
                    [line for line in log if comparator(line)])
                continue

            raise TypeError("Invalid comparator")

        return log

    def _vector(self, name, *selection, **kwargs):

        if not selection:
            vector = set()
            for line in self:
                [vector.add(t) for t in getattr(line, name)]

            return sorted(vector, key=self._get_sort_key)

        mode = kwargs.pop('mode', 'any')

        selection = set(selection)
        lines = []

        for line in self:
            passes = []
            value = getattr(line, name)
            for select in selection:

                # if self._vector_match(value, select):
                #     lines.append(line)

                if passes and mode == 'any' and any(passes):
                    break

                if self._vector_match(value, select):
                    passes.append(True)
                else:
                    passes.append(False)

            if passes and mode == 'any' and any(passes):
                lines.append(line)
            elif passes and mode == 'all' and all(passes):
                lines.append(line)
            elif mode == 'none' and (not passes or not any(passes)):
                lines.append(line)
            elif mode == 'only' and passes and all(passes) and len(passes) == len(value):
                lines.append(line)

        return self.__class__(set(lines))

    def _get_sort_key(self, obj):

        return str(obj)

    def _scalar(self, name, *selection, **kwargs):

        if not selection:
            return (
                sorted(set([getattr(line, name)
                       for line in self]), key=self._get_sort_key)
            )

        mode = kwargs.pop('mode', 'any')

        selection = set(selection)
        lines = []

        for line in self:
            passes = []
            value = getattr(line, name)
            for select in selection:

                # if self._scalar_match(value, select):
                #     lines.append(line)

                if passes and mode == 'any' and any(passes):
                    break

                if self._scalar_match(value, select):
                    passes.append(True)
                else:
                    passes.append(False)

            if passes and mode == 'any' and any(passes):
                lines.append(line)
            elif passes and mode == 'all' and all(passes):
                lines.append(line)
            elif mode == 'none' and (not passes or not any(passes)):
                lines.append(line)
            elif mode == 'only' and passes and all(passes) and len(passes) == len(value):
                lines.append(line)

        return self.__class__(set(lines))

    def _vector_match(self, value, select):

        invalid = (types.ClassType, types.TypeType, MetaNoValue)
        if type(select) not in invalid:
            if callable(select):
                if select(value):
                    return True
            else:
                for elem in value:
                    if self._scalar_match(elem, select):
                        return True
        else:
            if select in (str, unicode, basestring, bytes) or issubclass(
                    select, basestring):
                select = str
            if type(value) in (str, unicode, basestring, bytes) or issubclass(
                    type(value), basestring):
                value = str(value)
            if isinstance(value, select):
                return True

    def _scalar_match(self, value, select):

        if select == value:
            return True
        else:
            invalid = (types.ClassType, types.TypeType, MetaNoValue)
            if type(select) not in invalid:
                if isinstance(select, PATTERN_TYPE):
                    if select.match(value):
                        return True
                elif callable(select):
                    if select(value):
                        return True
            else:
                if select in (str, unicode, basestring, bytes) or issubclass(
                        select, basestring):
                    select = str
                if type(value) in (str, unicode, basestring, bytes) or issubclass(
                        type(value), basestring):
                    value = str(value)
                if isinstance(value, select):
                    return True

    def __call__(self, *comparators, **comparator):

        return self._where(*comparators, **comparator)

    def __getslice__(self, i, j):

        # this special method is gone in py 3.x; detect a slice object in
        # __getitem__ for py 3 instead (py 2.x code will still call this
        # special method)

        return self.__class__(
            list.__getslice__(self, i, j),
            *self._args,
            **self._kwargs
        )

    def __getitem__(self, item):

        if type(item) in (unicode, str, bytes) or issubclass(
                type(item), basestring):
            return getattr(self, item)

        if isinstance(item, slice):
            return self.__class__(
                list.__getitem__(self, item),
                *self._args,
                **self._kwargs
            )

        return list.__getitem__(self, item)

    def __setitem__(self, item, value):

        if type(item) in (unicode, str, bytes) or issubclass(
                type(item), basestring):
            setattr(self, item, value)
            return

        list.__setitem__(self, item, value)

    def __sub__(self, other):

        lines = [line for line in self if line not in other]
        return self.__class__(lines)

    def __isub__(self, other):

        lines = [line for line in self if line not in other]
        return self.__class__(lines)

    def __add__(self, other):

        return self.__class__(set(list(self) + list(other)))

    def __iadd__(self, other):

        return self.__class__(set(list(self) + list(other)))

    def __eq__(self, other):

        return set(map(hash, self)) == set(map(hash, other))

    def __repr__(self):

        return "<Log: {} lines>".format(len(self))


class PositionalLog(object):

    class OutOfBoundsError(Exception):
        pass

    def __init__(self, lines, *args, **kwargs):

        super(PositionalLog, self).__init__(lines, *args, **kwargs)
        self._position = 0

    def current(self):

        if self._position == len(self) or self._position == -1:
            raise PositionalLog.OutOfBoundsError

        return self[self._position]

    def next(self):

        self._position += 1
        if self._position > len(self):
            self._position = len(self)

        return self.current()

    def previous(self):

        self._position -= 1
        if self._position < -1:
            self._position = -1

        return self.current()

    def start(self):

        self._position = 0

        return self

    def end(self):

        self._position = len(self) - 1

        return self

    def position(self, position=None):

        if position:
            self._position = position
            return self

        return self._position


try:
    types.ClassType = types.ClassType
    types.TypeType = types.TypeType
except AttributeError:
    types.ClassType = type
    types.TypeType = type


class Jogger(object):

    def __init__(self, reader=reader, chunker=chunker, parser=parser,
                 buncher=buncher, inspector=inspector, patcher=patcher,
                 line=Line, log=Log, api=APIMixin):

        self.read = reader
        self.chunk = chunker
        self.parse = parser
        self.bunch = partial(buncher, line)
        self.inspect = inspector
        self.klass = log
        self.patch = partial(patcher, api, log)

    def jog(self, *args, **kwargs):
        """
        This method returns an instance of a patched-together Log class
        """

        blob = self.read(*args, **kwargs)
        chunks = self.chunk(blob) if self.chunk else blob
        dicts = self.parse(chunks) if self.parse else chunks
        objects = self.bunch(dicts) if self.bunch else dicts
        api = self.inspect(objects)
        klass = self.patch(api)
        log = klass(objects, *args, **kwargs)

        return log

"""
A default jogger implementation (a json-based one)
"""

jogger = Jogger()
jog = jogger.jog


if __name__ == "__main__":

    pass

########NEW FILE########
__FILENAME__ = tests

def static_json_reader():

    return (
    """
        {"line": "what?"}
        {"line": 0}
        bad line
        {"file": "foo.py"}

        {"msg": "Hello"}
        {"tags": ["greetings"]}
        {"tags": ["farewell-ings"]}
        {"tags": ["farewell-ings", "greetings"]}
        {"tags": ["farewell-ings", "greetings", "shazzam"]}
    """)


def test(reader, parser, Klass):

    from jogger import Jogger, NoValue

    jog = Jogger(reader=reader, parser=parser, log=Klass).jog
    log = jog()

    expected_length = 9
    expected_attrs = ['file', 'line', 'msg', 'tags', 'unparsed']
    expected_attrs_length = len(expected_attrs)

    assert len(log) == expected_length
    assert len(log.attributes) == expected_attrs_length
    assert log.attributes == expected_attrs

    for attr in expected_attrs:
        assert(attr in log.attributes)

    # return
    assert log.line() == [0, NoValue, 'what?']
    assert log.file() == ['', 'foo.py']
    assert log.msg() == ['Hello', None]
    assert log.unparsed() == ['', '        bad line']
    assert log.tags() == ['farewell-ings', 'greetings', 'shazzam']

    # value searching by attribute

    assert len(log.line(0)) == 1
    assert len(log.line(NoValue)) == expected_length - 2
    assert len(log.line('what?')) == 1
    assert len(log.line(NoValue, 'what?')) == expected_length - 1
    assert len(log.line(NoValue, 'what?', 0)) == expected_length

    assert len(log.file('foo.py')) == 1
    assert len(log.file('')) == expected_length - 1
    assert len(log.file('foo.py', '')) == expected_length

    assert len(log.msg('Hello')) == 1
    assert len(log.msg(None)) == expected_length - 1
    assert len(log.msg('Hello', None)) == expected_length

    assert len(log.tags('greetings')) == 3
    assert len(log.tags('farewell-ings')) == 3
    assert len(log.tags('farewell-ings').tags('greetings')) == 2

    assert len(log.unparsed('        bad line')) == 1
    assert len(log.unparsed('')) == expected_length - 1
    assert len(log.unparsed('        bad line', '')) == expected_length

    # type searching by attribute

    assert len(log.line(int)) == 1
    assert len(log.line(str)) == 1
    assert len(log.line(str, int)) == 2

    assert len(log.file(str)) == expected_length

    assert len(log.msg(str)) == 1

    assert len(log.tags(list)) == expected_length
    assert len(log.tags(str)) == 0

    assert len(log.unparsed(str)) == expected_length
    assert len(log.unparsed(int)) == 0

    # lambda searching by attribute

    assert len(log.line(lambda line: line == 0)) == 1

    assert len(log.tags(lambda tags: 'greetings' in tags)) == 3

    # mixed searching by attribute

    assert len(log.line(str, 0)) == 2
    assert len(log.line(
        str,
        0,
        lambda line: line == NoValue
    )) == expected_length

    # dictionary searching

    assert len(log({'line': 0})) == 1
    assert len(log({'line': int})) == 1
    assert len(log({'line': lambda line: line == 'what?'})) == 1
    assert len(log({
        'tags': 'greetings',
        'msg': None
    })) == 3
    assert len(log({'tags': 'greetings'})({'msg': None})) == 3

    # using all and any on an attribute

    tags = ['farewell-ings', 'greetings']
    assert len(log.tags.any(*tags)) == 4
    assert len(log.tags.all(*tags)) == 2
    assert len(log.tags.none(*tags)) == 5
    assert len(log.tags.only(*tags)) == 1

    # copying

    log2 = log()
    assert log2 == log

    # adding, subtracting, equality

    log2 = log.tags.any('greetings')
    log3 = log.tags.none('greetings')

    assert log2 != log3
    assert log2 != log
    assert log3 != log

    log4 = log2 + log3

    assert log4 == log

    # testing positional mixin

    assert log.current() == log[0]

    try:
        log.previous()
    except Exception as ex:
        assert isinstance(ex, Klass.OutOfBoundsError)

    log.end()
    assert log.current() == log[-1]

    log.start()
    assert log.current() == log[0]

    assert log.next() == log[1]

    assert log.end().previous() == log[-2]


def run_tests():

    from jogger import PositionalLog, parser

    class MyLog(PositionalLog):

        msg = None

    test(
        static_json_reader,
        parser,
        MyLog
    )

    from jogger.catalogue import _tests
    _tests()

if __name__ == "__main__":

    run_tests()


########NEW FILE########
