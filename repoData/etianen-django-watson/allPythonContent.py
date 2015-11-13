__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
"""
Django settings for test_project project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '50l^23v!p7$mdlnd5v#ag5%lya9t=a%$51co6@rk50gl53+(n8'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "watson",
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

WSGI_APPLICATION = 'test_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.environ.get("DB_ENGINE", 'django.db.backends.sqlite3'),
        'NAME': os.environ.get("DB_NAME", os.path.join(BASE_DIR, 'db.sqlite3')),
        'USER': os.environ.get("DB_USER", ""),
        'PASSWORD': os.environ.get("DB_PASSWORD", ""),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_project.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for test_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

########NEW FILE########
__FILENAME__ = admin
"""Admin integration for django-watson."""

from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.admin.views.main import ChangeList

from watson.registration import SearchEngine, SearchAdapter


admin_search_engine = SearchEngine("admin")


class WatsonSearchChangeList(ChangeList):

    """A change list that takes advantage of django-watson full text search."""
        
    def get_query_set(self, *args, **kwargs):
        """Creates the query set."""
        # Do the basic searching.
        search_fields = self.search_fields
        self.search_fields = ()
        try:
            qs = super(WatsonSearchChangeList, self).get_query_set(*args, **kwargs)
        finally:
            self.search_fields = search_fields
        # Do the full text searching.
        if self.query.strip():
            qs = self.model_admin.search_engine.filter(qs, self.query, ranking=False)
        return qs


class SearchAdmin(admin.ModelAdmin):

    """
    A ModelAdmin subclass that provides full-text search integration.
    
    Subclass this admin class and specify a tuple of search_fields for instant
    integration!
    """
    
    search_engine = admin_search_engine
    
    search_adapter_cls = SearchAdapter
    
    @property
    def search_context_manager(self):
        """The search context manager used by this SearchAdmin."""
        return self.search_engine._search_context_manager
    
    def __init__(self, *args, **kwargs):
        """Initializes the search admin."""
        super(SearchAdmin, self).__init__(*args, **kwargs)
        # Check that the search fields are valid.
        for search_field in self.search_fields or ():
            if search_field[0] in ("^", "@", "="):
                raise ValueError("SearchAdmin does not support search fields prefixed with '^', '=' or '@'")
        # Register with the search engine.
        self.register_model_with_watson()
        # Set up revision contexts on key methods, just in case.
        self.add_view = self.search_context_manager.update_index()(self.add_view)
        self.change_view = self.search_context_manager.update_index()(self.change_view)
        self.delete_view = self.search_context_manager.update_index()(self.delete_view)
        self.changelist_view = self.search_context_manager.update_index()(self.changelist_view)
    
    def register_model_with_watson(self):
        """Registers this admin class' model with django-watson."""
        if not self.search_engine.is_registered(self.model) and self.search_fields:
            self.search_engine.register(
                self.model,
                fields = self.search_fields,
                adapter_cls = self.search_adapter_cls,
                get_live_queryset = lambda self_: None,  # Ensure complete queryset is used in admin.
            )
    
    def get_changelist(self, request, **kwargs):
        """Returns the ChangeList class for use on the changelist page."""
        return WatsonSearchChangeList

########NEW FILE########
__FILENAME__ = backends
"""Search backends used by django-watson."""

from __future__ import unicode_literals

import re, abc

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Q
from django.utils.encoding import force_text
from django.utils import six

from watson.models import SearchEntry, has_int_pk


def regex_from_word(word):
    """Generates a regext from the given search word."""
    return "(\s{word})|(^{word})".format(
        word = re.escape(word),
    )
    
    
def make_escaper(badchars):
    """Creates an efficient escape function that strips the given characters from the string."""
    translation_table = dict((ord(c), None) for c in badchars)
    def escaper(text):
        return force_text(text, errors="ignore").translate(translation_table)
    return escaper


class SearchBackend(six.with_metaclass(abc.ABCMeta)):

    """Base class for all search backends."""
    
    def is_installed(self):
        """Checks whether django-watson is installed."""
        return True
    
    def do_install(self):
        """Executes the SQL needed to install django-watson."""
        pass
        
    def do_uninstall(self):
        """Executes the SQL needed to uninstall django-watson."""
        pass
    
    requires_installation = False
    
    supports_ranking = False
    
    supports_prefix_matching = False
        
    def do_search_ranking(self, engine_slug, queryset, search_text):
        """Ranks the given queryset according to the relevance of the given search text."""
        return queryset.extra(
            select = {
                "watson_rank": "1",
            },
        )
        
    @abc.abstractmethod
    def do_search(self, engine_slug, queryset, search_text):
        """Filters the given queryset according the the search logic for this backend."""
        raise NotImplementedError
        
    def do_filter_ranking(self, engine_slug, queryset, search_text):
        """Ranks the given queryset according to the relevance of the given search text."""
        return queryset.extra(
            select = {
                "watson_rank": "1",
            },
        )
    
    @abc.abstractmethod
    def do_filter(self, engine_slug, queryset, search_text):
        """Filters the given queryset according the the search logic for this backend."""
        raise NotImplementedError


class RegexSearchMixin(six.with_metaclass(abc.ABCMeta)):
    
    """Mixin to adding regex search to a search backend."""
    
    supports_prefix_matching = True
    
    def do_search(self, engine_slug, queryset, search_text):
        """Filters the given queryset according the the search logic for this backend."""
        word_query = Q()
        for word in search_text.split():
            regex = regex_from_word(word)
            word_query &= (Q(title__iregex=regex) | Q(description__iregex=regex) | Q(content__iregex=regex))
        return queryset.filter(
            word_query
        )
        
    def do_filter(self, engine_slug, queryset, search_text):
        """Filters the given queryset according the the search logic for this backend."""
        model = queryset.model
        db_table = connection.ops.quote_name(SearchEntry._meta.db_table)
        model_db_table = connection.ops.quote_name(model._meta.db_table)
        pk = model._meta.pk
        id = connection.ops.quote_name(pk.db_column or pk.attname)
        # Add in basic filters.
        word_query = ["""
            ({db_table}.{engine_slug} = %s)
        """, """
            ({db_table}.{content_type_id} = %s)
        """]
        word_kwargs= {
            "db_table": db_table,
            "model_db_table": model_db_table,
            "engine_slug": connection.ops.quote_name("engine_slug"),
            "title": connection.ops.quote_name("title"),
            "description": connection.ops.quote_name("description"),
            "content": connection.ops.quote_name("content"),
            "content_type_id": connection.ops.quote_name("content_type_id"),
            "object_id": connection.ops.quote_name("object_id"),
            "object_id_int": connection.ops.quote_name("object_id_int"),
            "id": id,
            "iregex_operator": connection.operators["iregex"],
        }
        word_args = [
            engine_slug,
            ContentType.objects.get_for_model(model).id,
        ]
        # Add in join.
        if has_int_pk(model):
            word_query.append("""
                ({db_table}.{object_id_int} = {model_db_table}.{id})
            """)
        else:
            word_query.append("""
                ({db_table}.{object_id} = {model_db_table}.{id})
            """)
        # Add in all words.
        for word in search_text.split():
            regex = regex_from_word(word)
            word_query.append("""
                ({db_table}.{title} {iregex_operator} OR {db_table}.{description} {iregex_operator} OR {db_table}.{content} {iregex_operator}) 
            """)
            word_args.extend((regex, regex, regex))
        # Compile the query.
        full_word_query = " AND ".join(word_query).format(**word_kwargs)
        return queryset.extra(
            tables = (db_table,),
            where = (full_word_query,),
            params = word_args,
        )


class RegexSearchBackend(RegexSearchMixin, SearchBackend):
    
    """A search backend that works with SQLite3."""


escape_postgres_query_chars = make_escaper("():|!&*")


