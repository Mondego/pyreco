__FILENAME__ = base
from weakref import WeakValueDictionary

from django.core.signals import request_finished
from django.db.models.base import Model, ModelBase
from django.db.models.signals import post_save, pre_delete, \
  post_syncdb

from manager import SharedMemoryManager


class SharedMemoryModelBase(ModelBase):
    # CL: upstream had a __new__ method that skipped ModelBase's __new__ if
    # SharedMemoryModelBase was not in the model class's ancestors. It's not
    # clear what was the intended purpose, but skipping ModelBase.__new__
    # broke things; in particular, default manager inheritance.

    def __call__(cls, *args, **kwargs):
        """
        this method will either create an instance (by calling the default implementation)
        or try to retrieve one from the class-wide cache by infering the pk value from
        args and kwargs. If instance caching is enabled for this class, the cache is
        populated whenever possible (ie when it is possible to infer the pk value).
        """
        def new_instance():
            return super(SharedMemoryModelBase, cls).__call__(*args, **kwargs)

        instance_key = cls._get_cache_key(args, kwargs)
        # depending on the arguments, we might not be able to infer the PK, so in that case we create a new instance
        if instance_key is None:
            return new_instance()

        # cached_instance = cls.get_cached_instance(instance_key)
        # if cached_instance is None:
        cached_instance = new_instance()
        cls.cache_instance(cached_instance)

        return cached_instance

    def _prepare(cls):
        cls.__instance_cache__ = WeakValueDictionary()
        super(SharedMemoryModelBase, cls)._prepare()


class SharedMemoryModel(Model):
    # CL: setting abstract correctly to allow subclasses to inherit the default
    # manager.
    __metaclass__ = SharedMemoryModelBase

    objects = SharedMemoryManager()

    class Meta:
        abstract = True

    def _get_cache_key(cls, args, kwargs):
        """
        This method is used by the caching subsystem to infer the PK value from the constructor arguments.
        It is used to decide if an instance has to be built or is already in the cache.
        """
        result = None
        # Quick hack for my composites work for now.
        if hasattr(cls._meta, 'pks'):
            pk = cls._meta.pks[0]
        else:
            pk = cls._meta.pk
        # get the index of the pk in the class fields. this should be calculated *once*, but isn't atm
        pk_position = cls._meta.fields.index(pk)
        if len(args) > pk_position:
            # if it's in the args, we can get it easily by index
            result = args[pk_position]
        elif pk.attname in kwargs:
            # retrieve the pk value. Note that we use attname instead of name, to handle the case where the pk is a
            # a ForeignKey.
            result = kwargs[pk.attname]
        elif pk.name != pk.attname and pk.name in kwargs:
            # ok we couldn't find the value, but maybe it's a FK and we can find the corresponding object instead
            result = kwargs[pk.name]

        if result is not None and isinstance(result, Model):
            # if the pk value happens to be a model instance (which can happen wich a FK), we'd rather use its own pk as the key
            result = result._get_pk_val()
        return result
    _get_cache_key = classmethod(_get_cache_key)

    def get_cached_instance(cls, id):
        """
        Method to retrieve a cached instance by pk value. Returns None when not found
        (which will always be the case when caching is disabled for this class). Please
        note that the lookup will be done even when instance caching is disabled.
        """
        return cls.__instance_cache__.get(id)
    get_cached_instance = classmethod(get_cached_instance)

    def cache_instance(cls, instance):
        """
        Method to store an instance in the cache.
        """
        if instance._get_pk_val() is not None:
            cls.__instance_cache__[instance._get_pk_val()] = instance
    cache_instance = classmethod(cache_instance)

    def _flush_cached_by_key(cls, key):
        try:
            del cls.__instance_cache__[key]
        except KeyError:
            pass
    _flush_cached_by_key = classmethod(_flush_cached_by_key)

    def flush_cached_instance(cls, instance):
        """
        Method to flush an instance from the cache. The instance will always be flushed from the cache,
        since this is most likely called from delete(), and we want to make sure we don't cache dead objects.
        """
        cls._flush_cached_by_key(instance._get_pk_val())
    flush_cached_instance = classmethod(flush_cached_instance)

    def flush_instance_cache(cls):
        cls.__instance_cache__ = WeakValueDictionary()
    flush_instance_cache = classmethod(flush_instance_cache)


