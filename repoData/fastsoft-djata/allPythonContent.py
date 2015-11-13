__FILENAME__ = exceptions

from os.path import join
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from djata.python.names import *

class UserError(Exception):

    @property
    def template(self):
        return join('djata', 'errors',
            lower(self.__class__.__name__, '_') + '.html'
        )

    response_class = HttpResponseBadRequest

class PostActionError(UserError):
    def __init__(self, actions):
        UserError.__init__(self)
        self.actions = actions

class ModelFormatNotAvailable(UserError): pass

class ObjectFormatNotAvailable(UserError):
    def __init__(self, format, formats):
        UserError.__init__(self)
        self.format = format
        self.formats = formats

class ModelParserNotAvailable(UserError): pass

class ObjectParserNotAvailable(UserError): pass

class NoFormatSpecifiedError(UserError): pass

class NoParserSpecifiedError(UserError): pass

class NoSuchObjectError(UserError): pass

class NoSuchMethodError(UserError): pass

class NoSuchActionError(UserError): pass

class NoFormatContentTypError(UserError): pass

class NotExactSupportedFormatError(UserError):
    def __init__(self, request_format, response_format):
        UserError.__init__(self, request_format)
        self.request_format = request_format
        self.response_format = response_format

class NoSuchViewError(UserError): pass

class PaginationRequiredError(UserError): pass

class PageLengthMustBeNumberError(UserError): pass

class PageNumberMustBeNumberError(UserError): pass

class EmptyPageError(UserError): pass

class NonExistantFieldsError(UserError):
    def __init__(self, fields):
        UserError.__init__(self)
        self.fields = fields

class NotAuthenticatedError(UserError):
    response_class = HttpResponseForbidden

class PermissionDeniedError(UserError):
    response_class = HttpResponseForbidden

class InvalidSortFieldError(UserError):
    def __init__(self, invalids, valids):
        UserError.__init__(self)
        self.invalids = invalids
        self.valids = valids

class TooManyObjectsError(UserError):
    pass

class NotYetImplemented(UserError):
    pass

class PageNotFoundError(UserError):
    pass



########NEW FILE########
__FILENAME__ = fields

from djata.python.orderedclass import *

def map_field(field):
    return field

class Cell(object):
    def __init__(self, field, object):
        self.field = field
        self.object = object
    def __unicode__(self):
        return self.value
    @property
    def value(self):
        return self.field.value_from_object(self.object)

class Field(OrderedProperty):
    Cell = Cell

    def __init__(self, name = None, link = False, filter = False, identity = False):
        self.name = name
        self.link = link
        self.filter = filter

    def dub(self, view, field, name):
        self.view = view
        self.field = field
        if self.name is None:
            self.name = name
        return self

    def to_python(self, value):
        return value

    def value_from_object(self, object):
        return object[self.attname]

    def __get__(self, object, klass):
        return object[self.attname]
    def __set__(self, object, value):
        object[self.attname] = value

class ForeignKey(Field):
    def __init__(self, view):
        self.to = view


########NEW FILE########
__FILENAME__ = format_csv

from djata.formats import ModelFormat, ModelParser
import csv
from cStringIO import StringIO

class Csv(object):
    content_type = 'text/csv'
    name = 'csv'

class CsvModelFormat(ModelFormat, Csv):

    def __call__(self, request, view):
        fields = view.get_fields()
        objects = view.get_objects()

        kws = {}
        if 'excel' in request.GET:
            kws['dialect'] = 'excel'

        string = StringIO()
        writer = csv.writer(string, **kws)
        writer.writerow([
            field.name
            for field in fields
        ])
        writer.writerows([
            ([
                field.value_from_object(object)
                for field in fields
            ])
            for object in objects
        ])

        return string.getvalue()

class CsvModelParser(ModelParser, Csv):

    def __call__(self, request, view):
        fields = view.get_fields()

        kws = {}
        if 'excel' in requestGET:
            kws['dialect'] = 'excel'

        reader = csv.reader(StringIO(request.raw_post_data))

        if 'noheaders' in request.GET:
            headers = [
                field.name
                for field in fields
            ]
        else:
            headers = reader.next()

        return list(
            dict(zip(headers, row))
            for row in reader
        )

class CsvObjectParser(object):
    pass


########NEW FILE########
__FILENAME__ = format_html

from djata.formats import TemplateFormat, ModelFormat, ObjectFormat, ObjectPage
from django.forms import ModelForm
from django.db.models import ForeignKey

def form_for_model(model):
    return type(model.__class__.__name__ + 'Form', (ModelForm,), {
        "Meta": type("Meta", (object,), {
            "model": model,
        })
    })

class RawHtmlFormat(TemplateFormat):
    name = 'raw.html'
    content_type = 'text/html'

class HtmlFormat(RawHtmlFormat):
    name = 'html'

class RawHtmlObjectFormat(ObjectFormat, RawHtmlFormat):
    template = 'djata/object.raw.html'
    name = 'raw.html'
    label = 'Raw HTML'

    def process(self, request, view):
        context = request.context
        object = view.get_object()
        fields = view.get_fields()
        parent_fields = None # XXX
        child_fields = view.get_child_fields()
        related_fields = view.get_related_fields()
        context['view'] = view
        context['object'] = object
        context['fields'] = fields
        context['related_fields'] = related_fields
        context['child_fields'] = related_fields
        context['items'] = [
            {
                'name': field.name,
                'value': cell(field, object, view)
            }
            for field in fields
        ]
        context['child_items'] = [
            {
                'name': field.var_name,
                'items': [
                    ChildCell(item, view)
                    for item in
                    field.model.objects.filter(**{
                        field.field.name: object,
                    })
                ]
            }
            for field in child_fields
        ]
        context['related_items'] = [
            {
                'name': field.name,
                'items': [
                ]
            }
            for field in related_fields
        ]

class HtmlObjectFormat(RawHtmlObjectFormat):
    template = 'djata/object.html'
    name = 'html'
    label = 'HTML'

    def process(self, request, view):
        formats = [
            view._object_formats_lookup[name]
            for name in view._object_formats
        ]
        request.context['formats'] = [
            format for format in formats
            if not getattr(format, 'is_action', False)
        ]
        request.context['actions'] = [
            format for format in formats
            if getattr(format, 'is_action', False)
        ]
        return super(HtmlObjectFormat, self).process(request, view)

class RawHtmlModelFormat(ModelFormat, HtmlFormat):
    template = 'djata/model.raw.html'
    name = 'raw.html'
    label = 'Raw HTML'

    def process(self, request, view):
        context = request.context
        objects = view.get_objects()
        fields = view.get_fields()
        context['objects'] = objects
        context['fields'] = fields
        context['table'] = [
            [
                cell(field, object, view)
                for field in fields
            ]
            for object in objects
        ]
        context['field_names'] = [
            field.verbose_name
            for field in fields
        ]

class HtmlModelFormat(RawHtmlModelFormat):
    name = 'html'
    label = 'HTML'
    template = 'djata/model.html'

    def process(self, request, view):
        formats = [
            view._model_formats_lookup[name]
            for name in view._model_formats
        ]
        request.context['formats'] = [
            format for format in formats
            if not getattr(format, 'is_action', False)
        ]
        request.context['actions'] = [
            format for format in formats
            if getattr(format, 'is_action', False)
        ]
        return super(HtmlModelFormat, self).process(request, view)


class UploadHtmlModelFormat(ModelFormat, TemplateFormat):
    template = 'djata/model.upload.html'
    name = 'upload.html'
    label = 'Upload'
    content_type = 'text/html'
    is_action = True
    def process(self, request, view):
        request.context['formats'] = view._model_parsers

class EditHtmlObjectFormat(HtmlObjectFormat):
    template = 'djata/object.edit.html'
    name = 'edit.html'
    label = 'Edit'
    is_action = True
    def process(self, request, view):
        object = view.get_object()
        Form = form_for_model(view.model)
        request.context['form'] = Form(instance = object)
        super(EditHtmlObjectFormat, self).process(request, view)

class AddHtmlObjectFormat(HtmlModelFormat):
    template = 'djata/object.add.html'
    name = 'add.html'
    label = 'Add'
    is_action = True
    def process(self, request, view):
        Form = form_for_model(view.model)
        request.context['form'] = Form()
        super(AddHtmlObjectFormat, self).process(request, view)

def cell(field, object, view):
    value = get_object_field_value(object, field)
    if value is None:
        return
    else:
        return Cell(field, object, view, value)
    
class Cell(object):
    def __init__(self, field, object, view, value):
        self.field = field
        self.object = object
        self.view = view
        self.value = value
    def __unicode__(self):
        return unicode(self.value)
    @property
    def url(self):
        if self.field.primary_key:
            return self.view.get_url_of_object(self.object)
        elif isinstance(self.field, ForeignKey):
            return self.view.get_url_of_object(self.value)

class ChildCell(object):
    def __init__(self, object, view):
        self.object = object
        self.view = view
    def __unicode__(self):
        return unicode(self.object)
    @property
    def url(self):
        return self.view.get_url_of_object(self.object)

def get_object_field_value(object, field):
    value = field.value_from_object(object)
    if isinstance(field, ForeignKey) and value is not None:
        value = field.rel.to.objects.get(pk = value)
    return value


########NEW FILE########
__FILENAME__ = format_html_chart

from djata.formats.format_html import HtmlModelFormat
from math import ceil

