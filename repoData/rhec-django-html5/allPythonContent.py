__FILENAME__ = fields
from django.forms.fields import IntegerField as DjangoIntegerField

from html5.forms import NumberInput

class IntegerField(DjangoIntegerField):
    widget = NumberInput

    def widget_attrs(self, widget):
        """
        Given a Widget instance (*not* a Widget class), returns a dictionary of
        any HTML attributes that should be added to the Widget, based on this
        Field.
        """
        attrs = {}
        if self.min_value is not None:
            attrs['min'] = self.min_value
        if self.max_value is not None:
            attrs['max'] = self.max_value
        return attrs

########NEW FILE########
__FILENAME__ = widgets
"""
HTML5 input widgets.
TODO: Date widgets
"""
from django.forms.widgets import Input

class HTML5Input(Input):
    use_autofocus_fallback = False
    
    def render(self, *args, **kwargs):
        rendered_string = super(HTML5Input, self).render(*args, **kwargs)
        # js only works when an id is set
        if self.use_autofocus_fallback and kwargs.has_key('attrs') and kwargs['attrs'].get("id",False) and kwargs['attrs'].has_key("autofocus"):
            rendered_string += """<script>
if (!("autofocus" in document.createElement("input"))) {
  document.getElementById("%s").focus();
}
</script>""" % kwargs['attrs']['id']
        return rendered_string

class TextInput(HTML5Input):
    input_type = 'text'

class EmailInput(HTML5Input):
    input_type = 'email'

class TelephoneInput(HTML5Input):
    input_type = 'tel'

class URLInput(HTML5Input):
    input_type = 'url'

class SearchInput(HTML5Input):
    input_type = 'search'

class ColorInput(HTML5Input):
    """
    Not supported by any browsers at this time (Jan. 2010).
    """
    input_type = 'color'
    
class NumberInput(HTML5Input):
    input_type = 'number'
    
class RangeInput(NumberInput):
    input_type = 'range'
    
class DateInput(HTML5Input):
    input_type = 'date'
    
class MonthInput(HTML5Input):
    input_type = 'month'

class WeekInput(HTML5Input):
    input_type = 'week'

class TimeInput(HTML5Input):
    input_type = 'time'

class DateTimeInput(HTML5Input):
    input_type = 'datetime'

class DateTimeLocalInput(HTML5Input):
    input_type = 'datetime-local'

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
r"""
>>> from html5.forms import *

# Field Tests   ############################################################\n
>>> i = IntegerField(max_value = 10, min_value=1)
>>> i.widget.render('name','')
u'<input max="10" type="number" name="name" min="1" />'
>>> i = IntegerField(max_value = 10, min_value=0)
>>> i.widget.render('name','')
u'<input max="10" type="number" name="name" min="0" />'
>>> i = IntegerField()
>>> i.widget.render('name','')
u'<input type="number" name="name" />'

#  Widget Tests ############################################################\n

>>> w = TextInput()
>>> w.render('email', '')
u'<input type="text" name="email" />'
>>> w = EmailInput()
>>> w.render('email', '')
u'<input type="email" name="email" />'
>>> w = TelephoneInput()
>>> w.render('phone_number', '')
u'<input type="tel" name="phone_number" />'
>>> w = URLInput()
>>> w.render('url', '')
u'<input type="url" name="url" />'
>>> w = SearchInput()
>>> w.render('q', '')
u'<input type="search" name="q" />'
>>> w = ColorInput()
>>> w.render('color', '')
u'<input type="color" name="color" />'
>>> w = NumberInput()
>>> w.render('number', '')
u'<input type="number" name="number" />'
>>> w = RangeInput()
>>> w.render('number_range', '')
u'<input type="range" name="number_range" />'
>>> w = DateInput()
>>> w.render('start_date', '')
u'<input type="date" name="start_date" />'
>>> w = MonthInput()
>>> w.render('month', '')
u'<input type="month" name="month" />'
>>> w = WeekInput()
>>> w.render('week', '')
u'<input type="week" name="week" />'
>>> w = TimeInput()
>>> w.render('time', '')
u'<input type="time" name="time" />'
>>> w = DateTimeInput()
>>> w.render('datetime', '')
u'<input type="datetime" name="datetime" />'
>>> w = DateTimeLocalInput()
>>> w.render('datetime_local', '')
u'<input type="datetime-local" name="datetime_local" />'

# Test Placeholder attr #####################################\n
>>> w = TextInput()
>>> w.render('name', '', attrs={'placeholder':'placeholder text'})
u'<input type="text" name="name" placeholder="placeholder text" />'

# Test autofocus attr #######################################\n
>>> w.render('name', '', attrs={'autofocus':'true'})
u'<input type="text" name="name" autofocus="true" />'
>>> w.use_autofocus_fallback = True
>>> w.render('name', '', attrs={'autofocus':'true', 'id': "id_name"})
u'<input type="text" name="name" id="id_name" autofocus="true" /><script>\nif (!("autofocus" in document.createElement("input"))) {\n  document.getElementById("id_name").focus();\n}\n</script>'
>>> w.render('name', '', attrs={'autofocus':'true'})
u'<input type="text" name="name" autofocus="true" />'

# should not render js when autofocus attribute is not present\n
>>> w.render('name', '', attrs={'id': "id_name"})
u'<input type="text" name="name" id="id_name" />'

# should not render js when id is blank\n
>>> w.render('name', '', attrs={'id': "", 'autofocus':'true'})
u'<input autofocus="true" type="text" name="name" id="" />'
"""
########NEW FILE########
