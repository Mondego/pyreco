__FILENAME__ = base
from brabeion.models import BadgeAward
from brabeion.signals import badge_awarded



class BadgeAwarded(object):
    def __init__(self, level=None, user=None):
        self.level = level
        self.user = user


class BadgeDetail(object):
    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description


class Badge(object):
    async = False
    
    def __init__(self):
        assert not (self.multiple and len(self.levels) > 1)
        for i, level in enumerate(self.levels):
            if not isinstance(level, BadgeDetail):
                self.levels[i] = BadgeDetail(level)
    
    def possibly_award(self, **state):
        """
        Will see if the user should be awarded a badge.  If this badge is
        asynchronous it just queues up the badge awarding.
        """
        assert "user" in state
        if self.async:
            from brabeion.tasks import AsyncBadgeAward
            state = self.freeze(**state)
            AsyncBadgeAward.delay(self, state)
            return
        self.actually_possibly_award(**state)
    
    def actually_possibly_award(self, **state):
        """
        Does the actual work of possibly awarding a badge.
        """
        user = state["user"]
        force_timestamp = state.pop("force_timestamp", None)
        awarded = self.award(**state)
        if awarded is None:
            return
        if awarded.level is None:
            assert len(self.levels) == 1
            awarded.level = 1
        # awarded levels are 1 indexed, for conveineince
        awarded = awarded.level - 1
        assert awarded < len(self.levels)
        if (not self.multiple and
            BadgeAward.objects.filter(user=user, slug=self.slug, level=awarded)):
            return
        extra_kwargs = {}
        if force_timestamp is not None:
            extra_kwargs["awarded_at"] = force_timestamp
        badge = BadgeAward.objects.create(user=user, slug=self.slug,
            level=awarded, **extra_kwargs)
        badge_awarded.send(sender=self, badge_award=badge)
    
    def freeze(self, **state):
        return state


def send_badge_messages(badge_award, **kwargs):
    """
    If the Badge class defines a message, send it to the user who was just
    awarded the badge.
    """
    user_message = getattr(badge_award.badge, "user_message", None)
    if callable(user_message):
        message = user_message(badge_award)
    else:
        message = user_message
    if message is not None:
        badge_award.user.message_set.create(message=message)
badge_awarded.connect(send_badge_messages)

########NEW FILE########
__FILENAME__ = internals
from django.contrib.auth.models import User

from brabeion.base import Badge



class BadgeCache(object):
    """
    This is responsible for storing all badges that have been registered, as
    well as providing the pulic API for awarding badges.
    
    This class should not be instantiated multiple times, if you do it's your
    fault when things break, and you get to pick up all the pieces.
    """
    def __init__(self):
        self._event_registry = {}
        self._registry = {}
    
    def register(self, badge):
        # We should probably duck-type this, but for now it's a decent sanity
        # check.
        assert issubclass(badge, Badge)
        badge = badge()
        self._registry[badge.slug] = badge
        for event in badge.events:
            self._event_registry.setdefault(event, []).append(badge)
    
    def possibly_award_badge(self, event, **state):
        if event in self._event_registry:
            for badge in self._event_registry[event]:
                badge.possibly_award(**state)


badges = BadgeCache()

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone



class BadgeAward(models.Model):
    user = models.ForeignKey(User, related_name="badges_earned")
    awarded_at = models.DateTimeField(default=timezone.now)
    slug = models.CharField(max_length=255)
    level = models.IntegerField()
    
    def __getattr__(self, attr):
        return getattr(self._badge, attr)
    
    @property
    def badge(self):
        return self
    
    @property
    def _badge(self):
        from brabeion import badges
        return badges._registry[self.slug]
    
    @property
    def name(self):
        return self._badge.levels[self.level].name
    
    @property
    def description(self):
        return self._badge.levels[self.level].description
    
    @property
    def progress(self):
        return self._badge.progress(self.user, self.level)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal



badge_awarded = Signal(providing_args=["badge"])
########NEW FILE########
__FILENAME__ = tasks
from celery.task import Task



class AsyncBadgeAward(Task):
    ignore_result = True
    
    def run(self, badge, state, **kwargs):
        badge.actually_possibly_award(**state)

########NEW FILE########
__FILENAME__ = brabeion_tags
from django import template

from brabeion.models import BadgeAward


register = template.Library()


class BadgeCountNode(template.Node):
    @classmethod
    def handle_token(cls, parser, token):
        bits = token.split_contents()
        if len(bits) == 2:
            return cls(bits[1])
        elif len(bits) == 4:
            if bits[2] != "as":
                raise template.TemplateSyntaxError("Second argument to %r must "
                    "be 'as'" % bits[0])
            return cls(bits[1], bits[3])
        raise template.TemplateSyntaxError("%r takes either 1 or 3 arguments." % bits[0])
    
    def __init__(self, user, context_var=None):
        self.user = template.Variable(user)
        self.context_var = context_var
    
    def render(self, context):
        user = self.user.resolve(context)
        badge_count = BadgeAward.objects.filter(user=user).count()
        if self.context_var is not None:
            context[self.context_var] = badge_count
            return ""
        return unicode(badge_count)

@register.tag
def badge_count(parser, token):
    """
    Returns badge count for a user, valid usage is::

        {% badge_count user %}
    
    or
    
        {% badge_count user as badges %}
    """
    return BadgeCountNode.handle_token(parser, token)