class PostgresSearchBackend(SearchBackend):

    """A search backend that uses native PostgreSQL full text indices."""

    search_config = "pg_catalog.english"
    """Text search configuration to use in `to_tsvector` and `to_tsquery` functions"""

    def escape_postgres_query(self, text):
        """Escapes the given text to become a valid ts_query."""
        return " & ".join(
            "{0}:*".format(word)
            for word
            in escape_postgres_query_chars(text).split()
        )
    
    def is_installed(self):
        """Checks whether django-watson is installed."""
        cursor = connection.cursor()
        cursor.execute("""        
            SELECT attname FROM pg_attribute
            WHERE attrelid = (SELECT oid FROM pg_class WHERE relname = 'watson_searchentry') AND attname = 'search_tsv';
        """)
        return bool(cursor.fetchall())
    
    def do_install(self):
        """Executes the PostgreSQL specific SQL code to install django-watson."""
        connection.cursor().execute("""
            -- Ensure that plpgsql is installed.
            CREATE OR REPLACE FUNCTION make_plpgsql() RETURNS VOID LANGUAGE SQL AS
            $$
                CREATE LANGUAGE plpgsql;
            $$;
            SELECT
                CASE
                WHEN EXISTS(
                    SELECT 1
                    FROM pg_catalog.pg_language
                    WHERE lanname='plpgsql'
                )
                THEN NULL
                ELSE make_plpgsql() END;
            DROP FUNCTION make_plpgsql();

            -- Create the search index.
            ALTER TABLE watson_searchentry ADD COLUMN search_tsv tsvector NOT NULL;
            CREATE INDEX watson_searchentry_search_tsv ON watson_searchentry USING gin(search_tsv);

            -- Create the trigger function.
            CREATE OR REPLACE FUNCTION watson_searchentry_trigger_handler() RETURNS trigger AS $$
            begin
                new.search_tsv :=
                    setweight(to_tsvector('{search_config}', coalesce(new.title, '')), 'A') ||
                    setweight(to_tsvector('{search_config}', coalesce(new.description, '')), 'C') ||
                    setweight(to_tsvector('{search_config}', coalesce(new.content, '')), 'D');
                return new;
            end
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER watson_searchentry_trigger BEFORE INSERT OR UPDATE
            ON watson_searchentry FOR EACH ROW EXECUTE PROCEDURE watson_searchentry_trigger_handler();
        """.format(
            search_config = self.search_config
        ))

    def do_uninstall(self):
        """Executes the PostgreSQL specific SQL code to uninstall django-watson."""
        connection.cursor().execute("""
            ALTER TABLE watson_searchentry DROP COLUMN search_tsv;

            DROP TRIGGER watson_searchentry_trigger ON watson_searchentry;

            DROP FUNCTION watson_searchentry_trigger_handler();
        """)
        
    requires_installation = True
    
    supports_ranking = True
    
    supports_prefix_matching = True
        
    def do_search(self, engine_slug, queryset, search_text):
        """Performs the full text search."""
        return queryset.extra(
            where = ("search_tsv @@ to_tsquery('{search_config}', %s)".format(
                search_config = self.search_config
            ),),
            params = (self.escape_postgres_query(search_text),),
        )
        
    def do_search_ranking(self, engine_slug, queryset, search_text):
        """Performs full text ranking."""
        return queryset.extra(
            select = {
                "watson_rank": "ts_rank_cd(watson_searchentry.search_tsv, to_tsquery('{search_config}', %s))".format(
                    search_config = self.search_config
                ),
            },
            select_params = (self.escape_postgres_query(search_text),),
            order_by = ("-watson_rank",),
        )
        
    def do_filter(self, engine_slug, queryset, search_text):
        """Performs the full text filter."""
        model = queryset.model
        content_type = ContentType.objects.get_for_model(model)
        pk = model._meta.pk
        if has_int_pk(model):
            ref_name = "object_id_int"
        else:
            ref_name = "object_id"
        return queryset.extra(
            tables = ("watson_searchentry",),
            where = (
                "watson_searchentry.engine_slug = %s",
                "watson_searchentry.search_tsv @@ to_tsquery('{search_config}', %s)".format(
                    search_config = self.search_config
                ),
                "watson_searchentry.{ref_name} = {table_name}.{pk_name}".format(
                    ref_name = ref_name,
                    table_name = connection.ops.quote_name(model._meta.db_table),
                    pk_name = connection.ops.quote_name(pk.db_column or pk.attname),
                ),
                "watson_searchentry.content_type_id = %s"
            ),
            params = (engine_slug, self.escape_postgres_query(search_text), content_type.id),
        )
        
    def do_filter_ranking(self, engine_slug, queryset, search_text):
        """Performs the full text ranking."""
        return queryset.extra(
            select = {
                "watson_rank": "ts_rank_cd(watson_searchentry.search_tsv, to_tsquery('{search_config}', %s))".format(
                    search_config = self.search_config
                ),
            },
            select_params = (self.escape_postgres_query(search_text),),
            order_by = ("-watson_rank",),
        )
        
        
class PostgresLegacySearchBackend(PostgresSearchBackend):

    """
    A search backend that uses native PostgreSQL full text indices.
    
    This backend doesn't support prefix matching, and works with PostgreSQL 8.3 and below.
    """
    
    supports_prefix_matching = False
    
    def escape_postgres_query(self, text):
        """Escapes the given text to become a valid ts_query."""
        return " & ".join(escape_postgres_query_chars(text).split())


class PostgresPrefixLegacySearchBackend(RegexSearchMixin, PostgresLegacySearchBackend):
    
    """
    A legacy search backend that uses a regexp to perform matches, but still allows
    relevance rankings.
    
    Use if your postgres vesion is less than 8.3, and you absolutely can't live without
    prefix matching. Beware, this backend can get slow with large datasets! 
    """
        

escape_mysql_boolean_query_chars = make_escaper("+-<>()*\".!:,;")

def escape_mysql_boolean_query(search_text):
    return " ".join(
        '+{word}*'.format(
            word = word,
        )
        for word in escape_mysql_boolean_query_chars(search_text).split()
    )
    

class MySQLSearchBackend(SearchBackend):

    def is_installed(self):
        """Checks whether django-watson is installed."""
        cursor = connection.cursor()
        cursor.execute("SHOW INDEX FROM watson_searchentry WHERE Key_name = 'watson_searchentry_fulltext'");
        return bool(cursor.fetchall())

    def do_install(self):
        """Executes the MySQL specific SQL code to install django-watson."""
        cursor = connection.cursor()
        # Drop all foreign keys on the watson_searchentry table.
        cursor.execute("SELECT CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'watson_searchentry' AND CONSTRAINT_TYPE = 'FOREIGN KEY'")
        for constraint_name, in cursor.fetchall():
            cursor.execute("ALTER TABLE watson_searchentry DROP FOREIGN KEY {constraint_name}".format(
                constraint_name = constraint_name,
            ))
        # Change the storage engine to MyISAM.
        cursor.execute("ALTER TABLE watson_searchentry ENGINE = MyISAM")
        # Add the full text indexes.
        cursor.execute("CREATE FULLTEXT INDEX watson_searchentry_fulltext ON watson_searchentry (title, description, content)")
        cursor.execute("CREATE FULLTEXT INDEX watson_searchentry_title ON watson_searchentry (title)")
        cursor.execute("CREATE FULLTEXT INDEX watson_searchentry_description ON watson_searchentry (description)")
        cursor.execute("CREATE FULLTEXT INDEX watson_searchentry_content ON watson_searchentry (content)")
    
    def do_uninstall(self):
        """Executes the SQL needed to uninstall django-watson."""
        cursor = connection.cursor()
        # Destroy the full text indexes.
        cursor.execute("DROP INDEX watson_searchentry_fulltext ON watson_searchentry")
        cursor.execute("DROP INDEX watson_searchentry_title ON watson_searchentry")
        cursor.execute("DROP INDEX watson_searchentry_description ON watson_searchentry")
        cursor.execute("DROP INDEX watson_searchentry_content ON watson_searchentry")
    
    supports_prefix_matching = True
    
    requires_installation = True
    
    supports_ranking = True
    
    def do_search(self, engine_slug, queryset, search_text):
        """Performs the full text search."""
        return queryset.extra(
            where = ("MATCH (title, description, content) AGAINST (%s IN BOOLEAN MODE)",),
            params = (escape_mysql_boolean_query(search_text),),
        )
        
    def do_search_ranking(self, engine_slug, queryset, search_text):
        """Performs full text ranking."""
        search_text = escape_mysql_boolean_query(search_text)
        return queryset.extra(
            select = {
                "watson_rank": """
                    ((MATCH (title) AGAINST (%s IN BOOLEAN MODE)) * 3) +
                    ((MATCH (description) AGAINST (%s IN BOOLEAN MODE)) * 2) +
                    ((MATCH (content) AGAINST (%s IN BOOLEAN MODE)) * 1)
                """,
            },
            select_params = (search_text, search_text, search_text,),
            order_by = ("-watson_rank",),
        )
        
    def do_filter(self, engine_slug, queryset, search_text):
        """Performs the full text filter."""
        model = queryset.model
        content_type = ContentType.objects.get_for_model(model)
        pk = model._meta.pk
        if has_int_pk(model):
            ref_name = "object_id_int"
        else:
            ref_name = "object_id"
        return queryset.extra(
            tables = ("watson_searchentry",),
            where = (
                "watson_searchentry.engine_slug = %s",
                "MATCH (watson_searchentry.title, watson_searchentry.description, watson_searchentry.content) AGAINST (%s IN BOOLEAN MODE)",
                "watson_searchentry.{ref_name} = {table_name}.{pk_name}".format(
                    ref_name = ref_name,
                    table_name = connection.ops.quote_name(model._meta.db_table),
                    pk_name = connection.ops.quote_name(pk.db_column or pk.attname),
                ),
                "watson_searchentry.content_type_id = %s",
            ),
            params = (engine_slug, escape_mysql_boolean_query(search_text), content_type.id),
        )
        
    def do_filter_ranking(self, engine_slug, queryset, search_text):
        """Performs the full text ranking."""
        search_text = escape_mysql_boolean_query(search_text)
        return queryset.extra(
            select = {
                "watson_rank": """
                    ((MATCH (watson_searchentry.title) AGAINST (%s IN BOOLEAN MODE)) * 3) +
                    ((MATCH (watson_searchentry.description) AGAINST (%s IN BOOLEAN MODE)) * 2) +
                    ((MATCH (watson_searchentry.content) AGAINST (%s IN BOOLEAN MODE)) * 1)
                """,
            },
            select_params = (search_text, search_text, search_text,),
            order_by = ("-watson_rank",),
        )


def get_postgresql_version(connection):
    """Returns the version number of the PostgreSQL connection."""
    try:
        from django.db.backends.postgresql.version import get_version  # Django 1.3
    except ImportError:
        # Use the Django 1.4 method.
        from django.db.backends.postgresql_psycopg2.version import get_version
        return get_version(connection)
    else:
        # Use the Django 1.3 method. 
        cursor = connection.cursor()
        major, major2, minor = get_version(cursor)
        return major * 10000 + major2 * 100 + minor
        
        
class AdaptiveSearchBackend(SearchBackend):

    """
    A search backend that guesses the correct search backend based on the
    DATABASES["default"] settings.
    """
    
    def __new__(cls):
        """Guess the correct search backend and initialize it."""
        if connection.vendor == "postgresql":
            version = get_postgresql_version(connection)
            if version > 80400:
                return PostgresSearchBackend()
            if version > 80300:
                return PostgresLegacySearchBackend()
        if connection.vendor == "mysql":
            return MySQLSearchBackend()
        return RegexSearchBackend()

########NEW FILE########
__FILENAME__ = buildwatson
"""Rebuilds the database indices needed by django-watson."""

from __future__ import unicode_literals, print_function

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_model
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from watson.registration import SearchEngine, _bulk_save_search_entries
from watson.models import SearchEntry


# Sets up registration for django-watson's admin integration.
admin.autodiscover()

def get_engine(engine_slug_):
    '''returns search engine with a given name'''
    try:
        return [x[1] for x in SearchEngine.get_created_engines() if x[0] == engine_slug_][0]
    except IndexError:
        raise CommandError("Search Engine \"%s\" is not registered!" % engine_slug_)

