__FILENAME__ = reversetag
from django.conf import settings
from django.template import (Library, Node, TemplateSyntaxError)
from django.utils.encoding import smart_str

register = Library()

class Reversible(object):
    def __init__(self, view, args, kwargs):
        self.view = view
        self.args = args
        self.kwargs = kwargs
        self.resolved_view = None
        self.resolved_args = []
        self.resolved_kwargs = {}

    def resolve(self, context):
        self.resolved_view = self.view.resolve(context)
        self.resolved_args = [arg.resolve(context) 
                              for arg in self.args]
        self.resolved_kwargs = dict(
            [(smart_str(k,'ascii'), v.resolve(context))
             for k, v in self.kwargs.items()])
    
    def merge(self, reversible=None):
        """Walk down the (maybe existing) stack of Rerversibles."""
        
        if reversible is None:
            reversible = self
        if isinstance(reversible.resolved_view, Reversible): 
            view, args, kwargs = reversible.merge(reversible.resolved_view)
            args.extend(reversible.resolved_args)
            kwargs.update(reversible.resolved_kwargs)
            return view, args, kwargs
        return (reversible.resolved_view, 
                reversible.resolved_args, 
                reversible.resolved_kwargs,
            )
    
    def reverse(self, context):
        from django.core.urlresolvers import reverse, NoReverseMatch
        url = ''
        view, args, kwargs = self.merge()
        if not view:
            # view is empty or None so silently ignore for now
            return ""

        # The following has been taken from django's url tag for 
        # backwards compatibility: 
        # Try to look up the URL twice: once given the view name, and 
        # again relative to what we guess is the "main" app. If they 
        # both fail, re-raise the NoReverseMatch unless we're using the 
        # {% reverse ... as var %} construct in which cause return 
        # nothing.
        try:
            url = reverse(view, args=args, 
                          kwargs=kwargs)
        except NoReverseMatch, exc:
            project_name = settings.SETTINGS_MODULE.split('.')[0]
            try:
                url = reverse(project_name + '.' + view,
                              args=args, kwargs=kwargs)
            except NoReverseMatch:
                # reraise the original NoReverseMatch since the above 
                # is just a (failed, if we reach here) attempt to fix 
                # things.
                raise exc
        return url
        
        
    def __unicode__(self):
        # don't output partially reversed urls
        if settings.TEMPLATE_DEBUG:
            return u"[Cannot render: %r. You have to use it through " \
                   u"the 'reverse' tag.]" % self
        else:
            return u'' # fail silently

    def __repr__(self):
        return "<%s: reverse %r with args %r and kwargs %r>" % (
                self.__class__.__name__, 
                self.view.var, 
                [a.var for a in self.args], 
                dict((k,v.var) for k,v in self.kwargs.iteritems()))

class ReverseBaseNode(Node):
    """Base class for ReverseNodes"""
    def __init__(self, view, args, kwargs, asvar):
        self.reversible = Reversible(view, args, kwargs)
        self.asvar = asvar

    def __repr__(self):
        return repr(self.reversible)
        

class ReverseNode(ReverseBaseNode):
    """Represents a to-be-reversed url"""
    def render(self, context):
        from django.core.urlresolvers import NoReverseMatch
        self.reversible.resolve(context)
        url = ''
        try:
            url = self.reversible.reverse(context)
        except NoReverseMatch:
            if self.asvar is None:
                # only re-raise if not using <reverse ... as bla>
                raise
                    
        if self.asvar:
            context[self.asvar] = url
            return ''
        else:
            return url
    
class PartialReverseNode(ReverseBaseNode):
    """Represents a partial to-be-reversed url"""
    def render(self, context):
        self.reversible.resolve(context)
        
        if self.asvar:
            context[self.asvar] = self.reversible
            return ''
        else:
            raise TemplateSyntaxError("When using 'partial' the " 
                "'reverse' tag requires 'as varname' argument")

    def __unicode__(self):
        # don't output partially reversed urls
        if settings.TEMPLATE_DEBUG:
            return "[Cannot render: %r. You have to use it through " \
                "the 'reverse' tag.]" % self
        else:
            return '' # fail silently