class BadgesForUserNode(template.Node):
    @classmethod
    def handle_token(cls, parser, token):
        bits = token.split_contents()
        if len(bits) != 4:
            raise template.TemplateSyntaxError("%r takes exactly 3 arguments." % bits[0])
        if bits[2] != "as":
            raise template.TemplateSyntaxError("The 2nd argument to %r should "
                "be 'as'" % bits[0])
        return cls(bits[1], bits[3])
    
    def __init__(self, user, context_var):
        self.user = template.Variable(user)
        self.context_var = context_var
    
    def render(self, context):
        user = self.user.resolve(context)
        context[self.context_var] = BadgeAward.objects.filter(
            user=user
        ).order_by("-awarded_at")
        return ""
        

@register.tag
def badges_for_user(parser, token):
    """
    Sets the badges for a given user to a context var.  Usage:
        
        {% badges_for_user user as badges %}
    """
    return BadgesForUserNode.handle_token(parser, token)

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from django.db import models


class PlayerStat(models.Model):
    user = models.OneToOneField(User, related_name="stats")
    points = models.IntegerField(default=0)

########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase

from brabeion import badges
from brabeion.base import Badge, BadgeAwarded
from brabeion.tests.models import PlayerStat


class PointsBadge(Badge):
    slug = "points"
    levels = [
        "Bronze",
        "Silver",
        "Gold",
    ]
    events = [
        "points_awarded",
    ]
    multiple = False
    
    def award(self, **state):
        user = state["user"]
        points = user.stats.points
        if points > 10000:
            return BadgeAwarded(3)
        elif points > 7500:
            return BadgeAwarded(2)
        elif points > 5000:
            return BadgeAwarded(1)


badges.register(PointsBadge)


class BaseTestCase(TestCase):
    def assert_num_queries(self, n, func):
        current_debug = settings.DEBUG
        settings.DEBUG = True
        current = len(connection.queries)
        func()
        self.assertEqual(current+n, len(connection.queries), connection.queries[current:])
        settings.DEBUG = current_debug

class BadgesTests(BaseTestCase):
    def test_award(self):
        u = User.objects.create_user("Lars Bak", "lars@hotspot.com", "x864lyfe")
        PlayerStat.objects.create(user=u)
        badges.possibly_award_badge("points_awarded", user=u)
        self.assertEqual(u.badges_earned.count(), 0)

        u.stats.points += 5001
        u.stats.save()
        badges.possibly_award_badge("points_awarded", user=u)
        self.assertEqual(u.badges_earned.count(), 1)
        self.assertEqual(u.badges_earned.all()[0].badge.name, "Bronze")

        badges.possibly_award_badge("points_awarded", user=u)
        self.assertEqual(u.badges_earned.count(), 1)

        u.stats.points += 2500
        badges.possibly_award_badge("points_awarded", user=u)
        self.assertEqual(u.badges_earned.count(), 2)
    
    def test_lazy_user(self):
        u = User.objects.create_user("Lars Bak", "lars@hotspot.com", "x864lyfe")
        PlayerStat.objects.create(user=u, points=5001)
        badges.possibly_award_badge("points_awarded", user=u)
        self.assertEqual(u.badges_earned.count(), 1)
        
        self.assert_num_queries(1, lambda: u.badges_earned.get().badge)

########NEW FILE########
__FILENAME__ = test_settings
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
    }
}

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "brabeion",
    "brabeion.tests",
]

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *



urlpatterns = patterns("",
    url(r"^$", "brabeion.views.badge_list", name="badge_list"),
    url(r"^(\w+)/(\d+)/$", "brabeion.views.badge_detail", name="badge_detail"),
)

########NEW FILE########
__FILENAME__ = views
from collections import defaultdict

from django.db.models import Count
from django.shortcuts import render_to_response
from django.template import RequestContext

from brabeion import badges
from brabeion.models import BadgeAward



def badge_list(request):
    if request.user.is_authenticated():
        user_badges = set((slug, level) for slug, level in
            BadgeAward.objects.filter(
                user = request.user
            ).values_list("slug", "level"))
    else:
        user_badges = []
    badges_awarded = BadgeAward.objects.values("slug", "level").annotate(
        num = Count("pk")
    )
    badges_dict = defaultdict(list)
    for badge in badges_awarded:
        badges_dict[badge["slug"]].append({
            "level": badge["level"],
            "name": badges._registry[badge["slug"]].levels[badge["level"]].name,
            "description": badges._registry[badge["slug"]].levels[badge["level"]].description,
            "count": badge["num"],
            "user_has": (badge["slug"], badge["level"]) in user_badges
        })
    
    for badge_group in badges_dict.values():
        badge_group.sort(key=lambda o: o["level"])
    
    return render_to_response("brabeion/badges.html", {
        "badges": sorted(badges_dict.items()),
    }, context_instance=RequestContext(request))


def badge_detail(request, slug, level):
    
    badge = badges._registry[slug].levels[int(level)]
    
    badge_awards = BadgeAward.objects.filter(
        slug = slug,
        level = level
    ).order_by("-awarded_at")
    
    badge_count = badge_awards.count()
    latest_awards = badge_awards[:50]
    
    return render_to_response("brabeion/badge_detail.html", {
        "badge": badge,
        "badge_count": badge_count,
        "latest_awards": latest_awards,
    }, context_instance=RequestContext(request))

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# brabeion documentation build configuration file, created by
# sphinx-quickstart on Thu Jun  3 13:44:25 2010.
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

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.txt'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'brabeion'
copyright = u'2010, Eldarion'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1.dev11'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'eldarion'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ["_theme"]

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_theme/eldarion/static/eldarion_logo_medium.png"

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'brabeiondoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'brabeion.tex', u'brabeion Documentation',
   u'Eldarion', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'brabeion', u'brabeion Documentation',
     [u'Eldarion'], 1)
]

########NEW FILE########
