__FILENAME__ = css
#!/usr/bin/python


class CSS:
    """
    a CSS object is a dictionary whose keys are CSS selectors and whose values
    are dictionaries of CSS declarations. This object is named according to the
    definition of CSS on wikipedia:
        A style sheet consists of a list of rules.
        Each rule or rule-set consists of one or more selectors and a
        declaration block.
        A declaration-block consists of a list of declarations in braces.
        Each declaration itself consists of a property, a colon (:), a value.
    """
    def __init__(self, css=None):
        self.rules = css or {}
        assert isinstance(self.rules, dict)

    def __getitem__(self, selector):
        "returns the dictionary of CSS declarations, given a selector"
        return self.rules[selector]

    def __setitem__(self, selector, declarations):
        "adds a dictionary of CSS declarations to the specified selector"
        assert isinstance(declarations, dict)
        if selector in self.rules:
            self.rules[selector].update(declarations)
        else:
            self.rules[selector] = declarations

    def __add__(self, css):
        if isinstance(css, dict):
            for selector, declarations in css.iteritems():
                try:
                    self.rules[selector].update(declarations)
                except KeyError:
                    self.rules[selector] = declarations
            return self
        elif isinstance(css, CSS):
            return self.__add__(css.rules)
        else:
            errmsg = "Unsupported addition between %s and %s"
            raise Exception(errmsg % (type(self), type(css)))

    def __str__(self):
        css = ""
        for selector, declarations in self.rules.iteritems():
            css += "%s {\n" % selector
            for prop, value in declarations.iteritems():
                if value is None:
                    value = "none"
                css += "\t%s: %s;\n" % (prop, value)
            css += "}\n\n"
        return css

########NEW FILE########
__FILENAME__ = figure
  # -*- coding: utf-8 -*-
'''
Figure
-------

Abstract Base Class for all figures. Currently subclassed by pandas_figure, 
can be subclassed for other figure types. 

'''
import logging
import webbrowser
from HTTPHandler import CustomHTTPRequestHandler, ThreadedHTTPServer
import IPython.core.display
import threading
from cStringIO import StringIO
import time
import json
import os
from pkg_resources import resource_string

from css import CSS
import javascript as JS
import vega

class Figure(object):
    '''Abstract Base Class for all figures'''
    
    def __init__(self, name, width, height, interactive, font, logging, 
                 template, host, port, **kwargs):
        '''
        Figure is the abstract base class for all figures. Currently 
        subclassed by pandas_figure and networkx_figure. 
        
        Parameters:
        -----------
        name: string
            Name of visualization; will appear in title bar of the webpage, 
            and in the folder where files are stored. 
        width : int 
            Width of the figure in pixels
        height : int 
            Height of the figure in pixels
        interactive : boolean
            Set to false if you are drawing the graph using a script and
            not in the command line. 
        font : string
            Name of the font you'd like to use. See     
            http://www.google.com/webfonts for options
        logging: 
            Logging via the sandard Python loggin library
        template: string
            HTML template for figure. Defaults to /d3py_template (Also, when 
            building your own HTML, please see the default template for 
            correct usage of {{ name }}, {{ host }}, {{ port }}, and 
            {{ font }}
        host: string
            Generally default to 'localhost' for local plotting
        port: int
            Generally defaults to 8000 for local plotting
        
        '''

        # store data
        self.name = '_'.join(name.split())
        d3py_path = os.path.abspath(os.path.dirname(__file__))
        self.filemap = {"static/d3.js":{"fd":open(d3py_path+"/d3.js","r"), 
                                        "timestamp":time.time()},}
                                                                               
        # Networking stuff
        self.host = host
        self.port = port
        self._server_thread = None
        self.httpd = None

        '''Interactive is true by default, as this is designed to be a command
        line tool. We do not want to block interaction after plotting.'''
        self.interactive = interactive
        self.logging = logging

        # initialise strings
        self.js = JS.JavaScript()
        self.margins = {"top": 10, "right": 20, "bottom": 25, "left": 60, 
                        "height":height, "width":width}
        
        # we use bostock's scheme http://bl.ocks.org/1624660
        self.css = CSS()
        self.html = ""
        self.template = template or resource_string('d3py', 'd3py_template.html')
        self.js_geoms = JS.JavaScript()
        self.css_geoms = CSS()
        self.geoms = []
        # misc arguments - these go into the css!
        self.font = font
        self.args = {"width": width - self.margins["left"] - self.margins["right"],
                     "height": height - self.margins["top"] - self.margins["bottom"],
                     "font-family": "'%s'; sans-serif"%self.font}
        
        kwargs = dict([(k[0].replace('_','-'), k[1]) for k in kwargs.items()])
        self.args.update(kwargs)
        
    def update(self):
        '''Build or update JS, CSS, & HTML, and save all data'''
        logging.debug('updating chart')
        self._build()
        self.save()
        
    def _build(self):
        '''Build all JS, CSS, HTML, and Geometries'''
        logging.debug('building chart')
        if hasattr(self, 'vega'):
            self.vega.build_vega()
        self._build_js()
        self._build_css()
        self._build_html()
        self._build_geoms()

    def _build_css(self):
        '''Build basic CSS'''
        chart = {}
        chart.update(self.args)
        self.css["#chart"] = chart

    def _build_html(self):
        '''Build HTML, either via 'template' argument or default template 
        at /d3py_template.html.'''
        self.html = self.template
        self.html = self.html.replace("{{ name }}", self.name)
        self.html = self.html.replace("{{ font }}", self.font)
        self._save_html()

    def _build_geoms(self):
        '''Build D3py CSS/JS geometries. See /geoms for more details'''
        self.js_geoms = JS.JavaScript()
        self.css_geoms = CSS()
        for geom in self.geoms:
            self.js_geoms.merge(geom._build_js())
            self.css_geoms += geom._build_css()
        
    def _build_js(self):
        '''Build Javascript for Figure'''
        draw = JS.Function("draw", ("data",))
        draw += "var margin = %s;"%json.dumps(self.margins).replace('""','')
        draw += "    width = %s - margin.left - margin.right"%self.margins["width"]
        draw += "    height = %s - margin.top - margin.bottom;"%self.margins["height"]
        # this approach to laying out the graph is from Bostock: http://bl.ocks.org/1624660
        draw += "var g = " + JS.Selection("d3").select("'#chart'") \
            .append("'svg'") \
            .attr("'width'", 'width + margin.left + margin.right + 25') \
            .attr("'height'", 'height + margin.top + margin.bottom + 25') \
            .append("'g'") \
            .attr("'transform'", "'translate(' + margin.left + ',' + margin.top + ')'")

        self.js = JS.JavaScript() + draw + JS.Function("init")
        
    def _cleanup(self):
        raise NotImplementedError


    def __enter__(self):
        self.interactive = False
        return self

    def __exit__(self, ex_type, ex_value, ex_tb):
        if ex_tb is not None:
            print "Cleanup after exception: %s: %s"%(ex_type, ex_value)
        self._cleanup()

    def __del__(self):
        self._cleanup()

    def ion(self):
        """
        Turns interactive mode on ala pylab
        """
        self.interactive = True
    
    def ioff(self):
        """
        Turns interactive mode off
        """
        self.interactive = False

    def _set_data(self):
        '''Update JS, CSS, HTML, save all'''
        self.update()
        
    def __add__(self, geom):
        '''Add d3py.geom object to the Figure'''
        if isinstance(figure, vega.Vega):
            self._add_vega(figure)
        else: 
            self._add_geom(figure)

    def __iadd__(self, figure):
        '''Add d3py.geom or d3py.vega object to the Figure'''
        if isinstance(figure, vega.Vega):
            self._add_vega(figure)
        else: 
            self._add_geom(figure)
        return self
        
    def _add_vega(self, figure):
        '''Add D3py.Vega Figure'''
        self.vega = figure
        self.vega.tabular_data(self.data, columns=self.columns,
                               use_index=self.use_index)
        self.template = resource_string('d3py', 'vega_template.html')
        self._save_vega()                                 
        
    def _add_geom(self, geom):
        '''Append D3py.geom to existing D3py geoms'''
        self.geoms.append(geom)
        self.save()
        
    def save(self):
        '''Save data and all Figure components: JS, CSS, and HTML'''
        logging.debug('saving chart')
        if hasattr(self, 'vega'):
            self._save_vega()
        self._save_data()
        self._save_css()
        self._save_js()
        self._save_html()
        
    def _save_data(self,directory=None):
        """
        Build file map (dir path and StringIO for output) of data
        
        Parameters:
        -----------
        directory : str
            Specify a directory to store the data in (optional)
        """
        # write data
        filename = "%s.json"%self.name
        self.filemap[filename] = {"fd":StringIO(self._data_to_json()),
                                  "timestamp":time.time()}
                                  
    def _save_vega(self):
        '''Build file map (dir path and StringIO for output) of Vega'''
        vega = json.dumps(self.vega.vega, sort_keys=True, indent=4)
        self.filemap['vega.json'] = {"fd":StringIO(vega),
                                     "timestamp":time.time()}

    def _save_css(self):
        '''Build file map (dir path and StringIO for output) of CSS'''
        filename = "%s.css"%self.name
        css = "%s\n%s"%(self.css, self.css_geoms)
        self.filemap[filename] = {"fd":StringIO(css),
                                  "timestamp":time.time()}

    def _save_js(self):
        '''Build file map (dir path and StringIO for output) of data'''
        final_js = JS.JavaScript()
        final_js.merge(self.js)
        final_js.merge(self.js_geoms)

        filename = "%s.js"%self.name
        js = "%s"%final_js
        self.filemap[filename] = {"fd":StringIO(js),
                "timestamp":time.time()}

    def _save_html(self):
        '''Save HTML data. Will save Figure name to 'name.html'. Will also
        replace {{ port }} and {{ host }} fields in template with
        Figure.port and Figure.host '''
        self.html = self.html.replace("{{ port }}", str(self.port))
        self.html = self.html.replace("{{ host }}", str(self.host))
        # write html
        filename = "%s.html"%self.name
        self.filemap[filename] = {"fd":StringIO(self.html),
                "timestamp":time.time()}
                
    def _data_to_json(self):
        raise NotImplementedError

    def show(self, interactive=None):
        self.update()
        self.save()
        if interactive is not None:
            blocking = not interactive
        else:
            blocking = not self.interactive

        if blocking:
            self._serve(blocking=True)
        else:
            # if not blocking, we serve the 
            self._serve(blocking=False)
            # fire up a browser
            webbrowser.open_new_tab("http://%s:%s/%s.html"%(self.host,self.port, self.name))

    def display(self, width=700, height=400):
        html = "<iframe src=http://%s:%s/%s.html width=%s height=%s>" %(self.host, self.port, self.name, width, height)
        IPython.core.display.HTML(html)

    def _serve(self, blocking=True):
        """
        start up a server to serve the files for this vis.
        """
        msgparams = (self.host, self.port, self.name)
        url = "http://%s:%s/%s.html"%msgparams
        if self._server_thread is None or self._server_thread.active_count() == 0:
            Handler = CustomHTTPRequestHandler
            Handler.filemap = self.filemap
            Handler.logging = self.logging
            try:
                self.httpd = ThreadedHTTPServer(("", self.port), Handler)
            except Exception, e:
                print "Exception %s"%e
                return False
            if blocking:
                logging.info('serving forever on port: %s'%msgparams[1])
                msg = "You can find your chart at " + url
                print msg
                print "Ctrl-C to stop serving the chart and quit!"
                self._server_thread = None
                self.httpd.serve_forever()
            else:
                logging.info('serving asynchronously on port %s'%msgparams[1])
                self._server_thread = threading.Thread(
                    target=self.httpd.serve_forever
                )
                self._server_thread.daemon = True
                self._server_thread.start()
                msg = "You can find your chart at " + url
                print msg


    def _cleanup(self):
        try:
            if self.httpd is not None:
                print "Shutting down httpd"
                self.httpd.shutdown()
                self.httpd.server_close()
        except Exception, e:
            print "Error in clean-up: %s"%e