class HtmlChartModelFormat(HtmlModelFormat):
    name = 'chart.html'
    content_type = 'text/html'
    template = 'djata/model.chart.html'
    height = 400
    width = 600

    def process(self, request, view):
        context = request.context
        objects = view.get_objects()
        model_options = view.meta.model._meta

        height = self.height
        width = self.width
        x = model_options.get_field_by_name(self.x)[0]
        y = model_options.get_field_by_name(self.y)[0]
        series = model_options.get_field_by_name(self.series)[0]

        chart = [
            {
                'x': x.value_from_object(object),
                'y': y.value_from_object(object),
                'series': series.value_from_object(object),
                'object': object,
            }
            for object in objects
        ]
        max_y = chart and max(point['y'] for point in chart) or 0
        column_count = len(chart)
        column_width = int(ceil(width / column_count))
        width = column_width * column_count
        for point in chart:
            bottom_height = max_y == 0 and height or int(round(
                height * point['y'] / max_y
            ))
            top_height = height - bottom_height
            point.update({
                'top_height': top_height,
                'bottom_height': bottom_height,
            })

        context['max_y'] = max_y
        context['x'] = x
        context['y'] = y
        context['series'] = series
        context['chart'] = chart
        context['height'] = height
        context['width'] = width
        context['column_width'] = column_width

        super(HtmlChartModelFormat, self).process(request, view)


########NEW FILE########
__FILENAME__ = format_json

# TODO indent
# TODO page_length page_number
# TODO compact
# TODO expand related fields
# TODO use URLs for foreign keys

from datetime import datetime
from django.db.models import ForeignKey
from django.utils.simplejson import *
from djata.python.wrap import wrap
from djata.formats import ModelFormat, ObjectFormat, ModelParser, ObjectParser

def complex(data):
    if data is None:
        return data
    if not isinstance(data, type) and hasattr(data, 'json'):
        return data.json()
    if isinstance(data, list) or isinstance(data, tuple):
        return list(
            complex(datum)
            for datum in data
        )
    elif isinstance(data, dict):
        return dict(
            (complex(key), complex(value))
            for key, value in data.items()
        )
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, int):
        return data
    elif isinstance(data, long):
        return data
    elif isinstance(data, float):
        return data
    elif isinstance(data, basestring):
        return data
    else:
        return unicode(data)

class JsonMixin(object):
    def __call__(self, request, view):

        if 'indent' in request.JSON:
            indent = request.JSON['indent'] or 4
        elif 'indent' in request.GET:
            indent = int(request.GET['indent'] or 4)
        else:
            indent = None

        allow_nan = (
            'allow_nan' in request.GET or
            request.JSON.get('allow_nan', False) == True
        )

        if 'compact' in request.JSON:
            if request.JSON['compact'] == True:
                separators = (',', ':')
        elif 'compact' in request.GET:
            separators = (',', ':')
        else:
            separators = None

        return dumps(
            complex(self.python(request, view)),
            indent = indent,
            allow_nan = allow_nan,
            separators = separators,
        )

class JsonpMixin(object):
    callback = 'callback'
    def __call__(self, request, view):
        callback = request.JSON.get(
            'callback',
            request.GET.get(
                'callback',
                self.callback
            )
        )
        return '%s(%s)' % (
            callback,
            super(JsonpMixin, self).__call__(request, view),
        )

class JsonObjectFormat(JsonMixin, ObjectFormat):
    name = 'json'
    extension = 'json'
    content_type = 'application/x-javascript'

    def cell(self, field, object, view):
        value = field.value_from_object(object)
        if isinstance(field, ForeignKey):
            return {
                field.rel.field_name: object.pk,
                "$type": field.rel.to._meta.verbose_name,
                "$ref": view.get_url_of_object(
                    field.rel.to.objects.get(pk = value)
                ),
            }
        return value

    def python(self, request, view):
        object = view.get_object()
        fields = view.get_fields()
        return dict(
            (field.name, self.cell(field, object, view))
            for field in fields
        )

class JsonpObjectFormat(JsonpMixin, JsonObjectFormat):
    name = 'jsonp'

class JsonObjectParser(ObjectParser):
    extension = 'json'
    content_type = 'application/x-javascript'

    def __call__(self, request, view):
        fields = view.get_fields()
        object = loads(request.raw_post_data)
        return dict(
            (field.attname, object[field.name])
            for field in fields
            if field.name in object
        )

class JsonModelFormat(JsonMixin, ModelFormat):
    name = 'json'
    content_type = 'application/x-javascript'
    def python(self, request, view):

        context = request.context
        objects = view.get_objects()
        fields = view.get_fields()
        field_names = [
            field.name
            for field in fields
        ]

        use_envelope = 'envelope' in request.GET or request.JSON.get('envelope', False)
        use_table = 'table' in request.GET or request.JSON.get('table', False)
        use_map = 'map' in request.GET or request.JSON.get('map', False)
        index = view.index

        envelope = {
            'length': objects.count(),
            'fields': field_names,
            'page_number': context.get('page_number', None),
            'page_length': context.get('page_length', None),
        }

        objects = tuple(dict(
            (field.name, field.value_from_object(object))
            for field in fields
        ) for object in objects)

        if use_table:
            if use_map:
                objects = dict(
                    (object[index.name], tuple(
                        object[field_name]
                        for field_name in field_names
                    ))
                    for object in objects
                )
            else:
                objects = tuple(
                    tuple(
                        object[field_name]
                        for field_name in field_names
                    )
                    for object in objects
                )

        else:
            if use_map:
                objects = dict(
                    (object[index.name], object)
                    for object in objects
                )

        envelope['objects'] = objects

        if use_envelope:
            return envelope
        else:
            return objects

class JsonpModelFormat(JsonpMixin, JsonModelFormat):
    name = 'jsonp'


########NEW FILE########
__FILENAME__ = format_text

from djata.formats import ObjectFormat, ModelFormat, TemplateFormat

class TextModelFormat(ModelFormat, TemplateFormat):
    name = 'text'
    content_type = 'text/plain'
    template = 'djata/model.text'

    def process(self, request, view):
        objects = view.get_objects()
        fields = view.get_fields()

        capitalize = 'capitalize' in request.GET
        display_header = request.GET.get('display_header', 'yes')
        if display_header not in ('yes', 'no'):
            raise ValueError()
        display_header = display_header == 'yes'

        field_names = [
            field.name
            for field in fields
        ]

        # transform list of dictionaries and column names to a lines in cells in rows
        rows = list(
            list(
                unicode(
                    default_if_none(field.value_from_object(object), "")
                ).expandtabs(4).replace(
                    u"\r", u""
                ).split(
                    u"\n"
                )
                for field in fields
            )
            for object in objects
        )

        # normalize the number of lines in each row
        rows = list(
            list(
                list_pad(cell, row_height)
                for cell in row
            )
            for row, row_height in rows_and_heights(rows)
        )

        # transpose lines in cells in rows to cell lines in rows
        rows = list(
            line
            for row in rows
            for line in zip(*row)
        )

        # calculate the width of each column based on the
        # widths of each column name and the widest line in each column
        if display_header:
            column_widths = list(
                max(len(column_name), len(rows) and max(
                    len(unicode(row[column_index]))
                    for row in rows
                ) or 1)
                for column_name, column_index in zip(
                    field_names,
                    range(len(field_names))
                )
            )
        else:
            column_widths = list(
                len(rows) and max(
                    len(unicode(row[column_index]))
                    for row in rows
                ) or 1
                for column_name, column_index in zip(
                    field_names,
                    range(len(field_names))
                )
            )


        # convert lines in rows to lines delimited by double spaces
        lines = list(
            u"  ".join(
                string_pad(row[column_index], column_width)
                for column_width, column_index in
                zip(column_widths, range(len(field_names)))
            )
            for row in rows
        )

        # add headings
        if display_header:
            lines = [
                u"  ".join(
                    string_pad(
                        capitalize and
                        column_name.upper() or
                        column_name,
                        column_width
                    )
                    for column_width, column_name in
                    zip(column_widths, field_names)
                ),
                u"  ".join(
                    u"-" * column_width
                    for column_width
                    in column_widths
                ),
            ] + lines

        request.context['content'] = u"".join(
            u"%s\n" % line for line in lines
        )

class TextObjectFormat(ObjectFormat, TemplateFormat):
    name = 'text'
    content_type = 'text/plain'
    template = 'djata/object.text'

    def process(self, request, view):
        context = request.context
        object = view.get_object()
        fields = view.get_fields()
        context['items'] = [
            [field.name, field.value_from_object(object)]
            for field in fields
        ]

def string_pad(cell, cell_width):
    if isinstance(cell, int) or isinstance(cell, long):
        return ("%s" % cell).rjust(cell_width)
    else:
        string = unicode(cell)
        return ("%s" % cell).ljust(cell_width)

def list_pad(cell, height):
    return cell + [u"" for n in range(height - len(cell))]

def rows_and_heights(rows):
    for row in rows:
        yield row, max(
            len(cell)
            for cell in row
        )

def default_if_none(value, default):
    if value is None: return default
    return value


########NEW FILE########
__FILENAME__ = format_url

from djata.formats import ObjectParser, ObjectFormat
from urllib import urlencode

class UrlencodeFormat(object):
    def coerce(self, field, value):
        if field.null and value == '':
            return None
        if field.blank and value == '':
            return ''
        try:
            return field.to_python(value)
        except:
            raise Exception("Validation error %s to %s" % (repr(value), field.name))

