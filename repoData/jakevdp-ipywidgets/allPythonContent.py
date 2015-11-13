__FILENAME__ = interact
from collections import OrderedDict
import itertools
import matplotlib.pyplot as plt
from IPython import get_ipython


def _get_html(obj):
    """Get the HTML representation of an object"""
    # TODO: use displaypub to make this more general
    ip = get_ipython()
    png_rep = ip.display_formatter.formatters['image/png'](obj)

    if png_rep is not None:
        if isinstance(obj, plt.Figure):
            plt.close(obj)  # keep from displaying twice
        return ('<img src="data:image/png;'
                'base64,{0}">'.format(png_rep.encode('base64')))
    else:
        return "<p> {0} </p>".format(str(obj))

    rep = ip.display_formatter.formatters['text/html'](obj)

    if rep is not None:
        return rep
    elif hasattr(obj, '_repr_html_'):
        return obj._repr_html_()


class StaticInteract(object):
    """Static Interact Object"""
    
    template = """
    <script type="text/javascript">
      var mergeNodes = function(a, b) {{
        return [].slice.call(a).concat([].slice.call(b));
      }}; // http://stackoverflow.com/questions/914783/javascript-nodelist/17262552#17262552
      function interactUpdate(div){{
         var outputs = div.getElementsByTagName("div");
         //var controls = div.getElementsByTagName("input");
         var controls = mergeNodes(div.getElementsByTagName("input"), div.getElementsByTagName("select"));
         function nameCompare(a,b) {{
            return a.getAttribute("name").localeCompare(b.getAttribute("name"));
         }}
         controls.sort(nameCompare);

         var value = "";
         for(i=0; i<controls.length; i++){{
           if((controls[i].type == "range") || controls[i].checked){{
             value = value + controls[i].getAttribute("name") + controls[i].value;
           }}
           if(controls[i].type == "select-one"){{
             value = value + controls[i].getAttribute("name") + controls[i][controls[i].selectedIndex].value;
           }}
         }}

         for(i=0; i<outputs.length; i++){{
           var name = outputs[i].getAttribute("name");
           if(name == value){{
              outputs[i].style.display = 'block';
           }} else if(name != "controls"){{
              outputs[i].style.display = 'none';
           }}
         }}
      }}
    </script>
    
    <div>
      {outputs}
      {widgets}
    </div>
    """
    
    subdiv_template = """
    <div name="{name}" style="display:{display}">
      {content}
    </div>
    """

    @staticmethod
    def _get_strrep(val):
        """Need to match javascript string rep"""
        # TODO: is there a better way to do this?
        if isinstance(val, str):
            return val
        elif val % 1 == 0:
            return str(int(val))
        else:
            return str(val)

    def __init__(self, function, **kwargs):
        # TODO: implement *args (difficult because of the name thing)
        # update names
        for name in kwargs:
            kwargs[name] = kwargs[name].renamed(name)

        self.widgets = OrderedDict(kwargs)
        self.function = function
        
    def _output_html(self):
        names = [name for name in self.widgets]
        values = [widget.values() for widget in self.widgets.values()]
        defaults = tuple([widget.default for widget in self.widgets.values()])

        #Now reorder alphabetically by names so divnames match javascript
        names,values,defaults = zip(*sorted(zip(names,values,defaults)))
                    
        results = [self.function(**dict(zip(names, vals)))
                   for vals in itertools.product(*values)]

        divnames = [''.join(['{0}{1}'.format(n, self._get_strrep(v))
                             for n, v in zip(names, vals)])
                    for vals in itertools.product(*values)]
        display = [vals == defaults for vals in itertools.product(*values)]
    
        tmplt = self.subdiv_template
        return "".join(tmplt.format(name=divname,
                                    display="block" if disp else "none",
                                    content=_get_html(result))
                       for divname, result, disp in zip(divnames,
                                                        results,
                                                        display))
    
                       
    def _widget_html(self):
        return "\n<br>\n".join([widget.html()
                                for name, widget in sorted(self.widgets.iteritems())])
        
    def html(self):
        return self.template.format(outputs=self._output_html(),
                                    widgets=self._widget_html())
        
    def _repr_html_(self):
        return self.html()
        

########NEW FILE########
__FILENAME__ = widgets
import copy
import numpy as np


