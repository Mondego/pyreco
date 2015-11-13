__FILENAME__ = admin
from django.contrib import admin

from models import Page


admin.site.register(Page)

########NEW FILE########
__FILENAME__ = forms
from django import forms as forms

from models import Page


class PageForm(forms.Form):
    name = forms.CharField(max_length=255)
    content = forms.CharField(widget=forms.Textarea())

    def clean_name(self):
        import re
        from templatetags.wiki import WIKI_WORD

        pattern = re.compile(WIKI_WORD)

        name = self.cleaned_data['name']
        if not pattern.match(name):
            raise forms.ValidationError('Must be a WikiWord.')

        return name

########NEW FILE########
__FILENAME__ = models
from django.db import models

from templatetags.wiki import wikify


class Page(models.Model):
    name = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    rendered = models.TextField()

    class Meta:
        ordering = ('name', )

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.rendered = wikify(self.content)
        super(Page, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = wiki
import re

from django import template


WIKI_WORD = r'(?:[A-Z]+[a-z]+){2,}'


register = template.Library()


wikifier = re.compile(r'\b(%s)\b' % WIKI_WORD)


@register.filter
def wikify(s):
    from django.core.urlresolvers import reverse
    wiki_root = reverse('wiki.views.index', args=[], kwargs={})
    return wikifier.sub(r'<a href="%s\1/">\1</a>' % wiki_root, s)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from templatetags.wiki import WIKI_WORD


urlpatterns = patterns('wiki.views',
    (r'^$', 'index'),
    ('(?P<name>%s)/$' % WIKI_WORD, 'view'),
    ('(?P<name>%s)/edit/$' % WIKI_WORD, 'edit'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext

from forms import PageForm
from models import Page


def index(request):
    """Lists all pages stored in the wiki."""
    context = {
        'pages': Page.objects.all(),
    }

    return render_to_response('wiki/index.html',
        RequestContext(request, context))


def view(request, name):
    """Shows a single wiki page."""
    try:
        page = Page.objects.get(name=name)
    except Page.DoesNotExist:
        page = Page(name=name)

    context = {
        'page': page,
    }

    return render_to_response('wiki/view.html',
        RequestContext(request, context))


def edit(request, name):
    """Allows users to edit wiki pages."""
    try:
        page = Page.objects.get(name=name)
    except Page.DoesNotExist:
        page = None

    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if not page:
                page = Page()
            page.name = form.cleaned_data['name']
            page.content = form.cleaned_data['content']

            page.save()
            return redirect(view, name=page.name)
    else:
        if page:
            form = PageForm(initial=page.__dict__)
        else:
            form = PageForm(initial={'name': name})

    context = {
        'form': form,
    }

    return render_to_response('wiki/edit.html',
        RequestContext(request, context))

########NEW FILE########