class UrlencodedObjectParser(ObjectParser, UrlencodeFormat):
    name = 'urlencoded'
    content_type = 'application/x-www-urlencoded'

    def __call__(self, request, view):
        fields = view.get_fields()
        return dict(
            (field.attname, self.coerce(field, request.POST[field.attname]))
            for field in fields
            if field.attname in request.POST
        )

class UrlqueryObjectParser(ObjectParser, UrlencodeFormat):
    name = 'urlquery'

    def __call__(self, request, view):
        fields = view.get_fields()
        return dict(
            (field.attname, self.coerce(field, request.GET[field.attname]))
            for field in fields
            if field.name in request.GET
        )

class UrlencodedObjectFormat(ObjectFormat):
    name = 'urlencoded'
    content_type = 'application/x-www-urlencoded'

    def __call__(self, request, view):
        fields = view.get_fields()
        object = view.get_object()
        return urlencode([
            (
                field.attname,
                default_if_none(field.value_from_object(object))
            )
            for field in fields
        ])

def default_if_none(object, default = ''):
    if object is None: return default
    return object


########NEW FILE########
__FILENAME__ = format_xls

from pyExcelerator.Workbook import Workbook
from pyExcelerator import XFStyle
from cStringIO import StringIO
from datetime import *

def any(values):
    for value in values:
        if value:
            return value

def xls(request, rows):
    column_names = request.column_names

    string = StringIO()
    workbook = Workbook()
    worksheet = workbook.add_sheet('Data')
    for row_number, row in enumerate(rows):
        for column_number, column_name in enumerate(column_names):
            style = XFStyle()
            cell = row[column_name] or ''

            if any(isinstance(cell, type) for type in (date, time, datetime)):
                cell = str(cell)

            if not any(isinstance(cell, type) for type in (
                basestring,
                int, long, float,
                datetime, date, time,
            )):
                cell = str(cell)

            if isinstance(cell, basestring):
                cell = cell.replace("\r", "")

            worksheet.write(row_number, column_number, cell, style)
    workbook.save(string)
    
    content = string.getvalue()
    content_type = 'application/vnd.ms-excel'
    return content_type, content


########NEW FILE########
__FILENAME__ = middleware

from django.utils import simplejson
from django.http import HttpResponse

class Middleware(object):
    """\
    An optional base class for Middleware that permits but does not require
    a Middleware class to be used as a view function decorator.  Middleware
    can be used as a mixin to transform other middleware types into
    decorators.
    """

    def __init__(self, view = None):
        if view is not None:
            self.view = view

    def __call__(self, request, *args, **kws):

        if not hasattr(request, 'middleware'):
            request.middleware = set()
        if type(self) in request.middleware:
            return self.view(request, *args, **kws)
        request.middleware.add(type(self))

        has_process_request = hasattr(self, 'process_request')
        has_process_view = hasattr(self, 'process_view')
        has_process_response = hasattr(self, 'process_response')
        has_process_exception = hasattr(self, 'process_exception')

        try:
            if has_process_request:
                self.process_request(request)

            if has_process_view:
                response = self.process_view(request, self.view, *args, **kws)
                if response is not None:
                    return response

            response = self.view(request, *args, **kws)

        except Exception, exception:
            if has_process_exception:
                return self.process_exception(request, exception)
            else:
                raise

        if has_process_response:
            response_new = self.process_response(request, response)
            if response_new is not None:
                response = response_new

        if not isinstance(response, HttpResponse):
            raise ValueError("%s did not return an HttpResponse." % self.view)

        return response

class JsonRequestMiddleware(Middleware):
    """\
    a middleware or view decorator that adds a JSON attribute to
    the request that contains either JSON post data in Python
    form, or JSON data from a JSON attribute in a GET query parameter.
    guarantees that a JSON attribute will exist for any requests,
    falling back to an empty dictionary if nothing is specified.
    """

    def process_request(self, request):
        if (
            request.method == 'POST' and
            'json_post' in request.GET
        ):
            JSON = request.raw_post_data
        elif 'json' in request.GET:
            JSON = request.GET['json']
        else:
            JSON = '{}'
        JSON = simplejson.loads(JSON)
        request.JSON = JSON


########NEW FILE########
__FILENAME__ = paginate

from itertools import chain
from decimal import Decimal
from django.core.paginator import Paginator
from djata.python.topo_sort import classify

page_range = xrange(1, 1000)
page_number = 1

speed = 1

def pairs(values):
    values = iter(values)
    at = values.next()
    try:
        while True:
            prev = at
            at = values.next()
            yield (prev, at)
    except StopIteration:
        pass

def magnitudes(number):
    n = 1
    while n < number:
        yield n
        yield n * 5
        n *= 10

def _page_range_iter(start, at, stop):
    yield [start, at, stop]
    yield [
        number for number in range(at - 2, at + 3, 1)
        if number > start and number < stop
    ]
    for magnitude in reversed(list(magnitudes(stop))):
        values = range(
            start // magnitude * magnitude,
            (stop + magnitude + 1) // magnitude * magnitude,
            magnitude
        )
        maxes = list(n for n in values if n < at)
        mins = list(n for n in values if n > at)
        yield [value for value in values if value > start and value < stop]
        if maxes: start = max(maxes)
        if mins: stop = min(mins)

def _page_range_set(start, at, stop):
    return set(reduce(lambda x, y: x + y, _page_range_iter(start, at, stop)))

def page_range(start, at, stop):
    return sorted(_page_range_set(start, at, stop))

def page_groups(start, at, stop):
    page_numbers = _page_range_set(start, at, stop)
    adjacency = (
        (a, b)
        for a in page_numbers
        for b in page_numbers
        if a == b + 1 or a == b - 1
    )
    return sorted(
        sorted(row) for row in
        classify(page_numbers, gt_pairs = adjacency)
    )

def paginate(request, context, objects, default_length = 10, default_end = 0, dimension = None):
    page_length = request.GET.get('page_length', default_length)
    page_length = int(page_length)
    paginator = Paginator(objects, page_length)
    page_number = request.GET.get('page', paginator.num_pages if default_end else 1)
    page = paginator.page(page_number)
    context['page_number'] = int(page_number)
    context['paginator'] = paginator
    context['page'] = page
    return page.object_list

__all__ = ('page_range', 'page_groups', 'paginate')

if __name__ == '__main__':
    print page_range(1, 284, 15830)
    print page_groups(1, 284, 15830)


########NEW FILE########
__FILENAME__ = iterkit
"""\
Provides tools for working with iterations, including enumerations,
boolean and transitive comparisons, and others.

Provides "any" and "all" functions for determining whether
any or all of an iteration of boolean values are true.  Provides
an enumerate function for pairing the items of an iteration
with the index of their occurence.  Provides transitive functions
for evaluating where every adjacent pair in an iteration passes
a given test, specifically all comparison relationships like
equality, inequality, less than, less than or equal to by their
two letter names: eq, ne, lt, le, gt, and ge respectively.  On that
topic, also provides |respective|, a function that returns an
iteration of tuples of the respective elements of multiple iterations.
"""

from itertools import *
from wrap import wrap
from types import GeneratorType

try:
    all = all
except NameError:
    def all(items):
        for item in items:
            if not item:
                return False
        return True

try:
    any = any
except:
    def any(items):
        for item in items:
            if item:
                return True
        return False

def transitive(function):
    def transitive(items): 
        items = iter(items)
        try:
            prev = items.next()
            while True:
                next = items.next()
                if not function(prev, next):
                    return False
            prev = next
        except StopIteration:
            pass
        return True 
    return transitive

eq = transitive(lambda x, y: x == y)
ne = transitive(lambda x, y: x != y)
lt = transitive(lambda x, y: x < y)
le = transitive(lambda x, y: x <= y)
gt = transitive(lambda x, y: x > y)
ge = transitive(lambda x, y: x >= y)

try:
    reversed = reversed
except NameError:
    def reversed(items):
        return iter(tuple(items)[::-1])

def shuffle(items, buffer = None):
    raise Exception("Not implemented.")
    if buffer is not None:
        pass
    else:
        pass

def group(predicate, items):
    raise Exception("Not implemented.")

# Apparently, enumerate is part of the builtin library now.
# Part of me is glad someone else thought the exact same
# thing would be a good idea.
enumerate = enumerate

#def enumerate(items):
#    return respective(count(), items)

respective = zip

@wrap(list)
def flatten(elements):
    for element in elements:
        if any(
            isinstance(element, klass)
            for klass in (list, tuple, GeneratorType)
        ):
            for child in flatten(element):
                yield child
        else:
            yield element

def first(elements):
    elements = iter(elements)
    return elements.next()

def unique(elements):
    visited = set()
    for element in elements:
        if element in visited:
            continue
        visited.add(element)
        yield element

if __name__ == '__main__':
    assert all(int(a) == b for a, b in respective(['0', '1', '2'], range(10)))
    assert all(eq([a, b, c]) for a, (b, c) in enumerate(enumerate(range(10))))
    assert all(lt([a, b]) for a, b in enumerate(n + 1 for n in range(10)))


########NEW FILE########
__FILENAME__ = names

# from https://cixar.com/svns/javascript/trunk/src/base.js
# by Kris Kowal

from re import compile as re