# Use a signal so we make sure to catch cascades.
def flush_cache(**kwargs):
    for model in SharedMemoryModel.__subclasses__():
        model.flush_instance_cache()
request_finished.connect(flush_cache)
post_syncdb.connect(flush_cache)


def flush_cached_instance(sender, instance, **kwargs):
    # XXX: Is this the best way to make sure we can flush?
    if not hasattr(instance, 'flush_cached_instance'):
        return
    sender.flush_cached_instance(instance)
pre_delete.connect(flush_cached_instance)


def update_cached_instance(sender, instance, **kwargs):
    if not hasattr(instance, 'cache_instance'):
        return
    sender.cache_instance(instance)
post_save.connect(update_cached_instance)

########NEW FILE########
__FILENAME__ = manager
from django.db.models.manager import Manager
try:
    from django.db import router
except:
    pass


class SharedMemoryManager(Manager):
    # CL: this ensures our manager is used when accessing instances via
    # ForeignKey etc. (see docs)
    use_for_related_fields = True

    # CL: in the dev version of django, ReverseSingleRelatedObjectDescriptor
    # will call us as:
    #     rel_obj = rel_mgr.using(db).get(**params)
    # We need to handle using, or the get method will be called on a vanilla
    # queryset, and we won't get a change to use the cache.
    def using(self, alias):
        if alias == router.db_for_read(self.model):
            return self
        else:
            return super(SharedMemoryManager, self).using(alias)

    # TODO: improve on this implementation
    # We need a way to handle reverse lookups so that this model can
    # still use the singleton cache, but the active model isn't required
    # to be a SharedMemoryModel.
    def get(self, **kwargs):
        items = kwargs.keys()
        inst = None
        if len(items) == 1:
            # CL: support __exact
            key = items[0]
            if key.endswith('__exact'):
                key = key[:-len('__exact')]
            if key in ('pk', self.model._meta.pk.attname):
                inst = self.model.get_cached_instance(kwargs[items[0]])
        if inst is None:
            inst = super(SharedMemoryManager, self).get(**kwargs)
        return inst

########NEW FILE########
__FILENAME__ = models
from django.db.models import *
from base import SharedMemoryModel
########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase

from base import SharedMemoryModel
from django.db import models

class Category(SharedMemoryModel):
    name = models.CharField(max_length=32)

class RegularCategory(models.Model):
    name = models.CharField(max_length=32)

class Article(SharedMemoryModel):
    name = models.CharField(max_length=32)
    category = models.ForeignKey(Category)
    category2 = models.ForeignKey(RegularCategory)

class RegularArticle(models.Model):
    name = models.CharField(max_length=32)
    category = models.ForeignKey(Category)
    category2 = models.ForeignKey(RegularCategory)

class SharedMemorysTest(TestCase):
    # TODO: test for cross model relation (singleton to regular)
    
    def setUp(self):
        n = 0
        category = Category.objects.create(name="Category %d" % (n,))
        regcategory = RegularCategory.objects.create(name="Category %d" % (n,))
        
        for n in xrange(0, 10):
            Article.objects.create(name="Article %d" % (n,), category=category, category2=regcategory)
            RegularArticle.objects.create(name="Article %d" % (n,), category=category, category2=regcategory)
    
    def testSharedMemoryReferences(self):
        article_list = Article.objects.all().select_related('category')
        last_article = article_list[0]
        for article in article_list[1:]:
            self.assertEquals(article.category is last_article.category, True)
            last_article = article

    def testRegularReferences(self):
        article_list = RegularArticle.objects.all().select_related('category')
        last_article = article_list[0]
        for article in article_list[1:]:
            self.assertEquals(article.category2 is last_article.category2, False)
            last_article = article

    def testMixedReferences(self):
        article_list = RegularArticle.objects.all().select_related('category')
        last_article = article_list[0]
        for article in article_list[1:]:
            self.assertEquals(article.category is last_article.category, True)
            last_article = article

        article_list = Article.objects.all().select_related('category')
        last_article = article_list[0]
        for article in article_list[1:]:
            self.assertEquals(article.category2 is last_article.category2, False)
            last_article = article
        
    def testObjectDeletion(self):
        # This must execute first so its guaranteed to be in memory.
        article_list = list(Article.objects.all().select_related('category'))
        
        article = Article.objects.all()[0:1].get()
        pk = article.pk
        article.delete()
        self.assertEquals(pk not in Article.__instance_cache__, True)
        
        
########NEW FILE########