class StaticWidget(object):
    """Base Class for Static Widgets"""
    def __init__(self, name=None, divclass=None):
        self.name = name
        if divclass is None:
            self.divargs = ""
        else:
            self.divargs = 'class:"{0}"'.format(divclass)
    
    def __repr__(self):
        return self.html()
    
    def _repr_html_(self):
        return self.html()

    def copy(self):
        return copy.deepcopy(self)

    def renamed(self, name):
        if (self.name is not None) and (self.name != name):
            obj = self.copy()
        else:
            obj = self
        obj.name = name
        return obj


class RangeWidget(StaticWidget):
    """Range (slider) widget"""
    slider_html = ('<b>{name}:</b> <input type="range" name="{name}" '
                   'min="{range[0]}" max="{range[1]}" step="{range[2]}" '
                   'value="{default}" style="{style}" '
                   'oninput="interactUpdate(this.parentNode);" '
                   'onchange="interactUpdate(this.parentNode);">')
    def __init__(self, min, max, step=1, name=None,
                 default=None, width=350, divclass=None,
                 show_range=False):
        StaticWidget.__init__(self, name, divclass)
        self.datarange = (min, max, step)
        self.width = width
        self.show_range = show_range
        if default is None:
            self.default = min
        else:
            self.default = default
            
    def values(self):
        min, max, step = self.datarange
        return np.arange(min, max + step, step)
            
    def html(self):
        style = ""
        
        if self.width is not None:
            style += "width:{0}px".format(self.width)
            
        output = self.slider_html.format(name=self.name, range=self.datarange,
                                         default=self.default, style=style)
        if self.show_range:
            output = "{0} {1} {2}".format(self.datarange[0],
                                          output,
                                          self.datarange[1])
        return output

class DropDownWidget(StaticWidget):
    select_html = ('<b>{name}:</b> <select name="{name}" '
                      'onchange="interactUpdate(this.parentNode);"> '
                      '{options}'
                      '</select>'
        )
    option_html = ('<option value="{value}" '
                      '{selected}>{label}</option>')
    def __init__(self, values, name=None,
                 labels=None, default=None, divclass=None,
                 delimiter="      "
                 ):
        StaticWidget.__init__(self, name, divclass)
        self._values = values
        self.delimiter = delimiter
        if labels is None:
            labels = map(str, values)
        elif len(labels) != len(values):
            raise ValueError("length of labels must match length of values")
        self.labels = labels

        if default is None:
            self.default = values[0]
        elif default in values:
            self.default = default
        else:
            raise ValueError("if specified, default must be in values")

    def _single_option(self,label,value):
        if value == self.default:
            selected = ' selected '
        else:
            selected = ''
        return self.option_html.format(label=label,
                                       value=value,
                                       selected=selected)
    def values(self):
        return self._values
    def html(self):
        options = self.delimiter.join(
            [self._single_option(label,value)
             for (label,value) in zip(self.labels, self._values)]
        )
        return self.select_html.format(name=self.name,
                                       options=options)

class RadioWidget(StaticWidget):
    radio_html = ('<input type="radio" name="{name}" value="{value}" '
                  '{checked} '
                  'onchange="interactUpdate(this.parentNode);">')
    
    def __init__(self, values, name=None,
                 labels=None, default=None, divclass=None,
                 delimiter="      "):
        StaticWidget.__init__(self, name, divclass)
        self._values = values
        self.delimiter = delimiter
        
        if labels is None:
            labels = map(str, values)
        elif len(labels) != len(values):
            raise ValueError("length of labels must match length of values")
        self.labels = labels
        
        if default is None:
            self.default = values[0]
        elif default in values:
            self.default = default
        else:
            raise ValueError("if specified, default must be in values")
            
    def _single_radio(self, value):
        if value == self.default:
            checked = 'checked="checked"'
        else:
            checked = ''
        return self.radio_html.format(name=self.name, value=value,
                                      checked=checked)
    
    def values(self):
        return self._values
            
    def html(self):
        preface = '<b>{name}:</b> '.format(name=self.name)
        return  preface + self.delimiter.join(
            ["{0}: {1}".format(label, self._single_radio(value))
             for (label, value) in zip(self.labels, self._values)])
    

########NEW FILE########
