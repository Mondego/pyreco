__FILENAME__ = app
"""
                  ___
 walrus-mix    .-9 9 `\
             =(:(::)=  ;
               ||||     \
               ||||      `-.
              ,\|\|         `,
             /                \
            ;                  `'---.,
            |                         `\
            ;                     /     |
            \                    |      /
     jgs     )           \  __,.--\    /
          .-' \,..._\     \`   .-'  .-'
         `-=``      `:    |   /-/-/`
                      `.__/
"""
import datetime

from flask import Flask, redirect, render_template, request, g, abort, url_for, flash
from peewee import *
from wtforms.validators import Length
from wtfpeewee.fields import ModelHiddenField
from wtfpeewee.orm import model_form, ModelConverter


# config
DATABASE = 'example.db'
DEBUG = True
SECRET_KEY = 'my favorite food is walrus mix'

app = Flask(__name__)
app.config.from_object(__name__)

database = SqliteDatabase(DATABASE)

# request handlers
@app.before_request
def before_request():
    g.db = database
    g.db.connect()

@app.after_request
def after_request(response):
    g.db.close()
    return response

# model definitions
class BaseModel(Model):
    class Meta:
        database = database


class Post(BaseModel):
    title = CharField()
    content = TextField()
    pub_date = DateTimeField(default=datetime.datetime.now)

    def __unicode__(self):
        return self.title

    class Meta:
        order_by = ('-pub_date',)


class Comment(BaseModel):
    post = ForeignKeyField(Post, related_name='comments')
    name = CharField()
    comment = TextField()
    pub_date = DateTimeField(default=datetime.datetime.now)
    
    class Meta:
        order_by = ('pub_date',)


# form classes
class HiddenForeignKeyConverter(ModelConverter):
    def handle_foreign_key(self, model, field, **kwargs):
        return field.name, ModelHiddenField(model=field.rel_model, **kwargs)


PostForm = model_form(Post, field_args={
    'title': dict(validators=[Length(min=3, max=200)]), # title must be at least 3 chars long
    'content': dict(description='this is the body of the post'), # a little help text
})
CommentForm = model_form(Comment, exclude=('pub_date',), converter=HiddenForeignKeyConverter())


def get_or_404(query, *expr):
    try:
        return query.where(*expr).get()
    except query.model_class.DoesNotExist:
        abort(404)

# views
@app.route('/')
def index():
    posts = Post.select().join(
        Comment, JOIN_LEFT_OUTER
    ).switch(Post).annotate(Comment, fn.Count(Comment.id).alias('comment_count'))
    return render_template('posts/index.html', posts=posts)

@app.route('/<id>/')
def detail(id):
    post = get_or_404(Post.select(), Post.id == id)
    comment_form = CommentForm(post=post)
    return render_template('posts/detail.html', post=post, comment_form=comment_form)

@app.route('/add/', methods=['GET', 'POST'])
def add():
    post = Post()
    
    if request.method == 'POST':
        form = PostForm(request.form, obj=post)
        if form.validate():
            form.populate_obj(post)
            post.save()
            flash('Successfully added %s' % post, 'success')
            return redirect(url_for('detail', id=post.id))
    else:
        form = PostForm(obj=post)
    
    return render_template('posts/add.html', post=post, form=form)

@app.route('/<id>/edit/', methods=['GET', 'POST'])
def edit(id):
    post = get_or_404(Post.select(), Post.id == id)
    
    if request.method == 'POST':
        form = PostForm(request.form, obj=post)
        if form.validate():
            form.populate_obj(post)
            post.save()
            flash('Changes to %s saved successfully' % post.title, 'success')
            return redirect(url_for('detail', id=post.id))
    else:
        form = PostForm(obj=post)
    
    return render_template('posts/edit.html', post=post, form=form)

@app.route('/comment/', methods=['POST'])
def comment():
    comment = Comment()
    form = CommentForm(request.form, obj=comment)
    if form.validate():
        form.populate_obj(comment)
        comment.save()
        flash('Thank you for your comment!', 'success')
    else:
        flash('There were errors with your comment', 'error')
    
    return redirect(url_for('detail', id=comment.post.id))



def create_tables():
    Post.create_table(True)
    Comment.create_table(True)

if __name__ == '__main__':
    create_tables()
    app.run()

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
import sys
import unittest

from wtfpeewee import tests