__all__ = (
    'lower',
    'upper',
    'camel',
    'title',
    'sentence',
    'split_name',
    'join_name',
)

split_name_expression = re(r'[a-z]+|[A-Z](?:[a-z]+|[A-Z]*(?![a-z]))|[.\d]+')

def split_name(name):
    return split_name_expression.findall(name)

digit_expression = re(r'\d')

def join_name(parts, delimiter = None):
    parts = list(parts)
    if delimiter is None: delimiter = '_';
    def reduction(parts, part):
        if (
            digit_expression.search(part) and
            parts and digit_expression.search(parts[-1])
        ):
            return parts + [delimiter + part]
        else:
            return parts + [part]
    return "".join(reduce(reduction, parts, []))

def lower(value, delimiter = None):
    if delimiter is None: delimiter = '_'
    return delimiter.join(
        part.lower()
        for part in split_name(value)
    )

def upper(value, delimiter = None):
    if delimiter is None: delimiter = '_'
    return delimiter.join(
        part.upper() for part in
        split_name(value)
    )

def camel(value, delimiter = None):
    return join_name(
        (
            n and part.title() or part.lower()
            for n, part in enumerate(split_name(value))
        ),
        delimiter
    )

def title(value, delimiter = None):
    return join_name(
        (
            part.title() for part in 
            split_name(value)
        ),
        delimiter
    )

def sentence(value, delimiter = None):
    if delimiter is None: delimiter = ' '
    return delimiter.join(
        n and part.lower() or part.title()
        for n, part in enumerate(split_name(value))
    )

def main():

    samples = (
        'CaseCase1_2',
        'caseCase1_2',
        'caseCase1_2',
        'case_case1_2',
        'case_case_1_2',
        'CASE_CASE1_2',
        'CASE_CASE1_2',
        'CASE_CASE_1_2',
        'case case 1 2',
    )

    oracles = (
        (lower, None, 'case_case_1_2'),
        (camel, None, 'caseCase1_2'),
        (title, None, 'CaseCase1_2'),
        (upper, None, 'CASE_CASE_1_2'),
    )

    for function, delimiter, oracle in oracles:
        for sample in samples:
            result = function(sample, delimiter) == oracle
            if not result:
                print function, sample, delimiter, function(sample, delimiter)

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = orderedclass
"""
Provides classes to permit a class to track the order in which certain
properties and nested classes are declared.  The properties of interest
must inherit ``OrderedProperty`` and assure that their super-class
``__init__``ializers are called.  Classes must inherit ``OrderedClass``.
``(name, value)`` pairs are created by the metaclass of ``OrderedClass``
in lists called ``_properties`` and ``_classes`` for ``OrderedProperty``
and ``OrderedClass`` values in the class and all of its ancestors.
You can create a dictionary from either of these lists to capture a
lookup table of the most recent declarations for each name ::

    >>> class Foo(OrderedClass):
    ...    baz = OrderedProperty()
    ...    bar = OrderedProperty()
    ...    class Baz(OrderedClass): pass
    ...    class Bar(OrderedClass):  pass
    ...

    >>> Foo._properties == [('baz', Foo.baz), ('bar', Foo.bar)]
    True

    >>> Foo._classes == [('Baz', Foo.Baz), ('Bar', Foo.Bar)]
    True

Subclasses inerherit the properties and classes of their parent
classes in reversed method resolution order::


    >>> class Qux(Foo):
    ...     qux = OrderedProperty()
    ...     class Qux(OrderedClass): pass
    ...

    >>> Qux._properties == [
    ...     ('baz', Foo.baz),
    ...     ('bar', Foo.bar),
    ...     ('qux', Qux.qux),
    ... ]
    True

    >>> Qux._classes == [
    ...     ('Baz', Foo.Baz),
    ...     ('Bar', Foo.Bar),
    ...     ('Qux', Qux.Qux),
    ... ]
    True


It's a good practice to filter theses lists for a subclass of
``OrderedClass`` or ``OrderedProperty`` that is of interest for your
particular application since parent classes might be interested in
different properties and classes.  As a reminder, in Python, when
you create a subclass with a metaclass, its metaclass must inherit
the parent class's metaclass and bubble function calls to the 
parent metaclass before running specialized code::

    >>> class QuuxProperty(OrderedProperty):
    ...     def __init__(self, n, *args, **kwargs):
    ...         super(QuuxProperty, self).__init__(*args, **kwargs)
    ...         self.n = n
    ...

    >>> class QuuxMetaclass(OrderedClass.__metaclass__):
    ...     def __init__(self, name, bases, attys):
    ...         super(QuuxMetaclass, self).__init__(name, bases, attys)
    ...         self._quux_properties = [
    ...             (name, property)
    ...             for name, property in self._properties
    ...         ]

    >>> class Quux(OrderedClass):
    ...     __metaclass__ = QuuxMetaclass
    ...     foo = OrderedProperty(1)
    ...

    >>> Quux._quux_properties == [
    ...     ('foo', Quux.foo),
    ... ]
    True


"""

from itertools import count, chain

__all__ = [
    'OrderedProperty',
    'OrderedClass',
    'OrderedMetaclass',
]

# a global counter to measure the monotonic order
# of property declarations.
_next_creation_counter = count().next
# inherits thread safty from the global interpreter lock

class OrderedProperty(object):
    def __init__(self, *args, **kws):
        self._creation_counter = _next_creation_counter()
        # pass the buck:
        super(OrderedProperty, self).__init__(*args, **kws)

class OrderedMetaclass(type):
    def __init__(self, name, bases, attrs):
        super(OrderedMetaclass, self).__init__(name, bases, attrs)
        self._creation_counter = _next_creation_counter()

        # The following code should only run after OrderedClass
        # has been declared.
        try: OrderedClass
        except NameError: return

        for ordered_name, Class in (
            ('_properties', OrderedProperty),
            ('_classes', OrderedMetaclass),
        ):
            setattr(self, ordered_name, sorted(
                (
                    (name, value)
                    for base in reversed(self.__mro__)
                    for name, value in vars(base).items()
                    if isinstance(value, Class)
                ),
                # sorted by their declaration number
                key = lambda (name, value): value._creation_counter
            ))

class OrderedClass(object):
    __metaclass__ = OrderedMetaclass

if __name__ == '__main__':

    import doctest
    doctest.testmod()


########NEW FILE########
__FILENAME__ = topo_sort
"""\
"""

from djata.python.iterkit import any, chain
from djata.python.wrap import wrap

def _topo_sorted(key, gt_dict_set, visited, inner_visited = None):

    if inner_visited is None:
        inner_visited = set()

    if key in inner_visited:
        raise Exception("cycle")

    visited.add(key)
    inner_visited.add(key)

    if key in gt_dict_set:
        for inner in gt_dict_set[key]:
            if inner in visited:
                continue
            for item in _topo_sorted(
                inner,
                gt_dict_set,
                visited,
                inner_visited
            ):
                yield item

    yield key

def _gt_dict_set(
    # you can provide any one of these arguments
    lt_dict = None,
    gt_dict = None,
    lt_pairs = None,
    gt_pairs = None,
    lt_dict_set = None,
    gt_dict_set = None,
    lt_matrix = None,
    gt_matrix = None,
    matrix_headers = None,
    inverse = False,
):
    if matrix_headers is not None:
        if lt_matrix is not None:
            lt_pairs = tuple(
                (matrix_headers[x], matrix_headers[y])
                for x in range(len(matrix_headers))
                for y in range(len(matrix_headers))
                if lt_matrix[x][y]
            )
        if gt_matrix is not None:
            gt_pairs = tuple(
                (matrix_headers[x], matrix_headers[y])
                for x in range(len(matrix_headers))
                for y in range(len(matrix_headers))
                if gt_matrix[x][y]
            )
    if lt_dict is not None:
        lt_pairs = lt_dict.items()
    if gt_dict is not None:
        gt_pairs = gt_dict.items()
    if lt_pairs is not None:
        lt_dict_set = dict_set_from_pairs(lt_pairs)
    if gt_pairs is not None:
        gt_dict_set = dict_set_from_pairs(gt_pairs)
    if lt_dict_set is not None:
        gt_dict_set = inverse_dict_set(lt_dict_set)
    if gt_dict_set is None:
        gt_dict_set = {}
    if inverse:
        gt_dict_set = inverse_dict_set(gt_dict_set)
    return gt_dict_set

def topo_sorted_iter(
    items,
    lt_dict = None,
    gt_dict = None,
    lt_pairs = None,
    gt_pairs = None,
    lt_dict_set = None,
    gt_dict_set = None,
    lt_matrix = None,
    gt_matrix = None,
    matrix_headers = None,
    inverse = False,
):
    """\
    """

    gt_dict_set = _gt_dict_set(
        lt_dict = lt_dict,
        gt_dict = gt_dict,
        lt_pairs = lt_pairs,
        gt_pairs = gt_pairs,
        lt_dict_set = lt_dict_set,
        gt_dict_set = gt_dict_set,
        lt_matrix = lt_matrix,
        gt_matrix = gt_matrix,
        matrix_headers = matrix_headers,
        inverse = inverse,
    )

    visited = set()

    for key in items:
        if key not in visited:
            for line in _topo_sorted(key, gt_dict_set, visited):
                yield line

topo_sorted = wrap(list)(topo_sorted_iter)

