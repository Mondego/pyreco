__FILENAME__ = prefetch
from logging import getLogger
logger = getLogger(__name__)

import time
import collections

from django.db import models
from django.db.models import query
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor

class PrefetchManagerMixin(models.Manager):
    use_for_related_fields = True
    prefetch_definitions = {}

    @classmethod
    def get_queryset_class(cls):
        return PrefetchQuerySet

    def __init__(self):
        super(PrefetchManagerMixin, self).__init__()
        for name, prefetcher in self.prefetch_definitions.items():
            if prefetcher.__class__ is not Prefetcher and not callable(prefetcher):
                raise InvalidPrefetch("Invalid prefetch definition %s. This prefetcher needs to be a class not an instance." % name)

    def get_queryset(self):
        qs = self.get_queryset_class()(
            self.model, prefetch_definitions=self.prefetch_definitions
        )

        if getattr(self, '_db', None) is not None:
            qs = qs.using(self._db)
        return qs

    def get_query_set(self):
        """
        Django <1.6 compatibility method.
        """

        return self.get_queryset()

    def prefetch(self, *args):
        return self.get_queryset().prefetch(*args)


class PrefetchManager(PrefetchManagerMixin):
    def __init__(self, **kwargs):
        self.prefetch_definitions = kwargs
        super(PrefetchManager, self).__init__()

class InvalidPrefetch(Exception):
    pass

class PrefetchOption(object):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        self.args = args
        self.kwargs = kwargs

P = PrefetchOption

class PrefetchQuerySet(query.QuerySet):
    def __init__(self, model=None, query=None, using=None,
                 prefetch_definitions=None, **kwargs):
        if using is None: # this is to support Django 1.1
            super(PrefetchQuerySet, self).__init__(model, query, **kwargs)
        else:
            super(PrefetchQuerySet, self).__init__(model, query, using, **kwargs)
        self._prefetch = {}
        self.prefetch_definitions = prefetch_definitions

    def _clone(self, klass=None, setup=False, **kwargs):
        return super(PrefetchQuerySet, self). \
            _clone(klass, setup, _prefetch=self._prefetch,
                   prefetch_definitions=self.prefetch_definitions, **kwargs)

    def prefetch(self, *names):
        obj = self._clone()

        for opt in names:
            if isinstance(opt, PrefetchOption):
                name = opt.name
            else:
                name = opt
                opt = None
            parts = name.split('__')
            forwarders = []
            prefetcher = None
            model = self.model
            prefetch_definitions = self.prefetch_definitions

            for what in parts:
                if not prefetcher:
                    if what in prefetch_definitions:
                        prefetcher = prefetch_definitions[what]
                        continue
                    descriptor = getattr(model, what, None)
                    if isinstance(descriptor, ReverseSingleRelatedObjectDescriptor):
                        forwarders.append(descriptor.field.name)
                        model = descriptor.field.rel.to
                        manager = model.objects
                        if not isinstance(manager, PrefetchManager):
                            raise InvalidPrefetch('Manager for %s is not a PrefetchManager instance.' % model)
                        prefetch_definitions = manager.prefetch_definitions
                    else:
                        raise InvalidPrefetch("Invalid part %s in prefetch call for %s on model %s. The name is not a prefetcher nor a forward relation (fk)." % (what, name, self.model))
                else:
                    raise InvalidPrefetch("Invalid part %s in prefetch call for %s on model %s. You cannot have any more relations after the prefetcher." % (what, name, self.model))
            if not prefetcher:
                raise InvalidPrefetch("Invalid prefetch call with %s for on model %s. The last part isn't a prefetch definition." % (name, self.model))
            if opt:
                if prefetcher.__class__ is Prefetcher:
                    raise InvalidPrefetch("Invalid prefetch call with %s for on model %s. This prefetcher (%s) needs to be a subclass of Prefetcher." % (name, self.model, prefetcher))

                obj._prefetch[name] = forwarders, prefetcher(*opt.args, **opt.kwargs)
            else:
                obj._prefetch[name] = forwarders, prefetcher if prefetcher.__class__ is Prefetcher else prefetcher()


        for forwarders, prefetcher in obj._prefetch.values():
            if forwarders:
                obj = obj.select_related('__'.join(forwarders))
        return obj

    def iterator(self):
        data = list(super(PrefetchQuerySet, self).iterator())
        for name, (forwarders, prefetcher) in self._prefetch.items():
            prefetcher.fetch(data, name, self.model, forwarders,
                             getattr(self, '_db', None))
        return iter(data)