def runtests(*test_args):
    suite = unittest.TestLoader().loadTestsFromModule(tests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.failures:
        sys.exit(1)
    elif result.errors:
        sys.exit(2)
    sys.exit(0)

if __name__ == '__main__':
    runtests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = fields
"""
Useful form fields for use with the Peewee ORM.
(cribbed from wtforms.ext.django.fields)
"""
import datetime
import operator
import warnings

from wtforms import fields, form, widgets
from wtforms.fields import FormField, _unset_value
from wtforms.validators import ValidationError
from wtforms.widgets import HTMLString, html_params
from wtfpeewee._compat import text_type

__all__ = (
    'ModelSelectField', 'ModelSelectMultipleField', 'ModelHiddenField',
    'SelectQueryField', 'SelectMultipleQueryField', 'HiddenQueryField',
    'SelectChoicesField', 'BooleanSelectField', 'WPTimeField', 'WPDateField',
    'WPDateTimeField',
)


class StaticAttributesMixin(object):
    attributes = {}

    def __call__(self, **kwargs):
        for key, value in self.attributes.items():
            if key in kwargs:
                curr = kwargs[key]
                kwargs[key] = '%s %s' % (value, curr)
        return super(StaticAttributesMixin, self).__call__(**kwargs)


class BooleanSelectField(fields.SelectFieldBase):
    widget = widgets.Select()

    def iter_choices(self):
        yield ('1', 'True', self.data)
        yield ('', 'False', not self.data)

    def process_data(self, value):
        try:
            self.data = bool(value)
        except (ValueError, TypeError):
            self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = bool(valuelist[0])
            except ValueError:
                raise ValueError(self.gettext(u'Invalid Choice: could not coerce'))


class WPTimeField(StaticAttributesMixin, fields.TextField):
    attributes = {'class': 'time-widget'}
    formats = ['%H:%M:%S', '%H:%M']

    def _value(self):
        if self.raw_data:
            return u' '.join(self.raw_data)
        else:
            return self.data and self.data.strftime(self.formats[0]) or u''

    def convert(self, time_str):
        for format in self.formats:
            try:
                return datetime.datetime.strptime(time_str, format).time()
            except ValueError:
                pass

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = self.convert(' '.join(valuelist))
            if self.data is None:
                raise ValueError(self.gettext(u'Not a valid time value'))


class WPDateField(StaticAttributesMixin, fields.DateField):
    attributes = {'class': 'date-widget'}


def datetime_widget(field, **kwargs):
    kwargs.setdefault('id', field.id)
    kwargs.setdefault('class', '')
    kwargs['class'] += ' datetime-widget'
    html = []
    for subfield in field:
        html.append(subfield(**kwargs))
    return HTMLString(u''.join(html))


def generate_datetime_form(validators=None):
    class _DateTimeForm(form.Form):
        date = WPDateField(validators=validators)
        time = WPTimeField(validators=validators)
    return _DateTimeForm


class WPDateTimeField(FormField):
    widget = staticmethod(datetime_widget)

    def __init__(self, label='', validators=None, **kwargs):
        DynamicForm = generate_datetime_form(validators)
        super(WPDateTimeField, self).__init__(
            DynamicForm, label, validators=None, **kwargs)

    def process(self, formdata, data=_unset_value):
        prefix = self.name + self.separator
        kwargs = {}
        if data is _unset_value:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        if data and data is not _unset_value:
            kwargs['date'] = data.date()
            kwargs['time'] = data.time()

        self.form = self.form_class(formdata, prefix=prefix, **kwargs)

    def populate_obj(self, obj, name):
        setattr(obj, name, self.data)

    @property
    def data(self):
        date_data = self.date.data
        time_data = self.time.data or datetime.time(0, 0)
        if date_data:
            return datetime.datetime.combine(date_data, time_data)


class ChosenSelectWidget(widgets.Select):
    """
        `Chosen <http://harvesthq.github.com/chosen/>`_ styled select widget.

        You must include chosen.js for styling to work.
    """
    def __call__(self, field, **kwargs):
        if field.allow_blank and not self.multiple:
            kwargs['data-role'] = u'chosenblank'
        else:
            kwargs['data-role'] = u'chosen'

        return super(ChosenSelectWidget, self).__call__(field, **kwargs)


class SelectChoicesField(fields.SelectField):
    widget = ChosenSelectWidget()

    # all of this exists so i can get proper handling of None
    def __init__(self, label=None, validators=None, coerce=text_type, choices=None, allow_blank=False, blank_text=u'', **kwargs):
        super(SelectChoicesField, self).__init__(label, validators, coerce, choices, **kwargs)
        self.allow_blank = allow_blank
        self.blank_text = blank_text or '----------------'

    def iter_choices(self):
        if self.allow_blank:
            yield (u'__None', self.blank_text, self.data is None)

        for value, label in self.choices:
            yield (value, label, self.coerce(value) == self.data)

    def process_data(self, value):
        if value is None:
            self.data = None
        else:
            try:
                self.data = self.coerce(value)
            except (ValueError, TypeError):
                self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                try:
                    self.data = self.coerce(valuelist[0])
                except ValueError:
                    raise ValueError(self.gettext(u'Invalid Choice: could not coerce'))

    def pre_validate(self, form):
        if self.allow_blank and self.data is None:
            return
        super(SelectChoicesField, self).pre_validate(form)


class SelectQueryField(fields.SelectFieldBase):
    """
    Given a SelectQuery either at initialization or inside a view, will display a
    select drop-down field of choices. The `data` property actually will
    store/keep an ORM model instance, not the ID. Submitting a choice which is
    not in the queryset will result in a validation error.

    Specify `get_label` to customize the label associated with each option. If
    a string, this is the name of an attribute on the model object to use as
    the label text. If a one-argument callable, this callable will be passed
    model instance and expected to return the label text. Otherwise, the model
    object's `__unicode__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`.  The label for the blank choice can be set by specifying the
    `blank_text` parameter.
    """
    widget = ChosenSelectWidget()

    def __init__(self, label=None, validators=None, query=None, get_label=None, allow_blank=False, blank_text=u'', **kwargs):
        super(SelectQueryField, self).__init__(label, validators, **kwargs)
        self.allow_blank = allow_blank
        self.blank_text = blank_text or '----------------'
        self.query = query
        self.model = query.model_class
        self._set_data(None)

        if get_label is None:
            self.get_label = lambda o: text_type(o)
        elif isinstance(get_label, basestring):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

    def get_model(self, pk):
        try:
            return self.query.where(self.model._meta.primary_key==pk).get()
        except self.model.DoesNotExist:
            pass

    def _get_data(self):
        if self._formdata is not None:
            self._set_data(self.get_model(self._formdata))
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def __call__(self, **kwargs):
        if 'value' in kwargs:
            self._set_data(self.get_model(kwargs['value']))
        return self.widget(self, **kwargs)

    def iter_choices(self):
        if self.allow_blank:
            yield (u'__None', self.blank_text, self.data is None)

        for obj in self.query.clone():
            yield (obj.get_id(), self.get_label(obj), obj == self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None':
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        if self.data is not None:
            if not self.query.where(self.model._meta.primary_key==self.data.get_id()).exists():
                raise ValidationError(self.gettext('Not a valid choice'))
        elif not self.allow_blank:
            raise ValidationError(self.gettext('Selection cannot be blank'))


class SelectMultipleQueryField(SelectQueryField):
    widget =  ChosenSelectWidget(multiple=True)

    def __init__(self, *args, **kwargs):
        kwargs.pop('allow_blank', None)
        super(SelectMultipleQueryField, self).__init__(*args, **kwargs)

    def get_model_list(self, pk_list):
        if pk_list:
            return list(self.query.where(self.model._meta.primary_key << pk_list))
        return []

    def _get_data(self):
        if self._formdata is not None:
            self._set_data(self.get_model_list(self._formdata))
        return self._data or []

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def __call__(self, **kwargs):
        if 'value' in kwargs:
            self._set_data(self.get_model_list(kwargs['value']))
        return self.widget(self, **kwargs)

    def iter_choices(self):
        for obj in self.query.clone():
            yield (obj.get_id(), self.get_label(obj), obj in self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            self._data = []
            self._formdata = list(map(int, valuelist))

    def pre_validate(self, form):
        if self.data:
            id_list = [m.get_id() for m in self.data]
            if id_list and not self.query.where(self.model._meta.primary_key << id_list).count() == len(id_list):
                raise ValidationError(self.gettext('Not a valid choice'))


class HiddenQueryField(fields.HiddenField):
    def __init__(self, label=None, validators=None, query=None, get_label=None, **kwargs):
        self.allow_blank = kwargs.pop('allow_blank', False)
        super(fields.HiddenField, self).__init__(label, validators, **kwargs)
        self.query = query
        self.model = query.model_class
        self._set_data(None)

        if get_label is None:
            self.get_label = lambda o: text_type(o)
        elif isinstance(get_label, basestring):
            self.get_label = operator.attrgetter(get_label)
        else:
            self.get_label = get_label

    def get_model(self, pk):
        try:
            return self.query.where(self.model._meta.primary_key==pk).get()
        except self.model.DoesNotExist:
            pass

    def _get_data(self):
        if self._formdata is not None:
            if self.allow_blank and self._formdata == '__None':
                self._set_data(None)
            else:
                self._set_data(self.get_model(self._formdata))
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def __call__(self, **kwargs):
        if 'value' in kwargs:
            self._set_data(self.get_model(kwargs['value']))
        return self.widget(self, **kwargs)

    def _value(self):
        return self.data and self.data.get_id() or ''

    def process_formdata(self, valuelist):
        if valuelist:
            model_id = valuelist[0]
            self._data = None
            self._formdata = model_id or None


class ModelSelectField(SelectQueryField):
    """
    Like a SelectQueryField, except takes a model class instead of a
    queryset and lists everything in it.
    """
    def __init__(self, label=None, validators=None, model=None, **kwargs):
        super(ModelSelectField, self).__init__(label, validators, query=model.select(), **kwargs)


class ModelSelectMultipleField(SelectMultipleQueryField):
    """
    Like a SelectMultipleQueryField, except takes a model class instead of a
    queryset and lists everything in it.
    """
    def __init__(self, label=None, validators=None, model=None, **kwargs):
        super(ModelSelectMultipleField, self).__init__(label, validators, query=model.select(), **kwargs)

class ModelHiddenField(HiddenQueryField):
    """
    Like a HiddenQueryField, except takes a model class instead of a
    queryset and lists everything in it.
    """
    def __init__(self, label=None, validators=None, model=None, **kwargs):
        super(ModelHiddenField, self).__init__(label, validators, query=model.select(), **kwargs)

########NEW FILE########
__FILENAME__ = orm
"""
Tools for generating forms based on Peewee models
(cribbed from wtforms.ext.django)
"""

from collections import namedtuple
from wtforms import Form
from wtforms import fields as f
from wtforms import validators
from wtfpeewee.fields import ModelSelectField
from wtfpeewee.fields import SelectChoicesField
from wtfpeewee.fields import SelectQueryField
from wtfpeewee.fields import WPDateField
from wtfpeewee.fields import WPDateTimeField
from wtfpeewee.fields import WPTimeField
from wtfpeewee._compat import text_type

from peewee import BigIntegerField
from peewee import BlobField
from peewee import BooleanField
from peewee import CharField
from peewee import DateField
from peewee import DateTimeField
from peewee import DecimalField
from peewee import DoubleField
from peewee import FloatField
from peewee import ForeignKeyField
from peewee import IntegerField
from peewee import PrimaryKeyField
from peewee import TextField
from peewee import TimeField


__all__ = (
    'FieldInfo',
    'ModelConverter',
    'model_fields',
    'model_form')

def handle_null_filter(data):
    if data == '':
        return None
    return data

FieldInfo = namedtuple('FieldInfo', ('name', 'field'))

class ModelConverter(object):
    defaults = {
        BigIntegerField: f.IntegerField,
        BlobField: f.TextAreaField,
        BooleanField: f.BooleanField,
        CharField: f.TextField,
        DateField: WPDateField,
        DateTimeField: WPDateTimeField,
        DecimalField: f.DecimalField,
        DoubleField: f.FloatField,
        FloatField: f.FloatField,
        IntegerField: f.IntegerField,
        PrimaryKeyField: f.HiddenField,
        TextField: f.TextAreaField,
        TimeField: WPTimeField,
    }
    coerce_defaults = {
        BigIntegerField: int,
        CharField: text_type,
        DoubleField: float,
        FloatField: float,
        IntegerField: int,
        TextField: text_type,
    }
    required = (
        CharField,
        DateTimeField,
        ForeignKeyField,
        PrimaryKeyField,
        TextField)

    def __init__(self, additional=None, additional_coerce=None, overrides=None):
        self.converters = {ForeignKeyField: self.handle_foreign_key}
        if additional:
            self.converters.update(additional)

        self.coerce_settings = dict(self.coerce_defaults)
        if additional_coerce:
            self.coerce_settings.update(additional_coerce)
            
        self.overrides = overrides or {}

    def handle_foreign_key(self, model, field, **kwargs):
        if field.null:
            kwargs['allow_blank'] = True
        if field.choices is not None:
            field_obj = SelectQueryField(query=field.choices, **kwargs)
        else:
            field_obj = ModelSelectField(model=field.rel_model, **kwargs)
        return FieldInfo(field.name, field_obj)

    def convert(self, model, field, field_args):
        kwargs = {
            'label': field.verbose_name,
            'validators': [],
            'filters': [],
            'default': field.default,
            'description': field.help_text}
        if field_args:
            kwargs.update(field_args)

        if field.null:
            # Treat empty string as None when converting.
            kwargs['filters'].append(handle_null_filter)

        if (field.null or (field.default is not None)) and not field.choices:
            # If the field can be empty, or has a default value, do not require
            # it when submitting a form.
            kwargs['validators'].append(validators.Optional())
        else:
            if isinstance(field, self.required):
                kwargs['validators'].append(validators.Required())

        if field.name in self.overrides:
            return FieldInfo(field.name, self.overrides[field.name](**kwargs))

        field_class = type(field)
        if field_class in self.converters:
            return self.converters[field_class](model, field, **kwargs)
        elif field_class in self.defaults:
            if issubclass(self.defaults[field_class], f.FormField):
                # FormField fields (i.e. for nested forms) do not support
                # filters.
                kwargs.pop('filters')
            if field.choices or 'choices' in kwargs:
                choices = kwargs.pop('choices', field.choices)
                if field_class in self.coerce_settings or 'coerce' in kwargs:
                    coerce_fn = kwargs.pop('coerce',
                                           self.coerce_settings[field_class])
                    allow_blank = kwargs.pop('allow_blank', field.null)
                    kwargs.update({
                        'choices': choices,
                        'coerce': coerce_fn,
                        'allow_blank': allow_blank})

                    return FieldInfo(field.name, SelectChoicesField(**kwargs))

            return FieldInfo(field.name, self.defaults[field_class](**kwargs))

        raise AttributeError("There is not possible conversion "
                             "for '%s'" % field_class)


def model_fields(model, allow_pk=False, only=None, exclude=None,
                 field_args=None, converter=None):
    """
    Generate a dictionary of fields for a given Peewee model.

    See `model_form` docstring for description of parameters.
    """
    converter = converter or ModelConverter()
    field_args = field_args or {}

    model_fields = list(model._meta.get_sorted_fields())
    if not allow_pk:
        model_fields.pop(0)

    if only:
        model_fields = [x for x in model_fields if x[0] in only]
    elif exclude:
        model_fields = [x for x in model_fields if x[0] not in exclude]

    field_dict = {}
    for name, model_field in model_fields:
        name, field = converter.convert(model, model_field, field_args.get(name))
        field_dict[name] = field

    return field_dict


def model_form(model, base_class=Form, allow_pk=False, only=None, exclude=None,
               field_args=None, converter=None):
    """
    Create a wtforms Form for a given Peewee model class::

        from wtfpeewee.orm import model_form
        from myproject.myapp.models import User
        UserForm = model_form(User)

    :param model:
        A Peewee model class
    :param base_class:
        Base form class to extend from. Must be a ``wtforms.Form`` subclass.
    :param only:
        An optional iterable with the property names that should be included in
        the form. Only these properties will have fields.
    :param exclude:
        An optional iterable with the property names that should be excluded
        from the form. All other properties will have fields.
    :param field_args:
        An optional dictionary of field names mapping to keyword arguments used
        to construct each field object.
    :param converter:
        A converter to generate the fields based on the model properties. If
        not set, ``ModelConverter`` is used.
    """
    field_dict = model_fields(model, allow_pk, only, exclude, field_args, converter)
    return type(model.__name__ + 'Form', (base_class, ), field_dict)

########NEW FILE########
__FILENAME__ = tests
import datetime
import unittest

from peewee import *
from wtforms import fields as wtfields
from wtforms.form import Form as WTForm
from wtfpeewee.fields import *
from wtfpeewee.orm import model_form
from wtfpeewee._compat import PY2


if not PY2:
    implements_to_string = lambda x: x
else:
    def implements_to_string(cls):
        cls.__unicode__ = cls.__str__
        cls.__str__ = lambda x: x.__unicode__().encode('utf-8')
        return cls


test_db = SqliteDatabase(':memory:')

class TestModel(Model):
    class Meta:
        database = test_db


@implements_to_string
class Blog(TestModel):
    title = CharField()

    def __str__(self):
        return self.title


@implements_to_string
class Entry(TestModel):
    pk = PrimaryKeyField()
    blog = ForeignKeyField(Blog)
    title = CharField(verbose_name='Wacky title')
    content = TextField()
    pub_date = DateTimeField(default=datetime.datetime.now)

    def __str__(self):
        return '%s: %s' % (self.blog.title, self.title)


class NullEntry(TestModel):
    blog = ForeignKeyField(Blog, null=True)


class NullFieldsModel(TestModel):
    c = CharField(null=True)
    b = BooleanField(null=True)


class ChoicesModel(TestModel):
    gender = CharField(choices=(('m', 'Male'), ('f', 'Female')))
    status = IntegerField(choices=((1, 'One'), (2, 'Two')), null=True)
    salutation = CharField(null=True)
    true_or_false = BooleanField(choices=((True, 't'), (False, 'f')))


class NonIntPKModel(TestModel):
    id = CharField(primary_key=True)
    value = CharField()


BlogForm = model_form(Blog)
EntryForm = model_form(Entry)
NullFieldsModelForm = model_form(NullFieldsModel)
ChoicesForm = model_form(ChoicesModel, field_args={'salutation': {'choices': (('mr', 'Mr.'), ('mrs', 'Mrs.'))}})
NonIntPKForm = model_form(NonIntPKModel, allow_pk=True)

class FakePost(dict):
    def getlist(self, key):
        val = self[key]
        if isinstance(val, list):
            return val
        return [val]


class WTFPeeweeTestCase(unittest.TestCase):
    def setUp(self):
        NullEntry.drop_table(True)
        Entry.drop_table(True)
        Blog.drop_table(True)
        NullFieldsModel.drop_table(True)
        NonIntPKModel.drop_table(True)

        Blog.create_table()
        Entry.create_table()
        NullEntry.create_table()
        NullFieldsModel.create_table()
        NonIntPKModel.create_table()

        self.blog_a = Blog.create(title='a')
        self.blog_b = Blog.create(title='b')

        self.entry_a1 = Entry.create(blog=self.blog_a, title='a1', content='a1 content', pub_date=datetime.datetime(2011, 1, 1))
        self.entry_a2 = Entry.create(blog=self.blog_a, title='a2', content='a2 content', pub_date=datetime.datetime(2011, 1, 2))
        self.entry_b1 = Entry.create(blog=self.blog_b, title='b1', content='b1 content', pub_date=datetime.datetime(2011, 1, 1))

    def test_defaults(self):
        BlogFormDef = model_form(Blog, field_args={'title': {'default': 'hello world'}})

        form = BlogFormDef()
        self.assertEqual(form.data, {'title': 'hello world'})

        form = BlogFormDef(obj=self.blog_a)
        self.assertEqual(form.data, {'title': 'a'})

    def test_non_int_pk(self):
        form = NonIntPKForm()
        self.assertEqual(form.data, {'value': None, 'id': None})
        self.assertFalse(form.validate())

        obj = NonIntPKModel(id='a', value='A')
        form = NonIntPKForm(obj=obj)
        self.assertEqual(form.data, {'value': 'A', 'id': 'a'})
        self.assertTrue(form.validate())

        form = NonIntPKForm(FakePost({'id': 'b', 'value': 'B'}))
        self.assertTrue(form.validate())

        obj = NonIntPKModel()
        form.populate_obj(obj)
        self.assertEqual(obj.id, 'b')
        self.assertEqual(obj.value, 'B')

        self.assertEqual(NonIntPKModel.select().count(), 0)
        obj.save(True)
        self.assertEqual(NonIntPKModel.select().count(), 1)

        # its hard to validate unique-ness because a form may be updating
        #form = NonIntPKForm(FakePost({'id': 'b', 'value': 'C'}))
        #self.assertFalse(form.validate())

    def test_choices(self):
        form = ChoicesForm()
        self.assertTrue(isinstance(form.gender, SelectChoicesField))
        self.assertTrue(isinstance(form.status, SelectChoicesField))
        self.assertTrue(isinstance(form.salutation, SelectChoicesField))
        self.assertTrue(isinstance(form.true_or_false, wtfields.BooleanField))

        self.assertEqual(list(form.gender.iter_choices()), [
            ('m', 'Male', False), ('f', 'Female', False)
        ])
        self.assertEqual(list(form.status.iter_choices()), [
            ('__None', '----------------', True), (1, 'One', False), (2, 'Two', False)
        ])
        self.assertEqual(list(form.salutation.iter_choices()), [
            ('__None', '----------------', True), ('mr', 'Mr.', False), ('mrs', 'Mrs.', False),
        ])

        choices_obj = ChoicesModel(gender='m', status=2, salutation=None)
        form = ChoicesForm(obj=choices_obj)
        self.assertEqual(form.data, {'gender': 'm', 'status': 2, 'salutation': None, 'true_or_false': False})
        self.assertTrue(form.validate())

        choices_obj = ChoicesModel(gender='f', status=1, salutation='mrs', true_or_false=True)
        form = ChoicesForm(obj=choices_obj)
        self.assertEqual(form.data, {'gender': 'f', 'status': 1, 'salutation': 'mrs', 'true_or_false': True})
        self.assertTrue(form.validate())

        choices_obj.gender = 'x'
        form = ChoicesForm(obj=choices_obj)
        self.assertFalse(form.validate())
        self.assertEqual(form.errors, {'gender': ['Not a valid choice']})

        choices_obj.gender = 'm'
        choices_obj.status = '1'
        form = ChoicesForm(obj=choices_obj)
        self.assertEqual(form.status.data, 1)
        self.assertTrue(form.validate())

        choices_obj.status = '3'
        form = ChoicesForm(obj=choices_obj)

        self.assertFalse(form.validate())

        choices_obj.status = None
        form = ChoicesForm(obj=choices_obj)
        self.assertEqual(form.status.data, None)
        self.assertTrue(form.validate())

    def test_blog_form(self):
        form = BlogForm()
        self.assertEqual(list(form._fields.keys()), ['title'])
        self.assertTrue(isinstance(form.title, wtfields.TextField))
        self.assertEqual(form.data, {'title': None})

    def test_entry_form(self):
        form = EntryForm()
        self.assertEqual(sorted(form._fields.keys()), ['blog', 'content', 'pub_date', 'title'])

        self.assertTrue(isinstance(form.blog, ModelSelectField))
        self.assertTrue(isinstance(form.content, wtfields.TextAreaField))
        self.assertTrue(isinstance(form.pub_date, WPDateTimeField))
        self.assertTrue(isinstance(form.title, wtfields.TextField))

        self.assertEqual(form.title.label.text, 'Wacky title')
        self.assertEqual(form.blog.label.text, 'Blog')
        self.assertEqual(form.pub_date.label.text, 'Pub Date')

        # check that the default value appears
        self.assertTrue(isinstance(form.pub_date.data, datetime.datetime))

        # check that the foreign key defaults to none
        self.assertEqual(form.blog.data, None)

        # check that the options look right
        self.assertEqual(list(form.blog.iter_choices()), [
            (self.blog_a.get_id(), u'a', False), (self.blog_b.get_id(), u'b', False)
        ])

    def test_blog_form_with_obj(self):
        form = BlogForm(obj=self.blog_a)
        self.assertEqual(form.data, {'title': 'a'})
        self.assertTrue(form.validate())

    def test_entry_form_with_obj(self):
        form = EntryForm(obj=self.entry_a1)
        self.assertEqual(form.data, {
            'title': 'a1',
            'content': 'a1 content',
            'pub_date': datetime.datetime(2011, 1, 1),
            'blog': self.blog_a,
        })
        self.assertTrue(form.validate())

        # check that the options look right
        self.assertEqual(list(form.blog.iter_choices()), [
            (self.blog_a.get_id(), u'a', True), (self.blog_b.get_id(), u'b', False)
        ])

    def test_blog_form_saving(self):
        form = BlogForm(FakePost({'title': 'new blog'}))
        self.assertTrue(form.validate())

        blog = Blog()
        form.populate_obj(blog)
        self.assertEqual(blog.title, 'new blog')

        # no new blogs were created
        self.assertEqual(Blog.select().count(), 2)

        # explicitly calling save will create the new blog
        blog.save()

        # make sure we created a new blog
        self.assertEqual(Blog.select().count(), 3)

        form = BlogForm(FakePost({'title': 'a edited'}), obj=self.blog_a)
        self.assertTrue(form.validate())
        form.populate_obj(self.blog_a)

        self.assertEqual(self.blog_a.title, 'a edited')
        self.blog_a.save()

        # make sure no new blogs were created
        self.assertEqual(Blog.select().count(), 3)

        # grab it from the database
        a = Blog.get(title='a edited')

    def test_entry_form_saving(self):
        # check count of entries
        self.assertEqual(Entry.select().count(), 3)

        form = EntryForm(FakePost({
            'title': 'new entry',
            'content': 'some content',
            'pub_date-date': '2011-02-01',
            'pub_date-time': '00:00:00',
            'blog': self.blog_b.get_id(),
        }))
        self.assertTrue(form.validate())

        self.assertEqual(form.pub_date.data, datetime.datetime(2011, 2, 1))
        self.assertEqual(form.blog.data, self.blog_b)

        entry = Entry()
        form.populate_obj(entry)

        # ensure entry count hasn't changed
        self.assertEqual(Entry.select().count(), 3)

        entry.save()
        self.assertEqual(Entry.select().count(), 4)
        self.assertEqual(self.blog_a.entry_set.count(), 2)
        self.assertEqual(self.blog_b.entry_set.count(), 2)

        # make sure the blog object came through ok
        self.assertEqual(entry.blog, self.blog_b)

        # edit entry a1
        form = EntryForm(FakePost({
            'title': 'a1 edited',
            'content': 'a1 content',
            'pub_date': '2011-01-01 00:00:00',
            'blog': self.blog_b.get_id(),
        }), obj=self.entry_a1)
        self.assertTrue(form.validate())

        form.populate_obj(self.entry_a1)
        self.entry_a1.save()

        self.assertEqual(self.entry_a1.blog, self.blog_b)

        self.assertEqual(self.blog_a.entry_set.count(), 1)
        self.assertEqual(self.blog_b.entry_set.count(), 3)

        # pull from the db just to be 100% sure
        a1 = Entry.get(title='a1 edited')

        form = EntryForm(FakePost({
            'title': 'new',
            'content': 'blah',
            'pub_date': '2011-01-01 00:00:00',
            'blog': 10000
        }))
        self.assertFalse(form.validate())

    def test_null_form_saving(self):
        form = NullFieldsModelForm(FakePost({'c': ''}))
        self.assertTrue(form.validate())

        nfm = NullFieldsModel()
        form.populate_obj(nfm)
        self.assertEqual(nfm.c, None)

        # this is a bit odd, but since checkboxes do not send a value if they
        # are unchecked this will evaluate to false (and passing in an empty
        # string evalutes to true) since the wtforms booleanfield blindly coerces
        # to bool
        self.assertEqual(nfm.b, False)

        form = NullFieldsModelForm(FakePost({'c': '', 'b': ''}))
        self.assertTrue(form.validate())

        nfm = NullFieldsModel()
        form.populate_obj(nfm)
        self.assertEqual(nfm.c, None)

        # again, this is for the purposes of documenting behavior -- nullable
        # booleanfields won't work without a custom field class
        # Passing an empty string will evalute to False
        # https://bitbucket.org/simplecodes/wtforms/commits/35c5f7182b7f0c62a4d4db7a1ec8719779b4b018
        self.assertEqual(nfm.b, False)

        form = NullFieldsModelForm(FakePost({'c': 'test'}))
        self.assertTrue(form.validate())

        nfm = NullFieldsModel()
        form.populate_obj(nfm)
        self.assertEqual(nfm.c, 'test')

    def test_form_with_only_exclude(self):
        frm = model_form(Entry, only=('title', 'content',))()
        self.assertEqual(sorted(frm._fields.keys()), ['content', 'title'])

        frm = model_form(Entry, exclude=('title', 'content',))()
        self.assertEqual(sorted(frm._fields.keys()), ['blog', 'pub_date'])

    def test_form_multiple(self):
        class TestForm(WTForm):
            blog = SelectMultipleQueryField(query=Blog.select())

        frm = TestForm()
        self.assertEqual([x for x in frm.blog.iter_choices()], [
            (self.blog_a.id, 'a', False),
            (self.blog_b.id, 'b', False),
        ])

        frm = TestForm(FakePost({'blog': [self.blog_b.id]}))
        self.assertEqual([x for x in frm.blog.iter_choices()], [
            (self.blog_a.id, 'a', False),
            (self.blog_b.id, 'b', True),
        ])
        self.assertEqual(frm.blog.data, [self.blog_b])
        self.assertTrue(frm.validate())

        frm = TestForm(FakePost({'blog': [self.blog_b.id, self.blog_a.id]}))
        self.assertEqual([x for x in frm.blog.iter_choices()], [
            (self.blog_a.id, 'a', True),
            (self.blog_b.id, 'b', True),
        ])
        self.assertEqual(frm.blog.data, [self.blog_a, self.blog_b])
        self.assertTrue(frm.validate())

        bad_id = [x for x in range(1,4) if x not in [self.blog_a.id, self.blog_b.id]][0]
        frm = TestForm(FakePost({'blog': [self.blog_b.id, bad_id]}))
        self.assertTrue(frm.validate())

    def test_hidden_field(self):
        class TestEntryForm(WTForm):
            blog = HiddenQueryField(query=Blog.select())
            title = wtfields.TextField()
            content = wtfields.TextAreaField()

        form = TestEntryForm(FakePost({
            'title': 'new entry',
            'content': 'some content',
            'blog': self.blog_b.get_id(),
        }))

        # check the htmlz for the form's hidden field
        html = form._fields['blog']()
        self.assertEqual(html, u'<input id="blog" name="blog" type="hidden" value="%s">' % self.blog_b.get_id())

        self.assertTrue(form.validate())
        self.assertEqual(form.blog.data, self.blog_b)

        entry = Entry()
        form.populate_obj(entry)

        # ensure entry count hasn't changed
        self.assertEqual(Entry.select().count(), 3)

        entry.save()
        self.assertEqual(Entry.select().count(), 4)
        self.assertEqual(self.blog_a.entry_set.count(), 2)
        self.assertEqual(self.blog_b.entry_set.count(), 2)

        # make sure the blog object came through ok
        self.assertEqual(entry.blog, self.blog_b)

        # edit entry a1
        form = TestEntryForm(FakePost({
            'title': 'a1 edited',
            'content': 'a1 content',
            'blog': self.blog_b.get_id(),
        }), obj=self.entry_a1)

        # check the htmlz for the form's hidden field
        html = form._fields['blog']()
        self.assertEqual(html, u'<input id="blog" name="blog" type="hidden" value="%s">' % self.blog_b.get_id())

        self.assertTrue(form.validate())

        form.populate_obj(self.entry_a1)
        self.entry_a1.save()

        self.assertEqual(self.entry_a1.blog, self.blog_b)

        self.assertEqual(self.blog_a.entry_set.count(), 1)
        self.assertEqual(self.blog_b.entry_set.count(), 3)

        # pull from the db just to be 100% sure
        a1 = Entry.get(title='a1 edited')

    def test_hidden_field_none(self):
        class TestNullEntryForm(WTForm):
            blog = HiddenQueryField(query=Blog.select())

        form = TestNullEntryForm(FakePost({
            'blog': '',
        }))

        # check the htmlz for the form's hidden field
        html = form._fields['blog']()
        self.assertEqual(html, u'<input id="blog" name="blog" type="hidden" value="">')

        self.assertTrue(form.validate())
        self.assertEqual(form.blog.data, None)

        entry = NullEntry()
        form.populate_obj(entry)

        # ensure entry count hasn't changed
        self.assertEqual(NullEntry.select().count(), 0)

        entry.save()
        self.assertEqual(NullEntry.select().count(), 1)

        # make sure the blog object came through ok
        self.assertEqual(entry.blog, None)

        # edit entry a1
        form = TestNullEntryForm(FakePost({
            'blog': None,
        }), obj=self.entry_a1)

        # check the htmlz for the form's hidden field
        html = form._fields['blog']()
        self.assertEqual(html, u'<input id="blog" name="blog" type="hidden" value="">')

        self.assertTrue(form.validate())

########NEW FILE########
__FILENAME__ = _compat
import sys


PY2 = sys.version_info[0] == 2

if PY2:
    text_type = unicode
    string_types = (str, unicode)
    unichr = unichr
    reduce = reduce
else:
    text_type = str
    string_types = (str,)
    unichr = chr
    from functools import reduce

########NEW FILE########