def classify_iter(
    items,
    lt_dict = None,
    gt_dict = None,
    lt_pairs = None,
    gt_pairs = None,
    lt_dict_set = None,
    gt_dict_set = None,
    lt_matrix = None,
    gt_matrix = None,
    matrix_headers = None,
    inverse = False,
):
    """\
    """

    gt_dict_set = _gt_dict_set(
        lt_dict = lt_dict,
        gt_dict = gt_dict,
        lt_pairs = lt_pairs,
        gt_pairs = gt_pairs,
        lt_dict_set = lt_dict_set,
        gt_dict_set = gt_dict_set,
        lt_matrix = lt_matrix,
        gt_matrix = gt_matrix,
        matrix_headers = matrix_headers,
        inverse = inverse,
    )

    visited = set()

    for key in items:
        if key not in visited:
            yield list(_topo_sorted(key, gt_dict_set, visited))

classify = wrap(list)(classify_iter)

def dict_set_from_pairs(pairs):
    result = {}
    for a, b in pairs:
        if not a in result:
            result[a] = set()
        result[a].add(b)
    return result

@wrap(dict)
def dict_set_from_dict(pairs):
    for a, b in pairs.items():
        yield a, set((b,))

@wrap(dict_set_from_pairs)
def inverse_dict_set(pairs):
    for a, bs in pairs.items():
        for b in bs:
            yield b, a

class relation(object):
    def __init__(self, function):
        self.function = function
    def __getitem__(self, key):
        return self.function(key)

if __name__ == '__main__':
    print topo_sorted([1,2,3])
    print topo_sorted([1,2,3], {1: 2, 2: 3})
    print topo_sorted([1,2,3], gt_dict = {3: 2, 2: 1})
    print topo_sorted([1,2,3], lt_pairs = [(1, 2), (2, 3)])
    print topo_sorted([1,2,3], gt_pairs = [(2, 1), (3, 2)])
    print topo_sorted([1,2,3], lt_dict_set = {1: [2, 3], 2: [3]})
    print topo_sorted([1,2,3], gt_dict_set = {3: (2, 1), 2: (1,)})
    print topo_sorted([1,2,3], lt_dict_set = {3: (2, 1), 2: (1,)}, inverse = True)
    print topo_sorted([1,2,3], matrix_headers = [1, 2, 3], lt_matrix = (
        (0, 1, 0),
        (0, 0, 1),
        (0, 0, 0),
    ))


########NEW FILE########
__FILENAME__ = wrap

def wrap(wrapper):
    def wrap_this_function(function):
        def wrapped_function(*arguments, **keywords):
            return wrapper(function(*arguments, **keywords))
        return wrapped_function
    return wrap_this_function

if __name__ == '__main__':

    @wrap(list)
    def foo():
        yield "a"
    print foo()


########NEW FILE########
__FILENAME__ = rules
"""\
provides functions for creating Django queries
from predicate data structures.
"""

from django.db.models import Q

def parse_rules(*rules):
    """\
    parses notaion for representing sentential filter rules
    as a query value in a URL and produces
    a Django ``Q`` query.
    """

    return R([None, None, [
        rule.split(u',')
        for rule in rules
    ], u'all'])

def R(rule):
    """\
    constructs a Django ``Q`` query, suitable for
    use as an argument to a queryset's ``filter``
    method from a parsed JSON predicate structure.

    Rules are recursive lists of strings of this
    form::

        predicate   := [subject, verb, object] |
                       [None, None, [predicate, ...], "any" | "all"] |
                       [None, None, predicate, "not"];
        verb        := "exact" | "iexact" |
                       "startswith" | "istartswith" |
                       "endswith" | "iendswith" |
                       "lt" | "gt" | "lte" | "gte" |
                       "year" | "month" | "day" |
                       "contains" | "icontains" |
                       "range" |
                       "search";

    ``subject`` is a symbol string and the type of ``object``
    depends on the ``verb``.  Most verbs accept strings;
    "in" requires a container (``list``, ``tuple``, etc);
    "range" requires a duple of a start and stop.
    """

    if len(rule) == 3:
        subject, verb, object = rule
        assert '__' not in subject, '"Subject names cannot contain "__".'
        return Q(**{
            (u'%s__%s' % (
                 u'__'.join(subject.split(u'.')),
                 verb
            )).encode('utf-8'): object
        })

    elif len(rule) == 4:
        dontcare, dontcare, rules, conjunction = rule

        if conjunction == 'not':
            assert False, "Rules do not yet support 'not'."

        return reduce(
            {
                u'all': lambda x, y: x & y,
                u'any': lambda x, y: x | y,
            }[conjunction],
            [
                R(rule)
                for rule in rules
            ]
        )

    else:
        assert False, (
            u"Rules require three or four terms, not %d." %
            len(rule)
        )


########NEW FILE########
__FILENAME__ = urls

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^(?:\.(?P<format>[^/]*)|/|)$', 'djata.views.respond'),
    (r'^/(?P<view_name>[^/\.]*)(?=/|\.)', include('djata.urls_model')),
)


########NEW FILE########
__FILENAME__ = urls_model

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^(?:\.(?P<format>[^/]*)|/|)$', 'djata.views.respond'),
    (r'^/', include('djata.urls_model_root')),
)


########NEW FILE########
__FILENAME__ = urls_model_root

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'djata.views.respond'),
    (r'^~(?P<meta_page>.*)$', 'djata.views.respond'),
    (r'^(?P<pk>[^/&\.]+)/(?P<field_name>.*)$', 'djata.views.respond'),
    (r'^(?P<pk>[^/&\.]+)(?:\.(?P<format>[^/]*))?$', 'djata.views.respond'),
    (r'^(?P<pks>(?:[^/&\.]&?)+)(?:\.(?P<format>[^/]*))?$', 'djata.views.respond'),
)


########NEW FILE########
__FILENAME__ = urls_root
# deprecated

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'djata.views.respond'),
    (r'^(?P<view_name>[^/\.]*)(?=/|\.)', include('djata.urls_model')),
)


########NEW FILE########
__FILENAME__ = views

# select
# where
# order
#.limit
#.ranges

# pagination
# interpolated page numbers
# read
# write
# authentication/authorization
#.django field declarations
# multiple customized views
# multiple customized parsers
# multiple customized formatters
#.json/get input
#.application keys
#.field links
#.field filters
#.grouping
#.bordered text format

# html table no display headers

import string
from types import ModuleType, FunctionType
from urllib import quote
from urllib2 import unquote
from os.path import join
from itertools import chain

from django.db.models import Model
from django.template import RequestContext, loader, TemplateDoesNotExist
from django.http import HttpResponse, HttpResponseServerError, \
    HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotAllowed
from django.core.exceptions import ObjectDoesNotExist, FieldError
import django.forms as forms
from django.conf import settings

from djata.python.names import *
from djata.python.orderedclass import \
     OrderedClass, OrderedProperty, OrderedMetaclass
from djata.python.iterkit import unique
from djata.paginate import page_groups
from djata.rules import *
from djata.exceptions import *
from djata.formats import *
from django.db.models import ForeignKey

class ViewOptions(object):
    visible = True