class Prefetcher(object):
    """
    Prefetch definitition. For convenience you can either subclass this and
    define the methods on the subclass or just pass the functions to the
    contructor.

    Eg, subclassing::

        class GroupPrefetcher(Prefetcher):

            @staticmethod
            def filter(ids):
                return User.groups.through.objects.filter(user__in=ids).select_related('group')

            @staticmethod
            def reverse_mapper(user_group_association):
                return [user_group_association.user_id]

            @staticmethod
            def decorator(user, user_group_associations=()):
                setattr(user, 'prefetched_groups', [i.group for i in user_group_associations])

    Or with contructor::

        Prefetcher(
            filter = lambda ids: User.groups.through.objects.filter(user__in=ids).select_related('group'),
            reverse_mapper = lambda user_group_association: [user_group_association.user_id],
            decorator = lambda user, user_group_associations=(): setattr(user, 'prefetched_groups', [i.group for i in user_group_associations])
        )


    Glossary:

    * filter(list_of_ids):

        A function that returns a queryset containing all the related data for a given list of keys.
        Takes a list of ids as argument.

    * reverse_mapper(related_object):

        A function that takes the related object as argument and returns a list
        of keys that maps that related object to the objects in the queryset.

    * mapper(object):

        Optional (defaults to ``lambda obj: obj.id``).

        A function that returns the key for a given object in your query set.

    * decorator(object, list_of_related_objects):

        A function that will save the related data on each of your objects in
        your queryset. Takes the object and a list of related objects as
        arguments. Note that you should not override existing attributes on the
        model instance here.

    """
    collect = False

    def __init__(self, filter=None, reverse_mapper=None, decorator=None, mapper=None, collect=None):
        if filter:
            self.filter = filter
        elif not hasattr(self, 'filter'):
            raise RuntimeError("You must define a filter function")

        if reverse_mapper:
            self.reverse_mapper = reverse_mapper
        elif not hasattr(self, 'reverse_mapper'):
            raise RuntimeError("You must define a reverse_mapper function")

        if decorator:
            self.decorator = decorator
        elif not hasattr(self, 'decorator'):
            raise RuntimeError("You must define a decorator function")

        if mapper:
            self.mapper = mapper

        if collect is not None:
            self.collect = collect

    @staticmethod
    def mapper(obj):
        return obj.id

    def fetch(self, dataset, name, model, forwarders, db):
        collect = self.collect or forwarders

        try:
            data_mapping = collections.defaultdict(list)
            t1 = time.time()
            for obj in dataset:
                for field in forwarders:
                    obj = getattr(obj, field, None)

                if not obj:
                    continue

                if collect:
                    data_mapping[self.mapper(obj)].append(obj)
                else:
                    data_mapping[self.mapper(obj)] = obj

                self.decorator(obj)

            t2 = time.time()
            logger.debug("Creating data_mapping for %s query took %.3f secs for the %s prefetcher.", model.__name__, t2-t1, name)
            t1 = time.time()
            related_data = self.filter(data_mapping.keys())
            if db is not None:
                related_data = related_data.using(db)
            related_data_len = len(related_data)
            t2 = time.time()
            logger.debug("Filtering for %s related objects for %s query took %.3f secs for the %s prefetcher.", related_data_len, model.__name__, t2-t1, name)
            relation_mapping = collections.defaultdict(list)

            t1 = time.time()
            for obj in related_data:
                for id_ in self.reverse_mapper(obj):
                    if id_:
                        relation_mapping[id_].append(obj)
            for id_, related_items in relation_mapping.items():
                if id_ in data_mapping:
                    if collect:
                        for item in data_mapping[id_]:
                            self.decorator(item, related_items)
                    else:
                        self.decorator(data_mapping[id_], related_items)

            t2 = time.time()
            logger.debug("Adding the related objects on the %s query took %.3f secs for the %s prefetcher.", model.__name__, t2-t1, name)
            return dataset
        except Exception:
            logger.exception("Prefetch failed for %s prefetch on the %s model:", name, model.__name__)
            raise