########NEW FILE########
__FILENAME__ = area
from geom import Geom, JavaScript, Selection, Function

class Area(Geom):
    def __init__(self,x,yupper,ylower,**kwargs):
        Geom.__init__(self,**kwargs)
        self.x = x
        self.yupper = yupper
        self.ylower = ylower
        self.params = [x, yupper, ylower]
        self.debug = True
        self.name = "area"
        self._build_js()
        self._build_css()
        
    def _build_js(self):


        scales = """
            scales = {
                x: get_scales(['%s'], 'horizontal'),
                y: get_scales(['%s','%s'], 'vertical')
            }
        """%(self.x, self.ylower, self.yupper)


        x_fxn = Function(None, "d", "return scales.x(d.%s)"%self.x)
        y1_fxn = Function(None, "d", "return scales.y(d.%s)"%self.yupper)
        y0_fxn = Function(None, "d", "return scales.y(d.%s)"%self.ylower)


        draw = Function("draw", ("data", ))
        draw += scales
        draw += "var area = " + Selection("d3.svg").add_attribute("area") \
            .add_attribute("x", x_fxn) \
            .add_attribute("y0", y0_fxn) \
            .add_attribute("y1", y1_fxn)
    
        draw += "console.log(data)"
        draw += "console.log(area(data))"
        draw += "console.log(scales.y(data[0].y))"
        
        draw += Selection("g").append("'svg:path'") \
             .attr("'d'", "area(data)") \
             .attr("'class'", "'geom_area'") \
             .attr("'id'", "'area_%s_%s_%s'"%(self.x, self.yupper, self.ylower))

        self.js = JavaScript(draw)
        return self.js
        
    def _build_css(self):
        # default css
        geom_area = {"stroke-width": "1px", "stroke": "black", "fill": "MediumSeaGreen"}
        self.css[".geom_area"] = geom_area

        self.css["#area_%s_%s_%s"%(self.x,self.yupper, self.ylower)] = self.styles
        return self.css


########NEW FILE########
__FILENAME__ = bar
from geom import Geom, JavaScript, Selection, Function

class Bar(Geom):
    def __init__(self,x,y,**kwargs):
        """
        This is a vertical bar chart - the height of each bar represents the 
        magnitude of each class
        
        x : string
            name of the column that contains the class labels
        y : string
            name of the column that contains the magnitude of each class
        """
        Geom.__init__(self,**kwargs)
        self.x = x
        self.y = y
        self.name = "bar"
        self._id = 'bar_%s_%s'%(self.x,self.y)
        self._build_js()
        self._build_css()
        self.params = [x,y]
        self.styles = dict([(k[0].replace('_','-'), k[1]) for k in kwargs.items()])
    
    def _build_js(self):


        # build scales
        scales = """ 
            scales = {
                x : get_scales(['%s'], 'horizontal'),
                y : get_scales(['%s'], 'vertical')
            }
        """%(self.x, self.y)

        xfxn = Function(None, "d", "return scales.x(d.%s);"%self.x)
        yfxn = Function( None, "d", "return scales.y(d.%s)"%self.y)
        
        heightfxn = Function(
            None, 
            "d", 
            "return height - scales.y(d.%s)"%self.y
        )

        draw = Function("draw", ("data",), [scales])
        draw += scales
        draw += Selection("g").selectAll("'.bars'") \
            .data("data") \
            .enter() \
            .append("'rect'") \
            .attr("'class'", "'geom_bar'") \
            .attr("'id'", "'%s'"%self._id) \
            .attr("'x'", xfxn) \
            .attr("'y'", yfxn) \
            .attr("'width'", "scales.x.rangeBand()")\
            .attr("'height'", heightfxn)
        # TODO: rangeBand above breaks for histogram type bar-plots... fix!

        self.js = JavaScript() + draw
        self.js += (Function("init", autocall=True) + "console.debug('Hi');")
        return self.js
    
    def _build_css(self):
        bar = {
            "stroke-width": "1px",
             "stroke": "black",
             "fill-opacity": 0.7,
             "stroke-opacity": 1,
             "fill": "blue"
        }
        bar.update
        self.css[".geom_bar"] = bar 
        # arbitrary styles
        self.css["#"+self._id] = self.styles
        return self.css