class ViewMetaclass(OrderedMetaclass):

    def __init__(self, name, bases, attys):
        super(ViewMetaclass, self).__init__(name, bases, attys)

        if self.abstract:
            return

        # module
        self.init_module()
        # meta
        self.init_meta()
        # model
        self.init_model()
        # views, module.views
        self.init_views()

        # fields, objects, verbose_name, verbose_name_plural
        self.init_objects_fields_names()

        # pertaining to include_fields, exclude_fields, and
        # custom Field views
        self.init_fields() # fields
        self.init_actions_methods()
        self.init_formats_parsers()
        self.init_default_format()
        self.init_index()

        self.base_url = self.get('base_url')
        self.insecure = self.get('insecure', False)

        self.update_views()

    def get(self, name, value = None):
        # places to check, in priority order:
        # view, view.meta
        # views
        # model, model.meta
        # module
        model = self.model
        meta = self.meta
        model_meta = getattr(model, '_meta')
        views = getattr(self, 'views', None)
        return getattr(self, name,
            getattr(meta, name,
                getattr(views, name,
                    getattr(model, name,
                        getattr(model_meta, name,
                            getattr(self.module, name,
                                value
                            )
                        )
                    )
                )
            )
        )

    @property
    def abstract(self):
        return (
            hasattr(self, 'Meta') and 
            hasattr(self.Meta, 'abstract') and
            self.Meta.abstract
        )

    def get_module(self):
        # discover the module that contains the model view
        if self.__module__ is None:
            return
        return __import__(
            self.__module__,
            {}, {}, [self.__name__]
        )

    def init_module(self):
        self.module = self.get_module()

    @property
    def Views(self):
        return self.get('Views')

    def init_views(self):
        self.views = self.get_views()

    def get_views(self):
        views = getattr(self.meta, 'views', getattr(self.module, 'views', None))
        assert views is not None or self.module is not None, \
            'View %s does not reference its parent views.  ' \
            'The containing module is %s.' % (self, self.module)
        if views is None:
            Views = self.Views
            views = Views()
            if self.module is not None:
                # memoize
                self.module.views = views
        return views

    def update_views(self):
        views = self.views
        views.add_object_view(self.verbose_name, self)
        views.add_model_view(self.verbose_name_plural.__str__(), self)

    def init_meta(self):
        if 'Meta' in self.__dict__:
            class Meta(ViewOptions):
                pass
            for name, value in vars(self.__dict__['Meta']).items():
                if not name.startswith('__'):
                    setattr(Meta, name, value)
        else:
            Meta = ViewOptions
        self.meta = Meta()

    def get_model(self):
        # attempt to grab a model from the containing module's "models"
        #  value
        if hasattr(self.meta, 'model'):
            return self.meta.model
        if hasattr(self.module, 'models'):
            return getattr(self.module.models, self.__name__, None)

    def init_model(self):
        self.model = self.get_model()

    def init_objects_fields_names(self):
        model = self.model
        meta = self.meta
        model_meta = getattr(model, '_meta')

        self.objects = self.get('objects')
        self.fields = self.get('fields')

        assert model is not None or hasattr(meta, 'objects') or hasattr(self,
        'objects'), 'View %s does not define its "objects" property, a '\
        '"meta.objects" property, a "meta.model.objects" property, and the '\
        'containing module does not provide a "models" property with a model '\
        'with the same name' % self

        self.verbose_name = self.get('verbose_name')
        assert self.verbose_name is not None, 'View %s does not define a'\
        '"verbose_name", "Meta.verbose_name", provide a model with a'\
        '"verbose_name"'

        self.verbose_name_plural = self.get('verbose_name_plural') or\
        "%ss" % self.verbose_name

    def init_fields(self):
        meta = self.meta
        fields = self.fields

        exclude_fields = set(getattr(meta, 'exclude_fields', ()))
        self.fields = [
            field for field in fields
            if field.name not in exclude_fields
        ]
        self.fields.extend([
            value.dub(self, name)
            for (name, value) in self._properties
            if isinstance(value, Field)
        ])
        if hasattr(meta, 'include_fields'):
            fields = dict(
                (field.name, field)
                for field in self.fields
            )
            self.fields = [
                fields[field_name]
                for field_name in meta.include_fields
            ]

    def init_actions_methods(self):
        meta = self.meta

        # build dictionaries for looking up properties
        for prefix, property in (
            ('action', 'actions'),
            ('method', 'methods'),
        ):
            pairs = [
                (name.split('_', 1)[1], value)
                for base in self.__mro__[::-1]
                for name, value in vars(base).items()
                if name.startswith('%s_' % prefix) and
                name.split('_', 1)[1] not in
                getattr(meta, 'exclude_%s' % property, ())
            ]
            setattr(self, '_%s' % property, [name for name, value in pairs])
            setattr(self, '_%s_lookup' % property, dict(pairs))

    def init_formats_parsers(self):
        meta = self.meta

        # formatters
        for variable, type in (
            ('model_formats', ModelFormat),
            ('object_formats', ObjectFormat),
            ('model_parsers', ModelParser),
            ('object_parsers', ObjectParser),
            ('model_pages', ModelPage),
            ('object_pages', ObjectPage),
        ):
            exclude = getattr(meta, 'exclude_%s' % variable, ())
            pairs = [
                value.dub(self, name)
                for name, value in self._classes
                if issubclass(value, type) and name not in exclude
            ]
            setattr(self, '_%s' % variable, tuple(unique(name for name, value in pairs)))
            setattr(self, '_%s_lookup' % variable, dict(pairs))

    def init_default_format(self):
        self.default_format = self.get('default_format')

    def init_index(self):
        model = self.model
        meta = self.meta

        # index
        self.index = model._meta.pk
        if hasattr(meta, 'index'):
            self.index, ingore, ignore, ignore = \
                    model._meta.get_field_by_name(meta.index)