########NEW FILE########
__FILENAME__ = models
from django import VERSION
from django.db import models
from prefetch import PrefetchManager, Prefetcher

class SillyException(Exception):
    pass

class SillyPrefetcher(Prefetcher):
    def filter(ids):
        raise SillyException()
    def reverse_mapper(book):
        raise SillyException()
    def decorator(author, books=()):
        raise SillyException()

class LatestNBooks(Prefetcher):
    def __init__(self, count=2):
        self.count = count

    def filter(self, ids):
        return Book.objects.filter(author__in=ids)

    def reverse_mapper(self, book):
        return [book.author_id]

    def decorator(self, author, books=()):
        books = sorted(books, key=lambda book: book.created, reverse=True)
        setattr(author,
                'prefetched_latest_%s_books' % self.count,
                books[:self.count])

class LatestBook(Prefetcher):
    def filter(self, ids):
        return Book.objects.filter(author__in=ids)

    def reverse_mapper(self, book):
        return [book.author_id]

    def decorator(self, author, books=()):
        setattr(
            author,
            'prefetched_latest_book',
            max(books, key=lambda book: book.created) if books else None
        )

class Author(models.Model):
    name = models.CharField(max_length=100)

    objects = PrefetchManager(
        books = Prefetcher(
            filter = lambda ids: Book.objects.filter(author__in=ids),
            mapper = lambda author: author.id,
            reverse_mapper = lambda book: [book.author_id],
            decorator = lambda author, books=():
                setattr(author, 'prefetched_books', books)
        ),
        latest_n_books = LatestNBooks,
        latest_book_as_class = LatestBook,
        latest_book = Prefetcher(
            filter = lambda ids: Book.objects.filter(author__in=ids),
            reverse_mapper = lambda book: [book.author_id],
            decorator = lambda author, books=(): setattr(
                author,
                'prefetched_latest_book',
                max(books, key=lambda book: book.created) if books else None
            )
        ),
        silly = SillyPrefetcher,
    )

    @property
    def books(self):
        if hasattr(self, 'prefetched_books'):
            return self.prefetched_books
        else:
            return self.book_set.all()

    @property
    def latest_book(self):
        if hasattr(self, 'prefetched_latest_book'):
            return self.prefetched_latest_book
        else:
            try:
                return self.book_set.latest()
            except Book.DoesNotExist:
                return

class Tag(models.Model):
    name = models.CharField(max_length=100)

if VERSION < (1, 2):
    class Book_Tag(models.Model):
        book = models.ForeignKey("Book")
        tag = models.ForeignKey("Tag")

class Publisher(models.Model):
    name = models.CharField(max_length=100)

class Book(models.Model):
    class Meta:
        get_latest_by = 'created'

    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(Author)
    publisher = models.ForeignKey(Publisher, null=True)

    if VERSION < (1, 2):
        tags = models.ManyToManyField(Tag, through="Book_Tag")
    else:
        tags = models.ManyToManyField(Tag)

    objects = PrefetchManager(
        tags = Prefetcher(
            filter = lambda ids: (Book_Tag if VERSION < (1, 2) else Book.tags.through).objects.filter(book__in=ids),
            reverse_mapper = lambda book_tag: [book_tag.book_id],
            decorator = lambda user, book_tags=():
                setattr(user, 'prefetched_tags', [i.tag for i in book_tags])
        ),
        similar_books = Prefetcher(
            filter = lambda ids: Book.objects.filter(author__in=ids),
            mapper = lambda book: book.author_id,
            reverse_mapper = lambda book: [book.author_id],
            decorator = lambda book, books=():
                setattr(book.author, 'prefetched_books', books),
            collect = True,
        ),
        similar_books_missing_collect = Prefetcher(
            filter = lambda ids: Book.objects.filter(author__in=ids),
            mapper = lambda book: book.author_id,
            reverse_mapper = lambda book: [book.author_id],
            decorator = lambda book, books=():
                setattr(book.author, 'prefetched_books', books),
        ),
    )

    @property
    def similar_books(self):
        if hasattr(self.author, 'prefetched_books'):
            return [i for i in self.author.prefetched_books if i != self]
        else:
            return Book.objects.filter(
                author = self.author_id
            ).exclude(
                id = self.id
            )

    @property
    def selected_tags(self):
        if hasattr(self, 'prefetched_tags'):
            return self.prefetched_tags
        else:
            return self.tags.all()