@register.tag
def reverse(parser, token):
    """
    Returns an absolute URL matching given view with its parameters.

    This is a way to define links that aren't tied to a particular URL
    configuration::

        {% reverse "path.to.some_view" "arg1","arg2" [as varname] %}
    or:
        {% reverse "path.to.some_view" name1="value1" [as varname] %}

    The first argument is a path to a view or a view name. It can be an 
    absolute python path or just ``app_name.view_name`` without the project 
    name if the view is located inside the project.  Other arguments are 
    comma-separated values that will be filled in place of positional and 
    keyword arguments in the URL. All arguments for the URL must be present 
    unless you use the ``partial`` form of ``reverse`` which is described 
    below.
    If you'd like to store the resulting url in a ``context`` variable instead of 
    directly displaying it you can use the optional ``as varname`` argument.

    For example if you have a view ``app_name.client`` taking client's id and
    the corresponding line in a URLconf looks like this::

        ('^client/(\d+)/$', 'app_name.client')

    and this app's URLconf is included into the project's URLconf under some
    path::

        ('^clients/', include('project_name.app_name.urls'))

    then in a template you can create a link for a certain client like this::

        {% reverse "app_name.client" client.id %}

    The URL will look like ``/clients/client/123/``.
    
    
    Advanced usage
    ~~~~~~~~~~~~~~
    
    The ``reverse`` tag also supports a more advanced mode of operation
    called "partial resolving". This allows you to reverse an URL in two or 
    more stages. Each time only specifying some of required view arguments
    until the URL is resolved.
    Syntax:
    
        {% reverse partial "path.to.some_view" "arg1" key1="value1" as varname %}
    
    TODO: add more doc and usage examples
    
    Note: When using the partial keyword the ``as varname`` clause is required
          since a partially reversed URL can not be output directly but only 
          be used as the ``view`` argument to another invocation of 
          ``reverse``.
    Note: The "last" invocation MUST NOT specify ``partial`` 
    """
    bits = token.contents.split(' ')
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument"
                                  " (path to a view)" % bits[0])
    partial = False
    args = []
    kwargs = {}
    asvar = None

    argstart = 2
    if bits[1] == "partial":
        partial = True
        view = parser.compile_filter(bits[2])
        argstart = 3
    else:
        view = parser.compile_filter(bits[1])

    if len(bits) > 2:
        bits = iter(bits[argstart:])
        for bit in bits:
            if bit == 'as':
                asvar = bits.next()
                break
            else:
                for arg in bit.split(","):
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        k = k.strip()
                        kwargs[k] = parser.compile_filter(v)
                    elif arg:
                        args.append(parser.compile_filter(arg))
        if partial and asvar is None:
            raise TemplateSyntaxError("When using 'partial' '%s' requires"
                                      " (as varname) argument" % bits[0])
    if partial:
        return PartialReverseNode(view, args, kwargs, asvar)
    return ReverseNode(view, args, kwargs, asvar)


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = revtest_dummy
from django.template import Library

register = Library()

@register.inclusion_tag("revtest_dummy.html")
def revtest_dummy(view):
    return {'view': view}

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.template import Template
from django.template.context import Context
from django.core.urlresolvers import NoReverseMatch


class ReversetagTest(TestCase):
    def test_base(self):        
        t1 = Template("""{% load reversetag %}{% reverse "URL1" %}""")
        self.assertEqual(t1.render(Context()), u"/T1/")

        t2 = Template("""{% load reversetag %}{% reverse "URL2" 1 %}""")
        self.assertEqual(t2.render(Context()), u"/T2/1/")

        t3 = Template("""{% load reversetag %}{% reverse "URL3" x=1,y=2,z=3 %}""")
        self.assertEqual(t3.render(Context()), u"/T3/1/2/3/")

        t4 = Template("""{% load reversetag %}{% with "URL1" as somevar %}{% reverse somevar %}{% endwith %}""")
        self.assertEqual(t4.render(Context()), u"/T1/")

    def test_failures(self):
        t1 = Template("""{% load reversetag %}{% reverse "NOURL1" %}""")
        self.assertRaises(NoReverseMatch, t1.render, Context())
    
        t2 = Template("""{% load reversetag %}{% reverse "URL2" x %}""")
        self.assertRaises(NoReverseMatch, t2.render, Context())

        t3 = Template("""{% load reversetag %}{% reverse "URL3" x=a,y=b,z=c %}""")
        self.assertRaises(NoReverseMatch, t3.render, Context())


    def test_partial(self):
        t1 = Template("""{% load reversetag %}{% reverse partial "URL1" as P1 %}{% reverse P1 %}""")
        self.assertEqual(t1.render(Context()), u"/T1/")

        t2 = Template("""{% load reversetag %}{% reverse partial "URL3" as P3 %}{% reverse P3 x=1,y=2,z=3 %}""")
        self.assertEqual(t2.render(Context()), u"/T3/1/2/3/")

        t3 = Template("""{% load reversetag %}{% reverse partial "URL3" as P3 %}{% reverse partial P3 x=1 as P3_1 %}{% reverse partial P3_1 y=2 as P3_2 %}{% reverse P3_2 z=3 %}""")
        self.assertEqual(t3.render(Context()), u"/T3/1/2/3/")

    def test_loop(self):
        t1 = Template("""{% load reversetag %}{% reverse partial "URL3" as P3 %}{% reverse partial P3 x=1 as P3_1 %}{% reverse partial P3_1 y=2 as P3_2 %}{% for VAR_X in values %}{% reverse P3_2 z=VAR_X %} {% endfor %}""")
        self.assertEqual(t1.render(Context({'values': [3,4,5]})), u"/T3/1/2/3/ /T3/1/2/4/ /T3/1/2/5/ ")

    def test_context(self):
        t1 = Template("""{% load reversetag revtest_dummy %}{% reverse partial "URL3" as P3 %}{% reverse partial P3 x=1 as P3_1 %}{% reverse partial P3_1 y=2 as P3_2 %}{% revtest_dummy P3_2 %}""")
        self.assertEqual(t1.render(Context()), u"/T3/1/2/9/")
        
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^T1/$', 'revtest.views.test_view', name="URL1"),
    url(r'^T2/([0-9]+)/$', 'revtest.views.test_view', name="URL2"),
    url(r'^T3/(?P<x>[0-9]+)/(?P<y>[0-9]+)/(?P<z>[0-9]+)/$', 'revtest.views.test_view', name="URL3"),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

def test_view(request, x=None, y=None, z=None):
    return HttpResponse("Done")

########NEW FILE########
__FILENAME__ = test_settings

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db',
    }
}

ROOT_URLCONF = 'revtest.urls'

INSTALLED_APPS = (
    'reversetag',
    'revtest',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.load_template_source',
)

########NEW FILE########