def rebuild_index_for_model(model_, engine_slug_, verbosity_):
    '''rebuilds index for a model'''

    search_engine_ = get_engine(engine_slug_)

    local_refreshed_model_count = [0]  # HACK: Allows assignment to outer scope.
    def iter_search_entries():
        for obj in model_._default_manager.all().iterator():
            for search_entry in search_engine_._update_obj_index_iter(obj):
                yield search_entry
            local_refreshed_model_count[0] += 1
            if verbosity_ >= 3:
                print("Refreshed search entry for {model} {obj} in {engine_slug!r} search engine.".format(
                    model = model_._meta.verbose_name,
                    obj = obj,
                    engine_slug = engine_slug_,
                ))
        if verbosity_ == 2:
            print("Refreshed {local_refreshed_model_count} {model} search entry(s) in {engine_slug!r} search engine.".format(
                model = model_._meta.verbose_name,
                local_refreshed_model_count = local_refreshed_model_count[0],
                engine_slug = engine_slug_,
            ))
    _bulk_save_search_entries(iter_search_entries())
    return local_refreshed_model_count[0]

class Command(BaseCommand):
    args = "[[--engine=search_engine] <app.model|model> <app.model|model> ... ]"
    help = "Rebuilds the database indices needed by django-watson. You can (re-)build index for selected models by specifying them"

    option_list = BaseCommand.option_list + (
        make_option("--engine",
            help="Search engine models are registered with"),
        )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        """Runs the management command."""
        verbosity = int(options.get("verbosity", 1))

        # see if we're asked to use a specific search engine
        if options['engine']:
            engine_slug = options['engine']
            engine_selected = True
        else:
            engine_slug = "default"
            engine_selected = False

        # get the search engine we'll be checking registered models for, may be "default"
        search_engine = get_engine(engine_slug)

        models = []
        for model_name in args:
            try:
                model = get_model(*model_name.split("."))  # app label, model name
            except TypeError:  # were we given only model name without app_name?
                registered_models = search_engine.get_registered_models()
                matching_models = [x for x in registered_models if x.__name__ == model_name]
                if len(matching_models) > 1:
                    raise CommandError("Model name \"%s\" is not unique, cannot continue!" % model_name)
                if matching_models:
                    model = matching_models[0]
                else:
                    model = None
            if model is None or not search_engine.is_registered(model):
                raise CommandError("Model \"%s\" is not registered with django-watson search engine \"%s\"!" % (model_name, engine_slug))
            models.append(model)
        
        refreshed_model_count = 0

        if models:  # request for (re-)building index for a subset of registered models
            if verbosity >= 3:
                print("Using search engine \"%s\"" % engine_slug)
            for model in models:
                refreshed_model_count += rebuild_index_for_model(model, engine_slug, verbosity)

        else:  # full rebuild (for one or all search engines)
            if engine_selected:
                engine_slugs = [engine_slug]
                if verbosity >= 2:
                    # let user know the search engine if they selected one
                    print("Rebuilding models registered with search engine \"%s\"" % engine_slug)
            else:  # loop through all engines
                engine_slugs = [x[0] for x in SearchEngine.get_created_engines()]

            for engine_slug in engine_slugs:
                search_engine = get_engine(engine_slug)
                registered_models = search_engine.get_registered_models()
                # Rebuild the index for all registered models.
                for model in registered_models:
                    refreshed_model_count += rebuild_index_for_model(model, engine_slug, verbosity)

            # Clean out any search entries that exist for stale content types. Only do it during full rebuild
            valid_content_types = [ContentType.objects.get_for_model(model) for model in registered_models]
            stale_entries = SearchEntry.objects.filter(
                engine_slug = engine_slug,
            ).exclude(
                content_type__in = valid_content_types
            )
            stale_entry_count = stale_entries.count()
            if stale_entry_count > 0:
                stale_entries.delete()
            if verbosity >= 1:
                print("Deleted {stale_entry_count} stale search entry(s) in {engine_slug!r} search engine.".format(
                    stale_entry_count = stale_entry_count,
                    engine_slug = engine_slug,
                ))

        if verbosity == 1:
            print("Refreshed {refreshed_model_count} search entry(s) in {engine_slug!r} search engine.".format(
                refreshed_model_count = refreshed_model_count,
                engine_slug = engine_slug,
            ))

########NEW FILE########
__FILENAME__ = installwatson
"""Creates the database indices needed by django-watson."""

from __future__ import unicode_literals

from django.core.management.base import NoArgsCommand
from django.db import transaction

from watson.registration import get_backend


class Command(NoArgsCommand):

    help = "Creates the database indices needed by django-watson."
    
    @transaction.commit_on_success
    def handle_noargs(self, **options):
        """Runs the management command."""
        verbosity = int(options.get("verbosity", 1))
        backend = get_backend()
        if not backend.requires_installation:
            if verbosity >= 2:
                self.stdout.write("Your search backend does not require installation.\n")
        elif backend.is_installed():
            if verbosity >= 2:
                self.stdout.write("django-watson is already installed.\n")
        else:
            backend.do_install()
            if verbosity >= 2:
                self.stdout.write("django-watson has been successfully installed.\n")

########NEW FILE########
__FILENAME__ = uninstallwatson
"""Destroys the database indices needed by django-watson."""

from __future__ import unicode_literals

from django.core.management.base import NoArgsCommand
from django.db import transaction

from watson.registration import get_backend


class Command(NoArgsCommand):

    help = "Destroys the database indices needed by django-watson."
    
    @transaction.commit_on_success
    def handle_noargs(self, **options):
        """Runs the management command."""
        verbosity = int(options.get("verbosity", 1))
        backend = get_backend()
        if not backend.requires_installation:
            if verbosity >= 2:
                self.stdout.write("Your search backend does not require installation.\n")
        elif backend.is_installed():
            backend.do_uninstall()
            if verbosity >= 2:
                self.stdout.write("django-watson has been successfully uninstalled.\n")
        else:
            if verbosity >= 2:
                self.stdout.write("django-watson is not installed.\n")

########NEW FILE########
__FILENAME__ = middleware
"""Middleware used by django-watson."""

from __future__ import unicode_literals

from watson.registration import search_context_manager


WATSON_MIDDLEWARE_FLAG = "watson.search_context_middleware_active"