class BookNote(models.Model):
    book = models.ForeignKey("Book", null=True)
    notes = models.TextField()

    objects = PrefetchManager()

########NEW FILE########
__FILENAME__ = tests
import logging
import logging.handlers

import time

from django import VERSION
from django.test import TestCase

import time
import re

from .models import Book, Author, Tag, BookNote, SillyException, LatestBook
from prefetch import InvalidPrefetch, Prefetcher, P, PrefetchManager

class AssertingHandler(logging.handlers.BufferingHandler):

    def __init__(self,capacity):
        logging.handlers.BufferingHandler.__init__(self,capacity)

    def assertLogged(self, test_case, msg):
        for record in self.buffer:
            s = self.format(record)
            if s.startswith(msg):
                return
        test_case.assertTrue(False, "Failed to find log message: " + msg)

class _AssertRaisesContext(object):
    """A context manager used to implement TestCase.assertRaises* methods."""

    def __init__(self, expected, test_case, expected_regexp=None):
        self.expected = expected
        self.failureException = test_case.failureException
        self.expected_regexp = expected_regexp

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            raise self.failureException(
                "{0} not raised".format(exc_name))
        if not issubclass(exc_type, self.expected):
            # let unexpected exceptions pass through
            return False
        self.exception = exc_value # store for later retrieval
        if self.expected_regexp is None:
            return True

        expected_regexp = self.expected_regexp
        if isinstance(expected_regexp, basestring):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(str(exc_value)):
            raise self.failureException('"%s" does not match "%s"' %
                     (expected_regexp.pattern, str(exc_value)))
        return True