class ViewBase(OrderedClass):

    __metaclass__ = ViewMetaclass

    class Meta:
        abstract = True

    content_types = {
        'application/x-www-urlencoded': 'urlencoded',
        'application/x-www-form-urlencoded': 'urlencoded',
    }

    def __init__(self, request, view, pk, pks, format):
        self._request = request
        self._view = view
        self._pk = pk
        self._pks = pks
        self._format = format

    def get_url_of_object(self, object):
        #return self.views.get_view_of_object(object).get_object_url(object)
        return self.views.get_url_of_object(object)

    def get_url_of_model(self, model):
        views = self.views
        view = views.get_view_of_model(model)
        return view.get_model_url()

    @classmethod
    def get_objects_url(self):
        return self.get_model_url()

    @classmethod
    def get_model_url(self):
        return '%s/%s.%s' % (
            self.base_url,
            self.verbose_name_plural,
            'html'
        )

    @classmethod
    def get_models_url(self):
        return '%s/' % self.base_url

    @classmethod
    def respond(
        self,
        request,
        view,
        pk = None,
        pks = None,
        format = None,
        field_name = None,
        responder = None,
        meta_page = None,
    ):

        pk, pks = self.normalize_pks(pk, pks)
        responder = self(request, view, pk, pks, format,)

        if field_name is not None:
            raise NotYetImplemented("Individual field names.")

        request.context['view'] = responder

        action = responder.negotiate_action()
        if action is not None:
            if action not in self._actions:
                raise NoSuchActionError(action)
            return self._actions_lookup[action](responder)
        method = request.method.lower()
        if method not in self._methods:
            raise NoSuchMethodError(
                "No action specified in the query-string, "
                "nor method provided for %s (from %s)" % (
                    repr(method),
                    repr(self._methods),
                )
            )
        return self._methods_lookup[method](responder)

    @classmethod
    def normalize_pks(self, pk = None, pks = None):
        to_python = self.index.to_python
        if pk is not None:
            pk = to_python(unquote(pk))
        if pks is not None:
            pks = [
                to_python(unquote(key))
                for key in pks.rstrip('&').split('&')
            ]
        return pk, pks

    def negotiate_action(self):
        request = self._request
        if 'action' in request.GET:
            return request.GET['action']
        for action in self._actions:
            if action in request.GET:
                return action


    # METHODS

    def method_get(self):
        return self.action_read()

    def method_put(self):
        return self.action_write()

    def method_post(self):
        # XXX django template for error with inspection
        #  of the available methods and actions.
        raise PostActionError(self._actions)


    # ACTIONS

    def action_read(self):
        self.authorize_read()
        request = self._request
        if request.method == 'POST':
            # allow JSON queries for read (eventually other formats too)
            request.JSON = json.loads(request.raw_post_data)
        return self.format()

    def action_write(self):
        if self._view == 'model':
            raise NotYetImplemented('write model (try writing the objects individually).')
        elif self._view == 'object':
            try:
                object = self.get_object()
                # change
                self.authorize_change()
                fields = self.get_fields()
                updates = self.parse_object()
                for field in fields:
                    if field.attname in updates:
                        setattr(object, field.attname, updates[field.attname])
                object.save()
                self._object = object
            except self.model.DoesNotExist:
                # add
                self.authorize_add()
                object = self.parse_object()
                object = self.model.objects.create(**object)
                object.save()
                self._object = object
            return HttpResponseRedirect(self.get_url_of_object(object))

    def action_add(self):
        self.authorize_add()
        object = self.parse_object()
        object = self.model.objects.create(**object)
        object.save()
        self._object = object
        return HttpResponseRedirect(self.get_url_of_object(object))

    def action_change(self):
        self.authorize_change()
        if self._view == 'model':
            raise NotYetImplemented()
        elif self._view == 'object':
            object = self.get_object()
            fields = self.get_fields()
            updates = self.parse_object()
            for field in fields:
                if field.attname in updates:
                    setattr(object, field.attname, updates[field.attname])
            object.save()
            self._object = object
        return HttpResponseRedirect(self.get_url_of_object(object))

    def action_delete(self):
        self.authorize_delete()
        if self._view == 'model':
            objects = self.get_objects()
            for object in objects:
                object.delete()
            return HttpResponseRedirect(self.get_url_of_model(self.model))
        elif self._view == 'object':
            object = self.get_object()
            object.delete()
            return HttpResponseRedirect(self.get_url_of_model(self.model))


    # FORMAT RESPONSES

    def format(self):
        format = self.negotiate_format()
        if self._view == 'model':
            if format not in self._model_formats:
                raise ModelFormatNotAvailable(format)
            formatter = self._model_formats_lookup[format]
        elif self._view == 'object':
            if format not in self._object_formats:
                raise ObjectFormatNotAvailable(format, self._object_formats)
            formatter = self._object_formats_lookup[format]
        content_type = self.negotiate_format_content_type(formatter)
        content = formatter(self._request, self)
        return HttpResponse(content, mimetype = content_type)

    def negotiate_format(self):
        request = self._request
        format = self._format
        if hasattr(self.meta, 'format'):
            if format is not None and format != self.meta.format:
                raise NotExactSupportedFormatError(format, self.meta.format)
            return self.meta.format
        elif 'format' in request.JSON:
            format = request.JSON['format']
        elif 'format' in request.GET:
            format = request.GET['format']
        elif format is None:
            if 'ACCEPT' in request.META:
                self.content_types
                # XXX content negotiation
            format = getattr(self.meta, 'default_format', None)
            if format is None:
                format = getattr(getattr(self, 'module', None), 'default_format', None)
            if format is None:
                raise NoFormatSpecifiedError()
        return format

    def negotiate_format_content_type(self, format):
        request = self._request
        content_type = format.content_type
        if 'content_type' in request.GET:
            content_type = str(request.GET['content_type'])
        if content_type is None:
            raise NoFormatContentTypeError(format.name)
        return content_type


    # PARSE REQUESTS

    def parse_object(self):
        parser = self.negotiate_parser()
        if parser not in self._object_parsers:
            raise ObjectParserNotAvailable(parser)
        parser = self._object_parsers_lookup[parser]
        return parser(self._request, self)

    def parse(self):
        parser = self.negotiate_parser()
        if self._view == 'model':
            if parser not in self._model_parsers:
                raise ModelParserNotAvailable(parser)
            parser = self._model_formats_lookup[format]
        elif self._view == 'object':
            if format not in self._object_formats:
                raise ObjectFormatNotAvailable(format)
            formatter = self._object_formats_lookup[format]
        raise ModelParserNotAvailable(format)

    def negotiate_parser(self):
        request = self._request
        parser = self.negotiate_format()
        if hasattr(self.meta, 'parser'):
            parser = self.meta.parser
        elif 'parser' in request.JSON:
            parser = reuqest.JSON['parser']
        elif 'parser' in request.GET:
            parser = request.GET['parser']
        elif 'CONTENT_TYPE' in request.META and request.META['CONTENT_TYPE']:
            parser = self.content_types[request.META['CONTENT_TYPE']]
        if parser is None:
            raise NoParserSpecifiedError()
        return parser


    # TABLE STUFF

    def get_fields(self):
        request = self._request
        fields = self.fields

        # eclude fields that refer to models that are
        # have no corresponding view
        fields = [
            field for field in fields
            if not isinstance(field, ForeignKey)
            or field.rel.to in self.meta.views.view_of_model
        ]

        select = None
        if 'select' in request.JSON:
            select = request.JSON['select']
        if 'select' in request.GET:
            select = request.GET['select'].split(',')
        if select is not None:
            field_dict = dict(
                (field.name, field)
                for field in fields
            )
            non_existant_fields = [
                name for name in select
                if name not in field_dict
            ]
            if non_existant_fields:
                raise NonExistantFieldsError(non_existant_fields)
            fields = list(field_dict[name] for name in select)

        return fields

    def get_child_fields(self):
        model = self.model
        model_meta = model._meta
        return [
            field
            for field, model, direct, m2m in (
                model_meta.get_field_by_name(name)
                for name in model_meta.get_all_field_names()
            ) if not direct and not m2m
        ]

    def get_related_fields(self):
        model = self.model
        model_meta = model._meta
        return [
            field
            for field, model, direct, m2m in (
                model_meta.get_field_by_name(name)
                for name in model_meta.get_all_field_names()
            ) if m2m
        ]

    def get_objects(self):
        if hasattr(self, '_objects'):
            return self._objects
        objects = self.__get_objects()
        objects = objects.all()
        objects = self.paginate_for_request(objects)
        return objects

    def get_object(self):
        request = self._request
        if hasattr(self, '_object'):
            return self._object
        try:
            return self.__get_objects().get()
        except ObjectDoesNotExist, exception:
            raise NoSuchObjectError()

    def __get_objects(self):
        request = self._request
        objects = self.objects

        if self._pk is not None:
            objects = objects.filter(**{
                '%s__exact' % self.index.name: self._pk
            })
        if self._pks is not None:
            objects = objects.filter(**{
                '%s__in' % self.index.name: self._pks
            })

        objects = self.order(objects)
        objects = self.filter(objects)
        objects = self.filter_for_user(objects)
        
        return objects

    def filter(self, objects):
        request = self._request

        for field in self.fields:

            name = field.name
            foreign = hasattr(field, 'rel') and hasattr(field.rel, 'to')

            if name in request.GET:
                value = field.to_python(request.GET[name])
                objects = objects.filter(**{name: value})

                # for foreign keys
                if foreign:
                    object = field.rel.to.objects.get(pk = value)

                    # add the field's object to the list of filters
                    #  for the rendering context
                    filters = request.context.get('filters', [])
                    filters.append(object)
                    request.context['filters'] = filters

                    request.context[name] = object

            if foreign:
                attname = field.attname
                if attname in request.GET:
                    value = field.to_python(request.GET[attname])
                    objects = objects.filter(**{name: value})

            if foreign:
                plural = field.rel.to._meta.verbose_name_plural[:]
            else:
                plural = field.name + 's'

            if plural in request.GET:
                values = [
                    field.to_python(unquote(value))
                    for value in request.GET[plural].split(",")
                ]
                objects = objects.filter(**{
                    '%s__in' % name: values
                })

        if 'where' in request.JSON:
            objects = objects.filter(R(request.JSON['where']))
        if 'where' in request.GET:
            objects = objects.filter(parse_rules(*request.GET.getlist('where')))

        return objects

    def filter_for_user(self, objects):
        return objects

    def paginate(self, objects, page_number, page_length):
        request = self._request
        from django.core.paginator import Paginator
        paginator = Paginator(objects, page_length)
        if page_number == 0:
            raise EmptyPageError(0)
        elif page_number < 1:
            page_number = paginator.num_pages + page_number + 1
        try:
            page = paginator.page(page_number)
        except:
            raise EmptyPageError(page_number)
        request.context['paginator'] = paginator
        request.context['page'] = page
        request.context['page_groups'] = page_groups(
            1,
            page.number,
            paginator.num_pages
        )
        return page.object_list

    @classmethod
    def page_ranges(self, paginator, page):
        page_range = paginator.page_range
        if len(page_ranges) < 10:
            return [page_range]
        elif page_number in page_ranges[:10]:
            return [page_range]
        elif page_number in page_ranges[-10:]:
            return [page_range]
        else:
            return [range(page_range - 2, page_range + 3)]


    def paginate_for_request(self, objects):
        request = self._request

        if hasattr(self.meta, 'page_length'):
            page_length = self.meta.page_length
            request.context['fixed_page_length'] = True
        else:
            default_page_length = getattr(self.meta, 'default_page_length', None)
            page_length = request.JSON.get(
                'pageLength',
                request.GET.get('page_length', default_page_length)
            )
            if page_length == '':
                page_length = None
            elif isinstance(page_length, basestring):
                try:
                    page_length = long(page_length) 
                except ValueError:
                    raise PageLengthMustBeNumberError(page_length)

        default_page_number = getattr(self.meta, 'default_page_number', 1)
        page_number = request.JSON.get(
            'page',
            request.GET.get('page', default_page_number)
        )
        if page_number == '':
            page_number = default_page_number
        if isinstance(page_number, basestring):
            try:
                page_number = long(page_number)
            except ValueError:
                raise PageNumberMustBeNumberError(page_number)

        require_pagination = getattr(self.meta, 'require_pagination', False)
        if page_length is None and require_pagination:
            raise PaginationRequiredError()

        if page_length is not None:
            if hasattr(self.meta, 'max_page_length'):
                if page_length > self.meta.max_page_length:
                    raise Exception("")
            objects = self.paginate(
                objects,
                page_number,
                page_length
            )

        return objects


    def order(self, objects):
        request = self._request

        field_names = []
        if 'order' in request.GET:
            field_names.extend(
                field_name
                for field_names in request.GET.getlist('order')
                for field_name in field_names.split(',')
            )
        if 'order' in request.JSON:
            field_names.extend(request.JSON['order'])

        field_names.append(self.model._meta.pk.name)

        field_names = [
            "__".join(field_name.split('.'))
            for field_name in field_names
        ]
        objects = objects.order_by(*field_names)

        return objects


    # AUTHORIZATION

    def authorize_read(self):
        request = self._request
        if self.insecure:
            return True
        if hasattr(self.model._meta, 'get_read_permission'):
            if not user.is_authenticated():
                raise NotAuthenticatedError()
            if not request.user.has_permission('%s.%s' % (
                meta.app_label,
                meta.get_read_permission()
            )):
                raise PermissionDeniedError('read')
        elif 'can_read' in self.model._meta.permissions:
            if not user.is_authenticated():
                raise NotAuthenticatedError()
            if not request.user.has_permission('%s.%s' % (
                meta.app_label,
                 'can_read',
            )):
                raise PermissionDeniedError('read')

    def authorize_add(self):
        request = self._request
        if self.insecure:
            return True
        if not request.user.is_authenticated():
            raise NotAuthenticatedError()
        if not request.user.has_permission('%s.%s' % (
            meta.app_label,
            meta.get_add_permission()
        )):
            raise Exception("You cannot pass!")

    def authorize_change(self):
        request = self._request
        if self.insecure:
            return True
        if not request.user.is_authenticated():
            raise NotAuthenticatedError()
        if not request.user.has_permission('%s.%s' % (
            meta.app_label,
            meta.get_change_permission()
        )):
            raise Exception("You cannot pass!")

    def authorize_delete(self):
        request = self._request
        if self.insecure:
            return True
        if not request.user.is_authenticated():
            raise NotAuthenticatedError()
        if not request.user.has_permission('%s.%s' % (
            meta.app_label,
            meta.get_delete_permission()
        )):
            raise Exception("You cannot pass!")


    # stubs for TemplateFormats

    def process(self, request):
        pass

    def process_extra(self, request):
        pass