########NEW FILE########
__FILENAME__ = geom
from ..css import CSS
from ..javascript import JavaScript, Selection, Function

class Geom:
    def __init__(self, **kwargs):
        self.styles = kwargs
        self.js = JavaScript()
        self.css = CSS()
    
    def _build_js(self):
        raise NotImplementedError
    
    def _build_css(self):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = graph
from geom import Geom, JavaScript, Selection, Function

class ForceLayout(Geom):
    def __init__(self,**kwargs):
        Geom.__init__(self,**kwargs)
        self.name = "forceLayout"
        self._id = 'forceLayout'
        self._build_js()
        self._build_css()
        self.styles = dict([(k[0].replace('_','-'), k[1]) for k in kwargs.items()])
    
    def _build_js(self):
        
        draw = Function("draw", ("data",), [])
        
        draw += Selection("g") \
            .selectAll("'circle.node'") \
            .data("data.nodes") \
            .enter() \
            .append("'circle'") \
            .attr("'class'","'node'") \
            .attr("'r'", 12) 
        
        draw += Selection("g") \
            .selectAll("'line.link'") \
            .data("data.links") \
            .enter() \
            .append("'line'") \
            .attr("'class'", "'link'")
        
        code = [
            "var force = d3.layout.force()",
                ".charge(-120)",
                '.linkDistance(30)',
                '.size([width, height])',
                '.nodes(data.nodes)',
                '.links(data.links);'
               
            
            'force.on("tick", function() {',
                'g.selectAll("line.link").attr("x1", function(d) { return d.source.x; })',
                    '.attr("y1", function(d) { return d.source.y; })',
                    '.attr("x2", function(d) { return d.target.x; })',
                    '.attr("y2", function(d) { return d.target.y; });',
                
                'g.selectAll("circle.node").attr("cx", function(d) { return d.x; })',
                    '.attr("cy", function(d) { return d.y; });',
                '});',
                
            'g.selectAll("circle.node").call(force.drag);',
            
            'force.start();',
        ]
        # TODO the order of the next two lines seems inappropriately important
        draw += JavaScript(code)
        self.js = JavaScript() + draw
        self.js += (Function("init", autocall=True) + "console.debug('Hi');")
        
        return self.js
    
    def _build_css(self):
        line = {
            "stroke-width": "1px",
             "stroke": "black",
        }
        self.css[".link"] = line
        # arbitrary styles
        self.css["#"+self._id] = self.styles
        return self.css
        

########NEW FILE########
__FILENAME__ = line
from geom import Geom, JavaScript, Selection, Function

class Line(Geom):
    def __init__(self,x,y,**kwargs):
        Geom.__init__(self,**kwargs)
        self.x = x
        self.y = y
        self.params = [x,y]
        self.debug = True
        self.name = "line"
        self._build_js()
        self._build_css()
        
    def _build_js(self):
        # build scales
        scales = """ 
            scales = {
                x : get_scales(['%s'], 'horizontal'),
                y : get_scales(['%s'], 'vertical')
            }
        """%(self.x, self.y)
        # add the line

        x_fxn = Function(None, "d", "return scales.x(d.%s)"%self.x)
        y_fxn = Function(None, "d", "return scales.y(d.%s)"%self.y)

        draw = Function("draw", ("data", ))
        draw += scales
        draw += "var line = " + Selection("d3.svg").add_attribute("line") \
                                                      .add_attribute("x", x_fxn) \
                                                      .add_attribute("y", y_fxn)

        draw += Selection("g").append("'svg:path'") \
                                 .attr("'d'", "line(data)") \
                                 .attr("'class'", "'geom_line'") \
                                 .attr("'id'", "'line_%s_%s'"%(self.x, self.y))

        self.js = JavaScript(draw)
        return self.js
        
    def _build_css(self):
        # default css
        geom_line = {"stroke-width": "1px", "stroke": "black", "fill": None}
        self.css[".geom_line"] = geom_line

        self.css["#line_%s_%s"%(self.x,self.y)] = self.styles
        return self.css


########NEW FILE########
__FILENAME__ = point
from geom import Geom, JavaScript, Selection, Function

class Point(Geom):
    def __init__(self,x,y,c=None,**kwargs):
        Geom.__init__(self, **kwargs)
        self.x = x
        self.y = y
        self.c = c
        self._id = 'point_%s_%s_%s'%(self.x,self.y,self.c)
        self.params = [x,y,c]
        self.name = "point"
        self._build_css()
        self._build_js()
    
    def _build_css(self):
        point = {
            "stroke-width"  : "1px",
             "stroke"        : "black",
             "fill-opacity"  : 0.7,
             "stroke-opacity": 1,
             "fill"          : "blue"
        }
        self.css[".geom_point"] = point 
        # arbitrary styles
        self.css["#"+self._id] = self.styles
        return self.css
        
    def _build_js(self):
        scales = """ 
            scales = {
                x : get_scales(['%s'], 'horizontal'),
                y : get_scales(['%s'], 'vertical')
            }
        """%(self.x, self.y)
        draw = Function("draw", ("data",))
        draw += scales
        js_cx = Function(None, "d", "return scales.x(d.%s);"%self.x) 
        js_cy = Function(None, "d", "return scales.y(d.%s);"%self.y) 

        obj = Selection("g").selectAll("'.geom_point'")      \
                            .data("data")                    \
                            .enter()                         \
                            .append("'svg:circle'")          \
                            .attr("'cx'", js_cx)             \
                            .attr("'cy'", js_cy)             \
                            .attr("'r'", 4)                  \
                            .attr("'class'", "'geom_point'") \
                            .attr("'id'", "'%s'"%self._id)
        if self.c:
            fill = Function(None, "return d.%s;"%self.c)
            obj.add_attribute("style", "fill", fill)

        draw += obj
        self.js = JavaScript(draw)
        return self.js

########NEW FILE########
__FILENAME__ = xaxis
from geom import Geom, JavaScript, Selection, Function

