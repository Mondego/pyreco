__FILENAME__ = context_processors
from django.conf import settings

REQUEST_FORMAT_NAME = getattr(settings, 'REQUEST_FORMAT_NAME', 'format')
REQUEST_FORMAT_PDF_VALUE = getattr(settings, 'REQUEST_FORMAT_PDF_VALUE', 'pdf')
TEMPLATE_PDF_CHECK = getattr(settings, 'TEMPLATE_PDF_CHECK',
'DJANGO_PDF_OUTPUT')


def check_format(request):
    """
    Adds a TEMPLATE_PDF_CHECK variable to the context.
    This var will normally be used in templates like this:
    {% if DJANGO_PDF_OUTPUT %}
        ... content to be displayed only in the PDF output
    {% endif %}
    or:
    {% if not DJANGO_PDF_OUTPUT %}
        ... content that won't be displayed only in the PDF output
    {% endif %}

    Notice:
    Here the value of TEMPLATE_PDF_CHECK settings var is the default one, i.e.
    DJANGO_PDF_OUTPUT. You can change this in your settings
    """
    format = request.GET.get(REQUEST_FORMAT_NAME, None)
    if format == REQUEST_FORMAT_PDF_VALUE:
        return {TEMPLATE_PDF_CHECK: True}
    else:
        return {TEMPLATE_PDF_CHECK: False}

########NEW FILE########
__FILENAME__ = middleware
#!/usr/bin/env python

import os.path
import cStringIO as StringIO
import cgi
import ho.pisa as pisa
import cStringIO as StringIO
import cgi
from django.http import HttpResponse
from django.conf import settings

REQUEST_FORMAT_NAME = getattr(settings, 'REQUEST_FORMAT_NAME', 'format')
REQUEST_FORMAT_PDF_VALUE = getattr(settings, 'REQUEST_FORMAT_PDF_VALUE', 'pdf')
TEMPLATE_PDF_CHECK = getattr(settings, 'TEMPLATE_PDF_CHECK',
'DJANGO_PDF_OUTPUT')


def fetch_resources(uri, rel):
    """
    Prepares paths for pisa
    """
    path = os.path.join(settings.MEDIA_ROOT,
            uri.replace(settings.MEDIA_URL, ""))
    return path


def transform_to_pdf(response):
    response['mimetype'] = 'application/pdf'
    response['Content-Disposition'] = 'attachment; filename=report.pdf'
    content = response.content
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(content),
            response, link_callback=fetch_resources)
    if not pdf.err:
        return response
    else:
        return http.HttpResponse('We had some errors<pre>%s</pre>' %
                cgi.escape(html))


class PdfMiddleware(object):
    """
    Converts the response to a pdf one.
    """
    def process_response(self, request, response):
        format = request.GET.get(REQUEST_FORMAT_NAME, None)
        if format == REQUEST_FORMAT_PDF_VALUE:
            response = transform_to_pdf(response)
        return response

########NEW FILE########
__FILENAME__ = pdf_tags
from django import template
from django.http import Http404
from django.conf import settings

register = template.Library()

REQUEST_FORMAT_NAME = getattr(settings, 'REQUEST_FORMAT_NAME', 'format')
REQUEST_FORMAT_PDF_VALUE = getattr(settings, 'REQUEST_FORMAT_PDF_VALUE', 'pdf')
TEMPLATE_PDF_CHECK = getattr(settings, 'TEMPLATE_PDF_CHECK',
'DJANGO_PDF_OUTPUT')


def pdf_link(parser, token):
    """
    Parses a tag that's supposed to be in this format: {% pdf_link title %}
    """
    bits = [b.strip('"\'') for b in token.split_contents()]
    if len(bits) < 2:
        raise template.TemplateSyntaxError, "pdf_link tag takes 1 argument"
    title = bits[1]
    return PdfLinkNode(title.strip())


class PdfLinkNode(template.Node):
    """
    Renders an <a> HTML tag with a link which href attribute
    includes the ?REQUEST_FORMAT_NAME=REQUEST_FORMAT_PDF_VALUE
    to the current page's url to generate a PDF link to the PDF version of this
    page.

    Eg.
        {% pdf_link PDF %} generates
        <a href="/the/current/path/?format=pdf" title="PDF">PDF</a>

    """
    def __init__(self, title):
        self.title = title

    def render(self, context):
        request = context['request']
        getvars = request.GET.copy()
        getvars[REQUEST_FORMAT_NAME] = REQUEST_FORMAT_PDF_VALUE

        if len(getvars.keys()) > 1:
            urlappend = "&%s" % getvars.urlencode()
        else:
            urlappend = '%s=%s' % (REQUEST_FORMAT_NAME, REQUEST_FORMAT_PDF_VALUE)

        url = '%s?%s' % (request.path, urlappend)
        return '<a href="%s" title="%s">%s</a>' % (url, self.title, self.title)

pdf_link = register.tag(pdf_link)

########NEW FILE########