class View(ViewBase):

    default_format = 'html'

    class Meta:
        abstract = True

    # model formats
    class JsonModelFormat(JsonModelFormat):
        label = 'JSON'
        description = 'A data serialization format based on JavaScript'
    class JsonpModelFormat(JsonpModelFormat):
        label = 'JSONP'
        description = 'JSON with callbacks for cross domain script injection'
    class HtmlModelFormat(HtmlModelFormat):
        label = 'HTML'
    class BasicHtmlModelFormat(HtmlModelFormat):
        name = 'basic.html'
        label = 'Basic HTML'
        description = 'Normal HTML is often overridden to expose a more focused view; basic HTML hides nothing and exposes nothing extra.'
    class RawHtmlModelFormat(RawHtmlModelFormat):
        label = 'Raw HTML'
        description = 'An HTML fragment for AJAX or proxies'
    class UploadHtmlModelFormat(UploadHtmlModelFormat):
        label = 'Upload'
    class TextModelFormat(TextModelFormat):
        label = 'Formatted Text (<tt>text</tt>)'
    class TxtModelFormat(TextModelFormat):
        name = 'txt'
        label = 'Formatted Text (<tt>txt</tt>)'
    class CsvModelFormat(CsvModelFormat):
        label = 'Comma Separated Values Spreadsheet'
    try:
        class XlsModelFormat(XlsModelFormat):
            label = 'Excel Spreadsheet'
    except NameError:
         pass

    # object formats
    class HtmlObjectFormat(HtmlObjectFormat):
        label = 'HTML'
    class BasicHtmlObjectFormat(HtmlObjectFormat):
        name = 'basic.html'
        label = 'Basic HTML'
        description = 'Normal HTML is often overridden to expose a more focused view; basic HTML hides nothing and exposes nothing extra.'
    class RawHtmlObjectFormat(RawHtmlObjectFormat):
        label = 'Raw HTML'
        description = 'An HTML fragment for AJAX or proxies'
    class JsonObjectFormat(JsonObjectFormat):
        label = 'JSON'
        description = 'A data serialization format based on JavaScript'
    class JsonpObjectFormat(JsonpObjectFormat):
        label = 'JSONP'
        description = 'JSON with callbacks for cross domain script injection'

    class TextObjectFormat(TextObjectFormat):
        label = 'Formatted text (<tt>text</tt>)'
    class TxtObjectFormat(TextObjectFormat):
        name = 'txt'
        label = 'Formatted text (<tt>txt</tt>)'
    class UrlencodedObjectFormat(UrlencodedObjectFormat):
        label = 'URL encoded data'

    class AddHtmlObjectFormat(AddHtmlObjectFormat): pass
    class EditHtmlObjectFormat(EditHtmlObjectFormat): pass

    class VerifyDeleteHtmlObjectFormat(HtmlObjectFormat):
        name = 'verify-delete.html'
        template = 'djata/object.verify-delete.html'
        label = 'Delete&hellip;'
        is_action = True

    # model parsers
    class CsvModelParser(CsvModelParser): pass

    # object parsers
    class UrlencodedObjectParser(UrlencodedObjectParser): pass
    class UrlqueryObjectParser(UrlqueryObjectParser): pass

class Views(object):

    def __init__(self):
        self.model_views = {}
        self.model_view_names = {}
        self.object_views = {}
        self.object_view_names = {}
        self.view_of_model = {}

    def add_model_view(self, name, view):
        self.model_views[name] = view
        self.model_view_names[view] = name
        self.view_of_model[view.model] = view

    def add_object_view(self, name, view):
        self.object_views[name] = view
        self.object_view_names[view] = name
        self.view_of_model[view.model] = view

    def get_view_of_object(self, object):
        model = object._base_manager.model
        return self.view_of_model[model]

    def get_view_of_model(self, model):
        return self.view_of_model[model]

    def get_url_of_object(self, object, format = None):
        model = object._base_manager.model
        if model not in self.view_of_model:
            return
        view = self.view_of_model[model]
        index = view.index.value_from_object(object)
        view_name = self.object_view_names[view]
        url = view.base_url
        if url is None:
            return '#'
        if format is None and view.default_format:
            format = view.default_format
        if format is None:
            return '%s/%s/%s/' % (url, view_name, index,)
        else:
            return '%s/%s/%s.%s' % (url, view_name, index, format,)

    def respond(
        self,
        request,
        view_name = None,
        pk = None,
        pks = None,
        format = None,
        field_name = None,
        meta_page = None,
    ):
        if view_name is not None:
            lookup = dict(
                (name, (view, responder))
                for responders, view in (
                    (self.model_views, 'model'),
                    (self.object_views, 'object'),
                )
                for name, responder in responders.items()
            )
            if view_name in lookup:
                view, responder = lookup[view_name]
                return responder.respond(
                    request,
                    view = view,
                    pk = pk,
                    pks = pks,
                    format = format,
                    field_name = field_name,
                    meta_page = meta_page,
                )
            raise NoSuchViewError(view_name)
        else:
            return self(request)

    template = 'djata/models.html'
    response_class = HttpResponse

    def __call__(self, request):
        self.process(request)
        self.process_extra(request)
        context = request.context
        template = loader.get_template(self.template)
        response = template.render(context)
        return self.response_class(response)

    def process(self, request):
        request.context['views'] = [
            view.meta
            for view in sorted(
                self.model_views.values(),
                key = lambda view: view._creation_counter
            )
            if view.meta.visible
        ]

    def process_extra(self, request):
        pass

class ViewsFromModelsMetaclass(type):

    def __init__(self, name, bases, attys):
        super(ViewsFromModelsMetaclass, self).__init__(name, bases, attys)
        if self.__module__ == ViewsFromModelsMetaclass.__module__:
            return
        self.module = self.get_module()
        self.exclude = getattr(self, 'exclude', set())
        models = self.models = self.module.models
        views = self.module.views = self()
        views.init_views_from_models()

    def get_module(self):
        # discover the module that contains the model view
        if self.__module__ is None:
            return
        return __import__(
            self.__module__,
            {}, {}, [self.__name__]
        )

class ViewsFromModels(Views):
    __metaclass__ = ViewsFromModelsMetaclass

    def init_views_from_models(self):
        for model_name, model in vars(self.models).items():
            if model_name in self.exclude:
                continue
            if (
                not isinstance(model, type) or
                not issubclass(model, Model)
            ):
                continue
            ViewMetaclass(model_name, (View,), {
                "Meta": type('Meta', (object,), {
                    "model": model,
                    "views": self,
                    "verbose_name": lower(model_name, '-'),
                    "verbose_name_plural": lower(model_name, '-') + 's',
                }),
                "__module__": self.__module__
            })

class Url(object):

    def __init__(self, request = None, path = None, query = None, terminal = None):
        if request is not None:
            self.path = request.path
            self.query = request.GET.copy()
            self.terminal = None
        else:
            self.path = path
            self.query = query.copy()
            if terminal in self.query:
                del self.query[terminal]
            self.terminal = terminal

    def __delitem__(self, key):
        del self.query[key]

    def __getattr__(self, terminal):
        if terminal in self.query:
            del self.query[terminal]
        return Url(
            path = self.path,
            query = self.query,
            terminal = terminal,
        )

    def __unicode__(self):
        from itertools import chain
        return u'%s?%s' % (
            self.path,
            u"&".join(
                part for part in (
                    chain(
                        (
                            u"%s=%s" % (quote(key), quote(value))
                            for key, values in self.query.lists()
                            for value in values
                        ),
                        (
                            self.terminal,
                        )
                    )
                )
                if part is not None
            ),
        )

class Request(object):
    def __init__(self, _parent, **kws):
        super(Request, self).__init__()
        for name, value in kws.items():
            setattr(self, name, value)
        self._parent = _parent
    def __getattr__(self, *args):
        if self._parent is not None:
            return getattr(self._parent, *args)
        else:
            raise AttributeError(args[0])

def respond(request, **kws):
    return respond_kws(request, **kws)

def respond_kws(
    request,
    module = None,
    module_name = None,
    model = None,
    view_name = None,
    pk = None,
    pks = None,
    format = None,
    field_name = None,
    meta_page = None,
):

    context = RequestContext(request)
    context['settings'] = settings
    context['url'] = Url(request = request)
    request = Request(
        request,
        view_name = view_name,
        pk = pk,
        pks = pks,
        format = format,
        field_name = field_name,
        meta_page = meta_page,
        context = context,
        JSON = {},
    )

    request.context = RequestContext(request)
    request.context['settings'] = settings
    request.context['url'] = Url(request = request)
    request.JSON = {}

    if model is not None:
        if isinstance(model, basestring):
            pass
        else:
            pass
    if module is not None:
        if isinstance(module, basestring):
            pass
        else:
            pass

    try:
        try:
            module = __import__(module_name, {}, {}, [view_name])
            views = module.views
            return views.respond(
                request,
                view_name = view_name,
                pk = pk,
                pks = pks,
                format = format,
                field_name = field_name,
                meta_page = meta_page,
            )
        except Exception, exception:
            # render a text/plain exception for Python's urllib
            if (
                'HTTP_USER_AGENT' in request.META and
                'urllib' in request.META['HTTP_USER_AGENT']
            ):
                import traceback
                HttpResponseClass = HttpResponseServerError
                if isinstance(exception, UserError):
                    HttpResponseClass = exception.response_class
                return HttpResponseClass(traceback.format_exc(), 'text/plain')
            raise

    except UserError, exception:
        request.context['title'] = sentence(exception.__class__.__name__)
        request.context['error'] = exception
        try:
            template = loader.get_template(exception.template)
        except TemplateDoesNotExist:
            template = loader.get_template('djata/errors/base.html')
        response = template.render(request.context)
        return exception.response_class(response)


########NEW FILE########
