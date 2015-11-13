__FILENAME__ = runtests
#!/usr/bin/env python
import sys

from os.path import dirname, abspath

from django.conf import settings

if not settings.configured:
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        DATABASE_NAME='test.db',
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'taggit',
            'taggit_suggest',
        ]
    )

from django.test.simple import run_tests


def runtests(*test_args):
    if not test_args:
        test_args = ['taggit_suggest']
    parent = dirname(abspath(__file__))
    sys.path.insert(0, parent)
    failures = run_tests(test_args, verbosity=1, interactive=True)
    sys.exit(failures)


if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from taggit.admin import TaggedItemInline
from taggit_suggest.models import TagKeyword, TagRegex
from taggit.models import Tag


class TagKeywordInline(admin.StackedInline):
    model = TagKeyword


class TagRegxInline(admin.StackedInline):
    model = TagRegex


class TagSuggestAdmin(admin.ModelAdmin):
    inlines = [
        TaggedItemInline,
        TagKeywordInline,
        TagRegxInline,
    ]


admin.site.unregister(Tag)
admin.site.register(Tag, TagSuggestAdmin)

########NEW FILE########
__FILENAME__ = models
import re

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from taggit.models import Tag

try:
    import Stemmer
except ImportError:
    Stemmer = None


class TagKeyword(models.Model):
    """
    Model to associate simple keywords to a Tag
    """
    tag = models.ForeignKey(Tag, related_name='tkeywords')
    keyword = models.CharField(max_length=30)
    stem = models.CharField(max_length=30)

    def __unicode__(self):
        return "Keyword '%s' for Tag '%s'" % (self.keyword, self.tag.name)

    def save(self, *args, **kwargs):
        """
        Stem the keyword on save if they have PyStemmer
        """
        language = kwargs.pop('stemmer-language', 'english')
        if not self.pk and not self.stem and Stemmer:
            stemmer = Stemmer.Stemmer(language)
            self.stem = stemmer.stemWord(self.keyword)
        super(TagKeyword, self).save(*args, **kwargs)


def validate_regex(value):
    """
    Make sure we have a valid regular expression
    """
    try:
        re.compile(value)
    except Exception:
        # TODO: more restrictive in the exceptions
        raise ValidationError('Please enter a valid regular expression')


class TagRegex(models.Model):
    """
    Model to associate regular expressions with a Tag
    """
    tag = models.ForeignKey(Tag, related_name='tregexes')
    name = models.CharField(max_length=30)
    regex = models.CharField(
        max_length=250,
         validators=[validate_regex],
         help_text=_('Enter a valid Regular Expression. To make it '
            'case-insensitive include "(?i)" in your expression.')
     )

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Make sure to validate
        """
        self.full_clean()
        super(TagRegex, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = tests
from django.core.exceptions import ValidationError
from django.test import TestCase

from taggit_suggest.models import TagKeyword, TagRegex
from taggit_suggest.utils import suggest_tags
from taggit.models import Tag


class SuggestCase(TestCase):
    def test_simple_suggest(self):
        ku_tag = Tag.objects.create(name='ku')
        TagKeyword.objects.create(
            tag=ku_tag,
            keyword='kansas university'
        )

        suggested_tags = suggest_tags('I used to be a student at kansas university')
        self.assertTrue(ku_tag in suggested_tags)

    def test_regex_suggest(self):
        ku_tag = Tag.objects.create(name='ku')
        TagRegex.objects.create(
            tag=ku_tag,
            name='Find University of Kansas',
            regex='University\s+of\s+Kansas'
        )

        suggested_tags = suggest_tags('I was once a student at the University of Kansas')

        self.assertTrue(ku_tag in suggested_tags)

    def test_bad_regex(self):
        ku_tag = Tag.objects.create(name='ku')
        TagKeyword.objects.create(
            tag=ku_tag,
            keyword='kansas university'
        )
        new_regex = TagRegex(
            tag=ku_tag,
            name='Find University of Kansas',
            regex='University\s+of(\s+Kansas'
        )
        self.assertRaises(ValidationError, new_regex.save)

        suggested_tags = suggest_tags('I was once a student at the University '
            'of Kansas. Also known as kansas university by the way.')

        self.assertTrue(ku_tag in suggested_tags)

########NEW FILE########
__FILENAME__ = utils
import re

from taggit_suggest.models import TagKeyword, TagRegex
from taggit.models import Tag


def _suggest_keywords(content):
    """
    Suggest by keywords
    """
    suggested_keywords = set()
    keywords = TagKeyword.objects.all()

    for k in keywords:
        # Use the stem if available, otherwise use the whole keyword
        if k.stem:
            if k.stem in content:
                suggested_keywords.add(k.tag_id)
        elif k.keyword in content:
            suggested_keywords.add(k.tag_id)

    return suggested_keywords

def _suggest_regexes(content):
    """
    Suggest by regular expressions
    """
    # Grab all regular expressions and compile them
    suggested_regexes = set()
    regex_keywords = TagRegex.objects.all()

    # Look for our regular expressions in the content
    for r in regex_keywords:
        if re.search(r.regex, content):
            suggested_regexes.add(r.tag_id)

    return suggested_regexes

def suggest_tags(content):
    """
    Suggest tags based on text content
    """
    suggested_keywords = _suggest_keywords(content)
    suggested_regexes  = _suggest_regexes(content)
    suggested_tag_ids  = suggested_keywords | suggested_regexes

    return Tag.objects.filter(id__in=suggested_tag_ids)

########NEW FILE########