class PrefetchTests(TestCase):
    def assertRegexpMatches(self, text, expected_regexp, msg=None):
        """Fail the test unless the text matches the regular expression."""
        if isinstance(expected_regexp, str):
            expected_regexp = re.compile(expected_regexp)
        if not expected_regexp.search(text):
            msg = msg or "Regexp didn't match"
            msg = '%s: %r not found in %r' % (msg, expected_regexp.pattern, text)
            raise self.failureException(msg)

    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        """Fail unless an exception of class excClass is thrown
           by callableObj when invoked with arguments args and keyword
           arguments kwargs. If a different type of exception is
           thrown, it will not be caught, and the test case will be
           deemed to have suffered an error, exactly as for an
           unexpected exception.

           If called with callableObj omitted or None, will return a
           context object used like this::

                with self.assertRaises(SomeException):
                    do_something()

           The context manager keeps a reference to the exception as
           the 'exception' attribute. This allows you to inspect the
           exception after the assertion::

               with self.assertRaises(SomeException) as cm:
                   do_something()
               the_exception = cm.exception
               self.assertEqual(the_exception.error_code, 3)
        """
        context = _AssertRaisesContext(excClass, self)
        if callableObj is None:
            return context
        with context:
            callableObj(*args, **kwargs)

    def test_books(self):
        author = Author.objects.create(name="John Doe")
        for i in range(3):
            Book.objects.create(name="Book %s"%i, author=author)

        for i in Author.objects.prefetch('books').filter(pk=author.pk):
            self.assertTrue(hasattr(i, 'prefetched_books'))
            self.assertEqual(len(i.books), 3, i.books)

        for i in Author.objects.filter(pk=author.pk):
            self.assertFalse(hasattr(i, 'prefetched_books'))
            self.assertEqual(len(i.books), 3, i.books)

    def test_latest_n_books(self):
        author1 = Author.objects.create(name="Johnny")
        for i in range(20, 30):
            Book.objects.create(name="Book %s"%i, author=author1)
            time.sleep(0.05)

        for i in Author.objects.prefetch('latest_n_books').filter(pk=author1.pk):
            self.assertTrue(hasattr(i, 'prefetched_latest_2_books'))
            self.assertEqual(
                [j.name for j in i.prefetched_latest_2_books],
                ["Book 29", "Book 28"]
            )

        for i in Author.objects.prefetch(P('latest_n_books')).filter(pk=author1.pk):
            self.assertTrue(hasattr(i, 'prefetched_latest_2_books'))
            self.assertEqual(
                [j.name for j in i.prefetched_latest_2_books],
                ["Book 29", "Book 28"]
            )

        for i in Author.objects.prefetch(P('latest_n_books', 5)).filter(pk=author1.pk):
            self.assertTrue(hasattr(i, 'prefetched_latest_5_books'))
            self.assertEqual(
                [j.name for j in i.prefetched_latest_5_books],
                ["Book 29", "Book 28", "Book 27", "Book 26", "Book 25"]
            )

        for i in Author.objects.prefetch(P('latest_n_books', count=5)).filter(pk=author1.pk):
            self.assertTrue(hasattr(i, 'prefetched_latest_5_books'))
            self.assertEqual(
                [j.name for j in i.prefetched_latest_5_books],
                ["Book 29", "Book 28", "Book 27", "Book 26", "Book 25"]
            )

    def test_latest_book(self):
        author1 = Author.objects.create(name="Johnny")
        author2 = Author.objects.create(name="Johnny")
        for i in range(3, 6):
            Book.objects.create(name="Book %s"%i, author=author1)
            time.sleep(0.1)

        for i in Author.objects.prefetch('latest_book').filter(pk=author1.pk):
            self.assertTrue(hasattr(i, 'prefetched_latest_book'))
            self.assertEqual(i.latest_book.name, "Book 5", i.latest_book.name)

        for i in Author.objects.prefetch('latest_book_as_class').filter(pk=author1.pk):
            self.assertTrue(hasattr(i, 'prefetched_latest_book'))
            self.assertEqual(i.latest_book.name, "Book 5", i)

        for i in Author.objects.prefetch('latest_book_as_class').filter(pk=author2.pk):
            self.assertTrue(hasattr(i, 'prefetched_latest_book'))
            self.assertEqual(i.latest_book, None, i)

        for i in Author.objects.filter(pk=author1.pk):
            self.assertFalse(hasattr(i, 'prefetched_latest_book'))
            self.assertEqual(i.latest_book.name, "Book 5", i)

        for i in Author.objects.filter(pk=author2.pk):
            self.assertFalse(hasattr(i, 'prefetched_latest_book'))
            self.assertEqual(i.latest_book, None, i)

    def test_forwarders(self):
        author = Author.objects.create(name="Johnny")
        tags = []
        for i in range(100):
            tags.append(Tag.objects.create(name="Tag %s" % i))

        for i in range(10, 20):
            book = Book.objects.create(name="Book %s"%i, author=author)
            if VERSION < (1, 2):
                from .models import Book_Tag
                for tag in tags[::7]:
                    Book_Tag.objects.create(tag=tag, book=book)
            else:
                book.tags.add(*tags[::7])

            for j in range(3):
                BookNote.objects.create(notes="Note %s/%s" % (i, j), book=book)

        for note in BookNote.objects.select_related("book").prefetch("book__tags"):
            self.assertTrue(hasattr(note.book, 'prefetched_tags'))
            self.assertEqual(len(note.book.selected_tags), 15, i)
            self.assertEqual(set(note.book.selected_tags), set(tags[::7]), i)

        for note in BookNote.objects.select_related("book"):
            self.assertFalse(hasattr(note.book, 'prefetched_tags'))
            self.assertEqual(len(note.book.selected_tags), 15, i)
            self.assertEqual(set(note.book.selected_tags), set(tags[::7]), i)

    def test_manual_forwarders_aka_collect(self):
        authors = [
            Author.objects.create(name="Johnny-%s" % i) for i in range(20)
        ]

        for author in authors:
            for i in range(20, 25):
                book = Book.objects.create(name="Book %s"%i, author=author)

        for book in Book.objects.select_related('author').prefetch('similar_books'):
            self.assertTrue(hasattr(book.author, 'prefetched_books'))
            self.assertEqual(len(book.similar_books), 4, book.similar_books)
            self.assertEqual(
                set(book.similar_books),
                set(Book.objects.filter(
                    author = book.author_id
                ).exclude(
                    id = book.id
                ))
            )

        failed = 0
        for book in Book.objects.select_related('author').prefetch('similar_books_missing_collect'):
            self.assertTrue(hasattr(book.author, 'prefetched_books'))
            if len(book.similar_books) != 4:
                failed += 1
        self.assertTrue(failed > 0, "There's should be at least 1 failure for similar_books_missing_collect prefetcher.")

        for book in Book.objects.select_related('author'):
            self.assertFalse(hasattr(book.author, 'prefetched_books'))
            self.assertEqual(len(book.similar_books), 4, book.similar_books)
            self.assertEqual(
                set(book.similar_books),
                set(Book.objects.filter(
                    author = book.author_id
                ).exclude(
                    id = book.id
                ))
            )


    def test_forwarders_with_null(self):
        author = Author.objects.create(name="Johnny")
        book = Book.objects.create(name="Book", author=author)
        BookNote.objects.create(notes="Note 1", book=book)
        BookNote.objects.create(notes="Note 2")

        note1, note2 = BookNote.objects.select_related("book").prefetch("book__tags").order_by('notes')
        self.assertTrue(hasattr(note1.book, 'prefetched_tags'))
        self.assertEqual(len(note1.book.selected_tags), 0)
        self.assertEqual(note2.book, None)

    def test_tags(self):
        tags = []
        for i in range(100):
            tags.append(Tag.objects.create(name="Tag %s" % i))
        author = Author.objects.create(name="Johnny")
        book = Book.objects.create(name="TaggedBook", author=author)
        if VERSION < (1, 2):
            from .models import Book_Tag
            for tag in tags[::7]:
                Book_Tag.objects.create(tag=tag, book=book)
        else:
            book.tags.add(*tags[::7])

        for i in Book.objects.prefetch('tags').filter(pk=book.pk):
            self.assertTrue(hasattr(i, 'prefetched_tags'))
            self.assertEqual(len(i.selected_tags), 15, i)
            self.assertEqual(set(i.selected_tags), set(tags[::7]), i)

        for i in Book.objects.filter(pk=book.pk):
            self.assertFalse(hasattr(i, 'prefetched_tags'))
            self.assertEqual(len(i.selected_tags), 15, i)
            self.assertEqual(set(i.selected_tags), set(tags[::7]), i)

    def test_books_queryset_get(self):
        author = Author.objects.create(name="John Doe")
        for i in range(3):
            Book.objects.create(name="Book %s"%i, author=author)

        i = Author.objects.prefetch('books').get(pk=author.pk)
        self.assertTrue(hasattr(i, 'prefetched_books'))
        self.assertEqual(len(i.books), 3, i.books)

        i = Author.objects.get(name="John Doe")
        self.assertFalse(hasattr(i, 'prefetched_books'))
        self.assertEqual(len(i.books), 3, i.books)

    if VERSION >= (1, 2):
        def test_using_db(self):
            author = Author.objects.using('secondary').create(name="John Doe")
            for i in range(3):
                Book.objects.using('secondary').create(name="Book %s"%i, author=author)

            for i in Author.objects.prefetch('books').filter(pk=author.pk).using('secondary'):
                self.assertTrue(hasattr(i, 'prefetched_books'))
                self.assertEqual(len(i.books), 3, i.books)

            for i in Author.objects.using('secondary').prefetch('books').filter(pk=author.pk):
                self.assertTrue(hasattr(i, 'prefetched_books'))
                self.assertEqual(len(i.books), 3, i.books)

            for i in Author.objects.db_manager('secondary').prefetch('books').filter(pk=author.pk):
                self.assertTrue(hasattr(i, 'prefetched_books'))
                self.assertEqual(len(i.books), 3, i.books)

            for i in Author.objects.filter(pk=author.pk).using('secondary'):
                self.assertFalse(hasattr(i, 'prefetched_books'))
                self.assertEqual(len(i.books), 3, i.books)

    def test_wrong_prefetch_subclass_and_instance(self):
        with self.assertRaises(InvalidPrefetch) as cm:
                objects = PrefetchManager(
                    latest_book_as_instance = LatestBook(),
                )


        self.assertEqual(cm.exception.args, ("Invalid prefetch definition latest_book_as_instance. This prefetcher needs to be a class not an instance.",))

    def test_wrong_prefetch_options_and_simple_prefetch(self):
        with self.assertRaises(InvalidPrefetch) as cm:
            Author.objects.prefetch(P('latest_book'))
        self.assertEqual(1, len(cm.exception.args))
        self.assertRegexpMatches(cm.exception.args[0], r"Invalid prefetch call with latest_book for on model <class 'test_app\.models\.Author'>. This prefetcher \(<prefetch\.Prefetcher object at 0x\w+>\) needs to be a subclass of Prefetcher\.")

    def test_wrong_prefetch_fwd(self):
        with self.assertRaises(InvalidPrefetch) as cm:
            Book.objects.prefetch('author__asdf')

        self.assertEqual(cm.exception.args, ("Invalid part asdf in prefetch call for author__asdf on model <class 'test_app.models.Book'>. The name is not a prefetcher nor a forward relation (fk).",))

    def test_wrong_prefetch_after_miss(self):
        with self.assertRaises(InvalidPrefetch) as cm:
            Book.objects.prefetch('author')

        self.assertEqual(cm.exception.args, ("Invalid prefetch call with author for on model <class 'test_app.models.Book'>. The last part isn't a prefetch definition.",))

    def test_wrong_prefetch_after_wrong(self):
        with self.assertRaises(InvalidPrefetch) as cm:
            Author.objects.prefetch('books__asdf')

        self.assertEqual(cm.exception.args, ("Invalid part asdf in prefetch call for books__asdf on model <class 'test_app.models.Author'>. You cannot have any more relations after the prefetcher.",))

    def test_wrong_prefetch_fwd_no_manager(self):
        with self.assertRaises(InvalidPrefetch) as cm:
            Book.objects.prefetch('publisher__whatev')

        self.assertEqual(cm.exception.args, ("Manager for <class 'test_app.models.Publisher'> is not a PrefetchManager instance.",))

    def test_wrong_prefetch(self):
        with self.assertRaises(InvalidPrefetch) as cm:
            Author.objects.prefetch('asdf')

        self.assertEqual(cm.exception.args, ("Invalid part asdf in prefetch call for asdf on model <class 'test_app.models.Author'>. The name is not a prefetcher nor a forward relation (fk).",))

    def test_wrong_definitions(self):
        class Bad1(Prefetcher):
            pass
        class Bad2(Bad1):
            def filter(self, ids):
                pass
        class Bad3(Bad2):
            def reverse_mapper(self, obj):
                pass

        self.assertRaises(RuntimeError, Bad1)
        self.assertRaises(RuntimeError, Bad2)
        self.assertRaises(RuntimeError, Bad3)

    def test_exception_raising_definitions(self):
        author = Author.objects.create(name="John Doe")

        asserting_handler = AssertingHandler(10)
        logging.getLogger().addHandler(asserting_handler)

        self.assertRaises(SillyException, lambda: list(Author.objects.prefetch('silly')))

        asserting_handler.assertLogged(self, "Prefetch failed for silly prefetch on the Author model:\nTraceback (most recent call last):")
        logging.getLogger().removeHandler(asserting_handler)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *

urlpatterns = patterns('')



########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import os
DEBUG = True

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = os.path.join(os.path.dirname(__file__), 'database.sqlite')
SECONDARY_DATABASE_NAME = os.path.join(os.path.dirname(__file__), 'database-secondary.sqlite')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_NAME
    },
    'secondary': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': SECONDARY_DATABASE_NAME
    }
}
INSTALLED_APPS = (
    'django.contrib.auth', 
    'django.contrib.contenttypes', 
    'django.contrib.sessions', 
    'django.contrib.sites',
    'test_app',
)
SITE_ID = 1
ROOT_URLCONF = 'test_project.urls'

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

SECRET_KEY = "DON'T MATTER"
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *


urlpatterns = patterns('',
    url(r'/', include('test_project.apps.testapp.urls'))
)

########NEW FILE########