class xAxis(Geom):
    def __init__(self,x, label=None, **kwargs):
        """
        x : string
            name of the column you want to use to define the x-axis
        """
        Geom.__init__(self, **kwargs)
        self.x = x
        self.label = label if label else x
        self.params = [x]
        self._id = 'xaxis'
        self.name = 'xaxis'
        self._build_css()
        self._build_js()
    
    def _build_js(self):
        draw = Function("draw", ("data",), [])
        scale = "scales.x"
        draw += "xAxis = d3.svg.axis().scale(%s)"%scale
        
        xaxis_group = Selection("g").append('"g"') \
              .attr('"class"','"xaxis"') \
              .attr('"transform"', '"translate(0," + height + ")"') \
              .call("xAxis")
        draw += xaxis_group

        if self.label:
            # TODO: Have the transform on this label be less hacky
            label_group = Selection("g").append('"text"') \
                    .add_attribute("text", '"%s"'%self.label) \
                    .attr('"text-anchor"', '"middle"') \
                    .attr('"x"', "width/2") \
                    .attr('"y"', "height+45")
            draw += label_group

        self.js = JavaScript() + draw
        return self.js
    
    def _build_css(self):
        axis_path = {
            "fill" : "none",
            "stroke" : "#000"
        }
        self.css[".xaxis path"] = axis_path
        axis_path = {
            "fill" : "none",
            "stroke" : "#000"
        }
        self.css[".xaxis line"] = axis_path
        
        return self.css

########NEW FILE########
__FILENAME__ = yaxis
from geom import Geom, JavaScript, Selection, Function

class yAxis(Geom):
    def __init__(self,y, label=None, **kwargs):
        """
        y : string
            name of the column you want to use to define the y-axis
        """
        Geom.__init__(self, **kwargs)
        self.y = y
        self.label = label if label else y
        self.params = [y]
        self._id = 'yaxis'
        self.name = 'yaxis'
        self._build_css()
        self._build_js()
    
    def _build_js(self):
        draw = Function("draw", ("data",), [])
        scale = "scales.y"
        draw += "yAxis = d3.svg.axis().scale(%s).orient('left')"%scale
        
        yaxis_group = Selection("g").append('"g"') \
              .attr('"class"','"yaxis"') \
              .call("yAxis")
        draw += yaxis_group

        if self.label:
            # TODO: Have the transform on this label be less hacky
            label_group = Selection("g").append('"text"') \
                    .add_attribute("text", '"%s"'%self.label) \
                    .attr('"y"', '- margin.left + 15') \
                    .attr('"x"', '- height / 2.0') \
                    .attr('"text-anchor"', '"middle"') \
                    .attr('"transform"', '"rotate(-90, 0, 0)"')
            draw += label_group

        self.js = JavaScript() + draw
        return self.js
    
    def _build_css(self):
        axis_path = {
            "fill" : "none",
            "stroke" : "#000"
        }
        self.css[".yaxis path"] = axis_path
        axis_path = {
            "fill" : "none",
            "stroke" : "#000"
        }
        self.css[".yaxis line"] = axis_path
        
        return self.css

########NEW FILE########
__FILENAME__ = HTTPHandler
import SimpleHTTPServer
import SocketServer
from cStringIO import StringIO
import sys

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True


class CustomHTTPRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        """
        We get rid of the BaseHTTPRequestHandler logging messages
        because they can get annoying!
        """
        if self.logging:
            super().log_message(format, *args)

    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.seek(0)

    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.seek(0)

    def send_head(self):
        """
        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.path[1:] #get rid of leading '/'
        f = None
        ctype = self.guess_type(path)
        try:
            f = self.filemap[path]["fd"]
        except KeyError:
            return self.list_directory()
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.send_header("Last-Modified", self.date_time_string(self.filemap[path]["timestamp"]))
        self.end_headers()
        return f

    def list_directory(self):
        f = StringIO()
        f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write("<html>\n<title>Directory listing</title>\n")
        f.write("<body>\n<h2>Directory listing</h2>\n")
        f.write("<hr>\n<ul>\n")
        for path, meta in self.filemap.iteritems():
            f.write('<li><a href="%s">%s</a>\n' % (path, path))
        f.write("</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        encoding = sys.getfilesystemencoding()
        self.send_header("Content-type", "text/html; charset=%s" % encoding)
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

########NEW FILE########
__FILENAME__ = javascript
#!/usr/bin/python
import logging

class JavaScript(object):
    # TODO: Add a lookup function so you can easily find/edit functions/objects
    #       defined within the JavaScript object
    def __init__(self, statements=None):
        self.statements = []
        self.objects_lookup = {}
        if statements is not None:
            statements = self._obj_to_statements(statements)
            if isinstance(statements, list):
                self.statements = statements
                self.objects_lookup = self.parse_objects()
            else:
                raise Exception("Invalid inputed statement type")

    def merge(self, other):
        for line in other.statements:
            if hasattr(line, "name") and (line.name, type(line.__class__)) in self.objects_lookup:
                idx = self.objects_lookup[(line.name, type(line.__class__))][1]
                self.statements[idx] += line
            else:
                self.statements.append(line)
        self.objects_lookup = self.parse_objects()

    def get_object(self, name, objtype):
        return self.objects_lookup[(name,type(objtype))][0]

    def __getitem__(self, item):
        return self.statements[item]

    def __setitem__(self, item, value):
        self.statements[item] = value

    def parse_objects(self):
        objects = {}
        for i, item in enumerate(self.statements):
            if hasattr(item, "name") and item.name:
                # Is it necissary to compound the key with the class type?
                objects[ (item.name, type(item.__class__)) ] = (item, i)
        return objects

    def _obj_to_statements(self, other):
        if isinstance(other, (Function, Selection)):
            other = [other, ]
        elif isinstance(other, str):
            other = [other, ]
        elif isinstance(other, JavaScript):
            other = other.statements
        return other

    def __radd__(self, other):
        other = self._obj_to_statements(other)
        if isinstance(other, list):
            return JavaScript(self.statements + other)
        raise NotImplementedError

    def __add__(self, other):
        other = self._obj_to_statements(other)
        if isinstance(other, list):
            newobj = JavaScript()
            newobj.statements = self.statements + other
            newobj.objects_lookup = newobj.parse_objects()
            return newobj
        raise NotImplementedError

    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        js = ""
        for statement in self.statements:
            js += str(statement) + "\n"
        return js

class Selection:
    def __init__(self, name):
        self.name = name
        self.opts = []
    
    # TODO maybe add_attribute should be add_method instead?
    
    def add_attribute(self, name, *args):
        self.opts.append({"name":name, "param":",".join(str(x) for x in args)})
        return self

    def select(self, *args): 
        return self.add_attribute("select", *args)
    def selectAll(self, *args): 
        return self.add_attribute("selectAll", *args)
    def data(self, *args): 
        return self.add_attribute("data", *args)
    def enter(self, *args): 
        return self.add_attribute("enter", *args)
    def append(self, *args): 
        return self.add_attribute("append", *args)
    def attr(self, *args): 
        return self.add_attribute("attr", *args)
    def style(self, *args): 
        return self.add_attribute("style", *args)
    def id(self, *args): 
        # TODO what's this one for then?
        return self.add_attribute("id", *args)
    def call(self, *args):
        return self.add_attribute("call", *args)

    def __add__(self, other):
        if isinstance(other, str):
            return self.__str__() + other
        raise NotImplementedError

    def __radd__(self, other):
        return other.__add__( self.__str__() )

    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        obj = self.name
        for opt in self.opts:
            if opt["param"] is None:
                param = ""
            elif isinstance(opt["param"], (list, tuple)):
                param = ",".join([str(x) for x in opt["param"]])
            else:
                param = opt["param"]
            obj += ".%s(%s)"%(opt["name"], param)
        return obj

class Function(object):
    def __init__(self, name=None, arguments=None, statements=None, autocall=False):
        """
        name: string
        
        arguments: list of strings
        
        statements: list of strings
        
        This ends up as 
        
        function name(arg1, arg2, arg3){
            statement1;
            statement2;
            statement3;
        }
        
        """
        self.name = name
        self.arguments = arguments
        if isinstance(statements, str):
            statements = [statements, ]
        self.statements = statements or []
        self.autocall = autocall

    def _obj_to_statements(self, other):
        if isinstance(other, str):
            other = [other, ]
        elif isinstance(other, JavaScript):
            other = other.statements
        elif isinstance(other, Function) and other.name == self.name and other.arguments == self.arguments:
            other = other.statements
        elif isinstance(other, Selection):
            other = [other, ]
        else:
            print isinstance(other, Function)
            print other.statements
            logging.debug('failed to convert %s object:\n %s\n\n to statements'%(type(other),other))
            other = None
        return other

    def __add__(self, more_statements):
        more_statements = self._obj_to_statements(more_statements)
        if isinstance(more_statements, (list, tuple)):
            return Function(
                self.name, 
                self.arguments, 
                self.statements + more_statements, 
                self.autocall
            )
        raise NotImplementedError(type(more_statements))

    def __radd__(self, more_statements):
        more_statements = self._obj_to_statements(more_statements)
        if isinstance(more_statements, (list, tuple)):
            return Function(self.name, self.arguments, more_statements + self.statements, self.autocall)
        raise NotImplementedError

    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        fxn = "function"
        if self.name is not None:
            fxn += " %s"%self.name
        fxn += "(%s) {\n"%(",".join(self.arguments or ""))
        for line in self.statements:
            fxn += "\t%s\n"%str(line)
        fxn += "}\n"
        if self.autocall:
            fxn += "%s(%s);\n"%(self.name, ",".join(self.arguments or ""))
        return fxn

########NEW FILE########
__FILENAME__ = networkx_figure
import logging
import json
from networkx.readwrite import json_graph

import javascript as JS
from figure import Figure

class NetworkXFigure(Figure):
    def __init__(self, graph, name="figure", width=400, height=100, 
        interactive=True, font="Asap", logging=False,  template=None,
        host="localhost", port=8000, **kwargs):
        """
        data : networkx gprah
            networkx graph used for the plot.
        name : string
            name of visualisation. This will appear in the title
            bar of the webpage, and is the name of the folder where
            your files will be stored.
        width : int 
            width of the figure in pixels (default is 400)
        height : int 
            height of the figure in pixels (default is 100)
        interactive : boolean
            set this to false if you are drawing the graph using a script and
            not in the command line (default is True)
        font : string
            name of the font you'd like to use. See     
            http://www.google.com/webfonts for options (default is Asap)
            
        keyword args are converted from foo_bar to foo-bar if you want to pass
        in arbitrary css to the figure    
        
        You will need NetworkX installed for this type of Figure to work!
        http://networkx.lanl.gov/
        """
        super(NetworkXFigure, self).__init__(
            name=name, width=width, height=height, 
            interactive=interactive, font=font, logging=logging,  template=template,
            host=host, port=port, **kwargs
        )
        # store data
        self.G = graph
        self._save_data()

    def _data_to_json(self):
        """
        converts the data frame stored in the figure to JSON
        """
        data = json_graph.node_link_data(self.G)
        s = json.dumps(data)
        return s

########NEW FILE########
__FILENAME__ = pandas_figure
import numpy as np
import logging
import json

import javascript as JS
from figure import Figure

class PandasFigure(Figure):
    def __init__(self, data, name="figure", width=800, height=400, 
        columns = None, use_index=False, interactive=True, font="Asap", 
        logging=False,  template=None, host="localhost", port=8000, **kwargs):
        """
        data : dataFrame
            pandas dataFrame used for the plot. This dataFrame is column centric
        name : string
            name of visualisation. This will appear in the title
            bar of the webpage, and is the name of the folder where
            your files will be stored.
        width : int 
            width of the figure in pixels (default is 1024)
        height : int 
            height of the figure in pixels (default is 768)
        columns: dict, default None
            DataFrame columns you want to visualize for Vega 
        use_index: boolean, default False
            If true, D3py.Vega uses the index for the x-axis instead of a second
            column
        interactive : boolean
            set this to false if you are drawing the graph using a script and
            not in the command line (default is True)
        font : string
            name of the font you'd like to use. See     
            http://www.google.com/webfonts for options (default is Asap)
            
        keyword args are converted from foo_bar to foo-bar if you want to pass
        in arbitrary css to the figure    
        
        """
        super(PandasFigure, self).__init__(name=name, width=width, height=height, 
                                           interactive=interactive, font=font, 
                                           logging=logging,  template=template,
                                           host=host, port=port, **kwargs)
    
        # store data
        self.columns = columns
        self.use_index = use_index
        self.data = data
        self._save_data()

    def _set_data(self, data):
        errmsg = "the %s geom requests %s which is not the given dataFrame!"
        for geom in self.geoms:
            for param in geom.params:
                if param:
                    assert param in data, errmsg%(geom.name, param)
        self.update()

    def _add_geom(self, geom):
        errmsg = "the %s geom requests %s which is not in our dataFrame!"
        for p in geom.params:
            if p:
                assert p in self.data, errmsg%(geom.name, p)
        self.geoms.append(geom)
        self.save()

    def _build_scales(self):
        """
        build a function that returns the requested scale 
        """
        logging.debug('building scales')
        get_scales = """
        function get_scales(colnames, orientation){
            var this_data = d3.merge(
                colnames.map(
                    function(name){
                        return data.map(
                            function(d){
                                return d[name]
                            }
                        )
                    }
                )
            )
            if (orientation==="vertical"){
                if (isNaN(this_data[0])){
                    // not a number
                    console.log('using ordinal scale for vertical axis')
                    scale = d3.scale.ordinal()
                        .domain(this_data)
                        .range(d3.range(height,0,height/this_data.length))
                } else {
                    // a number
                    console.log('using linear scale for vertical axis')
                    extent = d3.extent(this_data)
                    extent[0] = extent[0] > 0 ? 0 : extent[0]
                    scale = d3.scale.linear()
                        .domain(extent)
                        .range([height,0])

                }
            } else {
                if (isNaN(this_data[0])){
                    // not a number
                    console.log('using ordinal scale for horizontal axis')
                    scale = d3.scale.ordinal()
                        .domain(this_data)
                        .rangeBands([0,width], 0.1)
                } else {
                    // a number
                    console.log('using linear scale for horizontal axis')
                    scale = d3.scale.linear()
                        .domain(d3.extent(this_data))
                        .range([0,width])
                }
            }
            return scale
        }
        """
        return get_scales

    def _build_js(self):
        draw = JS.Function("draw", ("data",))
        draw += "var margin = %s;"%json.dumps(self.margins).replace('""','')
        draw += "    width = %s - margin.left - margin.right"%self.margins["width"]
        draw += "    height = %s - margin.top - margin.bottom;"%self.margins["height"]
        # this approach to laying out the graph is from Bostock: http://bl.ocks.org/1624660
        draw += "var g = " + JS.Selection("d3").select("'#chart'") \
            .append("'svg'") \
            .attr("'width'", 'width + margin.left + margin.right + 25') \
            .attr("'height'", 'height + margin.top + margin.bottom + 25') \
            .append("'g'") \
            .attr("'transform'", "'translate(' + margin.left + ',' + margin.top + ')'")
        scales = self._build_scales()
        draw += scales
        self.js = JS.JavaScript() + draw + JS.Function("init")

    def _data_to_json(self):
        """
        converts the data frame stored in the figure to JSON
        """
        def cast(a):
            try:
                return float(a)
            except ValueError:
                return a

        d = [
            dict([
                (colname, cast(row[i]))
                for i,colname in enumerate(self.data.columns)
            ])
            for row in self.data.values
        ]
        try:
            s = json.dumps(d, sort_keys=True, indent=4)
        except OverflowError, e:
            print "Error: Overflow on variable (type %s): %s: %s"%(type(d), d, e)
            raise
        return s

########NEW FILE########
__FILENAME__ = templates
d3py_template = '''<html>
<head>
	<script type="text/javascript" src="http://mbostock.github.com/d3/d3.js"></script>
	<script type="text/javascript" src="http://{{ host }}:{{ port }}/{{ name }}.js"></script>
	<link type="text/css" rel="stylesheet" href="http://{{ host }}:{{ port }}/{{ name }}.css">
    <link href='http://fonts.googleapis.com/css?family={{ font }}' rel='stylesheet' type='text/css'>
    
	<title>d3py: {{ name }}</title>
</head>

<body>
	<div id="chart"></div>
	<script>
		d3.json("http://{{ host }}:{{ port }}/{{ name }}.json", draw);
	</script>
</body>

</html>
'''

########NEW FILE########
__FILENAME__ = test
import unittest
import css
import pandas
import d3py
import javascript


class TestCSS(unittest.TestCase):
    
    def setUp(self):
        self.css = css.CSS()
    
    def test_init(self):
        out = css.CSS({"#test":{"fill":"red"}})
        self.assertTrue(out["#test"] == {"fill":"red"})
    
    def test_get(self):
        self.css["#test"] = {"fill":"red"}
        self.assertTrue(self.css["#test"] == {"fill":"red"})
    
    def test_set(self):
        self.css["#test"] = {"fill":"red"}
        self.css["#test"] = {"stroke":"black"}
        self.assertTrue(self.css["#test"] == {"fill":"red", "stroke":"black"})
    
    def test_add(self):
        a = css.CSS()
        b = css.CSS()
        a["#foo"] = {"fill":"red"}
        a["#bar"] = {"fill":"blue"}
        b["#foo"] = {"stroke":"green"}
        b["#bear"] = {"fill":"yellow"}
        out = a + b
        expected = css.CSS({
            "#foo":{
                "fill":"red", 
                "stroke":"green"
            },
            "#bar" : {"fill":"blue"},
            "#bear" : {"fill":"yellow"}
        })
        self.assertTrue(out.rules == expected.rules)
    
    def test_str(self):
        self.css["#test"] = {"fill":"red"}
        out = str(self.css)
        self.assertTrue(out == "#test {\n\tfill: red;\n}\n\n")

class Test_d3py(unittest.TestCase):
    def setUp(self):
        self.df = pandas.DataFrame({
            "count": [1,2,3],
            "time": [1326825168, 1326825169, 1326825170]
        })
        
    def test_data_to_json(self):
        p = d3py.Figure(self.df)
        j = p.data_to_json()

class Test_JavaScript_object_lookup(unittest.TestCase):
    def setUp(self):
        self.g = javascript.Selection("g").attr("color", "red")
        self.j = javascript.JavaScript() + self.g
        self.f = javascript.Function("test", None, "return 5")
    
    def test_getobject(self):
        self.assertTrue(self.j.get_object("g", javascript.Selection) == self.g)

    def test_inplace_mod(self):
        self.g.attr("test", "test")
        self.assertTrue(self.j.get_object("g", javascript.Selection) == self.g)

    def test_add_fucntion(self):
        self.j += self.f
        self.assertTrue(self.j.get_object("test", javascript.Function) == self.f)

    def test_prepend_function(self):
        self.j += self.f
        self.f = "console.debug('hello')" + self.f
        self.assertTrue(self.j.get_object("test", javascript.Function) == self.f)

if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = vega
'''
Vega/Vincent
-------

The d3py port of the Vincent project: 
https://github.com/wrobstory/vincent

'''

from __future__ import print_function
import os
import json
from pkg_resources import resource_string
import pandas as pd
import pdb


class Vega(object):
    '''Vega abstract base class'''

    def __init__(self, width=400, height=200,
                 padding={'top': 10, 'left': 30, 'bottom': 20, 'right': 10},
                 viewport=None):
        '''
        The Vega classes generate JSON output in Vega grammar, a
        declarative format for creating and saving visualization designs.
        This class is meant to be an abstract base class on which to build
        the other piece of the complete VEGA specification.

        A Vega object is instantiated with only the Vega Visualization basic,
        properties, with default values for the name, width, height, padding,
        and viewport.

        Parameters:
        -----------

        width: int, default 800
            Width of the visualization
        height: int, default 400
            Height of the visualization
        padding: dict, default {'top': 10, 'left': 30, 'bottom':20, 'right':10}
            Internal margins for the visualization, Top, Left, Bottom, Right
        viewport: list, default None
            Width and height of on-screen viewport

        '''

        self.width = width
        self.height = height
        self.padding = padding
        self.viewport = viewport
        self.visualization = {'width': self.width,
                              'padding': self.padding,
                              'viewport': self.viewport}
        self.data = []
        self.scales = []
        self.axes = []
        self.marks = []
        self.build_vega()

    def __add__(self, tuple):
        '''Allow for updating of Vega with add operator'''
        self.update_component('add', *tuple)

    def __iadd__(self, tuple):
        '''Allow for updating of Vega with iadd operator'''
        self.update_component('add', *tuple)
        return self

    def __sub__(self, tuple):
        '''Allow for updating of Vega with sub operator'''
        self.update_component('remove', *tuple)

    def __isub__(self, tuple):
        '''Allow for updating of Vega with sub operator'''
        self.update_component('remove', *tuple)
        return self

    def build_vega(self, *args):
        '''Build complete vega specification. String arguments passed will not
        be included in vega dict.

        Ex: object.build_vega('viewport')

        '''

        keys = ['width', 'height', 'padding', 'viewport', 'data',
                'scales', 'axes', 'marks']
        self.vega = {}
        for key in keys:
            if key not in args:
                self.vega[key] = getattr(self, key)

    def update_vis(self, **kwargs):
        '''
        Update Vega Visualization basic properties:
        width, height, padding, viewport

        Ex: >>>my_vega.update_vis(height=800, width=800)
        '''

        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        self.build_vega()

    def build_component(self, append=True, **kwargs):
        '''Build complete Vega component.

        The Vega grammar will update with passed keywords. This method
        rebuilds an entire Vega component: axes, data, scales, marks, etc.

        Examples:
        >>>my_vega.build_component(scales=[{"domain": {"data": "table",
                                                      "field": "data.x"},
                                            "name":"x", "type":"ordinal",
                                            "range":"width"}])
        >>>my_vega.build_component(axes=[{"scale": "x", type: "x"},
                                         {"scale": "y", type: "y"}],
                                   append=False)

        '''

        for key, value in kwargs.iteritems():
                setattr(self, key, value)

        self.build_vega()

    def update_component(self, change, value, parameter, index, *args):
        '''Update individual parameters of any component.

        Parameters:
        -----------
        change: string, either 'add' or 'remove'
            'add' will add the value to the last specified key in *args (this
            can be a new key). 'remove' will remove the key specified by
            'value'.
        value: Any JSON compatible datatype
            The value you want to substitute into the component
        parameter: string
            The Vega component you want to modify (scales, marks, etc)
        index: int
            The index of dict/object in the component array you want to mod

        Examples:
        >>>my_vega.update_component(add, 'w', 'axes', 0, 'scale')
        >>>my_vega.update_component('remove', 'width', 'marks', 0,
                                    'properties', 'enter')

        '''
        def set_keys(value, param, key, *args):
            if args:
                return set_keys(value, param.get(key), *args)
            if change == 'add':
                param[key] = value
            else:
                param[key].pop(value)

        parameter = getattr(self, parameter)[index]
        if not args:
            args = [value]
            if change == 'remove':
                parameter.pop(value)
                self.build_vega()
                return
        set_keys(value, parameter, *args)

        self.build_vega()

    def multi_update(self, comp_list):
        '''Pass a list of component updates to change all'''

        for update in comp_list:
            self.update_component(*update)

    def _json_IO(self, host, port):
        '''Return data values as JSON for StringIO '''

        data_vals = self.data[0]['values']
        self.update_component('remove', 'values', 'data', 0)
        url = ''.join(['http://', host, ':', str(port), '/data.json'])
        self.update_component('add', url, 'data', 0, 'url')
        vega = json.dumps(self.vega, sort_keys=True, indent=4)
        data = json.dumps(data_vals, sort_keys=True, indent=4)
        return vega, data

    def to_json(self, path, split_data=False, html=False):
        '''
        Save Vega object to JSON

        Parameters:
        -----------
        path: string
            File path for Vega grammar JSON.
        split_data: boolean, default False
            Split the output into a JSON with only the data values, and a
            Vega grammar JSON referencing that data.
        html: boolean, default False
            Output Vega Scaffolding HTML file to path

        '''

        def json_out(path, output):
            '''Output to JSON'''
            with open(path, 'w') as f:
                json.dump(output, f, sort_keys=True, indent=4,
                          separators=(',', ': '))

        if split_data:
            data_out = self.data[0]['values']
            self.update_component('remove', 'values', 'data', 0)
            self.update_component('add', 'data.json', 'data', 0, 'url')
            data_path = os.path.dirname(path) + r'/data.json'
            json_out(data_path, data_out)
            json_out(path, self.vega)
            if html:
                template = resource_string('vincent', 'vega_template.html')
                html_path = ''.join([os.path.dirname(path),
                                     r'/vega_template.html'])
                with open(html_path, 'w') as f:
                    f.write(template)

            self.tabular_data(self.raw_data)
            
        else:
            json_out(path, self.vega)

    def tabular_data(self, data, name="table", columns=None, use_index=False,
                     append=False):
        '''Create the data for a bar chart in Vega grammer. Data can be passed
        in a list, dict, or Pandas Dataframe. 

        Parameters:
        -----------
        name: string, default "table"
            Type of visualization
        columns: list, default None
            If passing Pandas DataFrame, you must pass at least one column
            name.If one column is passed, x-values will default to the index
            values.If two column names are passed, x-values are columns[0],
            y-values columns[1].
        use_index: boolean, default False
            Use the DataFrame index for your x-values
        append: boolean, default False
            Append new data to data already in object

        Examples:
        ---------
        >>>myvega.tabular_data([10, 20, 30, 40, 50])
        >>>myvega.tabular_data({'A': 10, 'B': 20, 'C': 30, 'D': 40, 'E': 50}
        >>>myvega.tabular_data(my_dataframe, columns=['column 1'],
                               use_index=True)
        >>>myvega.tabular_data(my_dataframe, columns=['column 1', 'column 2'])

        '''
        
        self.raw_data = data

        #Tuples
        if isinstance(data, tuple):
            values = [{"x": x[0], "y": x[1]} for x in data]

        #Lists
        if isinstance(data, list):
            if append:
                start = self.data[0]['values'][-1]['x'] + 1
                end = len(self.data[0]['values']) + len(data)
            else:
                start, end = 0, len(data)

            default_range = xrange(start, end+1, 1)
            values = [{"x": x, "y": y} for x, y in zip(default_range, data)]

        #Dicts
        if isinstance(data, dict) or isinstance(data, pd.Series):
            values = [{"x": x, "y": y} for x, y in data.iteritems()]

        #Dataframes
        if isinstance(data, pd.DataFrame):
            if len(columns) > 1 and use_index:
                raise ValueError('If using index as x-axis, len(columns)'
                                 'cannot be > 1')
            if use_index or len(columns) == 1:
                values = [{"x": x[0], "y": x[1][columns[0]]}
                          for x in data.iterrows()]
            else:
                values = [{"x": x[1][columns[0]], "y": x[1][columns[1]]}
                          for x in data.iterrows()]

        if append:
            self.data[0]['values'].extend(values)
        else:
            self.data = []
            self.data.append({"name": name, "values": values})

        self.build_vega()


class Bar(Vega):
    '''Create a bar chart in Vega grammar'''

    def __init__(self):
        '''Build Vega Bar chart with default parameters'''
        super(Bar, self).__init__()

        self.scales = [{"name": "x", "type": "ordinal", "range": "width",
                        "domain": {"data": "table", "field": "data.x"}},
                       {"name": "y", "range": "height", "nice": True,
                        "domain": {"data": "table", "field": "data.y"}}]

        self.axes = [{"type": "x", "scale": "x"}, {"type": "y", "scale": "y"}]

        self.marks = [{"type": "rect", "from": {"data": "table"},
                      "properties": {
                                     "enter": {
                                     "x": {"scale": "x", "field": "data.x"},
                                     "width": {"scale": "x", "band": True,
                                               "offset": -1},
                                     "y": {"scale": "y", "field": "data.y"},
                                     "y2": {"scale": "y", "value": 0}
                                     },
                                     "update": {"fill": {"value": "#2a3140"}},
                                     "hover": {"fill": {"value": "#a63737"}}
                                      }
                      }]

        self.build_vega()


class Area(Bar):
    '''Create an area chart in Vega grammar'''

    def __init__(self):
        '''Build Vega Area chart with default parameters'''
        super(Area, self).__init__()
        area_updates = [('remove', 'width', 'marks', 0, 'properties', 'enter'),
                        ('add', 'area', 'marks', 0, 'type'),
                        ('add', 'linear', 'scales', 0, 'type')]

        self.multi_update(area_updates)
        self.build_vega()


class Scatter(Bar):
    '''Create a scatter plot in Vega grammar'''

    def __init__(self):
        '''Build Vega Scatter chart with default parameters'''
        super(Scatter, self).__init__()
        self.height, self.width = 400, 400
        self.padding = {'top': 40, 'left': 40, 'bottom': 40, 'right': 40}
        scatter_updates = [('remove', 'type', 'scales', 0),
                           ('add', True, 'scales', 0, 'nice'),
                           ('remove', 'width', 'marks', 0, 'properties',
                            'enter'),
                           ('remove', 'y2', 'marks', 0, 'properties',
                            'enter'),
                           ('remove', 'hover', 'marks', 0, 'properties'),
                           ('add', {'value': '#2a3140'}, 'marks', 0,
                            'properties', 'enter', 'stroke'),
                           ('add', {'value': 0.9}, 'marks', 0, 'properties',
                            'enter', 'fillOpacity'),
                           ('add', 'symbol', 'marks', 0, 'type')]

        self.multi_update(scatter_updates)
        self.build_vega()


class Line(Bar):
    '''Create a line plot in Vega grammar'''

    def __init__(self):
        '''Build Vega Line plot chart with default parameters'''

        pass

        #Something still broken- need to do some syntax hunting...
        super(Line, self).__init__()
        line_updates = [('add', 'linear', 'scales', 0, 'type'),
                        ('remove', 'update', 'marks', 0, 'properties'),
                        ('remove', 'hover', 'marks', 0, 'properties'),
                        ('remove', 'width', 'marks', 0, 'properties', 'enter'),
                        ('add', 'line', 'marks', 0, 'type'),
                        ('add', {'value': '#2a3140'}, 'marks', 0,
                         'properties', 'enter', 'stroke'),
                        ('add', {'value': 2}, 'marks', 0, 'properties',
                         'enter', 'strokeWidth')]

        self.multi_update(line_updates)
        self.build_vega()

########NEW FILE########
__FILENAME__ = d3py_area
import numpy as np
import d3py
import pandas

N = 500
T = 5*np.pi
x = np.linspace(-T,T,N)
y = np.sin(x)
y0 = np.cos(x)

df = pandas.DataFrame({
    'x' : x,
    'y' : y,
    'y0' : y0,
})

with d3py.PandasFigure(df, 'd3py_area', width=500, height=250) as fig:
    fig += d3py.geoms.Area('x', 'y', 'y0')
    fig += d3py.geoms.xAxis('x')
    fig += d3py.geoms.yAxis('y')
    fig.show()

########NEW FILE########
__FILENAME__ = d3py_bar
import pandas
import d3py

import logging
logging.basicConfig(level=logging.DEBUG)


df = pandas.DataFrame(
    {
        "count" : [1,4,7,3,2,9],
        "apple_type": ["a", "b", "c", "d", "e", "f"],
    }
)

# use 'with' if you are writing a script and want to serve this up forever
with d3py.PandasFigure(df) as p:
    p += d3py.Bar(x = "apple_type", y = "count", fill = "MediumAquamarine")
    p += d3py.xAxis(x = "apple_type")
    p.show()

# if you are writing in a terminal, use without 'with' to keep everything nice
# and interactive
"""
p = d3py.PandasFigure(df)
p += d3py.Bar(x = "apple_type", y = "count", fill = "MediumAquamarine")
p += d3py.xAxis(x = "apple_type")
p.show()
"""

########NEW FILE########
__FILENAME__ = d3py_graph
import d3py
import networkx as nx

import logging
logging.basicConfig(level=logging.DEBUG)

G=nx.Graph()
G.add_edge(1,2)
G.add_edge(1,3)
G.add_edge(3,2)
G.add_edge(3,4)
G.add_edge(4,2)

# use 'with' if you are writing a script and want to serve this up forever
with d3py.NetworkXFigure(G, width=500, height=500) as p:
    p += d3py.ForceLayout()
    p.show()

########NEW FILE########
__FILENAME__ = d3py_line
import numpy as np
import d3py
import pandas

T = 5*np.pi
x = np.linspace(-T,T,100)
a = 0.05
y = np.exp(-a*x) * np.sin(x)

df = pandas.DataFrame({
    'x' : x,
    'y' : y
})

with d3py.PandasFigure(df, 'd3py_line', width=600, height=200) as fig:
    fig += d3py.geoms.Line('x', 'y', stroke='BlueViolet')
    fig += d3py.xAxis('x')
    fig += d3py.yAxis('y')
    fig.show()

########NEW FILE########
__FILENAME__ = d3py_multiline
import numpy as np
import d3py
import pandas

T = 5*np.pi
x = np.linspace(-T,T,100)
a = 0.05
y = np.exp(-a*x) * np.sin(x)
z = np.exp(-a*x) * np.sin(0.5*x)

df = pandas.DataFrame({
    'x' : x,
    'y' : y,
    'z' : z,
})

with d3py.PandasFigure(df, 'd3py_line', width=600, height=200) as fig:
    fig += d3py.geoms.Line('x', 'y', stroke='BlueViolet')
    fig += d3py.geoms.Line('x', 'z', stroke='DeepPink')
    fig += d3py.xAxis('x')
    fig += d3py.yAxis('y')
    fig.show()

########NEW FILE########
__FILENAME__ = d3py_scatter
import numpy as np
import pandas
import d3py
n = 400

df = pandas.DataFrame({
    'd1': np.arange(0,n),
    'd2': np.random.normal(0, 1, n)
})

with d3py.PandasFigure(df, "example scatter plot using d3py", width=400, height=400) as fig:
    fig += d3py.Point("d1", "d2", fill="DodgerBlue")
    fig += d3py.xAxis('d1', label="Random")
    fig += d3py.yAxis('d2', label="Also random")
    fig.show()

########NEW FILE########
__FILENAME__ = d3py_vega_area
import d3py
import pandas as pd
import random

x = range(0, 21, 1)
y = [random.randint(25, 100) for num in range(0, 21, 1)]

df = pd.DataFrame({'x': x, 'y': y})

#Create Pandas figure
fig = d3py.PandasFigure(df, 'd3py_area', port=8080, columns=['x', 'y'])

#Add Vega Area plot
fig += d3py.vega.Area()

#Add interpolation to figure data
fig.vega + ({'value': 'basis'}, 'marks', 0, 'properties', 'enter', 
            'interpolate')
fig.show()
########NEW FILE########
__FILENAME__ = d3py_vega_bar
import d3py
import pandas as pd
import random

x = ['apples', 'oranges', 'grapes', 'bananas', 'plums', 'blackberries']
y = [10, 17, 43, 23, 31, 18]

df = pd.DataFrame({'x': x, 'y': y})

#Create Pandas figure
fig = d3py.PandasFigure(df, 'd3py_area', port=8000, columns=['x', 'y'])

#Add Vega Area plot
fig += d3py.vega.Bar()

#Show figure
fig.show()
########NEW FILE########
__FILENAME__ = d3py_vega_line
import d3py
import pandas as pd
import random

x = range(0, 101, 1)
y = [random.randint(10, 100) for num in range(0, 101, 1)]

df = pd.DataFrame({'x': x, 'y': y})

#Create Pandas figure
fig = d3py.PandasFigure(df, 'd3py_area', port=8000, columns=['x', 'y'])

#Add Vega Area plot
fig += d3py.vega.Line()

#Show figure
fig.show()


########NEW FILE########
__FILENAME__ = d3py_vega_scatter
import d3py
import pandas as pd
import random

n = 400
df = pd.DataFrame({'d1': np.arange(0,n),'d2': np.random.normal(0, 1, n)})

#Create Pandas figure
fig = d3py.PandasFigure(df, 'd3py_area', port=8000, columns=['d1', 'd2'])

#Add Vega Area plot
fig += d3py.vega.Scatter()

#Show figure
fig.show()


########NEW FILE########
__FILENAME__ = test_figure
  # -*- coding: utf-8 -*-
'''
Figure Test
-------

Test figure object with nose package:
https://nose.readthedocs.org/en/latest/

'''

import d3py
import nose.tools as nt


class TestFigure():

    def setup(self):
        '''Setup Figure object for testing'''

        self.Figure = d3py.Figure('test figure', 1024, 768, True, 'Asap',
                                  False, None, 'localhost', 8000,
                                  kwarg='test')

    def test_atts(self):
        '''Test attribute setting'''

        assert self.Figure.name == 'test_figure'
        assert self.Figure.host == 'localhost'
        assert self.Figure.port == 8000
        assert self.Figure._server_thread == None
        assert self.Figure.httpd == None
        assert self.Figure.interactive == True
        assert self.Figure.margins == {'bottom': 25, 'height': 768, 'left': 60,
                                       'right': 20, 'top': 10, 'width': 1024}
        assert self.Figure.font == 'Asap'
        assert self.Figure.args == {'font-family': "'Asap'; sans-serif",
                                    'height': 733, 'width': 944,
                                    'kwarg': 'test'}

########NEW FILE########
__FILENAME__ = test_javascript
#!/usr/bin/python

from d3py import javascript as JS

def test_JavaScript_object_lookup():
    g = JS.Selection("g").attr("color", "red")
    j = JS.JavaScript() + g

    assert(j.get_object("g", JS.Selection) == g)

    g.attr("test", "test")
    assert(j.get_object("g", JS.Selection) == g)

    f = JS.Function("test", None, "return 5")
    j += f

    assert(j.get_object("test", JS.Function) == f)

    f = "console.debug('hello')" + f
    assert(j.get_object("test", JS.Function) == f)

if __name__ == "__main__":
    test_JavaScript_object_lookup()



########NEW FILE########