class SearchContextMiddleware(object):
    
    """Wraps the entire request in a search context."""
    
    def process_request(self, request):
        """Starts a new search context."""
        request.META[(WATSON_MIDDLEWARE_FLAG, self)] = True
        search_context_manager.start()
    
    def _close_search_context(self, request):
        """Closes the search context."""
        if request.META.get((WATSON_MIDDLEWARE_FLAG, self), False):
            del request.META[(WATSON_MIDDLEWARE_FLAG, self)]
            search_context_manager.end()
    
    def process_response(self, request, response):
        """Closes the search context."""
        self._close_search_context(request)
        return response
        
    def process_exception(self, request, exception):
        """Closes the search context."""
        search_context_manager.invalidate()    
        self._close_search_context(request)

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SearchEntry'
        db.create_table('watson_searchentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('engine_slug', self.gf('django.db.models.fields.CharField')(max_length=200, db_index=True)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.TextField')()),
            ('object_id_int', self.gf('django.db.models.fields.IntegerField')(db_index=True, null=True, blank=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('content', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=1000, blank=True)),
            ('meta_encoded', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('watson', ['SearchEntry'])


    def backwards(self, orm):
        
        # Deleting model 'SearchEntry'
        db.delete_table('watson_searchentry')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'watson.searchentry': {
            'Meta': {'object_name': 'SearchEntry'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'engine_slug': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta_encoded': ('django.db.models.fields.TextField', [], {}),
            'object_id': ('django.db.models.fields.TextField', [], {}),
            'object_id_int': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'})
        }
    }

    complete_apps = ['watson']

########NEW FILE########
__FILENAME__ = 0002_installwatson
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.core.management import call_command

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        
        # Needs to be run in a separate migration to avoid borking MySQL.
        call_command("installwatson", verbosity=0)


    def backwards(self, orm):
        "Write your backwards methods here."
        
        call_command("uninstallwatson", verbosity=0)


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'watson.searchentry': {
            'Meta': {'object_name': 'SearchEntry'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'engine_slug': ('django.db.models.fields.CharField', [], {'max_length': '200', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta_encoded': ('django.db.models.fields.TextField', [], {}),
            'object_id': ('django.db.models.fields.TextField', [], {}),
            'object_id_int': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'})
        }
    }

    complete_apps = ['watson']

########NEW FILE########
__FILENAME__ = models
"""Models used by django-watson."""

from __future__ import unicode_literals

import json

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

def has_int_pk(model):
    """Tests whether the given model has an integer primary key."""
    pk = model._meta.pk
    return (
        (
            isinstance(pk, (models.IntegerField, models.AutoField)) and
            not isinstance(pk, models.BigIntegerField)
        ) or (
            isinstance(pk, models.ForeignKey) and has_int_pk(pk.rel.to)
        )
    )
    
    
META_CACHE_KEY = "_meta_cache"


class SearchEntry(models.Model):

    """An entry in the search index."""
    
    engine_slug = models.CharField(
        max_length = 200,
        db_index = True,
        default = "default",
    )
    
    content_type = models.ForeignKey(
        ContentType,
    )

    object_id = models.TextField()
    
    object_id_int = models.IntegerField(
        blank = True,
        null = True,
        db_index = True,
    )
    
    object = generic.GenericForeignKey()
    
    title = models.CharField(
        max_length = 1000,
    )
    
    description = models.TextField(
        blank = True,
    )
    
    content = models.TextField(
        blank = True,
    )
    
    url = models.CharField(
        max_length = 1000,
        blank = True,
    )
    
    meta_encoded = models.TextField()
    
    @property
    def meta(self):
        """Returns the meta information stored with the search entry."""
        # Attempt to use the cached value.
        if hasattr(self, META_CACHE_KEY):
            return getattr(self, META_CACHE_KEY)
        # Decode the meta.
        meta_value = json.loads(self.meta_encoded)
        setattr(self, META_CACHE_KEY, meta_value)
        return meta_value
        
    def get_absolute_url(self):
        """Returns the URL of the referenced object."""
        return self.url
        
    def __unicode__(self):
        """Returns a unicode representation."""
        return self.title
        
    class Meta:
        verbose_name_plural = "search entries"

########NEW FILE########
__FILENAME__ = registration
"""Adapters for registering models with django-watson."""

from __future__ import unicode_literals

import sys, json
from itertools import chain, islice
from threading import local
from functools import wraps
from weakref import WeakValueDictionary

from django.conf import settings
from django.core.signals import request_finished
from django.core.exceptions import ImproperlyConfigured
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet
from django.db.models.signals import post_save, pre_delete
from django.utils.encoding import force_text
from django.utils.html import strip_tags
from django.utils.importlib import import_module

from watson.models import SearchEntry, has_int_pk


class SearchAdapterError(Exception):

    """Something went wrong with a search adapter."""


class SearchAdapter(object):

    """An adapter for performing a full-text search on a model."""
    
    # Use to specify the fields that should be included in the search.
    fields = ()
    
    # Use to exclude fields from the search.
    exclude = ()
    
    # Use to specify object properties to be stored in the search index.
    store = ()
    
    def __init__(self, model):
        """Initializes the search adapter."""
        self.model = model
    
    def _resolve_field(self, obj, name):
        """Resolves the content of the given model field."""
        name_parts = name.split("__", 1)
        prefix = name_parts[0]
        # Get the attribute.
        if hasattr(obj, prefix):
            value = getattr(obj, prefix)
            if callable(value):
                value = value()
        elif hasattr(self, prefix):
            value = getattr(self, prefix)
            if callable(value):
                value = value(obj)
        else:
            raise SearchAdapterError("Could not find a property called {name!r} on either {obj!r} or {search_adapter!r}".format(
                name = prefix,
                obj = obj,
                search_adapter = self,
            ))
        # Look up recursive fields.
        if len(name_parts) == 2:
            if isinstance(value, (QuerySet, models.Manager)):
                return " ".join(force_text(self._resolve_field(obj, name_parts[1])) for obj in value.all())
            return self._resolve_field(value, name_parts[1])
        # Resolve querysets.
        if isinstance(value, (QuerySet, models.Manager)):
            value = " ".join(force_text(related) for related in value.all())
        # Resolution complete!
        return value
    
    def prepare_content(self, content):
        """Sanitizes the given content string for better parsing by the search engine."""
        # Strip out HTML tags.
        content = strip_tags(content)
        return content
    
    def get_title(self, obj):
        """
        Returns the title of this search result. This is given high priority in search result ranking.
        
        You can access the title of the search entry as `entry.title` in your search results.
        
        The default implementation returns `force_text(obj)`.
        """
        return force_text(obj)
        
    def get_description(self, obj):
        """
        Returns the description of this search result. This is given medium priority in search result ranking.
        
        You can access the description of the search entry as `entry.description` in your search results. Since
        this should contains a short description of the search entry, it's excellent for providing a summary
        in your search results.
        
        The default implementation returns `""`.
        """
        return ""
        
    def get_content(self, obj):
        """
        Returns the content of this search result. This is given low priority in search result ranking.
        
        You can access the content of the search entry as `entry.content` in your search results, although
        this field generally contains a big mess of search data so is less suitable for frontend display.
        
        The default implementation returns all the registered fields in your model joined together.
        """
        # Get the field names to look up.
        field_names = self.fields or (field.name for field in self.model._meta.fields if isinstance(field, (models.CharField, models.TextField)))
        # Exclude named fields.
        field_names = (field_name for field_name in field_names if field_name not in self.exclude)
        # Create the text.
        return self.prepare_content(" ".join(
            force_text(self._resolve_field(obj, field_name))
            for field_name in field_names
        ))
    
    def get_url(self, obj):
        """Return the URL of the given obj."""
        if hasattr(obj, "get_absolute_url"):
            return obj.get_absolute_url()
        return ""
    
    def get_meta(self, obj):
        """Returns a dictionary of meta information about the given obj."""
        return dict(
            (field_name, self._resolve_field(obj, field_name))
            for field_name in self.store
        )
        
    def get_live_queryset(self):
        """
        Returns the queryset of objects that should be considered live.
        
        If this returns None, then all objects should be considered live, which is more efficient.
        """
        return None


class SearchEngineError(Exception):

    """Something went wrong with a search engine."""


class RegistrationError(SearchEngineError):

    """Something went wrong when registering a model with a search engine."""
    
    
class SearchContextError(Exception):
    
    """Something went wrong with the search context management."""


def _bulk_save_search_entries(search_entries, batch_size=100):
    """Creates the given search entry data in the most efficient way possible."""
    if search_entries:
        if hasattr(SearchEntry.objects, "bulk_create"):
            search_entries = iter(search_entries)
            while True:
                search_entry_batch = list(islice(search_entries, 0, batch_size))
                if not search_entry_batch:
                    break
                SearchEntry.objects.bulk_create(search_entry_batch)
        else:
            for search_entry in search_entries:
                search_entry.save()


class SearchContextManager(local):

    """A thread-local context manager used to manage saving search data."""
    
    def __init__(self):
        """Initializes the search context."""
        self._stack = []
        # Connect to the signalling framework.
        request_finished.connect(self._request_finished_receiver)
    
    def is_active(self):
        """Checks that this search context is active."""
        return bool(self._stack)
    
    def _assert_active(self):
        """Ensures that the search context is active."""
        if not self.is_active():
            raise SearchContextError("The search context is not active.")
        
    def start(self):
        """Starts a level in the search context."""
        self._stack.append((set(), False))
    
    def add_to_context(self, engine, obj):
        """Adds an object to the current context, if active."""
        self._assert_active()
        objects, _ = self._stack[-1]
        objects.add((engine, obj))
    
    def invalidate(self):
        """Marks this search context as broken, so should not be commited."""
        self._assert_active()
        objects, _ = self._stack[-1]
        self._stack[-1] = (objects, True)
        
    def is_invalid(self):
        """Checks whether this search context is invalid."""
        self._assert_active()
        _, is_invalid = self._stack[-1]
        return is_invalid
    
    def end(self):
        """Ends a level in the search context."""
        self._assert_active()
        # Save all the models.
        tasks, is_invalid = self._stack.pop()
        if not is_invalid:
            _bulk_save_search_entries(list(chain.from_iterable(engine._update_obj_index_iter(obj) for engine, obj in tasks)))
    
    # Context management.
            
    def update_index(self):
        """
        Marks up a block of code as requiring the search indexes to be updated.
        
        The returned context manager can also be used as a decorator.
        """
        return SearchContext(self)
    
    # Signalling hooks.
        
    def _request_finished_receiver(self, **kwargs):
        """
        Called at the end of a request, ensuring that any open contexts
        are closed. Not closing all active contexts can cause memory leaks
        and weird behaviour.
        """
        while self.is_active():
            self.end()
            
            
class SearchContext(object):

    """An individual context for a search index update."""

    def __init__(self, context_manager):
        """Initializes the search index context."""
        self._context_manager = context_manager
    
    def __enter__(self):
        """Enters a block of search index management."""
        self._context_manager.start()
        
    def __exit__(self, exc_type, exc_value, traceback):
        """Leaves a block of search index management."""
        try:
            if exc_type is not None:
                self._context_manager.invalidate()
        finally:
            self._context_manager.end()
        
    def __call__(self, func):
        """Allows this search index context to be used as a decorator."""
        @wraps(func)
        def do_search_context(*args, **kwargs):
            self.__enter__()
            exception = False
            try:
                return func(*args, **kwargs)
            except:
                exception = True
                if not self.__exit__(*sys.exc_info()):
                    raise
            finally:
                if not exception:
                    self.__exit__(None, None, None)
        return do_search_context
        
            
# The shared, thread-safe search context manager.
search_context_manager = SearchContextManager()


class SearchEngine(object):

    """A search engine capable of performing multi-table searches."""
    
    _created_engines = WeakValueDictionary()
    
    @classmethod
    def get_created_engines(cls):
        """Returns all created search engines."""
        return list(cls._created_engines.items())
    
    def __init__(self, engine_slug, search_context_manager=search_context_manager):
        """Initializes the search engine."""
        # Check the slug is unique for this project.
        if engine_slug in SearchEngine._created_engines:
            raise SearchEngineError("A search engine has already been created with the slug {engine_slug!r}".format(
                engine_slug = engine_slug,
            ))
        # Initialize thie engine.
        self._registered_models = {}
        self._engine_slug = engine_slug
        # Store the search context.
        self._search_context_manager = search_context_manager
        # Store a reference to this engine.
        self.__class__._created_engines[engine_slug] = self

    def is_registered(self, model):
        """Checks whether the given model is registered with this search engine."""
        return model in self._registered_models

    def register(self, model, adapter_cls=SearchAdapter, **field_overrides):
        """
        Registers the given model with this search engine.
        
        If the given model is already registered with this search engine, a
        RegistrationError will be raised.
        """
        # Add in custom live filters.
        if isinstance(model, QuerySet):
            live_queryset = model
            model = model.model
            field_overrides["get_live_queryset"] = lambda self_: live_queryset.all()
        # Check for existing registration.
        if self.is_registered(model):
            raise RegistrationError("{model!r} is already registered with this search engine".format(
                model = model,
            ))
        # Perform any customization.
        if field_overrides:
            # Conversion to str is needed because Python 2 doesn't accept unicode for class name
            adapter_cls = type(str("Custom") + adapter_cls.__name__, (adapter_cls,), field_overrides)
        # Perform the registration.
        adapter_obj = adapter_cls(model)
        self._registered_models[model] = adapter_obj
        # Connect to the signalling framework.
        post_save.connect(self._post_save_receiver, model)
        pre_delete.connect(self._pre_delete_receiver, model)
    
    def unregister(self, model):
        """
        Unregisters the given model with this search engine.
        
        If the given model is not registered with this search engine, a RegistrationError
        will be raised.
        """
        # Add in custom live filters.
        if isinstance(model, QuerySet):
            model = model.model
        # Check for registration.
        if not self.is_registered(model):
            raise RegistrationError("{model!r} is not registered with this search engine".format(
                model = model,
            ))
        # Perform the unregistration.
        del self._registered_models[model]
        # Disconnect from the signalling framework.
        post_save.disconnect(self._post_save_receiver, model)
        pre_delete.disconnect(self._pre_delete_receiver, model)
        
    def get_registered_models(self):
        """Returns a sequence of models that have been registered with this search engine."""
        return list(self._registered_models.keys())
    
    def get_adapter(self, model):
        """Returns the adapter associated with the given model."""
        if self.is_registered(model):
            return self._registered_models[model]
        raise RegistrationError("{model!r} is not registered with this search engine".format(
            model = model,
        ))
    
    def _get_entries_for_obj(self, obj):
        """Returns a queryset of entries associate with the given obj."""
        model = obj.__class__
        content_type = ContentType.objects.get_for_model(model)
        object_id = force_text(obj.pk)
        # Get the basic list of search entries.
        search_entries = SearchEntry.objects.filter(
            content_type = content_type,
            engine_slug = self._engine_slug,
        )
        if has_int_pk(model):
            # Do a fast indexed lookup.
            object_id_int = int(obj.pk)
            search_entries = search_entries.filter(
                object_id_int = object_id_int,
            )
        else:
            # Alas, have to do a slow unindexed lookup.
            object_id_int = None
            search_entries = search_entries.filter(
                object_id = object_id,
            )
        return object_id_int, search_entries
    
    def _update_obj_index_iter(self, obj):
        """Either updates the given object index, or yields an unsaved search entry."""
        model = obj.__class__
        adapter = self.get_adapter(model)
        content_type = ContentType.objects.get_for_model(model)
        object_id = force_text(obj.pk)
        # Create the search entry data.
        search_entry_data = {
            "engine_slug": self._engine_slug,
            "title": adapter.get_title(obj),
            "description": adapter.get_description(obj),
            "content": adapter.get_content(obj),
            "url": adapter.get_url(obj),
            "meta_encoded": json.dumps(adapter.get_meta(obj)),
        }
        # Try to get the existing search entry.
        object_id_int, search_entries = self._get_entries_for_obj(obj)
        # Attempt to update the search entries.
        update_count = search_entries.update(**search_entry_data)
        if update_count == 0:
            # This is the first time the entry was created.
            search_entry_data.update((
                ("content_type", content_type),
                ("object_id", object_id),
                ("object_id_int", object_id_int),
            ))
            yield SearchEntry(**search_entry_data)
        elif update_count > 1:
            # Oh no! Somehow we've got duplicated search entries!
            search_entries.exclude(id=search_entries[0].id).delete()
    
    def update_obj_index(self, obj):
        """Updates the search index for the given obj."""
        _bulk_save_search_entries(list(self._update_obj_index_iter(obj)))
        
    # Signalling hooks.
            
    def _post_save_receiver(self, instance, **kwargs):
        """Signal handler for when a registered model has been saved."""
        if self._search_context_manager.is_active():
            self._search_context_manager.add_to_context(self, instance)
        else:
            self.update_obj_index(instance)
            
    def _pre_delete_receiver(self, instance, **kwargs):
        """Signal handler for when a registered model has been deleted."""
        _, search_entries = self._get_entries_for_obj(instance)
        search_entries.delete()
        
    # Searching.
    
    def _create_model_filter(self, models):
        """Creates a filter for the given model/queryset list."""
        filters = Q()
        for model in models:
            filter = Q()
            # Process querysets.
            if isinstance(model, QuerySet):
                sub_queryset = model
                model = model.model
                queryset = sub_queryset.values_list("pk", flat=True)
                if has_int_pk(model):
                    filter &= Q(
                        object_id_int__in = queryset,
                    )
                else:
                    live_ids = list(queryset)
                    if live_ids:
                        filter &= Q(
                            object_id__in = live_ids,
                        )
                    else:
                        # HACK: There is a bug in Django (https://code.djangoproject.com/ticket/15145) that messes up __in queries when the iterable is empty.
                        # This bit of nonsense ensures that this aspect of the query will be impossible to fulfill.
                        filter &= Q(
                            content_type = ContentType.objects.get_for_model(model).id + 1,
                        )
            # Add the model to the filter.
            content_type = ContentType.objects.get_for_model(model)
            filter &= Q(
                content_type = content_type,
            )
            # Combine with the other filters.
            filters |= filter
        return filters
    
    def _get_included_models(self, models):
        """Returns an iterable of models and querysets that should be included in the search query."""
        for model in models or self.get_registered_models():
            if isinstance(model, QuerySet):
                yield model
            else:
                adaptor = self.get_adapter(model)
                queryset = adaptor.get_live_queryset()
                if queryset is None:
                    yield model
                else:
                    yield queryset.all()
    
    def search(self, search_text, models=(), exclude=(), ranking=True):
        """Performs a search using the given text, returning a queryset of SearchEntry."""
        # Check for blank search text.
        search_text = search_text.strip()
        if not search_text:
            return SearchEntry.objects.none()
        # Get the initial queryset.
        queryset = SearchEntry.objects.filter(
            engine_slug = self._engine_slug,
        )
        # Process the allowed models.
        queryset = queryset.filter(
            self._create_model_filter(self._get_included_models(models))
        ).exclude(
            self._create_model_filter(exclude)
        )
        # Perform the backend-specific full text match.
        backend = get_backend()
        queryset = backend.do_search(self._engine_slug, queryset, search_text)
        # Perform the backend-specific full-text ranking.
        if ranking:
            queryset = backend.do_search_ranking(self._engine_slug, queryset, search_text)
        # Return the complete queryset.
        return queryset
        
    def filter(self, queryset, search_text, ranking=True):
        """
        Filters the given model or queryset using the given text, returning the
        modified queryset.
        """
        # If the queryset is a model, get all of them.
        if isinstance(queryset, type) and issubclass(queryset, models.Model):
            queryset = queryset._default_manager.all()
        # Check for blank search text.
        search_text = search_text.strip()
        if not search_text:
            return queryset
        # Perform the backend-specific full text match.
        backend = get_backend()
        queryset = backend.do_filter(self._engine_slug, queryset, search_text)
        # Perform the backend-specific full-text ranking.
        if ranking:
            queryset = backend.do_filter_ranking(self._engine_slug, queryset, search_text)
        # Return the complete queryset.
        return queryset


# The default search engine.
default_search_engine = SearchEngine("default")


# The cache for the initialized backend.
_backend_cache = None


def get_backend():
    """Initializes and returns the search backend."""
    global _backend_cache
    # Try to use the cached backend.
    if _backend_cache is not None:
        return _backend_cache
    # Load the backend class.
    backend_name = getattr(settings, "WATSON_BACKEND", "watson.backends.AdaptiveSearchBackend")
    backend_module_name, backend_cls_name = backend_name.rsplit(".", 1)
    backend_module = import_module(backend_module_name)
    try:
        backend_cls = getattr(backend_module, backend_cls_name)
    except AttributeError:
        raise ImproperlyConfigured("Could not find a class named {backend_module_name!r} in {backend_cls_name!r}".format(
            backend_module_name = backend_module_name,
            backend_cls_name = backend_cls_name,
        ))
    # Initialize the backend.
    backend = backend_cls()
    _backend_cache = backend
    return backend

########NEW FILE########
__FILENAME__ = watson
"""Template helpers used by watsons search."""

from __future__ import unicode_literals

from django import template


register = template.Library()


@register.simple_tag(takes_context=True)
def search_results(context, search_results):
    """Renders a list of search results."""
    # Prefetch related for speed, if available.
    if hasattr(search_results, "prefetch_related"):
        search_results = search_results.prefetch_related("object")
    # Render the template.
    context.push()
    try:
        context.update({
            "search_results": search_results,
            "query": context["query"],
        })
        return template.loader.render_to_string("watson/includes/search_results.html", context)
    finally:
        context.pop()
    
    
@register.simple_tag(takes_context=True)
def search_result_item(context, search_result):
    obj = search_result.object
    params = {
        "app_label": obj._meta.app_label,
        "model_name": obj.__class__.__name__.lower(),
    }
    # Render the template.
    context.push()
    try:
        context.update({
            "obj": obj,
            "result": search_result,
            "query": context["query"],
        })
        return template.loader.render_to_string((
            "watson/includes/search_result_{app_label}_{model_name}.html".format(**params),
            "watson/includes/search_result_{app_label}.html".format(**params),
            "watson/includes/search_result_item.html",
        ), context)
    finally:
        context.pop()

########NEW FILE########
__FILENAME__ = tests
"""
Tests for django-watson.

Fun fact: The MySQL full text search engine does not support indexing of words
that are 3 letters or fewer. Thus, the standard metasyntactic variables in
these tests have been amended to 'fooo' and 'baar'. Ho hum.
"""

from __future__ import unicode_literals

import os, json
try:
    from unittest import skipUnless
except:
    from django.utils.unittest import skipUnless

from django.db import models
from django.test import TestCase
from django.core.management import call_command
try:
    from django.conf.urls import *
except ImportError:  # Django<1.4
    from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.http import HttpResponseNotFound, HttpResponseServerError
from django import template
from django.utils.encoding import force_text

import watson
from watson.registration import RegistrationError, get_backend, SearchEngine
from watson.models import SearchEntry


class TestModelBase(models.Model):

    title = models.CharField(
        max_length = 200,
    )
    
    content = models.TextField(
        blank = True,
    )
    
    description = models.TextField(
        blank = True,
    )
    
    is_published = models.BooleanField(
        default = True,
    )
    
    def __unicode__(self):
        return self.title

    class Meta:
        abstract = True
        app_label = "auth"  # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
        
        
class WatsonTestModel1(TestModelBase):

    pass


str_pk_gen = 0;

def get_str_pk():
    global str_pk_gen
    str_pk_gen += 1;
    return str(str_pk_gen)
    
    
class WatsonTestModel2(TestModelBase):

    id = models.CharField(
        primary_key = True,
        max_length = 100,
        default = get_str_pk
    )


class RegistrationTest(TestCase):
    
    def testRegistration(self):
        # Register the model and test.
        watson.register(WatsonTestModel1)
        self.assertTrue(watson.is_registered(WatsonTestModel1))
        self.assertRaises(RegistrationError, lambda: watson.register(WatsonTestModel1))
        self.assertTrue(WatsonTestModel1 in watson.get_registered_models())
        self.assertTrue(isinstance(watson.get_adapter(WatsonTestModel1), watson.SearchAdapter))
        # Unregister the model and text.
        watson.unregister(WatsonTestModel1)
        self.assertFalse(watson.is_registered(WatsonTestModel1))
        self.assertRaises(RegistrationError, lambda: watson.unregister(WatsonTestModel1))
        self.assertTrue(WatsonTestModel1 not in watson.get_registered_models())
        self.assertRaises(RegistrationError, lambda: isinstance(watson.get_adapter(WatsonTestModel1)))


complex_registration_search_engine = SearchEngine("restricted")


class InstallUninstallTestBase(TestCase):

    def testUninstallAndInstall(self):
        # Not too much to test here, as some backends don't require installation.
        # Just make sure the commands don't error.
        call_command("uninstallwatson", verbosity=0)
        call_command("installwatson", verbosity=0)
        
    @skipUnless(get_backend().requires_installation, "search backend does not require installation")
    def testRealInstallAndUninstall(self):
        backend = get_backend()
        call_command("uninstallwatson", verbosity=0)
        self.assertFalse(backend.is_installed())
        call_command("installwatson", verbosity=0)
        self.assertTrue(backend.is_installed())


class SearchTestBase(TestCase):

    model1 = WatsonTestModel1
    
    model2 = WatsonTestModel2

    def setUp(self):
        # If migrations are off, then this is needed to get the indices installed. It has to
        # be called in the setUp() method, but multiple invocations should be safe.
        call_command("installwatson", verbosity=0)
        # Remove all the current registered models.
        self.registered_models = watson.get_registered_models()
        for model in self.registered_models:
            watson.unregister(model)
        # Register the test models.
        watson.register(self.model1)
        watson.register(self.model2, exclude=("id",))
        complex_registration_search_engine.register(WatsonTestModel1, exclude=("content", "description",), store=("is_published",))
        complex_registration_search_engine.register(WatsonTestModel2, fields=("title",))
        # Create some test models.
        self.test11 = WatsonTestModel1.objects.create(
            title = "title model1 instance11",
            content = "content model1 instance11",
            description = "description model1 instance11",
        )
        self.test12 = WatsonTestModel1.objects.create(
            title = "title model1 instance12",
            content = "content model1 instance12",
            description = "description model1 instance12",
        )
        self.test21 = WatsonTestModel2.objects.create(
            title = "title model2 instance21",
            content = "content model2 instance21",
            description = "description model2 instance21",
        )
        self.test22 = WatsonTestModel2.objects.create(
            title = "title model2 instance22",
            content = "content model2 instance22",
            description = "description model2 instance22",
        )

    def tearDown(self):
        # Re-register the old registered models.
        for model in self.registered_models:
            watson.register(model)
        # Unregister the test models.
        watson.unregister(self.model1)
        watson.unregister(self.model2)
        complex_registration_search_engine.unregister(WatsonTestModel1)
        complex_registration_search_engine.unregister(WatsonTestModel2)
        # Delete the test models.
        WatsonTestModel1.objects.all().delete()
        WatsonTestModel2.objects.all().delete()
        del self.test11
        del self.test12
        del self.test21
        del self.test22
        # Delete the search index.
        SearchEntry.objects.all().delete()


class InternalsTest(SearchTestBase):

    def testSearchEntriesCreated(self):
        self.assertEqual(SearchEntry.objects.filter(engine_slug="default").count(), 4)

    def testBuildWatsonForModelCommand(self):
        # Hack a change into the model using a bulk update, which doesn't send signals.
        WatsonTestModel1.objects.filter(id=self.test11.id).update(title="fooo1_selective")
        WatsonTestModel2.objects.filter(id=self.test21.id).update(title="fooo2_selective")
        # Test that no update has happened.
        self.assertEqual(watson.search("fooo1_selective").count(), 0)
        self.assertEqual(watson.search("fooo2_selective").count(), 0)
        # Run the rebuild command.
        call_command("buildwatson", "WatsonTestModel1", verbosity=0)
        # Test that the update is now applied to selected model.
        self.assertEqual(watson.search("fooo1_selective").count(), 1)
        self.assertEqual(watson.search("fooo2_selective").count(), 0)
        call_command("buildwatson", "WatsonTestModel1", "WatsonTestModel2", verbosity=0)
        # Test that the update is now applied to multiple selected models.
        self.assertEqual(watson.search("fooo1_selective").count(), 1)
        self.assertEqual(watson.search("fooo2_selective").count(), 1)

    def testBuildWatsonCommand(self):
        # Hack a change into the model using a bulk update, which doesn't send signals.
        WatsonTestModel1.objects.filter(id=self.test11.id).update(title="fooo1")
        WatsonTestModel2.objects.filter(id=self.test21.id).update(title="fooo2")
        # Test that no update has happened.
        self.assertEqual(watson.search("fooo1").count(), 0)
        self.assertEqual(watson.search("fooo2").count(), 0)
        # Run the rebuild command.
        call_command("buildwatson", verbosity=0)
        # Test that the update is now applied.
        self.assertEqual(watson.search("fooo1").count(), 1)
        self.assertEqual(watson.search("fooo2").count(), 1)

    def testUpdateSearchIndex(self):
        # Update a model and make sure that the search results match.
        self.test11.title = "fooo"
        self.test11.save()
        # Test a search that should get one model.
        exact_search = watson.search("fooo")
        self.assertEqual(len(exact_search), 1)
        self.assertEqual(exact_search[0].title, "fooo")
        # Delete a model and make sure that the search results match.
        self.test11.delete()
        self.assertEqual(watson.search("fooo").count(), 0)
    
    def testSearchIndexUpdateDeferredByContext(self):
        with watson.update_index():
            self.test11.title = "fooo"
            self.test11.save()
            self.assertEqual(watson.search("fooo").count(), 0)
        self.assertEqual(watson.search("fooo").count(), 1)
    
    def testSearchIndexUpdateAbandonedOnError(self):
        try:
            with watson.update_index():
                self.test11.title = "fooo"
                self.test11.save()
                raise Exception("Foo")
        except:
            pass
        # Test a search that should get not model.
        self.assertEqual(watson.search("fooo").count(), 0)
        
    def testFixesDuplicateSearchEntries(self):
        search_entries = SearchEntry.objects.filter(engine_slug="default")
        # Duplicate a couple of search entries.
        for search_entry in search_entries.all()[:2]:
            search_entry.id = None
            search_entry.save()
        # Make sure that we have six (including duplicates).
        self.assertEqual(search_entries.all().count(), 6)
        # Run the rebuild command.
        call_command("buildwatson", verbosity=0)
        # Make sure that we have four again (including duplicates).
        self.assertEqual(search_entries.all().count(), 4)
    
    def testEmptyFilterGivesAllResults(self):
        for model in (WatsonTestModel1, WatsonTestModel2):
            self.assertEqual(watson.filter(model, "").count(), 2)
            self.assertEqual(watson.filter(model, " ").count(), 2)
        
    def testFilter(self):
        for model in (WatsonTestModel1, WatsonTestModel2):
            # Test can find all.
            self.assertEqual(watson.filter(model, "TITLE").count(), 2)
        # Test can find a specific one.
        obj = watson.filter(WatsonTestModel1, "INSTANCE12").get()
        self.assertTrue(isinstance(obj, WatsonTestModel1))
        self.assertEqual(obj.title, "title model1 instance12")
        # Test can do filter on a queryset.
        obj = watson.filter(WatsonTestModel1.objects.filter(title__icontains="TITLE"), "INSTANCE12").get()
        self.assertTrue(isinstance(obj, WatsonTestModel1))
        self.assertEqual(obj.title, "title model1 instance12")
    
    @skipUnless(get_backend().supports_prefix_matching, "Search backend does not support prefix matching.")    
    def testPrefixFilter(self):
        self.assertEqual(watson.filter(WatsonTestModel1, "INSTAN").count(), 2)
        
        
class SearchTest(SearchTestBase):
    
    def emptySearchTextGivesNoResults(self):
        self.assertEqual(watson.search("").count(), 0)
        self.assertEqual(watson.search(" ").count(), 0)        
    
    def testMultiTableSearch(self):
        # Test a search that should get all models.
        self.assertEqual(watson.search("TITLE").count(), 4)
        self.assertEqual(watson.search("CONTENT").count(), 4)
        self.assertEqual(watson.search("DESCRIPTION").count(), 4)
        self.assertEqual(watson.search("TITLE CONTENT DESCRIPTION").count(), 4)
        # Test a search that should get two models.
        self.assertEqual(watson.search("MODEL1").count(), 2)
        self.assertEqual(watson.search("MODEL2").count(), 2)
        self.assertEqual(watson.search("TITLE MODEL1").count(), 2)
        self.assertEqual(watson.search("TITLE MODEL2").count(), 2)
        # Test a search that should get one model.
        self.assertEqual(watson.search("INSTANCE11").count(), 1)
        self.assertEqual(watson.search("INSTANCE21").count(), 1)
        self.assertEqual(watson.search("TITLE INSTANCE11").count(), 1)
        self.assertEqual(watson.search("TITLE INSTANCE21").count(), 1)
        # Test a search that should get zero models.
        self.assertEqual(watson.search("FOOO").count(), 0)
        self.assertEqual(watson.search("FOOO INSTANCE11").count(), 0)
        self.assertEqual(watson.search("MODEL2 INSTANCE11").count(), 0)

    def testSearchWithApostrophe(self):
        WatsonTestModel1.objects.create(
            title = "title model1 instance12",
            content = "content model1 instance13 d'Argent",
            description = "description model1 instance13",
        )
        self.assertEqual(watson.search("d'Argent").count(), 1)
        
    @skipUnless(get_backend().supports_prefix_matching, "Search backend does not support prefix matching.")
    def testMultiTablePrefixSearch(self):
        self.assertEqual(watson.search("DESCR").count(), 4)
    
    def testLimitedModelList(self):
        # Test a search that should get all models.
        self.assertEqual(watson.search("TITLE", models=(WatsonTestModel1, WatsonTestModel2)).count(), 4)
        # Test a search that should get two models.
        self.assertEqual(watson.search("MODEL1", models=(WatsonTestModel1, WatsonTestModel2)).count(), 2)
        self.assertEqual(watson.search("MODEL1", models=(WatsonTestModel1,)).count(), 2)
        self.assertEqual(watson.search("MODEL2", models=(WatsonTestModel1, WatsonTestModel2)).count(), 2)
        self.assertEqual(watson.search("MODEL2", models=(WatsonTestModel2,)).count(), 2)
        # Test a search that should get one model.
        self.assertEqual(watson.search("INSTANCE11", models=(WatsonTestModel1, WatsonTestModel2)).count(), 1)
        self.assertEqual(watson.search("INSTANCE11", models=(WatsonTestModel1,)).count(), 1)
        self.assertEqual(watson.search("INSTANCE21", models=(WatsonTestModel1, WatsonTestModel2,)).count(), 1)
        self.assertEqual(watson.search("INSTANCE21", models=(WatsonTestModel2,)).count(), 1)
        # Test a search that should get zero models.
        self.assertEqual(watson.search("MODEL1", models=(WatsonTestModel2,)).count(), 0)
        self.assertEqual(watson.search("MODEL2", models=(WatsonTestModel1,)).count(), 0)
        self.assertEqual(watson.search("INSTANCE21", models=(WatsonTestModel1,)).count(), 0)
        self.assertEqual(watson.search("INSTANCE11", models=(WatsonTestModel2,)).count(), 0)
        
    def testExcludedModelList(self):
        # Test a search that should get all models.
        self.assertEqual(watson.search("TITLE", exclude=()).count(), 4)
        # Test a search that should get two models.
        self.assertEqual(watson.search("MODEL1", exclude=()).count(), 2)
        self.assertEqual(watson.search("MODEL1", exclude=(WatsonTestModel2,)).count(), 2)
        self.assertEqual(watson.search("MODEL2", exclude=()).count(), 2)
        self.assertEqual(watson.search("MODEL2", exclude=(WatsonTestModel1,)).count(), 2)
        # Test a search that should get one model.
        self.assertEqual(watson.search("INSTANCE11", exclude=()).count(), 1)
        self.assertEqual(watson.search("INSTANCE11", exclude=(WatsonTestModel2,)).count(), 1)
        self.assertEqual(watson.search("INSTANCE21", exclude=()).count(), 1)
        self.assertEqual(watson.search("INSTANCE21", exclude=(WatsonTestModel1,)).count(), 1)
        # Test a search that should get zero models.
        self.assertEqual(watson.search("MODEL1", exclude=(WatsonTestModel1,)).count(), 0)
        self.assertEqual(watson.search("MODEL2", exclude=(WatsonTestModel2,)).count(), 0)
        self.assertEqual(watson.search("INSTANCE21", exclude=(WatsonTestModel2,)).count(), 0)
        self.assertEqual(watson.search("INSTANCE11", exclude=(WatsonTestModel1,)).count(), 0)

    def testLimitedModelQuerySet(self):
        # Test a search that should get all models.
        self.assertEqual(watson.search("TITLE", models=(WatsonTestModel1.objects.filter(title__icontains="TITLE"), WatsonTestModel2.objects.filter(title__icontains="TITLE"),)).count(), 4)
        # Test a search that should get two models.
        self.assertEqual(watson.search("MODEL1", models=(WatsonTestModel1.objects.filter(
            title__icontains = "MODEL1",
            description__icontains = "MODEL1",
        ),)).count(), 2)
        self.assertEqual(watson.search("MODEL2", models=(WatsonTestModel2.objects.filter(
            title__icontains = "MODEL2",
            description__icontains = "MODEL2",
        ),)).count(), 2)
        # Test a search that should get one model.
        self.assertEqual(watson.search("INSTANCE11", models=(WatsonTestModel1.objects.filter(
            title__icontains = "MODEL1",
        ),)).count(), 1)
        self.assertEqual(watson.search("INSTANCE21", models=(WatsonTestModel2.objects.filter(
            title__icontains = "MODEL2",
        ),)).count(), 1)
        # Test a search that should get no models.
        self.assertEqual(watson.search("INSTANCE11", models=(WatsonTestModel1.objects.filter(
            title__icontains = "MODEL2",
        ),)).count(), 0)
        self.assertEqual(watson.search("INSTANCE21", models=(WatsonTestModel2.objects.filter(
            title__icontains = "MODEL1",
        ),)).count(), 0)
        
    def testExcludedModelQuerySet(self):
        # Test a search that should get all models.
        self.assertEqual(watson.search("TITLE", exclude=(WatsonTestModel1.objects.filter(title__icontains="FOOO"), WatsonTestModel2.objects.filter(title__icontains="FOOO"),)).count(), 4)
        # Test a search that should get two models.
        self.assertEqual(watson.search("MODEL1", exclude=(WatsonTestModel1.objects.filter(
            title__icontains = "INSTANCE21",
            description__icontains = "INSTANCE22",
        ),)).count(), 2)
        self.assertEqual(watson.search("MODEL2", exclude=(WatsonTestModel2.objects.filter(
            title__icontains = "INSTANCE11",
            description__icontains = "INSTANCE12",
        ),)).count(), 2)
        # Test a search that should get one model.
        self.assertEqual(watson.search("INSTANCE11", exclude=(WatsonTestModel1.objects.filter(
            title__icontains = "MODEL2",
        ),)).count(), 1)
        self.assertEqual(watson.search("INSTANCE21", exclude=(WatsonTestModel2.objects.filter(
            title__icontains = "MODEL1",
        ),)).count(), 1)
        # Test a search that should get no models.
        self.assertEqual(watson.search("INSTANCE11", exclude=(WatsonTestModel1.objects.filter(
            title__icontains = "MODEL1",
        ),)).count(), 0)
        self.assertEqual(watson.search("INSTANCE21", exclude=(WatsonTestModel2.objects.filter(
            title__icontains = "MODEL2",
        ),)).count(), 0)
        
    def testKitchenSink(self):
        """For sanity, let's just test everything together in one giant search of doom!"""
        self.assertEqual(watson.search(
            "INSTANCE11",
            models = (
                WatsonTestModel1.objects.filter(title__icontains="INSTANCE11"),
                WatsonTestModel2.objects.filter(title__icontains="TITLE"),
            ),
            exclude = (
                WatsonTestModel1.objects.filter(title__icontains="MODEL2"),
                WatsonTestModel2.objects.filter(title__icontains="MODEL1"),
            )
        ).get().title, "title model1 instance11")
        
        
class LiveFilterSearchTest(SearchTest):
    
    model1 = WatsonTestModel1.objects.filter(is_published=True)
    
    model2 = WatsonTestModel2.objects.filter(is_published=True)
    
    def testUnpublishedModelsNotFound(self):
        # Make sure that there are four to find!
        self.assertEqual(watson.search("tItle Content Description").count(), 4)
        # Unpublish two objects.
        self.test11.is_published = False
        self.test11.save()
        self.test21.is_published = False
        self.test21.save()
        # This should return 4, but two of them are unpublished.
        self.assertEqual(watson.search("tItle Content Description").count(), 2)
        
    def testCanOverridePublication(self):
        # Unpublish two objects.
        self.test11.is_published = False
        self.test11.save()
        # This should still return 4, since we're overriding the publication.
        self.assertEqual(watson.search("tItle Content Description", models=(WatsonTestModel2, WatsonTestModel1._base_manager.all(),)).count(), 4)
        
        
class RankingTest(SearchTestBase):

    def setUp(self):
        super(RankingTest, self).setUp()
        self.test11.title += " fooo baar fooo"
        self.test11.save()
        self.test12.content += " fooo baar"
        self.test12.save()

    def testRankingParamPresentOnSearch(self):
        self.assertGreater(watson.search("TITLE")[0].watson_rank, 0)
        
    def testRankingParamPresentOnFilter(self):
        self.assertGreater(watson.filter(WatsonTestModel1, "TITLE")[0].watson_rank, 0)
        
    def testRankingParamAbsentOnSearch(self):
        self.assertRaises(AttributeError, lambda: watson.search("TITLE", ranking=False)[0].watson_rank)
        
    def testRankingParamAbsentOnFilter(self):
        self.assertRaises(AttributeError, lambda: watson.filter(WatsonTestModel1, "TITLE", ranking=False)[0].watson_rank)
    
    @skipUnless(get_backend().supports_ranking, "search backend does not support ranking")
    def testRankingWithSearch(self):
        self.assertEqual(
            [entry.title for entry in watson.search("FOOO")],
            ["title model1 instance11 fooo baar fooo", "title model1 instance12"]
        )
            
    @skipUnless(get_backend().supports_ranking, "search backend does not support ranking")
    def testRankingWithFilter(self):
        self.assertEqual(
            [entry.title for entry in watson.filter(WatsonTestModel1, "FOOO")],
            ["title model1 instance11 fooo baar fooo", "title model1 instance12"]
        )


class ComplexRegistrationTest(SearchTestBase):

    def testMetaStored(self):
        self.assertEqual(complex_registration_search_engine.search("instance11")[0].meta["is_published"], True)
        
    def testMetaNotStored(self):
        self.assertRaises(KeyError, lambda: complex_registration_search_engine.search("instance21")[0].meta["is_published"])
        
    def testFieldsExcludedOnSearch(self):
        self.assertEqual(complex_registration_search_engine.search("TITLE").count(), 4)
        self.assertEqual(complex_registration_search_engine.search("CONTENT").count(), 0)
        self.assertEqual(complex_registration_search_engine.search("DESCRIPTION").count(), 0)
        
    def testFieldsExcludedOnFilter(self):
        self.assertEqual(complex_registration_search_engine.filter(WatsonTestModel1, "TITLE").count(), 2)
        self.assertEqual(complex_registration_search_engine.filter(WatsonTestModel1, "CONTENT").count(), 0)
        self.assertEqual(complex_registration_search_engine.filter(WatsonTestModel1, "DESCRIPTION").count(), 0)
        self.assertEqual(complex_registration_search_engine.filter(WatsonTestModel2, "TITLE").count(), 2)
        self.assertEqual(complex_registration_search_engine.filter(WatsonTestModel2, "CONTENT").count(), 0)
        self.assertEqual(complex_registration_search_engine.filter(WatsonTestModel2, "DESCRIPTION").count(), 0)


class WatsonTestModel1Admin(watson.SearchAdmin):

    search_fields = ("title", "description", "content",)
    
    list_display = ("title",)
    
    
admin.site.register(WatsonTestModel1, WatsonTestModel1Admin)


urlpatterns = patterns("",

    url("^simple/", include("watson.urls")),
    
    url("^custom/", include("watson.urls"), kwargs={
        "query_param": "fooo",
        "empty_query_redirect": "/simple/",
        "extra_context": {
            "foo": "bar",
            "foo2": lambda: "bar2",
        },
        "paginate_by": 10,
    }),
    
    url("^admin/", include(admin.site.urls)),

)


def handler404(request):
    return HttpResponseNotFound("Not found")
    
    
def handler500(request):
    return HttpResponseServerError("Server error")


class AdminIntegrationTest(SearchTestBase):

    urls = "watson.tests"
    
    def setUp(self):
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(admin.__file__), "templates"),
        )
        super(AdminIntegrationTest, self).setUp()
        self.user = User(
            username = "foo",
            is_staff = True,
            is_superuser = True,
        )
        self.user.set_password("bar")
        self.user.save()
    
    @skipUnless("django.contrib.admin" in settings.INSTALLED_APPS, "Django admin site not installed")
    def testAdminIntegration(self):
        # Log the user in.
        if hasattr(self, "settings"):
            with self.settings(INSTALLED_APPS=tuple(set(tuple(settings.INSTALLED_APPS) + ("django.contrib.sessions",)))):  # HACK: Without this the client won't log in, for some reason.
                self.client.login(
                    username = "foo",
                    password = "bar",
                )
        else:
            self.client.login(
                username = "foo",
                password = "bar",
            )
        # Test a search with no query.
        response = self.client.get("/admin/auth/watsontestmodel1/")
        self.assertContains(response, "instance11")
        self.assertContains(response, "instance12")
        self.assertContains(response, "searchbar")  # Ensure that the search bar renders.
        # Test a search for all the instances.
        response = self.client.get("/admin/auth/watsontestmodel1/?q=title content description")
        self.assertContains(response, "instance11")
        self.assertContains(response, "instance12")
        # Test a search for half the instances.
        response = self.client.get("/admin/auth/watsontestmodel1/?q=instance11")
        self.assertContains(response, "instance11")
        self.assertNotContains(response, "instance12")
        
    def tearDown(self):
        super(AdminIntegrationTest, self).tearDown()
        self.user.delete()
        del self.user
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS
        
        
class SiteSearchTest(SearchTestBase):

    urls = "watson.tests"
    
    def setUp(self):
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(admin.__file__), "templates"),
        )
        super(SiteSearchTest, self).setUp()
    
    def testSiteSearch(self):
        # Test a search than should find everything.
        response = self.client.get("/simple/?q=title")
        self.assertContains(response, "instance11")
        self.assertContains(response, "instance12")
        self.assertContains(response, "instance21")
        self.assertContains(response, "instance22")
        self.assertTemplateUsed(response, "watson/search_results.html")
        # Test a search that should find one thing.
        response = self.client.get("/simple/?q=instance11")
        self.assertContains(response, "instance11")
        self.assertNotContains(response, "instance12")
        self.assertNotContains(response, "instance21")
        self.assertNotContains(response, "instance22")
        # Test a search that should find nothing.
        response = self.client.get("/simple/?q=fooo")
        self.assertNotContains(response, "instance11")
        self.assertNotContains(response, "instance12")
        self.assertNotContains(response, "instance21")
        self.assertNotContains(response, "instance22")
        
    def testSiteSearchJSON(self):
        # Test a search that should find everything.
        response = self.client.get("/simple/json/?q=title")
        self.assertEqual(response["Content-Type"], "application/json; charset=utf-8")
        results = set(result["title"] for result in json.loads(force_text(response.content))["results"])
        self.assertEqual(len(results), 4)
        self.assertTrue("title model1 instance11" in results)
        self.assertTrue("title model1 instance12" in results)
        self.assertTrue("title model2 instance21" in results)
        self.assertTrue("title model2 instance22" in results)
        
    def testSiteSearchCustom(self):
        # Test a search than should find everything.
        response = self.client.get("/custom/?fooo=title")
        self.assertContains(response, "instance11")
        self.assertContains(response, "instance12")
        self.assertContains(response, "instance21")
        self.assertContains(response, "instance22")
        self.assertTemplateUsed(response, "watson/search_results.html")
        # Test that the extra context is included.
        self.assertEqual(response.context["foo"], "bar")
        self.assertEqual(response.context["foo2"], "bar2")
        # Test that pagination is included.
        self.assertEqual(response.context["paginator"].num_pages, 1)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(response.context["search_results"], response.context["page_obj"].object_list)
        # Test a request for an empty page.
        try:
            response = self.client.get("/custom/?fooo=title&page=10")
        except template.TemplateDoesNotExist as ex:
            # No 404 template defined.
            self.assertEqual(ex.args[0], "404.html")
        else:
            self.assertEqual(response.status_code, 404)
        # Test a requet for the last page.
        response = self.client.get("/custom/?fooo=title&page=last")
        self.assertEqual(response.context["paginator"].num_pages, 1)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(response.context["search_results"], response.context["page_obj"].object_list)
        # Test a search that should find nothing.
        response = self.client.get("/custom/?q=fooo")
        self.assertRedirects(response, "/simple/")
        
    def testSiteSearchCustomJSON(self):
        # Test a search that should find everything.
        response = self.client.get("/custom/json/?fooo=title&page=last")
        self.assertEqual(response["Content-Type"], "application/json; charset=utf-8")
        results = set(result["title"] for result in json.loads(force_text(response.content))["results"])
        self.assertEqual(len(results), 4)
        self.assertTrue("title model1 instance11" in results)
        self.assertTrue("title model1 instance12" in results)
        self.assertTrue("title model2 instance21" in results)
        self.assertTrue("title model2 instance22" in results)
        # Test a search with an invalid page.
        response = self.client.get("/custom/json/?fooo=title&page=200")
        self.assertEqual(response.status_code, 404)
        
    def tearDown(self):
        super(SiteSearchTest, self).tearDown()
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS

########NEW FILE########
__FILENAME__ = urls
"""URLs for the built-in site search functionality."""

from __future__ import unicode_literals

try:
    from django.conf.urls import *
except ImportError:  # Django<1.4
    from django.conf.urls.defaults import *


urlpatterns = patterns("watson.views",

    url("^$", "search", name="search"),
    
    url("^json/$", "search_json", name="search_json"),

)

########NEW FILE########
__FILENAME__ = views
"""Views used by the built-in site search functionality."""

from __future__ import unicode_literals

import json

from django.shortcuts import redirect
from django.http import HttpResponse
from django.utils import six
from django.views import generic
from django.views.generic.list import BaseListView

import watson


class SearchMixin(object):
    
    """Base mixin for search views."""
    
    context_object_name = "search_results"
    
    query_param = "q"
    
    def get_query_param(self):
        """Returns the query parameter to use in the request GET dictionary."""
        return self.query_param
    
    models = ()
    
    def get_models(self):
        """Returns the models to use in the query."""
        return self.models 
    
    exclude = ()
    
    def get_exclude(self):
        """Returns the models to exclude from the query."""
        return self.exclude
    
    def get_queryset(self):
        """Returns the initial queryset."""
        return watson.search(self.query, models=self.get_models(), exclude=self.get_exclude())
    
    def get_query(self, request):
        """Parses the query from the request."""
        return request.GET.get(self.get_query_param(), "").strip()
    
    empty_query_redirect = None
    
    def get_empty_query_redirect(self):
        """Returns the URL to redirect an empty query to, or None."""
        return self.empty_query_redirect
    
    extra_context = {}
    
    def get_extra_context(self):
        """
        Returns any extra context variables.
        
        Required for backwards compatibility with old function-based views.
        """
        return self.extra_context
    
    def get_context_data(self, **kwargs):
        """Generates context variables."""
        context = super(SearchMixin, self).get_context_data(**kwargs)
        context["query"] = self.query
        # Process extra context.
        for key, value in six.iteritems(self.get_extra_context()):
            if callable(value):
                value = value()
            context[key] = value
        return context
    
    def get(self, request):
        """Performs a GET request."""
        self.query = self.get_query(request)
        if not self.query:
            empty_query_redirect = self.get_empty_query_redirect()
            if empty_query_redirect:
                return redirect(empty_query_redirect)
        return super(SearchMixin, self).get(request)


class SearchView(SearchMixin, generic.ListView):
    
    """View that performs a search and returns the search results."""
    
    template_name = "watson/search_results.html"
    
    
class SearchApiView(SearchMixin, BaseListView):
    
    """A JSON-based search API."""
    
    def render_to_response(self, context, **response_kwargs):
        """Renders the search results to the response."""
        content = json.dumps({
            "results": [
                {
                    "title": result.title,
                    "description": result.description,
                    "url": result.url,
                    "meta": result.meta,
                } for result in context[self.get_context_object_name(self.get_queryset())]
            ]
        }).encode("utf-8")
        # Generate the response.
        response = HttpResponse(content, **response_kwargs)
        response["Content-Type"] = "application/json; charset=utf-8"
        response["Content-Length"] = len(content)
        return response


# Older function-based views.

def search(request, **kwargs):
    """Renders a page of search results."""
    return SearchView.as_view(**kwargs)(request)
    
    
def search_json(request, **kwargs):
    """Renders a JSON representation of matching search entries."""
    return SearchApiView.as_view(**kwargs)(request)

########NEW FILE########
